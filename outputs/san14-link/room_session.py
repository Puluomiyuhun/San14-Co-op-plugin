"""Two-player room identity and faction binding. No SAN14 execution adapter.

Room selection is a protocol choice, not an actual game-player switch. Loaded
state, UI identity, AI hooks and world replication must pass a future native
barrier; this module deliberately has no start-game transition.
"""
from copy import deepcopy
import hashlib
import hmac
import json
import re
import secrets
import threading

PROTOCOL = 'san14.room.v1'


class RoomError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise RoomError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class Room:
    def __init__(self, manifest):
        require(type(manifest) is dict and set(manifest) == {'profile', 'forces', 'source'}, 'Bad manifest')
        profile = manifest['profile']
        require(type(profile) is dict and set(profile) == {'protocol', 'game_sha256', 'adapter_contract', 'checkpoint_sha256', 'rules_sha256'}, 'Bad compatibility profile')
        require(profile['protocol'] == PROTOCOL and profile['adapter_contract'] == 'research-no-native-room-adapter.v1', 'Unsupported protocol/adapter')
        for name in ('game_sha256', 'checkpoint_sha256', 'rules_sha256'):
            require(type(profile[name]) is str and re.fullmatch('[0-9a-f]{64}', profile[name]) is not None, 'Bad profile hash')
        require(type(manifest['forces']) is list and 2 <= len(manifest['forces']) <= 51, 'Bad force catalog')
        self.catalog = {}
        districts = set()
        for f in manifest['forces']:
            require(type(f) is dict and set(f) == {'id', 'name', 'main_district_id'}, 'Bad force entry')
            require(type(f['id']) is int and 1 <= f['id'] <= 51 and f['id'] not in self.catalog, 'Duplicate/invalid force')
            require(type(f['main_district_id']) is int and 1 <= f['main_district_id'] <= 51 and f['main_district_id'] not in districts, 'Duplicate/invalid main district')
            require(type(f['name']) is str and 1 <= len(f['name']) <= 80, 'Bad force label')
            self.catalog[f['id']] = deepcopy(f)
            districts.add(f['main_district_id'])
        self.manifest = deepcopy(manifest)
        self.room_id = secrets.token_hex(16)
        self.invite = secrets.token_urlsafe(32)
        self.host_token = secrets.token_urlsafe(32)
        self.players = {'A': {'token': self.host_token, 'connection': None, 'force': None, 'confirmed': False}}
        self.revision = 0
        self.binding_epoch = None
        self.bindings = None
        self.receipts = {}
        self.lock = threading.RLock()

    def authenticate(self, request, connection_id):
        with self.lock:
            require(type(request) is dict and set(request) == {'method', 'credential', 'profile'}, 'Bad greeting')
            require(request['profile'] == self.manifest['profile'], 'Game, adapter, rules or checkpoint mismatch')
            secret = request['credential']
            require(type(secret) is str and len(secret) <= 256, 'Bad credential')
            method = request['method']
            if method == 'join':
                require(hmac.compare_digest(secret, self.invite), 'Invalid invitation')
                require('B' not in self.players and self.bindings is None, 'Guest seat already reserved')
                token = secrets.token_urlsafe(32)
                self.players['B'] = {'token': token, 'connection': None, 'force': None, 'confirmed': False}
                player = 'B'
            elif method in ('host', 'resume'):
                matches = [p for p, row in self.players.items() if hmac.compare_digest(row['token'], secret)]
                require(len(matches) == 1 and (method != 'host' or matches[0] == 'A'), 'Invalid player credential')
                player = matches[0]
                token = self.players[player]['token']
            else:
                raise RoomError('Unknown greeting')
            require(self.players[player]['connection'] is None, 'Player already connected')
            self.players[player]['connection'] = connection_id
            self.revision += 1
            return {'player_id': player, 'resume_token': token, 'state': self.view(player)}

    def disconnect(self, player, connection_id):
        with self.lock:
            row = self.players.get(player)
            if row is None or row['connection'] != connection_id:
                return
            row['connection'] = None
            if self.bindings is None:
                for p in self.players.values():
                    p['confirmed'] = False
            self.revision += 1

    def view(self, player):
        offline = sorted(p for p, row in self.players.items() if row['connection'] is None)
        state = 'CHOOSING_FORCES' if self.bindings is None else 'WAITING_NATIVE_ADAPTER'
        if self.bindings is not None and offline:
            state = 'BOUND_PEER_OFFLINE'
        return {'room_id': self.room_id, 'revision': self.revision, 'phase': state,
                'you': player, 'your_force': self.players[player]['force'],
                'players': {p: {'force_id': row['force'], 'connected': row['connection'] is not None,
                                'confirmed': row['confirmed']} for p, row in self.players.items()},
                'forces': deepcopy(list(self.catalog.values())), 'manifest_source': self.manifest['source'],
                'binding_epoch': self.binding_epoch, 'bindings': deepcopy(self.bindings),
                'native_gameplay_enabled': False, 'client_viewer_switched': False,
                'world_synchronized': False, 'host_restart_recovery': False}

    def binding_for_command(self, player, envelope):
        """Server-derived authority only; not a legal-command or execution receipt."""
        require(self.bindings is not None, 'Faction selection is not locked')
        require(len(self.players) == 2 and all(r['connection'] is not None for r in self.players.values()), 'Peer offline; commands paused')
        require(type(envelope) is dict and set(envelope) == {'room_id', 'binding_epoch', 'command'}, 'Bad command envelope')
        require(envelope['room_id'] == self.room_id and envelope['binding_epoch'] == self.binding_epoch, 'Stale room or faction binding')
        command = envelope['command']
        require(type(command) is dict and command.get('schema') == 'san14.authority-reward-command.v1', 'Only reward authority routing is connected')
        force = self.bindings[player]['force_id']
        require(type(command.get('force_id')) is int and command['force_id'] == force, 'Command belongs to another player')
        require(command.get('game_sha256') == self.manifest['profile']['game_sha256'], 'Command build mismatch')
        return {'room_id': self.room_id, 'binding_epoch': self.binding_epoch, 'player_id': player,
                'authorized_force_id': force, 'main_district_id': self.bindings[player]['main_district_id'],
                'status': 'BINDING_CHECK_ONLY', 'command_legality_checked': False,
                'applied_to_game': False, 'state_replicated': False}

    def native_control_config(self):
        """Trusted-server export for the future AI adapter; never a client setter."""
        require(self.bindings is not None, 'No locked bindings')
        return {'room_id': self.room_id, 'binding_epoch': self.binding_epoch,
                'human_force_mask': sum(1 << row['force_id'] for row in self.bindings.values()),
                'main_districts': {str(row['force_id']): row['main_district_id'] for row in self.bindings.values()},
                'preserve_delegated_district_ai': True, 'installed_in_game': False}

    def event_recipient(self, owner_force):
        require(self.bindings is not None, 'No locked bindings')
        require(type(owner_force) is int, 'Invalid event owner')
        return next((p for p, row in self.bindings.items() if row['force_id'] == owner_force), None)

    def handle(self, player, connection_id, request):
        with self.lock:
            try:
                require(player in self.players and self.players[player]['connection'] == connection_id, 'Connection is no longer authenticated')
                require(type(request) is dict, 'Bad request')
                if request == {'action': 'status'}:
                    return {'ok': True, 'state': self.view(player)}
                require(type(request.get('request_id')) is str and re.fullmatch('[0-9a-f]{32}', request['request_id']) is not None, 'Bad request ID')
                key = (player, request['request_id'])
                fingerprint = digest(request)
                if key in self.receipts:
                    previous, receipt = self.receipts[key]
                    require(previous == fingerprint, 'Request ID reused with different content')
                    return {'ok': True, 'duplicate': True, 'receipt': deepcopy(receipt), 'state': self.view(player)}
                require(len(self.receipts) < 4096, 'Room request capacity reached')
                action = request.get('action')
                if action in ('select_force', 'confirm_force'):
                    fields = {'action', 'request_id', 'expected_revision'} | ({'force_id'} if action == 'select_force' else set())
                    require(set(request) == fields, 'Unexpected selection fields')
                    require(self.bindings is None, 'Faction binding is locked for this match')
                    require(type(request['expected_revision']) is int and request['expected_revision'] == self.revision, 'Stale room view; refresh selection')
                    row = self.players[player]
                    if action == 'select_force':
                        force = request['force_id']
                        require(type(force) is int and force in self.catalog, 'Unavailable faction')
                        require(all(p == player or r['force'] != force for p, r in self.players.items()), 'Faction already selected')
                        row['force'] = force
                        for r in self.players.values():
                            r['confirmed'] = False
                    else:
                        require(len(self.players) == 2 and all(r['connection'] is not None for r in self.players.values()), 'Both players must be connected')
                        require(row['force'] is not None, 'Select a faction first')
                        row['confirmed'] = True
                        if all(r['confirmed'] for r in self.players.values()):
                            require(len({r['force'] for r in self.players.values()}) == 2, 'Two different factions required')
                            self.binding_epoch = secrets.token_hex(16)
                            self.bindings = {p: {'force_id': r['force'], 'main_district_id': self.catalog[r['force']]['main_district_id']} for p, r in self.players.items()}
                    self.revision += 1
                    receipt = {'status': 'FACTION_SELECTION_UPDATED', 'revision': self.revision,
                               'binding_epoch': self.binding_epoch, 'game_started': False}
                elif action == 'route_preview':
                    require(set(request) == {'action', 'request_id', 'envelope'}, 'Unexpected route fields')
                    receipt = self.binding_for_command(player, request['envelope'])
                else:
                    raise RoomError('Unsupported action; no native game start or execution adapter installed')
                self.receipts[key] = (fingerprint, deepcopy(receipt))
                return {'ok': True, 'duplicate': False, 'receipt': receipt, 'state': self.view(player)}
            except (RoomError, TypeError) as e:
                return {'ok': False, 'error': str(e), 'applied_to_game': False}
