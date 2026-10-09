"""Two real TLS/journal/coordinator periods; native and memory are explicit doubles."""
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT.parent/'mod_research'
sys.path[:0] = [str(PRIVATE/'python_deps'), str(ROOT/'outputs/san14-link')]
import b_warm_room_test as transport
import b_warm_received_apply_test as apply_test
import b_warm_world as world
from b_warm_world_test import Reader
from b_warm_projection import TrustedProjection, host_observation, receiver_from_journal
from b_warm_received_apply import ReceivedApply
from b_warm_profile_contract import Profile, Date, Identity
from human_rules_world_lifecycle import NextWorldRequest
from checkpoint_fresh_save_binding_test import model_artifact, run_model
from authoritative_sync import PeriodCoordinator, scope_from_room, next_node

OUTPUT = None
EVIDENCE = []


def sha(raw): return hashlib.sha256(raw).hexdigest()


class BridgeDouble(apply_test.BridgeDouble):
    def replace(self, *args, **kwargs):
        # Frozen prior double used two arguments; real WorldLifecycle calls
        # prepare(expected) once. Adapt only this successor's fixture boundary.
        prepare = kwargs['prepare_rules']
        kwargs['prepare_rules'] = lambda req, observed: prepare(observed)
        outcome = super().replace(*args, **kwargs)
        c = outcome['details']['completion']
        c['accepted']['input_exclusion_proven'] = False
        c['attempt'] += len(self.calls)
        c['accepted']['receipt_key'] = sha(('explicit native load double '+str(len(self.calls))).encode())
        return outcome


class Joint(unittest.TestCase):
    tearDown = transport.RoomTests.tearDown
    receive = transport.RoomTests.receive

    def setUp(self):
        original_manifest = transport.manifest
        def manifest():
            value = original_manifest(); value['profile']['game_sha256'] = world.objects.GAME_SHA256
            return value
        def coordinator(room):
            c = PeriodCoordinator(scope_from_room(room), world.CONTRACT, 'd'*64,
                {'A': 'a'*32, 'B': 'b'*32}, dict(year=203, month=8, day=1, phase='PLANNING_BOUNDARY'))
            room.bind_coordinator(c)
            for side in ('A', 'B'): c.applied_prefix(side, c.epoch, 9, 'e'*64, 'd'*64, c.attachments[side])
            return c
        with patch.object(transport, 'manifest', manifest), patch.object(transport, 'make_coordinator', coordinator):
            transport.RoomTests.setUp(self)

    def test_two_tls_periods_through_actual_loaded(self):
        bridge = BridgeDouble(); holds = []; rows = []
        readers = {'A': Reader('A'), 'B': Reader('B', 0x1000000000)}
        readers['B'].pid = bridge.lifecycle.current.module.pid
        birth = bridge.lifecycle.current.module.birth
        for generation in (1, 2):
            before_epoch, before_attachment = self.c.epoch, self.c.attachments['B']
            node = next_node(self.c.node)
            data = ('EXPLICIT MODEL SAVE PERIOD '+str(generation)).encode()*4000
            profile = Profile(); profile.file.name = b'svdexccSC03.s14'; profile.file.slot = 63
            profile.file.size = len(data); profile.file.sha256[:] = bytes.fromhex(sha(data))
            profile.before = Date(self.c.node['year'], self.c.node['month'], self.c.node['day'])
            profile.loaded = Date(node['year'], node['month'], node['day'])
            profile.source = Identity(666, 12, 11); profile.target = Identity(952, 2, 2); profile.currentForce = 2
            # Only fake memory advances. No engine date write or native simulation.
            for reader in readers.values():
                reader.memory.put(reader.world+0x34,
                    struct.pack('<HBB', node['year'], node['month'], node['day'])+bytes([0, 0, reader.force, 1]))
            def sample(side, p, receipt):
                return world.sample(readers[side], scope=self.c.scope, epoch=self.c.epoch,
                    period=self.c.period, profile=p, side=side, receipt_key=receipt,
                    read_birth=lambda: birth if side == 'B' else 1001)
            received = request = adapter = None
            native_results = []
            def native_load(permit):
                def prepare(observed): self.assertEqual(observed, {'double': True})
                answer = adapter.apply(received, request, profile, observe_loaded=lambda req: {'double': True},
                    prepare_rules=prepare, reservation=permit,
                    sample_loaded=lambda r, p, completion: sample('B', p, completion['accepted']['receipt_key']))
                self.assertEqual(received.journal.status()['status'], 'INTENT')
                self.assertEqual(self.c.period, generation)
                self.assertEqual(self.a.request(dict(action='status'))['state']['warm_completion']['packet']['checkpoint_id'],
                                 request.checkpoint)
                native_results.append(answer)
                return answer['completion']
            projection = TrustedProjection(self.c, host_sampler=lambda p, key: sample('A', p, key),
                guest_sampler=lambda p, key: sample('B', p, key), verify_held=lambda: True,
                guest_before=lambda: dict(attachment=self.c.attachments['B'], viewer_force=2, safe_boundary=True),
                native_load=native_load, source_kind='FIXTURE_ONLY')
            host_receipt = sha(('explicit native Save double '+str(generation)).encode())
            run_model(self.c)
            def observe_host():
                return host_observation(self.c, reader=readers['A'], read_birth=lambda: 1001,
                                        verify_held=lambda: True, source_ruler=666)
            host = observe_host()
            reservation = self.binding.reserve(generation, f'mp{generation:08d}.s14', host)
            self.artifacts[generation] = model_artifact(reservation.request, generation, data=data)
            package = self.binding.publish(generation, observe_host)
            self.assertEqual(package.manifest['state_contract'], world.CONTRACT)
            self.assertNotEqual(package.manifest['world_sha256'], sha(data))
            received = self.receive(package, f'received-{generation}')
            request = NextWorldRequest(generation+1, package.checkpoint_id, bytes([0x70+generation])*16,
                                       node['year'], node['month'], node['day'])
            adapter = ReceivedApply(bridge, self.b, scope=self.c.scope, epoch=self.c.epoch,
                period=self.c.period, attachments=self.c.attachments, on_hold=lambda reason: holds.append(reason))
            receiver = receiver_from_journal(received.journal)
            result = projection.apply(received.journal, receiver, profile, host_receipt_key=host_receipt)
            self.assertEqual(received.journal.status()['status'], 'COMPLETED')
            self.assertEqual((self.c.period, self.c.phase), (generation+1, 'PLANNING'))
            self.assertNotEqual(self.c.epoch, before_epoch); self.assertNotEqual(self.c.attachments['B'], before_attachment)
            self.assertEqual(len(self.c.applied_receipts), generation); self.assertEqual(len(native_results), 1)
            self.assertFalse(self.c.ready); self.assertFalse(result['ready_authorized'])
            self.assertFalse(result['full_world_verified']); self.assertFalse(result['native_gameplay_enabled'])
            self.assertTrue((received.directory/'warm-partial-world.json').is_file())
            rows.append(dict(period=generation, checkpoint=package.checkpoint_id, manifest=package.manifest,
                result=result, journal=received.journal.status(), diagnostic_ack=native_results[0]['reply'],
                native_epoch=request.epoch.hex(), wire_epoch=before_epoch, next_epoch=self.c.epoch))
        self.assertFalse(holds); self.assertEqual(len(bridge.calls), 2)
        self.assertEqual(len([r for r in self.c.trace if r['kind']=='authoritative_replacement_confirmed']), 2)
        EVIDENCE.append(dict(case='two-real-protocol-periods', periods=rows, bridge_calls=bridge.calls,
            complete_model_called=False, actual_tls=True, actual_journal_loaded=True,
            fake_native_save_load=True, fake_memory=True, fake_held=True, ready=False))


def pins():
    paths = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, '__file__', None)}
    paths.add(Path(__file__).resolve())
    return {str(p): sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix == '.py'}


if __name__ == '__main__':
    OUTPUT = PRIVATE/'b_warm_joint_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f'); OUTPUT.mkdir(parents=True)
    transport.OUTPUT = OUTPUT; before = pins(); stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Joint))
    (OUTPUT/'test.log').write_text(stream.getvalue(), encoding='utf-8')
    sources = pins(); stable = all(sources.get(k) == v for k, v in before.items())
    report = dict(family='san14.b-warm-joint.v1', result='PASS' if result.wasSuccessful() and result.testsRun==1 and stable else 'FAIL',
        tests=result.testsRun, sources=sources, inputs_unchanged=stable, cases=EVIDENCE,
        game_access=False, native_calls=False, actual_tls=True, ready=False,
        failures=[(str(t), detail) for t, detail in result.failures+result.errors])
    report['artifacts'] = {str(p): sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(OUTPUT/'result.json'); print(stream.getvalue())
    raise SystemExit(0 if report['result']=='PASS' else 1)
