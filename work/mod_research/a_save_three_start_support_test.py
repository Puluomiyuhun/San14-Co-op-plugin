"""Offline typed cleanup and owned file/context doubles; never target execution."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ctypes as C
import hashlib,io,json,sys,unittest
import a_save_runtime_contract as old
import a_save_repeat_contract as old_repeat
import a_save_three_runtime_contract as wire
import a_save_three_repeat_contract as repeat
import a_save_three_start_support as support
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research';NONCE=b'\x39'*32

def snapshot(generation=3):
    s=repeat.envelope(repeat.Snapshot,'RepeatSnapshot',NONCE);s.stopped=1
    s.activeGeneration=generation
    if generation==1:return s
    s.state=4;s.hostThread=77;s.retiredSerial=9;s.retiredCount=generation-1
    s.previousArtifactMatched=s.nativeDateMatched=1
    q=s.request;q.previousGeneration=generation-1;q.generation=generation;q.period=generation;q.epoch=20+generation
    q.previousSha256[:]=b'\x51'*32;q.inputDigest[:]=b'\x61'*32;q.year=203;q.month=9;q.day=1
    return s

def inventory():
    before={'old.s14':dict(size=22,sha256='9'*64)}
    artifacts=[dict(generation=i,filename=f'mp{i:08x}.s14',size=100+i,sha256=str(i)*64) for i in (1,2,3)]
    after={**deepcopy(before),**{a['filename']:dict(size=a['size'],sha256=a['sha256']) for a in artifacts}}
    return before,after,artifacts

class Query:
    def __init__(self,debug=False,success=True):self.debug=debug;self.success=success;self.calls=0
    def __call__(self,handle,value):self.calls+=1;value._obj.value=int(self.debug);return self.success

def context(date=(203,9,1)):
    return dict(snapshot=dict(date=dict(zip(('year','month','day'),date)),player=dict(force_id=12,ruler_id=666),
        state_stack=['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']),state_sample=dict(phase_raw=2))

class Cases(unittest.TestCase):
    def test_new_repeat_rejects_old_wire_and_bad_type(self):
        for kind,op in ((repeat.Next,'RequestNext'),(repeat.Snapshot,'RepeatSnapshot')):
            q=repeat.envelope(kind,op,NONCE);self.assertEqual(q.header.magic,0x33585241)
            self.assertEqual(bytes(repeat.decode(kind,op,NONCE,bytes(q))),bytes(q))
            oldkind=old_repeat.Next if kind is repeat.Next else old_repeat.Snapshot
            with self.assertRaises(ValueError):repeat.decode(kind,op,NONCE,bytes(old_repeat.envelope(oldkind,op,NONCE)))
            with self.assertRaises(ValueError):repeat.envelope(oldkind,op,NONCE)
        with self.assertRaises(ValueError):repeat.envelope(repeat.Next,'RequestNext',NONCE.hex())
    def test_second_and_third_complete_allow_stopped(self):
        for g in (2,3):
            for stopped in (0,1):
                s=snapshot(g);s.stopped=stopped;self.assertIsNone(support.cleanup_gate(s))
    def test_initial_zero_artifacts_stop_only_exact_idle(self):
        self.assertIsNone(support.cleanup_gate(snapshot(1)))
        for field,value in (('activeGeneration',0),('retiredCount',1),('requested',1),('retiredSerial',1),('hostThread',1)):
            s=snapshot(1);setattr(s,field,value)
            with self.subTest(field=field),self.assertRaises(RuntimeError):support.cleanup_gate(s)
    def test_running_stop_and_failed_successors_always_refused(self):
        for state in (1,2,3,5):
            s=snapshot();s.state=state;s.requested=1
            with self.subTest(state=state),self.assertRaises(RuntimeError):support.cleanup_gate(s)
        s=snapshot();s.error=6
        with self.assertRaises(RuntimeError):support.cleanup_gate(s)
    def test_bad_retirement_active_lease_and_third_request_refused(self):
        for field,value in (('retiredCount',1),('retiredSerial',0),('hostThread',0),('requested',1),('lease',1),
                            ('frame',1),('drainPending',1),('previousArtifactMatched',0),('nativeDateMatched',0),
                            ('activeGeneration',4),('simulationEnabled',1),('stopped',2)):
            s=snapshot();setattr(s,field,value)
            with self.subTest(field=field),self.assertRaises(RuntimeError):support.cleanup_gate(s)
        for field,value in (('previousGeneration',1),('generation',2),('period',0),('epoch',0),('day',2)):
            s=snapshot();setattr(s.request,field,value)
            with self.subTest(field=field),self.assertRaises(RuntimeError):support.cleanup_gate(s)
        s=snapshot();s.request.previousSha256[:]=bytes(32)
        with self.assertRaises(RuntimeError):support.cleanup_gate(s)
    def test_three_files_and_no_changed_originals(self):
        b,a,art=inventory();v=support.compare_three_files(b,a,art)
        self.assertTrue(v['originals_unchanged'] and v['only_expected_new_files'] and v['new_hashes_match'])
        self.assertTrue(v['native_autosave_changes_are_not_silently_approved'])
    def test_missing_changed_extra_duplicate_or_reordered_files_refused(self):
        for mode in ('hash','size','missing','extra','old','duplicate','order','two','alias'):
            b,a,art=inventory()
            if mode=='hash':a[art[2]['filename']]['sha256']='0'*64
            if mode=='size':a[art[2]['filename']]['size']+=1
            if mode=='missing':del a[art[2]['filename']]
            if mode=='extra':a['extra.s14']=dict(size=10,sha256='0'*64)
            if mode=='old':a['old.s14']['size']+=1
            if mode=='duplicate':art[2]=deepcopy(art[1])
            if mode=='order':art.reverse()
            if mode=='two':art.pop()
            if mode=='alias':b[art[0]['filename']]=deepcopy(a[art[0]['filename']])
            v=support.compare_three_files(b,a,art)
            with self.subTest(mode=mode):self.assertFalse(all(v[k] for k in ('originals_unchanged','only_expected_new_files','new_hashes_match')))
    def _check(self,start=(203,8,11),end=(203,9,1),mutate=None,debug=False,success=True):
        p=wire.envelope(wire.Prepare,'Prepare',NONCE);p.pid=12;p.birth=99;p.base=0x100000000;p.force=12;p.ruler=666;p.year,p.month,p.day=start
        q=Query(debug,success);reader=SimpleNamespace(pid=12,memory=SimpleNamespace(base=p.base,handle=1,k=SimpleNamespace(CheckRemoteDebuggerPresent=q)))
        c=context(end);birth=99
        if mutate:mutate(p,reader,c)
        with patch.dict(sys.modules,{'startup_identity_reader':SimpleNamespace(capture_startup_context=lambda r:c),
                                     'checkpoint_push_start':SimpleNamespace(process_birth=lambda r:birth)}):
            result=support.post_turn_check(reader,p)
        return result,q
    def test_two_period_postcheck_cross_month_and_year(self):
        for start,end in (((203,8,11),(203,9,1)),((203,12,11),(204,1,1)),((203,8,1),(203,8,21))):
            result,q=self._check(start,end);self.assertEqual(result['result'],'PASS_READ_ONLY');self.assertEqual(q.calls,1)
            self.assertEqual(result['native_calls'],0);self.assertFalse(result['atomic_snapshot'])
    def test_postcheck_wrong_date_identity_planning_debugger_refused(self):
        mutations=[lambda p,r,c:setattr(r,'pid',13),lambda p,r,c:setattr(p,'birth',100),
            lambda p,r,c:c['snapshot']['player'].update(force_id=2),lambda p,r,c:c['snapshot']['state_stack'].pop(),
            lambda p,r,c:c['state_sample'].update(phase_raw=1),lambda p,r,c:setattr(p.header,'magic',old.MAGIC)]
        for mutate in mutations:
            with self.subTest(mutate=mutate),self.assertRaises((RuntimeError,ValueError)):self._check(mutate=mutate)
        with self.assertRaises(RuntimeError):self._check(end=(203,8,21))
        with self.assertRaises(RuntimeError):self._check(debug=True)
        with self.assertRaises(RuntimeError):self._check(success=False)
        with self.assertRaises(RuntimeError):support.next_date(9999,12,21)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    folder=PRIVATE/'a_save_three_start_support_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    names=('a_save_three_start_support.py','a_save_three_start_support_test.py','a_save_three_repeat_contract.py',
           'a_save_three_runtime_contract.py','a_save_runtime_contract.py','a_save_repeat_contract.py','a_save_runtime_control.py')
    pins={str(P/n):sha(P/n) for n in names};stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (folder/'test.log').write_text(stream.getvalue(),encoding='utf-8');stable=all(sha(n)==h for n,h in pins.items())
    report=dict(result='PASS' if result.wasSuccessful() and result.testsRun==9 and stable else 'FAIL',tests=result.testsRun,
        sources=pins,inputs_unchanged=stable,game_access=False,native_execution=False,process_access=False,
        owned_context_and_inventory_doubles=True,production_permission=False,failures=[(str(t),d) for t,d in result.failures+result.errors])
    report['artifacts']={str(p):sha(p) for p in folder.iterdir() if p.is_file()}
    path=folder/'result.json';path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=report['result'],path=str(path),sha256=sha(path))));print(stream.getvalue());return int(report['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
