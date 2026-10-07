"""Fault injection for remote-call argument lifetime; does not access a process."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from checkpoint_live_user_threads_v2_start import invoke,RemoteCallError


class Kernel:
    def __init__(self,case):self.case=case;self.freed=[];self.closed=[];self.started=False
    def VirtualAllocEx(self,*args):return 123456
    def WriteProcessMemory(self,handle,address,buffer,size,written):
        written._obj.value=size
        return self.case!='write-failure'
    def CreateRemoteThread(self,*args):
        if self.case=='creation-failure':return None
        self.started=True;args[-1]._obj.value=44
        if self.case=='interrupted-after-create':raise KeyboardInterrupt('After native publication')
        return 5678
    def WaitForSingleObject(self,*args):return 258 if self.case=='timeout' else 0
    def GetExitCodeThread(self,handle,result):
        result._obj.value=0
        return self.case!='exit-query-failure'
    def CloseHandle(self,handle):self.closed.append(handle);return True
    def VirtualFreeEx(self,handle,address,*args):
        self.freed.append(address);return self.case!='free-failure'


def api(case):
    def read(address,size):
        if case=='output-read-failure':raise OSError('Read failed after completed thread')
        return b'X'*size
    return SimpleNamespace(k=Kernel(case),handle=1,reader=SimpleNamespace(memory=SimpleNamespace(read=read)))


class LifetimeTests(unittest.TestCase):
    def test_completed_control_releases_its_argument(self):
        a=api('success');self.assertEqual(invoke(a,100,b'abc'),(0,None));self.assertEqual(a.k.freed,[123456])
    def test_timeout_retains_argument_and_reports_uncertain_publication(self):
        a=api('timeout')
        with self.assertRaises(RemoteCallError) as c:invoke(a,100,b'abc')
        self.assertFalse(c.exception.completed);self.assertTrue(c.exception.may_have_started)
        self.assertEqual(a.k.freed,[]);self.assertEqual(a.k.closed,[5678])
    def test_interrupted_native_creation_does_not_free_unassigned_live_argument(self):
        a=api('interrupted-after-create')
        with self.assertRaises(RemoteCallError) as c:invoke(a,100,b'abc')
        self.assertTrue(a.k.started);self.assertTrue(c.exception.may_have_started)
        self.assertEqual(a.k.freed,[]);self.assertEqual(a.k.closed,[])
    def test_confirmed_creation_failure_releases_argument(self):
        a=api('creation-failure')
        with self.assertRaises(RemoteCallError) as c:invoke(a,100,b'abc')
        self.assertFalse(c.exception.may_have_started);self.assertEqual(a.k.freed,[123456])
    def test_exit_query_failure_retains_known_completion_for_serial_stop(self):
        a=api('exit-query-failure')
        with self.assertRaises(RemoteCallError) as c:invoke(a,100,b'abc')
        self.assertTrue(c.exception.completed);self.assertEqual(a.k.freed,[123456])
    def test_free_failure_does_not_erase_known_completion(self):
        a=api('free-failure')
        with self.assertRaises(RemoteCallError) as c:invoke(a,100,b'abc')
        self.assertTrue(c.exception.completed);self.assertEqual(c.exception.cleanup_errors,['BUFFER_RELEASE_FAILED'])
    def test_failed_input_publication_frees_before_any_thread(self):
        a=api('write-failure')
        with self.assertRaises(RemoteCallError) as c:invoke(a,100,b'abc')
        self.assertFalse(c.exception.may_have_started);self.assertFalse(a.k.started)
        self.assertEqual(a.k.freed,[123456])
    def test_output_failure_reports_completed_thread_and_releases_buffer(self):
        a=api('output-read-failure')
        with self.assertRaises(RemoteCallError) as c:invoke(a,100,output_size=12)
        self.assertTrue(c.exception.completed);self.assertEqual(a.k.freed,[123456])


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LifetimeTests))
    here=Path(__file__).resolve().parent
    folder=here/'checkpoint_live_user_threads_v2_launcher_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    row=dict(result='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,
        game_access=False,process_access=False,kernel_calls='TEST_DOUBLES_FOR_FAULT_INJECTION',
        source_sha256={name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in
            ('checkpoint_live_user_threads_v2_start.py','checkpoint_live_user_threads_v2_launcher_test.py')})
    (folder/'result.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
    print(folder/'result.json')
    raise SystemExit(not result.wasSuccessful())
