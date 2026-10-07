"""Production composition of NativePort and the existing bound SessionChannel.

This module has no native input/world/bootstrap implementation. Those explicitly
trusted dependencies are mandatory; default construction rejects. A real channel
identity flag is never promoted to COMPLETE. No paths/pointers travel over IPC.
"""
from copy import deepcopy
from dataclasses import dataclass, asdict
import hashlib
import secrets
import threading
import time

from checkpoint_guest_transition import (Context, InputHold, WorldObservation,
                                        LoadProgress, InputRelease)
from checkpoint_session_channel import SessionChannel, SessionStatus
from checkpoint_visual_client import TargetBinding, VisualError, require, hexid
from checkpoint_presentation import MapWaitGate
from authoritative_sync import canonical, digest

PRODUCTION='ROOT_TRUSTED_NATIVE_ADAPTER'
FIXTURE='FIXTURE_ONLY'


@dataclass(frozen=True)
class SessionProfile:
    """Launcher-approved configuration, not discovered or self-approved here."""
    provenance: str
    profile_id: str
    game_build_sha256: str
    session_binary_sha256: str
    native_contract_sha256: str
    state_contract: str
    target_basename: str
    world_size: int
    world_file_sha256: str
    node_sha256: str
    viewer_force: int

    @property
    def sha256(self):
        return digest(asdict(self))

    def validate(self):
        require(self.provenance in (PRODUCTION,FIXTURE), 'Untrusted profile realm')
        require(self.profile_id == 'san14.cc63-native-session.v1', 'Unsupported native session profile')
        require(all(hexid(v,64) for v in (self.game_build_sha256,self.session_binary_sha256,
                    self.native_contract_sha256,self.world_file_sha256,self.node_sha256)), 'Invalid profile hashes')
        require(type(self.state_contract) is str and self.state_contract and
                self.target_basename == 'svdexccSC03.s14' and type(self.world_size) is int and
                self.world_size > 0 and type(self.viewer_force) is int and self.viewer_force == 2,
                'Unsupported slot/faction/profile shape')
        if self.provenance == PRODUCTION:
            # Frozen Session cores currently support this one researched file.
            # A new checkpoint/build requires a separately reviewed profile.
            require(self.world_size == 274880 and self.world_file_sha256 ==
                    '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c' and
                    self.node_sha256 == digest({'year':203,'month':8,'day':11,'phase':'PLANNING_BOUNDARY'}),
                    'Frozen native profile does not support these checkpoint bytes/date')


@dataclass(frozen=True)
class Binding:
    context: Context
    target: TargetBinding
    profile_sha256: str
    manifest_sha256: str
    epoch: str
    old_host: str
    old_guest: str
    viewer_force: int
    semantic_world_sha256: str
    world_file_sha256: str
    adapter_file_sha256: str
    lease: str | None
    intent: str | None
    new_attachment: str | None


@dataclass(frozen=True)
class EvidenceRequest:
    binding: Binding
    purpose: str
    challenge: str
    requested_monotonic_ns: int
    current_room_epoch: str
    channel_sequence: int = 0
    grant_json: bytes | None = None


@dataclass(frozen=True)
class HeldEvidence:
    request: EvidenceRequest
    hold: InputHold
    survives_controller_loss: bool
    observed_monotonic_ns: int


@dataclass(frozen=True)
class WorldEvidence:
    request: EvidenceRequest
    observation: WorldObservation
    planning_verified: bool
    planning_evidence_id: str
    native_pairs_verified: bool
    native_callback_boundary_verified: bool
    observed_monotonic_ns: int


@dataclass(frozen=True)
class ReleaseEvidence:
    request: EvidenceRequest
    release: InputRelease
    physical_all_released: bool
    devices_known: bool
    drain_completed: bool
    pending_native_requests: int
    neutral_cycle: str
    neutral_started_monotonic_ns: int
    released_monotonic_ns: int


@dataclass(frozen=True)
class RetainedEvidence:
    request: EvidenceRequest
    input_blocked: bool
    observers_retained: bool
    observed_monotonic_ns: int


@dataclass(frozen=True)
class BootstrapEvidence:
    """Independent publisher/launcher receipt. Never accepted from a peer.

    The provider has staged the exact verified bytes and configured this one
    Session with the request's attempt/intent/profile. Native paths and pointers
    belong to that external implementation; this API does not accept them.
    """
    request: EvidenceRequest
    channel: SessionChannel
    profile_sha256: str
    stage_manifest_json: bytes
    stage_receipt_sha256: str
    world_size: int
    world_file_sha256: str
    adapter_size: int
    adapter_file_sha256: str
    target_basename: str
    new_attachment: str
    stage_verified: bool
    session_configured: bool
    observed_monotonic_ns: int


class SessionNativePort:
    """One guest transition; all native capabilities come from trusted providers.

    native_provider implements hold_input/observe/release_input/retain, each
    taking EvidenceRequest and returning its corresponding immutable evidence.
    bootstrap_provider.bootstrap(request, parts) returns BootstrapEvidence only
    after external publication/configuration succeeds. Both expose provenance.
    Providers must retain barriers/resources on uncertain exceptions; the adapter
    never detaches hooks, deletes intents or automatically republishes/re-arms.
    """
    def __init__(self, gate, *, approved_profile=None, approved_profile_sha256=None,
                 native_provider=None, bootstrap_provider=None, allow_fixture_providers=False):
        require(type(gate) is MapWaitGate, 'Existing MapWaitGate required')
        require(type(approved_profile) is SessionProfile and native_provider is not None and
                bootstrap_provider is not None, 'Approved profile and all trusted providers are required')
        approved_profile.validate()
        require(hexid(approved_profile_sha256,64) and approved_profile.sha256 == approved_profile_sha256,
                'Profile differs from independently approved launcher profile')
        require(type(allow_fixture_providers) is bool, 'Explicit fixture mode required')
        realms=(approved_profile.provenance,getattr(native_provider,'provenance',None),
                getattr(bootstrap_provider,'provenance',None))
        require(all(r in (PRODUCTION,FIXTURE) for r in realms), 'Missing trusted provider provenance')
        require(allow_fixture_providers or FIXTURE not in realms, 'Fixture provider needs explicit opt-in')
        for provider,names in ((native_provider,('hold_input','observe','release_input','retain')),
                               (bootstrap_provider,('bootstrap',))):
            require(all(callable(getattr(provider,n,None)) for n in names), 'Incomplete native provider')
        self.gate=gate;self.profile=approved_profile;self.native=native_provider;self.bootstrap=bootstrap_provider
        self._realms=realms;self._provenance=FIXTURE if FIXTURE in realms else PRODUCTION
        self._identity=canonical(gate.identity);self.lock=threading.RLock()
        self.context=None;self.target=None;self.hold=None;self.intent=None;self.channel=None
        self._channel_endpoint=None
        self.new_attachment=None;self.bootstrap_receipt=None;self.last_session=None;self.last_world=None
        self.hold_consumed=False;self.start_consumed=False;self.arm_dispatched=False;self.release_consumed=False
        self.completed=False;self.held=False;self.uncertain=False;self.reason='';self.errors=[]
        self._check_profile()

    @property
    def provenance(self):
        # No caller-supplied override and no upgrade after fixture construction.
        return self._provenance

    def _providers(self):
        require((self.profile.provenance,getattr(self.native,'provenance',None),
                getattr(self.bootstrap,'provenance',None)) == self._realms, 'Provider realm changed')
        require(self.provenance == (FIXTURE if FIXTURE in self._realms else PRODUCTION), 'Provider trust drift')

    def _check_profile(self):
        require(canonical(self.gate.identity) == self._identity, 'Checkpoint identity changed')
        m=self.gate.identity['manifest'];p=self.profile
        scope=self.gate.identity['scope']
        require(scope['profile']['game_sha256']==p.game_build_sha256 and
                scope['bindings']=={'A':{'force_id':12,'main_district_id':11},
                                   'B':{'force_id':2,'main_district_id':2}} and
                m['state_contract']==p.state_contract and m['parts']['world.s14']['size']==p.world_size and
                m['parts']['world.s14']['sha256']==p.world_file_sha256 and digest(m['node'])==p.node_sha256 and
                self.gate.identity['scope']['bindings']['B']['force_id']==p.viewer_force,
                'Approved session profile does not match staged checkpoint')
        self._providers()

    def _room(self, *, released=False):
        self._check_profile();c=self.gate.coordinator
        with self.gate.lock,c.lock:
            require(c.connected=={'A','B'}, 'Room disconnected')
            if released:
                require(self.gate.phase=='LIVE' and self.gate.status()['accept_planning_intents'] and
                        c.attachments['B']==self.new_attachment, 'Release room/epoch changed')
            else:
                self.gate._boundary()
                require(c.epoch==self.gate.identity['manifest']['epoch'], 'Checkpoint epoch changed')

    def _binding(self):
        i=self.gate.identity;m=i['manifest']
        return Binding(self.context,self.target,self.profile.sha256,digest(m),m['epoch'],
            i['attachments']['A'],i['attachments']['B'],self.profile.viewer_force,m['world_sha256'],
            m['parts']['world.s14']['sha256'],m['parts']['adapter.json']['sha256'],
            self.hold.lease if self.hold else None,self.intent,self.new_attachment)

    def _request(self,purpose,grant=None):
        return EvidenceRequest(self._binding(),purpose,secrets.token_hex(16),time.monotonic_ns(),
            self.gate.coordinator.epoch,
            self.last_session.sequence if self.last_session else 0,canonical(grant) if grant is not None else None)

    @staticmethod
    def _fresh(proof,request):
        require(proof.request==request and type(proof.observed_monotonic_ns) is int and
                proof.observed_monotonic_ns>=request.requested_monotonic_ns, 'Stale/foreign native evidence')

    def _same_hold(self,hold):
        require(type(hold) is InputHold and self.hold is not None and hold==self.hold,
                'Foreign input lease/context')

    def _uncertain(self,reason):
        self.uncertain=True;self.reason=reason

    def hold_input(self,context,target):
        with self.lock:
            require(not self.hold_consumed, 'Input acquisition already consumed')
            self.hold_consumed=True
            require(type(context) is Context and type(target) is TargetBinding, 'Bound context/target required')
            target.validate();self._room()
            require(context.presentation==self.gate.nonce and context.checkpoint_id==self.gate.identity['checkpoint_id'] and
                    context.state_contract==self.profile.state_contract and hexid(context.attempt) and
                    target.attachment==self.gate.identity['attachments']['B'], 'Foreign controller context')
            require(self.gate.journal.status()['status']=='STAGED', 'No new attempt after durable INTENT')
            self.context=context;self.target=target;request=self._request('HOLD_INPUT')
            try:
                proof=self.native.hold_input(request)
                require(type(proof) is HeldEvidence, 'Actual native input hold proof required');self._fresh(proof,request)
                h=proof.hold
                require(type(h) is InputHold and h.context==context and h.attachment==target.attachment and
                        hexid(h.lease) and h.input_blocked is True and proof.survives_controller_loss is True,
                        'Native input barrier not confirmed')
                self.hold=h;self._room();return h
            except BaseException:
                # If no confirmed lease returns, root cannot call retain(hold).
                # The provider must itself preserve its context-bound barrier
                # on exceptions and must never automatically reopen input.
                self._uncertain('INPUT_HOLD_UNCONFIRMED');raise

    def _observe(self,hold,*,restored):
        self._same_hold(hold)
        self._room(released=self.gate.phase=='LIVE')
        request=self._request('RESTORED_WORLD' if restored else 'OLD_WORLD')
        proof=self.native.observe(request)
        require(type(proof) is WorldEvidence, 'Independent world evidence required');self._fresh(proof,request)
        obs=deepcopy(proof.observation)
        require(type(obs) is WorldObservation and obs.lease==hold.lease and obs.input_blocked is True and
                obs.full_world_verified is True and obs.state_contract==self.profile.state_contract and
                proof.planning_verified is True and hexid(proof.planning_evidence_id) and
                proof.native_pairs_verified is True and proof.native_callback_boundary_verified is True,
                'Complete world, planning and input proof required')
        i=self.gate.identity;m=i['manifest']
        host={'attachment':i['attachments']['A'],'world_sha256':m['world_sha256'],'node':m['node']}
        guest={'attachment':self.new_attachment if restored else i['attachments']['B'],
               'viewer_force':self.profile.viewer_force,'safe_boundary':True}
        if restored:guest.update(world_sha256=m['world_sha256'],node=m['node'])
        require(type(obs.host) is dict and type(obs.guest) is dict and canonical(obs.host)==canonical(host) and
                canonical(obs.guest)==canonical(guest) and type(obs.guest['viewer_force']) is int and
                obs.guest['safe_boundary'] is True, 'Observed host/guest differs from checkpoint binding')
        if restored:
            require(hexid(self.new_attachment) and type(obs.planning_ready_time) is int and
                    obs.planning_ready_time>0, 'Restored native planning not established')
        self._room(released=self.gate.phase=='LIVE');self.last_world=obs
        return obs

    def observe(self,hold):
        with self.lock:
            require(not self.held and not self.uncertain, 'Attempt held or uncertain')
            return self._observe(hold,restored=self.completed)

    def _durable_permit(self,permit,parts):
        require(type(permit) is dict and set(permit)=={'checkpoint_id','intent','native_load_permitted_once'} and
                permit['checkpoint_id']==self.context.checkpoint_id and hexid(permit['intent']) and
                permit['native_load_permitted_once'] is True, 'Invalid load permit')
        j=self.gate.journal
        # Frozen journal has no public read-intent API; use its validating read
        # transaction without updating its row or granting a replacement permit.
        with j._transaction() as db:
            row=j._row(db);require(row['status']=='INTENT', 'Durable INTENT must precede native bootstrap')
            stored=j._intent(row['intent'])
            require(stored['coordinator_intent']==permit['intent'], 'Permit differs from durable intent')
            expected=j._parts(db)
        require(type(parts) is dict and set(parts)=={'world.s14','adapter.json'} and
                all(type(parts[n]) is bytes and parts[n]==expected[n] for n in expected),
                'Verified checkpoint bytes changed')
        require(self.gate.coordinator.load_intent==permit['intent'], 'Room load intent changed')

    def start_load(self,context,permit,parts,hold):
        with self.lock:
            require(not self.start_consumed, 'Bootstrap/arm already consumed')
            self.start_consumed=True
            try:
                self._same_hold(hold);require(context==self.context and not self.uncertain and not self.held,
                                               'Foreign/held native start')
                self._room();self._durable_permit(permit,parts);self.intent=permit['intent']
                request=self._request('BOOTSTRAP_BOUND_SESSION')
                receipt=self.bootstrap.bootstrap(request,deepcopy(parts))
                require(type(receipt) is BootstrapEvidence, 'External stage/session receipt required')
                self._fresh(receipt,request)
                require(type(receipt.channel) is SessionChannel, 'Real validated SessionChannel required')
                endpoint=receipt.channel.endpoint;endpoint.validate();m=self.gate.identity['manifest']
                require(endpoint.server_pid==self.target.pid and endpoint.server_birth==self.target.birth and
                        endpoint.attempt==bytes.fromhex(context.attempt) and
                        endpoint.intent==bytes.fromhex(self.intent), 'IPC endpoint binding differs from native permit')
                require(receipt.profile_sha256==self.profile.sha256 and
                        receipt.stage_manifest_json==canonical(m) and hexid(receipt.stage_receipt_sha256,64) and
                        receipt.world_size==m['parts']['world.s14']['size'] and
                        receipt.world_file_sha256==m['parts']['world.s14']['sha256'] and
                        receipt.adapter_size==m['parts']['adapter.json']['size'] and
                        receipt.adapter_file_sha256==m['parts']['adapter.json']['sha256'] and
                        receipt.target_basename==self.profile.target_basename and
                        receipt.stage_verified is True and receipt.session_configured is True and
                        hexid(receipt.new_attachment) and receipt.new_attachment not in self.gate.identity['attachments'].values(),
                        'External publication/configuration receipt mismatch')
                # Never send even Stop to a channel rejected as foreign above.
                # The independent bootstrap provider owns rejected resources.
                self.channel=receipt.channel;self._channel_endpoint=endpoint;self.bootstrap_receipt=receipt
                require(self.channel.sequence==0 and not self.channel.arm_consumed and
                        not self.channel.observation_only and self.channel.fault is None,
                        'Session channel is not a fresh, unarmed binding')
                self.new_attachment=receipt.new_attachment
                self.last_session=self.channel.snapshot()
                require(self.last_session.fields['state']==1 and
                        not any(self.last_session.fields[k] for k in ('error','exception_code','armed','menu_bound',
                            'request_in_flight','cas_published','may_have_published','stop_requested','hooks_restored',
                            'bytes_ready','lifecycle_ready','identity_ready','active_callbacks')),
                        'Native session is not cleanly initialized')
                self._room();self._durable_permit(permit,parts)
                self.arm_dispatched=True  # Before possibly ambiguous transport.
                self.last_session=self.channel.arm_once()
                require(self.last_session.fields['armed']==1 and not self.last_session.fields['error'] and
                        not self.last_session.fields['exception_code'] and
                        self.last_session.fields['state'] in range(2,9), 'Native arm was not acknowledged')
            except BaseException:
                self._uncertain('NATIVE_START_UNCONFIRMED');raise

    def _channel_exact(self):
        self._providers()
        require(type(self.channel) is SessionChannel and self.channel.endpoint==self._channel_endpoint,
                'Bound session endpoint changed')

    def _session_ready(self):
        self._channel_exact();self.last_session=self.channel.snapshot();f=self.last_session.fields
        require(f['state'] in range(2,9) and not any(f[k] for k in
                ('error','exception_code','stop_requested','hooks_restored')), 'Native session failed/stopped')
        if f['identity_ready']:
            require(f['state']==8 and all(f[k] for k in ('armed','menu_bound','cas_published','may_have_published',
                    'bytes_ready','lifecycle_ready')), 'Inconsistent native identity receipt')
        return f['identity_ready']==1 and f['request_in_flight']==0 and f['active_callbacks']==0

    def poll_load(self,hold):
        with self.lock:
            self._same_hold(hold);require(self.start_consumed, 'Native attempt not started')
            if self.channel is None or self.channel.transport is None:
                self._uncertain('NATIVE_CHANNEL_UNAVAILABLE')
                return LoadProgress(self.context,hold.lease,'UNCERTAIN')
            if self.held or self.uncertain:
                # Stop/RetainingObservation is a normal diagnostic state here.
                # Preserve late identity evidence without re-running admission
                # checks or promoting it to an automatically usable receipt.
                self._channel_exact();self.last_session=self.channel.snapshot()
                return LoadProgress(self.context,hold.lease,'UNCERTAIN')
            try:ready=self._session_ready()
            except BaseException:
                self._uncertain('NATIVE_OBSERVATION_UNCERTAIN');raise
            fields=self.last_session.fields
            if fields['error'] or fields['exception_code'] or fields['stop_requested'] or fields['hooks_restored']:
                self._uncertain('NATIVE_SESSION_FAILED_OR_STOPPED')
                return LoadProgress(self.context,hold.lease,'UNCERTAIN')
            if not ready:
                return LoadProgress(self.context,hold.lease,'PENDING')
            # Channel identity is necessary but emphatically insufficient.
            # The provider may raise EvidencePending while planning/full-world proof is
            # still unavailable; no COMPLETE receipt is fabricated in that case.
            self._room()
            try:obs=self._observe(hold,restored=True)
            except EvidencePending:
                return LoadProgress(self.context,hold.lease,'PENDING')
            try:ready=self._session_ready()
            except BaseException:
                self._uncertain('NATIVE_CHANGED_DURING_WORLD_PROOF');raise
            self._room()
            if not ready:return LoadProgress(self.context,hold.lease,'PENDING')
            i=self.gate.identity;m=i['manifest']
            receipt={'player':'B','epoch':m['epoch'],'checkpoint_id':i['checkpoint_id'],'intent':self.intent,
                'world_sha256':m['world_sha256'],'viewer_force':self.profile.viewer_force,
                'attachment':self.new_attachment,'host_observation':deepcopy(obs.host)}
            self.completed=True
            return LoadProgress(self.context,hold.lease,'COMPLETE',receipt)

    def hold_and_retain_observers(self,hold):
        with self.lock:
            self._same_hold(hold);self.held=True
            request=self._request('HOLD_AND_RETAIN')
            failures=[]
            try:
                proof=self.native.retain(request)
                require(type(proof) is RetainedEvidence, 'Actual retained input/observer proof required')
                self._fresh(proof,request)
                require(proof.input_blocked is True and proof.observers_retained is True, 'Barrier/observers not retained')
            except BaseException as error:failures.append('native retain: '+type(error).__name__)
            if self.channel and self.channel.transport is not None:
                try:
                    self._channel_exact();self.last_session=self.channel.stop_keep_observing()
                except BaseException as error:failures.append('session stop: '+type(error).__name__)
            self.errors.extend(failures)
            if failures:
                self._uncertain('HOLD_NOT_CONFIRMED');raise VisualError('; '.join(failures))

    def release_input(self,hold,grant):
        with self.lock:
            require(not self.release_consumed, 'Native release already consumed')
            self.release_consumed=True
            self._same_hold(hold)
            require(self.completed and not self.held and not self.uncertain, 'No fully verified native world')
            self._room(released=True)
            expected={'presentation':self.gate.nonce,'checkpoint_id':self.context.checkpoint_id,
                      'token':self.gate.reveal_token,'attachment':self.new_attachment}
            require(type(grant) is dict and grant==expected and hexid(grant['token']), 'Foreign release grant')
            try:
                require(self._session_ready(), 'Native callbacks are not quiet for release')
                self._observe(hold,restored=True)
                require(self._session_ready(), 'Native session changed before release')
                request=self._request('RELEASE_AFTER_FRESH_NEUTRAL',grant)
                proof=self.native.release_input(request)
                require(type(proof) is ReleaseEvidence and proof.request==request, 'Bound native release proof required')
                r=proof.release
                require(type(r) is InputRelease and r.context==self.context and r.lease==hold.lease and
                        r.grant_token==grant['token'] and r.attachment==self.new_attachment and r.released is True,
                        'Native release identity mismatch')
                require(proof.physical_all_released is True and proof.devices_known is True and
                        proof.drain_completed is True and type(proof.pending_native_requests) is int and
                        proof.pending_native_requests==0 and hexid(proof.neutral_cycle) and
                        type(proof.neutral_started_monotonic_ns) is int and
                        type(proof.released_monotonic_ns) is int and
                        request.requested_monotonic_ns<=proof.neutral_started_monotonic_ns<=proof.released_monotonic_ns,
                        'Fresh post-reveal physical neutral/drain cycle not proved')
                require(self._session_ready(), 'Native session changed during release')
                self._room(released=True);return r
            except BaseException:
                self._uncertain('NATIVE_RELEASE_UNCONFIRMED')
                # Root also calls hold; this independent attempt protects direct
                # adapter users after a possibly applied release with bad ack.
                try:self.hold_and_retain_observers(hold)
                except BaseException:pass
                raise

    def reconnect_for_observation(self):
        with self.lock:
            require(self.channel is not None and self.start_consumed, 'No existing bound channel')
            self._channel_exact()
            self.held=True;self._uncertain('OBSERVATION_ONLY_RECONNECT')
            self.last_session=self.channel.reconnect_for_observation()
            return deepcopy(self.last_session.progress())

    def status(self):
        with self.lock:
            return {'provenance':self.provenance,'hold_consumed':self.hold_consumed,
                'bootstrap_consumed':self.start_consumed,'arm_dispatched':self.arm_dispatched,
                'complete_independent_evidence':self.completed,'release_consumed':self.release_consumed,
                'held':self.held,'uncertain':self.uncertain,'reason':self.reason,'errors':list(self.errors),
                'channel':self.channel.status() if self.channel else None,
                'last_session':deepcopy(self.last_session.progress()) if self.last_session else None,
                'native_gameplay_enabled':False,'input_implementation_provided':False,
                'full_world_implementation_provided':False,'bootstrap_implementation_provided':False}


class EvidencePending(VisualError):
    """Trusted provider explicitly has no complete planning/world proof yet."""
