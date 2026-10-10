"""Actual retained entry/mount/SQLite/TLS and new operator wiring, owned environment.

Native code, PE/RAM/channel and rules publisher remain the explicitly named
predecessor fixture doubles. No SAN14/Steam process, files, or live calls.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import a_simple_remote_host as host
import a_reward_runtime_entry_test as actual
import observed_protected_host_test as prior
from reward_room_flow import Replica
from reward_observed_flow import GuestConsumer
import observed_room_service as service
import checkpoint_complete_live_capture as capture_module

ROOT=Path(__file__).resolve().parents[2];PRIVATE=ROOT.parent/'mod_research'
OUTPUT=None;ROWS=[]


def configuration(folder):
    c=prior.configuration(folder);c['schema']=host.SCHEMA
    c['native'].update(reward_build_run=str(folder/'reward-build'),reward_build_sha256='a'*64)
    c.update(reward_report_key_path=str(folder/'reward-key'),guest_cut_key_path=str(folder/'cut-key'))
    return c


class EntryCases(actual.Cases):
    def setUp(self):
        super().setUp();self.operator_events=[];self.requests=[];self.tls_fault=False
        original=self.a.request
        def request(packet):
            if packet.get('action')=='reward_submit':
                self.requests.append(deepcopy(packet))
                answer=original(packet)
                if self.tls_fault:raise ConnectionError('owned lost accepted reward reply')
                return answer
            return original(packet)
        self.a.request=request;host.serialize_control(self.a)
        self.input=io.StringIO(json.dumps(dict(action='reward',request_id='7'*32,district_id=11,officer_ids=[97]))+'\n'+
                               json.dumps(dict(action='ready',request_id='8'*32))+'\n')

    def connect(self):
        self.operator=host.connect_operator(self.entry,self.mount,stream=self.input,emit=self.operator_events.append)

    def progress_reward(self):
        if self.mount.phase not in ('ACTIVE','RETIRED'):return
        if self.guest_cut is None:
            self.b_world.attachment=self.c.attachments['B'];port=self.b_world.port()
            replica=Replica(self.folder/'external-B.sqlite',self.mount.flow.scope,'B',port)
            consumer=GuestConsumer(self.b,replica,self.mount.reward_key);consumer.report()
            self.guest_cut=actual.mounting.GuestCutConsumer(consumer,self.mount.profile,
                cut_key=self.mount.cut_key,checkpoint_epoch=self.c.epoch)
            self.guest_cut.finish_input()
        self.guest_cut.poll()
        if self.mount.phase=='RETIRED' and not self.guest_cut.ready_attempted:self.guest_cut.ready_after_cut()

    def test_console_to_actual_mount_entry_two_saves_and_cleanup(self):
        self.connect();self.assertEqual(self.run_entry(),0,self.final)
        self.assertEqual(self.received_count,2);self.assertEqual(self.published,['install','restore'])
        self.assertTrue(self.final['cleanup_verified']);self.assertTrue(self.operator.closed)
        self.assertTrue(self.operator.console.ready);self.assertIsNone(self.operator.failure)
        self.assertEqual(self.mount.gate.receipt['cut']['sequence'],1)
        self.assertEqual(len(self.requests),1);self.assertEqual(self.requests[0]['request_id'],'7'*32)
        self.assertEqual(self.operator.rows['7'*32]['reply']['status'],'QUEUED')
        self.assertTrue(any(e.get('event')=='external-reward-planning-open' for e in self.operator_events))
        self.assertEqual(self.calls.count('RewardSubmit'),1);self.assertEqual(self.calls.count('RequestNext'),1)
        self.assertLess(self.calls.index('OpenPlanning'),self.calls.index('RewardSubmit'))
        self.assertLess(self.calls.index('RewardSubmit'),self.calls.index('RequestNext'))
        self.assertTrue(self.final['save_comparison']['originals_unchanged'])
        ROWS.append(dict(case=self._testMethodName,actual_mounted_entry=True,actual_TLS=True,
                         two_formal_completions=2,shared_cut=1,operator=self.operator.status()))

    def test_lost_reward_ack_holds_same_owner_without_resubmit(self):
        self.tls_fault=True;self.connect();self.assertEqual(self.run_entry(),1)
        self.assertTrue(self.operator.closed);self.assertIn('lost accepted',self.operator.failure)
        self.assertEqual(len(self.requests),1);self.assertNotIn('RequestNext',self.calls)
        self.assertNotIn('submit-2',self.calls);self.assertNotIn('Stop',self.calls)
        self.assertEqual(self.published,['install']);self.assertEqual(self.mount.phase,'HELD')
        self.assertFalse(self.final['cleanup_verified'])
        with self.assertRaises(RuntimeError):self.operator.console.submit_line(json.dumps(
            dict(action='reward',request_id='7'*32,district_id=11,officer_ids=[97])))
        self.assertEqual(len(self.requests),1)
        ROWS.append(dict(case=self._testMethodName,accepted_reply_lost=True,no_replay=True,operator=self.operator.status()))

    def test_original_open_failure_never_starts_console(self):
        original=self.mount._planning_call
        def fail(kind,operation):
            if operation==14:raise RuntimeError('owned original OpenPlanning rejection')
            return original(kind,operation)
        self.mount._planning_call=fail;self.connect()
        self.assertEqual(self.run_entry(),1);self.assertIsNone(self.operator.console)
        self.assertTrue(self.operator.closed);self.assertEqual(self.requests,[])
        self.assertNotIn('RewardSubmit',self.calls);self.assertNotIn('RequestNext',self.calls)
        ROWS.append(dict(case=self._testMethodName,console_started=False,requests=0))


class Cases(unittest.TestCase):
    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir();self.c=configuration(self.folder)

    def test_exact_configuration_and_default_are_inert(self):
        host.validate_config(self.c)
        for key,value in [('schema','san14.a-protected-host.v1'),('input_fence',True),('reward_report_key_path','relative')]:
            bad=deepcopy(self.c);bad[key]=value
            with self.assertRaises(ValueError):host.validate_config(bad)
        with patch.object(host.native,'capture',side_effect=AssertionError('no game')),patch.object(host,'HostService',side_effect=AssertionError('no socket')),patch('sys.stdout',new=io.StringIO()):
            self.assertEqual(host.main([]),0);self.assertEqual(host.main(['--config-fields']),0)
            with patch.object(host,'read_config',return_value=self.c),patch.object(host,'check',return_value=(None,b'a'*32,None,b'b'*32,b'c'*32)):
                self.assertEqual(host.main(['--check','--config','owned']),0)
        with patch.object(host,'read_config',side_effect=AssertionError('not before consent')),patch('sys.stderr',new=io.StringIO()),self.assertRaises(SystemExit):
            host.main(['--execute','--config','owned'])

    def test_check_uses_real_successor_approval_and_exports_before_capture(self):
        calls=[]
        build=SimpleNamespace(check=lambda:calls.append('rules'))
        symbols=[SimpleNamespace(name=('ASaveRuntime'+n).encode(),forwarder=None) for n in
                 ('RewardConfigure','RewardSubmit','RewardSnapshot','OpenPlanning','PlanningSnapshot')]
        pe=SimpleNamespace(DIRECTORY_ENTRY_EXPORT=SimpleNamespace(symbols=symbols),close=lambda:calls.append('PE-close'))
        def approval(a,b):
            self.assertEqual(a.reward_build_sha256,'a'*64);calls.append('reward-closure')
            return {},{'production_dll':'owned-approved.dll'}
        import pefile
        baseline={'production':{'binaries':{'a_save_local_runtime.dll':'a'*64,'checkpoint_planning_hold.dll':'b'*64}}}
        with patch.object(host,'verify_network_tests',side_effect=lambda _:calls.append('CLI-tests')),patch.object(host.predecessor,'check',side_effect=AssertionError('old entry checker not applicable')),patch.object(host.native,'verify_entry_tests',side_effect=lambda _:calls.append('entry-tests')),patch.object(host.native,'verify_launcher_tests',side_effect=lambda _:calls.append('launcher-tests')),patch.object(host.native,'verify_native_build',return_value=(baseline,None,{'binaries':{'publisher.exe':'c'*64}})),patch.object(host.native,'verified_artifact',side_effect=lambda *a:calls.append('artifact')),patch.object(host,'approved_planning_runtime',side_effect=approval),patch.object(pefile,'PE',return_value=pe),patch.object(host,'RulesBuild',return_value=build),patch.object(host,'load_key',side_effect=[b'a'*32,b'b'*32,b'c'*32]),patch.object(host.native,'capture',side_effect=AssertionError('no game')):
            value=host.check(self.c);self.assertIs(value[2],build)
        self.assertEqual(calls,['CLI-tests','entry-tests','launcher-tests','artifact','artifact','artifact','reward-closure','PE-close','rules'])

    def test_approval_source_drift_fails(self):
        folder=self.folder/'approved';folder.mkdir();source=self.folder/'watched.py';source.write_text('first')
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        value=dict(schema='san14.simple-remote-host-tests.v1',result='PASS',sources_unchanged=True,
            actual_TLS=True,mounted_entry_executed=True,full_cli_actual_entry=True,game_access=False,
            sources={str(Path(host.__file__).resolve()):sha(Path(host.__file__)),str(source):sha(source)})
        (folder/'result.json').write_text(json.dumps(value));host.verify_network_tests(folder)
        source.write_text('changed')
        with self.assertRaisesRegex(ValueError,'source changed'):host.verify_network_tests(folder)

    def test_all_shared_connection_requests_are_serialized(self):
        active=0;peak=0;lock=threading.Lock();seen=[]
        def request(packet):
            nonlocal active,peak
            with lock:active+=1;peak=max(peak,active)
            time.sleep(.02);seen.append(packet)
            with lock:active-=1
            return {'ok':True}
        c=SimpleNamespace(request=request);identity=id(c);host.serialize_control(c)
        threads=[threading.Thread(target=c.request,args=({'action':a},)) for a in ('reward_submit','period_ready','status')]
        for t in threads:t.start()
        for t in threads:t.join(2);self.assertFalse(t.is_alive())
        self.assertEqual(id(c),identity);self.assertEqual(peak,1);self.assertEqual(len(seen),3)

    def test_close_drains_callback_without_gate_lock_reversal(self):
        # Only synchronization surface is doubled; actual Console/Operator.close run.
        operator=host.Operator.__new__(host.Operator);operator.lock=threading.RLock();operator.closed=False
        entered=threading.Event();release=threading.Event();closed=threading.Event();calls=[]
        gate=threading.RLock()
        def callback(*args):
            with operator.lock:
                entered.set();release.wait(2)
                with gate:calls.append('callback-returned')
            return {'ok':True}
        operator.console=host.Console(on_reward=callback,on_ready=lambda _:None,on_failure=lambda _:None,emit=lambda _:None)
        worker=threading.Thread(target=operator.console.submit_line,args=(json.dumps(dict(action='reward',request_id='a'*32,district_id=11,officer_ids=[97])),))
        worker.start();self.assertTrue(entered.wait(1))
        def close():operator.close();calls.append('closed');closed.set()
        closer=threading.Thread(target=close);closer.start();self.assertFalse(closed.wait(.05))
        # close must not hold a server-side gate while callback returns from TLS.
        self.assertTrue(gate.acquire(timeout=.5));gate.release();release.set()
        worker.join(3);closer.join(3);self.assertFalse(worker.is_alive() or closer.is_alive())
        self.assertEqual(calls,['callback-returned','closed']);self.assertTrue(operator.closed)

    def test_actual_service_cleanup_barrier_uses_new_run_entry(self):
        services=[];threads=[];errors=[];seen=[];original=service.HostService
        source=self.folder/'owned-source.s14';source.write_bytes(b'own file no Steam')
        self.c['manifest']['profile']['checkpoint_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
        def factory(*args,**kwargs):
            kwargs.update(control_port=0,download_port=0);s=original(*args,**kwargs);services.append(s)
            def guest():
                g=None
                try:
                    g=service.join_guest(s.invitation);g.wait_context(3);deadline=time.monotonic()+4
                    while len(s.coordinator.applied_receipts)!=2:
                        if time.monotonic()>deadline:raise AssertionError('fixture entry stalled')
                        time.sleep(.01)
                    self.assertTrue(g.control.request(dict(action='pilot_guest_finished',formal_completions=2,native_cleanup_verified=True,retained_native_state=False))['ok'])
                    while not g.control.request(dict(action='pilot_host_finished'))['host_finished']:
                        if time.monotonic()>deadline:raise AssertionError('host barrier stalled')
                        time.sleep(.01)
                except BaseException as exc:errors.append(repr(exc))
                finally:
                    if g:g.close()
            t=threading.Thread(target=guest);threads.append(t);t.start();return s
        class Entry:
            def __init__(self,room,c,key,*,mount,no_new_commands):self.room,self.coordinator,self.mount=room,c,mount
            def status(self):return dict(protection=dict(installed_once=True,restore_verified=True,retained_or_unknown=False))
        class Mount:
            def __init__(self,*a,**k):self.phase='NEW';self.failure=None
            def status(self):return dict(phase=self.phase,failure=self.failure)
        class Op:
            def __init__(self):self.failure=None;self.console=SimpleNamespace(ready=True);self.closed=False
            def close(self):self.closed=True;seen.append('console-close')
            def status(self):return dict(closed=self.closed,ready_sent=True)
        def connect(entry,mount,**kw):return Op()
        def execute(*a,entry,on_event,reward_flow,input_fence,**k):
            self.assertIs(entry.mount,reward_flow);self.assertIs(input_fence,False)
            # This test verifies only real network/CLI lifetime; full entry above.
            with entry.room.lock,entry.coordinator.lock:
                entry.coordinator.applied_receipts.update({'owned1':{},'owned2':{}})
                entry.coordinator.period=3
            reward_flow.phase='RETIRED';on_event('running-await-human',{});return 0
        with ExitStack() as stack:
            for obj,name,value in [(host,'check',lambda c:(SimpleNamespace(pid=123,wait_seconds=3),b'a'*32,object(),b'b'*32,b'c'*32)),
                (host.native,'capture',lambda _:(source,dict(planning={'context':{'snapshot':dict(date=dict(year=203,month=8,day=11),player=dict(force_id=12,ruler_id=666))}}))),
                (host,'HostService',factory),(host,'RuntimeMount',Mount),(host.native,'RoomEntry',Entry),
                (host,'connect_operator',connect),(host.native,'execute',execute),(capture_module,'SOURCE',source),
                (capture_module,'SOURCE_SHA',self.c['manifest']['profile']['checkpoint_sha256'])]:
                stack.enter_context(patch.object(obj,name,value))
            stack.enter_context(patch('sys.stdout',new=io.StringIO()))
            code=host.run(self.c,no_native_commands=True,stream=io.StringIO(''))
        for t in threads:t.join(5);self.assertFalse(t.is_alive())
        self.assertFalse(errors,errors);self.assertEqual(code,0);self.assertTrue(services[0]._closed)
        report=json.loads((Path(self.c['network']['directory'])/'host-result.json').read_text())
        self.assertTrue(report['guest_disconnect']['guest_control_disconnected']);self.assertTrue(report['operator']['closed'])
        self.assertFalse(report['native_menu_supported']);self.assertFalse(report['input_exclusion_proven'])
        ROWS.append(dict(case=self._testMethodName,actual_service=True,native_and_receipts_double=True))


class FullRunCase(EntryCases):
    def setUp(self):
        def network_setup(t):
            t.folder=OUTPUT/t._testMethodName;t.folder.mkdir();t.cfg=configuration(t.folder)
            # The fixture's supported manifest is used for this actual service.
            t.cfg['manifest']=actual.transport.manifest()
            network={**t.cfg['network'],'control_port':0,'download_port':0}
            s=service.HostService(t.cfg['manifest'],dict(year=203,month=8,day=11,phase='PLANNING_BOUNDARY'),**network)
            t.full_service=s;t.full_guest=service.join_guest(s.invitation)
            t.c=s.wait_bound(3);t.room=s.room;t.a=s.control;t.b=t.full_guest.control
            t.servers=s.servers;t.clients=[t.a,t.b]
            t.port=s.invitation['control_port'];t.download=s.invitation['download_port'];t.fp=s.invitation['fingerprint']
            t.artifacts={}
            t.binding=actual.joint.BootstrapFreshSaveBinding(t.room,t.c,native_room_id=actual.transport.NATIVE_ID,
                native_room_epoch=actual.transport.NATIVE_EPOCH,artifact_reader=lambda gen:t.artifacts[gen],source_kind='FIXTURE_ONLY')
        with patch.object(actual.transport.RoomTests,'setUp',network_setup),patch.object(host,'serialize_control',return_value=None):super().setUp()
        # The inherited entry harness constructs a legacy service shell. It is
        # discarded; this test retains the actually constructed HostService.
        self.service._stop.set();self.monitor.join(3);self.assertFalse(self.monitor.is_alive())
        self.service=self.full_service
        self.captured['planning']['context']={'snapshot':dict(date=dict(year=203,month=8,day=11),player=dict(force_id=12,ruler_id=666))}
        self.cfg['manifest']['profile']['checkpoint_sha256']=host.hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.full_errors=[];self.full_threads=[]

    def tearDown(self):
        self.scheduler.close()
        if self.warm.native_lease:self.warm.native_lease.close()
        self.capture_patch.stop();self.stage_patch.stop();self.full_guest.close();self.full_service.close()

    def test_new_cli_run_actual_entry_service_mount_console_two_periods(self):
        real_execute=host.native.execute;real_connect=host.connect_operator
        def route(args,path,captured,*,entry,on_event,rules_build,settings,reward_flow,**kw):
            args.pid=self.raw.pid
            def connect(actual_entry,mount,**kwargs):
                self.entry,self.mount=actual_entry,mount
                self.operator=real_connect(actual_entry,mount,**kwargs)
                return self.operator
            def execute(*args,**kwargs):
                notify=kwargs['on_event']
                def event(kind,info):on_event(kind,info);notify(kind,info)
                kwargs['on_event']=event
                code=real_execute(*args,**kwargs)
                if code==0:
                    def finish():
                        try:
                            reply=self.b.request(dict(action='pilot_guest_finished',formal_completions=2,native_cleanup_verified=True,retained_native_state=False))
                            self.assertTrue(reply['ok']);deadline=time.monotonic()+4
                            while not self.b.request(dict(action='pilot_host_finished'))['host_finished']:
                                if time.monotonic()>deadline:raise AssertionError('host result barrier stalled')
                                time.sleep(.01)
                        except BaseException as exc:self.full_errors.append(repr(exc))
                        finally:self.full_guest.close()
                    thread=threading.Thread(target=finish);self.full_threads.append(thread);thread.start()
                return code
            # The actual service was constructed during fixture setup so that
            # the retained B native-memory fixture binds its genuine scope.
            # Only constructor timing is injected, not its room/transport/Ready.
            with patch.object(host,'check',return_value=(args,self.key,rules_build,b'r'*32,b'c'*32)), \
                 patch.object(host,'HostService',return_value=self.full_service), \
                 patch.object(host,'connect_operator',side_effect=connect), \
                 patch.object(host.native,'execute',side_effect=execute):
                return host.run(self.cfg,no_native_commands=True,stream=self.input)
        with patch.object(host.native,'execute',side_effect=route):code=self.run_entry()
        for t in self.full_threads:t.join(5);self.assertFalse(t.is_alive())
        self.assertFalse(self.full_errors,self.full_errors);self.assertEqual(code,0,self.final)
        self.assertEqual(self.received_count,2);self.assertEqual(self.calls.count('RewardSubmit'),1)
        report=json.loads((Path(self.cfg['network']['directory'])/'host-result.json').read_text())
        self.assertEqual(report['result'],'PASS_EXTERNAL_REWARD_TWO_SNAPSHOT_ENTRY',report)
        self.assertTrue(report['network_cleanup']['network_closed']);self.assertTrue(report['operator']['closed'])
        self.assertEqual(self.mount.gate.receipt['cut']['sequence'],1)
        ROWS.append(dict(case=self._testMethodName,full_cli_actual_entry=True,actual_service_constructor=True,
            service_constructed_during_fixture_setup=True,actual_mounted_entry=True,actual_TLS=True,
            two_formal_completions=2,shared_cut=1,report=report))


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    OUTPUT=PRIVATE/'a_simple_remote_host_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    actual.OUTPUT=OUTPUT;actual.joint.OUTPUT=OUTPUT;actual.transport.OUTPUT=OUTPUT
    before=pins();stream=io.StringIO()
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Cases),
        unittest.TestSuite(EntryCases(name) for name in ('test_console_to_actual_mount_entry_two_saves_and_cleanup',
            'test_lost_reward_ack_holds_same_owner_without_resubmit','test_original_open_failure_never_starts_console')),
        FullRunCase('test_new_cli_run_actual_entry_service_mount_console_two_periods')])
    r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins()
    unchanged=all(sources.get(k)==v for k,v in before.items())
    private=actual.PRIVATE_INPUTS
    stable_private=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in private.items())
    value=dict(schema='san14.simple-remote-host-tests.v1',result='PASS' if r.wasSuccessful() and unchanged and stable_private else 'FAIL',
        tests=r.testsRun,sources=sources,sources_unchanged=unchanged,private_inputs=private,private_inputs_unchanged=stable_private,
        actual_TLS=True,mounted_entry_executed=any(x.get('actual_mounted_entry') for x in ROWS),
        full_cli_actual_entry=any(x.get('full_cli_actual_entry') for x in ROWS),
        actual_journal=True,game_access=False,steam_access=False,native_execution=False,
        native_RAM_PE_rules_publisher_channel_doubles=True,service_cleanup_native_receipts_double=True,
        cases=ROWS,entry_cases=actual.ROWS,failures=[(str(t),d) for t,d in r.errors+r.failures])
    value['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(OUTPUT/'result.json');raise SystemExit(value['result']!='PASS')
