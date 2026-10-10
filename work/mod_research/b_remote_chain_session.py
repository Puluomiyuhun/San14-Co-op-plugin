"""Retained B native diagnostic session. Import performs no process/file writes.

open() builds the real ports; apply_native() produces local evidence only.
The adapter key and authenticated TLS connection are retained, but this module
does NOT complete a Journal, send formal completion, grant Ready, or advance A.
No-new-commands is a human condition, never a native continuous input fence.
"""
from copy import deepcopy
from dataclasses import asdict
import hashlib
from pathlib import Path
import threading

from authoritative_sync import canonical, digest, validate_scope
from checkpoint_room_client import RoomConnection
from checkpoint_bootstrap_journal import BootstrapCheckpointJournal
from checkpoint_journal import CheckpointJournal
from b_warm_room import ReceivedCheckpoint
from b_warm_profile_contract import Profile, validate_profile
from b_warm_received_apply import write_once
from b_warm_refresh_received_apply import ReceivedApply as RefreshAcceptance
from b_warm_world import sample
from human_rules_world_lifecycle import NextWorldRequest
from b_remote_session_boundary import DiagnosticBoundary, need
from b_remote_chain_lifecycle import DiagnosticRulesCapture, DiagnosticRulesFactory, DiagnosticLifecycle, DiagnosticBridge


REQUIRED_SOURCES=('b_remote_chain_session.py','b_warm_chain_bootstrap.py','b_warm_chain_rules_bridge.py','b_warm_chain_coordinator_contract.py','b_observed_chain_completion.py','b_remote_session_boundary.py','b_remote_chain_lifecycle.py',
    'b_warm_chain_resident.py','b_warm_stable_refresh_coordinator.py','b_warm_refresh_coordinator.py',
    'b_warm_coordinator_contract.py','b_warm_refresh_contract.py','b_warm_stable_capture.py','b_warm_profile_capture.py',
    'b_warm_rules_factory.py','b_warm_rules_capture.py','b_warm_remote_rules.py',
    'human_rules_world_lifecycle.py','b_warm_refresh_rules_bridge.py','b_warm_refresh_bootstrap.py',
    'b_warm_bootstrap.py','b_warm_refresh_received_apply.py','b_warm_received_apply.py','b_warm_rules_bridge.py',
    'b_warm_world.py','b_warm_adapter_key.py','b_warm_staging.py','b_warm_coordinator.py',
    'b_warm_start.py','b_warm_start_support.py','b_warm_refresh_start_support.py',
    'b_warm_start_acceptance.py','b_warm_pair_diagnostic.py','b_warm_pair_preflight.py')


def verify_sources(pins):
    need(type(pins) is dict and pins, 'Explicit approved source manifest required')
    here=Path(__file__).resolve().parent
    for name in REQUIRED_SOURCES:
        path=str((here/name).resolve())
        need(path in pins, 'Missing session source pin: '+name)
    for name,h in pins.items():
        need(Path(name).is_absolute() and hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,
             'Session source drift: '+name)


def approved_builds(pair_path,pair_sha,helper_path,helper_sha):
    from b_warm_coordinator import approved_component
    pair=approved_component(pair_path,pair_sha,'san14.b-warm-refresh-pair.v1')
    helper=approved_component(helper_path,helper_sha,'san14.b-warm-chain-coordinator.v1')
    need(pair.get('refresh_factory_pair_passed') is True,'Actual two refresh factories required')
    need(helper.get('chain_exports_passed') is True,'Actual bounded-chain export checks required')
    required=('b_warm_chain_coordinator_native.h','b_warm_chain_coordinator_native.cpp',
              'b_warm_chain_handover.h','b_warm_chain_handover.cpp','b_warm_two_bank_owner.cpp')
    for name in required:
        path=str((Path(__file__).resolve().parent/name).resolve())
        need(helper['sources'].get(path)==hashlib.sha256(Path(path).read_bytes()).hexdigest(),
             'Missing chain helper source closure: '+name)
    for n,h in helper['sources'].items():
        if Path(n).suffix in ('.h','.cpp') and n in pair['sources']:
            need(pair['sources'][n]==h,'Shared native source differs')
    for row,path in ((pair,pair_path),(helper,helper_path)):
        p=Path(row['production_dll']['path']).resolve(strict=True);h=row['production_dll']['sha256']
        need(p.is_relative_to(Path(path).resolve().parent) and row['binaries'].get(str(p))==h and
             hashlib.sha256(p.read_bytes()).hexdigest()==h,'Production DLL closure differs')
    return pair,helper


class Session(RefreshAcceptance):
    def __init__(self,*args,**kwargs):
        raise TypeError('Use Session.open with explicit production bindings')

    def apply(self,*args,**kwargs):
        raise TypeError('Only apply_native is exposed; no inherited formal/advisory adapter')

    @classmethod
    def open(cls, *, reader, control, scope, settings, profile, initial_request, target, initial_target,
             records, adapter_key_path, pair_build, pair_sha256, helper_build, helper_sha256,
             rules_build, steam_paths, source_pins, no_new_commands, timeout=180):
        """Explicit local installation entry; callers retain this object on failure.

        An exception after allocation exposes retained_session. Never discard it
        and reconnect/reconstruct to replay: unknown native calls remain unknown.
        The first profile is known received-file metadata, not a future save hash.
        initial_request describes the existing A-view world, generation 1.
        """
        from game_reader import GameReader
        from checkpoint_complete_live_capture import process_birth
        from b_warm_rules_factory import RulesBuild
        from b_warm_chain_resident import Resident
        from b_warm_refresh_start_support import identity
        from b_warm_pair_preflight import dll_identity,STEAM_HASHES
        from b_warm_pair_diagnostic import require_original_rules,require_no_debugger
        from b_warm_start import refuse_prior_attempt,PRIVATE,save_new
        from b_warm_adapter_key import load_key
        import b_warm_staging as files
        verify_sources(source_pins);validate_scope(scope);validate_profile(profile)
        target=files.clean_path(target);records=files.clean_path(records)
        need(target.name==files.NAME and records.is_dir() and not any(records.iterdir()) and
             records!=target.parent,'Exact target and fresh independent records required')
        for side,viewer in (('A',profile.source),('B',profile.target)):
            need(scope['bindings'][side]==dict(force_id=viewer.force,main_district_id=viewer.district),
                 'Initial profile differs from room human bindings')
        need(type(reader) is GameReader and type(control) is RoomConnection and control.player_id=='B',
             'Actual retained reader and authenticated B connection required')
        need(no_new_commands is True and type(rules_build) is RulesBuild and
             rules_build.source_kind=='LOCAL_NATIVE_PROVIDER','Explicit diagnostic condition/production rules required')
        need(type(initial_request) is NextWorldRequest and initial_request.generation==1 and
             (initial_request.year,initial_request.month,initial_request.day)==
             (profile.before.year,profile.before.month,profile.before.day) and
             profile.currentForce==profile.source.force,'Initial A-view generation required')
        need(type(timeout) is int and 30<=timeout<=1800,'Bounded timeout required')
        pair,helper=approved_builds(pair_build,pair_sha256,helper_build,helper_sha256)
        need(type(steam_paths) is dict and set(steam_paths)==set(STEAM_HASHES),'Exact storage module paths required')
        for name,h in STEAM_HASHES.items():
            need(Path(steam_paths[name]).name==name and dll_identity(steam_paths[name])['sha256']==h,
                 'Storage module file differs')
        rules_build.check();identity(initial_target)
        need(files.read_file(target)[0]==initial_target,'Initial target changed')
        key=load_key(adapter_key_path);birth=process_birth(reader)
        boundary=DiagnosticBoundary(reader,profile,pid=reader.pid,birth=birth,no_new_commands=True)
        boundary.observe();require_original_rules(reader,pid=reader.pid,birth=birth);require_no_debugger(reader)
        refuse_prior_attempt(reader.pid,birth)
        obj=cls.__new__(cls);obj.reader=reader;obj.control=control;obj._key=key;obj.boundary=boundary
        obj.records=records;obj.scope=deepcopy(scope);obj.phase='PREPARING';obj.sessions=[];obj._lock=threading.RLock()
        obj.source_pins=dict(source_pins);obj._control_owner=control;obj.warm=None;obj.factory=None
        obj.native_identity=(reader.pid,birth);obj.read_birth=lambda:process_birth(reader)
        try:
            claims=PRIVATE/'b_warm_start_claims';claims.mkdir(exist_ok=True)
            save_new(claims/f'{reader.pid}-{birth}.json',dict(pid=reader.pid,birth=birth,run=str(records),
                kind='retained-no-new-command-session',automatic_retry=False))
            for n in ('native','rules','bridge'):(records/n).mkdir()
            p,h=pair['production_dll'],helper['production_dll']
            obj.warm=Resident.__new__(Resident)
            Resident.__init__(obj.warm,reader,records/'native',Path(p['path']),p['sha256'],Path(h['path']),h['sha256'],
                              steam_paths,profile.source.ruler,timeout)
            obj.capture=DiagnosticRulesCapture(reader,control,scope,settings,boundary=boundary,read_birth=obj.read_birth)
            obj.factory=DiagnosticRulesFactory(obj.capture,obj.warm.api,rules_build,records/'rules',
                rulers={profile.source.force:profile.source.ruler,profile.target.force:profile.target.ruler})
            initial=obj.capture.capture_loaded(initial_request,side='A',expected_ruler=profile.source.ruler)
            port=obj.factory.prepare_rules(initial);port.install()
            obj.lifecycle=DiagnosticLifecycle(port,boundary)
            obj.bridge=DiagnosticBridge(obj.lifecycle,obj.warm,target=target,records=records/'bridge')
            obj.observe_loaded=lambda request:obj.capture.capture_loaded(request,side='B',expected_ruler=profile.target.ruler)
            obj.prepare_rules=obj.factory.prepare_rules
            obj._owners=(obj.reader,obj.control,obj.warm,obj.lifecycle,obj.bridge,obj.boundary,obj.factory)
            obj._scope_bytes=canonical(obj.scope)
            need(obj.bridge.initial_target==initial_target,'Target changed while preparing rules')
            boundary.observe();verify_sources(source_pins);obj.phase='ACTIVE'
            write_once(records/'prepared.json',obj.status())
            return obj
        except BaseException as exc:
            obj.phase='TERMINAL';boundary.hold(repr(exc));exc.retained_session=obj
            try:write_once(records/'prepare-failed.json',dict(error=repr(exc),retained=True,ready=False))
            except BaseException as log_exc:obj.record_error=repr(log_exc);exc.record_error=obj.record_error
            raise

    def status(self):
        return dict(phase=self.phase,completed=len(self.sessions),pid=self.native_identity[0],birth=self.native_identity[1],
            adapter_key_fingerprint=hashlib.sha256(self._key).hexdigest(),ready=False,formal_completion_sent=False,
            input_exclusion_proven=False,scheduler_fence_proven=False,human_no_new_commands=True,
            native_gameplay_enabled=False,full_world_verified=False)

    def _validate(self, received, request, profile, reservation):
        need(self._owners==(self.reader,self.control,self.warm,self.lifecycle,self.bridge,self.boundary,self.factory) and
             self.bridge.warm is self.warm and self.bridge.lifecycle is self.lifecycle and
             self.lifecycle.boundary is self.boundary and self.warm.reader is self.reader and
             canonical(self.scope)==self._scope_bytes,'Retained owner graph/scope changed')
        need(self.control is self._control_owner and self.control.player_id=='B' and
             self.control.status()['transport_open'] is True,'Retained TLS control lost or replaced')
        need(type(received) is ReceivedCheckpoint and type(request) is NextWorldRequest and type(profile) is Profile and
             not received.ack_attempted,'Typed unused received checkpoint required')
        validate_profile(profile);context=received.context();m=context['manifest'];j=received.journal
        need(canonical(context['scope'])==canonical(self.scope) and request.checkpoint==context['checkpoint_id'],
             'Received scope/checkpoint differs')
        expected=dict(schema='san14.checkpoint-journal.v1',local_player='B',scope=self.scope,manifest=m,
                      checkpoint_id=request.checkpoint,attachments=context['attachments'])
        if not self.sessions:
            need(type(j) is BootstrapCheckpointJournal and m['period']==1,'First source-view bootstrap journal required')
            expected.update(schema='san14.checkpoint-bootstrap-journal.v1',
                            pre_load_viewer_force=self.scope['bindings']['A']['force_id'])
        else:
            need(type(j) is CheckpointJournal,'Exact ordinary checkpoint journal required')
            need(m['period']==self.sessions[-1]['period']+1 and m['epoch']!=self.sessions[-1]['epoch'],
                 'Next diagnostic input has not advanced its authority period')
        need(canonical(j.identity)==canonical(expected),'Journal identity differs')
        if reservation is None:need(j.status()['status']=='STAGED','Journal already consumed/reserved')
        else:
            need(type(reservation) is dict and set(reservation)=={'checkpoint_id','intent','native_load_permitted_once'} and
                 reservation['checkpoint_id']==request.checkpoint and reservation['native_load_permitted_once'] is True,
                 'Malformed local reservation')
            with j._transaction() as db:
                row=j._row(db)
                need(row['status']=='INTENT' and j._intent(row['intent'])['coordinator_intent']==reservation['intent'],
                     'No matching persisted local reservation')
        need(m['node']==dict(year=request.year,month=request.month,day=request.day,phase='PLANNING_BOUNDARY'),
             'Native request date differs')
        for side,viewer in (('A',profile.source),('B',profile.target)):
            need(self.scope['bindings'][side]==dict(force_id=viewer.force,main_district_id=viewer.district),
                 'Received human identity changed')
        raw=received.verified_file()
        need((profile.file.size,bytes(profile.file.sha256).hex())==(len(raw),hashlib.sha256(raw).hexdigest()),
             'Profile differs from TLS-verified bytes')
        need(self.read_birth()==self.native_identity[1] and self.reader.pid==self.native_identity[0],
             'Retained process incarnation changed')
        return context

    def apply_native(self, received, request, profile, *, reservation=None):
        with self._lock:
            need(self.phase=='ACTIVE' and len(self.sessions)<3,'Session consumed/terminal; no replay')
            self.phase='APPLYING'
            try:
                verify_sources(self.source_pins)
                context=self._validate(received,request,profile,reservation)
                write_once(received.directory/'diagnostic-native-intent.json',dict(checkpoint=request.checkpoint,
                    profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(),retry_allowed=False,
                    boundary='OBSERVATION_AND_HUMAN_NO_NEW_COMMANDS',formal_permission=False))
                outcome=self.bridge.replace(request,profile,received.file,
                    observe_loaded=self.observe_loaded,prepare_rules=self.prepare_rules)
                completion=RefreshAcceptance._completion(self,outcome,request,profile)
                observation=self.boundary.observe()
                world=sample(self.reader,scope=self.scope,epoch=context['manifest']['epoch'],
                    period=context['manifest']['period'],profile=profile,side='B',
                    receipt_key=completion['accepted']['receipt_key'],read_birth=self.read_birth)
                self.boundary.observe();received.verified_file()
                need(self.control.status()['transport_open'] is True,'TLS closed after native completion')
                result=dict(completion=completion,sample=world,boundary=asdict(observation),
                    ready=False,formal_completion_sent=False,journal_completed=False,retain_for_review=True)
                write_once(received.directory/'diagnostic-native-completion.json',result)
                self.sessions.append(dict(period=context['manifest']['period'],epoch=context['manifest']['epoch'],
                                          checkpoint=request.checkpoint,result=result))
                self.phase='ACTIVE' if len(self.sessions)<3 else 'THREE_LOADS_RETAINED'
                return result
            except BaseException as exc:
                self.phase='TERMINAL';self.boundary.hold(repr(exc))
                try:write_once(received.directory/'diagnostic-native-failed.json',dict(error=repr(exc),
                    native_may_have_completed=True,retry_allowed=False,ready=False))
                except BaseException as log_exc:self.record_error=repr(log_exc);exc.record_error=self.record_error
                raise

    # Used by RefreshAcceptance's unchanged super() dispatch.
    _completion=RefreshAcceptance._completion
