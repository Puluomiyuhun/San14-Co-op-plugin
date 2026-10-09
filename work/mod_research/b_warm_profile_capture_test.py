"""Offline fake-read tests only. No GameReader or Windows process is opened."""
import copy
import ctypes as C
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import unittest

import b_warm_profile_capture as capture
import b_warm_profile_contract as abi


def row(second=False):
    return dict(file=dict(name='svdexccSC03.s14', slot=63, size=274880,
                         sha256=hashlib.sha256(b'diagnostic input').hexdigest()),
                before=dict(year=203, month=8, day=21 if second else 11),
                loaded=dict(year=203, month=9 if second else 8, day=1 if second else 11),
                source=dict(ruler=666, force=12, district=11),
                target=dict(ruler=952, force=2, district=2), currentForce=2 if second else 12)


class Memory:
    base = 0x140000000
    def __init__(self):
        self.blocks = [(self.base, bytearray(0x2030000)), (0x200000000, bytearray(0x100000))]
    def span(self, address, size):
        for start, block in self.blocks:
            if start <= address and address+size <= start+len(block):
                return block, address-start
        raise RuntimeError('Unmapped fake read')
    def read(self, address, size):
        block, offset = self.span(address, size)
        return bytes(block[offset:offset+size])
    def put(self, address, value, fmt='<Q'):
        raw = struct.pack(fmt, value)
        block, offset = self.span(address, len(raw))
        block[offset:offset+len(raw)] = raw


class Reader:
    pid, sha256 = 1234, capture.GAME_SHA
    def __init__(self, second=False):
        self.memory = m = Memory()
        self.profile = capture.profile_from_dict(row(second))
        self.ruler = 952 if second else 666
        self.birth = 1234567
        self.states = [0x200090000+i*0x1000 for i in range(5)]
        if second:
            self.states = [a+0x10000 for a in self.states]
        self.root, self.world = 0x200000000, 0x200086000
        self.cache, self.toolbar, self.panel, self.keyboard, self.stack = [0x2000b0000+i*0x1000 for i in range(5)]
        self.types = {self.root: 'CSan14Data', self.world: 'CWorldData', **dict(zip(self.states, capture.NAMES))}
        b = m.base
        m.put(b+0x1fca1e0, self.root)
        m.put(self.root+0x85130, self.world)
        m.put(b+0x2025318, self.cache)
        m.put(b+0x1fca0a0, self.keyboard)
        m.put(self.states[4]+0x478, self.toolbar)
        m.put(self.states[2]+0x480, self.panel)
        m.put(self.states[4]+0x470, 2, '<I')
        m.put(self.toolbar+0x88, -1, '<i')
        m.put(self.cache+0x3ec, -1, '<i')
        for offset, value in ((0x10, 5), (0x18, 5), (0x20, self.stack)):
            m.put(b+0x19e7310+offset, value)
        for i, state in enumerate(self.states):
            m.put(self.stack+8*i, state)
        for slot, original in capture.SLOTS:
            m.put(b+slot, b+original)
    def pointer(self, address):
        value = struct.unpack('<Q', self.memory.read(address, 8))[0]
        capture.require(value >= 0x10000 and value % 8 == 0, 'Fake pointer')
        return value
    def state_objects(self):
        return list(zip(capture.NAMES, self.states))
    def require_type(self, address, name):
        capture.require(self.types.get(address) == name, 'Fake RTTI mismatch')
    def context(self):
        p = self.profile
        return dict(snapshot=dict(date=dict(year=p.before.year, month=p.before.month, day=p.before.day),
                                  player=dict(force_id=p.currentForce, ruler_id=self.ruler)))


def sample(reader, context_reader=None, birth_reader=None):
    return capture.capture_planning(reader, reader.profile, reader.ruler,
        context_reader=context_reader or (lambda r: r.context()),
        birth_reader=birth_reader or (lambda r: r.birth),
        range_check=lambda r, a, n: r.memory.span(a, n))


class Tests(unittest.TestCase):
    def test_initial_and_rebound_player(self):
        a, b = Reader(), Reader(True)
        one, two = sample(a), sample(b)
        self.assertNotEqual(one['states'], two['states'])
        self.assertEqual(two['context']['snapshot']['player']['force_id'], 2)
        self.assertEqual(two['context']['snapshot']['date']['day'], 21)
        self.assertFalse(two['atomic_snapshot'])

    def test_wrong_current_identity_and_date(self):
        r = Reader(True)
        for key, value in [('force_id', 12), ('ruler_id', 666)]:
            wrong = r.context()
            wrong['snapshot']['player'][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Current player'):
                sample(r, lambda _: wrong)
        wrong = r.context()
        wrong['snapshot']['date']['day'] = 11
        with self.assertRaisesRegex(ValueError, 'Current date'):
            sample(r, lambda _: wrong)

    def test_current_task_and_birth_drift_rejected(self):
        for which in ('current', 'task', 'birth'):
            r = Reader()
            calls = 0
            def context(_):
                nonlocal calls
                calls += 1
                if calls == 2:
                    if which == 'birth':
                        r.birth += 1
                    else:
                        address = r.memory.base+0x19e7310+0x48 if which == 'current' else r.states[4]+0x50
                        r.memory.put(address, r.states[4])
                return r.context()
            with self.subTest(which=which), self.assertRaisesRegex(ValueError, 'changed during capture'):
                sample(r, context)

    def test_hooks_queue_and_pending_rejected(self):
        for field in ('hook', 'queue', 'pending'):
            r = Reader()
            if field == 'hook':
                r.memory.put(r.memory.base+capture.SLOTS[0][0], 0x77770000)
            elif field == 'queue':
                r.memory.put(r.memory.base+0x19e7310+0x30, 1)
            else:
                r.memory.put(r.states[2]+0x47c, 1, '<I')
            with self.subTest(field=field), self.assertRaises(ValueError):
                sample(r)

    def test_profile_parser_no_wrap_or_alias(self):
        r = Reader()
        r.pid = 0x100000000+1234
        with self.assertRaisesRegex(ValueError, 'no ABI truncation'):
            sample(r)
        for key, value in [('currentForce', 258), ('currentForce', True), ('currentForce', -1)]:
            data = row()
            data[key] = value
            with self.assertRaises(ValueError):
                capture.profile_from_dict(data)
        for mutation in (lambda d: d['file'].update(slot=64), lambda d: d['before'].update(day=12),
                         lambda d: d.update(target=copy.deepcopy(d['source'])), lambda d: d['file'].update(sha256='0'*64)):
            data = row()
            mutation(data)
            with self.assertRaises(ValueError):
                capture.profile_from_dict(data)

    def test_typed_config_rejects_stale_generation(self):
        r = Reader(True)
        plan = sample(r)
        owner = abi.old.Config()
        for name in capture.BINDINGS:
            setattr(owner, name, plan[name])
        owner.states[:] = plan['states']
        owner.attempt = owner.epoch = owner.generation = 2
        owner.gameSha256[:] = bytes.fromhex(capture.GAME_SHA)
        for name in ('attachment', 'ownerBinding', 'nonce'):
            getattr(owner, name)[:] = bytes([7])*32
        combined = capture.wrap_owner_config(owner, r.profile, plan)
        self.assertEqual(combined.profile.currentForce, 2)
        self.assertEqual(bytes(combined.owner), bytes(owner))
        self.assertEqual(combined.size, C.sizeof(abi.Config))
        owner.states[4] -= 0x10000
        with self.assertRaisesRegex(ValueError, 'stale'):
            capture.wrap_owner_config(owner, r.profile, plan)
        owner.states[:] = plan['states']
        wrong = abi.Profile.from_buffer_copy(bytes(r.profile))
        wrong.loaded.day = 11
        with self.assertRaisesRegex(ValueError, 'Profile differs'):
            capture.wrap_owner_config(owner, wrong, plan)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    run = capture.PRIVATE/'b_warm_profile_capture_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    paths = [Path(__file__), Path(capture.__file__), Path(abi.__file__), Path(abi.old.__file__)]
    report = dict(result='PASS' if result.wasSuccessful() else 'FAIL', tests=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), fake_reads_only=True,
                  game_touched=False, installation_tested=False,
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (run/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(run/'result.json')
    raise SystemExit(not result.wasSuccessful())
