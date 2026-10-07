"""Owned fake memory only; never imports or constructs a live reader."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import unittest

import checkpoint_live_force_capture as cap
from checkpoint_world_next_table_native import source_objects

P=Path(__file__).resolve().parent
IMAGE=(P/'game-runtime-image.bin').read_bytes()
assert hashlib.sha256(IMAGE).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'


class FakeMemory:
    base=0x7FF749440000
    image_size=len(IMAGE)
    def __init__(self):self.regions={};self.counts={};self.hook=None
    def put(self,address,raw):self.regions[address]=bytearray(raw)
    def q(self,address,value):self.put(address,struct.pack('<Q',value))
    def u32(self,address,value):self.put(address,struct.pack('<I',value))
    def read(self,address,size):
        key=(address,size);self.counts[key]=self.counts.get(key,0)+1
        if self.hook:self.hook(self,address,size,self.counts[key])
        for start,raw in reversed(list(self.regions.items())):
            if start<=address and address+size<=start+len(raw):return bytes(raw[address-start:address-start+size])
        if self.base<=address and address+size<=self.base+self.image_size:
            return IMAGE[address-self.base:address-self.base+size]
        raise ValueError('unmapped fake memory')


class FakeReader:
    pid=41;sha256=cap.GAME_SHA256
    def __init__(self,relocation=0):
        self.memory=FakeMemory();self.root=0x300000000+relocation;self.world=self.root+0x100000
        self.forces=tuple(self.root+0x200000+i*0x200 for i in range(52))
        self.states=[(name,self.root+0x300000+i*0x1000) for i,name in enumerate(cap.STACK)]
        self.snapshots=0;self.snapshot_change=None
        m=self.memory;m.q(m.base+cap.ROOT_POINTER_RVA,self.root);m.q(self.root,m.base+cap.ROOT_VTABLE_RVA)
        m.q(self.root+0x85130,self.world);m.q(self.world,m.base+cap.WORLD_VTABLE_RVA)
        m.put(self.world+0x34,struct.pack('<HBBBBBB',203,8,11,0,0,12,0))
        m.u32(self.world+0x40,1);m.u32(self.world+0x16A8,0);m.u32(self.states[-1][1]+0x470,2)
        m.put(self.root+cap.ROOT_OFFSET,struct.pack('<52Q',*self.forces))
        for i,raw in source_objects().items():
            body=bytearray(raw);body[:8]=struct.pack('<Q',m.base+cap.FORCE_VTABLE_RVA);m.put(self.forces[i],body)
    def state_objects(self):return deepcopy(self.states)
    def snapshot(self):
        self.snapshots+=1
        value=dict(mode='OWN_FAKE_MEMORY',pid=self.pid,exe_sha256=self.sha256,
            date=dict(year=203,month=8,day=11,period='middle'),player=dict(force_id=12,ruler_id=666,ruler_name='fake'),
            state_stack=list(cap.STACK),in_player_strategy=True)
        if self.snapshot_change:self.snapshot_change(self,value)
        return value


class CaptureTests(unittest.TestCase):
    def test_complete_two_pass_projection_no_stream_claim(self):
        r=FakeReader();s=cap.capture(r)
        self.assertEqual(len(s['records']),52)
        self.assertEqual(len(bytes.fromhex(s['ordered_payload_hex'])),19656)
        self.assertEqual(s['stability']['context_samples'],3)
        for pointer in r.forces:self.assertEqual(r.memory.counts[(pointer+0x10,0x185)],2)
        expected=b''.join(b''.join(raw[o:o+n] for o,n in cap.FIELD_LAYOUT) for raw in source_objects().values())
        self.assertEqual(bytes.fromhex(s['ordered_payload_hex']),expected)
        self.assertIsNone(s['projection']['actual_stream_version_observed'])
        self.assertIsNone(s['projection']['actual_stream_transform_flag_observed'])
        self.assertFalse(s['projection']['native_serialization_executed']);self.assertFalse(s['full_world_verified'])
        json.dumps(s)

    def test_record_and_nonprojected_mutation_detected_in_comparison(self):
        before=cap.capture(FakeReader());r=FakeReader()
        r.memory.regions[r.forces[51]][0x194]^=1
        r.memory.regions[r.forces[26]][0x71]^=1 # Padding after first nested29-byte structure.
        after=cap.capture(r);diff=cap.compare(before,after)
        self.assertFalse(diff['observed_table_equal'])
        self.assertEqual(diff['changed_records'][0]['physical_slot'],51)
        self.assertEqual(diff['changed_records'][0]['changed_bytes'][0]['object_offset'],0x194)
        self.assertEqual(diff['nonprojected_memory_changes'][0]['object_offset'],0x71)
        self.assertFalse(diff['full_world_verified'])

    def test_relocation_diagnostic_separate_from_all_field_comparison(self):
        diff=cap.compare(cap.capture(FakeReader()),cap.capture(FakeReader(0x10000000)))
        self.assertTrue(diff['observed_table_equal']);self.assertFalse(diff['pointer_diagnostics_equal'])
        self.assertFalse(diff['sampled_context_equal']);self.assertFalse(diff['authorize_load_or_ready'])

    def test_wrong_build_root_force_type_serializer_code_and_alias_rejected(self):
        def wrong_build(r):r.sha256='0'*64
        def wrong_root(r):r.memory.q(r.root,0x99900)
        def wrong_force(r):r.memory.q(r.forces[51],r.memory.base+cap.WORLD_VTABLE_RVA)
        def wrong_method(r):r.memory.q(r.memory.base+cap.FORCE_VTABLE_RVA+0x28,r.memory.base+cap.SERIALIZER_RVA+1)
        def wrong_code(r):r.memory.put(r.memory.base+cap.SERIALIZER_RVA,bytes(1581))
        def alias(r):r.memory.put(r.root+cap.ROOT_OFFSET,struct.pack('<52Q',*(r.forces[:-1]+(r.forces[0],))))
        for change in (wrong_build,wrong_root,wrong_force,wrong_method,wrong_code,alias):
            r=FakeReader();change(r)
            with self.subTest(change=change.__name__),self.assertRaises(cap.ForceCaptureError):cap.capture(r)

    def test_changed_bytes_table_and_context_during_capture_rejected(self):
        for kind in ('payload','padding','table','context'):
            r=FakeReader()
            def hook(m,address,size,count):
                if kind in ('payload','padding') and address==r.forces[0]+cap.START and count==2:
                    m.regions[r.forces[0]][0x10 if kind=='payload' else 0x71]^=1
                if kind=='table' and address==r.root+cap.ROOT_OFFSET and count==2:
                    m.put(address,struct.pack('<52Q',*reversed(r.forces)))
            r.memory.hook=hook
            if kind=='context':r.snapshot_change=lambda reader,value:value['player'].update(ruler_name='changed' if reader.snapshots>1 else 'fake')
            with self.subTest(kind=kind),self.assertRaises(cap.ForceCaptureError):cap.capture(r)

    def test_short_reads_and_nonplanning_context_rejected(self):
        r=FakeReader();original=r.memory.read
        r.memory.read=lambda address,size:original(address,size)[:-1] if address==r.forces[2]+cap.START else original(address,size)
        with self.assertRaises(cap.ForceCaptureError):cap.capture(r)
        r=FakeReader();r.memory.u32(r.states[-1][1]+0x470,1)
        with self.assertRaises(cap.ForceCaptureError):cap.capture(r)
        r=FakeReader();r.snapshot_change=lambda reader,value:value['state_stack'].append('CReportDisplayState')
        with self.assertRaises(cap.ForceCaptureError):cap.capture(r)

    def test_bad_saved_sample_cannot_compare_by_intersection(self):
        before=cap.capture(FakeReader())
        for kind in ('missing','tampered','stream'):
            after=deepcopy(before)
            if kind=='missing':del after['records']['force_slot:51']
            elif kind=='tampered':after['ordered_payload_hex']='00'+after['ordered_payload_hex'][2:]
            else:after['projection']['actual_stream_transform_flag_observed']=0
            with self.subTest(kind=kind),self.assertRaises(cap.ForceCaptureError):cap.compare(before,after)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CaptureTests))
    folder=P/'checkpoint_live_force_capture_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    report=dict(schema='san14.live-force-capture-fixtures.v1',result='PASS' if result.wasSuccessful() else 'FAIL',
        tests_run=result.testsRun,errors=len(result.errors),failures=len(result.failures),game_access=False,
        process_access=False,fixture='OWN_FAKE_MEMORY_AND_ARCHIVED_IMAGE',
        source_sha256={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in
            ('checkpoint_live_force_capture.py','checkpoint_live_force_capture_test.py','checkpoint_world_next_table_schema.py')})
    path=folder/'result.json';path.write_text(json.dumps(report,indent=2),encoding='utf8');print(path)
    raise SystemExit(not result.wasSuccessful())
