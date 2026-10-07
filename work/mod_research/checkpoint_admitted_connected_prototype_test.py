"""Real loopback TLS and owned C++ child, including failed transfer/return paths."""
from datetime import datetime
from copy import deepcopy
import hashlib
import json
import unittest

from checkpoint_admitted_connected_prototype import HERE, run
from checkpoint_admitted_receipt import classify, ReceiptRejected

REPORTS = []


class ConnectedTests(unittest.TestCase):
    def execute(self, case):
        report, path = run(case)
        REPORTS.append({'case':case, 'path':str(path), 'report_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                        'result':report['result']})
        self.assertTrue(report['result'].startswith('PASS_'),report)
        self.assertTrue(report['owned_resources_closed'])
        self.assertEqual(report['cleanup_errors'],[])
        self.assertFalse(report['game_access'])
        self.assertFalse(report['full_world_verified'])
        self.assertFalse(report['native_gameplay_enabled'])
        return report

    def test_received_tls_bytes_reach_session_then_new_user_planning_without_room_disconnect(self):
        r = self.execute('success')
        self.assertEqual(r['result'],'PASS_EXPECTED_WAIT_FOR_GAME_PROVIDERS')
        self.assertTrue(r['transfer']['integrity_verified'])
        self.assertTrue(r['host_export_provenance_transferred'])
        self.assertEqual(r['host_export']['provenance'],'HISTORICAL_REVIEWED_ARCHIVE')
        self.assertFalse(r['host_export']['current_A_world_verified'])
        self.assertTrue(r['control_channels_preserved_after_download'])
        self.assertTrue(r['control_channels_preserved_after_native'])
        self.assertEqual(r['runtime_receipt']['consumed_world_source'],'verified_workspace_stage')
        self.assertEqual(r['runtime_receipt']['planningBoundaryObserved'],1)
        self.assertEqual(r['native_arm_count'],1)
        self.assertTrue(r['duplicate_arm_rejected'])
        self.assertTrue(r['reopened_journal_replay_rejected'])
        self.assertEqual(r['journal']['status'],'INTENT')
        self.assertEqual(r['coordinator']['phase'],'RECONCILING')
        self.assertEqual([p['stage'] for p in r['host_progress_history']],
            ['RECEIVING','STAGED','LOAD_REQUESTED','IDENTITY_RESTORED','WAITING_WORLD'])
        self.assertTrue(all(not p['grants_permission'] for p in r['host_progress_history']))
        receipt=r['runtime_receipt']
        binding={k:receipt[k] for k in ('attempt','intent','binding_sha256','native_attempt','observer_epoch')}
        args=dict(binding=binding,fixture_case='success-new',archive_sha256=r['archive_sha256'],
                  archive_size=receipt['actual_archive_read_bytes'])
        self.assertEqual(classify(receipt,**args)['outcome'],'WAITING_WORLD')
        # Mutate real child evidence: contradictory partial receipts must never
        # become IDENTITY_RESTORED merely because fixture_checks_passed was true.
        mutations={'intent':'0'*32,'admission_wired':False,'admission_prefetched':False,
            'admission_blocked':True,'admission_eligible':False,'admission_queue_calls':2,
            'admission_scope_finished':0,'session_error':1,'cas_published':True,
            'identity_force':12,'actual_archive_read_sha256':'0'*64,'request_intent_durable':False,
            'planning_upstream_links_match':False,'fullWorldVerified':True,
            'pixelPresentationProven':True,'consumed_world_source':'fixed_archive_copy',
            'admission_reentry':1,'old_user_calls':0,'user_controller_calls':0,
            'new_user_calls':0,'planning_before':0,'planning_after':0}
        for key,value in mutations.items():
            with self.subTest(invalid_receipt_field=key):
                bad=deepcopy(receipt);bad[key]=value
                with self.assertRaises(ReceiptRejected):classify(bad,**args)

    def test_changed_download_bytes_never_start_native_and_preserve_both_controls(self):
        r = self.execute('corrupt-transfer')
        self.assertFalse(r['runtime_started'])
        self.assertEqual(r['native_arm_count'],0)
        self.assertEqual(r['journal']['status'],'EMPTY')
        self.assertTrue(r['host_control_still_connected'])
        self.assertTrue(r['guest_control_still_connected'])
        self.assertEqual(r['host_progress_history'][-1]['reason'],'TRANSFER_FAILED')

    def test_guest_control_disconnect_revokes_already_authenticated_download(self):
        r = self.execute('control-disconnect')
        self.assertFalse(r['runtime_started'])
        self.assertEqual(r['native_arm_count'],0)
        self.assertEqual(r['journal']['status'],'EMPTY')
        self.assertTrue(r['host_control_still_connected'])

    def test_report_screen_after_loaded_identity_does_not_admit_next_period(self):
        r = self.execute('planning-not-ready')
        self.assertEqual(r['runtime_receipt']['identityReady'],1)
        self.assertEqual(r['runtime_receipt']['planningBoundaryObserved'],0)
        self.assertEqual(r['journal']['status'],'INTENT')
        self.assertTrue(r['reopened_journal_replay_rejected'])
        self.assertEqual(r['coordinator']['phase'],'RECONCILING')
        self.assertEqual(r['host_progress_history'][-1]['reason'],'WAITING_PLANNING')

    def test_disconnect_after_download_keeps_staged_bytes_without_starting_native(self):
        r = self.execute('disconnect-after-download')
        self.assertEqual(r['journal']['status'],'STAGED')
        self.assertFalse(r['runtime_started'])
        self.assertEqual(r['native_arm_count'],0)
        self.assertTrue(r['observed_disconnect_blocks_arm'])
        self.assertEqual(r['coordinator']['connected'],['A'])

    def test_disconnect_after_binding_keeps_intent_and_does_not_arm_child(self):
        r = self.execute('disconnect-after-bind')
        self.assertEqual(r['journal']['status'],'INTENT')
        self.assertTrue(r['runtime_started'])
        self.assertEqual(r['runtime_cleanup']['exit_code'],0)
        self.assertFalse(r['runtime_cleanup']['arm_consumed'])
        self.assertEqual(r['native_arm_count'],0)
        self.assertTrue(r['observed_disconnect_blocks_arm'])
        self.assertEqual(r['coordinator']['connected'],['A'])

    def test_lost_progress_reply_is_not_a_load_receipt_and_does_not_arm_or_retry(self):
        r=self.execute('progress-reply-lost')
        self.assertEqual(r['result'],'PASS_PROGRESS_REPLY_LOST_NO_ARM')
        self.assertEqual(r['host_observed_after_lost_reply']['stage'],'LOAD_REQUESTED')
        self.assertFalse(r['host_observed_after_lost_reply']['grants_permission'])
        self.assertTrue(r['guest_connection_fault']['request_may_have_been_sent'])
        self.assertFalse(r['guest_connection_fault']['automatically_retried'])
        self.assertFalse(r['runtime_cleanup']['arm_consumed'])
        self.assertEqual(r['native_arm_count'],0)
        self.assertEqual(r['journal']['status'],'INTENT')

    def check_player_input_rejection(self,case):
        r=self.execute(case)
        self.assertEqual(r['result'],'PASS_PLAYER_INPUT_BLOCKED_LOAD')
        self.assertEqual(r['runtime_classification']['outcome'],'ADMISSION_REJECTED')
        self.assertEqual(r['native_arm_count'],1)
        self.assertEqual(r['runtime_receipt']['cas_attempts'],0)
        self.assertEqual(r['runtime_receipt']['admission_queue_calls'],0)
        self.assertTrue(r['runtime_receipt']['admission_prefetched'])
        self.assertEqual(r['runtime_receipt']['identityReady'],0)
        self.assertEqual(r['journal']['status'],'INTENT')
        self.assertEqual(r['coordinator']['phase'],'RECONCILING')
        self.assertEqual([p['stage'] for p in r['host_progress_history']],
            ['RECEIVING','STAGED','LOAD_REQUESTED','HELD'])
        self.assertTrue(r['control_channels_preserved_after_native'])
        self.assertTrue(r['duplicate_arm_rejected'])

    def test_existing_player_input_blocks_actual_queue_and_cas_after_network_transfer(self):
        self.check_player_input_rejection('input-pending-at-entry')

    def test_input_appearing_inside_original_blocks_actual_queue_and_cas(self):
        self.check_player_input_rejection('input-pending-during-original')


if __name__=='__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ConnectedTests))
    folder = HERE/'checkpoint_admitted_connected_prototype_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    report = dict(schema='san14.admitted-connected-prototype-tests.v1',result='PASS' if result.wasSuccessful() else 'FAIL',
        tests_run=result.testsRun, failures=len(result.failures),errors=len(result.errors),runs=REPORTS,
        source_sha256={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in
            ('checkpoint_admitted_connected_prototype.py','checkpoint_admitted_connected_prototype_test.py','checkpoint_admitted_receipt.py',
             'checkpoint_room_artifacts.py','checkpoint_room_lifecycle.py','checkpoint_room_client.py','checkpoint_room_progress.py',
             'checkpoint_host_export_reader.py','checkpoint_admitted_runtime_client.py')},game_access=False)
    (folder/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(folder/'result.json')
    raise SystemExit(0 if result.wasSuccessful() else 1)
