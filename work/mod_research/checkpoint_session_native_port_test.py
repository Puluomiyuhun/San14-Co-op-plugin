"""Real composition, synthetic native providers and binary channel transport.

No process, pipe, window, game, Steam or publisher is opened by this test.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest

from checkpoint_session_native_port import *
from checkpoint_session_channel import (Endpoint,REQUEST,RESPONSE,MAGIC,VERSION,FIELDS,
                                        ARM_ONCE,SNAPSHOT,STOP_KEEP_OBSERVING,OutcomeUnknown)
from checkpoint_visual_client_test import FakeTransport,BINDING,fixture_evidence,GateFixture
from checkpoint_visual_client import VisualClient
from checkpoint_visual_client_bridge import GateVisualBridge
from checkpoint_guest_transition import GuestTransition

HERE=Path(__file__).resolve().parent


class BinarySessionTransport:
    """Bytes pass through the actual frozen SessionChannel codec and state rules."""
    def __init__(self,endpoint):
        self.endpoint=endpoint;self.sent=[];self.closed=False;self.sequence=0
        self.armed=False;self.ready=False;self.stopped=False;self.active=0;self.error=0
        self.state_override=None;self.fail_arm=False;self.fail_stop=False;self.interceptor=None
    def exchange(self,data,timeout):
        m,v,op,seq,secret,attempt,intent=REQUEST.unpack(data)
        assert (m,v,secret,attempt,intent)==(MAGIC,VERSION,self.endpoint.secret,self.endpoint.attempt,self.endpoint.intent)
        assert seq>self.sequence;self.sequence=seq;self.sent.append(op)
        if op==ARM_ONCE:
            assert not self.armed and not self.stopped;self.armed=True
            if self.fail_arm:raise OutcomeUnknown('Synthetic acknowledgement loss after arm')
        elif op==STOP_KEEP_OBSERVING:
            self.stopped=True
            if self.fail_stop:raise OutcomeUnknown('Synthetic stop acknowledgement loss')
        elif op!=SNAPSHOT:raise AssertionError('Unsupported opcode')
        state=(10 if self.ready else 9) if self.stopped else (8 if self.ready else 2 if self.armed else 1)
        fields=dict.fromkeys(FIELDS,0)
        fields.update(state=self.state_override if self.state_override is not None else state,
            armed=int(self.armed),menu_bound=int(self.ready),cas_published=int(self.ready),
            may_have_published=int(self.ready),stop_requested=int(self.stopped),bytes_ready=int(self.ready),
            lifecycle_ready=int(self.ready),identity_ready=int(self.ready),active_callbacks=self.active,error=self.error)
        if self.interceptor:fields=self.interceptor(op,fields)
        return RESPONSE.pack(MAGIC,VERSION,op,seq,attempt,*[fields[k] for k in FIELDS])
    def close(self):self.closed=True


class SyntheticNativeEvidence:
    provenance=FIXTURE
    def __init__(self,fixture):
        self.f=fixture;self.calls=[];self.world_ready=False;self.input_open=False
        self.world_mutator=lambda p:p;self.release_mutator=lambda p:p
        self.observe_action=lambda req:None;self.release_action=lambda req:None;self.retain_error=False
    def hold_input(self,request):
        self.calls.append('hold_input');self.input_open=False
        return HeldEvidence(request,InputHold(request.binding.context,'2'*32,
            request.binding.target.attachment,True),True,time.monotonic_ns())
    def observe(self,request):
        self.calls.append('observe');self.observe_action(request)
        restored=request.purpose=='RESTORED_WORLD'
        if restored and not self.world_ready:raise EvidencePending('Only identity arrived, no full-world proof')
        obs=WorldObservation(request.binding.lease,deepcopy(self.f.host),
            deepcopy(self.f.new if restored else self.f.old),not self.input_open,True,
            request.binding.context.state_contract,250 if restored else 0)
        return self.world_mutator(WorldEvidence(request,obs,True,'3'*32,True,True,time.monotonic_ns()))
    def release_input(self,request):
        self.calls.append('release_input');self.release_action(request);self.input_open=True
        grant=json.loads(request.grant_json);now=time.monotonic_ns()
        released=InputRelease(request.binding.context,request.binding.lease,grant['token'],
                              request.binding.new_attachment,True)
        return self.release_mutator(ReleaseEvidence(request,released,True,True,True,0,'4'*32,now,now+1))
    def retain(self,request):
        self.calls.append('retain');self.input_open=False
        if self.retain_error:raise RuntimeError('Synthetic retain failure')
        return RetainedEvidence(request,True,True,time.monotonic_ns())


class SyntheticBootstrap:
    provenance=FIXTURE
    def __init__(self,fixture,profile):
        self.f=fixture;self.profile=profile;self.calls=0;self.wire=None;self.channel=None
        self.mutator=lambda r:r;self.endpoint_mutator=lambda e:e;self.wire_setup=lambda w:None
        self.last_request=None
    def bootstrap(self,request,parts):
        self.calls+=1;self.last_request=request
        assert self.f.j.status()['status']=='INTENT'
        assert parts==self.f.j.verified_parts()
        b=request.binding
        endpoint=self.endpoint_mutator(Endpoint('\\\\.\\pipe\\san14-checkpoint-portfixture',b.target.pid,
            b.target.birth,b's'*32,bytes.fromhex(b.context.attempt),bytes.fromhex(b.intent)))
        self.wire=BinarySessionTransport(endpoint);self.wire_setup(self.wire)
        self.channel=SessionChannel(endpoint,transport_factory=lambda e:self.wire)
        m=self.f.g.identity['manifest']
        result=BootstrapEvidence(request,self.channel,self.profile.sha256,canonical(m),'5'*64,
            len(parts['world.s14']),hashlib.sha256(parts['world.s14']).hexdigest(),len(parts['adapter.json']),
            hashlib.sha256(parts['adapter.json']).hexdigest(),'svdexccSC03.s14','c'*32,True,True,time.monotonic_ns())
        return self.mutator(result)


def profile_for(fixture):
    i=fixture.g.identity;m=i['manifest']
    return SessionProfile(FIXTURE,'san14.cc63-native-session.v1',i['scope']['profile']['game_sha256'],
        '6'*64,'7'*64,m['state_contract'],'svdexccSC03.s14',m['parts']['world.s14']['size'],
        m['parts']['world.s14']['sha256'],digest(m['node']),2)


class NativePortTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='checkpoint_session_native_port_',dir=HERE)
        self.addCleanup(self.tmp.cleanup);self.f=GateFixture(self.tmp.name);self.profile=profile_for(self.f)
        self.native=SyntheticNativeEvidence(self.f);self.bootstrap=SyntheticBootstrap(self.f,self.profile)
        self.port=self.make_port()
        self.visual_transport=FakeTransport();self.client=VisualClient(self.visual_transport,session='1'*32,timeout=.3)
        self.addCleanup(self.close)
        self.bridge=GateVisualBridge(self.client,evidence_provider=fixture_evidence,allow_fixture_evidence=True)
        self.flow=GuestTransition(self.f.g,self.bridge,self.port,allow_fixture_native=True)
    def make_port(self,**overrides):
        kw=dict(approved_profile=self.profile,approved_profile_sha256=self.profile.sha256,
            native_provider=self.native,bootstrap_provider=self.bootstrap,allow_fixture_providers=True)
        kw.update(overrides);return SessionNativePort(self.f.g,**kw)
    def close(self):
        if not self.client._closed:self.client.terminate_helper(accept_cover_loss=True)
        if self.bootstrap.channel:self.bootstrap.channel.close()
    def start(self):return self.flow.start(BINDING)
    def identity_ready(self):self.bootstrap.wire.ready=True
    def fully_ready(self):self.identity_ready();self.native.world_ready=True
    def held(self):
        self.assertEqual(self.flow.phase,'HELD');self.assertFalse(self.native.input_open)
        self.assertFalse(self.flow.status()['accept_planning_intents'])
        if self.bootstrap.wire:self.assertLessEqual(self.bootstrap.wire.sent.count(ARM_ONCE),1)
    def test_real_controller_journal_channel_bridge_cycle(self):
        self.assertEqual(self.start()['phase'],'LOADING');self.assertEqual(self.f.j.status()['status'],'INTENT')
        self.assertEqual(self.bootstrap.wire.sent,[SNAPSHOT,ARM_ONCE])
        self.fully_ready();self.assertTrue(self.flow.poll()['accept_planning_intents'])
        self.assertTrue(self.native.input_open);self.assertEqual(self.f.j.status()['status'],'COMPLETED')
        self.assertEqual(self.bootstrap.calls,1);self.assertEqual(self.bootstrap.wire.sent.count(ARM_ONCE),1)
        self.assertEqual(self.port.provenance,FIXTURE);self.assertFalse(self.port.status()['native_gameplay_enabled'])
    def test_constructor_missing_providers_and_fixture_upgrade_rejected(self):
        with self.assertRaises(VisualError):SessionNativePort(self.f.g)
        with self.assertRaises(VisualError):self.make_port(allow_fixture_providers=False)
        with self.assertRaises(AttributeError):self.port.provenance=PRODUCTION
        self.native.provenance=PRODUCTION
        with self.assertRaises(VisualError):self.start()
        self.assertEqual(self.bootstrap.calls,0)
    def test_wrong_build_profile_rejected_before_native_calls(self):
        wrong=replace(self.profile,game_build_sha256='8'*64)
        with self.assertRaises(VisualError):self.make_port(approved_profile=wrong,approved_profile_sha256=wrong.sha256)
        self.assertEqual(self.native.calls,[])
    def test_unapproved_profile_hash_rejected(self):
        with self.assertRaises(VisualError):self.make_port(approved_profile_sha256='0'*64)
    def test_identity_alone_does_not_complete(self):
        self.start();self.identity_ready();r=self.flow.poll()
        self.assertEqual(r['phase'],'LOADING');self.assertEqual(self.f.j.status()['status'],'INTENT')
        self.assertFalse(self.port.completed);self.assertNotIn('release_input',self.native.calls)
    def test_active_callbacks_wait_without_requesting_world_completion(self):
        self.start();self.fully_ready();self.bootstrap.wire.active=1;n=len(self.native.calls)
        self.assertEqual(self.flow.poll()['phase'],'LOADING');self.assertEqual(len(self.native.calls),n)
        self.assertEqual(self.f.j.status()['status'],'INTENT')
    def test_uncertain_native_state_rejects_even_with_identity_flags(self):
        self.start();self.fully_ready();self.bootstrap.wire.state_override=12
        with self.assertRaises(VisualError):self.flow.poll()
        self.held();self.assertFalse(self.port.completed)
    def test_wrong_endpoint_intent_never_arms_or_stops_foreign_channel(self):
        self.bootstrap.endpoint_mutator=lambda ep:replace(ep,intent=b'x'*16)
        with self.assertRaises(VisualError):self.start()
        self.held();self.assertEqual(self.bootstrap.wire.sent,[])
    def test_wrong_endpoint_attempt_pid_birth_never_arms(self):
        self.bootstrap.endpoint_mutator=lambda ep:replace(ep,attempt=b'x'*16,server_birth=ep.server_birth+1)
        with self.assertRaises(VisualError):self.start()
        self.held();self.assertEqual(self.bootstrap.wire.sent,[])
    def test_stage_manifest_or_sha_mismatch_never_arms(self):
        self.bootstrap.mutator=lambda r:replace(r,world_file_sha256='0'*64)
        with self.assertRaises(VisualError):self.start()
        self.held();self.assertEqual(self.bootstrap.wire.sent,[])
    def test_bootstrap_is_after_durable_intent_and_cannot_repeat(self):
        self.start()
        with self.assertRaises(VisualError):self.port.start_load(self.flow.context,self.flow.permit,
            self.f.j.verified_parts(),self.flow.hold)
        self.assertEqual(self.bootstrap.calls,1);self.assertEqual(self.bootstrap.wire.sent.count(ARM_ONCE),1)
    def test_unknown_arm_retains_input_and_no_second_arm(self):
        self.bootstrap.wire_setup=lambda wire:setattr(wire,'fail_arm',True)
        with self.assertRaises(OutcomeUnknown):self.start()
        self.held();self.assertEqual(self.f.j.status()['status'],'INTENT')
        self.assertEqual(self.bootstrap.wire.sent.count(ARM_ONCE),1)
        with self.assertRaises(VisualError):self.port.start_load(self.flow.context,self.flow.permit,
            self.f.j.verified_parts(),self.flow.hold)
    def test_wrong_restored_attachment_not_promoted_to_complete(self):
        self.start();self.fully_ready()
        self.native.world_mutator=lambda p:replace(p,observation=replace(p.observation,
            guest={**p.observation.guest,'attachment':'d'*32}))
        with self.assertRaises(VisualError):self.flow.poll()
        self.held();self.assertEqual(self.f.j.status()['status'],'INTENT')
    def test_missing_planning_or_pair_proof_rejected(self):
        self.start();self.fully_ready()
        self.native.world_mutator=lambda p:replace(p,native_pairs_verified=False)
        with self.assertRaises(VisualError):self.flow.poll()
        self.held();self.assertFalse(self.port.completed)
    def test_session_stop_during_world_observation_prevents_completion(self):
        self.start();self.fully_ready()
        self.native.observe_action=lambda request:setattr(self.bootstrap.wire,'stopped',True)
        with self.assertRaises(VisualError):self.flow.poll()
        self.held();self.assertFalse(self.port.completed)
    def test_old_physical_neutral_cycle_cannot_release(self):
        self.start();self.fully_ready()
        self.native.release_mutator=lambda p:replace(p,neutral_started_monotonic_ns=1)
        with self.assertRaises(VisualError):self.flow.poll()
        self.held();self.assertIn('retain',self.native.calls)
    def test_session_error_during_release_recloses_input(self):
        self.start();self.fully_ready()
        self.native.release_action=lambda request:setattr(self.bootstrap.wire,'error',9)
        with self.assertRaises(VisualError):self.flow.poll()
        self.held();self.assertIn(STOP_KEEP_OBSERVING,self.bootstrap.wire.sent)
    def test_retain_failure_still_sends_stop(self):
        self.start();self.native.retain_error=True
        with self.assertRaises(VisualError):self.port.hold_and_retain_observers(self.flow.hold)
        self.assertIn(STOP_KEEP_OBSERVING,self.bootstrap.wire.sent);self.assertTrue(self.port.errors)
        self.bootstrap.wire.ready=True
        self.assertEqual(self.port.poll_load(self.flow.hold).state,'UNCERTAIN')
        self.assertEqual(self.port.last_session.fields['identity_ready'],1)
        self.assertFalse(self.port.completed)
    def test_stop_failure_still_invokes_independent_input_retain(self):
        self.start();self.bootstrap.wire.fail_stop=True;self.native.input_open=True
        with self.assertRaises(VisualError):self.port.hold_and_retain_observers(self.flow.hold)
        self.assertFalse(self.native.input_open);self.assertIn('retain',self.native.calls)
        self.assertTrue(self.port.errors)
    def test_new_adapter_cannot_reacquire_after_durable_intent(self):
        self.start();other=self.make_port()
        with self.assertRaises(VisualError):other.hold_input(self.flow.context,BINDING)
        self.assertEqual(self.native.calls.count('hold_input'),1)


if __name__=='__main__':
    frozen=[HERE/'checkpoint_session_channel.py',HERE/'checkpoint_session_ipc.cpp',HERE/'checkpoint_session_ipc.h',
        HERE/'checkpoint_guest_transition.py',HERE/'checkpoint_visual_client.py',HERE/'checkpoint_visual_client_bridge.py']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={str(p):sha(p) for p in frozen}
    out=HERE/'checkpoint_session_native_port_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    with (out/'unittest.txt').open('w',encoding='utf8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativePortTests))
    assert before=={str(p):sha(p) for p in frozen}
    report={'schema':'san14.session-native-port-composition-fixtures.v1','result':'PASS' if result.wasSuccessful() else 'FAIL',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'source_sha256':{n:sha(HERE/n) for n in ('checkpoint_session_native_port.py','checkpoint_session_native_port_test.py')},
        'frozen_unchanged':before,'native_providers_and_wire':'SYNTHETIC',
        'actual_modules':['GuestTransition','MapWaitGate','CheckpointJournal','VisualClient','GateVisualBridge','SessionChannel'],
        'game_access':False,'steam_access':False,'window_access':False,'process_access':False,
        'actual_ipc_exercised_by_this_test':False,'native_gameplay_enabled':False,
        'production_input_world_publisher_provider_implemented':False}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'result':report['result'],'tests':result.testsRun,'path':str(out/'result.json')}))
    if not result.wasSuccessful():print((out/'unittest.txt').read_text())
    raise SystemExit(not result.wasSuccessful())
