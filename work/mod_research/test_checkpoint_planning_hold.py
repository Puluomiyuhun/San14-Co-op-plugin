"""Real normally loaded DLL function calls plus independent room-port tests.
Native User/menu/command bodies remain explicit owned doubles; no SAN14 access.
"""
from pathlib import Path
from datetime import datetime
import copy
import hashlib
import json
import subprocess
import unittest
from checkpoint_planning_hold_room_adapter import RoomPlanningHoldAdapter,make_native_binding,input_digest
from test_checkpoint_ready_barrier import new_room,request
ROOT=Path(__file__).resolve().parent
CASES=[]
NATIVE=('open-forward','hold-replay','nested-replay','cancel','drain-ticket','stale-binding','modified-ticket',
        'indirect-mutation','missing-deep-provider','wrong-thread','cpp-exception','seh-exception','late-pending',
        'missing-prefetch','hold-inflight','disconnect-inflight')


class NativeTests(unittest.TestCase):
    def test_actual_dll_and_owned_six_bridge(self):
        for case in (*NATIVE,'dry-held','dry-wrong-phase','production-skip-refusal'):
            binary='checkpoint_planning_hold_fixture.exe'
            if case.startswith('dry-'):binary='checkpoint_planning_hold_user_dry_fixture.exe'
            if case=='production-skip-refusal':binary='checkpoint_planning_hold_user_production_fixture.exe'
            run=subprocess.run([str(ROOT/binary),case],capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,0,(case,run.stdout,run.stderr))
            data=json.loads(run.stdout);self.assertEqual(data['result'],'PASS');CASES.append(data)


class NativeControlDouble:
    """Room binding-only double; actual DLL paths are exercised above in C++."""
    def __init__(self,binding):self.binding=binding;self.calls=[];self.generation=0;self.stopped=False
    def request(self,operation,generation):self.calls.append((operation,generation));self.generation=generation;return 0
    def snapshot(self):return dict(action_generation=self.generation,full_input_hold=False,room_ack_eligible=False,covered_operation_completed=True)
    def disconnect(self):self.stopped=True


class RoomTests(unittest.TestCase):
    def prepare(self):
        room,c=new_room();self.assertTrue(request(room,c,'A',True)['ok'])
        # Native config must have been initialized with exactly this digest.
        binding=make_native_binding(room._input_binding('A'),attempt=bytes([1])*16,attachment=bytes([2])*16,owner_generation=3,native_epoch=4)
        native=NativeControlDouble(binding);return room,c,native,RoomPlanningHoldAdapter(room,'A',native)
    def test_real_room_action_drives_subset_but_cannot_ack(self):
        room,c,native,port=self.prepare();report=port.begin_owned_subset()
        self.assertEqual(native.calls,[('HOLD',port.action.generation)])
        self.assertFalse(report['room_ack_eligible']);self.assertEqual(c.ready,set())
        with self.assertRaises(RuntimeError):port.acknowledge_ready()
        self.assertTrue(native.stopped);self.assertEqual(c.phase,'HELD');self.assertEqual(c.ready,set())
    def test_changed_attachment_rejects_before_native_request(self):
        room,c,native,port=self.prepare();native.binding.room_input_digest[0]^=1
        with self.assertRaises(RuntimeError):port.begin_owned_subset()
        self.assertEqual(native.calls,[]);self.assertTrue(native.stopped);self.assertEqual(c.phase,'HELD')
    def test_remote_prefix_is_separate_from_local_hold_binding(self):
        room,c,native,_=self.prepare();value=room._input_binding('A');full=copy.deepcopy(value)
        full['applied_prefix']=dict(sequence=7,prefix_sha256='a'*64,world_sha256='b'*64)
        self.assertEqual(input_digest(value),input_digest(full))
        full['epoch']='different'
        self.assertNotEqual(input_digest(value),input_digest(full))
        self.assertEqual(bytes(native.binding.room_input_digest),input_digest(value))


if __name__=='__main__':
    result=unittest.main(verbosity=2,exit=False).result
    binaries={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('checkpoint_planning_hold.dll','checkpoint_planning_hold_fixture.exe','checkpoint_planning_hold_user_dry_fixture.exe','checkpoint_planning_hold_user_production_fixture.exe')}
    data=dict(result='PASS' if result.wasSuccessful() else 'FAIL',methods=result.testsRun,native_cases=CASES,binaries=binaries,game_access=False,
              room_adapter_test_backend='Explicit binding double; does not attest native game hold',native_backend='Normally loaded DLL, owned native argument bodies, archived menu consumption fragment, real six-entry bridge and OS worker thread')
    (ROOT/'checkpoint_planning_hold_result.json').write_text(json.dumps(data,indent=2),encoding='utf8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
