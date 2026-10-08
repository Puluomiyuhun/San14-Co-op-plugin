"""Pure reward-menu proposal capture; no native interception or execution.

The caller must be a trusted local adapter, not a TLS request handler. It owns
the menu lifetime/revision, fresh room/viewer observations and monotonic clock.
These inputs are contracts for that future adapter, not evidence it exists.
No return value authorizes skipping native code or reporting native success.
"""
from dataclasses import dataclass, field
import hashlib
import json
import re
import secrets
import threading
from types import MappingProxyType


CAPABILITIES = MappingProxyType(dict(
    schema='san14.reward-menu-capture.v1', semantic_capture=True,
    native_interception=False, native_cancellation=False,
    native_execution=False, network_submission=False, legality_verified=False))


class CaptureError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(ok, code):
    if not ok:
        raise CaptureError(code)


def _keys(value, fields):
    require(type(value) is dict and set(value) == set(fields), 'UNSUPPORTED_FIELDS')


def _integer(value, low, high, code='BAD_INTEGER'):
    require(type(value) is int and low <= value <= high, code)
    return value


def _hex(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{32}', value) is not None, 'BAD_ID')
    return value


def _preview(value):
    _keys(value, ('kind', 'force_id', 'district_id', 'funding_city_id', 'officer_ids'))
    require(value['kind'] == 'reward', 'NOT_REWARD')
    for key in ('force_id', 'district_id', 'funding_city_id'):
        _integer(value[key], 1, 51)
    ids = value['officer_ids']
    require(type(ids) is list and 1 <= len(ids) <= 16, 'BAD_OFFICER_LIST')
    for identity in ids:
        _integer(identity, 1, 5999, 'BAD_OFFICER_ID')
    require(len(set(ids)) == len(ids), 'DUPLICATE_OFFICER')
    return (value['force_id'], value['district_id'], value['funding_city_id'], tuple(ids))


_CONTEXT_FIELDS = ('room_id', 'binding_epoch', 'epoch', 'player_id',
                   'bound_force_id', 'main_district_id', 'viewer_force_id',
                   'attachment_id', 'menu_instance_id', 'world_revision',
                   'draft_revision', 'phase', 'observed_tick', 'expires_tick')
_IDENTITY_FIELDS = _CONTEXT_FIELDS[:-2]


def _context(value, now):
    _integer(now, 0, 2**63 - 1, 'BAD_CLOCK')
    _keys(value, _CONTEXT_FIELDS)
    for key in ('room_id', 'binding_epoch', 'epoch', 'attachment_id', 'menu_instance_id'):
        _hex(value[key])
    require(type(value['player_id']) is str and value['player_id'] in ('A', 'B'), 'BAD_PLAYER')
    for key in ('bound_force_id', 'main_district_id', 'viewer_force_id'):
        _integer(value[key], 1, 51)
    require(value['bound_force_id'] == value['viewer_force_id'], 'WRONG_VIEWER')
    require(value['phase'] == 'PLANNING', 'PLANNING_CLOSED')
    for key in ('world_revision', 'draft_revision', 'observed_tick', 'expires_tick'):
        _integer(value[key], 0, 2**63 - 1)
    require(value['observed_tick'] <= now < value['expires_tick'], 'STALE_CONTEXT')
    return tuple(value[key] for key in _IDENTITY_FIELDS)


@dataclass(frozen=True)
class PendingReward:
    """Immutable pending proposal; packet() is a defensive wire-shape copy.

    Creation is not enqueue/ack/execution. Repeated confirmations return this
    same request ID; a later network consumer must use server-side idempotency.
    funding_city_id is local evidence only: the authority derives it afresh.
    """
    room_id: str
    binding_epoch: str
    epoch: str
    player_id: str
    request_id: str
    district_id: int
    officer_ids: tuple
    preview_sha256: str
    native_interception: bool = field(default=False, init=False)
    native_execution: bool = field(default=False, init=False)
    legality_verified: bool = field(default=False, init=False)

    def packet(self):
        return dict(action='reward_submit', room_id=self.room_id,
                    binding_epoch=self.binding_epoch, epoch=self.epoch,
                    request_id=self.request_id, district_id=self.district_id,
                    officer_ids=list(self.officer_ids))


@dataclass
class _Draft:
    identity: tuple
    preview: tuple
    opened_tick: int
    expires_tick: int
    state: str = 'OPEN'
    proposal: PendingReward | None = None


class CaptureSession:
    """Bounded in-memory owner of menu lifetime tombstones, not a native lock.

    One menu instance can yield at most one request; changing a selection needs
    a new draft revision and a new capture after cancelling the old draft. The
    local adapter must supply a new menu_instance_id only for a real new native
    lifetime. Restarting this object does not prove old native work is absent.
    """
    def __init__(self, *, capacity=256):
        self._capacity = _integer(capacity, 1, 4096)
        self._drafts = {}
        self._menus = {}
        self._lock = threading.RLock()

    def capture(self, command_preview, trusted_context, *, capture_id, now_tick):
        capture_id = _hex(capture_id)
        identity = _context(trusted_context, now_tick)
        preview = _preview(command_preview)
        require(preview[0] == trusted_context['bound_force_id'], 'FOREIGN_FORCE')
        require(preview[1] == trusted_context['main_district_id'], 'FOREIGN_DISTRICT')
        with self._lock:
            require(capture_id not in self._drafts, 'CAPTURE_ID_REUSED')
            # A new capture ID cannot evade the one-menu/one-request tombstone.
            menu = (trusted_context['attachment_id'], trusted_context['menu_instance_id'])
            old_id = self._menus.get(menu)
            if old_id is not None:
                old = self._drafts[old_id]
                require(old.state == 'CANCELLED' and
                        trusted_context['draft_revision'] > old.identity[_IDENTITY_FIELDS.index('draft_revision')],
                        'MENU_ALREADY_CAPTURED')
            require(len(self._drafts) < self._capacity, 'CAPACITY_EXHAUSTED')
            self._drafts[capture_id] = _Draft(identity, preview, now_tick, trusted_context['expires_tick'])
            self._menus[menu] = capture_id
        return capture_id

    def _current(self, capture_id, trusted_context, now_tick):
        _hex(capture_id)
        identity = _context(trusted_context, now_tick)
        require(capture_id in self._drafts, 'UNKNOWN_CAPTURE')
        draft = self._drafts[capture_id]
        require(draft.state != 'INVALIDATED', 'INVALIDATED')
        if draft.identity != identity:
            draft.state = 'INVALIDATED'
            raise CaptureError('CONTEXT_CHANGED')
        if not draft.opened_tick <= trusted_context['observed_tick'] <= now_tick < draft.expires_tick:
            draft.state = 'INVALIDATED'
            raise CaptureError('STALE_DRAFT')
        return draft

    def confirm(self, capture_id, current_preview, trusted_context, *, now_tick):
        """Semantic confirm signal only; never inferred from ui_event_code_raw.

        The eventual native interception owner must supply this event after it
        proves submission was held before local effects. This API cannot do so.
        """
        preview = _preview(current_preview)
        with self._lock:
            draft = self._current(capture_id, trusted_context, now_tick)
            require(draft.state != 'CANCELLED', 'CANCELLED')
            if draft.preview != preview:
                draft.state = 'INVALIDATED'
                raise CaptureError('DRAFT_CHANGED')
            if draft.proposal is None:
                digest = hashlib.sha256(json.dumps(preview, separators=(',', ':')).encode()).hexdigest()
                draft.proposal = PendingReward(trusted_context['room_id'], trusted_context['binding_epoch'],
                    trusted_context['epoch'], trusted_context['player_id'], secrets.token_hex(16),
                    preview[1], preview[3], digest)
                draft.state = 'CONFIRMED'
            return draft.proposal

    def cancel(self, capture_id, trusted_context, *, now_tick):
        """Cancel a local pending draft, not a submitted/native command."""
        with self._lock:
            draft = self._current(capture_id, trusted_context, now_tick)
            require(draft.state != 'CONFIRMED', 'ALREADY_CONFIRMED')
            draft.state = 'CANCELLED'
        return 'CANCELLED'
