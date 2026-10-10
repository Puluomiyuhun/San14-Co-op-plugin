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
import a_room_three_control as control
import a_save_runtime_contract as wire
import a_save_repeat_contract as repeat
from a_room_three_protocol import BootstrapCoordinator, BootstrapRoom, BootstrapFreshSaveBinding
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
            if self.mode == 'ack-only' or (self.mode == 'third-timeout' and self.c.period == 3):
                return
            if self.ticks % 3 == 0:
                self.complete()
        elif self.c.phase == 'PLANNING' and self.c.bootstrap_completed:
            if self.mode == 'never-ready' or (self.mode == 'second-never-ready' and self.c.period == 3):
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
            assert self.command is None or value.request.previousGeneration == self.command.request.generation
            self.polls = 0
            self.command = repeat.decode(repeat.Next,op,bytes(self.prep.nonce),bytes(value))
            self.order.append('request-next')
            return self.command,None
        assert op == 'RepeatSnapshot'
        self.polls += 1
        q = repeat.envelope(repeat.Snapshot,op,bytes(self.prep.nonce))
        q.request = self.command.request
        q.hostThread = q.previousArtifactMatched = 1
        q.retiredSerial = q.retiredCount = self.command.request.previousGeneration
        q.state = 3 if self.polls < 3 else 4
        q.activeGeneration = self.command.request.previousGeneration if q.state == 3 else self.command.request.generation
        q.requested = int(q.state == 3)
        q.drainPending = int(q.state == 3)
        q.nativeDateMatched = int(q.state == 4)
        if self.mode == 'native-stopped': q.stopped = 1
        if q.state == 4:
            self.world = replace(self.world,month=q.request.month,day=q.request.day,world_sha256=str(q.request.generation)*64)
        return q,None

    def drive(self):
        def observe(node):
            assert self.world.value()['node'] == node
            return self.world
        return self.owner.drive(self,self.prep,['mp00000001.s14','mp00000002.s14','mp00000003.s14'],self.call,
            lambda *args:self.kept.append(args),lambda k,v:self.events.append((k,v)),
            self.binding,observe,wait_seconds=5,clock=lambda:self.ticks,pause=lambda _:None)


class Tests(unittest.TestCase):
    def test_three_formal_completions_and_lineage(self):
        f=Fixture();result=f.drive()
        self.assertEqual(result['formal_completions'],3)
        self.assertEqual(f.order,['submit-1','loaded-1','sealed-turn','request-next','submit-2','loaded-2','sealed-turn','request-next','submit-3','loaded-3'])
        self.assertEqual([(r.request['month'],r.request['day']) for r in f.submits],[(8,11),(8,21),(9,1)])
        self.assertEqual(f.c.period,4)
        self.assertFalse(f.c.ready)
        self.assertEqual(f.binding.status()['remaining_reservations'],0)
        with self.assertRaises(ValueError):f.c.native_binding(f.prep.epoch)
        with self.assertRaisesRegex(RuntimeError,'already attempted'):f.drive()

    def test_second_planning_requires_new_explicit_ready(self):
        f=Fixture('second-never-ready')
        with self.assertRaisesRegex(RuntimeError,'timed out'):f.drive()
        self.assertEqual(len(f.submits),2)
        self.assertEqual(f.calls.count('RequestNext'),1)
        self.assertEqual(len(f.c.applied_receipts),2)

    def test_third_completion_cannot_be_replaced_by_previous(self):
        f=Fixture('third-timeout')
        with self.assertRaisesRegex(RuntimeError,'timed out'):f.drive()
        self.assertEqual(len(f.submits),3)
        self.assertEqual(len(f.c.applied_receipts),2)
        self.assertTrue(f.binding.status()['held_reason'])

    def test_prior_readysecond_requested_flag_rejected(self):
        f=Fixture();old=f.call
        def call(op,value=None):
            q,r=old(op,value)
            if op=='RepeatSnapshot' and q.state==4:q.requested=1
            return q,r
        f.call=call
        with self.assertRaisesRegex(RuntimeError,'Successor binding'):f.drive()
        self.assertEqual(len(f.submits),1)

    def test_second_native_retirement_cannot_reuse_first_counts(self):
        f=Fixture();old=f.call
        def call(op,value=None):
            q,r=old(op,value)
            if op=='RepeatSnapshot' and q.request.generation==3:q.retiredCount=1
            return q,r
        f.call=call
        with self.assertRaisesRegex(RuntimeError,'Running lacks'):f.drive()
        self.assertEqual(len(f.submits),2)

    def test_no_skipped_generation_or_reused_filename(self):
        f=Fixture()
        with self.assertRaises(ValueError):f.binding.reserve(2,'mp00000001.s14',f.world)
        self.assertEqual(f.binding.status()['remaining_reservations'],3)
        f.drive()
        with self.assertRaises(ValueError):f.binding.reserve(4,'mp00000004.s14',f.world)

    def test_epoch_overflow_refused_before_submit(self):
        f=Fixture();f.prep.epoch=2**64-2
        with self.assertRaises(ValueError):f.drive()
        self.assertFalse(f.submits)


if __name__ == '__main__':
    run = ROOT.parent/'mod_research/a_room_three_control_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    names = ['a_room_three_control.py','a_room_three_control_test.py','a_room_three_protocol.py',
        'checkpoint_three_save_binding.py','checkpoint_three_save_packet.py','a_three_repeat_state.py',
        'a_native_turn_start_control.py','a_save_repeat_contract.py','a_save_runtime_contract.py',
        'checkpoint_fresh_save_binding.py','checkpoint_fresh_save_binding_test.py']
    paths = [P/n for n in names]+[ROOT/'outputs/san14-link/authoritative_sync.py']
    sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    pins = {str(p.relative_to(ROOT)):sha(p) for p in paths}
    log = io.StringIO()
    r = unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (run/'test.log').write_text(log.getvalue(),encoding='utf-8')
    unchanged = all(sha(ROOT/p)==h for p,h in pins.items())
    result = dict(result='PASS' if r.wasSuccessful() and r.testsRun==7 and unchanged else 'FAIL',
        tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),sources=pins,sources_unchanged=unchanged,
        game_access=False,native_channel_fixture=True,engine_fixture=True,tls_used=False,
        actual_coordinator_loaded=True,input_fence_provided=False,two_game_ready=False)
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue())
    print(json.dumps(dict(result=result['result'],path=str(run/'result.json'))))
    raise SystemExit(result['result']!='PASS')
