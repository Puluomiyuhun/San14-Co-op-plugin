"""Offline archived native-flow and strict trace-classification regressions."""
import copy
import unittest
import checkpoint_dispatch_handoff_probe as p


class HandoffProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = p.decode_profile()
        cls.native = p.exercise()
        cls.normal = cls.native[0]['samples']
        cls.yielded = cls.native[1]['samples']

    def test_archived_instruction_boundaries(self):
        self.assertEqual(len(self.profile), 13)
        self.assertEqual({r['rva'] for r in self.profile}, {hex(r) for r in p.TAPS})

    def test_native_normal_complete(self):
        result = p.analyze(self.normal)
        self.assertTrue(result['task_chain_observed'])
        self.assertFalse(result['scheduler_fence'])
        self.assertFalse(result['live_authority'])
        self.assertEqual(result['classification'], 'ONE_STATE_TASK_RETURNED_AND_DETACHED')

    def test_native_yield_reaches_same_tail_without_completion(self):
        last = self.yielded[-1]
        self.assertEqual(last['event'], 'dispatcher_common_tail')
        self.assertEqual(last['done'], 0)
        self.assertEqual(last['yielded'], 1)
        self.assertEqual(last['attached'], last['worker'])
        self.assertEqual(p.analyze(self.yielded)['classification'], 'YIELDED_TASK_STILL_OWNED')

    def test_user_return_not_runner_return(self):
        cut = next(i for i,r in enumerate(self.normal) if r['event']=='user_update_return')
        self.assertFalse(p.analyze(self.normal[:cut+1])['task_chain_observed'])
        self.assertEqual(self.normal[cut]['done'], 0)
        self.assertEqual(self.normal[cut]['attached'], self.normal[cut]['worker'])

    def test_runner_done_not_parent_detachment(self):
        cut = next(i for i,r in enumerate(self.normal) if r['event']=='runner_done_store')
        self.assertFalse(p.analyze(self.normal[:cut+1])['task_chain_observed'])
        self.assertEqual(self.normal[cut]['attached'], self.normal[cut]['worker'])

    def test_identity_and_completion_errors(self):
        changes = [(1, 'native_thread', 999), (1, 'thread', 999), (3, 'callable', 999),
                   (5, 'state', 999), (6, 'slot', 999), (7, 'worker', 999),
                   (2, 'done', 1), (4, 'done', 0), (5, 'attached', 0),
                   (6, 'attached', self.normal[6]['worker']), (0, 'yielded', 1),
                   (1, 'stopped', 1), (6, 'thread', 999), (2, 'control', 999),
                   (0, 'thread', self.normal[0]['native_thread'])]
        for index, field, value in changes:
            with self.subTest(index=index, field=field):
                rows = copy.deepcopy(self.normal); rows[index][field] = value
                self.assertEqual(p.analyze(rows)['classification'], 'REJECTED')

    def test_loss_and_unreadable_observations(self):
        for field, value in [('lost_events', 1), ('memory_fault', 'access_violation')]:
            rows = copy.deepcopy(self.normal); rows[3][field] = value
            self.assertEqual(p.analyze(rows)['classification'], 'REJECTED')

    def test_order_duplicate_unknown_and_mismatched_rva(self):
        for index, field, value in [(2, 'seq', 1), (2, 'seq', None),
                                    (2, 'rva', '0x123'), (2, 'event', 'runner_done_store')]:
            rows = copy.deepcopy(self.normal); rows[index][field] = value
            self.assertEqual(p.analyze(rows)['classification'], 'REJECTED')

    def test_missing_every_individual_event_refuses_chain(self):
        for i in range(len(self.normal)):
            rows = copy.deepcopy(self.normal); del rows[i]
            self.assertFalse(p.analyze(rows)['task_chain_observed'])

    def test_duplicate_or_two_task_epochs_never_collapsed_into_one(self):
        rows = copy.deepcopy(self.normal + self.normal)
        for i,r in enumerate(rows): r['seq'] = i + 1
        self.assertFalse(p.analyze(rows)['task_chain_observed'])

    def test_capture_memory_failure_is_data_not_success(self):
        def unreadable(address, size): raise OSError('fixture unreadable')
        row = p.capture_tap(0x50B598, dict(rdi=0x10000, rsp=0x20000), unreadable, 1, 1)
        self.assertEqual(row['memory_fault'], 'OSError')
        self.assertEqual(p.analyze([row])['classification'], 'REJECTED')

    def test_external_flags_cannot_replace_native_chain(self):
        rows = [dict(seq=1, rva='0x50b632', event='dispatcher_common_tail',
                     quiet=True, all_counts_zero=True, native_ready=True, waited_ms=10000)]
        self.assertFalse(p.analyze(rows)['task_chain_observed'])


if __name__ == '__main__': unittest.main(verbosity=2)
