"""Coordinator lifetime/error tests; fake OS calls and private temporary files."""
import ctypes as C
import json
from pathlib import Path
from datetime import datetime
import tempfile
import unittest
from types import SimpleNamespace
from a_save_runtime_control import (backup_saves,compare_saves,inventory,remote_call,
                                     RemoteCallUnknown,save_new,sha)

P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'


class Kernel:
    def __init__(self,mode):self.mode=mode;self.freed=False;self.closed=False;self.created=0
    def CheckRemoteDebuggerPresent(self,h,p):p._obj.value=self.mode=='debugger';return 1
    def VirtualAllocEx(self,*a):return 0x10000
    def WriteProcessMemory(self,h,a,b,n,p):p._obj.value=n;return 1
    def CreateRemoteThread(self,h,a,b,c,d,e,tid):
        self.created+=1;tid._obj.value=123;return 0 if self.mode=='creation-failed' else 456
    def WaitForSingleObject(self,*a):return 258 if self.mode=='timeout' else 0
    def GetExitCodeThread(self,h,p):p._obj.value=0;return 1
    def CloseHandle(self,h):self.closed=True;return 1
    def VirtualFreeEx(self,*a):self.freed=True;return 1


class Tests(unittest.TestCase):
    def test_backup_and_independent_file_checks(self):
        with tempfile.TemporaryDirectory(dir=PRIVATE) as d:
            p=Path(d);source=p/'saves';source.mkdir();(source/'old.s14').write_bytes(b'original')
            before=backup_saves(source,p/'backup')
            self.assertEqual((p/'backup/old.s14').read_bytes(),b'original')
            (source/'mp12345678.s14').write_bytes(b'new')
            check=compare_saves(before,inventory(source),'mp12345678.s14',sha(source/'mp12345678.s14'))
            self.assertTrue(check['originals_unchanged'] and check['only_expected_new_file'] and check['new_hash_matches'])
            (source/'old.s14').write_bytes(b'changed')
            self.assertFalse(compare_saves(before,inventory(source),'mp12345678.s14')['originals_unchanged'])
            with self.assertRaises(FileExistsError):backup_saves(source,p/'backup')

    def call_case(self,mode):
        with tempfile.TemporaryDirectory(dir=PRIVATE) as d:
            k=Kernel(mode);api=SimpleNamespace(k=k,handle=1,reader=SimpleNamespace(memory=SimpleNamespace(read=lambda a,n:b'X'*n)))
            if mode=='ok':self.assertEqual(remote_call(api,123456,b'1234',d,'test'),(0,b'XXXX'))
            elif mode=='timeout':
                with self.assertRaises(RemoteCallUnknown) as error:remote_call(api,123456,b'1234',d,'test')
                self.assertTrue(error.exception.record['retained_buffer'])
            else:
                with self.assertRaises(RuntimeError):remote_call(api,123456,b'1234',d,'test')
            r=json.loads((Path(d)/'test-result.json').read_text(encoding='utf-8'))
            self.assertEqual(k.freed,mode in ('ok','creation-failed'))
            self.assertEqual(k.closed,mode in ('ok','timeout'))
            self.assertEqual(r['may_have_started'],mode in ('ok','timeout'))
            count=k.created
            with self.assertRaises(FileExistsError):remote_call(api,123456,b'1234',d,'test')
            self.assertEqual(k.created,count)

    def test_completed_buffer_released(self):self.call_case('ok')
    def test_unresolved_call_retains_buffer_and_does_not_replay(self):self.call_case('timeout')
    def test_failed_creation_releases_buffer(self):self.call_case('creation-failed')
    def test_debugger_refused_before_remote_allocation(self):self.call_case('debugger')


if __name__=='__main__':
    run=PRIVATE/'a_save_runtime_control_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    pins={n:sha(P/n) for n in ('a_save_runtime_control.py','a_save_runtime_control_test.py')}
    with (run/'tests.log').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    same=all(sha(P/n)==h for n,h in pins.items())
    report=dict(result='PASS' if result.wasSuccessful() and same else 'FAIL',cases=result.testsRun,sources=pins,sources_unchanged=same,game_access=False,os_calls='FAKE',temporary_private_files=True)
    save_new(run/'result.json',report);print(json.dumps(dict(result=report['result'],path=str(run/'result.json'))))
    raise SystemExit(0 if report['result']=='PASS' else 1)
