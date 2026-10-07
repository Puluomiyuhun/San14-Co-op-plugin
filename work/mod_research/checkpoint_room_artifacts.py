"""Room-bound, separate authenticated checkpoint download channel.

Trusted host code must install an already offered PeriodCoordinator package.
No network action publishes a file, creates load permission or enables gameplay.
Control connections remain online while short-lived artifact connections close.
"""
from copy import deepcopy
import hmac
from pathlib import Path
import secrets
import sys
import threading
import time

OUT = Path(__file__).resolve().parents[2]/'outputs'/'san14-link'
sys.path.insert(0, str(OUT))
from room_session import Room, RoomError
from authoritative_sync import (CheckpointPackage, CheckpointReceiver, PeriodCoordinator,
                                scope_from_room, digest, SyncError)


def require(ok, message):
    if not ok:
        raise RoomError(message)


class ArtifactEnabledRoom(Room):
    """One optional adapter endpoint; original room/native flags stay unchanged."""
    def __init__(self, manifest):
        super().__init__(manifest)
        self.artifacts = None

    def install_offered_checkpoint(self, coordinator, package):
        with self.lock:
            require(self.artifacts is None, 'This room adapter owns one checkpoint only')
            self.artifacts = CheckpointArtifactService(self, coordinator, package)
            return self.artifacts

    def handle(self, player, connection_id, request):
        if type(request) is not dict or request.get('action') != 'checkpoint_download_offer':
            return super().handle(player, connection_id, request)
        try:
            with self.lock:
                require(set(request) == {'action','checkpoint_id'}, 'Invalid checkpoint offer request')
                require(self.artifacts is not None, 'No host checkpoint has been installed')
                require(request['checkpoint_id'] == self.artifacts.checkpoint_id, 'Wrong checkpoint')
                return {'ok': True, **self.artifacts.issue_ticket(player, connection_id)}
        except (RoomError, SyncError) as exc:
            return {'ok': False, 'error': str(exc), 'applied_to_game': False}


class CheckpointArtifactService:
    def __init__(self, room, coordinator, package, *, lifetime=30, clock=time.monotonic):
        require(isinstance(room, Room) and type(coordinator) is PeriodCoordinator and
                type(package) is CheckpointPackage, 'Trusted room/coordinator/package required')
        require(type(lifetime) in (int,float) and 1 <= lifetime <= 60, 'Bounded ticket lifetime required')
        self.room = room
        self.coordinator = coordinator
        self.lock = threading.RLock()
        self.clock = clock
        self.lifetime = lifetime
        self.chunks = {}
        self.tickets = {}
        self.channels = {}
        self.ticket_count = 0
        self.closed = False
        # Capture the offered boundary and verify the immutable download copy
        # under the same lock order as issuance/authentication/chunk delivery.
        # The caller may construct directly, without install_offered_checkpoint.
        with room.lock, coordinator.lock:
            self.manifest = package.manifest
            self.checkpoint_id = package.checkpoint_id
            self.scope = scope_from_room(room)
            self.connections = {p: row['connection'] for p,row in room.players.items()}
            self._current()
            receiver = CheckpointReceiver(self.manifest, self.checkpoint_id, self.scope,
                self.manifest['epoch'], self.manifest['period'], self.manifest['cut'])
            for chunk in package.chunks():
                receiver.accept(chunk)
                self.chunks[(chunk['part'], chunk['index'])] = deepcopy(chunk)
            receiver.verified_parts()
            self._current()

    def _current(self):
        c = self.coordinator
        require(not self.closed and self.room.bindings is not None, 'Download endpoint is closed')
        require(scope_from_room(self.room) == self.scope and
            {p: row['connection'] for p,row in self.room.players.items()} == self.connections,
            'Control connection or faction binding changed; acquire a new adapter')
        require(c.scope == self.scope and c.phase == 'RECONCILING' and c.connected == {'A','B'} and
            c.epoch == self.manifest['epoch'] and c.period == self.manifest['period'] and
            c.checkpoint_id == self.checkpoint_id and c.manifest == self.manifest and
            digest(self.manifest) == self.checkpoint_id and c.load_intent is None,
            'Checkpoint is no longer at its download boundary')

    def issue_ticket(self, player, connection):
        with self.room.lock, self.coordinator.lock, self.lock:
            self._current()
            require(player == 'B' and connection == self.connections['B'], 'Only the current guest may download')
            # A bounded one-checkpoint object. No automatic ticket renewal or
            # room reconnect recovery; a production outer owner must replace it.
            require(self.ticket_count < 64, 'Checkpoint download ticket limit reached')
            now = self.clock()
            self.tickets = {t: row for t,row in self.tickets.items() if row['expires'] > now}
            # Expired sockets may remain connected and keep sending rejected
            # requests. Their authorization no longer consumes active capacity.
            # This neither renews old tickets nor resets the lifetime quota.
            self.channels = {c: row for c,row in self.channels.items() if row['expires'] > now}
            require(len(self.tickets)+len(self.channels) < 8, 'Too many active downloads')
            token = secrets.token_urlsafe(32)
            self.tickets[token] = {'expires': now+self.lifetime}
            self.ticket_count += 1
            return dict(manifest=deepcopy(self.manifest), checkpoint_id=self.checkpoint_id,
                download_token=token, expires_in_seconds=self.lifetime,
                control_connection_preserved=True, native_loaded=False, native_gameplay_enabled=False)

    def authenticate(self, request, connection):
        with self.room.lock, self.coordinator.lock, self.lock:
            self._current()
            require(type(request) is dict and set(request) == {'method','credential','profile'} and
                request['method'] == 'checkpoint_download' and request['profile'] == self.room.manifest['profile'],
                'Invalid artifact greeting')
            token = request['credential']
            require(type(token) is str and 1 <= len(token) <= 256 and token.isascii(),
                    'Invalid artifact credential')
            matched = next((t for t in self.tickets if hmac.compare_digest(t, token)), None)
            require(matched is not None, 'Unknown or consumed download ticket')
            row = self.tickets.pop(matched)  # Consumed even if already expired.
            require(row['expires'] > self.clock(), 'Download ticket expired')
            require(connection not in self.channels, 'Duplicate artifact connection')
            self.channels[connection] = row
            return dict(player_id='B', resume_token='', state=self._view())

    def _view(self):
        return dict(phase='CHECKPOINT_DOWNLOAD_ONLY', checkpoint_id=self.checkpoint_id,
                    native_gameplay_enabled=False, native_loaded=False,
                    control_connection_preserved=True)

    def handle(self, player, connection, request):
        try:
            with self.room.lock, self.coordinator.lock, self.lock:
                self._current()
                require(player == 'B' and connection in self.channels, 'No authenticated artifact connection')
                if self.channels[connection]['expires'] <= self.clock():
                    self.channels.pop(connection)
                    raise RoomError('Artifact lease expired')
                require(type(request) is dict and set(request) == {'action','checkpoint_id','part','index'} and
                    request['action'] == 'checkpoint_chunk' and request['checkpoint_id'] == self.checkpoint_id and
                    type(request['part']) is str and type(request['index']) is int,
                    'Invalid artifact request')
                key = (request['part'], request['index'])
                require(key in self.chunks, 'Unknown chunk')
                return {'ok': True, 'chunk': deepcopy(self.chunks[key])}
        except (RoomError, SyncError) as exc:
            return {'ok': False, 'error': str(exc), 'applied_to_game': False}

    def disconnect(self, player, connection):
        with self.lock:
            self.channels.pop(connection, None)
        # Deliberately no room.disconnect: this is a separate artifact channel.

    def close(self):
        with self.lock:
            self.closed = True
            self.tickets.clear()
            self.channels.clear()

    def status(self):
        with self.lock:
            return dict(checkpoint_id=self.checkpoint_id, issued_tickets=self.ticket_count,
                active_downloads=len(self.channels), closed=self.closed,
                native_gameplay_enabled=False, native_loaded=False)
