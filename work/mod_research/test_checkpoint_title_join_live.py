"""Own-memory native sampling plus strict trace analyzer. Never opens game."""
from pathlib import Path
from datetime import datetime
import copy
import json
import subprocess
import unittest
import checkpoint_title_join_live as live
ROOT=Path(__file__).resolve().parent
CASES=[]
def model_case(mode):
    folder=ROOT/'checkpoint_title_join_live_semantic_runs'/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-'+mode);folder.mkdir(parents=True)
    trace=folder/'trace.jsonl'
    run=subprocess.run([str(ROOT/'checkpoint_title_join_live_semantic_fixture.exe'),str(trace),mode],capture_output=True,text=True,timeout=10)
    data=json.loads(run.stdout)
    rows=[json.loads(x) for x in trace.read_text().splitlines()]
    CASES.append(dict(mode=mode,trace=str(trace),exit=run.returncode,model=data))
    return run.returncode,data,rows


class SemanticTests(unittest.TestCase):
    def test_overlapping_title_workers_and_changed_join_threads(self):
        for mode in ('overlap','late590'):
            code,data,rows=model_case(mode)
            self.assertEqual(code,0,data);self.assertEqual(len(rows),20)
            # Native model does not attach or exercise debugger cleanup; these
            # envelopes exist solely for the offline analyzer's acceptance test.
            rows += [dict(event='restore_verified',all_six_debug_registers=True,owned_queue_drained=True),dict(event='detached',registers_restored=True,owned_queue_drained=True)]
            report=live.analyze_live(rows,0,data['module_base'],'svdexSC34.s14')
            self.assertTrue(report['task_chain_observed'],report)
            self.assertEqual(report['title590_done_before_title520_join'],mode=='overlap')
            self.assertFalse(report['live_authority']);self.assertFalse(report['scheduler_fence'])
    def test_native_sampler_rejects_wrong_identity_or_missing_stages(self):
        for mode in ('wrong-name','wrong-closure','wrong-payload','alias-thread','wrong-worker','missing-return','duplicate-done','uncleared-join'):
            code,data,_=model_case(mode);self.assertEqual(code,1,(mode,data));self.assertEqual(data['result'],'REJECTED')
    def test_adapter_rejects_mutations_and_missing_cleanup(self):
        code,data,rows=model_case('overlap');self.assertEqual(code,0,data)
        rows += [dict(event='restore_verified',all_six_debug_registers=True,owned_queue_drained=True),dict(event='detached',registers_restored=True,owned_queue_drained=True)]
        base=data['module_base']
        for index,key,value in ((0,'load',1),(1,'native_return',base+0x4BEEC2),(3,'worker_thread',999),(5,'done',0),(6,'cleanup_fields',[0,0,1]),(7,'native_return',base+0x497135),(11,'payload_rva','0x508b40'),(18,'seq',4),(-1,'owned_queue_drained',False),(-2,'owned_queue_drained',False)):
            mutated=copy.deepcopy(rows);mutated[index][key]=value
            self.assertFalse(live.analyze_live(mutated,0,base,'svdexSC34.s14')['task_chain_observed'],(index,key))
        for exit_code in (None,1,4):self.assertFalse(live.analyze_live(rows,exit_code,base,'svdexSC34.s14')['task_chain_observed'])
        self.assertFalse(live.analyze_live(rows,0,base+1,'svdexSC34.s14')['task_chain_observed'])
        self.assertFalse(live.analyze_live(rows,0,base,'svdexSC35.s14')['task_chain_observed'])
        self.assertFalse(live.analyze_live(rows[:-1],0,base,'svdexSC34.s14')['task_chain_observed'])


if __name__=='__main__':
    r=unittest.main(verbosity=2,exit=False).result
    (ROOT/'checkpoint_title_join_live_semantic_result.json').write_text(json.dumps(dict(result='PASS' if r.wasSuccessful() else 'FAIL',tests=r.testsRun,cases=CASES,game_access=False,fixture_sha256=live.sha(ROOT/'checkpoint_title_join_live_semantic_fixture.exe'),note='Own memory model; synthetic cleanup envelope only in analyzer tests; no live-game receipt.'),indent=2),encoding='utf8')
    raise SystemExit(0 if r.wasSuccessful() else 1)
