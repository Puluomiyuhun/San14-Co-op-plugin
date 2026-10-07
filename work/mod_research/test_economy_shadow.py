"""Offline guard tests for the emulation harness, no process access."""
import json, unittest, struct
from economy_shadow import Capture,Shadow,PAGE,HEAP,STACK,STACK_SIZE,STOP,HERE
from unicorn.x86_const import *

FIXTURE=HERE/'economy-shadow-nine-cities.zip'

class FakeReader:
    def __init__(self,pages):self.pages=pages;self.memory=self
    def read(self,a,n):return self.pages[a][:n]
    def snapshot(self):return {'same':True}

def tiny_capture(kind,address=0x10010,pool=True):
    c=object.__new__(Capture);c.pages={0x10000:b'\0'*PAGE};c.used={}
    c.meta={'base':0,'snapshot':{'same':True},'pool_captures':[]}
    if pool:c.meta['pool_captures']=[{'rva':'0x10000','ranges':[(0x10000,PAGE)]}]
    c.mark(address,1,kind=kind)
    modified=bytearray(PAGE);modified[address-0x10000]=1;c.reader=FakeReader({0x10000:bytes(modified)})
    return c

class Guards(unittest.TestCase):
    def shadow(self):return Shadow(Capture(path=FIXTURE))
    def test_missing_replay_page_does_not_open_game(self):
        c=Capture(path=FIXTURE)
        self.assertIsNone(c.reader)
        with self.assertRaisesRegex(RuntimeError,'Missing replay page'):c.read(0x500000000000,8)
    def test_unknown_external_execution_stops(self):
        s=self.shadow()
        with self.assertRaisesRegex(RuntimeError,'Unknown external execution'):s.call(0x500000000000-s.base)
    def test_non_shadow_allocation_cannot_be_freed(self):
        s=self.shadow()
        with self.assertRaisesRegex(RuntimeError,'Free of non-shadow'):s.call(0x3a58b0,s.world)
    def test_private_allocator_is_balanced(self):
        s=self.shadow();p=s.call(0x3a5820,48)
        self.assertTrue(HEAP<=p<HEAP+0x1000000);self.assertEqual(s.allocs[p],48)
        s.call(0x3a58b0,p);self.assertEqual(s.allocs,{})
    def test_native_identity_stays_in_shadow(self):
        s=self.shadow();original=s.source.read(s.world+0x3a,1)
        s.identity(2)
        self.assertEqual(s.read(s.world+0x3a,1),b'\2')
        self.assertEqual(s.source.read(s.world+0x3a,1),original)
        self.assertEqual(original,b'\x0c')
    def test_stack_probe_rejects_overflow(self):
        s=self.shadow();s.uc.reg_write(UC_X86_REG_RAX,STACK_SIZE*2)
        with self.assertRaisesRegex(RuntimeError,'stack overflow'):s.call(0xef9eb0)
    def test_uninitialized_settings_guard_rejects(self):
        s=self.shadow();s.write(s.base+0x1fd0c5c,struct.pack('<i',0))
        with self.assertRaisesRegex(RuntimeError,'not initialized'):s.call(0x39c260)
    def test_semantic_read_change_is_not_ignored(self):
        c=tiny_capture(1)
        with self.assertRaisesRegex(RuntimeError,'Source changed'):c.verify()
    def test_only_allocator_read_in_known_pool_is_classified(self):
        c=tiny_capture(2);r=c.verify()
        self.assertEqual(r['changed_bytes'],0);self.assertEqual(r['allocator_only_changed_bytes'],1)
    def test_allocator_read_outside_pool_is_not_ignored(self):
        c=tiny_capture(2,pool=False)
        with self.assertRaisesRegex(RuntimeError,'Source changed'):c.verify()
    def test_mixed_semantic_and_allocator_read_is_not_ignored(self):
        for first,second in ((1,2),(2,1)):
            c=tiny_capture(first);c.mark(0x10010,1,kind=second)
            with self.assertRaisesRegex(RuntimeError,'Source changed'):c.verify()
    def test_reads_after_shadow_write_are_not_source_inputs(self):
        c=tiny_capture(1);c.used={};dirty={0x10000:bytearray(PAGE)};dirty[0x10000][0x10]=1
        c.mark(0x10010,1,dirty)
        self.assertEqual(c.verify()['changed_bytes'],0)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Guards))
    (HERE/'economy-shadow-guard-tests.json').write_text(json.dumps({'result':'PASS' if result.wasSuccessful() else 'FAIL',
        'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'game_process_opened':False},indent=2)+'\n',encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
