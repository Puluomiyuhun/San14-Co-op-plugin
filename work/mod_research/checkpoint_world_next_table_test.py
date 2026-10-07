"""Strict versioned full-slot CForceData schema and actual VM evidence checks."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import unittest

from checkpoint_world_next_table_schema import *
from checkpoint_world_next_table_native import source_records

P=Path(__file__).resolve().parent
NATIVE=P/'checkpoint_world_next_table_runs'/'20261007-131837-618852'/'result.json'
PROFILE=dict(game_build_sha256=GAME_SHA256,archive_version=ARCHIVE_VERSION,transform_flag=0)


class ForceTableTests(unittest.TestCase):
    def setUp(self):
        self.records=source_records()
        self.payload=validate_payload_records(self.records,**PROFILE)

    def test_actual_native_evidence_hashes_and_all_field_traces(self):
        report=json.loads(NATIVE.read_text(encoding='utf8'))
        self.assertEqual(report['result'],'PASS');self.assertEqual(len(report['cases']),11)
        self.assertTrue(all(row['passed'] for row in report['cases']))
        for name,expected in report['source_sha256'].items():
            self.assertEqual(hashlib.sha256((P/name).read_bytes()).hexdigest(),expected,name)
        frame=(NATIVE.parent/'synthetic-force-table-frame.bin').read_bytes()
        self.assertEqual(frame,self.payload.frame())
        self.assertEqual(hashlib.sha256(frame).hexdigest(),report['native_table_frame_sha256'])
        self.assertEqual(self.payload.digest,report['payload_schema']['payload_sha256'])
        for case in report['cases'][:4]:
            self.assertTrue(case['all_field_traces_match_schema'])
            self.assertEqual(case['serializer_calls'],52)
            self.assertEqual(case['stream_reads']+case['stream_writes'],13418)
            self.assertEqual(tuple(map(tuple,case['first_record_actual_fields'])),FIELD_LAYOUT)
            self.assertFalse(case['external_stubs']);self.assertFalse(case['unclassified_stream_calls'])

    def test_native_order_all_slots_and_sparse_memory_mapping(self):
        unordered=dict(reversed(list(self.records.items())))
        self.assertEqual(validate_payload_records(unordered,**PROFILE),self.payload)
        self.assertEqual(decode_native_table_frame(self.payload.frame(),**PROFILE),self.payload)
        self.assertEqual(RECORD_SIZE,378);self.assertEqual(FRAME_SIZE,19664)
        self.assertEqual(len(FIELD_LAYOUT),258)
        self.assertEqual(len(self.payload.records()),52)
        mapped=self.payload.memory_segments()['force_slot:26']
        self.assertEqual(tuple((o,len(b)) for o,b in mapped),FIELD_LAYOUT)
        self.assertEqual(b''.join(b for _,b in mapped),self.records[26])
        self.assertLess(SERIALIZED_OFFSETS.index(0x179),SERIALIZED_OFFSETS.index(0x178))
        self.assertGreater(SERIALIZED_OFFSETS.index(0x12),SERIALIZED_OFFSETS.index(0x16C))
        for g in range(5):self.assertNotIn(0x54+g*0x1E+0x1D,SERIALIZED_OFFSETS)

    def test_missing_extra_bool_slots_and_wrong_width_rejected(self):
        for slot in (0,26,51):
            changed=dict(self.records);del changed[slot]
            with self.subTest(missing=slot),self.assertRaises(CoverageError):validate_payload_records(changed,**PROFILE)
        for key in (52,-1,True,'0'):
            changed=dict(self.records)
            if key is True:del changed[1]  # Preserve a real bool key; True aliases int1 in dict updates.
            changed[key]=bytes(RECORD_SIZE)
            with self.subTest(key=key),self.assertRaises(CoverageError):validate_payload_records(changed,**PROFILE)
        for raw in (bytes(RECORD_SIZE-1),bytes(RECORD_SIZE+1),bytearray(RECORD_SIZE),None):
            changed=dict(self.records);changed[0]=raw
            with self.subTest(width=type(raw)),self.assertRaises(CoverageError):validate_payload_records(changed,**PROFILE)

    def test_every_serialized_byte_including_nested_and_final_slot_changes(self):
        for slot,positions in ((0,(0,RECORD_SIZE-1)),(26,range(RECORD_SIZE)),(51,(0,RECORD_SIZE-1))):
            for at in positions:
                changed=dict(self.records);raw=bytearray(changed[slot]);raw[at]^=0x80;changed[slot]=bytes(raw)
                actual=validate_payload_records(changed,**PROFILE)
                diff=compare_payloads(self.payload,actual)
                with self.subTest(slot=slot,byte=at):
                    self.assertFalse(diff['observed_table_equal'])
                    self.assertEqual(diff['changed_records'],[dict(physical_slot=slot,
                        changed_bytes=[dict(object_offset=SERIALIZED_OFFSETS[at],before=self.records[slot][at],after=raw[at])])])
                    self.assertNotEqual(self.payload.digest,actual.digest)

    def test_frame_count_tag_extent_never_accept_intersection_or_trailing_bytes(self):
        frame=self.payload.frame()
        bad=(struct.pack('<II',0,TABLE_TAG),struct.pack('<I',51)+frame[4:],
             struct.pack('<I',53)+frame[4:],frame[:-1],frame+b'\0',frame[:-4]+struct.pack('<I',5))
        for index,value in enumerate(bad):
            with self.subTest(case=index),self.assertRaises(CoverageError):decode_native_table_frame(value,**PROFILE)

    def test_version_is_mandatory_same_size_old_branch_rejected(self):
        report=json.loads(NATIVE.read_text(encoding='utf8'))
        old=report['cases'][4]
        self.assertEqual(old['case'],'native_version91_same_size_is_not_v92_schema')
        self.assertEqual(old['changed_field_offsets'],[0x178,0x179])
        self.assertEqual(old['write']['buffer_bytes_consumed'],FRAME_SIZE)
        with self.assertRaises(TypeError):decode_native_table_frame(self.payload.frame(),game_build_sha256=GAME_SHA256,transform_flag=0)
        for version in (91,93,True,'92',None):
            with self.subTest(version=version),self.assertRaises(CoverageError):
                decode_native_table_frame(self.payload.frame(),game_build_sha256=GAME_SHA256,archive_version=version,transform_flag=0)
        for changes in ({'game_build_sha256':'0'*64},{'archive_mode':2},{'archive_mode':True},
                        {'auxiliary_flag':1},{'auxiliary_flag':False}):
            with self.subTest(changes=changes),self.assertRaises(CoverageError):
                validate_payload_records(self.records,**{**PROFILE,**changes})

    def test_transform_is_explicit_strict_int_zero_and_both_native_paths_reach_helper(self):
        missing={k:v for k,v in PROFILE.items() if k!='transform_flag'}
        with self.assertRaises(TypeError):validate_payload_records(self.records,**missing)
        with self.assertRaises(TypeError):decode_native_table_frame(self.payload.frame(),**missing)
        for value in (1,-1,True,False,0.0,'0',None):
            args={**PROFILE,'transform_flag':value}
            with self.subTest(transform=value),self.assertRaises(CoverageError):validate_payload_records(self.records,**args)
            with self.subTest(transform_decode=value),self.assertRaises(CoverageError):decode_native_table_frame(self.payload.frame(),**args)
        cases=json.loads(NATIVE.read_text(encoding='utf8'))['cases'][-2:]
        self.assertEqual([x['mode'] for x in cases],[0,1])
        for case in cases:
            self.assertEqual(case['transform_flag'],1)
            self.assertEqual(case['transform_calls'],1)
            self.assertFalse(case['reached_parent_next_callsite'])
        self.assertTrue(self.payload.evidence()['stream_transform_requires_external_provenance'])

    def test_equal_table_never_grants_world_provenance_or_permissions(self):
        diff=compare_payloads(self.payload,self.payload)
        self.assertTrue(diff['observed_table_equal'])
        self.assertEqual(diff['compared_physical_slots'],52)
        self.assertEqual(diff['compared_payload_bytes'],19656)
        for proof in (diff,self.payload.evidence()):
            for name in ('full_world_verified','current_world_provenance_verified','authorize_load_or_ready'):
                self.assertIs(proof[name],False)
        with self.assertRaises(CoverageError):ForceTablePayload(bytes(TABLE_PAYLOAD_SIZE-1))


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ForceTableTests))
    folder=P/'checkpoint_world_next_table_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    report=dict(schema='san14.cforcedata.schema-tests.v1',result='PASS' if result.wasSuccessful() else 'FAIL',
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),game_access=False,
        steam_access=False,full_world_verified=False,native_report=str(NATIVE),
        native_report_sha256=hashlib.sha256(NATIVE.read_bytes()).hexdigest(),
        source_sha256={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in
            ('checkpoint_world_next_table_schema.py','checkpoint_world_next_table_native.py','checkpoint_world_next_table_test.py')})
    path=folder/'result.json';path.write_text(json.dumps(report,indent=2),encoding='utf8');print(path)
    raise SystemExit(not result.wasSuccessful())
