"""Owned byte reads, pinned static sources and archived arithmetic tails only."""
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import unittest

import reward_counter_policy as policy

HERE = Path(__file__).resolve().parent
PRIVATE = HERE.parents[2]/'mod_research'
IMAGE = PRIVATE/'game-runtime-image.bin'
ROWS = []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class OwnedWorld:
    def __init__(self):
        self.address = 0x10000000
        self.data = bytearray(0x1700)
        self.calls = []
        self.set('world_3a_u8', 12)
        self.set('world_7c_u32', 30)
        self.set('world_80_u32', 9)
    def set(self, name, value):
        _, offset, fmt = next(row for row in policy.FIELDS if row[0] == name)
        struct.pack_into(fmt, self.data, offset, value)
    def read(self, address, size):
        self.calls.append((address, size))
        offset = address-self.address
        if offset < 0 or offset+size > len(self.data):
            raise AssertionError('Unexpected owned read')
        return bytes(self.data[offset:offset+size])
    def capture(self):
        return policy.capture(self.read, world=self.address)


class Cases(unittest.TestCase):
    def record(self, **values):
        ROWS.append(dict(case=self._testMethodName, **values))

    def test_exact_archive_sources_and_viewer_write_read_paths(self):
        evidence = policy.audit_archive(IMAGE)
        self.assertEqual(len(evidence['sections']), 13)
        self.assertFalse(evidence['save_mapping_verified'])
        self.assertFalse(evidence['complete_writer_inventory'])
        self.record(evidence=evidence)

    def test_capture_exact_little_endian_signed_byte_and_bounded_reads(self):
        w = OwnedWorld()
        w.set('world_80_u32', 0x12345678)
        w.data[0xBC:0xC0] = b'\xff\x00\x00\x00'
        value = w.capture()
        self.assertEqual(value['fields']['world_80_u32'], 0x12345678)
        self.assertEqual(value['fields']['world_bc_i8'], -1)
        self.assertEqual(struct.unpack_from('<i', w.data, 0xBC)[0], 255)
        self.assertEqual(len(w.calls), 14)
        self.assertTrue(all(n <= 4 for _, n in w.calls))
        self.assertFalse(value['atomic_snapshot'])
        self.record(fields=value['fields'], no_process_opened=True)

    def test_capture_refuses_mid_sample_change_and_short_read(self):
        w = OwnedWorld()
        def changing(address, size):
            if len(w.calls) == 7:
                w.set('world_80_u32', 10)
            return w.read(address, size)
        with self.assertRaisesRegex(ValueError, 'changed'):
            policy.capture(changing, world=w.address)
        with self.assertRaisesRegex(ValueError, 'Exact field'):
            policy.capture(lambda a, n: b'\x00'*(n-1), world=w.address)
        self.record(refused=True)

    def test_gate_unknowns_and_each_known_blocker_never_authorize(self):
        w = OwnedWorld()
        self.assertEqual(policy.reward_branch_gate(w.capture())['status'], 'UNKNOWN')
        args = dict(optional_context_present=True, current_force_valid=True,
                    district_force_id=12, district_leader_valid=True, district_leader_rank=1)
        good = policy.reward_branch_gate(w.capture(), **args)
        self.assertEqual(good['status'], 'AUDITED_CONDITIONS_OBSERVED_TRUE')
        self.assertFalse(good['production_permit'])
        self.assertFalse(good['native_call_observed'])
        for name, bad in [('optional_context_present', False), ('current_force_valid', False),
                          ('district_force_id', 2), ('district_leader_valid', False), ('district_leader_rank', 2)]:
            self.assertEqual(policy.reward_branch_gate(w.capture(), **{**args, name: bad})['status'], 'AUDITED_BRANCH_BLOCKED')
        w.set('world_bc_i8', -1)
        self.assertEqual(policy.reward_branch_gate(w.capture(), **args)['status'], 'AUDITED_BRANCH_BLOCKED')
        w.set('world_bc_i8', 0); w.set('world_16a8_u32', 0x100)
        self.assertEqual(policy.reward_branch_gate(w.capture(), **args)['status'], 'AUDITED_BRANCH_BLOCKED')
        self.record(known_conditions=good, unknown_is_not_permission=True)

    def test_arithmetic_against_actual_archived_add_unsigned_cap_tails(self):
        # Execute only 21-byte arithmetic tails, with owned registers and memory.
        # No reward/menu/loader body, Windows process or native DLL is executed.
        policy.audit_archive(IMAGE)
        sys.path.insert(0, str(PRIVATE/'python_deps'))
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
        from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RBX
        raw = IMAGE.read_bytes(); results = []
        for field, start, end, offset in [('world_80_u32', 0x2E63CD, 0x2E63E2, 8),
                                           ('world_7c_u32', 0x2E643D, 0x2E6452, 4)]:
            for before, delta in [(9, 1), (999, 20), (9999, 20), (0xffffffff, 1),
                                  (0xfffffff0, 20), (10, 0xffffffff), (0, 0xffffffff)]:
                emu = Uc(UC_ARCH_X86, UC_MODE_64)
                emu.mem_map(0x1000, 0x1000); emu.mem_map(0x2000, 0x1000)
                emu.mem_write(0x1000, raw[start:end]); emu.mem_write(0x2000+offset, struct.pack('<I', before))
                emu.reg_write(UC_X86_REG_RAX, 0x2000); emu.reg_write(UC_X86_REG_RBX, delta)
                emu.emu_start(0x1000, 0x1000+end-start, count=16)
                actual = struct.unpack('<I', emu.mem_read(0x2000+offset, 4))[0]
                self.assertEqual(actual, policy.native_counter_add(field, before, delta))
                results.append(dict(field=field, before=before, increment_bits=delta, after=actual))
        self.assertEqual(policy.native_counter_add('world_80_u32', 0xffffffff, 1), 0)
        self.record(archived_arithmetic_cases=results, complete_reward_executed=False)

    def test_arithmetic_refuses_wrong_types_and_unaudited_field(self):
        for value in (-1, 2**32, True, 1.0, None):
            with self.assertRaises(ValueError):
                policy.native_counter_add('world_80_u32', 1, value)
        with self.assertRaises(ValueError):
            policy.native_counter_add('gold', 1, 1)
        self.record(refused=True)

    def test_shared_delta_excludes_changed_unchanged_and_unknown_world_cases(self):
        w = OwnedWorld(); a = w.capture()
        self.assertEqual(policy.shared_delta_exclusion(a, a)['excluded_fields'], list(policy.COUNTERS))
        w.set('world_80_u32', 10); w.set('world_450_u32', 77)
        b = w.capture(); result = policy.shared_delta_exclusion(a, b)
        self.assertIn('world_450_u32', result['changes'])
        self.assertFalse(result['reward_attribution_proven'])
        self.assertFalse(result['shared_delta_inclusion_allowed'])
        b['world'] += 0x1000; b['fields']['world_3a_u8'] = 2
        result = policy.shared_delta_exclusion(a, b)
        self.assertFalse(result['same_local_address_and_viewer'])
        self.assertFalse(result['native_apply_permit'])
        self.assertFalse(result['load_restore_permit'])
        self.record(result=result)

    def test_checkpoint_plan_preserves_uncertainty_and_no_restore_permission(self):
        result = policy.checkpoint_impact()
        self.assertIsNone(result['serialized_in_save'])
        self.assertIsNone(result['copied_by_authority_checkpoint'])
        self.assertFalse(result['unconditional_preserve_is_safe'])
        self.assertFalse(result['unconditional_authority_overwrite_is_safe'])
        self.assertFalse(result['game_write_permit'])
        self.assertFalse(result['load_restore_permit'])
        self.record(result=result)


if __name__ == '__main__':
    output = PRIVATE/'reward_counter_policy_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True)
    sources = {str(HERE/name): sha(HERE/name) for name in ('reward_counter_policy.py', 'reward_counter_policy_test.py')}
    private_inputs = {str(IMAGE): sha(IMAGE)}
    stream = io.StringIO()
    tests = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (output/'test.log').write_text(stream.getvalue(), encoding='utf-8')
    unchanged = all(sha(path) == digest for path, digest in {**sources, **private_inputs}.items())
    result = dict(result='PASS' if tests.wasSuccessful() and unchanged else 'FAIL', tests=tests.testsRun,
        sources=sources, private_inputs=private_inputs, sources_unchanged=unchanged, cases=ROWS,
        game_access=False, native_process_execution=False, archived_arithmetic_only=True,
        production_permit=False, load_restore_permit=False,
        failures=[(str(t), trace) for t, trace in tests.errors+tests.failures],
        artifacts={str(p): sha(p) for p in output.rglob('*') if p.is_file()})
    path = output/'result.json'
    path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(stream.getvalue()); print(path)
    raise SystemExit(result['result'] != 'PASS')
