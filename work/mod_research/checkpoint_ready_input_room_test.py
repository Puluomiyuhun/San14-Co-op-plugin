import json,pathlib,unittest
from test_checkpoint_ready_barrier import new_room,request
from checkpoint_ready_input_room import RestrictedReadyInputBridge
from checkpoint_planning_hold_room_adapter import input_digest

class NativePortDouble:
    """Room-only double; actual native gate execution is in the MASM fixture."""
    def __init__(self,binding):self.input_binding_digest=input_digest(binding);self.generation=0;self.stopped=False;self.claim_full=False
    def request(self,operation,generation):self.generation=generation;return True
    def snapshot(self):return {'gate':{'action':self.generation,'room_ready_eligible':self.claim_full,'full_input_hold':self.claim_full},'user':{'covered_user_scope_held':True,'covered_user_scope_drained':True}}
    def disconnect(self):self.stopped=True

class Tests(unittest.TestCase):
    def test_subset_does_not_ready(self):
        room,c=new_room();request(room,c,'A',True);request(room,c,'B',True)
        port=NativePortDouble(room._input_binding('A'));bridge=RestrictedReadyInputBridge(room,'A',port)
        state=bridge.begin();self.assertFalse(state['room_ready_eligible']);self.assertEqual(c.ready,set());self.assertIsNone(c.seal)
        with self.assertRaises(RuntimeError):bridge.acknowledge_ready()
        self.assertTrue(port.stopped);self.assertEqual(c.phase,'HELD');self.assertEqual(c.ready,set())
    def test_forged_full_report_still_denied(self):
        room,c=new_room();request(room,c,'A',True);port=NativePortDouble(room._input_binding('A'));port.claim_full=True;bridge=RestrictedReadyInputBridge(room,'A',port)
        self.assertFalse(bridge.begin()['full_input_hold'])
        with self.assertRaises(RuntimeError):bridge.acknowledge_ready()
        self.assertTrue(port.stopped);self.assertIsNone(c.seal)
    def test_wrong_attachment_rejected_before_request(self):
        room,c=new_room();request(room,c,'A',True);binding=room._input_binding('A');binding['attachment']='wrong';port=NativePortDouble(binding);bridge=RestrictedReadyInputBridge(room,'A',port)
        with self.assertRaises(RuntimeError):bridge.begin()
        self.assertEqual(port.generation,0);self.assertTrue(port.stopped);self.assertEqual(c.phase,'HELD')

if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));out={'result':'PASS' if r.wasSuccessful() else 'FAIL','cases':r.testsRun,'actual_room':'ReadyBarrierRoom and PeriodCoordinator','native_port':'explicit double; no native execution claim','game_access':False};pathlib.Path(__file__).with_name('checkpoint_ready_input_room_result.json').write_text(json.dumps(out,indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
