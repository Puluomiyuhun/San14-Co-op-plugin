"""Read saved workspace evidence once; all adversarial tests mutate memory only."""
from datetime import datetime
from pathlib import Path
import copy
import json
import struct
import unittest

import checkpoint_push_export_receipt as receipt


class ReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=receipt.load_bundle()

    def case(self):return dict(self.original),copy.deepcopy(receipt.EXPECTED)

    def repin(self,bundle,expected):
        # Repin intentionally changed fixture bytes to exercise semantic checks,
        # not only the immutable real-artifact allowlist.
        expected['artifact_sha256']={k:receipt.sha(v) for k,v in bundle.items()}

    def edit_json(self,bundle,name,change):
        value=json.loads(bundle[name]);change(value)
        bundle[name]=(json.dumps(value,ensure_ascii=False)+'\n').encode()

    def test_actual_A_only_receipt_and_guest_refusal(self):
        bundle,expected=self.case();copy_before=dict(bundle)
        out=receipt.normalize(bundle,expected)
        self.assertEqual(bundle,copy_before)
        self.assertEqual(out['result'],'A_EXPORT_VERIFIED_GUEST_UNBOUND')
        self.assertTrue(out['local_archived_file_sha256_verified'])
        self.assertTrue(out['guest_contract_refusal']['rejected'])
        self.assertIsNone(out['B_binding'])
        for key in ('B_load_performed','load_authorized','formal_room_checkpoint_usable','full_world_verified','native_full_file_identity_verified','game_access_by_receipt_tool'):
            self.assertIs(out[key],False,key)
        source=out['source_fields_for_future_binding']
        for key in ('room_id','epoch','turn','last_command_seq','checkpoint_id','sequence'):
            self.assertNotIn(key,source)
        self.assertNotIn('nonce',source['attachment'])
        self.assertNotIn('new_commands_frozen',source['before']['planning'])
        self.assertNotIn('stable_samples',source['file'])
        self.assertEqual(out['trace_first_seen']['intent_created']['poll_index'],out['trace_first_seen']['queue_calls']['poll_index'])

    def test_missing_and_unpinned_evidence(self):
        for name in receipt.PINNED:
            with self.subTest(missing=name):
                bundle,expected=self.case();del bundle[name]
                with self.assertRaisesRegex(receipt.ReceiptError,'missing_or_extra_artifact'):receipt.normalize(bundle,expected)
        bundle,expected=self.case();bundle['result.json']+=b' '
        with self.assertRaisesRegex(receipt.ReceiptError,'artifact_hash_not_review_pinned'):receipt.normalize(bundle,expected)

    def test_stale_review_attachment(self):
        for key in ('pid','process_birth','base'):
            with self.subTest(key=key):
                bundle,expected=self.case();expected[key]+=1
                with self.assertRaisesRegex(receipt.ReceiptError,'stale_process_attachment_before'):receipt.normalize(bundle,expected)

    def test_worker_return_and_uncertainty_rejections(self):
        cases=[('status',4),('save_worker_started',0),('save_worker_joined',0),('save_native_success',0),
               ('save_finalizer_returned',0),('return_matched',0),('stop_requested',1),('pinned_user',0),('after_rng',0)]
        for key,value in cases:
            with self.subTest(key=key):
                bundle,expected=self.case();self.edit_json(bundle,'result.json',lambda r:r['adapter'].__setitem__(key,value));self.repin(bundle,expected)
                with self.assertRaisesRegex(receipt.ReceiptError,'worker_return_or_lifecycle_not_complete'):receipt.normalize(bundle,expected)

    def test_once_abi_attachment_slot_and_forensic_filename(self):
        cases=[(0,'<Q',0,'wrong_once_abi'),(8,'<I',1,'wrong_once_abi'),(12,'<I',999,'wrong_once_attachment'),
               (16,'<I',999,'wrong_once_attachment'),(20,'<I',34,'wrong_once_state')]
        for offset,fmt,value,reason in cases:
            with self.subTest(offset=offset):
                bundle,expected=self.case();raw=bytearray(bundle['checkpoint_push_once.intent']);struct.pack_into(fmt,raw,offset,value)
                bundle['checkpoint_push_once.intent']=bytes(raw);self.repin(bundle,expected)
                with self.assertRaisesRegex(receipt.ReceiptError,reason):receipt.normalize(bundle,expected)
        bundle,expected=self.case();raw=bytearray(bundle['checkpoint_push_once.intent']);raw[44:60]=b'mpckpt01.s14\0\0\0\0'
        bundle['checkpoint_push_once.intent']=bytes(raw);self.repin(bundle,expected)
        with self.assertRaisesRegex(receipt.ReceiptError,'forensic_or_wrong_once_filename'):receipt.normalize(bundle,expected)

    def test_mismatched_embedded_witness_and_missing_field(self):
        bundle,expected=self.case();self.edit_json(bundle,'after.json',lambda a:a.__setitem__('process_birth',1));self.repin(bundle,expected)
        with self.assertRaisesRegex(receipt.ReceiptError,'embedded_precheck_mismatch'):receipt.normalize(bundle,expected)
        bundle,expected=self.case();self.edit_json(bundle,'result.json',lambda r:r.pop('file'));self.repin(bundle,expected)
        with self.assertRaisesRegex(receipt.ReceiptError,'missing_or_malformed_evidence'):receipt.normalize(bundle,expected)

    def test_archived_file_corruption_and_wrong_digest(self):
        bundle,expected=self.case();bundle['mppush01.s14']=b'x'+bundle['mppush01.s14'][1:];self.repin(bundle,expected)
        with self.assertRaisesRegex(receipt.ReceiptError,'exported_file_hash_or_size'):receipt.normalize(bundle,expected)
        bundle,expected=self.case();expected['file_sha256']=receipt.guest_contract.FORENSIC_SHA
        with self.assertRaisesRegex(receipt.ReceiptError,'exported_file_hash_or_size'):receipt.normalize(bundle,expected)

    def test_source_business_change_rejected(self):
        bundle,expected=self.case()
        def change(value):
            k=next(iter(value['objects']['records']))
            old=value['objects']['records'][k]
            value['objects']['records'][k]=('ff' if old[:2]!='ff' else '00')+old[2:]
        self.edit_json(bundle,'known-after.json',change);self.repin(bundle,expected)
        with self.assertRaisesRegex(receipt.ReceiptError,'coverage_or_completion_evidence_mismatch'):receipt.normalize(bundle,expected)

    def test_trace_regression_and_wrong_final_report(self):
        bundle,expected=self.case();rows=[json.loads(x) for x in bundle['trace.jsonl'].splitlines()]
        rows[5]['adapter']['save_worker_started']=0
        bundle['trace.jsonl']=b'\n'.join(json.dumps(x).encode() for x in rows);self.repin(bundle,expected)
        with self.assertRaisesRegex(receipt.ReceiptError,'trace_flag_regression_save_worker_started'):receipt.normalize(bundle,expected)
        bundle,expected=self.case();rows=[json.loads(x) for x in bundle['trace.jsonl'].splitlines()];rows[-1]['adapter']['return_matched']=0
        bundle['trace.jsonl']=b'\n'.join(json.dumps(x).encode() for x in rows);self.repin(bundle,expected)
        with self.assertRaisesRegex(receipt.ReceiptError,'trace_final_report_mismatch'):receipt.normalize(bundle,expected)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReceiptTests))
    report={'result':'PASS' if result.wasSuccessful() else 'FAIL','unittest_methods':result.testsRun,
            'scope':'Pure receipt normalization/rejection over saved workspace bytes; no process/Steam access.',
            'game_access':False,'native_calls':False,'B_binding_created':False,
            'module_sha256':receipt.sha(Path(receipt.__file__).read_bytes()),'test_sha256':receipt.sha(Path(__file__).read_bytes())}
    path=receipt.ROOT/('checkpoint_push_export_receipt_tests_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with path.open('x',encoding='utf-8') as file:json.dump(report,file,indent=2)
    print(path)
    raise SystemExit(0 if result.wasSuccessful() else 1)
