"""Actual bootstrap/room/control objects; native channel and engine are doubles.
No GameReader, archived packets, game processes, or Steam paths are used.
"""
from dataclasses import replace
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
sys.path[:0] = [str(ROOT/'outputs/san14-link'), str(ROOT.parent/'mod_research/python_deps')]
import a_room_native_control as control
import a_save_runtime_contract as wire
import a_save_repeat_contract as repeat
from a_room_bootstrap_protocol import BootstrapCoordinator, BootstrapRoom, BootstrapFreshSaveBinding
from authoritative_sync import CheckpointReceiver, digest, scope_from_room, next_node
from checkpoint_fresh_save_binding import LocalWorldObservation
from checkpoint_fresh_save_binding_test import manifest, select_direct, model_artifact


class Fixture:
    def __init__(self, mode='normal'):
        self.mode = mode
        self.owner = control.RoomTurnControl()
        self.room = BootstrapRoom(manifest())
        select_direct(self.room)
        self.c = BootstrapCoordinator(scope_from_room(self.room), 'CONTROL_FIXTURE_ONLY', 'd'*64,
            dict(A='a'*32, B='b'*32), dict(year=203,month=8,day=11,phase='PLANNING_BOUNDARY'))
        self.room.bind_coordinator(self.c)
        self.binding = BootstrapFreshSaveBinding(self.room, self.c,
            native_room_id=bytes.fromhex(digest(self.c.scope)), native_room_epoch=7,
            artifact_reader=self.owner.copy_artifact, source_kind='FIXTURE_ONLY')
        self.c.begin_bootstrap()
        q = wire.envelope(wire.Prepare, 'Prepare', bytes([7])*32)
        q.pid, q.birth, q.period, q.epoch = 123, 456, 1, 11
        q.year, q.month, q.day, q.force, q.ruler = 203, 8, 11, 12, 666
        self.prep = control.prepare_from_room(q, self.binding)
        self.world = LocalWorldObservation('a'*32,203,8,11,12,666,'CONTROL_FIXTURE_ONLY','d'*64,True)
        self.events, self.submits, self.calls, self.kept = [], [], [], []
        self.ticks, self.polls, self.command = 0, 0, None
        self.order = []

    def submit(self, reservation):
        self.submits.append(reservation)
        self.order.append('submit-' + str(reservation.generation))

    def wait_artifact(self, generation, timeout):
        return model_artifact(self.submits[-1].request, generation)

    def complete(self):
        package = self.room.artifacts
        receiver = CheckpointReceiver(package.manifest, package.checkpoint_id, self.c.scope,
                                     self.c.epoch,self.c.period,package.manifest['cut'])
        for chunk in package.chunks.values():
            receiver.accept(chunk)
        self.c.received('B',self.c.epoch,receiver)
        intent = self.c.begin_guest_load('B',self.c.epoch)
        self.c.loaded('B',self.c.epoch,package.checkpoint_id,intent,
            package.manifest['world_sha256'],2,str(self.c.period)*32,
            dict(attachment=self.c.attachments['A'],world_sha256=package.manifest['world_sha256'],
                 node=package.manifest['node']))
        self.order.append('loaded-' + str(self.c.period-1))

    def snapshot(self):
        self.ticks += 1
        if self.mode == 'disconnect':
            self.room.disconnect('B','b')
            return
        if self.c.phase == 'RECONCILING':
            # A diagnostic ACK-looking field is deliberately insufficient.
            self.room._warm_ack = {'fixture_only':True,'checkpoint_id':self.c.checkpoint_id}
            if self.mode == 'ack-only' or (self.mode == 'second-timeout' and self.c.period == 2):
                return
            if self.ticks % 3 == 0:
                self.complete()
        elif self.c.phase == 'PLANNING' and self.c.bootstrap_completed:
            if self.mode == 'never-ready':
                return
            if self.mode == 'host-changed':
                self.world = replace(self.world,world_sha256='e'*64)
            if self.mode == 'new-command':
                for side in ('A','B'):
                    self.c.applied_prefix(side,self.c.epoch,1,'f'*64,'d'*64,self.c.attachments[side])
            for side in ('A','B'):
                self.c.set_ready(side,self.c.epoch,True)
            self.c.begin_simulation(self.c.seal_inputs())
            self.order.append('sealed-turn')

    def call(self, op, value=None):
        self.calls.append(op)
        if op == 'RequestNext':
            assert self.c.bootstrap_completed and self.c.phase == 'RUNNING'
            assert self.command is None
            self.command = repeat.decode(repeat.Next,op,bytes(self.prep.nonce),bytes(value))
            self.order.append('request-next')
            return self.command,None
        assert op == 'RepeatSnapshot'
        self.polls += 1
        q = repeat.envelope(repeat.Snapshot,op,bytes(self.prep.nonce))
        q.request = self.command.request
        q.requested = q.hostThread = q.previousArtifactMatched = q.retiredSerial = q.retiredCount = 1
        q.state = 3 if self.polls < 3 else 4
        q.activeGeneration = 1 if q.state == 3 else 2
        q.drainPending = int(q.state == 3)
        q.nativeDateMatched = int(q.state == 4)
        if self.mode == 'native-stopped': q.stopped = 1
        if q.state == 4:
            self.world = replace(self.world,day=21,world_sha256='e'*64)
        return q,None

    def drive(self):
        def observe(node):
            assert self.world.value()['node'] == node
            return self.world
        return self.owner.drive(self,self.prep,['mp00000001.s14','mp00000002.s14'],self.call,
            lambda *args:self.kept.append(args),lambda k,v:self.events.append((k,v)),
            self.binding,observe,wait_seconds=5,clock=lambda:self.ticks,pause=lambda _:None)


class Tests(unittest.TestCase):
    def test_two_formal_completions_order_and_real_room_digests(self):
        f = Fixture()
        result = f.drive()
        self.assertEqual(f.order, ['submit-1','loaded-1','sealed-turn','request-next','submit-2','loaded-2'])
        self.assertEqual(result['formal_completions'],2)
        self.assertEqual([r.request['day'] for r in f.submits],[11,21])
        self.assertEqual([r.request['period'] for r in f.submits],[1,2])
        self.assertEqual(f.c.node['day'],21)
        self.assertEqual(f.c.period,3)
        command = next(v for k,v in f.events if k == 'request-next')
        self.assertEqual(bytes(f.command.request.inputDigest).hex(),command['native_binding']['input_digest'])
        self.assertEqual(f.command.request.epoch,f.prep.epoch+1)
        self.assertEqual(bytes(f.command.request.previousSha256).hex(),f.kept[0][2].sha256)
        self.assertFalse(result['input_fence_provided'] or result['two_game_ready'])
        with self.assertRaisesRegex(RuntimeError,'already attempted'):f.drive()
        self.assertEqual(len(f.submits),2)

    def test_ack_alone_never_releases_native_turn(self):
        f = Fixture('ack-only')
        with self.assertRaisesRegex(RuntimeError,'timed out'):f.drive()
        self.assertEqual(len(f.submits),1)
        self.assertEqual(f.calls,[])
        self.assertEqual(f.c.applied_receipts,{})
        self.assertTrue(f.binding.status()['held_reason'])
        self.assertTrue(f.room.checkpoint_status()['closed'])

    def test_formal_completion_alone_does_not_mark_both_ready(self):
        f = Fixture('never-ready')
        with self.assertRaisesRegex(RuntimeError,'timed out'):f.drive()
        self.assertTrue(f.c.bootstrap_completed)
        self.assertEqual(f.calls,[])

    def test_disconnect_stops_without_second_native_action(self):
        f = Fixture('disconnect')
        with self.assertRaises((RuntimeError,ValueError)):f.drive()
        self.assertEqual(len(f.submits),1)
        self.assertEqual(f.calls,[])

    def test_changed_host_rejected_after_bootstrap_wait(self):
        f = Fixture('host-changed')
        with self.assertRaisesRegex(RuntimeError,'A changed'):f.drive()
        self.assertEqual(f.calls,[])

    def test_new_commands_outside_pilot_are_rejected(self):
        f = Fixture('new-command')
        with self.assertRaisesRegex(RuntimeError,'does not execute new commands'):f.drive()
        self.assertEqual(f.calls,[])

    def test_native_failure_never_submits_second(self):
        f = Fixture('native-stopped')
        with self.assertRaisesRegex(RuntimeError,'stopped or failed'):f.drive()
        self.assertEqual(len(f.submits),1)
        self.assertEqual(f.calls.count('RequestNext'),1)

    def test_second_missing_completion_is_not_success(self):
        f = Fixture('second-timeout')
        with self.assertRaisesRegex(RuntimeError,'timed out'):f.drive()
        self.assertEqual(len(f.submits),2)
        self.assertEqual(len(f.c.applied_receipts),1)
        with self.assertRaisesRegex(RuntimeError,'already attempted'):f.drive()
        self.assertEqual(f.calls.count('RequestNext'),1)

    def test_unbound_preparation_fails_before_submit(self):
        f = Fixture()
        f.prep.roomInputDigest[0] ^= 1
        with self.assertRaisesRegex(RuntimeError,'before installing'):f.drive()
        self.assertEqual(f.submits,[])

    def test_copy_cannot_publish_archive_or_repeat(self):
        f = Fixture()
        with self.assertRaisesRegex(RuntimeError,'completed channel artifact'):f.owner.copy_artifact(1)
        f.drive()
        with self.assertRaisesRegex(RuntimeError,'completed channel artifact'):f.owner.copy_artifact(1)

    def test_stale_room_connection_refused_before_native_prepare(self):
        f = Fixture()
        f.room.players['B']['connection'] = 'different-connection'
        with self.assertRaisesRegex(ValueError,'connection changed'):
            control.prepare_from_room(f.prep,f.binding)
        self.assertEqual(f.submits,[])


if __name__ == '__main__':
    run = ROOT.parent/'mod_research/a_room_native_control_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    names = ['a_room_native_control.py','a_room_native_control_test.py','a_room_bootstrap_protocol.py',
        'a_native_turn_start_control.py','a_save_repeat_contract.py','a_save_runtime_contract.py',
        'checkpoint_fresh_save_binding.py','checkpoint_fresh_save_binding_test.py']
    paths = [P/n for n in names]+[ROOT/'outputs/san14-link/authoritative_sync.py']
    sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    pins = {str(p.relative_to(ROOT)):sha(p) for p in paths}
    log = io.StringIO()
    r = unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (run/'test.log').write_text(log.getvalue(),encoding='utf-8')
    unchanged = all(sha(ROOT/p)==h for p,h in pins.items())
    result = dict(result='PASS' if r.wasSuccessful() and r.testsRun==11 and unchanged else 'FAIL',
        tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),sources=pins,sources_unchanged=unchanged,
        game_access=False,native_channel_fixture=True,engine_fixture=True,tls_used=False,
        actual_coordinator_loaded=True,input_fence_provided=False,two_game_ready=False)
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue())
    print(json.dumps(dict(result=result['result'],path=str(run/'result.json'))))
    raise SystemExit(result['result']!='PASS')
