"""B durable bytes -> authenticated round trip -> A coordinator.received.

Composes the exact existing RulesContextRoom. No load intent, native callback,
world receipt or Ready endpoint is added. Returning bytes proves possession,
not remote fsync or a native hold. This prototype deliberately sends the two
parts back once; it is not the final bandwidth optimization.
"""
import base64
from copy import deepcopy
import secrets
import threading

from checkpoint_rules_context import (RulesContextRoom, remote_context,
    context_from_room, _retire)
from checkpoint_room_client import RoomConnection
from checkpoint_room_artifacts import require, RoomError, SyncError
from authoritative_sync import (CheckpointReceiver, canonical, digest, hexid, CHUNK)
from checkpoint_journal import CheckpointJournal


FLAGS = dict(native_loaded=False, full_world_verified=False, native_permission=False,
             native_pause_confirmed=False, ready=False)
ACTIONS = {'checkpoint_delivery_begin', 'checkpoint_delivery_chunk', 'checkpoint_delivery_finish'}
COMMON = {'action', 'checkpoint_id', 'context_sha256'}


class DeliveryControlEndpoint:
    """Control-listener wrapper; all state uses the real Room's outer lock.

    One receiver at a time, replaced only after the Room has independently
    advanced from a completed prior checkpoint. No per-message lock inversion,
    timer, automatic retry/reconnect or repair of another native owner.
    """
    def __init__(self, room):
        require(type(room) is RulesContextRoom, 'Exact existing RulesContextRoom required')
        self.room = room
        self._row = None
        self._previous = None

    def authenticate(self, request, connection):
        return self.room.authenticate(request, connection)

    def disconnect(self, player, connection):
        with self.room.lock:
            self.room.disconnect(player, connection)
            row = self._row
            if row and connection in row['connections'].values():
                self._fail('CONTROL_DISCONNECTED')

    def _context(self, player, connection, packet):
        require(player == 'B' and self.room.players.get('B', {}).get('connection') == connection,
                'Only current authenticated B control may return checkpoint bytes')
        require(hexid(packet['checkpoint_id']) and hexid(packet['context_sha256']),
                'Invalid checkpoint/context identity')
        require(self.room._rules_contexts.get('B') ==
                (connection, packet['context_sha256'], packet['checkpoint_id']),
                'Explicit pinned rules context required')
        value = context_from_room(self.room, 'B', packet['checkpoint_id'])
        require(digest(value) == packet['context_sha256'], 'Pinned context changed')
        require(self.room._coordinator.load_intent is None, 'Load already attempted')
        return value

    def _reply(self, *, duplicate=False):
        row = self._row
        return dict(ok=True, transaction=row['id'], checkpoint_id=row['checkpoint_id'],
            context_sha256=row['context_sha256'], state=row['state'], duplicate=duplicate,
            returned_bytes=row['returned_bytes'], total_bytes=row['total_bytes'],
            byte_roundtrip_verified=row['state'] == 'RECEIVED',
            remote_durable_stage_verified=False, **FLAGS)

    def _fail(self, reason):
        row = self._row
        if row is None or row['state'] == 'HELD':
            return
        row.update(state='HELD', failure=reason, protocol_revocation_confirmed=False)
        try:
            _retire(self.room)
            row['protocol_revocation_confirmed'] = True
        except BaseException as exc:
            row['cleanup_error'] = type(exc).__name__

    def _begin(self, player, connection, packet):
        require(set(packet) == COMMON | {'request_id'} and hexid(packet['request_id'], 32),
                'Invalid delivery begin fields')
        value = self._context(player, connection, packet)
        c = self.room._coordinator
        row = self._row
        if row and row['checkpoint_id'] == packet['checkpoint_id']:
            require(row['state'] != 'HELD' and row['request_id'] == packet['request_id'] and
                    row['context'] == canonical(value) and row['connection'] == connection,
                    'Existing delivery cannot be replaced or rebound')
            require(c.bytes_received is (row['state'] == 'RECEIVED'), 'Delivery confirmation state changed')
            return self._reply(duplicate=True)
        require(c.bytes_received is False, 'Unknown prior byte confirmation')
        if row:
            require(row['state'] == 'RECEIVED' and row['checkpoint_id'] in c.applied_receipts and
                    self.room._generation == row['generation'] + 1,
                    'Previous checkpoint has not completed its independent lifecycle')
            self._previous = {k: row[k] for k in ('checkpoint_id', 'state', 'generation')}
        m = value['checkpoint']['manifest']
        receiver = CheckpointReceiver(m, packet['checkpoint_id'], value['scope'],
                                     m['epoch'], m['period'], m['cut'])
        self._row = dict(id=secrets.token_hex(16), request_id=packet['request_id'],
            connection=connection, connections=dict(self.room._connections),
            checkpoint_id=packet['checkpoint_id'], context_sha256=packet['context_sha256'],
            context=canonical(value), generation=self.room._generation, receiver=receiver,
            state='RECEIVING', returned_bytes=0,
            total_bytes=sum(p['size'] for p in m['parts'].values()),
            failure=None, protocol_revocation_confirmed=False, cleanup_error=None)
        return self._reply()

    def handle(self, player, connection, packet):
        action = packet.get('action') if type(packet) is dict else None
        if type(action) is not str or action not in ACTIONS:
            return self.room.handle(player, connection, packet)
        with self.room.lock:
            row = self._row
            # Foreign/malformed tokens cannot retire the current transaction.
            owns = bool(row and player == 'B' and connection == row['connection'] and
                        packet.get('transaction') == row['id'])
            try:
                c = self.room._coordinator
                require(c is not None, 'No bound coordinator')
                with c.lock:
                    if action == 'checkpoint_delivery_begin':
                        return self._begin(player, connection, packet)
                    extra = {'transaction', 'chunk'} if action.endswith('_chunk') else {'transaction'}
                    require(set(packet) == COMMON | extra and hexid(packet['transaction'], 32),
                            'Invalid delivery fields')
                    require(owns, 'Unknown delivery owner')
                    require(row['state'] != 'HELD', 'Delivery is terminally held')
                    value = self._context(player, connection, packet)
                    require(row['checkpoint_id'] == packet['checkpoint_id'] and
                            row['context_sha256'] == packet['context_sha256'] and
                            row['context'] == canonical(value) and row['generation'] == self.room._generation,
                            'Delivery generation or binding changed')
                    if action.endswith('_chunk'):
                        require(row['state'] == 'RECEIVING' and c.bytes_received is False,
                                'Byte return no longer open')
                        accepted = row['receiver'].accept(packet['chunk'])
                        if not accepted['duplicate']:
                            row['returned_bytes'] += len(base64.b64decode(packet['chunk']['data'], validate=True))
                        return self._reply(duplicate=accepted['duplicate'])
                    if row['state'] == 'RECEIVED':
                        require(c.bytes_received is True, 'Completed byte confirmation changed')
                        row['receiver'].verified_parts()
                        return self._reply(duplicate=True)
                    require(c.bytes_received is False, 'Unexpected external byte confirmation')
                    row['receiver'].verified_parts()
                    # A's independent receiver is the exact frozen-core type.
                    # This certifies the byte round trip, not B's game/disk state.
                    c.received('B', value['coordinator']['epoch'], row['receiver'])
                    require(c.bytes_received is True and c.load_intent is None,
                            'Byte acknowledgement changed native attempt state')
                    row['state'] = 'RECEIVED'
                    return self._reply()
            except (RoomError, SyncError, TypeError, ValueError, KeyError) as exc:
                if owns:
                    self._fail(type(exc).__name__)
                return dict(ok=False, error=str(exc), applied_to_game=False, **FLAGS)
            except BaseException:
                if owns:
                    self._fail('UNEXPECTED_DELIVERY_FAILURE')
                raise

    def status(self):
        with self.room.lock:
            row = self._row
            current = False
            if row and row['state'] != 'HELD':
                try:
                    c = self.room._coordinator
                    with c.lock:
                        value = self._context('B', row['connection'], row)
                        current = (row['context'] == canonical(value) and
                                   c.bytes_received is (row['state'] == 'RECEIVED'))
                except (RoomError, SyncError, TypeError, ValueError, KeyError):
                    pass
            return dict(state=row['state'] if row else 'EMPTY', current=current,
                can_return_bytes=current and row['state'] == 'RECEIVING' if row else False,
                returned_bytes=row['returned_bytes'] if row else 0,
                checkpoint_id=row['checkpoint_id'] if row else None,
                previous=deepcopy(self._previous),
                failure=row['failure'] if row else None,
                protocol_revocation_confirmed=row['protocol_revocation_confirmed'] if row else False,
                cleanup_error=row['cleanup_error'] if row else None, **FLAGS)


class GuestDelivery:
    """One explicit return of the current B journal; no native execution.

    Reopens and rehashes actual SQLite content before network acknowledgement.
    Failure retains the journal and requests protocol revocation, never claims
    that a game was paused. A later invocation cannot replay this object.
    """
    def __init__(self, connection, expected_profile, journal):
        require(type(connection) is RoomConnection and connection.player_id == 'B',
                'Real B control connection required')
        require(type(journal) is CheckpointJournal, 'Existing durable journal required')
        # Create our own context from THIS connection. A caller-supplied context
        # could belong to another room and a failed request would retire it.
        source = remote_context(connection, expected_profile, journal.identity['checkpoint_id'])
        self.connection, self.source, self.journal = connection, source, journal
        self.lock = threading.RLock()
        self.state = 'NEW'
        self.error = None
        self.transaction = None

    def _journal(self):
        self.source.check()
        context = self.source.value
        require(context['player'] == 'B' and context['checkpoint'] is not None,
                'B checkpoint context required')
        identity = self.journal.identity
        require(identity['scope'] == context['scope'] and
                identity['manifest'] == context['checkpoint']['manifest'] and
                identity['checkpoint_id'] == context['checkpoint']['id'] and
                identity['attachments'] == context['coordinator']['attachments'],
                'Journal belongs to another checkpoint/world')
        m = identity['manifest']
        reopened = CheckpointJournal(self.journal.path, identity['scope'], m,
            identity['checkpoint_id'], m['epoch'], m['period'], m['cut'], identity['attachments'])
        require(reopened.status()['status'] == 'STAGED', 'Only a fresh STAGED journal can acknowledge bytes')
        return reopened.verified_parts()

    def _request(self, action, **fields):
        value = self.source.value
        packet = dict(action=action, checkpoint_id=value['checkpoint']['id'],
                      context_sha256=digest(value), **fields)
        reply = self.connection.request(packet)
        require(reply.get('ok') is True and all(reply.get(k) is v for k, v in FLAGS.items()) and
                reply.get('remote_durable_stage_verified') is False and
                reply.get('checkpoint_id') == packet['checkpoint_id'] and
                reply.get('context_sha256') == packet['context_sha256'] and
                hexid(reply.get('transaction'), 32), 'Delivery request was not confirmed')
        if self.transaction is not None:
            require(reply['transaction'] == self.transaction, 'Delivery transaction changed')
        return reply

    def run(self):
        with self.lock:
            return self._run()

    def _run(self):
        require(self.state == 'NEW', 'Delivery already attempted; no automatic replay')
        self.state = 'SENDING'
        try:
            parts = self._journal()
            reply = self._request('checkpoint_delivery_begin', request_id=secrets.token_hex(16))
            self.transaction = reply['transaction']
            for name, raw in sorted(parts.items()):
                for offset in range(0, len(raw), CHUNK):
                    chunk = dict(checkpoint_id=self.source.value['checkpoint']['id'], part=name,
                        index=offset // CHUNK, data=base64.b64encode(raw[offset:offset + CHUNK]).decode('ascii'))
                    self._request('checkpoint_delivery_chunk', transaction=self.transaction, chunk=chunk)
            require(self._journal() == parts, 'Durable bytes changed during return')
            reply = self._request('checkpoint_delivery_finish', transaction=self.transaction)
            require(reply.get('state') == 'RECEIVED' and reply.get('byte_roundtrip_verified') is True and
                    reply.get('returned_bytes') == reply.get('total_bytes') == sum(map(len, parts.values())),
                    'Incomplete delivery acknowledgement')
            self._journal()
            self.state = 'RECEIVED'
            return self.status()
        except BaseException as exc:
            self.state, self.error = 'HELD', type(exc).__name__
            self.source.hold('LOCAL_GUARD_LOST')
            raise

    def status(self):
        return dict(state=self.state, error=self.error,
            local_durable_stage_verified=self.state == 'RECEIVED',
            protocol_revocation_confirmed=self.source.revocation_confirmed,
            protocol_revocation_error=self.source.revocation_error, **FLAGS)
