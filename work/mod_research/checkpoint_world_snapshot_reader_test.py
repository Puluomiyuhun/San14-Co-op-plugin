"""Archive-only reader checks; imports no process/window/native reader."""
import ast
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import checkpoint_world_snapshot_reader as reader
from checkpoint_world_snapshot_reader import read_snapshot,read_binary_range,SnapshotError

HERE=Path(__file__).resolve().parent
SWITCH=HERE/'startup-switch-traces/20261006-124754-542123'
KNOWN=HERE/'checkpoint_push_runs/20261006-203111-687580/known-before.json'


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=HERE,prefix='world-reader-test-');self.addCleanup(self.tmp.cleanup)
    def changed(self,obj):
        p=Path(self.tmp.name)/'sample.json';p.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8');return p
    def source(self):return json.loads((SWITCH/'before.json').read_text(encoding='utf-8'))
    def test_real_switch_and_restore_retain_all_raw_ranges(self):
        for name,force in (('before.json',12),('after.json',2),('restored34.json',12)):
            p=SWITCH/name;raw=json.loads(p.read_text(encoding='utf-8'));s=read_snapshot(p)
            self.assertEqual(s.metadata['player']['force_id'],force)
            self.assertEqual(len(s.records),784);self.assertFalse(s.coverage['full_world_verified'])
            for key,hx in raw['records'].items():
                self.assertEqual(s.records[key][0].offset,0x10)
                self.assertEqual(s.records[key][0].data,bytes.fromhex(hx))
            self.assertIn('/objects/eligibility/tasks',s.fields)
            self.assertEqual(s.fields['/objects/eligibility/tasks'],raw['eligibility']['tasks'])
            self.assertIn('/objects/focused/critical_state/player/force_id',s.diagnostic_fields)
            self.assertFalse(s.metadata['normalization_applied'])
    def test_actual_all_hex_payload_offsets_tagged_hash_and_last_slot(self):
        s=read_snapshot(KNOWN);raw=json.loads(KNOWN.read_text(encoding='utf-8'))['tiles']
        self.assertEqual(len(s.records),49184);self.assertEqual(s.coverage['domains']['hex']['count'],48400)
        self.assertEqual([r.offset for r in s.records['hex:48399']],[0x14,0x16,0x18,0x19])
        self.assertEqual(b''.join(r.data for r in s.records['hex:48399']),bytes.fromhex(raw['ordered_payload_hex'])[-5:])
        self.assertFalse(s.coverage['atomic_world_verified'])
    def test_economy_and_transcript_preserve_extended_records_with_limitations(self):
        for name in ('economy-extended-after-restoration.json','economy-reader-memory-fixture.json'):
            s=read_snapshot(HERE/name)
            self.assertEqual(s.coverage['domains']['area']['count'],501)
            self.assertEqual(len(s.records['city:13'][0].data),0x158)
            self.assertEqual(len(s.records['force:2'][0].data),0x1C0)
            self.assertEqual(len(s.records['person:0'][0].data),0x1F0)
            self.assertEqual(len(s.records),1228);self.assertFalse(s.coverage['full_world_verified'])
            if 'memory' in name:self.assertFalse(s.metadata['transcript_expected_sample_recomputed'])
    def test_context_only_is_not_a_world_and_preserves_rank_fields(self):
        s=read_snapshot(SWITCH/'context-after.json')
        self.assertEqual(s.records,{})
        self.assertEqual(s.fields['/context/world_rank_derived_count'],1)
        self.assertEqual(s.metadata['player']['ruler_id'],952)
        self.assertEqual(s.coverage['status'],'INCOMPLETE')
        self.assertFalse(s.metadata['planning_ready_proved'])
    def test_unknown_player_leaves_remain_shared_in_all_four_formats(self):
        context=json.loads((SWITCH/'context-after.json').read_text(encoding='utf-8'))
        objects=self.source()
        tiles=json.loads(KNOWN.read_text(encoding='utf-8'))['tiles']
        economy=json.loads((HERE/'economy-extended-after-restoration.json').read_text(encoding='utf-8'))
        cases=[(context,[context['snapshot']['player']],['/context/snapshot/player']),
               (objects,[objects['focused']['critical_state']['player'],objects['eligibility']['player']],
                ['/objects/focused/critical_state/player','/objects/eligibility/player']),
               (tiles,[tiles['context']['player']],['/tiles/context/player']),
               (economy,[economy['snapshot']['player']],['/economy/snapshot/player'])]
        for raw,players,prefixes in cases:
            with self.subTest(format=prefixes[0]):
                before=read_snapshot(self.changed(raw))
                for player in players:
                    player['unknown_business_field']=7
                    player['unknown_nested']={'balance':13}
                if raw is objects:
                    objects['focused']['critical_state_sha256']=reader._sha(reader._canonical(objects['focused']['critical_state']))
                after=read_snapshot(self.changed(raw))
                self.assertNotEqual(before.fields,after.fields)
                for prefix in prefixes:
                    self.assertEqual(after.fields[prefix+'/unknown_business_field'],7)
                    self.assertEqual(after.fields[prefix+'/unknown_nested/balance'],13)
                    self.assertNotIn(prefix+'/unknown_business_field',after.diagnostic_fields)
                    self.assertNotIn(prefix+'/unknown_nested/balance',after.diagnostic_fields)
                    for known in ('force_id','ruler_id','ruler_name'):
                        self.assertIn(prefix+'/'+known,after.diagnostic_fields)
                        self.assertNotIn(prefix+'/'+known,after.fields)
    def test_hash_malformed_membership_and_embedded_id_rejected(self):
        with self.assertRaises(SnapshotError):read_snapshot(SWITCH/'before.json',expected_sha256='0'*64)
        for action in ('missing_city','wrong_id','bad_hex','wrong_person_hash'):
            raw=self.source()
            if action=='missing_city':del raw['records']['city:51']
            elif action=='wrong_id':raw['records']['city:13']='0e00'+raw['records']['city:13'][4:]
            elif action=='bad_hex':raw['records']['city:13']='gg'+raw['records']['city:13'][2:]
            else:raw['eligibility']['person_records_sha256']='0'*64
            with self.subTest(action=action),self.assertRaises(SnapshotError):read_snapshot(self.changed(raw))
    def test_bad_tile_bytes_or_layout_rejected(self):
        raw=json.loads(KNOWN.read_text(encoding='utf-8'))['tiles'];raw['ordered_payload_hex']='ff'+raw['ordered_payload_hex'][2:]
        with self.assertRaises(SnapshotError):read_snapshot(self.changed(raw))
        raw=json.loads(KNOWN.read_text(encoding='utf-8'))['tiles'];raw['field_ranges'][0]['offset']=0x15
        with self.assertRaises(SnapshotError):read_snapshot(self.changed(raw))
    def test_unknown_results_duplicate_keys_and_external_path_rejected(self):
        with self.assertRaises(SnapshotError):read_snapshot(HERE/'economy-selector-viewer-2.json')
        p=Path(self.tmp.name)/'duplicate.json';p.write_bytes(b'{"schema":"a","schema":"b"}')
        with self.assertRaises(SnapshotError):read_snapshot(p)
        with self.assertRaises(SnapshotError):read_snapshot('\\\\example.invalid\\x\\sample.json')
        with self.assertRaises(SnapshotError):read_snapshot(Path(__file__).resolve().parents[4]/'desktop.ini')
    def test_explicit_binary_range_is_opaque_bounded_and_pinned(self):
        p=Path(self.tmp.name)/'opaque.bin';p.write_bytes(bytes(range(64)));sha=hashlib.sha256(p.read_bytes()).hexdigest()
        r=read_binary_range(p,expected_sha256=sha,file_offset=16,length=8)
        self.assertEqual(r.offset,16);self.assertEqual(r.data,bytes(range(16,24)))
        with self.assertRaises(SnapshotError):read_binary_range(p,expected_sha256=sha,file_offset=60,length=8)
        with self.assertRaises(SnapshotError):read_binary_range(p,expected_sha256='0'*64,file_offset=0,length=8)
        with self.assertRaises(SnapshotError):read_snapshot(p)
    def test_imports_are_standard_library_no_live_capability(self):
        tree=ast.parse(Path(reader.__file__).read_text(encoding='utf-8'))
        names=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):names.update(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):names.add(node.module)
        self.assertEqual(names,{'dataclasses','copy','hashlib','json','pathlib','re','struct'})


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReaderTests))
    folder=HERE/'checkpoint_world_snapshot_reader_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    sources=['checkpoint_world_snapshot_reader.py','checkpoint_world_snapshot_reader_test.py']
    report={'schema':'san14.archive-world-reader-tests.v1','result':'PASS' if result.wasSuccessful() else 'FAIL',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'source_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in sources},
        'game_access':False,'steam_access':False,'process_access':False,'window_access':False,
        'full_world_verified':False,'all_inputs':'Explicit archived workspace JSON and own temporary bytes'}
    (folder/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(folder/'result.json'),'result':report['result'],'tests_run':result.testsRun}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
