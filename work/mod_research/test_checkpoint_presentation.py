"""Presentation/journal/coordinator integration using synthetic worlds only."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'outputs'/'san14-link'))
from authoritative_sync import *
from checkpoint_journal import CheckpointJournal
from checkpoint_presentation import MapWaitGate
from test_authoritative_sync import bound_room, NODE, NEXT, OLD, HOST


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='map-wait-', dir=HERE)
        self.addCleanup(self.tmp.cleanup)
        scope = scope_from_room(bound_room())
        self.c = PeriodCoordinator(scope, 'fixture-map.v1', digest(OLD),
                                   {'A': 'a'*32, 'B': 'b'*32}, NODE)
        for player in ('A', 'B'):
            self.c.set_ready(player, self.c.epoch, True)
        self.c.begin_simulation(self.c.seal_inputs())
        cut = {k: self.c.seal[k] for k in ('sequence', 'prefix_sha256')}
        p = CheckpointPackage(scope, self.c.epoch, 1, cut, NEXT, self.c.state_contract,
            digest(HOST), {'world.s14': canonical(HOST), 'adapter.json': b'{"fixture":true}'},
            source_player='A')
        self.p = p
        self.c.offer_checkpoint('A', p.manifest)
        r = CheckpointReceiver(p.manifest, p.checkpoint_id, scope, self.c.epoch, 1, cut)
        for chunk in p.chunks(): r.accept(chunk)
        self.j = CheckpointJournal(Path(self.tmp.name)/'checkpoint.sqlite', scope, p.manifest,
            p.checkpoint_id, self.c.epoch, 1, cut, self.c.attachments, create=True)
        self.j.stage(r); self.c.received('B', self.c.epoch, r)
        self.g = MapWaitGate(self.c, self.j)
        self.host = {'attachment': 'a'*32, 'world_sha256': digest(HOST), 'node': NEXT}
        self.old_guest = {'attachment': 'b'*32, 'viewer_force': 2, 'safe_boundary': True}
        self.guest = {**self.old_guest, 'attachment': 'c'*32, 'world_sha256': digest(HOST), 'node': NEXT}
        self.cover = {'presentation': self.g.nonce, 'checkpoint_id': p.checkpoint_id,
            'attachment': 'b'*32, 'frame': 'd'*32, 'view': 'e'*32, 'surface': 'f'*32,
            'window_mode': 'windowed', 'visible': True, 'input_blocked': True}
        self.frame = {'presentation': self.g.nonce, 'checkpoint_id': p.checkpoint_id,
            'attachment': 'c'*32, 'frame': '1'*32, 'view': 'e'*32, 'surface': 'f'*32,
            'viewer_force': 2, 'kind': 'NATIVE_PLANNING_MAP',
            'window_mode': 'windowed', 'cover_visible': True, 'input_blocked': True}

    def covered(self):
        self.g.cover_presented(self.cover)

    def loading(self):
        self.covered()
        self.permit = self.g.reserve_load(self.host, self.old_guest)

    def restored(self):
        self.loading()
        self.receipt = {'player': 'B', 'epoch': self.p.manifest['epoch'],
            'checkpoint_id': self.p.checkpoint_id, 'intent': self.permit['intent'],
            'world_sha256': digest(HOST), 'viewer_force': 2, 'attachment': 'c'*32,
            'host_observation': self.host}
        self.j.complete(self.receipt)
        self.g.world_restored(self.host, self.guest)

    def reveal_ready(self):
        self.restored(); self.g.map_frame_presented(self.frame)

    def test_full_visual_barrier_keeps_room_held_until_new_map(self):
        self.restored()
        self.assertEqual(self.c.phase, 'RECONCILING')
        for player in ('A', 'B'):
            with self.assertRaises(SyncError): self.c.set_ready(player, self.c.epoch, True)
        self.assertFalse(self.g.status()['accept_planning_intents'])
        self.g.map_frame_presented(self.frame)
        self.assertEqual(self.c.phase, 'RECONCILING')
        token = self.g.begin_reveal(self.host, self.guest)
        self.assertEqual(self.c.phase, 'PLANNING')
        self.assertFalse(self.g.status()['accept_planning_intents'])
        self.g.revealed(token)
        self.assertTrue(self.g.status()['accept_planning_intents'])
        self.assertFalse(self.g.status()['request_map_cover'])
        self.assertFalse(self.g.status()['native_gameplay_enabled'])

    def test_no_load_before_cover_is_actually_presented(self):
        with self.assertRaises(SyncError): self.g.reserve_load(self.host, self.old_guest)
        self.assertIsNone(self.c.load_intent)
        self.assertEqual(self.j.status()['status'], 'STAGED')

    def test_stale_cover_wrong_surface_attachment_and_unblocked_input(self):
        for key, value in [('presentation', '0'*32), ('checkpoint_id', '0'*64),
                           ('attachment', '0'*32), ('surface', None), ('visible', False),
                           ('input_blocked', False), ('input_blocked', 1)]:
            with self.subTest(key=key, value=value), self.assertRaises(SyncError):
                self.g.cover_presented({**self.cover, key: value})
        self.assertEqual(self.g.phase, 'WAITING_FOR_COVER')

    def test_cover_failure_prevents_any_load(self):
        self.g.hold('COVER_PRESENTATION_FAILED')
        with self.assertRaises(SyncError): self.g.reserve_load(self.host, self.old_guest)
        self.assertIsNone(self.c.load_intent)

    def test_exclusive_fullscreen_or_unknown_mode_cannot_start_load(self):
        for mode in ('exclusive_fullscreen', 'unknown', None):
            with self.subTest(mode=mode), self.assertRaises(SyncError):
                self.g.cover_presented({**self.cover, 'window_mode': mode})
        self.assertIsNone(self.c.load_intent)
        self.assertEqual(self.j.status()['status'], 'STAGED')

    def test_borderless_supported_but_mode_change_requires_new_surface_check(self):
        self.cover['window_mode'] = 'borderless'
        self.restored()
        with self.assertRaises(SyncError): self.g.map_frame_presented(self.frame)
        self.g.map_frame_presented({**self.frame, 'window_mode': 'borderless'})
        token = self.g.begin_reveal(self.host, self.guest)
        self.g.revealed(token)
        self.assertTrue(self.g.status()['accept_planning_intents'])

    def test_duplicate_load_never_gets_a_second_permit(self):
        self.loading()
        with self.assertRaises(SyncError): self.g.reserve_load(self.host, self.old_guest)
        self.assertEqual(self.j.status()['status'], 'INTENT')

    def test_missing_receipt_cannot_release_cover(self):
        self.loading()
        with self.assertRaises(SyncError): self.g.world_restored(self.host, self.guest)
        self.assertTrue(self.g.status()['request_map_cover'])
        self.assertEqual(self.c.phase, 'RECONCILING')

    def test_old_world_frame_cannot_release_new_world(self):
        self.restored()
        for key, value in [('frame', self.cover['frame']), ('attachment', 'b'*32),
                           ('presentation', '0'*32), ('checkpoint_id', '0'*64)]:
            with self.subTest(key=key), self.assertRaises(SyncError):
                self.g.map_frame_presented({**self.frame, key: value})
        self.assertEqual(self.c.phase, 'RECONCILING')

    def test_title_loading_and_unrestored_view_are_not_a_map(self):
        self.restored()
        for key, value in [('kind', 'CLoadState'), ('kind', 'CTitleState'),
                           ('view', '0'*32), ('surface', '0'*32), ('viewer_force', 12),
                           ('cover_visible', False), ('input_blocked', False)]:
            with self.subTest(key=key), self.assertRaises(SyncError):
                self.g.map_frame_presented({**self.frame, key: value})

    def test_host_changes_between_world_check_and_reveal(self):
        self.reveal_ready()
        with self.assertRaises(SyncError):
            self.g.begin_reveal({**self.host, 'world_sha256': '0'*64}, self.guest)
        self.assertEqual(self.c.phase, 'RECONCILING')
        self.assertTrue(self.g.status()['request_map_cover'])

    def test_guest_reloads_between_world_check_and_reveal(self):
        self.reveal_ready()
        with self.assertRaises(SyncError):
            self.g.begin_reveal(self.host, {**self.guest, 'attachment': '9'*32})
        self.assertEqual(self.c.phase, 'RECONCILING')

    def test_unknown_result_keeps_covered_and_will_not_auto_retry(self):
        self.loading(); self.g.hold('NATIVE_LOAD_OUTCOME_UNKNOWN')
        for callback in (lambda: self.g.reserve_load(self.host, self.old_guest),
                         lambda: self.g.map_frame_presented(self.frame),
                         lambda: self.g.begin_reveal(self.host, self.guest)):
            with self.assertRaises(SyncError): callback()
        self.assertTrue(self.j.status()['native_outcome_unknown'])
        self.assertEqual(self.c.phase, 'RECONCILING')

    def test_disconnect_during_reveal_cannot_unlock(self):
        self.reveal_ready(); token = self.g.begin_reveal(self.host, self.guest)
        self.c.connection('B', False)
        with self.assertRaises(SyncError): self.g.revealed(token)
        self.assertFalse(self.g.status()['accept_planning_intents'])

    def test_stale_reveal_ack_does_not_unlock(self):
        self.reveal_ready(); token = self.g.begin_reveal(self.host, self.guest)
        with self.assertRaises(SyncError): self.g.revealed({**token, 'token': '0'*32})
        self.assertFalse(self.g.status()['accept_planning_intents'])
        self.g.revealed(token)

    def test_failed_renderer_keeps_reveal_ack_from_unlocking(self):
        self.reveal_ready(); token = self.g.begin_reveal(self.host, self.guest)
        self.g.hold('RENDER_SURFACE_LOST')
        with self.assertRaises(SyncError): self.g.revealed(token)
        self.assertTrue(self.g.status()['request_map_cover'])

    def test_next_epoch_invalidates_old_gate(self):
        self.reveal_ready(); token = self.g.begin_reveal(self.host, self.guest)
        self.g.revealed(token)
        for player in ('A', 'B'): self.c.set_ready(player, self.c.epoch, True)
        self.c.begin_simulation(self.c.seal_inputs())
        self.assertFalse(self.g.status()['accept_planning_intents'])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PresentationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'result': 'PASS' if result.wasSuccessful() else 'FAIL',
              'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'real_game_access': False, 'frames_and_renderer_reports': 'synthetic',
              'native_visual_cover_implemented': False, 'native_input_interception_implemented': False,
              'native_gameplay_enabled': False}
    (HERE/'checkpoint-presentation-tests.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
