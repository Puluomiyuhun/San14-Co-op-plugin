"""Actual owned child + Session bridges/planning observer, synthetic game bodies."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import secrets
import time
import unittest

from checkpoint_guest_runtime_fixture_client import *

ARCHIVE=HERE/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
APPROVED=hashlib.sha256(EXE.read_bytes()).hexdigest()
SOURCES=['checkpoint_guest_runtime_fixture.cpp','checkpoint_guest_runtime_fixture_control.inc',
    'checkpoint_guest_runtime_fixture_client.py','checkpoint_guest_runtime_fixture_make.py',
    'checkpoint_guest_runtime_fixture_build.cmd','checkpoint_guest_runtime_fixture_test.py',
    'checkpoint_planning_return_observer_session_fixture.cpp','checkpoint_guest_native_session_fixture.asm',
    'checkpoint_load_input_boundary_fixture_layout.h','checkpoint_push_bridge.h']
for stem in ('checkpoint_guest_native_session','checkpoint_planning_return_observer','checkpoint_load_worker_bridge',
    'checkpoint_load_dispatch_bridge','native_storage_read_core','checkpoint_cc_load_observer',
    'checkpoint_cc_load_lifecycle','checkpoint_title_identity_adapter','checkpoint_identity_pair_commit',
    'checkpoint_load_request_commit','checkpoint_load_input_boundary','checkpoint_load_hook_set'):
    SOURCES.extend((stem+'.h',stem+'.cpp'))
SOURCES.extend(('checkpoint_load_worker_bridge.asm','checkpoint_load_dispatch_bridge.asm'))


class RuntimeTests(unittest.TestCase):
    reports=[]
    def fixture(self,case='success-new',**kwargs):
        f=RuntimeFixture(approved_exe_sha256=APPROVED,case=case,**kwargs)
        self.addCleanup(self.cleanup,f);f.prepare();return f
    def cleanup(self,f):
        r=f.close()
        self.assertTrue(r['closed']);self.assertIsNotNone(r['exit_code'])
        self.assertEqual(r['errors'],[])
    def start(self,case='success-new',staged=True):
        f=self.fixture(case);a,i=secrets.token_hex(16),secrets.token_hex(16)
        f.bind(a,i,world_bytes=ARCHIVE.read_bytes() if staged else None);f.arm_once();r=f.wait_result()
        self.reports.append(r);return f,r
    def test_actual_staged_bytes_session_to_new_user_planning_and_no_authority(self):
        f,r=self.start()
        self.assertTrue(r['fixture_checks_passed']);self.assertTrue(r['native_binding_matches'])
        self.assertTrue(r['planning_upstream_links_match'])
        for k in ('bytesReady','lifecycleReady','identityReady','planningBoundaryObserved','cas_attempts',
                  'old_user_calls','new_user_calls','user_controller_calls','load_worker_calls','worker_join_calls'):
            self.assertEqual(r[k],1,k)
        self.assertEqual(r['preflight_read_calls'],2);self.assertEqual(r['load_update_calls'],4)
        self.assertEqual(r['consumed_world_source'],'verified_workspace_stage')
        self.assertEqual(r['actual_archive_read_sha256'],SHA);self.assertEqual(r['actual_archive_read_bytes'],SIZE)
        self.assertEqual(r['identity_force'],2);self.assertEqual(r['identity_ruler'],952)
        self.assertEqual(int(r['planning_native_rax']),0xFEDCBA9876543210)
        for k in ('session_active_dispatch','session_active_worker','session_active_read','planning_inflight','dispatch_unpaired'):
            self.assertEqual(r[k],0,k)
        for k in ('fullWorldVerified','inputExclusionProven','pixelPresentationProven','native_gameplay_enabled'):
            self.assertIs(r[k],False)
        run=HERE/'checkpoint_guest_runtime_fixture_runs'/f.binding['attempt']
        self.assertTrue((run/'arm-once.json').is_file())
        self.assertEqual((run/'svdexccSC03.s14').read_bytes(),ARCHIVE.read_bytes())
        self.assertIsNone(f.process.poll()) # held until explicit cleanup
    def test_two_attempts_derive_distinct_actual_native_tokens(self):
        a,r=self.start();b,s=self.start(staged=False)
        self.assertNotEqual(a.identity['pid'],b.identity['pid'])
        self.assertNotEqual(r['native_attempt'],s['native_attempt']);self.assertNotEqual(r['observer_epoch'],s['observer_epoch'])
        self.assertEqual(s['consumed_world_source'],'fixed_archive_copy')
        for f,row in ((a,r),(b,s)):
            expected=binding_values(row['attempt'],row['intent'])
            self.assertEqual(f.binding,expected);self.assertTrue(row['native_binding_matches'])
    def test_duplicate_arm_rejected_in_python_and_actual_child(self):
        f,r=self.start()
        with self.assertRaises(RuntimeFixtureError):f.arm_once()
        f._send('ARM '+f.binding['attempt']+' '+f.binding['intent'])
        error=f._next();self.assertEqual(error['event'],'ERROR');self.assertEqual(error['error'],'ARM_ALREADY_CONSUMED')
        self.assertEqual(r['cas_attempts'],1);self.assertEqual(r['new_user_calls'],1)
    def test_lost_result_never_rearms_and_explicit_close_drains_late_reply(self):
        f=self.fixture();f.bind(secrets.token_hex(16),secrets.token_hex(16),world_bytes=ARCHIVE.read_bytes());f.arm_once()
        original=f._next
        def lost(_=None):raise RuntimeFixtureError('Injected result timeout after ARM publication')
        f._next=lost
        with self.assertRaises(RuntimeFixtureError):f.wait_result()
        f._next=original
        with self.assertRaises(RuntimeFixtureError):f.arm_once()
        with self.assertRaises(RuntimeFixtureError):f.wait_result()
        self.assertTrue(f.arm_consumed);self.assertEqual(f.close()['errors'],[])
    def test_report_screen_and_epoch_rejection_never_claim_planning(self):
        for case in ('report-state','epoch-after','stale-attempt'):
            with self.subTest(case=case):
                _,r=self.start(case);self.assertTrue(r['fixture_checks_passed'])
                self.assertEqual(r['identityReady'],1);self.assertEqual(r['planningBoundaryObserved'],0)
                self.assertNotEqual(r['planning_error'],0)
                self.assertFalse(r['fullWorldVerified'])
    def test_read_corruption_blocks_upstream_and_new_user_exception_keeps_unpaired(self):
        _,bad=self.start('actual-byte-mismatch')
        self.assertTrue(bad['fixture_checks_passed']);self.assertEqual(bad['bytesReady'],0)
        self.assertEqual(bad['identityReady'],0);self.assertEqual(bad['planningBoundaryObserved'],0)
        self.assertEqual((bad['identity_force'],bad['identity_ruler']),(12,666))
        _,exc=self.start('user-exception')
        self.assertTrue(exc['fixture_checks_passed']);self.assertEqual(exc['identityReady'],1)
        self.assertEqual(exc['planningBoundaryObserved'],0);self.assertEqual(exc['planning_inflight'],1)
        self.assertEqual(exc['session_active_dispatch'],1)
    def test_stop_after_publication_preserves_observation_without_authority(self):
        _,r=self.start('stop-after-cas')
        self.assertTrue(r['fixture_checks_passed']);self.assertEqual(r['session_state'],10)
        self.assertEqual(r['planningBoundaryObserved'],1);self.assertFalse(r['fullWorldVerified'])
    def test_wrong_received_bytes_rejected_before_binding_or_arm(self):
        f=self.fixture();a,i=secrets.token_hex(16),secrets.token_hex(16)
        with self.assertRaises(RuntimeFixtureError):f.bind(a,i,world_bytes=b'bad checkpoint')
        self.assertFalse(f.arm_consumed);self.assertIsNone(f.binding)
        self.assertFalse((HERE/'checkpoint_guest_runtime_fixture_runs'/a).exists())
    def test_child_rejects_existing_bad_stage_instead_of_fallback(self):
        f=self.fixture();a,i=secrets.token_hex(16),secrets.token_hex(16)
        f._stage_world(a,i,ARCHIVE.read_bytes())
        (f.stage/'stage-ready.json').write_bytes(b'{}')
        with self.assertRaises(RuntimeFixtureError):f.bind(a,i)
        f.process.wait(timeout=5)
        self.assertEqual(f.process.returncode,4);self.assertFalse(f.arm_consumed)
        self.assertFalse((HERE/'checkpoint_guest_runtime_fixture_runs'/a/'arm-once.json').exists())
    def test_same_attempt_directory_cannot_run_second_session(self):
        first,r=self.start();second=self.fixture()
        with self.assertRaises(RuntimeFixtureError):second.bind(r['attempt'],r['intent'])
        second.process.wait(timeout=5);self.assertEqual(second.process.returncode,4)
        self.assertFalse(second.arm_consumed)


if __name__=='__main__':
    source_before={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeTests))
    source_after={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    unchanged=source_before==source_after and hashlib.sha256(EXE.read_bytes()).hexdigest()==APPROVED
    folder=HERE/'checkpoint_guest_runtime_fixture_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    report={'schema':'san14.guest-runtime-fixture-tests.v1','result':'PASS' if result.wasSuccessful() and unchanged else 'FAIL',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'source_sha256':source_after,'fixture_binary_sha256':APPROVED,'sources_unchanged':unchanged,
        'runtime_reports':RuntimeTests.reports,'game_access':False,'steam_access':False,'windows_accessed':False,
        'own_processes_only':True,'upstream_receipts_fabricated':False,'native_game_code_executed':False,
        'full_world_verified':False,'input_barrier_verified':False,'playable_mod':False}
    (folder/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(folder/'result.json'),'result':report['result'],'tests_run':result.testsRun}))
    raise SystemExit(0 if report['result']=='PASS' else 1)
