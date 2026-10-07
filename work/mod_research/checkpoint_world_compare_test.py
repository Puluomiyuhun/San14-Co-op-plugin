"""Meaningful archived-data regression and missing-state fault injection."""
from dataclasses import replace
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from checkpoint_world_snapshot_reader import Segment, Snapshot, read_snapshot
from checkpoint_world_compare import compare, write_report, HERE, SUPPORTED_BUILD

BEFORE = HERE/'startup-switch-traces/20261006-124754-542123/before.json'
AFTER = HERE/'startup-switch-traces/20261006-124754-542123/after.json'
FULL_MAP = HERE/'checkpoint_push_runs/20261006-203111-687580/known-before.json'


def mutate(snapshot, key, offset, value):
    records = dict(snapshot.records)
    segments = list(records[key])
    for index, segment in enumerate(segments):
        if segment.offset <= offset < segment.offset+len(segment.data):
            data = bytearray(segment.data)
            data[offset-segment.offset] = value
            segments[index] = replace(segment, data=bytes(data))
            break
    else:
        raise AssertionError('Mutation offset was not captured')
    records[key] = tuple(segments)
    return replace(snapshot, records=records)


class WorldComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = read_snapshot(BEFORE)
        cls.after = read_snapshot(AFTER)
        cls.map = read_snapshot(FULL_MAP)

    def test_archived_faction_switch_keeps_economy_differences(self):
        result = compare(self.before, self.after)
        self.assertEqual(result['counts']['raw_changed_bytes'], 177)
        self.assertEqual(result['counts']['display_changed_bytes'], 138)
        self.assertEqual(result['counts']['unresolved_changed_bytes'], 39)
        cities = {row['record'] for row in result['byte_difference_examples']}
        self.assertEqual(len(cities), 9)
        self.assertFalse(result['observed_fields_equal'])
        self.assertFalse(result['full_world_verified'])

    def test_every_archived_map_slot_is_compared_and_still_partial(self):
        self.assertEqual(sum(k.startswith('hex:') for k in self.map.records), 48400)
        result = compare(self.map, self.map)
        self.assertTrue(result['observed_fields_equal'])
        self.assertEqual(result['observed_hashes'][0], result['observed_hashes'][1])
        self.assertFalse(result['full_world_verified'])
        self.assertFalse(result['authorize_release'])

    def test_noncenter_last_map_slot_change_is_detected_even_without_examples(self):
        key = 'hex:48399'
        segment = self.map.records[key][0]
        modified = mutate(self.map, key, segment.offset, segment.data[0]^1)
        result = compare(self.map, modified, max_examples=0)
        self.assertEqual(result['counts']['unresolved_changed_bytes'], 1)
        self.assertEqual(result['unresolved_bytes_by_domain'], {'hex': 1})
        self.assertFalse(result['observed_fields_equal'])
        self.assertNotEqual(*result['observed_hashes'])
        self.assertEqual(result['byte_difference_examples'], [])

    def test_removed_record_cannot_disappear_in_intersection(self):
        records = dict(self.before.records)
        removed = next(k for k in records if k.startswith('force:'))
        del records[removed]
        result = compare(self.before, replace(self.before, records=records))
        self.assertEqual(result['removed_records']['count'], 1)
        self.assertEqual(result['removed_records']['examples'], [removed])
        self.assertFalse(result['observed_fields_equal'])

    def test_rng_and_native_task_order_are_not_treated_as_local_presentation(self):
        fields = {'global_rng': 10, 'tasks': [{'officer': 1}, {'officer': 2}]}
        original = replace(self.before, fields=fields)
        modified = replace(original, fields={**fields, 'global_rng': 11, 'tasks': list(reversed(fields['tasks']))})
        result = compare(original, modified)
        self.assertEqual(result['counts']['changed_fields'], 3)
        self.assertFalse(result['observed_fields_equal'])

    def test_pointer_exception_cannot_mask_different_build_or_unknown_fields(self):
        key = next(k for k in self.before.records if k.startswith('army:'))
        segments = self.before.records[key]
        data = next(s.data[0x148-s.offset] for s in segments if s.offset <= 0x148 < s.offset+len(s.data))
        changed = mutate(self.before, key, 0x148, data^1)
        good = compare(self.before, changed)
        self.assertEqual(good['counts']['display_changed_bytes'], 1)
        wrong_build = replace(changed, metadata={**changed.metadata, 'build_sha256': '0'*64})
        rejected = compare(self.before, wrong_build)
        self.assertEqual(rejected['counts']['unresolved_changed_bytes'], 1)
        self.assertFalse(rejected['observed_fields_equal'])
        city = next(k for k in self.before.records if k.startswith('city:'))
        segment = self.before.records[city][0]
        changed = mutate(self.before, city, 0x80, segment.data[0x80-segment.offset]^1)
        self.assertEqual(compare(self.before, changed)['counts']['unresolved_changed_bytes'], 1)

    def test_different_capture_phase_is_not_equal_context(self):
        other = replace(self.before, metadata={**self.before.metadata, 'phase': 'TITLE_INITIALIZING'})
        result = compare(self.before, other)
        self.assertFalse(result['recorded_context_equal'])
        self.assertFalse(result['observed_fields_equal'])

    def test_overlapping_ranges_are_not_silently_rehashed(self):
        records = dict(self.before.records)
        key = next(iter(records))
        segment = records[key][0]
        records[key] = (segment, segment)
        with self.assertRaises(ValueError):
            compare(self.before, replace(self.before, records=records))

    def test_output_cannot_overwrite_input_or_hardlink_alias(self):
        with tempfile.TemporaryDirectory(prefix='world-report-path-', dir=HERE) as folder:
            original = Path(folder)/'input.json'
            original.write_bytes(b'{"evidence":"must survive"}')
            alias = Path(folder)/'alias.json'
            os.link(original, alias)
            report = {'sources': [{'path':str(original)}]}
            for target in (original, alias):
                with self.assertRaises(ValueError):
                    write_report(report, target)
            self.assertEqual(original.read_bytes(), b'{"evidence":"must survive"}')


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WorldComparisonTests))
    folder = HERE/'checkpoint_world_compare_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    names = ('checkpoint_world_compare.py','checkpoint_world_compare_test.py','checkpoint_world_snapshot_reader.py')
    report = dict(result='PASS' if result.wasSuccessful() else 'FAIL', cases=result.testsRun,
        game_accessed=False, full_world_verified=False,
        source_sha256={name: hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in names},
        archive_sha256={str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (BEFORE, AFTER, FULL_MAP)})
    (folder/'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(str(folder/'result.json'))
    raise SystemExit(0 if result.wasSuccessful() else 1)
