"""Real Room/bootstrap/TLS/SQLite + two projections of each same owned reader.

All game/native Save/load/reward business callbacks remain explicit doubles.
No installed input fence or game process, no post-load reward field attestation.
"""
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import secrets
import sys
import unittest

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]; PRIVATE = ROOT.parent / 'mod_research'
sys.path[:0] = [str(PRIVATE / 'python_deps'), str(ROOT / 'outputs/san14-link')]
import b_observed_completion_test as observed
from authoritative_sync import digest, next_node
from checkpoint_fresh_save_binding import LocalWorldObservation
from reward_checkpoint_fixture import World
from reward_checkpoint_observer import CutObserver, packet
from reward_checkpoint_shared_cut import SharedCutGate
from reward_observed_flow import ObservedRewardFlow, GuestConsumer
from reward_room_flow import Replica, envelope
import b_warm_world as world

OUTPUT = None; ROWS = []


class Cases(observed.Cases):
    def setUp(self):
        super().setUp()
        self.worlds = {p: World(f) for p, f in (('A', 12), ('B', 2))}
        self.worlds['A'].copy_tables_to_bootstrap_double(self.host)
        self.worlds['B'].copy_tables_to_bootstrap_double(self.guest)
        r, q, self.profile = self.first(); reply = self.adapter.apply(r, q, self.profile)
        self.assertTrue(reply['ok']); self.assertTrue(self.c.bootstrap_completed)
        self.assertEqual((self.c.period, self.c.phase), (2, 'PLANNING'))
        for p, w in self.worlds.items():
            w.attachment = self.c.attachments[p]
        self.ports = {p: w.port() for p, w in self.worlds.items()}
        self.reward_key = secrets.token_bytes(32); self.cut_key = secrets.token_bytes(32)
        self.flow = ObservedRewardFlow(self.folder / 'reward-cut', self.room, self.ports['A'],
            self.ports['B'].attachment_id, deepcopy(self.c.node), guest_report_key=self.reward_key)
        self.replica = Replica(self.folder / 'reward-B.sqlite', self.flow.scope, 'B', self.ports['B'])
        self.observers = {p: CutObserver(replica, self.profile)
                          for p, replica in (('A', self.flow.host), ('B', self.replica))}
        self.gate = SharedCutGate(self.room, self.c, self.flow, self.observers['A'], guest_cut_key=self.cut_key)
        self.servers[0][0].room = self.gate
        self.consumer = GuestConsumer(self.b, self.replica, self.reward_key); self.consumer.report()

    def proposal(self, p='A'):
        return envelope(self.flow.scope, 'reward_submit', request_id=secrets.token_hex(16),
            district_id=11 if p == 'A' else 2, officer_ids=[97] if p == 'A' else [101])

    def reward(self, player='A'):
        client = self.a if player == 'A' else self.b
        self.assertTrue(client.request(self.proposal(player))['ok'])
        self.assertEqual(self.gate.pump_one()['status'], 'AWAITING_B')
        self.consumer.consume_one()

    def finish(self, player):
        client = self.a if player == 'A' else self.b
        self.assertTrue(client.request(dict(action='reward_cut_prepare', epoch=self.c.epoch))['ok'])

    def collect(self):
        self.finish('A'); self.finish('B'); challenge = self.gate.prepare_cut()
        self.assertIsNotNone(challenge)
        wire_challenge = self.b.request(dict(action='reward_cut_status'))['challenge']
        self.assertEqual(wire_challenge, challenge)
        self.assertTrue(self.b.request(self.observers['B'].attest(wire_challenge, self.cut_key))['ok'])
        return challenge

    def seal(self):
        for client in (self.a, self.b):
            self.assertTrue(client.request(dict(action='period_ready', epoch=self.c.epoch, ready=True))['ok'])
        permit = self.c.seal_inputs(); self.c.begin_simulation(permit)
        self.assertEqual(self.gate.assert_sealed(permit)['cut'], self.gate.receipt['cut'])
        return permit

    def blocked(self):
        for client in (self.a, self.b):
            self.assertFalse(client.request(dict(action='period_ready', epoch=self.c.epoch, ready=True))['ok'])
        with self.assertRaises(ValueError):
            self.c.seal_inputs()

    def evidence(self, **kw):
        ROWS.append(dict(case=self._testMethodName, state=self.gate.state,
            native_reward_business_double_calls={p: w.calls for p, w in self.worlds.items()},
            proof=self.gate.receipt, coordinator=self.c.status(), **kw))

    def test_nonzero_actual_paired_prefix_reaches_original_save_request(self):
        self.reward('A'); self.reward('B'); self.collect(); proof = self.gate.close_drained()
        self.assertEqual(proof['cut']['sequence'], 2)
        self.assertEqual(proof['descriptor']['reward_sequence'], 2)
        self.assertNotEqual(proof['cut']['world_sha256'], proof['descriptor']['reward_projection_sha256'])
        self.assertEqual(proof['cut']['world_sha256'], proof['host_observation']['world_sample']['partial_sha256'])
        self.assertFalse(proof['full_world_verified']); self.assertFalse(self.c.ready)
        self.assertTrue(self.ports['A'].sampler.failed)  # original executable port retired
        permit = self.seal(); current = self.gate.observe_sealed(deepcopy(self.c.node))
        self.assertEqual(current.world_sha256, permit['world_sha256'])
        # Explicit owned turn-date mutation: only actual world sample is used to
        # reserve generation2; there is no native simulation/save claim here.
        target = next_node(self.c.node); w = self.worlds['A']
        w.memory.pack(w.world + 0x34, '<HBB', target['year'], target['month'], target['day'])
        p = type(self.profile).from_buffer_copy(bytes(self.profile))
        p.loaded.year, p.loaded.month, p.loaded.day = target['year'], target['month'], target['day']
        sample = world.sample(w.reader, scope=self.c.scope, epoch=self.c.epoch, period=self.c.period,
            profile=p, side='A', receipt_key=proof['proof_sha256'], read_birth=lambda: w.birth)
        ob = LocalWorldObservation(w.attachment, target['year'], target['month'], target['day'],
            12, 666, world.CONTRACT, sample['partial_sha256'], True)
        reservation = self.binding.reserve(2, 'mp00000002.s14', ob)
        self.assertEqual(reservation.request['cut'], proof['cut']['sequence'])
        self.assertEqual(self.binding.validate_context()['cut'],
                         {k: proof['cut'][k] for k in ('sequence', 'prefix_sha256')})
        self.assertFalse(self.a.request(self.proposal())['ok'])
        with self.assertRaises(ValueError): self.flow.pump_one()
        self.assertTrue(self.b.request(dict(action='reward_cut_status'))['ok'])
        self.evidence(save_request={**dict(reservation.request),
            'room_id': reservation.request['room_id'].hex()}, two_native_saves_proven=False)

    def test_prepare_blocks_only_own_new_input_and_waits_for_actual_guest(self):
        self.assertTrue(self.a.request(self.proposal())['ok']); self.finish('A')
        self.assertFalse(self.a.request(self.proposal())['ok'])
        self.assertTrue(self.b.request(self.proposal('B'))['ok'])
        self.finish('B'); self.assertIsNone(self.gate.prepare_cut()); self.blocked()
        for _ in range(2):
            self.assertEqual(self.gate.pump_one()['status'], 'AWAITING_B')
            self.assertIsNone(self.gate.prepare_cut()); self.blocked(); self.consumer.consume_one()
        self.collect(); self.assertEqual(self.gate.close_drained()['cut']['sequence'], 2)
        self.evidence()

    def test_empty_keeps_original_cut_and_requires_both_explicit_finish(self):
        self.assertIsNone(self.gate.prepare_cut()); self.finish('A')
        self.assertIsNone(self.gate.prepare_cut()); self.collect()
        proof = self.gate.close_drained(); self.assertEqual(proof['cut'], self.gate.base)
        self.seal(); self.gate.observe_sealed(self.c.node); self.evidence()

    def test_signed_foreign_challenge_holds_without_rewriting_coordinator(self):
        self.reward(); self.finish('A'); self.finish('B'); challenge = self.gate.prepare_cut()
        body = self.observers['B'].capture(challenge); body['challenge_sha256'] = '9' * 64
        self.assertFalse(self.b.request(packet(self.cut_key, body))['ok'])
        self.assertEqual((self.gate.state, self.c.phase), ('HELD', 'HELD'))
        self.assertEqual(self.c.reports['A']['sequence'], 0); self.blocked(); self.evidence()

    def test_world_difference_not_covered_by_reward_hash_is_rejected(self):
        self.reward(); b = self.worlds['B']; address = b.tables['objects'][3000] + 0x14
        b.memory.pack(address, '<B', b.memory.read(address, 1)[0] ^ 1)
        self.collect()
        with self.assertRaisesRegex(ValueError, 'world table'): self.gate.close_drained()
        self.assertEqual(self.c.phase, 'HELD'); self.assertEqual(self.c.reports['A']['sequence'], 0)
        self.evidence()

    def test_loyalty_change_after_pair_fails_actual_observer(self):
        self.reward(); self.finish('A'); self.finish('B'); challenge = self.gate.prepare_cut()
        b = self.worlds['B']; b.memory.pack(b.people[97] + 0x120, '<B', 99)
        with self.assertRaises(Exception): self.observers['B'].attest(challenge, self.cut_key)
        self.assertIsNone(self.gate.close_drained()); self.blocked()
        self.assertEqual(self.c.reports['A']['sequence'], 0); self.evidence()

    def test_readonly_postseal_observer_detects_cost_drift_after_port_retired(self):
        self.reward(); self.collect(); self.gate.close_drained(); self.seal()
        a = self.worlds['A']; a.memory.pack(a.cities[19] + 0x34, '<I', 1)
        with self.assertRaisesRegex(ValueError, 'loyalty/cost'): self.gate.observe_sealed(self.c.node)
        self.assertEqual(self.c.phase, 'HELD'); self.evidence()

    def test_disconnect_during_collection_retires_and_never_releases_ready(self):
        self.reward(); self.collect()
        connection = self.room.players['B']['connection']
        self.gate.disconnect('B', connection)
        with self.assertRaises(ValueError): self.gate.close_drained()
        self.assertEqual(self.c.phase, 'HELD'); self.assertTrue(any(self.c.inflight.values()))
        self.evidence()

    def test_entire_guest_consumer_survives_status_to_next_closure_race(self):
        self.reward(); self.finish('A'); self.finish('B')
        self.assertEqual(self.b.request(dict(action='reward_cut_status'))['state'], 'ACTIVE')
        challenge = self.gate.prepare_cut()  # owner advances before B's next RPC
        self.assertEqual(self.consumer.consume_one()['status'], 'QUEUE_EMPTY')
        self.assertIsNone(self.consumer.failed)
        self.assertTrue(self.b.request(self.observers['B'].attest(challenge, self.cut_key))['ok'])
        self.gate.close_drained()
        self.assertEqual(self.consumer.consume_one()['status'], 'QUEUE_EMPTY')
        self.assertIsNone(self.consumer.failed)
        foreign = envelope(self.flow.scope, 'reward_next'); foreign['epoch'] = '0' * 32
        self.assertFalse(self.b.request(foreign)['ok'])
        self.assertFalse(self.b.request(self.proposal('B'))['ok'])
        self.assertEqual([w.calls for w in self.worlds.values()], [1, 1]); self.evidence()

    def test_postseal_recheck_reads_real_journal_not_only_frozen_receipt(self):
        self.reward(); self.collect(); self.gate.close_drained(); self.seal()
        self.flow.host.journal._halt('Owned late journal failure')
        with self.assertRaisesRegex(Exception, 'Owned late journal failure'):
            self.gate.observe_sealed(self.c.node)
        self.assertEqual(self.c.phase, 'HELD'); self.assertEqual(self.worlds['A'].calls, 1)
        self.evidence()


def pins():
    paths = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, '__file__', None)}
    paths.add(Path(__file__).resolve())
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)
            if p.is_relative_to(ROOT) and p.suffix == '.py'}


if __name__ == '__main__':
    OUTPUT = PRIVATE / 'reward_checkpoint_shared_cut_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True); observed.transport.OUTPUT = OUTPUT
    before = pins(); stream = io.StringIO()
    suite = unittest.TestSuite(Cases(name) for name in Cases.__dict__ if name.startswith('test_'))
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (OUTPUT / 'test.log').write_text(stream.getvalue(), encoding='utf-8'); after = pins()
    report = dict(result='PASS' if result.wasSuccessful() and before == after else 'FAIL', tests=result.testsRun,
        sources=after, inputs_unchanged=before == after, cases=ROWS,
        actual_room_bootstrap_TLS_SQLite=True, same_reader_reward_and_world_projection=True,
        native_RAM_save_load_reward_business_doubles=True,
        physical_input_fence=False, full_world_verified=False,
        reward_fields_verified_after_checkpoint_load=False, native_gameplay_enabled=False, game_access=False,
        failures=[(str(t), detail) for t, detail in result.errors + result.failures])
    report['artifacts'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(OUTPUT / 'result.json'); print(stream.getvalue()); raise SystemExit(report['result'] != 'PASS')
