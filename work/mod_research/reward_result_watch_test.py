"""Production GameReader/context sampling on owned bytes; no live process."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import reward_result_watch as watch
from reward_observed_fixture import World

HERE = Path(__file__).resolve().parent
PRIVATE = HERE.parents[2]/'mod_research'
OUTPUT = None


class Cases(unittest.TestCase):
    def sample(self, world):
        return watch.capture(world.reader, [12, 2], actor=world.viewer, read_birth=lambda: world.birth)

    def test_normal_menu_shaped_result_and_additional_field_are_observations_only(self):
        world = World(12); before = self.sample(world)
        context = watch.reward.capture_context(world.reader, 12)
        world.execute(watch.reward.make_command(context, 11, [97]))
        world.memory.pack(world.world+0x80, '<I', 1)
        after = self.sample(world); result = watch.compare_samples(before, after)
        self.assertEqual(result['result'], 'REWARD_SHAPED_CHANGE_OBSERVED')
        self.assertEqual(result['auxiliary_changes'], {'world_80_u32': {'before': 0, 'after': 1}})
        self.assertFalse(result['native_completion_observed']); self.assertFalse(result['full_reward_effects_verified'])
        self.assertFalse(result['replica_applied']); self.assertEqual(world.calls, 1)
        # Same code also accepts serialized records without integer-key drift.
        self.assertEqual(watch.compare_samples(json.loads(json.dumps(before)), json.loads(json.dumps(after))), result)

    def test_no_operation_or_unrelated_change_refused(self):
        world = World(12); before = self.sample(world)
        with self.assertRaises(ValueError): watch.compare_samples(before, self.sample(world))
        world.memory.pack(world.people[97]+0x120, '<B', 84)
        with self.assertRaises(ValueError): watch.compare_samples(before, self.sample(world))

    def test_changed_incarnation_or_date_cannot_be_compared(self):
        world = World(12); before = self.sample(world)
        world.execute(watch.reward.make_command(watch.reward.capture_context(world.reader, 12), 11, [97]))
        world.birth += 1
        with self.assertRaisesRegex(ValueError, 'Process/world/date/viewer'): watch.compare_samples(before, self.sample(world))

    def test_active_menu_rejected_without_mutation(self):
        world = World(12); world.memory.pack(world.states[-1]+0x470, '<I', 3)
        with self.assertRaisesRegex(ValueError, 'Planning identity'): self.sample(world)
        self.assertEqual(world.calls, 0)

    def test_complete_double_sample_drift_refused(self):
        world = World(12); original = watch.reward.capture_context; calls = []
        def changing(reader, force):
            result = original(reader, force); calls.append(force)
            if len(calls) == 2: world.memory.pack(world.people[97]+0x120, '<B', 81)
            return result
        with patch.object(watch.reward, 'capture_context', side_effect=changing):
            with self.assertRaisesRegex(ValueError, 'two complete samples'): self.sample(world)

    def test_cli_help_and_exclusive_record_no_process(self):
        with patch.object(watch, 'GameReader', side_effect=AssertionError('must not open')), redirect_stdout(io.StringIO()):
            self.assertEqual(watch.main([]), 0)
        path = OUTPUT/'sample.json'; value = self.sample(World(12))
        watch.write_new(path, value)
        with self.assertRaises(FileExistsError): watch.write_new(path, {})
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')), value)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if __name__ == '__main__':
    OUTPUT = PRIVATE/'reward_result_watch_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f'); OUTPUT.mkdir(parents=True)
    # The standard collector statically resolves the real reader/delta closure.
    import b_portable_release_export as collector
    sources, _, _ = collector.python_closure([Path(__file__)])
    sources = {str(p): h for p, h in sources.items()}
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(), encoding='utf-8')
    stable = all(sha(p) == h for p, h in sources.items())
    report = dict(result='PASS' if result.wasSuccessful() and stable else 'FAIL', tests=result.testsRun,
        sources=sources, inputs_unchanged=stable, game_access=False, native_executed=False,
        production_reader_on_owned_bytes=True, native_business_is_fixture=True,
        artifacts={str(p): sha(p) for p in OUTPUT.rglob('*') if p.is_file()})
    (OUTPUT/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(stream.getvalue()); print(OUTPUT/'result.json'); raise SystemExit(report['result'] != 'PASS')
