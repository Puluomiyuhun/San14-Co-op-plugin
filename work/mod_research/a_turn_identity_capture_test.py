"""Pure memory-read doubles; never imports or opens the real process reader."""
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest
import a_turn_identity_capture as subject


class Fake:
    def __init__(self, mutation=None):
        self.memory = self
        self.pid, self.handle, self.base, self.sha256 = 123, 456, 0x140000000, 'diagnostic'
        self.data, self.types = {}, {}
        self.roots, self.mutation = 0, mutation
        self.root, self.world, self.stack, self.user = 0x200000, 0x300000, 0x400000, 0x500000
        self.put(self.base+subject.ROOT, self.root)
        self.put(self.root+0x85130, self.world)
        self.write(self.world+0x34, struct.pack('<H6B', 203, 8, 11, 0, 0, 12, 0))
        self.types.update({self.root:'CSan14Data', self.world:'CWorldData'})
        self.state(self.user)
        self.put(self.stack, self.user)
        m = self.base+subject.MANAGER
        for off, value in ((0x10,1),(0x18,16),(0x20,self.stack),(0x30,0),(0x38,0),(0x40,0),(0x48,0)):
            self.put(m+off,value)

    def state(self, address):
        self.put(address, self.base+0x12CC4A8)
        self.put(address+0x50, 0)
        self.write(address+0x70, b'CUserStrategyState\0')
        self.types[address] = 'CUserStrategyState'

    def write(self, address, data):
        self.data.update({address+i:v for i,v in enumerate(data)})

    def put(self, address, value):
        self.write(address, struct.pack('<Q',value))

    def read(self, address, size):
        if address == self.base+subject.ROOT:
            self.roots += 1
            if self.roots == 2 and self.mutation:
                self.mutation(self)
        return bytes(self.data.get(address+i,0) for i in range(size))

    def pointer(self,address):
        return subject.pointer(struct.unpack('<Q',self.read(address,8))[0])

    def require_type(self,address,name):
        if self.types.get(address) != name:
            raise RuntimeError('Fake RTTI mismatch')


class CaptureTests(unittest.TestCase):
    def test_stable_records_exact_addresses_and_queue(self):
        fake = Fake()
        sample = subject.capture(fake,lambda _:9876)
        self.assertEqual((sample['pid'],sample['birth'],sample['root'],sample['world']),
                         (123,9876,fake.root,fake.world))
        self.assertEqual(sample['states'][0], dict(name='CUserStrategyState',address=fake.user,
                         vtable=fake.base+0x12CC4A8,task=0))
        self.assertEqual(sample['manager']['entries'], [])
        self.assertFalse(subject.compare(sample,sample)['same_object_lifetime_proven'])

    def test_same_name_different_address_race_is_rejected(self):
        def mutate(f):
            f.state(0x600000)
            f.put(f.stack,0x600000)
        with self.assertRaisesRegex(RuntimeError,'Identity changed'):
            subject.capture(Fake(mutate),lambda _:9876)

    def test_world_or_date_drift_is_rejected(self):
        def world(f):
            f.types[0x700000]='CWorldData'
            f.write(0x700034, f.read(f.world+0x34,8))
            f.put(f.root+0x85130,0x700000)
        def date(f):
            f.write(f.world+0x37,bytes([21]))
        for mutation in (world,date):
            with self.subTest(mutation=mutation.__name__), self.assertRaisesRegex(RuntimeError,'Identity changed'):
                subject.capture(Fake(mutation),lambda _:9876)


if __name__ == '__main__':
    run = subject.PRIVATE/'a_turn_identity_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    names = [Path(__file__),Path(subject.__file__)]
    sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    pins = {p.name:sha(p) for p in names}
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CaptureTests))
    (run/'test.log').write_text(log.getvalue(),encoding='utf-8')
    same = all(sha(p)==pins[p.name] for p in names)
    passed = result.wasSuccessful() and result.testsRun==3 and same
    out = dict(result='PASS' if passed else 'FAIL',tests=result.testsRun,sources=pins,
               sources_unchanged=same,game_access=False,pure_fake_reads=True)
    (run/'result.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(path=str(run/'result.json'),**out)))
    raise SystemExit(0 if passed else 1)
