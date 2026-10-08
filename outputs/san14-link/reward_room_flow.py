"""Reward planning successor: authenticated room -> ordered journals -> replicas.

No game discovery, hooks, or start-game endpoint. Local ports must supply fresh
contexts, verified execution, a stable semantic hash contract and attachment
identity. The provided integration tests use independently owned fixture worlds.
This does not certify complete SAN14 state, UI refresh, or native input fencing.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
import hashlib
import hmac
from pathlib import Path
import secrets
import socketserver
import sqlite3
import threading

import authority_reward as reward
import authoritative_sync as sync
import execution_journal as journal
from room_session import RoomError
import room_transport as transport


class FlowError(ValueError):
    pass


def require(value, message):
    if not value:
        raise FlowError(message)


def object_keys(value, keys):
    require(type(value) is dict and set(value) == set(keys), 'Unsupported fields')


def report_proof(key, report):
    """Private local-adapter key, never a room credential or client JSON field.

    The trusted consumer calls this only after Replica.report observed its own
    journal/world. Production must provision this channel from its native owner;
    this module does not defend against a compromised local adapter/OS process.
    """
    require(type(key) is bytes and len(key) == 32, 'Missing trusted adapter key')
    return hmac.new(key, ('san14.reward-adapter-report.v1\n' + journal.canonical(report)).encode('utf-8'),
                    hashlib.sha256).hexdigest()


class Replica:
    """Local adapter boundary. It never accepts a remote 'executed' flag.

    Both journals store the same authority intent. Local viewer/context hashes
    are rebuilt only inside invoke; process-local addresses never cross the wire.
    """
    def __init__(self, path, scope, player, port):
        self.port = port
        self.scope = deepcopy(scope)
        self.player = player
        self.attachment = port.attachment_id
        require(journal.hex_id(self.attachment, 32), 'Bad local attachment')
        self.journal = journal.ExecutionJournal(path, scope, player, self.attachment, create=True)

    def observe(self):
        require(self.port.attachment_id == self.attachment, 'Loaded world changed')
        value = self.port.observe()
        require(journal.hex_id(value), 'Missing semantic observation')
        return value

    def command(self, force, district, officers):
        self.observe()  # also checks the uninterrupted local attachment
        context = self.port.context(force)
        command = reward.make_command(context, district, officers)
        reward.validate_reward(command, context, authorized_force_id=force)
        return command

    def apply(self, intent):
        journal.validate_intent(self.scope, intent)
        force = self.scope['bindings'][intent['player_id']]['force_id']

        def invoke():
            remote = intent['command']
            local = self.command(force, remote['district_id'], remote['officer_ids'])
            semantic = lambda c: {k: v for k, v in c.items() if k != 'context_sha256'}
            require(semantic(local) == semantic(remote), 'Native semantic command changed')
            result = self.port.execute(local)
            require(type(result) is dict and all(result.get(k) is True for k in
                    ('native_returned', 'args_released', 'owned_slot_cleared')),
                    'Native result/cleanup not verified')
            return result

        return self.journal.execute(intent, self.observe, invoke)

    def report(self):
        return self.journal.report(self.observe)


class RewardFlow:
    """One planning boundary. Native execution is pumped by a trusted caller.

    Network handlers only enqueue commands and attest locally produced reports.
    A and B use the same queue. One command awaits B before the next is invoked.
    SQLite reserves dispatch before native effects; uncertainty/disconnect is
    terminal for this instance, with no automatic replay or host restart.
    """
    def __init__(self, folder, room, host_port, guest_attachment, state_contract, initial_node, *, guest_report_key):
        self.folder = Path(folder).resolve()
        self.folder.mkdir(parents=True, exist_ok=True)
        self.room = room
        self.lock = threading.RLock()
        require(type(guest_report_key) is bytes and len(guest_report_key) == 32,
                'Guest report verifier must come from separate trusted bootstrap')
        self._guest_report_key = guest_report_key
        self.period = sync.PeriodCoordinator(sync.scope_from_room(room), state_contract,
                host_port.observe(), {'A': host_port.attachment_id, 'B': guest_attachment}, initial_node)
        self.scope = journal.scope_from_room(room, self.period.epoch, state_contract, host_port.observe())
        require(self.scope['initial_state_sha256'] == self.period.reports['A']['world_sha256'],
                'Initial observation changed')
        self.host = Replica(self.folder / 'host-execution.sqlite', self.scope, 'A', host_port)
        self.db_path = self.folder / 'authority-queue.sqlite'
        with self.db_path.open('xb'):
            pass  # Never discard or reopen an unknown previous execution history.
        with self.db() as db:
            db.execute('CREATE TABLE metadata (id INTEGER PRIMARY KEY, scope TEXT, halt TEXT)')
            db.execute('INSERT INTO metadata VALUES (1,?,NULL)', (journal.canonical(self.scope),))
            db.execute('CREATE TABLE requests (ordinal INTEGER PRIMARY KEY AUTOINCREMENT, '
                       'player TEXT, request_id TEXT, fingerprint TEXT, proposal TEXT, status TEXT, '
                       'intent TEXT, host_receipt TEXT, guest_report TEXT, error TEXT, '
                       'UNIQUE(player,request_id))')
        self.last_guest = None

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.db_path.as_uri() + '?mode=rw', uri=True,
                             isolation_level=None, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def hold(self, reason):
        with self.db() as db:
            db.execute('UPDATE metadata SET halt=COALESCE(halt,?) WHERE id=1', (reason,))
        self.period.ready.clear()

    def _host_report(self):
        try:
            return self.host.report()
        except Exception as error:
            self.hold('Host observation/attachment unavailable: ' + str(error))
            raise

    def _active(self, planning=True):
        with self.db() as db:
            halt = db.execute('SELECT halt FROM metadata WHERE id=1').fetchone()[0]
        require(halt is None, halt or 'Held')
        require(self.period.connected == {'A', 'B'}, 'Peer offline')
        if planning:
            require(self.period.phase == 'PLANNING', 'Planning closed')

    def _authenticated(self, player, connection):
        require(player in ('A', 'B') and self.room.players[player]['connection'] == connection,
                'Connection is not the authenticated seat')
        require(self.room.bindings == self.scope['bindings'] and
                self.room.binding_epoch == self.scope['binding_epoch'], 'Room binding changed')

    def _envelope(self, request, fields):
        object_keys(request, {'action', 'room_id', 'binding_epoch', 'epoch'} | set(fields))
        require(request['room_id'] == self.scope['room_id'] and
                request['binding_epoch'] == self.scope['binding_epoch'] and
                request['epoch'] == self.scope['timeline_epoch'], 'Stale room/binding/period')

    def _pending(self):
        with self.db() as db:
            rows = db.execute("SELECT player,request_id FROM requests WHERE status NOT IN ('PAIRED','REJECTED')").fetchall()
        for player in ('A', 'B'):
            self.period.set_pending(player, self.period.epoch,
                    {r['request_id'] for r in rows if r['player'] == player})

    @staticmethod
    def _public(row):
        return {k: row[k] for k in ('ordinal', 'player', 'request_id', 'status', 'error')}

    def _submit(self, player, request):
        self._envelope(request, {'request_id', 'district_id', 'officer_ids'})
        require(journal.hex_id(request['request_id'], 32), 'Bad request ID')
        require(type(request['district_id']) is int and 1 <= request['district_id'] <= 51, 'Bad district')
        ids = request['officer_ids']
        require(type(ids) is list and 1 <= len(ids) <= 16 and
                all(type(i) is int and 1 <= i < 6000 for i in ids) and len(set(ids)) == len(ids),
                'Bad/duplicate officer IDs or owned adapter capacity exceeded')
        fingerprint = journal.digest(request)
        with self.db() as db:
            old = db.execute('SELECT * FROM requests WHERE player=? AND request_id=?',
                             (player, request['request_id'])).fetchone()
            if old:
                require(old['fingerprint'] == fingerprint, 'Request ID reused with changed command')
                return {**self._public(old), 'duplicate': True}
            require(player not in self.period.ready, 'Ready player cannot submit')
            require(db.execute('SELECT count(*) FROM requests').fetchone()[0] < 4096, 'Planning request limit')
            require(db.execute("SELECT count(*) FROM requests WHERE status IN ('QUEUED','DISPATCHING','AWAITING_B')").fetchone()[0] < 128,
                    'Queue full')
            db.execute('INSERT INTO requests(player,request_id,fingerprint,proposal,status) VALUES(?,?,?,?,?)',
                       (player, request['request_id'], fingerprint, journal.canonical(request), 'QUEUED'))
            row = db.execute('SELECT * FROM requests WHERE player=? AND request_id=?',
                             (player, request['request_id'])).fetchone()
        self._pending()
        return {**self._public(row), 'duplicate': False}

    def pump_one(self):
        """Called on the adapter's serialized execution lane, never TLS threads."""
        with self.lock, self.room.lock:
            self._active()
            require(self.last_guest is not None, 'Guest initial state not attested')
            with self.db() as db:
                require(not db.execute("SELECT 1 FROM requests WHERE status='DISPATCHING'").fetchone(),
                        'Unresolved native dispatch; recovery required')
                if db.execute("SELECT 1 FROM requests WHERE status='AWAITING_B'").fetchone():
                    return {'status': 'WAITING_GUEST_APPLICATION'}
                row = db.execute("SELECT * FROM requests WHERE status='QUEUED' ORDER BY ordinal LIMIT 1").fetchone()
            if row is None:
                return {'status': 'QUEUE_EMPTY'}
            proposal = json.loads(row['proposal'])
            force = self.scope['bindings'][row['player']]['force_id']
            before = self._host_report()
            try:
                command = self.host.command(force, proposal['district_id'], proposal['officer_ids'])
            except reward.PreflightError as error:
                legal_rejections = {'identity', 'district_owner', 'unsupported_funding', 'funding_city',
                                    'officer_ids', 'duplicate_officer', 'officer_identity', 'officer_owner',
                                    'menu_scope', 'officer_ineligible', 'insufficient_gold', 'insufficient_actions'}
                if error.code not in legal_rejections:
                    self.hold('Host context could not be verified: ' + str(error))
                    raise
                # No intent/native call reserved: legality failure is a terminal rejection.
                with self.db() as db:
                    db.execute("UPDATE requests SET status='REJECTED',error=? WHERE ordinal=?", (str(error), row['ordinal']))
                self._pending()
                return {'status': 'REJECTED', 'error': str(error)}
            except Exception as error:
                self.hold('Host adapter/context unavailable: ' + str(error))
                raise
            intent = journal.make_intent(self.scope, before['sequence'] + 1, row['player'],
                                         row['request_id'], command, before['state_sha256'])
            with self.db() as db:
                db.execute("UPDATE requests SET status='DISPATCHING',intent=? WHERE ordinal=?",
                           (journal.canonical(intent), row['ordinal']))
            try:
                receipt = self.host.apply(intent)
                self._host_report()  # verifies attachment/current tip after the native callback
                with self.db() as db:
                    db.execute("UPDATE requests SET status='AWAITING_B',host_receipt=? WHERE ordinal=?",
                               (journal.canonical(receipt), row['ordinal']))
                return {'status': 'AWAITING_B', 'sequence': intent['sequence']}
            except Exception:
                self.hold('Host dispatch/result uncertain; never automatically retry')
                raise

    def _accept_report(self, player, report, proof):
        require(player == 'B', 'Only guest supplies guest replica report')
        require(journal.hex_id(proof) and hmac.compare_digest(proof, report_proof(self._guest_report_key, report)),
                'Missing/invalid trusted replica attestation')
        require(type(report) is dict and report.get('attachment_id') == self.period.attachments['B'],
                'Guest attachment changed')
        with self.db() as db:
            row = db.execute("SELECT * FROM requests WHERE status='AWAITING_B'").fetchone()
        host_report = self._host_report()
        if report == self.last_guest and report['sequence'] < host_report['sequence']:
            # Acknowledgement loss/retransmission is not a second native effect
            # and cannot authorize the newer command that is still awaiting B.
            return {'status': 'ALREADY_CONFIRMED', 'sequence': report['sequence'],
                    'native_gameplay_enabled': False, 'full_world_synchronization_proven': False}
        if row is None:
            # An initial observation or a duplicate last acknowledgement, never a future effect.
            target = host_report['sequence']
            require(target == 0 or report == self.last_guest, 'Unsolicited guest report')
        else:
            intent = json.loads(row['intent'])
            target = intent['sequence']
        paired = journal.compare_applied_prefixes(self.scope, target, {'A': host_report, 'B': report})
        self.last_guest = deepcopy(report)
        if row is not None:
            with self.db() as db:
                db.execute("UPDATE requests SET status='PAIRED',guest_report=? WHERE ordinal=?",
                           (journal.canonical(report), row['ordinal']))
        # The two frozen modules use different initial hash seeds. At sequence 0
        # compare the actual journals, retain the coordinator's own initial seed.
        # From sequence 1 onward both use the verified journal prefix verbatim.
        if target > 0:
            for seat, observation in (('A', host_report), ('B', report)):
                self.period.applied_prefix(seat, self.period.epoch, target, observation['prefix_sha256'],
                        observation['state_sha256'], self.period.attachments[seat])
        self._pending()
        return paired

    def handle(self, player, connection, request):
        with self.lock, self.room.lock:
            self._authenticated(player, connection)
            require(type(request) is dict, 'Expected object')
            action = request.get('action')
            if action == 'reward_status':
                object_keys(request, {'action'})
                return {'ok': True, **self.status()}
            self._active()
            if action == 'reward_scope':
                object_keys(request, {'action'})
                result = {'scope': deepcopy(self.scope), 'attachment': self.period.attachments[player]}
            elif action == 'reward_submit':
                result = self._submit(player, request)
            elif action == 'reward_next':
                self._envelope(request, set())
                require(player == 'B', 'Only guest consumes remote queue')
                with self.db() as db:
                    row = db.execute("SELECT intent FROM requests WHERE status='AWAITING_B'").fetchone()
                result = {'intent': json.loads(row[0]) if row else None}
            elif action == 'reward_report':
                self._envelope(request, {'report', 'proof'})
                try:
                    result = self._accept_report(player, request['report'], request['proof'])
                except (journal.ExecutionHeld, FlowError, journal.JournalError) as error:
                    # A mismatch after native effects may mean state diverged. No future dispatch.
                    self.hold('Replica report not verified: ' + str(error))
                    raise
            elif action == 'reward_ready':
                self._envelope(request, {'value'})
                require(self.last_guest is not None, 'Guest initial observation missing')
                self._host_report()
                self.period.set_ready(player, self.period.epoch, request['value'])
                result = {'ready': sorted(self.period.ready)}
            else:
                raise FlowError('Unsupported reward action')
            return {'ok': True, **result, 'native_gameplay_enabled': False}

    def seal(self):
        """Protocol cut only. Does not set native ReadyFence or advance SAN14."""
        with self.lock, self.room.lock:
            self._active()
            require(self.last_guest is not None, 'Guest observation missing')
            report = self._host_report()
            journal.compare_applied_prefixes(self.scope, report['sequence'], {'A': report, 'B': self.last_guest})
            self._pending()
            return {'status': 'PROTOCOL_INPUTS_SEALED', 'cut': self.period.seal_inputs(),
                    'native_gameplay_enabled': False, 'native_ready_fence_verified': False}

    def disconnect(self, player, connection):
        with self.lock, self.room.lock:
            if self.room.players[player]['connection'] != connection:
                return
            self.room.disconnect(player, connection)
            self.period.connection(player, False)
            self.hold('Authenticated peer disconnected; explicit common recovery required')

    def status(self):
        with self.lock, self.db() as db:
            halt = db.execute('SELECT halt FROM metadata WHERE id=1').fetchone()[0]
            count = db.execute('SELECT count(*) FROM requests').fetchone()[0]
            rows = db.execute('SELECT * FROM requests ORDER BY ordinal DESC LIMIT 32').fetchall()[::-1]
        return {'flow_status': 'HELD' if halt else self.period.phase, 'halt': halt,
                'requests': [self._public(r) for r in rows], 'request_count': count, 'epoch': self.period.epoch,
                'ready': sorted(self.period.ready), 'host': self.host.journal.status(),
                'native_gameplay_enabled': False, 'full_world_synchronization_proven': False,
                'host_restart_recovery_implemented': False}


def envelope(scope, action, **fields):
    return {'action': action, 'room_id': scope['room_id'], 'binding_epoch': scope['binding_epoch'],
            'epoch': scope['timeline_epoch'], **fields}


class FlowHandler(socketserver.StreamRequestHandler):
    """Successor to the frozen room handler; every action keeps its TLS identity."""
    def handle(self):
        connection, player = secrets.token_hex(16), None
        self.connection.settimeout(30)
        try:
            greeting = self.server.room.authenticate(transport.read_packet(self.rfile), connection)
            player = greeting['player_id']
            transport.write_packet(self.wfile, {'ok': True, **greeting})
            while True:
                request = transport.read_packet(self.rfile)
                try:
                    if str(request.get('action', '')).startswith('reward_'):
                        require(self.server.flow is not None, 'Reward adapter not attached')
                        response = self.server.flow.handle(player, connection, request)
                    else:
                        response = self.server.room.handle(player, connection, request)
                except (ValueError, TypeError, KeyError) as error:
                    response = {'ok': False, 'error': str(error), 'native_gameplay_enabled': False}
                transport.write_packet(self.wfile, response)
        except (RoomError, ValueError, TypeError) as error:
            try:
                transport.write_packet(self.wfile, {'ok': False, 'error': str(error)})
            except OSError:
                pass
        except (EOFError, OSError):
            pass
        finally:
            if player is not None:
                if self.server.flow is not None:
                    self.server.flow.disconnect(player, connection)
                else:
                    self.server.room.disconnect(player, connection)


class FlowServer(transport.Server):
    def __init__(self, address, room, cert, key):
        # Offline successor remains loopback-only until real adapters are proven.
        require(address[0] == '127.0.0.1', 'Offline reward flow requires loopback')
        self.flow = None
        super().__init__(address, room, cert, key)
        self.RequestHandlerClass = FlowHandler
