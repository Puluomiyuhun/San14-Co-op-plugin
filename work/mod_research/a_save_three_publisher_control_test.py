"""Owned fake Popen and real private logs; no debugger, process or game access."""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,io,json,subprocess,tempfile,unittest
import a_save_three_publisher_control as api
from a_save_runtime_control import RemoteCallUnknown
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research';ROOT=None
class Child:
    pid=45454
    def __init__(self,mode):self.mode=mode;self.waits=0
    def wait(self,timeout):
        self.waits+=1
        if self.mode=='timeout':raise subprocess.TimeoutExpired('owned double',timeout)
        return 3 if self.mode=='reject' else 4 if self.mode=='failed' else 0
    def kill(self):raise AssertionError('must never kill publisher')
    def terminate(self):raise AssertionError('must never terminate publisher')
class Cases(unittest.TestCase):
    def call(self,mode='success',fault=None):
        run=Path(tempfile.mkdtemp(dir=ROOT));exe=run/'publisher.exe';dll=run/'owner.dll'
        exe.write_bytes(b'owned publisher identity');dll.write_bytes(b'owned DLL identity')
        child=Child(mode);rows=[]
        def popen(command,stdout,stderr,creationflags):
            if mode=='spawn-failed':raise OSError('no child')
            row=dict(status='INSTALLED',attached=True,detached=True,uncertain=False,written_mask=7)
            if mode=='reject':row.update(status='REJECTED_HELD_NO_WRITES',written_mask=0)
            if mode=='failed':row.update(status='CLEAN_ROLLBACK')
            if mode=='attached':row.update(detached=False)
            if mode=='uncertain':row.update(uncertain=True)
            if mode=='malformed':row['detached']='true'
            stdout.write(b'no json\n' if mode=='missing' else (json.dumps(row)+'\n').encode());stdout.flush();rows.append(row)
            return child
        original=api.save_new
        def save(path,value):
            if fault=='process' and path.name.endswith('-process.json'):raise OSError('disk process')
            if fault=='all-postspawn' and not path.name.endswith('-intent.json'):raise OSError('disk')
            if fault=='pending' and path.name.endswith('-pending.json'):raise OSError('disk pending')
            if fault=='result' and path.name.endswith('-result.json'):raise OSError('disk result')
            if fault=='intent' and path.name.endswith('-intent.json'):raise OSError('disk intent')
            return original(path,value)
        with patch.object(api.subprocess,'Popen',popen),patch.object(api,'save_new',save):
            return api.publish(exe,'install',SimpleNamespace(pid=1,birth=2,base=3),4,dll,run/'plans.bin',run/'snapshot.bin',run,'owned')
    def test_known_success_and_zero_write_rejection(self):
        self.assertEqual(self.call()['status'],'INSTALLED')
        self.assertEqual(self.call('reject')['status'],'REJECTED_HELD_NO_WRITES')
    def test_process_log_failure_preserves_unknown(self):
        with self.assertRaises(RemoteCallUnknown) as cm:self.call(fault='process')
        self.assertFalse(cm.exception.record['process_exit_observed']);self.assertTrue(cm.exception.record['must_not_terminate'])
    def test_timeout_and_pending_log_failure_preserve_unknown(self):
        with self.assertRaises(RemoteCallUnknown):self.call('timeout')
        with self.assertRaises(RemoteCallUnknown) as cm:self.call('timeout',fault='pending')
        self.assertEqual(cm.exception.record['pending_log_error'],'OSError')
        self.assertEqual(cm.exception.record['error_type'],'TimeoutExpired')
        with self.assertRaises(RemoteCallUnknown) as cm:self.call(fault='all-postspawn')
        self.assertEqual(cm.exception.record['pending_log_error'],'OSError')
    def test_exited_without_detach_proof_stays_unknown(self):
        for mode in ('attached','uncertain','malformed','missing'):
            with self.subTest(mode=mode),self.assertRaises(RemoteCallUnknown) as cm:self.call(mode)
            self.assertTrue(cm.exception.record['process_exit_observed'])
    def test_known_detached_failure_remains_plain_error(self):
        with self.assertRaises(RuntimeError) as cm:self.call('failed')
        self.assertNotIsInstance(cm.exception,RemoteCallUnknown)
        with self.assertRaises(OSError) as cm:self.call(fault='result')
        self.assertNotIsInstance(cm.exception,RemoteCallUnknown)
    def test_before_spawn_failure_has_no_unknown_process(self):
        for mode,fault in (('spawn-failed',None),('success','intent')):
            with self.subTest(mode=mode),self.assertRaises(OSError) as cm:self.call(mode,fault)
            self.assertNotIsInstance(cm.exception,RemoteCallUnknown)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    global ROOT
    ROOT=PRIVATE/'a_save_three_publisher_control_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');ROOT.mkdir(parents=True)
    pins={str(P/n):sha(P/n) for n in ('a_save_three_publisher_control.py','a_save_three_publisher_control_test.py','a_save_runtime_control.py')}
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (ROOT/'test.log').write_text(stream.getvalue());stable=all(sha(n)==h for n,h in pins.items())
    result=dict(result='PASS' if r.wasSuccessful() and r.testsRun==6 and stable else 'FAIL',tests=r.testsRun,sources=pins,
        inputs_unchanged=stable,game_access=False,process_access=False,native_execution=False,owned_popen_double=True,
        failures=[(str(t),v) for t,v in r.failures+r.errors])
    result['artifacts']={str(p):sha(p) for p in ROOT.rglob('*') if p.is_file()}
    path=ROOT/'result.json';path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=result['result'],path=str(path),sha256=sha(path))));print(stream.getvalue());return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
