"""Durable per-replica command gate; NOT a native game or network adapter.

The trusted adapter supplies the room binding, a fresh timeline epoch, and an
attachment ID for one uninterrupted loaded world. It must intercept local
commands before native execution, serialize callbacks on the game thread, and
detect loads/process replacement. Those hooks are not implemented here.

SQLite and SAN14 cannot share a transaction. An intent without a durable result
therefore stops execution; it is never automatically retried or marked applied.
State hashes have only the caller-declared coverage, not an implied full world.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import secrets
import sqlite3


class JournalError(ValueError):
    pass


class ExecutionHeld(JournalError):
    pass


def require(ok, message):
    if not ok:
        raise JournalError(message)


def canonical(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise JournalError('Value is not canonical JSON') from error
    require(len(raw.encode('utf-8')) <= 1024 * 1024, 'Record exceeds size limit')
    return raw


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def hex_id(value, size=64):
    return type(value) is str and re.fullmatch('[0-9a-f]{%d}' % size, value) is not None


def scope_from_room(room, timeline_epoch, state_contract, initial_state_sha256):
    """Trusted in-process export, not an endpoint accepting client authority.

    This allocates no game state and does not advance WAITING_NATIVE_ADAPTER.
    Initial state coverage and timeline freshness are the adapter's obligation.
    """
    with room.lock:
        require(room.bindings is not None, 'Room faction binding is not locked')
        require(all(p['connection'] is not None for p in room.players.values()), 'Peer offline')
        scope = {'schema': 'san14.replica-scope.v1', 'room_id': room.room_id,
                 'binding_epoch': room.binding_epoch, 'timeline_epoch': timeline_epoch,
                 'profile': deepcopy(room.manifest['profile']), 'bindings': deepcopy(room.bindings),
                 'state_contract': state_contract, 'initial_state_sha256': initial_state_sha256}
    validate_scope(scope)
    return scope


def validate_scope(scope):
    require(type(scope) is dict and set(scope) == {'schema', 'room_id', 'binding_epoch',
            'timeline_epoch', 'profile', 'bindings', 'state_contract', 'initial_state_sha256'}, 'Bad scope')
    require(scope['schema'] == 'san14.replica-scope.v1', 'Unsupported scope')
    require(all(hex_id(scope[k], 32) for k in ('room_id', 'binding_epoch', 'timeline_epoch')), 'Bad epoch')
    require(hex_id(scope['initial_state_sha256']), 'Bad initial state digest')
    require(type(scope['state_contract']) is str and 1 <= len(scope['state_contract']) <= 200,
            'Missing hash coverage contract')
    profile = scope['profile']
    require(type(profile) is dict and set(profile) == {'protocol', 'game_sha256',
            'adapter_contract', 'checkpoint_sha256', 'rules_sha256'}, 'Bad profile')
    require(profile['protocol'] == 'san14.room.v1' and
            profile['adapter_contract'] == 'research-no-native-room-adapter.v1', 'Unsupported adapter')
    require(all(hex_id(profile[k]) for k in ('game_sha256', 'checkpoint_sha256', 'rules_sha256')),
            'Bad profile digest')
    bindings = scope['bindings']
    require(type(bindings) is dict and set(bindings) == {'A', 'B'}, 'Two bindings required')
    for binding in bindings.values():
        require(type(binding) is dict and set(binding) == {'force_id', 'main_district_id'}, 'Bad binding')
        require(all(type(v) is int and 1 <= v <= 51 for v in binding.values()), 'Bad force/district')
    require(bindings['A']['force_id'] != bindings['B']['force_id'] and
            bindings['A']['main_district_id'] != bindings['B']['main_district_id'], 'Duplicate binding')


def make_intent(scope, sequence, player_id, request_id, command, pre_state_sha256):
    """Authority-assigned order only. Native legality still needs rechecking."""
    intent = {'schema': 'san14.execution-intent.v1', 'scope_sha256': digest(scope),
              'sequence': sequence, 'player_id': player_id, 'request_id': request_id,
              'command': deepcopy(command), 'pre_state_sha256': pre_state_sha256}
    validate_intent(scope, intent)
    return intent


def validate_intent(scope, intent):
    require(type(intent) is dict and set(intent) == {'schema', 'scope_sha256', 'sequence',
            'player_id', 'request_id', 'command', 'pre_state_sha256'}, 'Bad intent')
    require(intent['schema'] == 'san14.execution-intent.v1' and
            intent['scope_sha256'] == digest(scope), 'Wrong room, binding or timeline')
    require(type(intent['sequence']) is int and 1 <= intent['sequence'] < 2**31, 'Bad sequence')
    require(type(intent['player_id']) is str and intent['player_id'] in ('A', 'B'), 'Bad player')
    require(hex_id(intent['request_id'], 32) and hex_id(intent['pre_state_sha256']), 'Bad request/digest')
    command = intent['command']
    require(type(command) is dict and command.get('schema') == 'san14.authority-reward-command.v1',
            'Only the research reward command contract is connected')
    force = scope['bindings'][intent['player_id']]['force_id']
    require(type(command.get('force_id')) is int and command['force_id'] == force, 'Wrong command owner')
    require(command.get('game_sha256') == scope['profile']['game_sha256'], 'Wrong game build')
    canonical(intent)


class ExecutionJournal:
    """One file per replica, timeline, and continuously loaded world.

    Create is explicit/exclusive. Reopening must supply the SAME attachment ID;
    a reload/restart requires a verified common checkpoint and a new timeline,
    not reusing receipts for effects which have since been rolled back.
    """
    def __init__(self, path, scope, local_player, attachment_id, *, create=False):
        validate_scope(scope)
        require(type(local_player) is str and local_player in ('A', 'B'), 'Bad local player')
        require(hex_id(attachment_id, 32), 'Bad native attachment ID')
        self.path = Path(path).resolve()
        self.scope = deepcopy(scope)
        self.identity = {'scope': self.scope, 'local_player': local_player, 'attachment_id': attachment_id}
        if create:
            # Never erase or silently recreate a missing execution history.
            with self.path.open('xb'):
                pass
            with self._transaction() as db:
                db.execute('CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), identity TEXT NOT NULL, halt TEXT)')
                db.execute('CREATE TABLE entries (sequence INTEGER PRIMARY KEY, player TEXT NOT NULL, '
                           'request_id TEXT NOT NULL, fingerprint TEXT NOT NULL, intent TEXT NOT NULL, '
                           'status TEXT NOT NULL, token TEXT NOT NULL, receipt TEXT, '
                           'UNIQUE(player, request_id))')
                db.execute('INSERT INTO metadata VALUES(1,?,NULL)', (canonical(self.identity),))
                db.execute('PRAGMA user_version=1')
        with self._transaction() as db:
            require(db.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'Journal integrity check failed')
            require(db.execute('PRAGMA user_version').fetchone()[0] == 1, 'Unsupported journal version')
            row = db.execute('SELECT identity FROM metadata WHERE id=1').fetchone()
            require(row is not None and row[0] == canonical(self.identity), 'Journal scope/attachment mismatch')

    @contextmanager
    def _transaction(self):
        # mode=rw rejects a missing file instead of losing the once-only history.
        db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=5, isolation_level=None)
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

    def _state(self, db):
        metadata = db.execute('SELECT identity,halt FROM metadata WHERE id=1').fetchone()
        require(metadata is not None and metadata['identity'] == canonical(self.identity), 'Journal identity changed')
        rows = db.execute('SELECT * FROM entries ORDER BY sequence').fetchall()
        unknown = [r['sequence'] for r in rows if r['status'] != 'APPLIED']
        applied = [r for r in rows if r['status'] == 'APPLIED']
        tip = applied[-1] if applied else None
        receipt = json.loads(tip['receipt']) if tip else None
        return {'halt': metadata['halt'], 'unknown_sequences': unknown,
                'sequence': tip['sequence'] if tip else 0,
                'state_sha256': receipt['post_state_sha256'] if receipt else self.scope['initial_state_sha256'],
                'prefix_sha256': receipt['prefix_sha256'] if receipt else digest(self.scope)}

    @staticmethod
    def _unheld(state):
        if state['halt'] or state['unknown_sequences']:
            raise ExecutionHeld(state['halt'] or 'Execution result unknown; do not retry native call')

    def _halt(self, reason):
        with self._transaction() as db:
            db.execute('UPDATE metadata SET halt=COALESCE(halt,?) WHERE id=1', (reason,))

    def execute(self, intent, observe, invoke):
        """Observe -> persist intent -> native callback -> observe -> persist result.

        The observer returns a semantic digest under scope.state_contract. The
        callback must verify native success and return a JSON object. Exceptions
        or death after reservation leave an unresolved intent. Nothing retries it.
        These Python callbacks are an adapter boundary, not a game-thread hook.
        """
        intent = deepcopy(intent)
        validate_intent(self.scope, intent)
        fingerprint = digest(intent)
        drift = False
        with self._transaction() as db:
            state = self._state(db)
            self._unheld(state)
            existing = db.execute('SELECT * FROM entries WHERE sequence=?', (intent['sequence'],)).fetchone()
            if existing:
                require(existing['fingerprint'] == fingerprint, 'Sequence reused with different intent')
            else:
                require(db.execute('SELECT 1 FROM entries WHERE player=? AND request_id=?',
                        (intent['player_id'], intent['request_id'])).fetchone() is None,
                        'Request already assigned another sequence')
                require(intent['sequence'] == state['sequence'] + 1, 'Out-of-order sequence')
                require(intent['pre_state_sha256'] == state['state_sha256'], 'Wrong input state for next command')
            observed = observe()
            require(hex_id(observed), 'Observer did not return a state digest')
            if observed != state['state_sha256']:
                db.execute('UPDATE metadata SET halt=? WHERE id=1', ('Observed state differs from journal tip',))
                drift = True
            elif existing:
                receipt = json.loads(existing['receipt'])
                return {**receipt, 'duplicate': True, 'native_invoked': False}
            else:
                token = secrets.token_hex(16)
                db.execute('INSERT INTO entries VALUES(?,?,?,?,?,?,?,NULL)',
                           (intent['sequence'], intent['player_id'], intent['request_id'], fingerprint,
                            canonical(intent), 'INTENT', token))
        if drift:
            raise ExecutionHeld('Observed state differs from journal tip; common recovery required')
        try:
            result = invoke()
            require(type(result) is dict, 'Native adapter must return a verified result object')
            canonical(result)
            after = observe()
            require(hex_id(after), 'Post-execution observer failed')
            receipt = {'status': 'APPLIED_LOCAL', 'sequence': intent['sequence'],
                       'player_id': intent['player_id'], 'request_id': intent['request_id'],
                       'intent_sha256': fingerprint, 'post_state_sha256': after, 'native_result': result,
                       'prefix_sha256': digest({'previous': state['prefix_sha256'],
                                               'intent': fingerprint, 'post_state': after})}
            with self._transaction() as db:
                require(db.execute('SELECT halt FROM metadata WHERE id=1').fetchone()[0] is None,
                        'Execution held during callback')
                updated = db.execute('UPDATE entries SET status=?,receipt=? WHERE sequence=? AND token=? AND status=?',
                                     ('APPLIED', canonical(receipt), intent['sequence'], token, 'INTENT'))
                require(updated.rowcount == 1, 'Execution reservation changed')
            return {**receipt, 'duplicate': False, 'native_invoked': True}
        except Exception as error:
            # Even a callback exception may occur AFTER a native write.
            self._halt('Native execution or result persistence uncertain; common recovery required')
            raise ExecutionHeld('Result uncertain; native call must not be retried') from error

    def report(self, observe):
        """An applied-prefix observation, NOT permission to advance the game."""
        drift = False
        with self._transaction() as db:
            state = self._state(db)
            self._unheld(state)
            current = observe()
            require(hex_id(current), 'Observer did not return a state digest')
            if current != state['state_sha256']:
                db.execute('UPDATE metadata SET halt=? WHERE id=1', ('Observed state differs from journal tip',))
                drift = True
        if drift:
            raise ExecutionHeld('Observed state differs from journal tip')
        return {'schema': 'san14.applied-prefix.v1', 'scope_sha256': digest(self.scope),
                'local_player': self.identity['local_player'], 'attachment_id': self.identity['attachment_id'],
                'sequence': state['sequence'], 'state_sha256': state['state_sha256'],
                'prefix_sha256': state['prefix_sha256'], 'state_contract': self.scope['state_contract']}

    def status(self):
        with self._transaction() as db:
            state = self._state(db)
        return {**state, 'phase': 'HOLD' if state['halt'] or state['unknown_sequences'] else 'IDLE',
                'native_gameplay_enabled': False}


def compare_applied_prefixes(scope, target_sequence, reports):
    """Trusted local observations of both replicas; no network authentication.

    The future coordinator must bind reports to authenticated connections and
    the currently attached game. A match is evidence only for this hash contract.
    It cannot open native gameplay or establish complete world synchronization.
    """
    validate_scope(scope)
    require(type(target_sequence) is int and 0 <= target_sequence < 2**31, 'Bad target sequence')
    require(type(reports) is dict and set(reports) == {'A', 'B'}, 'Both replica reports required')
    keys = {'schema', 'scope_sha256', 'local_player', 'attachment_id', 'sequence',
            'state_sha256', 'prefix_sha256', 'state_contract'}
    for player, report in reports.items():
        require(type(report) is dict and set(report) == keys, 'Bad replica report')
        require(report['schema'] == 'san14.applied-prefix.v1' and report['local_player'] == player and
                report['scope_sha256'] == digest(scope), 'Wrong replica report identity')
        require(type(report['sequence']) is int and report['sequence'] == target_sequence, 'Replica has not applied target prefix')
        require(report['state_contract'] == scope['state_contract'] and hex_id(report['attachment_id'], 32) and
                hex_id(report['state_sha256']) and hex_id(report['prefix_sha256']), 'Bad replica coverage/digest')
    require(reports['A']['state_sha256'] == reports['B']['state_sha256'] and
            reports['A']['prefix_sha256'] == reports['B']['prefix_sha256'], 'Replica prefixes diverged')
    return {'status': 'PAIRED_EXECUTION_PREFIX_MATCH', 'sequence': target_sequence,
            'state_contract': scope['state_contract'], 'native_gameplay_enabled': False,
            'full_world_synchronization_proven': False}
