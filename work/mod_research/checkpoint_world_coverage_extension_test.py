"""Complete CObjectData slot/payload coverage and damaged-frame rejection."""
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest

import checkpoint_world_coverage_extension_schema as s

P = Path(__file__).resolve().parent
NATIVE_REPORT = P/'checkpoint_world_coverage_extension_runs/20261007-124704-645791/result.json'


class CoverageExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = (NATIVE_REPORT.parent/'synthetic-table-frame.bin').read_bytes()
        cls.table = s.decode_native_table_frame(cls.frame, game_build_sha256=s.GAME_SHA256)
        cls.rows = {i: cls.table.ordered_payload[i*8:(i+1)*8] for i in range(s.SLOT_COUNT)}

    def test_actual_machine_code_report_and_stream_frame_match(self):
        report = json.loads(NATIVE_REPORT.read_text(encoding='utf-8'))
        self.assertEqual(report['result'], 'PASS')
        self.assertEqual(len(report['cases']), 6)
        self.assertTrue(all(c['passed'] for c in report['cases']))
        self.assertEqual(hashlib.sha256(self.frame).hexdigest(), report['native_table_frame_sha256'])
        for name, sha in report['source_sha256'].items():
            self.assertEqual(hashlib.sha256((P/name).read_bytes()).hexdigest(), sha)
        self.assertEqual(report['payload_schema'], self.table.evidence())
        self.assertFalse(report['native_stream_functions_stubbed'])
        self.assertFalse(report['actual_game_table_captured'])

    def test_all_slots_and_fields_survive_roundtrip_in_physical_order(self):
        table = s.validate_payload_records(dict(reversed(list(self.rows.items()))), game_build_sha256=s.GAME_SHA256)
        self.assertEqual(table, self.table)
        self.assertEqual(table.frame(), self.frame)
        self.assertEqual(len(table.records()), 3001)
        self.assertEqual(len(table.ordered_payload), 24008)
        self.assertEqual(list(table.records()), [f'object_slot:{i}' for i in range(3001)])

    def test_missing_sentinel_middle_or_last_and_extra_slot_rejected(self):
        for missing in (0, 1500, 3000):
            rows = dict(self.rows); del rows[missing]
            with self.subTest(missing=missing), self.assertRaises(s.CoverageError):
                s.validate_payload_records(rows, game_build_sha256=s.GAME_SHA256)
        rows = dict(self.rows); rows[3001] = b'12345678'
        with self.assertRaises(s.CoverageError):s.validate_payload_records(rows, game_build_sha256=s.GAME_SHA256)
        rows = dict(self.rows); rows[False] = rows.pop(0)
        with self.assertRaises(s.CoverageError):s.validate_payload_records(rows, game_build_sha256=s.GAME_SHA256)

    def test_no_field_is_ignored_including_nondurability_and_last_slot(self):
        for slot in (0, 1500, 3000):
            for offset in range(8):
                rows = dict(self.rows); raw = bytearray(rows[slot]); raw[offset] ^= 1; rows[slot] = bytes(raw)
                other = s.validate_payload_records(rows, game_build_sha256=s.GAME_SHA256)
                diff = s.compare_payloads(self.table, other)
                with self.subTest(slot=slot, offset=offset):
                    self.assertNotEqual(self.table.digest, other.digest)
                    self.assertFalse(diff['all_this_table_payloads_equal'])
                    self.assertEqual(diff['changed_slots'], [{'physical_slot':slot,'changed_object_offsets':[0x10+offset]}])
                    self.assertFalse(diff['full_world_verified'])
                    self.assertFalse(diff['authorize_load_or_ready'])

    def test_count_zero_oversize_truncation_trailing_bytes_and_wrong_tag_rejected(self):
        cases = [struct.pack('<II', 0, 8), struct.pack('<I', 3002)+self.frame[4:],
                 struct.pack('<I', 3000)+self.frame[4:], self.frame[:-1], self.frame+b'\0',
                 self.frame[:-4]+struct.pack('<I',9)]
        for frame in cases:
            with self.subTest(length=len(frame)), self.assertRaises(s.CoverageError):
                s.decode_native_table_frame(frame, game_build_sha256=s.GAME_SHA256)

    def test_wrong_record_extent_mode_auxiliary_and_build_rejected(self):
        for raw in (b'x'*7, b'x'*9, bytearray(8)):
            rows = dict(self.rows); rows[2000] = raw
            with self.assertRaises(s.CoverageError):s.validate_payload_records(rows, game_build_sha256=s.GAME_SHA256)
        for kwargs in ({'game_build_sha256':'0'*64}, {'game_build_sha256':s.GAME_SHA256,'archive_mode':2},
                       {'game_build_sha256':s.GAME_SHA256,'archive_mode':False},
                       {'game_build_sha256':s.GAME_SHA256,'auxiliary_flag':1}):
            with self.assertRaises(s.CoverageError):s.validate_payload_records(self.rows, **kwargs)

    def test_all_equal_table_never_claims_fullworld_or_current_capture(self):
        result = s.compare_payloads(self.table, self.table)
        self.assertTrue(result['all_this_table_payloads_equal'])
        self.assertEqual(result['compared_slots'], 3001)
        self.assertFalse(result['full_world_verified'])
        self.assertFalse(result['authorize_load_or_ready'])
        e = self.table.evidence()
        self.assertFalse(e['current_world_provenance_verified'])
        self.assertFalse(e['all_object_business_semantics_known'])
        self.assertFalse(e['full_world_verified'])


def main():
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(CoverageExtensionTests))
    folder = P/'checkpoint_world_coverage_extension_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True,exist_ok=False)
    sources = ('checkpoint_world_coverage_extension_schema.py','checkpoint_world_coverage_extension_native.py',
               'checkpoint_world_coverage_extension_test.py','checkpoint_world_coverage_extension_notes.txt')
    report = {'schema':'san14.cobjectdata.coverage-fixtures.v1','result':'PASS' if result.wasSuccessful() else 'FAIL',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'native_report':str(NATIVE_REPORT),'native_report_sha256':hashlib.sha256(NATIVE_REPORT.read_bytes()).hexdigest(),
        'source_sha256':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in sources},
        'test_output':stream.getvalue(),'game_access':False,'full_world_verified':False,
        'actual_game_table_captured':False,'new_serialized_payload_schema_bytes':24008}
    path=folder/'result.json';path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(stream.getvalue());print(path)
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
