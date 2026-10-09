"""Trusted local adapter for exactly one declared partial-world contract.

This is not a network endpoint. Callbacks are retained local sampler/native
owners. verify_held must inspect the caller's real execution/input boundary;
constructing this object, a sample dictionary or a receipt is not that evidence.
Native execution and full-world/Ready authority remain separate.
"""
import base64
from copy import deepcopy
import hashlib
import threading
from authoritative_sync import PeriodCoordinator, CheckpointReceiver, CHUNK, digest, hexid, next_node
from checkpoint_journal import CheckpointJournal
from checkpoint_fresh_save_binding import LocalWorldObservation
from b_warm_profile_contract import Profile, validate_profile
import b_warm_world as world


def need(ok, reason):
    if not ok: raise ValueError(reason)


def receiver_from_journal(journal):
    """Recheck durable received bytes; no dependency on A's package instance."""
    need(type(journal) is CheckpointJournal, 'Actual local journal required')
    i=journal.identity;m=i['manifest']
    receiver=CheckpointReceiver(m,i['checkpoint_id'],i['scope'],m['epoch'],m['period'],m['cut'])
    for name,data in journal.verified_parts().items():
        for offset in range(0,len(data),CHUNK):
            receiver.accept(dict(checkpoint_id=i['checkpoint_id'],part=name,index=offset//CHUNK,
                                 data=base64.b64encode(data[offset:offset+CHUNK]).decode('ascii')))
    need(receiver.verified_parts()==journal.verified_parts(), 'Staged bytes changed during reconstruction')
    return receiver


def host_observation(coordinator, *, reader, read_birth, verify_held, source_ruler):
    """Read A's declared projection before/after Save, without knowing file bytes.

    This uses the actual table sampler and current native reader, not a fake
    future file Profile. The trusted caller supplies independent input/worker
    exclusion; repeated reads alone do not prove that boundary is held.
    """
    c=coordinator
    need(type(c) is PeriodCoordinator and c.state_contract==world.CONTRACT, 'Exact declared partial contract required')
    need(callable(read_birth) and callable(verify_held) and verify_held() is True, 'Native boundary is not held')
    with c.lock:
        need(c.phase=='RUNNING' and c.connected=={'A','B'}, 'Settled running authority required')
        context=deepcopy((c.scope,c.epoch,c.period,next_node(c.node),c.attachments))
    scope,epoch,period,node,attachments=context
    need(scope['profile']['game_sha256']==world.objects.GAME_SHA256, 'Room build differs')
    world.integer(source_ruler,high=6000)
    force=scope['bindings']['A']['force_id']
    expected=(node['year'],node['month'],node['day'],force,source_ruler)
    reads=world.Reads(reader.memory.read)
    before=world.context(reader,reads,read_birth,expected)
    payload=world.payload_pass(reader,reads,before['root'])
    middle=world.context(reader,reads,read_birth,expected)
    again=world.payload_pass(reader,reads,before['root'])
    after=world.context(reader,reads,read_birth,expected)
    need(before==middle==after and payload==again, 'Observed A projection changed')
    need(verify_held() is True, 'Native boundary was released')
    with c.lock:
        need(c.phase=='RUNNING' and c.connected=={'A','B'} and c.state_contract==world.CONTRACT and
             (c.scope,c.epoch,c.period,next_node(c.node),c.attachments)==context, 'A protocol context changed')
    return LocalWorldObservation(attachments['A'],node['year'],node['month'],node['day'],force,source_ruler,
                                 world.CONTRACT,digest(world.shared(node,payload)),True)


class TrustedProjection:
    def __init__(self, coordinator, *, host_sampler, guest_sampler, verify_held,
                 guest_before, native_load, source_kind):
        need(type(coordinator) is PeriodCoordinator and coordinator.state_contract == world.CONTRACT,
             'Explicit exact partial state_contract required')
        need(source_kind in ('LOCAL_NATIVE_PROVIDER', 'FIXTURE_ONLY'), 'Explicit local provenance required')
        need(all(callable(f) for f in (host_sampler, guest_sampler, verify_held, guest_before, native_load)),
             'Trusted local callbacks required; no received JSON permits')
        self.coordinator = coordinator
        self.host_sampler, self.guest_sampler = host_sampler, guest_sampler
        self.verify_held, self.guest_before, self.native_load = verify_held, guest_before, native_load
        self.source_kind = source_kind
        self.held_reason = None
        self._lock = threading.RLock()

    def _held(self):
        need(self.held_reason is None, 'Adapter is terminally held: '+str(self.held_reason))
        need(self.coordinator.state_contract == world.CONTRACT and
             self.coordinator.scope['profile']['game_sha256']==world.objects.GAME_SHA256, 'Partial contract/build changed')
        need(self.verify_held() is True, 'Native execution/input boundary is not held')

    def _sample(self, side, profile, receipt_key, context, native=None):
        self._held()
        need(type(profile) is Profile, 'Typed immutable profile required')
        validate_profile(profile)
        value = deepcopy((self.host_sampler if side == 'A' else self.guest_sampler)(profile, receipt_key))
        world.validate_sample(value)
        b = value['binding']; viewer = profile.source if side == 'A' else profile.target
        need({k:b[k] for k in ('scope_sha256','epoch','period','profile_sha256','side','receipt_key','viewer_force','viewer_ruler')} ==
             dict(scope_sha256=digest(context['scope']), epoch=context['epoch'], period=context['period'],
                  profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(), side=side, receipt_key=receipt_key,
                  viewer_force=viewer.force, viewer_ruler=viewer.ruler), 'Projection observation belongs to another context')
        need(context['scope']['bindings'][side] == dict(force_id=viewer.force, main_district_id=viewer.district),
             'Projection changes room faction')
        need(value['shared']['date'] == context['node'], 'Projection date differs')
        if native is not None:
            need((b['pid'],b['birth']) == (native['pid'],native['birth']), 'Projection belongs to another native process')
        self._held()
        return value

    def _completion(self, answer, profile, manifest):
        need(type(answer) is dict, 'Only retained native loader output accepted')
        accepted=answer['accepted']
        need(answer['profile_sha256'] == hashlib.sha256(bytes(profile)).hexdigest() and
             answer['slots_restored'] is True and accepted['result']=='PASS_WARM_LOAD_RETIRED' and
             hexid(accepted['receipt_key']) and int(accepted['receipt_key'],16), 'Native load/profile retirement differs')
        need(all(accepted.get(k) is False for k in ('ready_authorized','full_world_verified','input_exclusion_proven')),
             'Unexpected native authority claim')
        need((accepted['source_force'],accepted['source_ruler'],accepted['target_force'],accepted['target_ruler']) ==
             (profile.source.force,profile.source.ruler,profile.target.force,profile.target.ruler), 'Native completion faction differs')
        for name,maximum in (('pid',2**32),('birth',2**64),('attempt',2**64)):
            need(type(answer[name]) is int and 0<answer[name]<maximum, 'Native identity field invalid')
        s=answer['snapshot'];n=manifest['node']
        need(tuple(s['date'][k] for k in ('year','month','day')) == (n['year'],n['month'],n['day']) and
             (s['player']['force_id'],s['player']['ruler_id']) == (profile.target.force,profile.target.ruler),
             'Native completion date/viewer differs')
        return answer

    def apply(self, journal, receiver, profile, *, host_receipt_key):
        """Reserve the real journal once, load once, then apply real loaded().

        native_load(permit) may call ReceivedApply.apply(...,reservation=permit)
        and return its actual completion. It must not accept a remote ACK as a
        substitute. A failure retains INTENT and never reissues native work.
        """
        with self._lock:
            self._held()
            try:
                need(type(journal) is CheckpointJournal and type(receiver) is CheckpointReceiver,
                     'Actual staged journal and verified receiver required')
                need(type(profile) is Profile, 'Typed profile required');validate_profile(profile)
                c=self.coordinator;identity=journal.identity;m=identity['manifest']
                need(m['state_contract']==world.CONTRACT, 'Offered checkpoint has a different contract')
                need((profile.file.size,bytes(profile.file.sha256).hex()) ==
                     (m['parts']['world.s14']['size'],m['parts']['world.s14']['sha256']), 'Profile differs from checkpoint bytes')
                with c.lock:
                    need(c.phase=='RECONCILING' and c.scope==identity['scope'] and c.manifest==m and
                         c.checkpoint_id==identity['checkpoint_id'] and c.attachments==identity['attachments'] and
                         c.period==m['period'] and c.epoch==m['epoch'], 'Coordinator/journal lineage differs')
                    need((profile.before.year,profile.before.month,profile.before.day)==tuple(c.node[k] for k in ('year','month','day')) and
                         (profile.loaded.year,profile.loaded.month,profile.loaded.day)==tuple(m['node'][k] for k in ('year','month','day')),
                         'Profile dates differ from the offered period')
                    context=dict(scope=deepcopy(c.scope),epoch=c.epoch,period=c.period,node=deepcopy(m['node']))
                need(journal.verified_parts()==receiver.verified_parts(), 'Verified byte stores differ')
                a=self._sample('A',profile,host_receipt_key,context)
                need(a['partial_sha256']==m['world_sha256'], 'A changed its declared projection')
                host=dict(attachment=identity['attachments']['A'],world_sha256=a['partial_sha256'],node=m['node'])
                guest=self.guest_before()
                need(guest==dict(attachment=identity['attachments']['B'],viewer_force=profile.target.force,safe_boundary=True),
                     'Trusted pre-load B boundary differs')
                self._held()
                c.received('B',m['epoch'],receiver)
                intent=c.begin_guest_load('B',m['epoch'])
                permit=journal.reserve_load(intent,host,guest)
                self._held()
                answer=self._completion(self.native_load(permit),profile,m)
                self._held()
                b=self._sample('B',profile,answer['accepted']['receipt_key'],context,answer)
                again=self._sample('A',profile,host_receipt_key,context)
                comparison=world.compare(again,b)
                need(a['shared']==again['shared'] and comparison['result']=='PARTIAL_MATCH' and
                     b['partial_sha256']==m['world_sha256'], 'Loaded declared projection differs')
                # New attachment is a local protocol lifetime, derived from this
                # exact journal intent and independently accepted native result.
                new_attachment=digest(dict(checkpoint=identity['checkpoint_id'],intent=intent,
                    pid=answer['pid'],birth=answer['birth'],attempt=answer['attempt'],
                    receipt_key=answer['accepted']['receipt_key']))[:32]
                receipt=dict(player='B',epoch=m['epoch'],checkpoint_id=identity['checkpoint_id'],intent=intent,
                    world_sha256=b['partial_sha256'],viewer_force=profile.target.force,attachment=new_attachment,
                    host_observation=host)
                self._held();journal.complete(receipt)
                current_host=self._sample('A',profile,host_receipt_key,context)
                current_guest=self._sample('B',profile,answer['accepted']['receipt_key'],context,answer)
                need(current_host['shared']==again['shared'] and current_guest['shared']==b['shared'],
                     'Projection changed before receipt application')
                self._held()
                progress=journal.apply_to_coordinator(c,host,dict(attachment=new_attachment,
                    viewer_force=profile.target.force,world_sha256=b['partial_sha256'],node=m['node'],safe_boundary=True))
                return dict(result='DECLARED_PROJECTION_LOADED',contract=world.CONTRACT,partial_sha256=b['partial_sha256'],
                    protocol_progress=progress,comparison=comparison,source_kind=self.source_kind,
                    native_gameplay_enabled=False,full_world_verified=False,native_full_world_coverage_verified=False,
                    ready_authorized=False,fence_released=False)
            except BaseException as exc:
                self.held_reason=type(exc).__name__+': '+str(exc)
                raise
