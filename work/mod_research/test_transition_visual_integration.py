"""MapWaitGate + durable CheckpointJournal + surface; fixtures, no native access."""
from pathlib import Path
import json, unittest
from hashlib import sha256
from test_checkpoint_presentation import PresentationTests
from authoritative_sync import SyncError, canonical
from checkpoint_journal import CheckpointJournal
from transition_visual_surface import Frame, TransitionSurface, PresentationReceipt, SurfaceError

HERE = Path(__file__).resolve().parent
OLD = Frame(2, 2, bytes([32, 96, 64])*4, 'old-fixture-render-1')
NEW = Frame(2, 2, bytes([96, 128, 48])*4, 'new-fixture-render-2')


def frame_id(frame):
    # Gate frame is a 128-bit generation ID, not the world's SHA or pixel SHA.
    return sha256(canonical({'revision':frame.revision,'pixels':frame.digest})).hexdigest()[:32]


class Bridge:
    """Fixture glue; both gate and local renderer must agree before input opens."""
    def __init__(self, f):
        self.f = f; self.s = TransitionSurface(); self.token = None; self.pending = None
        self.ticket = self.s.begin(f.g.nonce, OLD, native_input_gate_ack=True)

    def paint(self, outcome='PRESENTED'):
        self.s.acknowledge(PresentationReceipt(self.s.ticket, outcome, self.s.ticket.frame.digest))

    def cover_and_reserve(self):
        self.paint()
        assert self.s.may_start_native
        self.f.g.cover_presented({**self.f.cover, 'frame':frame_id(OLD)})
        permit = self.f.g.reserve_load(self.f.host, self.f.old_guest)
        self.s.native_started(self.f.g.nonce)
        return permit

    def restored(self, permit):
        f = self.f
        f.j.complete({'player':'B','epoch':f.p.manifest['epoch'],
            'checkpoint_id':f.p.checkpoint_id,'intent':permit['intent'],
            'world_sha256':f.host['world_sha256'],'viewer_force':2,
            'attachment':f.guest['attachment'],'host_observation':f.host})
        f.g.world_restored(f.host, f.guest)
        # This is the backend's NEW map under the still-visible OLD cover.
        self.pending = (NEW, f.guest['attachment'], f.cover['view'], f.cover['surface'])
        f.g.map_frame_presented({**f.frame, 'frame':frame_id(NEW)})
        assert self.s.ticket.frame == OLD and self.s.input_held

    def prepare(self, frame=NEW, attachment=None, view=None, surface=None):
        f = self.f
        bound = (frame, attachment or f.guest['attachment'], view or f.cover['view'], surface or f.cover['surface'])
        if bound != self.pending: raise SurfaceError('pending new frame/view/attachment/surface mismatch')
        self.token = f.g.begin_reveal(f.host, f.guest)
        if self.token['attachment'] != bound[1]: raise SurfaceError('reveal token changed attachment')
        self.s.prepare_release(f.g.nonce, frame, controller_grant=self.token['token'])

    def finish(self):
        if not self.s._painted: raise SurfaceError('new frame not painted')
        self.f.g.revealed(self.token)
        try: self.s.commit_release(self.f.g.nonce, controller_grant=self.token['token'])
        except BaseException:
            self.f.g.hold('SURFACE_RELEASE_UNCERTAIN'); raise

    @property
    def input_open(self):
        return self.f.g.status()['accept_planning_intents'] and not self.s.input_held

    def fail(self):
        self.f.g.hold('PRESENT_FAILED'); self.s.fail(self.f.g.nonce, '画面呈现失败')


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.f = PresentationTests('test_full_visual_barrier_keeps_room_held_until_new_map')
        self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.b = Bridge(self.f)

    def test_durable_load_to_new_map_requires_both_gate_and_actual_receipt(self):
        b, f = self.b, self.f
        permit = b.cover_and_reserve(); self.assertEqual(f.j.status()['status'], 'INTENT')
        b.restored(permit); self.assertEqual(f.j.status()['status'], 'COMPLETED')
        b.prepare(); self.assertEqual(f.c.phase, 'PLANNING')
        self.assertFalse(b.input_open)
        with self.assertRaises(SurfaceError): b.finish()
        b.paint(); self.assertFalse(b.input_open)
        b.finish(); self.assertTrue(b.input_open)
        self.assertFalse(f.g.status()['native_gameplay_enabled'])

    def test_pending_frame_attachment_view_surface_cannot_be_substituted(self):
        b = self.b; b.restored(b.cover_and_reserve())
        for kwargs in ({'frame':OLD}, {'attachment':'9'*32}, {'view':'9'*32}, {'surface':'9'*32}):
            with self.subTest(kwargs=kwargs), self.assertRaises(SurfaceError): b.prepare(**kwargs)
        self.assertEqual(self.f.c.phase, 'RECONCILING'); self.assertFalse(b.input_open)

    def test_reveal_failure_after_coordinator_planning_keeps_combined_input_closed(self):
        b = self.b; b.restored(b.cover_and_reserve()); b.prepare()
        self.assertEqual(self.f.c.phase, 'PLANNING')
        with self.assertRaises(SurfaceError): b.paint('DEVICE_REMOVED')
        b.fail(); self.assertFalse(b.input_open)
        self.assertEqual(b.s.ticket.frame, OLD)
        with self.assertRaises(SyncError): self.f.g.revealed(b.token)
        self.assertEqual(self.f.j.status()['status'], 'COMPLETED')

    def test_old_cover_receipt_cannot_unlock_new_map(self):
        b = self.b; permit = b.cover_and_reserve(); old = b.s.ticket
        b.restored(permit); b.prepare()
        with self.assertRaises(SurfaceError):
            b.s.acknowledge(PresentationReceipt(old,'PRESENTED',OLD.digest))
        self.assertFalse(b.input_open)

    def test_unknown_load_after_intent_remains_durable_and_covered_on_reopen(self):
        b, f = self.b, self.f; b.cover_and_reserve(); b.fail()
        ident = f.j.identity
        j2 = CheckpointJournal(Path(f.tmp.name)/'checkpoint.sqlite', ident['scope'],ident['manifest'],
            ident['checkpoint_id'],ident['manifest']['epoch'],ident['manifest']['period'],
            ident['manifest']['cut'],ident['attachments'])
        self.assertTrue(j2.status()['native_outcome_unknown'])
        with self.assertRaises(SyncError): f.g.reserve_load(f.host,f.old_guest)
        self.assertFalse(b.input_open); self.assertEqual(b.s.ticket.frame, OLD)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IntegrationTests))
    (HERE/'transition_visual_integration_results.json').write_text(json.dumps({
        'passed':result.wasSuccessful(),'tests_run':result.testsRun,'failures':len(result.failures),
        'errors':len(result.errors),'synthetic_only':True,'native_gameplay':False,
        'real_game_access':False,'renderer_receipts':'synthetic',
        'modules':['PeriodCoordinator','CheckpointJournal','MapWaitGate','TransitionSurface']},indent=2))
    raise SystemExit(not result.wasSuccessful())
