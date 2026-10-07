"""Own-process staging/bootstrap tests. No game, Steam, window or WGC access."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
import secrets
import tempfile
import time
import unittest

from checkpoint_test_bootstrap import *
from checkpoint_guest_transition import Context,GuestTransition
from checkpoint_session_native_port import Binding,EvidenceRequest,SessionNativePort
from checkpoint_visual_client_test import BINDING,FakeTransport,fixture_evidence
from checkpoint_visual_client import VisualClient,VisualError
from checkpoint_visual_client_bridge import GateVisualBridge
from checkpoint_offline_prototype import ArchiveFixture,InitialOnlyFixtureEvidence

APPROVED=hashlib.sha256(EXE.read_bytes()).hexdigest()
SOURCES=['checkpoint_test_bootstrap.py','checkpoint_test_bootstrap_test.py',
    'checkpoint_session_ipc_fixture.cpp','checkpoint_session_ipc_fixture.asm',
    'checkpoint_session_ipc_build.cmd','checkpoint_session_ipc.h','checkpoint_session_ipc.cpp',
    'checkpoint_guest_native_session.h','checkpoint_guest_native_session.cpp',
    'checkpoint_session_channel.py','checkpoint_session_native_port.py',
    'checkpoint_guest_transition.py','checkpoint_offline_prototype.py']
for stem in ('checkpoint_load_worker_bridge','checkpoint_load_dispatch_bridge',
             'native_storage_read_core','checkpoint_cc_load_observer','checkpoint_cc_load_lifecycle',
             'checkpoint_title_identity_adapter','checkpoint_identity_pair_commit',
             'checkpoint_load_request_commit','checkpoint_load_input_boundary','checkpoint_load_hook_set'):
    SOURCES.extend((stem+'.h',stem+'.cpp'))
SOURCES.extend(('checkpoint_load_worker_bridge.asm','checkpoint_load_dispatch_bridge.asm',
                'checkpoint_push_bridge.h','checkpoint_load_input_boundary_fixture_layout.h'))


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='test-bootstrap-journal-',dir=HERE)
        self.addCleanup(self.tmp.cleanup)
        self.f=ArchiveFixture(Path(self.tmp.name));m=self.f.g.identity['manifest']
        self.profile=SessionProfile(FIXTURE,'san14.cc63-native-session.v1',GAME_SHA,APPROVED,
            hashlib.sha256((HERE/'checkpoint_guest_native_session.h').read_bytes()).hexdigest(),
            m['state_contract'],TARGET,SIZE,SHA,digest(NODE),2)
        self.children=[]
        self.addCleanup(self.cleanup)
    def cleanup(self):
        for child in self.children:
            r=child.close()
            self.assertEqual(r['close_errors'],[])
            if child.process:self.assertIsNotNone(r['exit_code'])
    def create(self,**kw):
        args=dict(profile=self.profile,manifest=self.f.g.identity['manifest'],approved_fixture_sha256=APPROVED)
        args.update(kw);b=WorkspaceFixtureBootstrap(**args);self.children.append(b);return b
    def request(self,b,*,attempt=None,intent=None):
        p=b.prepare_fixture();m=self.f.g.identity['manifest']
        context=Context(attempt or secrets.token_hex(16),self.f.g.nonce,digest(m),m['state_contract'])
        bind=Binding(context,replace(BINDING,pid=p['pid'],birth=p['birth']),self.profile.sha256,
            digest(m),m['epoch'],'a'*32,'b'*32,2,m['world_sha256'],SHA,
            m['parts']['adapter.json']['sha256'],'2'*32,intent or secrets.token_hex(16),None)
        return EvidenceRequest(bind,'BOOTSTRAP_BOUND_SESSION',secrets.token_hex(16),time.monotonic_ns(),m['epoch'])
    def test_deferred_process_has_exact_birth_no_window_no_session_before_binding(self):
        b=self.create();p=b.prepare_fixture()
        self.assertEqual(p['pid'],b.process.pid);self.assertEqual(p['birth'],b._birth())
        self.assertFalse(p['has_window']);self.assertIsNone(b.channel)
        time.sleep(.04);self.assertEqual(b.status()['phase'],'PREPARED')
        self.assertFalse(b.status()['binding_dispatched']);self.assertIsNone(b.status()['stage'])
        with self.assertRaises(VisualError):b.prepare_fixture()
    def test_stage_exact_parts_binding_and_actual_session_identity_stays_noncomplete(self):
        b=self.create();request=self.request(b);parts=self.f.j.verified_parts()
        receipt=b.bootstrap(request,parts);ep=receipt.channel.endpoint
        self.assertEqual(ep.attempt.hex(),request.binding.context.attempt)
        self.assertEqual(ep.intent.hex(),request.binding.intent)
        self.assertEqual(ep.server_pid,request.binding.target.pid)
        self.assertEqual(ep.server_birth,request.binding.target.birth)
        self.assertEqual(receipt.stage_manifest_json,canonical(self.f.g.identity['manifest']))
        stage=Path(b.status()['stage']);ready=json.loads((stage/'stage-ready.json').read_bytes())
        self.assertEqual(receipt.stage_receipt_sha256,digest(ready))
        for name,raw in parts.items():self.assertEqual((stage/name).read_bytes(),raw)
        self.assertEqual((stage/'native'/TARGET).read_bytes(),parts['world.s14'])
        once=json.loads((stage/'stage-once.json').read_bytes())
        self.assertEqual(once['binding'],asdict(request.binding))
        self.assertEqual(receipt.channel.snapshot().fields['armed'],0)
        receipt.channel.arm_once();end=time.monotonic()+4
        while True:
            report=receipt.channel.snapshot()
            if report.fields['identity_ready'] or time.monotonic()>=end:break
            time.sleep(.01)
        self.assertEqual(report.fields['identity_ready'],1)
        self.assertEqual(report.fields['bytes_ready'],1)
        self.assertEqual(report.fields['lifecycle_ready'],1)
        self.assertFalse(report.progress()['native_load_complete'])
        self.assertEqual(report.fields['capabilities'],0)
        secret=ep.secret.hex().encode()
        for file in stage.rglob('*'):
            if file.is_file():self.assertNotIn(secret,file.read_bytes(),'Secret leaked into staged evidence')
        self.assertNotIn(ep.secret.hex(),json.dumps(b.status()))
        with self.assertRaises(VisualError):b.bootstrap(request,parts)
    def test_bad_binary_approval_rejected_without_child(self):
        wrong=replace(self.profile,session_binary_sha256='0'*64)
        b=self.create(profile=wrong,approved_fixture_sha256='0'*64)
        with self.assertRaises(VisualError):b.prepare_fixture()
        self.assertIsNone(b.process)
    def test_corrupt_part_rejected_before_stage_or_bind(self):
        b=self.create();r=self.request(b);parts=self.f.j.verified_parts()
        parts['world.s14']=parts['world.s14'][:-1]+bytes([parts['world.s14'][-1]^1])
        with self.assertRaises(VisualError):b.bootstrap(r,parts)
        self.assertIsNone(b.status()['stage']);self.assertFalse(b.status()['binding_dispatched'])
        with self.assertRaises(VisualError):b.bootstrap(r,self.f.j.verified_parts())
    def test_foreign_pid_birth_intent_lease_epoch_and_manifest_fail_closed(self):
        b=self.create();r=self.request(b);parts=self.f.j.verified_parts()
        variants=[replace(r.binding,target=replace(r.binding.target,pid=r.binding.target.pid+1)),
            replace(r.binding,target=replace(r.binding.target,birth=r.binding.target.birth+1)),
            replace(r.binding,intent='0'*32),replace(r.binding,lease=None),
            replace(r.binding,epoch='0'*32),replace(r.binding,manifest_sha256='0'*64)]
        for binding in variants:
            with self.subTest(binding_field='redacted'),self.assertRaises(VisualError):
                b._check_request(replace(r,binding=binding),parts)
        self.assertFalse(b.status()['binding_dispatched'])
    def test_existing_attempt_cannot_overwrite_or_bind_new_child(self):
        b=self.create();r=self.request(b);receipt=b.bootstrap(r,self.f.j.verified_parts())
        stage=Path(b.status()['stage']);saved=(stage/'stage-once.json').read_bytes()
        other=self.create();new=self.request(other,attempt=r.binding.context.attempt)
        with self.assertRaises(FileExistsError):other.bootstrap(new,self.f.j.verified_parts())
        self.assertFalse(other.status()['binding_dispatched'])
        self.assertEqual((stage/'stage-once.json').read_bytes(),saved)
        self.assertEqual(receipt.channel.snapshot().fields['armed'],0)
    def test_child_death_before_binding_never_restarts_or_arms(self):
        b=self.create();r=self.request(b);pid=b.process.pid
        b.process.terminate();b.process.wait(timeout=5)
        with self.assertRaises(VisualError):b.bootstrap(r,self.f.j.verified_parts())
        self.assertEqual(b.process.pid,pid);self.assertIsNone(b.channel)
        self.assertFalse(b.status()['binding_dispatched'])
    def test_write_failure_after_flushed_once_retains_claim_and_never_binds(self):
        b=self.create();r=self.request(b);write=b._write_new
        def fail_world(path,raw):
            if path.name=='world.s14':raise OSError('Injected workspace write failure')
            write(path,raw)
        b._write_new=fail_world
        with self.assertRaises(OSError):b.bootstrap(r,self.f.j.verified_parts())
        stage=Path(b.status()['stage'])
        self.assertTrue((stage/'stage-once.json').is_file())
        self.assertFalse((stage/'stage-ready.json').exists())
        self.assertFalse((stage/'native').exists())
        self.assertFalse(b.status()['binding_dispatched'])
        b._write_new=write
        with self.assertRaises(VisualError):b.bootstrap(r,self.f.j.verified_parts())
    def test_explicit_cleanup_retains_stage_once_and_rejects_reuse(self):
        b=self.create();r=self.request(b);b.bootstrap(r,self.f.j.verified_parts())
        stage=Path(b.status()['stage']);before=(stage/'stage-once.json').read_bytes()
        result=b.close();self.assertTrue(result['closed']);self.assertIsNotNone(result['exit_code'])
        self.assertEqual((stage/'stage-once.json').read_bytes(),before)
        self.assertEqual(b.close(),result)
        with self.assertRaises(VisualError):b.bootstrap(r,self.f.j.verified_parts())
    def test_real_controller_port_bootstrap_pipe_remains_intent_without_world_provider(self):
        b=self.create();p=b.prepare_fixture();native=InitialOnlyFixtureEvidence(self.f)
        port=SessionNativePort(self.f.g,approved_profile=self.profile,approved_profile_sha256=self.profile.sha256,
            native_provider=native,bootstrap_provider=b,allow_fixture_providers=True)
        t=FakeTransport();client=VisualClient(t,session='1'*32,timeout=2)
        self.addCleanup(lambda:client.terminate_helper(accept_cover_loss=True) if not client._closed else None)
        bridge=GateVisualBridge(client,evidence_provider=fixture_evidence,allow_fixture_evidence=True)
        flow=GuestTransition(self.f.g,bridge,port,allow_fixture_native=True)
        self.assertEqual(flow.start(replace(BINDING,pid=p['pid'],birth=p['birth']))['phase'],'LOADING')
        end=time.monotonic()+4
        while True:
            status=flow.poll()
            if port.last_session.fields['identity_ready'] or time.monotonic()>=end:break
            time.sleep(.01)
        self.assertEqual(port.last_session.fields['identity_ready'],1)
        self.assertEqual(status['phase'],'LOADING');self.assertFalse(status['accept_planning_intents'])
        self.assertEqual(self.f.j.status()['status'],'INTENT');self.assertFalse(port.completed)
        self.assertIn('missing_real_world_proof',native.calls)
        self.assertNotIn('UNEXPECTED_RELEASE',native.calls)
        self.assertNotIn('reveal',[req['op'] for req in t.sent])
        self.assertEqual(b.channel.endpoint.intent.hex(),flow.permit['intent'])


class Result(unittest.TextTestResult):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.cases=[]
    def addSuccess(self,test):super().addSuccess(test);self.cases.append({'case':test._testMethodName,'passed':True})
    def addFailure(self,test,err):super().addFailure(test,err);self.cases.append({'case':test._testMethodName,'passed':False})
    def addError(self,test,err):super().addError(test,err);self.cases.append({'case':test._testMethodName,'passed':False})


if __name__=='__main__':
    initial={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in SOURCES}
    result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(unittest.defaultTestLoader.loadTestsFromTestCase(BootstrapTests))
    current={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in SOURCES}
    unchanged=initial==current and hashlib.sha256(EXE.read_bytes()).hexdigest()==APPROVED
    folder=HERE/'checkpoint_test_bootstrap_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    report={'schema':'san14.fixture-bootstrap-tests.v1','result':'PASS' if result.wasSuccessful() and unchanged else 'FAIL',
        'tests_run':result.testsRun,'cases':result.cases,'source_sha256':current,
        'fixture_binary_sha256':APPROVED,'sources_unchanged_during_tests':unchanged,
        'provenance':FIXTURE,'game_access':False,'steam_access':False,'windows_created_or_captured':False,
        'own_processes_only':True,'secrets_logged':False,'actual_session_ipc':True,
        'native_game_function_bodies':'SYNTHETIC','full_world_verified':False,'input_barrier_verified':False}
    (folder/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(folder/'result.json'),'result':report['result'],'tests_run':result.testsRun}))
    raise SystemExit(0 if report['result']=='PASS' else 1)
