"""Owned memory, real Journal/CheckedPort and typed local scheduling tests.

The scheduler and reward business in this file are explicit doubles, not the
production Runtime. A native MSVC program independently checks every ABI field.
"""
from datetime import datetime
import ctypes as C
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

import a_runtime_reward_port as port
from reward_observed_fixture import World
from reward_observed_context import CheckedPort,CONTRACT,reward
from reward_room_flow import Replica
import execution_journal as journal

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
OUTPUT=None;ROWS=[]


class CheckedOrderLock:
    """Test every nested port entry against the actual sampler RLock owner."""
    def __init__(self,sampler_lock):self.sampler_lock=sampler_lock;self.lock=threading.RLock()
    def __enter__(self):
        assert self.sampler_lock._is_owned(),'Port acquired before sampler: lock-order reversal'
        return self.lock.__enter__()
    def __exit__(self,*args):return self.lock.__exit__(*args)


class OwnedScheduler:
    """One real local worker, owned business bytes; no target process access."""
    def __init__(self,world):
        self.world=world;self.pending=None;self.report=None;self.calls=[];self.fault=None;self.queued_seen=0
        self.lock=threading.RLock();self.ready=threading.Event();self.done=threading.Event();self.stop=False
        self.worker=threading.Thread(target=self.run);self.worker.start()
    def close(self):
        self.stop=True;self.ready.set();self.worker.join(3);assert not self.worker.is_alive()
    def call(self,name,raw):
        kind={'ASaveRuntimeRewardConfigure':port.Configure,'ASaveRuntimeRewardSubmit':port.Submit,'ASaveRuntimeRewardSnapshot':port.Snapshot}[name]
        q=kind.from_buffer_copy(raw);self.calls.append(name)
        with self.lock:
            if kind is port.Submit:
                self.pending=q;s=port.Snapshot();s.header=port.base.Header(port.base.MAGIC,1,C.sizeof(s),13,0)
                s.nonce[:]=q.nonce;s.context=q.context;s.sequence=q.sequence;s.submitted=s.completed=q.sequence-1;s.configured=1;s.state=2
                self.report=s
                if self.fault=='unknown':
                    self.ready.set();raise port.RemoteCallUnknown('owned submit reply lost',{'may_have_started':True})
            if kind is port.Snapshot:
                s=port.Snapshot.from_buffer_copy(bytes(self.report))
                if s.state==2:
                    self.queued_seen+=1
                    if self.fault!='timeout':self.ready.set()
                if self.fault=='foreign':s.context.epoch+=1
                if self.fault=='malformed':return 0,bytes(s)[:-1]
                return 0,bytes(s)
            return 0,bytes(q)
    def run(self):
        while True:
            self.ready.wait();self.ready.clear()
            if self.stop:return
            with self.lock:
                q=self.pending;c=q.command
                context=reward.capture_context(self.world.reader,c.actor)
                command=reward.make_command(context,c.district,list(c.officers)[:c.count])
                self.world.execute(command)
                s=self.report;s.state=4;s.queued=0;s.submitted=s.completed=q.sequence;s.readyResealed=1;s.hostThread=threading.get_native_id()
                s.replayState=3;s.nativeReturned=s.argsReleased=s.ownedSlotCleared=1
                s.ctorCalls=s.dtorCalls=s.executeCalls=1;s.appendCalls=c.count;s.captureCalls=2;s.finallyCalls=q.sequence
                s.commandSha256[:]=port.command_hash(q.context,c);s.semanticSha256[:]=hashlib.sha256(bytes(c)).digest()
                if self.fault=='not-cleared':s.ownedSlotCleared=0
                if self.fault=='false-fence':s.fullInputHold=1
                self.done.set()


class Fixture:
    def __init__(self,folder):
        folder.mkdir();self.world=World(12);self.sampler=self.world.port().sampler
        self.scheduler=OwnedScheduler(self.world)
        c=port.Context();c.pid=self.world.reader.pid;c.birth=self.world.birth;c.period=1;c.epoch=123
        c.native.attempt[:]=b'a'*16;c.native.attachment[:]=bytes.fromhex(self.world.attachment);c.native.ownerGeneration=1;c.inputDigest[:]=b'd'*32
        self.native=port.RuntimeRewardPort(self.sampler,self.scheduler,nonce=b'n'*32,context=c,records=folder,wait_seconds=.3,poll_seconds=.005)
        self.native.lock=CheckedOrderLock(self.sampler.lock)
        self.checked=CheckedPort(self.sampler,self.native)
        self.scope=dict(schema='san14.replica-scope.v1',room_id='1'*32,binding_epoch='2'*32,timeline_epoch='3'*32,
            profile=dict(protocol='san14.room.v1',game_sha256=reward.SUPPORTED_SHA256,adapter_contract='research-no-native-room-adapter.v1',checkpoint_sha256='c'*64,rules_sha256='d'*64),
            bindings=dict(A=dict(force_id=12,main_district_id=11),B=dict(force_id=2,main_district_id=2)),
            state_contract=CONTRACT,initial_state_sha256=self.checked.observe())
        self.replica=Replica(folder/'journal.sqlite',self.scope,'A',self.checked)
        self.native.attach_journal(self.replica.journal);self.native.configure()
    def intent(self,seq=1,player='A'):
        force,district,person=(12,11,97) if player=='A' else (2,2,101)
        command=self.replica.command(force,district,[person])
        state=self.replica.journal.status()['state_sha256']
        return journal.make_intent(self.scope,seq,player,format(seq,'032x'),command,state)


class Tests(unittest.TestCase):
    def fixture(self,suffix=''):
        f=Fixture(OUTPUT/(self._testMethodName+suffix));self.addCleanup(f.scheduler.close);return f
    def test_two_actor_commands_real_intent_and_checked_projection(self):
        f=self.fixture()
        for seq,player in ((1,'A'),(2,'B')):
            intent=f.intent(seq,player);r=f.replica.apply(intent)
            self.assertEqual(r['status'],'APPLIED_LOCAL');self.assertEqual(f.world.calls,seq)
            self.assertTrue(f.replica.apply(intent)['duplicate']);self.assertEqual(f.world.calls,seq)
        self.assertEqual(f.native.attempted,{1,2});self.assertEqual(f.replica.journal.status()['phase'],'IDLE')
        self.assertGreaterEqual(f.scheduler.queued_seen,2)
        ROWS.append(dict(case=self._testMethodName,native_business_double=True,actual_SQLite=True,commands=2,submits=2))
    def test_requires_real_intent_before_any_submit(self):
        f=self.fixture();command=f.intent()['command']
        with self.assertRaises(RuntimeError):f.native.execute(command)
        self.assertEqual(f.world.calls,0);self.assertNotIn('ASaveRuntimeRewardSubmit',f.scheduler.calls)
    def test_unknown_submit_is_terminal_and_not_replayed(self):
        f=self.fixture();f.scheduler.fault='unknown';intent=f.intent()
        with self.assertRaises(journal.ExecutionHeld):f.replica.apply(intent)
        self.assertTrue(f.scheduler.done.wait(2))
        with self.assertRaises(Exception):f.replica.apply(intent)
        self.assertEqual(f.scheduler.calls.count('ASaveRuntimeRewardSubmit'),1)
        self.assertEqual(f.world.calls,1);self.assertEqual(f.replica.journal.status()['unknown_sequences'],[1])
    def test_timeout_keeps_intent_and_does_not_submit_again(self):
        f=self.fixture();f.scheduler.fault='timeout';intent=f.intent()
        with self.assertRaises(journal.ExecutionHeld):f.replica.apply(intent)
        with self.assertRaises(Exception):f.replica.apply(intent)
        self.assertEqual(f.world.calls,0);self.assertEqual(f.scheduler.calls.count('ASaveRuntimeRewardSubmit'),1)
    def test_foreign_malformed_or_uncleared_completion_refused(self):
        for fault in ('foreign','malformed','not-cleared','false-fence'):
            with self.subTest(fault=fault):
                f=self.fixture(fault);f.scheduler.fault=fault
                with self.assertRaises(journal.ExecutionHeld):f.replica.apply(f.intent())
                self.assertEqual(f.scheduler.calls.count('ASaveRuntimeRewardSubmit'),1)
                self.assertEqual(f.replica.journal.status()['phase'],'HOLD')
    def test_binding_or_durable_log_failure_prevents_submit(self):
        for fault in ('birth','attachment','log'):
            with self.subTest(fault=fault):
                f=self.fixture(fault);intent=f.intent()
                if fault=='birth':f.world.birth+=1
                if fault=='attachment':f.world.attachment='9'*32
                if fault=='log':
                    with patch.object(port,'save_new',side_effect=OSError('owned disk full')):
                        with self.assertRaises(journal.ExecutionHeld):f.replica.apply(intent)
                else:
                    with self.assertRaises(Exception):f.replica.apply(intent)
                self.assertNotIn('ASaveRuntimeRewardSubmit',f.scheduler.calls)
                self.assertEqual(f.world.calls,0)
    def test_unknown_is_shared_with_snapshot_and_stop_even_if_notification_fails(self):
        notified=[];attempted=[]
        def mark_unknown(exc):
            notified.append(exc);raise OSError('owned notification log failed')
        state=port.SharedCallState(threading.RLock(),mark_unknown)
        primary=port.RemoteCallUnknown('owned unresolved remote thread',dict(may_have_started=True,retained_buffer=True))
        # Use the production transport wrapper: only the actual Win32 body is
        # replaced. Its shared owner gate must latch the SAME primary exception.
        transport=port.RemoteTransport.__new__(port.RemoteTransport);transport.state=state
        def perform(name,payload):attempted.append(name);raise primary
        transport._perform=perform
        with self.assertRaises(port.RemoteCallUnknown) as caught:transport.call('ASaveRuntimeRewardSubmit',b'owned')
        self.assertIs(caught.exception,primary);self.assertIs(notified[0],primary)
        self.assertIn('notification log',primary.owner_notification_error)
        for op in ('Snapshot','Stop'):
            with self.assertRaises(RuntimeError):state.invoke(lambda:attempted.append(op))
        self.assertEqual(attempted,['ASaveRuntimeRewardSubmit']);self.assertIsNotNone(state.unknown)


def native_layout(run):
    kinds=(port.Context,port.Actor,port.Configure,port.Command,port.Submit,port.Snapshot)
    lines=['#include "a_runtime_reward_exports.h"','#include <cstdio>','#include <cstddef>','int main(){']
    for kind in kinds:
        cpp='a_runtime_reward_wire::'+kind.__name__
        lines.append(f'printf("{kind.__name__} %zu\\n",sizeof({cpp}));')
        for field,typ in kind._fields_:
            lines.append(f'printf("{kind.__name__}.{field} %zu %zu\\n",offsetof({cpp},{field}),sizeof((({cpp}*)0)->{field}));')
    lines.append('}')
    source=run/'schema.cpp';source.write_text('\n'.join(lines)+'\n')
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    cmd=run/'build.cmd';cmd.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /W4 /WX /EHsc /MT /I"'+str(HERE)+'" "'+str(source)+'" /Fe:schema.exe\n')
    child=subprocess.run(['cmd','/c',str(cmd)],cwd=run,capture_output=True,text=True,errors='replace',timeout=90)
    (run/'build.log').write_text(child.stdout+child.stderr);assert child.returncode==0,'native schema compilation failed'
    child=subprocess.run([str(run/'schema.exe')],capture_output=True,text=True,timeout=10);assert child.returncode==0
    (run/'schema.txt').write_text(child.stdout)
    expected={}
    for kind in kinds:
        expected[kind.__name__]=[C.sizeof(kind)]
        for name,typ in kind._fields_:expected[kind.__name__+'.'+name]=[getattr(kind,name).offset,C.sizeof(typ)]
    actual={row.split()[0]:list(map(int,row.split()[1:])) for row in child.stdout.splitlines()}
    assert actual==expected,'Native and Python field ABI differ'


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.update(HERE/n for n in ('a_runtime_reward_port_test.py','a_runtime_reward_exports.h','a_save_runtime_exports.h','checkpoint_reward_owned_replay.cpp'))
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_relative_to(ROOT) and p.suffix in ('.py','.h','.cpp')}


if __name__=='__main__':
    OUTPUT=PRIVATE/'a_runtime_reward_port_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    before=pins();result=dict(result='FAIL',game_access=False,steam_access=False,production_runtime_executed=False)
    try:
        native_layout(OUTPUT)
        stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        (OUTPUT/'test.log').write_text(stream.getvalue());print(stream.getvalue())
        stable=all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in before.items())
        result.update(result='PASS' if r.wasSuccessful() and r.testsRun==7 and stable else 'FAIL',tests=r.testsRun,
            abi_all_fields_verified=True,sources=before,inputs_unchanged=stable,cases=ROWS,
            failures=[(str(t),x) for t,x in r.errors+r.failures])
    except BaseException as exc:result['error']=repr(exc)
    result['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(OUTPUT/'result.json')
    raise SystemExit(result['result']!='PASS')
