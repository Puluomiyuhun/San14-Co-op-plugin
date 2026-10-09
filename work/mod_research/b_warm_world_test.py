"""Complete fake memory tables; no live GameReader construction or process IO."""
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT.parent/'mod_research'
sys.path.insert(0, str(ROOT/'outputs/san14-link'))
import b_warm_world as world
from b_warm_profile_contract import Profile, Date, Identity
from authoritative_sync import POLICY

OUTPUT = None


def configuration():
    profile = Profile()
    profile.file.name = b'svdexccSC03.s14'; profile.file.slot = 63; profile.file.size = 1234
    profile.file.sha256[:] = bytes.fromhex('a'*64)
    profile.before = Date(203, 8, 1); profile.loaded = Date(203, 8, 11)
    profile.source = Identity(666, 12, 11); profile.target = Identity(952, 2, 2); profile.currentForce = 12
    scope = dict(schema='san14.authoritative-sync-scope.v1', room_id='1'*32, binding_epoch='2'*32,
        profile=dict(protocol='san14.room.v1', game_sha256=world.objects.GAME_SHA256,
                     adapter_contract='research-no-native-room-adapter.v1', checkpoint_sha256='a'*64, rules_sha256='b'*64),
        bindings={'A': dict(force_id=12, main_district_id=11), 'B': dict(force_id=2, main_district_id=2)},
        authority='A', policy=POLICY)
    return profile, scope


class Memory:
    def __init__(self, base):
        self.base = base; self.spans = {}; self.counts = {}; self.mutate = None
    def put(self, address, data): self.spans[address] = bytes(data)
    def read(self, address, size):
        self.counts[address, size] = self.counts.get((address, size), 0)+1
        for start, raw in self.spans.items():
            if start <= address and address+size <= start+len(raw):
                result = raw[address-start:address-start+size]
                if self.mutate and self.mutate[:2] == (address, size) and self.counts[address, size] > 1:
                    offset = self.mutate[2]
                    result = result[:offset]+bytes([result[offset]^1])+result[offset+1:]
                return result
        raise ValueError('Missing fake memory span')


class Reader:
    def __init__(self, side, relocation=0):
        self.pid = 101 if side == 'A' else 202
        self.sha256 = world.objects.GAME_SHA256; self.side = side
        self.memory = Memory(0x140000000+relocation)
        self.root, self.world = 0x200000000+relocation, 0x300000000+relocation
        self.states = [(name, 0x400000000+relocation+i*0x1000) for i, name in enumerate(world.PLAN)]
        self.state_calls = 0; self.swap_state = False
        m = self.memory; m.put(m.base+0x1FCA1E0, struct.pack('<Q', self.root))
        m.put(self.root+0x85130, struct.pack('<Q', self.world))
        self.force, self.ruler = (12, 666) if side == 'A' else (2, 952)
        m.put(self.world+0x34, struct.pack('<HBB', 203, 8, 11)+bytes([0, 0, self.force, 1]))
        self.objects = {}
        for table_index, (name, offset, count, vt, serializer, layout) in enumerate(world.TABLES):
            m.put(m.base+vt+0x28, struct.pack('<Q', m.base+serializer))
            width = max(o+n for o, n in layout)
            pointers = [0x500000000+relocation+table_index*0x1000000+i*0x1000 for i in range(count)]
            m.put(self.root+offset, struct.pack('<'+'Q'*count, *pointers))
            self.objects[name] = pointers
            for slot, address in enumerate(pointers):
                raw = bytearray((slot*37+i*11) % 256 for i in range(width))
                struct.pack_into('<Q', raw, 0, m.base+vt)
                m.put(address, raw)

    def require_type(self, address, name):
        if (address, name) not in ((self.root, 'CSan14Data'), (self.world, 'CWorldData')):
            raise ValueError('Wrong fake context type')

    def snapshot(self):
        raw = self.memory.read(self.world+0x34, 8)
        year, month, day = struct.unpack_from('<HBB', raw)
        return dict(pid=self.pid, exe_sha256=self.sha256, date=dict(year=year, month=month, day=day),
                    player=dict(force_id=raw[6], ruler_id=self.ruler, ruler_name=self.side), state_stack=world.PLAN[:])

    def state_objects(self):
        self.state_calls += 1
        value = self.states[:]
        if self.swap_state and self.state_calls > 1: value[-1] = (value[-1][0], value[-1][1]+0x20000)
        return value


class Cases(unittest.TestCase):
    def observe(self, reader, **changes):
        p, scope = configuration()
        args = dict(scope=scope, epoch='3'*32, period=1, profile=p, side=reader.side,
                    receipt_key=('4' if reader.side == 'A' else '5')*64, read_birth=lambda: 999+reader.pid)
        args.update(changes)
        return world.sample(reader, **args)

    def test_different_viewer_and_all_addresses_same_shared_hash(self):
        a = self.observe(Reader('A')); b = self.observe(Reader('B', 0x1000000000))
        self.assertNotEqual(a['local_context']['base'], b['local_context']['base'])
        self.assertNotEqual(a['binding']['viewer_force'], b['binding']['viewer_force'])
        self.assertEqual(a['partial_sha256'], b['partial_sha256'])
        result = world.compare(a, b)
        self.assertEqual(result['result'], 'PARTIAL_MATCH')
        self.assertFalse(result['loaded_authorized']); self.assertFalse(result['full_world_verified'])
        (OUTPUT/'comparison.json').write_text(json.dumps(result, indent=2)+'\n')

    def test_force_and_object_business_differences_retained(self):
        a = self.observe(Reader('A')); reader = Reader('B')
        for table, slot, offset in [('objects', 3000, 0x14), ('forces', 51, 0x164)]:
            address = reader.objects[table][slot]; raw = bytearray(reader.memory.spans[address])
            raw[offset] ^= 1; reader.memory.put(address, raw)
        result = world.compare(a, self.observe(reader))
        self.assertEqual(result['result'], 'PARTIAL_DIFFERENCE')
        self.assertEqual(result['changed_bytes'], 2)
        self.assertEqual({(x['table'], x['physical_slot'], x['offset']) for x in result['differences']},
                         {('objects', 3000, 0x14), ('forces', 51, 0x164)})
        self.assertEqual(len(world.compare(a, self.observe(reader), max_examples=0)['differences']), 0)

    def test_payload_and_same_name_pointer_drift_refused(self):
        reader = Reader('A')
        reader.memory.mutate = (reader.objects['objects'][0], 0x18, 0x14)
        with self.assertRaisesRegex(ValueError, 'observed_memory_changed'): self.observe(reader)
        reader = Reader('A'); reader.swap_state = True
        with self.assertRaisesRegex(ValueError, 'context/payload changed'): self.observe(reader)

    def test_missing_slot_serializer_and_date_drift_refused(self):
        reader = Reader('A'); offset = world.objects.ROOT_OFFSET
        raw = reader.memory.spans[reader.root+offset]
        reader.memory.put(reader.root+offset, raw[:-8]+raw[:8])
        with self.assertRaisesRegex(ValueError, 'slots alias'): self.observe(reader)
        reader = Reader('A'); reader.memory.put(reader.memory.base+0x129FE58+0x28, struct.pack('<Q', reader.memory.base+0x214EC8))
        with self.assertRaisesRegex(ValueError, 'serializer slot'): self.observe(reader)
        reader = Reader('A'); reader.memory.mutate = (reader.world+0x34, 8, 3)
        with self.assertRaises(ValueError): self.observe(reader)

    def test_wrong_profile_scope_or_modified_witness_refused(self):
        a = self.observe(Reader('A')); b = self.observe(Reader('B'))
        bad = deepcopy(b); bad['binding']['epoch'] = '6'*32
        with self.assertRaisesRegex(ValueError, 'Foreign observation'): world.compare(a, bad)
        bad = deepcopy(b); bad['shared']['object_payload'] = '00'+bad['shared']['object_payload'][2:]
        # Slot0/offset10 happens to be 0xb0, so this changes actual payload.
        with self.assertRaisesRegex(ValueError, 'digest'): world.compare(a, bad)
        p, _ = configuration(); p.loaded.day = 21
        with self.assertRaisesRegex(ValueError, 'Date/viewer'): self.observe(Reader('A'), profile=p)
        bad = deepcopy(b); bad['full_world_verified'] = True
        with self.assertRaisesRegex(ValueError, 'authority'): world.compare(a, bad)


def pins():
    paths = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, '__file__', None)}
    paths.add(Path(__file__).resolve())
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)
            if p.is_relative_to(ROOT) and p.suffix == '.py'}


if __name__ == '__main__':
    OUTPUT = PRIVATE/'b_warm_world_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f'); OUTPUT.mkdir(parents=True)
    before = pins(); stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(), encoding='utf-8')
    sources = pins(); stable = all(sources.get(k) == v for k, v in before.items())
    report = dict(family='san14.b-warm-world-partial.v1', result='PASS' if result.wasSuccessful() and result.testsRun == 5 and stable else 'FAIL',
        tests=result.testsRun, sources=sources, inputs_unchanged=stable, game_access=False, native_calls=False,
        actual_live_samples=False, full_world_verified=False, ready_authorized=False,
        failures=[(str(t), detail) for t, detail in result.failures+result.errors])
    report['artifacts'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(OUTPUT/'result.json'); print(stream.getvalue())
    raise SystemExit(0 if report['result'] == 'PASS' else 1)
