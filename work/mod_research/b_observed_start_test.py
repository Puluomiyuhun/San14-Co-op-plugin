"""Actual startup orchestration/TLS/Journal/Session, explicit native environment doubles."""
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

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_observed_completion_test as fixture
import b_observed_start as start
import b_warm_staging as files
from observed_room_service import HostService,join_guest
from authoritative_sync import next_node
from checkpoint_fresh_save_binding_test import model_artifact

OUTPUT=None;ROWS=[]


class Cases(fixture.Cases):
    def setUp(self):
        oldmanifest=fixture.transport.manifest
        def manifest():
            m=oldmanifest();m['profile']['rules_sha256']=start.digest(start.rules(1,0));return m
        with patch.object(fixture.transport,'manifest',manifest):super().setUp()
        self.order=[];self.thread_errors=[];self.stop=threading.Event()
        # Replace the prior fixture's transport with the actual new HostService,
        # actual join_guest selection/confirmation and actual shared coordinator.
        approved_manifest=deepcopy(self.room.manifest);node=deepcopy(self.c.node)
        fixture.transport.RoomTests.tearDown(self);self.servers=[];self.clients=[]
        self.service=HostService(approved_manifest,node,directory=self.folder/'actual-service',
            listen_host='127.0.0.1',advertise_host='127.0.0.1',control_port=0,download_port=0)
        self.link=join_guest(self.service.invitation);self.c=self.service.wait_bound(5)
        self.room=self.service.room;self.a=self.service.control;self.b=self.link.control
        self.endpoint_owner=self.service;invitation=self.service.invitation
        self.contexts=[];wait_context=self.link.wait_context
        def context(timeout):
            c=wait_context(timeout)
            self.contexts.append((c['period'],c['phase'],c['manifest']['period'] if c['manifest'] else None))
            return c
        self.link.wait_context=context
        self.binding=fixture.BootstrapFreshSaveBinding(self.room,self.c,native_room_id=bytes.fromhex(start.digest(self.c.scope)),
            native_room_epoch=71,artifact_reader=lambda gen:self.artifacts[gen],source_kind='FIXTURE_ONLY')
        self.room.enroll_observed_adapter(self.key,host_sampler=self.host_sample,host_boundary=self.host_boundary,
            host_receipt_key=lambda:self.host_key,source_kind='FIXTURE_ONLY')
        self.rules=fixture.ScopedRules(self.c.scope);self.rules.current.day=11
        fixture.sync_reader(self.guest,self.rules.current)
        initial=self.rules.prepare(fixture.WorldGeneration(1,'1'*64,bytes(self.rules.current)));initial.install()
        self.life=SimpleNamespace(current=initial);self.warm=fixture.WarmMemory(self.rules,self.target,'success',self.guest)
        close=self.link.close
        def closed():self.order.append('network-close');return close()
        self.link.close=closed
        self.config=dict(schema=start.SCHEMA,network=invitation,local=dict(pid=self.guest.pid,birth=self.birth,
            target=str(self.target),initial_target=files.read_file(self.target)[0],initial_node=deepcopy(self.c.node),
            source_player=dict(force=12,ruler=666,district=11),target_player=dict(force=2,ruler=952,district=2),
            records=str(self.folder/'startup'),adapter_key_path=str(self.private_key),
            pair_build=dict(path=str(self.folder/'pair.json'),sha256='a'*64),
            helper_build=dict(path=str(self.folder/'helper.json'),sha256='b'*64),
            source_manifest=dict(path=str(self.folder/'sources.json'),sha256='c'*64),
            rules_build=dict(stage=str(self.folder/'rules.dll'),publisher=str(self.folder/'publisher.exe')),
            steam_paths={},rules=start.rules(1,0),wait_seconds=5,native_timeout=30))
        self.checked=dict(result='OWNED_ENVIRONMENT_PREFLIGHT_DOUBLE',sources=fixture.session_fixture.source_pins())
        self.host_thread=None;self.mark_host=True;self.retained_connection_observed=False

    def tearDown(self):
        self.stop.set()
        if self.host_thread:self.host_thread.join(timeout=6);self.assertFalse(self.host_thread.is_alive())
        if hasattr(self,'service'):self.service.close()
        super().tearDown()

    def offer_first(self):
        self.c.begin_bootstrap();r=self.binding.reserve(1,'mp00000001.s14',self.observation())
        self.artifacts[1]=model_artifact(r.request,1,data=b'owned startup first native Save'*1400)
        self.complete_host(1);self.binding.publish(1,self.observation)

    def advance_host(self):
        try:
            while not self.stop.wait(.01):
                with self.c.lock:
                    if self.c.period==2 and 'B' in self.c.ready:break
            else:return
            # A remains PLANNING with prior manifest until its independent ready.
            self.stop.wait(.35)
            self.service.ready_for_turn()
            while self.c.phase!='RUNNING':
                if self.stop.wait(.01):return
            self.host_fixture.complete_and_rebuild()
            r=self.binding.reserve(2,'mp00000002.s14',self.observation(next_node(self.c.node)))
            self.artifacts[2]=model_artifact(r.request,2,data=b'owned startup second native Save'*1600)
            self.complete_host(2);self.binding.publish(2,lambda:self.observation(next_node(self.c.node)))
            while self.service.guest_finished is None:
                if self.stop.wait(.01):return
            if self.service.guest_finished['native_cleanup_verified']:
                # Simulate A's later .25-second loaded2 polling and native
                # teardown. B must not race this with a socket disconnect.
                self.stop.wait(.35)
                self.assertTrue(self.b.status()['transport_open'])
                self.assertEqual(self.c.connected,{'A','B'})
                self.assertNotIn('network-close',self.order)
                self.retained_connection_observed=True
                if self.mark_host:
                    self.service.mark_host_finished();self.order.append('host-finished')
        except BaseException as exc:self.thread_errors.append(repr(exc))

    def open_owned(self,runner,context,profile,pins):
        # Explicit substitute ONLY for production Session.open environment setup.
        # Actual Session, retained lifecycle, GuestCompletion and predicates remain.
        self.local(profile);runner.session=self.session;runner.reader=self.guest
        runner.guest=start.GuestCompletion(self.session)
        original=self.session.apply_native
        def apply(received,request,p,**kw):
            self.warm.request=request;return original(received,request,p,**kw)
        self.session.apply_native=apply
        def finish():
            self.assertEqual(len(self.session.sessions),2);self.assertEqual(len(self.session.bridge.completed),2)
            self.order.append('native-helper-finish-double')
        self.warm.finish=finish;self.warm.close=lambda:self.order.append('api-close')
        self.guest.close=lambda:self.order.append('reader-close')

    def original_rules(self,reader,**kw):
        self.assertIs(reader,self.guest)
        self.assertTrue(all(self.rules.read(a,16)==bytes([0x90+i])*16 for i,a in enumerate(self.rules.sources)))
        self.order.append('six-original-rules-verified');return dict(six_sources_original=True,fixture=True)

    def execute(self):
        self.runner=start.Runner(self.config,self.link)
        with patch.object(start,'preflight',return_value=self.checked), \
             patch.object(start.Runner,'_open',side_effect=lambda c,p,pins:self.open_owned(self.runner,c,p,pins)), \
             patch.object(start,'require_original_rules',side_effect=self.original_rules), \
             patch.object(start,'require_no_debugger',side_effect=lambda _:self.order.append('no-debugger-double')):
            return self.runner.run()

    def test_entry_two_loads_rules_restore_before_network_close(self):
        self.offer_first();self.host_thread=threading.Thread(target=self.advance_host);self.host_thread.start()
        result=self.execute();self.assertFalse(self.thread_errors)
        self.assertEqual(self.c.period,3);self.assertTrue(result['cleanup']['native_cleanup_verified'])
        self.assertFalse(result['cleanup']['target_file_restored']);self.assertEqual(len(self.runner.received),2)
        self.assertTrue(all(r.journal.status()['status']=='COMPLETED' for r in self.runner.received))
        self.assertEqual(self.endpoint_owner.guest_finished,dict(action='pilot_guest_finished',formal_completions=2,
            native_cleanup_verified=True,retained_native_state=False))
        self.assertEqual(self.order[-4:],['api-close','reader-close','host-finished','network-close'])
        self.assertTrue(self.retained_connection_observed)
        self.assertGreater(json.loads((self.runner.records/'host-finished.json').read_text())['polls'],1)
        self.assertEqual(self.rules.events[-1],['restore',3,2]);self.assertTrue(self.session.lifecycle.current.retired)
        self.assertEqual(self.target.read_bytes(),self.runner.received[-1].verified_file())
        self.assertIn((2,'PLANNING',1),self.contexts)
        self.assertNotIn(self.key.hex(),json.dumps(result));self.assertNotIn(self.room.invite,json.dumps(result))
        ROWS.append(dict(case=self._testMethodName,result=result,order=self.order,rules=self.rules.events,
                         warm=self.warm.events,contexts=self.contexts,production_open_executed=False))

    def test_native_failure_retains_owner_no_final_restore(self):
        self.offer_first();self.warm.case='load-failed'
        with self.assertRaisesRegex(RuntimeError,'load failure') as caught:self.execute()
        self.assertIs(caught.exception.retained_runner,self.runner)
        self.assertTrue(self.runner.cleanup['retained_native_state']);self.assertEqual(self.runner.phase,'TERMINAL')
        self.assertNotIn('api-close',self.order);self.assertNotIn('reader-close',self.order)
        self.assertEqual(len([e for e in self.rules.events if e[0]=='restore']),1)
        self.assertEqual(len([e for e in self.warm.events if e[0]=='load']),1)
        with self.assertRaisesRegex(ValueError,'replayed'):self.runner.run()
        ROWS.append(dict(case=self._testMethodName,cleanup=self.runner.cleanup,order=self.order,warm=self.warm.events))

    def test_post_second_restore_failure_retains_without_reloading(self):
        self.offer_first();self.host_thread=threading.Thread(target=self.advance_host);self.host_thread.start()
        oldprepare=self.rules.prepare
        def prepare(w):
            port=oldprepare(w)
            if w.generation==3:
                original=port._publisher
                def publish(op):
                    if op=='restore':raise OSError('Owned unknown publisher return')
                    return original(op)
                port._publisher=publish
            return port
        self.rules.prepare=prepare
        with self.assertRaisesRegex(OSError,'unknown publisher'):self.execute()
        self.assertEqual(self.c.period,3);self.assertTrue(self.runner.cleanup['retained_native_state'])
        self.assertEqual(len(self.runner.guest.history),2);self.assertNotIn('api-close',self.order)
        self.assertFalse(self.endpoint_owner.guest_finished['native_cleanup_verified'])
        ROWS.append(dict(case=self._testMethodName,cleanup=self.runner.cleanup,order=self.order))

    def test_exact_config_refuses_before_open_or_join(self):
        for alter in (lambda v:v['local'].update(target=str(self.folder/'bad.s14')),
                      lambda v:v['local'].update(wait_seconds=0),lambda v:v['local'].update(pid=True)):
            v=deepcopy(self.config);alter(v)
            with self.assertRaises(ValueError):start.validate_config(v)
        with patch.object(start,'GameReader',side_effect=AssertionError('No process')), \
             patch.object(start,'join_guest',side_effect=AssertionError('No network')):
            with self.assertRaises(FileNotFoundError):start.preflight(self.config)
        self.assertFalse((self.folder/'startup').exists());self.assertFalse(self.warm.events)
        ROWS.append(dict(case=self._testMethodName,process_opened=False,native_calls=0))

    def test_primary_failure_survives_logging_failure(self):
        self.offer_first();self.warm.case='load-failed';original=start.Runner._record
        def record(r,name,value):
            if name=='failed.json':raise OSError('Owned failure-log disk error')
            return original(r,name,value)
        with patch.object(start.Runner,'_record',record):
            with self.assertRaisesRegex(RuntimeError,'load failure') as caught:self.execute()
        self.assertIs(caught.exception.retained_runner,self.runner)
        self.assertEqual(caught.exception.record_error,'OSError')
        ROWS.append(dict(case=self._testMethodName,primary_preserved=True,retained=True))

    def test_open_birth_failure_closes_only_read_handle(self):
        self.offer_first();self.runner=start.Runner(self.config,self.link)
        self.guest.close=lambda:self.order.append('reader-close')
        with patch.object(start,'preflight',return_value=self.checked), \
             patch.object(start,'GameReader',return_value=self.guest), \
             patch.object(start,'process_birth',return_value=self.birth+1):
            with self.assertRaisesRegex(ValueError,'incarnation changed') as caught:self.runner.run()
        self.assertIs(caught.exception.retained_runner,self.runner);self.assertIsNone(self.runner.session)
        self.assertEqual(self.order,['reader-close','network-close']);self.assertFalse(self.warm.events)
        self.assertTrue(self.runner.cleanup['local_handles_closed'])
        self.assertFalse(self.runner.cleanup['native_cleanup_verified'])
        ROWS.append(dict(case=self._testMethodName,cleanup=self.runner.cleanup,order=self.order))

    def test_local_close_failure_never_notifies_clean(self):
        self.offer_first();self.host_thread=threading.Thread(target=self.advance_host);self.host_thread.start()
        original=self.open_owned
        def opened(*args):
            original(*args)
            def fail():self.order.append('api-close-failed');raise OSError('Owned local handle close failure')
            self.warm.close=fail
        with patch.object(self,'open_owned',side_effect=opened):
            with self.assertRaisesRegex(OSError,'handle close'):self.execute()
        self.assertTrue(self.runner.cleanup['sources_restored'])
        self.assertFalse(self.runner.cleanup['native_cleanup_verified'])
        self.assertFalse(self.runner.cleanup['local_handles_closed'])
        self.assertTrue(self.endpoint_owner.guest_finished['retained_native_state'])
        self.assertFalse(self.endpoint_owner.guest_finished['native_cleanup_verified'])
        self.assertNotIn('reader-close',self.order)
        ROWS.append(dict(case=self._testMethodName,cleanup=self.runner.cleanup,order=self.order))

    def test_read_only_check_real_private_files_and_source_drift(self):
        # Actual private key DACL/read, exact target file identity and source
        # closure. Approved native binary lookup and RAM are explicit doubles.
        c=deepcopy(self.config);v=c['local'];path=Path(v['source_manifest']['path'])
        manifest=dict(result='PASS',inputs_unchanged=True,sources=pins())
        path.write_text(json.dumps(manifest),encoding='utf-8');v['source_manifest']['sha256']=fixture.sha(path.read_bytes())
        storage={}
        for name in ('steam_api64.dll','steamclient64.dll'):
            f=self.folder/name;f.write_bytes(b'owned build identity double '+name.encode())
            v['steam_paths'][name]=str(f);storage[name]=fixture.sha(f.read_bytes())
        self.life.current.restore();self.guest.close=lambda:self.order.append('reader-close')
        configpath=self.folder/'config.json';configpath.write_text(json.dumps(c),encoding='utf-8');output=io.StringIO()
        with patch.object(start,'approved_builds',return_value=({},{})), \
             patch.object(start,'RulesBuild',return_value=SimpleNamespace(check=lambda:None)), \
             patch.object(start,'STEAM_HASHES',storage), \
             patch.object(start,'dll_identity',side_effect=lambda p:dict(sha256=fixture.sha(Path(p).read_bytes()))), \
             patch.object(start,'GameReader',return_value=self.guest) as reader, \
             patch.object(start,'process_birth',return_value=self.birth), \
             patch.object(start,'require_original_rules',side_effect=self.original_rules), \
             patch.object(start,'require_no_debugger',return_value=None), \
             patch.object(start,'join_guest',side_effect=AssertionError('Check must not join')), \
             patch('sys.stdout',output):
            self.assertEqual(start.main(['--config',str(configpath),'--check','--no-new-commands']),0)
            self.assertEqual(reader.call_count,1)
            manifest['sources'][str(HERE/'b_observed_start.py')]='0'*64
            path.write_text(json.dumps(manifest),encoding='utf-8');v['source_manifest']['sha256']=fixture.sha(path.read_bytes())
            with self.assertRaisesRegex(ValueError,'source drift'):start.preflight(c)
            self.assertEqual(reader.call_count,1)
        result=json.loads(output.getvalue());self.assertEqual(result['native_calls'],0)
        self.assertFalse(result['network_joined']);self.assertFalse(result['claim_created'])
        self.assertFalse(Path(v['records']).exists());self.assertNotIn(self.key.hex(),output.getvalue())
        ROWS.append(dict(case=self._testMethodName,check=result,actual_private_key_and_file_reads=True,
                         native_artifact_and_RAM_doubles=True,source_drift_before_process_open=True))

    def test_missing_host_finish_times_out_without_native_replay(self):
        self.config['local']['wait_seconds']=2;self.mark_host=False
        self.offer_first();self.host_thread=threading.Thread(target=self.advance_host);self.host_thread.start()
        with self.assertRaisesRegex(ValueError,'Host finish acknowledgement timed out') as caught:self.execute()
        self.assertIs(caught.exception.retained_runner,self.runner)
        self.assertTrue(self.retained_connection_observed)
        self.assertTrue(self.runner.cleanup['native_cleanup_verified'])
        self.assertEqual(len(self.runner.guest.history),2)
        self.assertEqual(len([e for e in self.warm.events if e[0]=='load']),2)
        self.assertFalse((self.runner.records/'host-finished.json').exists())
        self.assertEqual(self.order.count('network-close'),1)
        ROWS.append(dict(case=self._testMethodName,native_completions=2,host_finish_missing=True,
                         connection_held_until_timeout=True,order=self.order))


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.update(Path(p) for p in fixture.session_fixture.source_pins())
    paths.add(Path(__file__).resolve())
    return {str(p):fixture.sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    OUTPUT=PRIVATE/'b_observed_start_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    fixture.transport.OUTPUT=OUTPUT;before=pins();stream=io.StringIO()
    names=[n for n in Cases.__dict__ if n.startswith('test_')]
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(Cases(n) for n in names))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins()
    report=dict(result='PASS' if tests.wasSuccessful() and sources==before else 'FAIL',tests=tests.testsRun,
        inputs_unchanged=sources==before,sources=sources,cases=ROWS,actual_tls=True,actual_session=True,
        actual_guest_completion=True,actual_rules_lifecycle=True,actual_journal=True,production_open_executed=False,
        native_RAM_load_publish_helper_doubles=True,game_access=False,
        failures=[(str(t),d) for t,d in tests.errors+tests.failures])
    report['artifacts']={str(p):fixture.sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(0 if report['result']=='PASS' else 1)
