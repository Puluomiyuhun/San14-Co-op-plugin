"""Actual TLS/Receiver/Journal through received apply; native/rules bridge double."""
from dataclasses import replace
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT.parent/'mod_research'
sys.path[:0] = [str(PRIVATE/'python_deps'), str(ROOT/'outputs/san14-link')]
import b_warm_room_test as transport
from b_warm_received_apply import ReceivedApply
from b_warm_room import ReceivedCheckpoint
from b_warm_profile_contract import Profile, Date, Identity
from human_rules_world_lifecycle import NextWorldRequest
from authoritative_sync import canonical, CheckpointReceiver

OUTPUT = None
EVIDENCE = []


def sha(raw): return hashlib.sha256(raw).hexdigest()


class BridgeDouble:
    """Trusted local dependency substituted explicitly; no native proof here."""
    def __init__(self, fail=False):
        self.calls = []; self.fail = fail
        self.lifecycle = SimpleNamespace(current=SimpleNamespace(
            module=SimpleNamespace(pid=123, birth=2**60+7)))
        self.warm = SimpleNamespace(reader=SimpleNamespace(pid=123))

    def replace(self, request, profile, source, *, observe_loaded, prepare_rules):
        self.calls.append(dict(checkpoint=request.checkpoint, generation=request.generation,
                               file_sha256=sha(Path(source).read_bytes())))
        if self.fail: raise RuntimeError('Explicit native bridge double failure')
        observed = observe_loaded(request)
        prepare_rules(request, observed)
        accepted = dict(result='PASS_WARM_LOAD_RETIRED', receipt_key='2'*64,
            source_force=profile.source.force, source_ruler=profile.source.ruler,
            target_force=profile.target.force, target_ruler=profile.target.ruler,
            ready_authorized=False, full_world_verified=False)
        completion = dict(accepted=accepted, profile_sha256=sha(bytes(profile)),
            attempt=2**63+3, pid=123, birth=2**60+7, slots_restored=True,
            snapshot=dict(date=dict(year=profile.loaded.year, month=profile.loaded.month, day=profile.loaded.day),
                          player=dict(force_id=profile.target.force, ruler_id=profile.target.ruler)))
        rules = dict(phase='RULES_REBOUND', generation=request.generation, checkpoint=request.checkpoint,
                     ready=False, fence_released=False, full_world_verified=False)
        return dict(result='WARM_LOAD_AND_RULES_REBOUND', generation=request.generation,
            checkpoint=request.checkpoint, details=dict(completion=completion, rules=rules),
            ready=False, fence_released=False, full_world_verified=False)


class Cases(unittest.TestCase):
    # Reuse actual room/TLS lifecycle, without inheriting/rerunning its old tests.
    setUp = transport.RoomTests.setUp
    tearDown = transport.RoomTests.tearDown
    offer = transport.RoomTests.offer
    receive = transport.RoomTests.receive

    def inputs(self, received):
        m = received.context()['manifest']; d = m['node']; p = Profile()
        p.file.name = b'svdexccSC03.s14'; p.file.slot = 63
        p.file.size = m['parts']['world.s14']['size']
        p.file.sha256[:] = bytes.fromhex(m['parts']['world.s14']['sha256'])
        p.before = Date(203, 8, 1); p.loaded = Date(d['year'], d['month'], d['day'])
        p.source = Identity(666, 12, 11); p.target = Identity(952, 2, 2); p.currentForce = 2
        # Local native epoch is deliberately distinct from the room timeline.
        request = NextWorldRequest(2, received.context()['checkpoint_id'], b'\x7a'*16,
                                   d['year'], d['month'], d['day'])
        return request, p

    def adapter(self, bridge, control=None):
        holds = []
        result = ReceivedApply(bridge, control or self.b, scope=self.c.scope,
            epoch=self.c.epoch, period=self.c.period, attachments=self.c.attachments,
            on_hold=lambda reason: holds.append(str(reason)))
        return result, holds

    def call(self, adapter, received, request, profile, **options):
        events = []
        def observe(req): events.append('observe_loaded_double'); return {'explicit_double': True}
        def prepare(req, observed):
            self.assertTrue(observed['explicit_double']); events.append('prepare_rules_double')
        result = adapter.apply(received, request, profile, observe_loaded=observe, prepare_rules=prepare, **options)
        return result, events

    def no_ack(self):
        self.assertIsNone(self.a.request(dict(action='status'))['state']['warm_completion'])
        self.assertEqual((self.c.period, self.c.phase), (1, 'RECONCILING'))

    def test_actual_received_bytes_to_diagnostic_ack(self):
        package = self.offer(1); received = self.receive(package)
        request, profile = self.inputs(received); bridge = BridgeDouble(); adapter, holds = self.adapter(bridge)
        result, events = self.call(adapter, received, request, profile)
        self.assertEqual(events, ['observe_loaded_double', 'prepare_rules_double'])
        self.assertEqual(len(bridge.calls), 1); self.assertFalse(holds)
        ack = self.a.request(dict(action='status'))['state']['warm_completion']
        self.assertEqual(ack['packet']['checkpoint_id'], package.checkpoint_id)
        self.assertEqual(ack['packet']['profile_sha256'], sha(bytes(profile)))
        self.assertEqual(ack['packet']['attempt'], str(2**63+3))
        self.assertTrue((received.directory/'warm-local-load-intent.json').is_file())
        self.assertTrue((received.directory/'warm-local-load-completion.json').is_file())
        self.assertTrue((received.directory/'warm-ack-attempt.json').is_file())
        self.assertEqual(received.journal.status()['status'], 'STAGED')
        self.assertEqual((self.c.period, self.c.phase), (1, 'RECONCILING'))
        self.assertFalse(self.b.request(dict(action='period_ready', epoch=self.c.epoch, ready=True))['ok'])
        self.assertFalse(ack['ready_authorized']); self.assertFalse(ack['full_world_verified'])
        EVIDENCE.append(dict(case='actual-transfer-to-ack', calls=bridge.calls, events=events, result=result,
                             native_rules_load='EXPLICIT_BRIDGE_DOUBLE', ready=False))

    def test_foreign_profile_request_and_scope_do_not_load(self):
        package = self.offer(1)
        for label in ('profile_hash', 'profile_force', 'request_checkpoint', 'request_date', 'received_scope', 'bridge_pid'):
            with self.subTest(label=label):
                received = self.receive(package, label); request, profile = self.inputs(received)
                if label == 'profile_hash': profile.file.sha256[0] ^= 1
                if label == 'profile_force': profile.target.force = 3
                if label == 'request_checkpoint': request = replace(request, checkpoint='9'*64)
                if label == 'request_date': request = replace(request, day=21)
                if label == 'received_scope':
                    ctx = received.context(); ctx['scope']['room_id'] = '8'*32
                    received = ReceivedCheckpoint(canonical(ctx), received.directory, received.journal)
                bridge = BridgeDouble()
                if label == 'bridge_pid': bridge.warm.reader.pid = 124
                with self.assertRaises(Exception):
                    adapter, holds = self.adapter(bridge)
                    self.call(adapter, received, request, profile)
                self.assertFalse(bridge.calls); self.no_ack()
                self.assertFalse((received.directory/'warm-local-load-completion.json').exists())
        EVIDENCE.append(dict(case='foreign-inputs-rejected', bridge_calls=0, variants=6))

    def test_load_failure_durable_intent_blocks_recreated_adapter(self):
        package = self.offer(1); received = self.receive(package); request, profile = self.inputs(received)
        bridge = BridgeDouble(True); adapter, holds = self.adapter(bridge)
        with self.assertRaisesRegex(RuntimeError, 'Explicit native'): self.call(adapter, received, request, profile)
        self.assertEqual(len(bridge.calls), 1); self.assertTrue(holds); self.no_ack()
        self.assertTrue((received.directory/'warm-local-load-intent.json').is_file())
        self.assertFalse((received.directory/'warm-local-load-completion.json').exists())
        again = ReceivedCheckpoint(received.context_json, received.directory, received.journal)
        second = BridgeDouble(); fresh, more_holds = self.adapter(second)
        with self.assertRaises(Exception): self.call(fresh, again, request, profile)
        self.assertFalse(second.calls); self.no_ack()
        EVIDENCE.append(dict(case='load-failed-no-replay', native_attempts=1, recreated_native_attempts=0,
                             journal=received.journal.status()['status'], holds=holds))

    def test_completion_from_another_process_is_not_acknowledged(self):
        package = self.offer(1)
        for field in ('pid', 'birth'):
            with self.subTest(field=field):
                received = self.receive(package, field); request, profile = self.inputs(received)
                class ForeignCompletion(BridgeDouble):
                    def replace(inner, *args, **kwargs):
                        outcome = super().replace(*args, **kwargs)
                        outcome['details']['completion'][field] += 1
                        return outcome
                bridge = ForeignCompletion(); adapter, holds = self.adapter(bridge)
                with self.assertRaises(Exception): self.call(adapter, received, request, profile)
                self.assertEqual(len(bridge.calls), 1); self.assertTrue(holds); self.no_ack()
                self.assertTrue((received.directory/'warm-local-load-intent.json').is_file())
                self.assertFalse((received.directory/'warm-local-load-completion.json').exists())
        EVIDENCE.append(dict(case='foreign-completion-process', variants=2, ack_sent=False))

    def test_actual_journal_intent_reservation_remains_uncompleted(self):
        package = self.offer(1); received = self.receive(package); request, profile = self.inputs(received)
        receiver = CheckpointReceiver(package.manifest, package.checkpoint_id, self.c.scope,
                                     self.c.epoch, self.c.period, package.manifest['cut'])
        for chunk in package.chunks(): receiver.accept(chunk)
        self.c.received('B', self.c.epoch, receiver)
        intent = self.c.begin_guest_load('B', self.c.epoch)
        host = dict(attachment=self.c.attachments['A'], world_sha256=package.manifest['world_sha256'],
                    node=package.manifest['node'])
        guest = dict(attachment=self.c.attachments['B'], viewer_force=2, safe_boundary=True)
        reservation = received.journal.reserve_load(intent, host, guest)
        wrong = {**reservation, 'intent': '7'*32}
        bridge = BridgeDouble(); rejected, _ = self.adapter(bridge)
        with self.assertRaises(Exception): self.call(rejected, received, request, profile, reservation=wrong)
        self.assertFalse(bridge.calls); self.no_ack()
        self.assertFalse((received.directory/'warm-local-load-intent.json').exists())
        good, holds = self.adapter(bridge)
        result, _ = self.call(good, received, request, profile, reservation=reservation)
        self.assertEqual(len(bridge.calls), 1); self.assertFalse(holds)
        self.assertEqual(received.journal.status()['status'], 'INTENT')
        self.assertEqual(self.c.load_intent, intent); self.assertEqual(self.c.period, 1)
        self.assertFalse(self.c.applied_receipts)
        self.assertEqual(result['completion']['profile_sha256'], sha(bytes(profile)))
        self.assertIsNotNone(self.a.request(dict(action='status'))['state']['warm_completion'])
        EVIDENCE.append(dict(case='persisted-intent-and-exact-reservation', wrong_reservation_loads=0,
                             native_attempts=1, formal_journal='INTENT', native_boundary='EXPLICIT_MODEL', ready=False))

    def test_delivered_ack_lost_reply_never_repeats_native(self):
        package = self.offer(1); received = self.receive(package); request, profile = self.inputs(received)
        delivered = []
        class LoseReply:
            player_id = 'B'
            def request(_, packet):
                reply = self.b.request(packet); self.assertTrue(reply['ok']); delivered.append(packet)
                raise EOFError('Actual TLS delivered ACK; caller did not receive reply')
        bridge = BridgeDouble(); adapter, holds = self.adapter(bridge, LoseReply())
        with self.assertRaises(EOFError): self.call(adapter, received, request, profile)
        self.assertEqual(len(bridge.calls), 1); self.assertEqual(len(delivered), 1); self.assertTrue(holds)
        self.assertTrue((received.directory/'warm-local-load-completion.json').is_file())
        self.assertTrue((received.directory/'warm-ack-attempt.json').is_file())
        self.assertIsNotNone(self.a.request(dict(action='status'))['state']['warm_completion'])
        with self.assertRaises(Exception): self.call(adapter, received, request, profile)
        second = BridgeDouble(); fresh, _ = self.adapter(second)
        reopened = ReceivedCheckpoint(received.context_json, received.directory, received.journal)
        with self.assertRaises(Exception): self.call(fresh, reopened, request, profile)
        self.assertFalse(second.calls); self.assertEqual(len(delivered), 1)
        self.assertEqual((self.c.period, self.c.phase), (1, 'RECONCILING'))
        EVIDENCE.append(dict(case='ack-reply-lost-no-native-repeat', sent=1, native_attempts=1, ready=False))


def pins():
    paths = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, '__file__', None)}
    paths.add(Path(__file__).resolve())
    return {str(p): sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix == '.py'}


if __name__ == '__main__':
    OUTPUT = PRIVATE/'b_warm_received_apply_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True); transport.OUTPUT = OUTPUT
    before = pins(); stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(), encoding='utf-8')
    sources = pins(); stable = all(sources.get(k) == v for k, v in before.items())
    report = dict(family='san14.b-warm-received-apply.v1',
        result='PASS' if result.wasSuccessful() and result.testsRun == 6 and stable else 'FAIL',
        tests=result.testsRun, sources=sources, inputs_unchanged=stable, cases=EVIDENCE,
        actual_tls=True, actual_receiver_journal=True, native_rules_load=False, game_access=False,
        ready=False, failures=[(str(t), detail) for t, detail in result.failures+result.errors])
    report['artifacts'] = {str(p): sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(OUTPUT/'result.json'); print(stream.getvalue())
    raise SystemExit(0 if report['result'] == 'PASS' else 1)
