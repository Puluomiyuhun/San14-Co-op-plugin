"""Research-only map-cover lifecycle around the durable checkpoint protocol.

This module neither captures/draws a frame nor intercepts native input. Trusted
renderer/adapter observations must establish those facts. It never enables room
gameplay. A received file or constructed menu is insufficient to reveal the map.
"""
from copy import deepcopy
import secrets
import threading

from authoritative_sync import PeriodCoordinator, canonical, hexid, require
from checkpoint_journal import CheckpointJournal


class MapWaitGate:
    """One immutable checkpoint presentation, no automatic load or retry.

    Sequence: cover_presented -> reserve_load -> native adapter completes its
    journal -> world_restored -> map_frame_presented -> begin_reveal -> revealed.
    The coordinator remains RECONCILING until begin_reveal. Both the renderer
    and input adapter must honor this gate in the future production integration.
    """
    def __init__(self, coordinator, journal):
        require(type(coordinator) is PeriodCoordinator and type(journal) is CheckpointJournal,
                'Trusted coordinator and durable journal required')
        self.lock = threading.RLock()
        self.coordinator = coordinator
        self.journal = journal
        self.identity = journal.identity
        self.nonce = secrets.token_hex(16)
        self.phase = 'WAITING_FOR_COVER'
        self.cover = None
        self.new_attachment = None
        self.new_frame = None
        self.reveal_token = None
        self.release_epoch = None
        self.hold_reason = None
        self.load_reserved = False
        with coordinator.lock:
            self._boundary()

    def _boundary(self):
        c = self.coordinator; i = self.identity
        require(c.phase == 'RECONCILING' and c.manifest == i['manifest'] and
                c.checkpoint_id == i['checkpoint_id'] and
                c.attachments == i['attachments'] and
                canonical(c.scope) == canonical(i['scope']), 'Changed checkpoint boundary')

    def _envelope(self, observation):
        require(type(observation) is dict and observation.get('presentation') == self.nonce and
                observation.get('checkpoint_id') == self.identity['checkpoint_id'],
                'Stale/foreign renderer observation')

    def cover_presented(self, observation):
        """A retained old-map frame must ALREADY cover the game surface.

        This is a trusted renderer report, never a permission requested from a
        remote peer. Surface usability must be checked by the real renderer;
        this protocol does not certify exclusive fullscreen overlay visibility.
        """
        with self.lock, self.coordinator.lock:
            require(self.phase == 'WAITING_FOR_COVER', 'Cover out of order')
            self._boundary(); self._envelope(observation)
            require(set(observation) == {'presentation', 'checkpoint_id', 'attachment',
                    'frame', 'view', 'surface', 'window_mode', 'visible', 'input_blocked'}, 'Bad cover report')
            require(observation['attachment'] == self.identity['attachments']['B'] and
                    all(hexid(observation[k], 32) for k in ('frame', 'view', 'surface')) and
                    observation['window_mode'] in ('windowed', 'borderless') and
                    observation['visible'] is True and observation['input_blocked'] is True,
                    'Map cover/input protection not confirmed')
            self.cover = deepcopy(observation)
            self.phase = 'COVERED'

    def reserve_load(self, host_observation, guest_observation):
        """Return one durable native permission only after cover confirmation."""
        with self.lock, self.coordinator.lock:
            require(self.phase == 'COVERED' and not self.load_reserved, 'No covered load boundary')
            self._boundary()
            try:
                intent = self.coordinator.begin_guest_load('B', self.identity['manifest']['epoch'])
                permit = self.journal.reserve_load(intent, host_observation, guest_observation)
            except BaseException:
                self.phase = 'HELD'; self.hold_reason = 'LOAD_RESERVATION_UNCERTAIN'
                raise
            self.load_reserved = True
            self.phase = 'LOADING'
            return permit

    def _fresh_world(self, host, guest):
        args = self.journal.coordinator_arguments()
        m = self.identity['manifest']
        expected_host = {'attachment': self.identity['attachments']['A'],
                         'world_sha256': m['world_sha256'], 'node': m['node']}
        expected_guest = {'attachment': args['new_attachment'], 'viewer_force': args['viewer_force'],
                          'world_sha256': m['world_sha256'], 'node': m['node'], 'safe_boundary': True}
        require(canonical(host) == canonical(expected_host) and
                canonical(guest) == canonical(expected_guest), 'Current world differs from receipt')
        return args

    def world_restored(self, host_observation, guest_observation):
        """Record a complete durable receipt, but do not release either player."""
        with self.lock, self.coordinator.lock:
            require(self.phase == 'LOADING', 'World observation out of order')
            self._boundary()
            args = self._fresh_world(host_observation, guest_observation)
            self.new_attachment = args['new_attachment']
            self.phase = 'WAITING_FOR_MAP_FRAME'

    def map_frame_presented(self, observation):
        """Require a newly rendered B map with its saved local view restored."""
        with self.lock, self.coordinator.lock:
            require(self.phase == 'WAITING_FOR_MAP_FRAME', 'Map frame out of order')
            self._boundary(); self._envelope(observation)
            require(set(observation) == {'presentation', 'checkpoint_id', 'attachment',
                    'frame', 'view', 'surface', 'viewer_force', 'kind', 'cover_visible',
                    'window_mode', 'input_blocked'}, 'Bad new-map frame report')
            require(observation['attachment'] == self.new_attachment and
                    hexid(observation['frame'], 32) and observation['frame'] != self.cover['frame'] and
                    observation['view'] == self.cover['view'] and
                    observation['surface'] == self.cover['surface'] and
                    observation['window_mode'] == self.cover['window_mode'] and
                    type(observation['viewer_force']) is int and
                    observation['viewer_force'] == self.identity['scope']['bindings']['B']['force_id'] and
                    observation['kind'] == 'NATIVE_PLANNING_MAP' and
                    observation['cover_visible'] is True and observation['input_blocked'] is True,
                    'B map, restored view or cover is not ready')
            self.new_frame = deepcopy(observation)
            self.phase = 'READY_TO_REVEAL'

    def begin_reveal(self, host_observation, guest_observation):
        """Recheck both games, advance the coordinator, then authorize uncovering.

        Input remains gated until revealed(). No native frame is fabricated by
        this operation, and a renderer failure must call hold().
        """
        with self.lock, self.coordinator.lock:
            require(self.phase == 'READY_TO_REVEAL', 'No verified new map frame')
            self._boundary()
            args = self._fresh_world(host_observation, guest_observation)
            require(args['new_attachment'] == self.new_attachment, 'Restored game changed')
            try:
                result = self.journal.apply_to_coordinator(self.coordinator, host_observation,
                                                           guest_observation)
            except BaseException:
                self.phase = 'HELD'; self.hold_reason = 'RELEASE_NOT_CONFIRMED'
                raise
            self.release_epoch = result['epoch']
            self.reveal_token = secrets.token_hex(16)
            self.phase = 'REVEALING'
            return {'presentation': self.nonce, 'checkpoint_id': self.identity['checkpoint_id'],
                    'token': self.reveal_token, 'attachment': self.new_attachment}

    def revealed(self, observation):
        with self.lock, self.coordinator.lock:
            require(self.phase == 'REVEALING', 'Reveal acknowledgement out of order')
            self._envelope(observation)
            require(set(observation) == {'presentation', 'checkpoint_id', 'token', 'attachment'} and
                    observation['token'] == self.reveal_token and
                    observation['attachment'] == self.new_attachment, 'Stale reveal acknowledgement')
            c = self.coordinator
            require(c.phase == 'PLANNING' and c.epoch == self.release_epoch and
                    c.attachments['B'] == self.new_attachment and c.connected == {'A', 'B'},
                    'Room changed while revealing')
            self.phase = 'LIVE'

    def hold(self, reason):
        with self.lock:
            require(type(reason) is str and 1 <= len(reason) <= 80, 'Invalid hold reason')
            self.phase = 'HELD'; self.hold_reason = reason

    def status(self):
        with self.lock, self.coordinator.lock:
            c = self.coordinator
            live = (self.phase == 'LIVE' and c.phase == 'PLANNING' and
                    c.epoch == self.release_epoch and c.attachments['B'] == self.new_attachment and
                    c.connected == {'A', 'B'})
            return {'phase': self.phase, 'presentation': self.nonce,
                    'checkpoint_id': self.identity['checkpoint_id'],
                    'accept_planning_intents': live,
                    'request_map_cover': not live,
                    'message': '' if live else '同步暂停，请等待恢复' if self.phase == 'HELD' else '正在同步本旬结果…',
                    'diagnostic_hold_reason': self.hold_reason,
                    'native_load_reserved': self.load_reserved,
                    'supported_window_modes': ['windowed', 'borderless'],
                    'native_input_interception_implemented': False,
                    'native_visual_cover_implemented': False,
                    'native_gameplay_enabled': False}
