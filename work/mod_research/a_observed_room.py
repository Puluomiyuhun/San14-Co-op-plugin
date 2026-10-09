"""Same-day Room completion under an explicit finite-observation contract.

Reuses the original receipt, projection, journal and native-result checks. It
does not enroll the strong held-fence protocol or turn samples into a fence.
"""
from copy import deepcopy
import threading

from authoritative_sync import scope_from_room, canonical
from a_room_bootstrap_protocol import BootstrapCoordinator, BootstrapRoom, BootstrapFreshSaveBinding
from b_warm_projection import TrustedProjection
from b_warm_remote_completion import ACTION as STRONG_ACTION, key_check, profile_from
from checkpoint_fresh_save_binding import _u64
import b_warm_world as world
import observed_completion_contract as contract

need = contract.need


class ObservedProjection(TrustedProjection):
    """Each check observes now; no continuously held state or release exists."""
    def __init__(self, coordinator, *, host_sampler, host_boundary, source_kind):
        need(type(coordinator) is BootstrapCoordinator and coordinator.state_contract == world.CONTRACT,
             'Exact same-day coordinator/partial contract required')
        need(source_kind in ('LOCAL_NATIVE_PROVIDER','FIXTURE_ONLY') and
             callable(host_sampler) and callable(host_boundary), 'Trusted finite observation providers required')
        self.coordinator = coordinator
        self.host_sampler, self.host_boundary = host_sampler, host_boundary
        self.source_kind = source_kind
        self.held_reason = None
        self._lock = threading.RLock()
        self.context = self.profile = self.kind = self.last_boundary = None

    def bind(self, context, profile, kind):
        self.context, self.profile, self.kind = deepcopy(context), profile, kind

    def _held(self):
        # Named to reuse frozen validation methods. The explicit class contract
        # changes this predicate to a fresh finite observation, never bool True.
        need(self.held_reason is None and self.context is not None, 'Observed projection unavailable')
        c, context = self.coordinator, self.context
        need(c.phase == 'RECONCILING' and c.scope == context['scope'] and c.manifest == context['manifest']
             and c.checkpoint_id == context['checkpoint_id'] and c.attachments == context['attachments']
             and c.connected == {'A','B'} and c.state_contract == world.CONTRACT
             and c.scope['profile']['game_sha256'] == world.objects.GAME_SHA256,
             'Observed authority context changed')
        local = self.host_boundary(self.profile, self.kind)
        observation = contract.boundary_envelope(local,context,self.profile,self.kind,side='A')
        contract.advances(self.last_boundary,observation)
        self.last_boundary = observation


class ObservedRoom(BootstrapRoom):
    def enroll_adapter(self, *args, **kwargs):
        raise ValueError('Strong held-fence enrollment is not this room contract')

    def enroll_observed_adapter(self, key, *, host_sampler, host_boundary, host_receipt_key, source_kind):
        with self.lock:
            key_check(key)
            need(self._remote is None and self._coordinator is not None and callable(host_receipt_key),
                 'One retained observed adapter and receipt provider required')
            self._remote = dict(key=key,helper=ObservedProjection(self._coordinator,
                host_sampler=host_sampler,host_boundary=host_boundary,source_kind=source_kind),
                host_key=host_receipt_key,connection=self.players['B']['connection'],rows={},held=None)
            self._observed_guest = None

    def handle(self, player, connection_id, request):
        if type(request) is dict and request.get('action') == STRONG_ACTION:
            return dict(ok=False,error='Strong boundary action rejected by observed room',native_gameplay_enabled=False)
        if type(request) is not dict or request.get('action') != contract.ACTION:
            return super().handle(player,connection_id,request)
        try:
            with self.lock:
                self._remote_current(player,connection_id)
                r = self._remote
                need(r is not None and r['connection'] == connection_id and r['held'] is None,
                     'No current observed adapter')
                body = contract.unpack(r['key'],request)
                with self._coordinator.lock:
                    if body.get('kind') == 'begin':
                        return self._begin(body)
                    need(body.get('kind') == 'complete','Unknown observed adapter operation')
                    return self._complete(body)
        except (ValueError,TypeError,KeyError,RuntimeError) as exc:
            return dict(ok=False,error=str(exc),boundary_contract=contract.CONTRACT,native_gameplay_enabled=False)

    def _begin(self, body):
        need(set(body) == {'kind','context','profile','guest_before','bootstrap','boundary'},
             'Exact observed begin fields required')
        r = self._remote
        context, p = body['context'], profile_from(body['profile'])
        guest = contract.validate_boundary(body['boundary'],context,p,'begin')
        contract.advances(self._observed_guest,guest)
        r['helper'].bind(context,p,'begin')
        legacy = {k:v for k,v in body.items() if k != 'boundary'}
        reply = super()._begin(legacy)
        row = r['rows'][context['checkpoint_id']]
        row['observed_begin'] = deepcopy(body)
        row['guest_boundary'] = guest
        self._observed_guest = guest
        return {**reply,'boundary_contract':contract.CONTRACT,
                'host_boundary':deepcopy(r['helper'].last_boundary),**contract.COVERAGE}

    def _complete(self, body):
        r, c = self._remote, self._coordinator
        need(set(body) == {'kind','checkpoint_id','intent','completion','sample','receipt','boundary'},
             'Exact observed completion fields required')
        need(body['checkpoint_id'] in r['rows'],'No observed once-only reservation')
        row = r['rows'][body['checkpoint_id']]
        if row.get('observed_complete') is not None:
            need(canonical(row['observed_complete']) == canonical(body),'Conflicting observed replay')
            return {**deepcopy(row['reply']),'duplicate':True}
        try:
            context, p = row['context'], profile_from(row['profile'])
            guest = contract.validate_boundary(body['boundary'],context,p,'complete',native=body['completion'])
            contract.advances(row['guest_boundary'],guest)
            contract.advances(self._observed_guest,guest)
            r['helper'].bind(context,p,'complete')
            legacy = {k:v for k,v in body.items() if k != 'boundary'}
            reply = super()._complete(legacy)
            reply = {**reply,'result':contract.RESULT,'boundary_contract':contract.CONTRACT,
                     'host_boundary':deepcopy(r['helper'].last_boundary),**contract.COVERAGE}
            row['observed_complete'], row['reply'] = deepcopy(body), deepcopy(reply)
            self._observed_guest = guest
            return reply
        except BaseException as exc:
            r['held'] = type(exc).__name__+': '+str(exc)
            self._held = 'OBSERVED_COMPLETION_UNCERTAIN'
            c.ready.clear()
            c.phase = 'HELD'
            raise


class ObservedFreshSaveBinding(BootstrapFreshSaveBinding):
    """Same byte/room validation, explicitly finite local observation semantics.

    safe_boundary denotes observed idle planning under the human condition;
    it does not stand for the predecessor's continuously held external fence.
    The caller supplies a genuine retained observer and current channel bytes.
    """
    def __init__(self, room, coordinator, *, native_room_id, native_room_epoch, artifact_reader, source_kind):
        need(type(room) is ObservedRoom and type(coordinator) is BootstrapCoordinator,
             'Exact observed room and bootstrap coordinator required')
        need(type(native_room_id) is bytes and len(native_room_id) == 32 and any(native_room_id),
             'Native nonzero room bytes32 required')
        need(_u64(native_room_epoch,nonzero=True) and callable(artifact_reader) and
             source_kind in ('FIXTURE_ONLY','LOCAL_NATIVE_PROVIDER'), 'Trusted observed export binding required')
        self.room,self.coordinator = room,coordinator
        self._native_room_id,self._native_room_epoch = native_room_id,native_room_epoch
        self._reader,self._source_kind = artifact_reader,source_kind
        self._held = self._publication_cleanup = None
        self._records = {}
        with room.lock,coordinator.lock:
            room._bound(coordinator)
            need(coordinator.phase == 'PLANNING' and coordinator.period == 1 and
                 coordinator.connected == {'A','B'}, 'Bind before initial bootstrap')
            self._scope = deepcopy(scope_from_room(room))
            need(self._scope == coordinator.scope,'Bound scope differs')
            self._host_attachment = coordinator.attachments['A']
            self._state_contract = coordinator.state_contract
