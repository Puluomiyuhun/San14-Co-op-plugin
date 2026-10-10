"""Three-checkpoint B Runner over actual service TLS with owned native substitutes.

Production preflight and Session.open environment installation are explicit test
substitutes. Actual Runner, Session, rule lifecycle, journal, signed GuestCompletion,
download service and cleanup handshake execute. No game or native install proof.
"""
from copy import deepcopy
from datetime import datetime
import hashlib,io,json,sys,threading,time,unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_observed_three_start as start
import observed_three_room_service_test as fixture
import b_observed_chain_completion_test as chain
import b_observed_completion_test as prior
import b_warm_staging as files
from a_room_three_test import decode_modeled_artifact
from authoritative_sync import next_node
from observed_completion_contract import ACTION,unpack

OUTPUT=None;ROWS=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()

class Cases(unittest.TestCase):
    host_sample=fixture.Cases.host_sample
    host_boundary=fixture.Cases.host_boundary
    local=fixture.Cases.local
    observation=fixture.Cases.observation
    _network_setup=fixture.Cases._network_setup
    wait=fixture.Cases.wait

    def setUp(self):
        fixture.OUTPUT=OUTPUT;old=fixture.transport.manifest
        def manifest():
            m=old();m['profile']['rules_sha256']=start.digest(start.rules(1,0));return m
        with patch.object(fixture.transport,'manifest',manifest):fixture.Cases.setUp(self)
        self.order=[];self.errors=[];self.stop=threading.Event();self.host_thread=None
        self.mark_host=True;self.connection_retained=False;self.fail_at=None
        close=self.guest_link.close
        def closed():self.order.append('network-close');return close()
        self.guest_link.close=closed
        self.config=dict(schema=start.SCHEMA,network=deepcopy(self.owner.invitation),local=dict(
            pid=self.guest.pid,birth=self.birth,target=str(self.target),initial_target=files.read_file(self.target)[0],
            initial_node=deepcopy(self.c.node),source_player=dict(force=12,ruler=666,district=11),
            target_player=dict(force=2,ruler=952,district=2),records=str(self.folder/'runner'),
            adapter_key_path=str(self.private_key),pair_build=dict(path=str(self.folder/'pair.json'),sha256='a'*64),
            helper_build=dict(path=str(self.folder/'helper.json'),sha256='b'*64),
            source_manifest=dict(path=str(self.folder/'sources.json'),sha256='c'*64),
            rules_build=dict(stage=str(self.folder/'rules.dll'),publisher=str(self.folder/'publisher.exe')),
            steam_paths={},rules=start.rules(1,0),wait_seconds=5,native_timeout=30))
        self.checked=dict(result='OWNED_ENVIRONMENT_PREFLIGHT_DOUBLE',sources=chain.pins())

    def tearDown(self):
        self.stop.set()
        if self.host_thread:self.host_thread.join(timeout=5);self.assertFalse(self.host_thread.is_alive())
        fixture.Cases.tearDown(self)

    def offer(self,n):
        if n==1:self.c.begin_bootstrap();node=deepcopy(self.c.node)
        else:node=next_node(self.c.node)
        prior.put_date(self.host,node)
        reserved=self.binding.reserve(n,f'mp{n:08d}.s14',self.observation(node))
        self.artifacts[n]=decode_modeled_artifact(reserved.request,n,data=('OWNED B RUNNER SAVE '+str(n)).encode()*2048)
        self.host_key=sha(('owned Save receipt '+str(n)).encode())
        return self.binding.publish(n,lambda:self.observation(node))

    def advance_host(self):
        try:
            for n in (2,3):
                while not self.stop.wait(.01):
                    with self.c.lock:
                        if self.c.period==n and 'B' in self.c.ready:break
                        if self.c.phase=='HELD':return
                else:return
                self.stop.wait(.1);self.owner.ready_for_turn()
                while self.c.phase!='RUNNING':
                    if self.stop.wait(.01):return
                self.offer(n)
            while self.owner.guest_finished is None:
                if self.stop.wait(.01):return
            if self.owner.guest_finished['native_cleanup_verified']:
                self.stop.wait(.2)
                self.assertTrue(self.b.status()['transport_open']);self.assertEqual(self.c.connected,{'A','B'})
                self.assertNotIn('network-close',self.order);self.connection_retained=True
                if self.mark_host:self.owner.mark_host_finished();self.order.append('host-finished')
        except BaseException as exc:self.errors.append(repr(exc))

    def launch_host(self):
        self.offer(1);self.host_thread=threading.Thread(target=self.advance_host);self.host_thread.start()

    def open_owned(self,runner,context,profile,pins):
        self.local(profile);runner.session=self.session;runner.reader=self.guest;runner.guest=self.adapter
        original=self.session.apply_native
        def apply(received,request,p,**kw):
            self.warm.request=request
            if self.fail_at==request.generation-1:self.warm.case='load-failed'
            return original(received,request,p,**kw)
        self.session.apply_native=apply
        def finish():
            self.assertEqual(len(self.session.sessions),3);self.assertEqual(len(self.session.bridge.completed),3)
            self.order.append('native-helper-finish-double')
        self.warm.finish=finish;self.warm.close=lambda:self.order.append('api-close')
        self.guest.close=lambda:self.order.append('reader-close')

    def original_rules(self,reader,**kw):
        self.assertIs(reader,self.guest)
        self.assertTrue(all(self.rules.read(a,16)==bytes([0x90+i])*16 for i,a in enumerate(self.rules.sources)))
        self.order.append('six-original-rules-verified');return dict(six_sources_original=True,fixture=True)

    def execute(self):
        self.runner=start.Runner(self.config,self.guest_link)
        with patch.object(start,'preflight',return_value=self.checked), \
             patch.object(start.Runner,'_open',side_effect=lambda c,p,pins:self.open_owned(self.runner,c,p,pins)), \
             patch.object(start,'require_original_rules',side_effect=self.original_rules), \
             patch.object(start,'require_no_debugger',side_effect=lambda _:self.order.append('no-debugger-double')):
            return self.runner.run()

    def test_actual_runner_three_signed_loads_cleanup_then_barrier(self):
        self.launch_host();result=self.execute();self.assertFalse(self.errors)
        self.assertEqual(result['result'],'PASS_B_OBSERVED_THREE_CHECKPOINTS_RULES_RESTORED')
        self.assertEqual((self.c.period,self.c.node['month'],self.c.node['day']),(4,9,1))
        self.assertEqual(len(self.runner.received),3)
        self.assertTrue(all(r.journal.status()['status']=='COMPLETED' for r in self.runner.received))
        self.assertEqual(len(self.owner._seal_started),2)
        self.assertEqual(self.order[-4:],['api-close','reader-close','host-finished','network-close'])
        self.assertTrue(self.connection_retained);self.assertTrue(self.session.lifecycle.current.retired)
        self.assertEqual(self.rules.events[-1],['restore',4,2])
        self.assertFalse(result['cleanup']['target_file_restored']);self.assertFalse(result['cleanup']['native_modules_unloaded'])
        self.assertEqual(self.target.read_bytes(),self.runner.received[-1].verified_file())
        self.assertEqual(self.owner.guest_finished['formal_completions'],3)
        ROWS.append(dict(case=self._testMethodName,result=result,order=self.order,rules=self.rules.events,
            warm=self.warm.events,production_open_executed=False,cleanup_reads_and_native_apis_doubled=True))

    def test_third_native_failure_retains_and_never_replays(self):
        self.fail_at=3;self.launch_host()
        with self.assertRaisesRegex(RuntimeError,'load failure') as caught:self.execute()
        self.assertIs(caught.exception.retained_runner,self.runner)
        self.assertEqual(len(self.runner.guest.history),2);self.assertEqual(self.c.period,3)
        self.assertTrue(self.runner.cleanup['retained_native_state']);self.assertEqual(self.runner.phase,'TERMINAL')
        self.assertNotIn('native-helper-finish-double',self.order);self.assertNotIn('api-close',self.order)
        self.assertEqual(len([e for e in self.warm.events if e[0]=='load']),3)
        self.assertEqual(self.owner.guest_finished['formal_completions'],2)
        self.assertFalse(self.owner.guest_finished['native_cleanup_verified'])
        with self.assertRaisesRegex(ValueError,'replayed'):self.runner.run()

    def test_third_rules_restore_failure_does_not_close_native_owners(self):
        old=self.rules.prepare
        def prepare(w):
            port=old(w)
            if w.generation==4:
                publish=port._publisher
                def failed(operation):
                    if operation=='restore':raise OSError('Owned final restore unknown')
                    return publish(operation)
                port._publisher=failed
            return port
        self.rules.prepare=prepare;self.launch_host()
        with self.assertRaisesRegex(OSError,'restore unknown'):self.execute()
        self.assertEqual(self.c.period,4);self.assertEqual(len(self.runner.guest.history),3)
        self.assertNotIn('api-close',self.order);self.assertTrue(self.runner.cleanup['retained_native_state'])
        self.assertFalse(self.owner.guest_finished['native_cleanup_verified'])

    def test_third_completion_reply_loss_keeps_unknown_and_no_cleanup(self):
        request=self.b.request
        def lose(value):
            result=request(value)
            if value.get('action')==ACTION and unpack(self.key,value)['kind']=='complete' and self.c.period==4:
                raise EOFError('Owned third completion reply lost')
            return result
        self.b.request=lose;self.launch_host()
        with self.assertRaisesRegex(EOFError,'reply lost'):self.execute()
        self.assertEqual(self.c.period,4);self.assertEqual(len(self.runner.guest.history),2)
        self.assertEqual(self.runner.received[-1].journal.status()['status'],'COMPLETED')
        self.assertTrue(self.runner.cleanup['retained_native_state']);self.assertFalse(self.runner.cleanup['native_cleanup_verified'])
        self.assertIsNone(self.owner.guest_finished);self.assertEqual(self.runner.notification_error,'ValueError')
        self.assertNotIn('native-helper-finish-double',self.order)

    def test_existing_records_preflight_failure_never_writes_or_notifies(self):
        records=Path(self.config['local']['records']);records.mkdir();sentinel=records/'prior.bin';sentinel.write_bytes(b'prior-run')
        runner=start.Runner(self.config,self.guest_link)
        with patch.object(start,'GameReader',side_effect=AssertionError('No process access')):
            with self.assertRaisesRegex(ValueError,'Fresh records'):runner.run()
        self.assertEqual(list(records.iterdir()),[sentinel]);self.assertEqual(sentinel.read_bytes(),b'prior-run')
        self.assertFalse(runner.notify_attempted);self.assertFalse(runner._owns_records)
        self.assertIsNone(self.owner.guest_finished);self.assertFalse(self.warm.events)

    def test_default_help_is_inert_and_old_schema_refused(self):
        with patch.object(start,'GameReader',side_effect=AssertionError('No process')), \
             patch.object(start,'join_guest',side_effect=AssertionError('No network')), \
             patch('sys.stdout',new=io.StringIO()):
            self.assertEqual(start.main([]),0)
        wrong=deepcopy(self.config);wrong['schema']='san14.b-observed-start.v1'
        with self.assertRaises(ValueError):start.validate_config(wrong)
        self.assertFalse(Path(self.config['local']['records']).exists())

    def test_missing_three_room_source_pin_refused_before_native_preflight(self):
        config=deepcopy(self.config);spec=config['local']['source_manifest'];path=Path(spec['path'])
        sources=pins();del sources[str(HERE/'a_room_three_protocol.py')]
        path.write_text(json.dumps(dict(result='PASS',inputs_unchanged=True,sources=sources)),encoding='utf-8')
        spec['sha256']=sha(path.read_bytes())
        with patch.object(start,'GameReader',side_effect=AssertionError('No process')), \
             patch.object(start,'approved_builds',side_effect=AssertionError('No native build validation yet')):
            with self.assertRaisesRegex(ValueError,'Startup source missing: a_room_three_protocol.py'):start.preflight(config)
        self.assertFalse(Path(config['local']['records']).exists());self.assertFalse(self.warm.events)

    def test_host_finish_timeout_does_not_repeat_native_or_finish_notification(self):
        self.config['local']['wait_seconds']=2;self.mark_host=False;self.launch_host()
        with self.assertRaisesRegex(ValueError,'Host finish acknowledgement timed out'):self.execute()
        self.assertTrue(self.connection_retained);self.assertTrue(self.runner.cleanup['native_cleanup_verified'])
        self.assertEqual(len(self.runner.guest.history),3);self.assertEqual(len([e for e in self.warm.events if e[0]=='load']),3)
        self.assertEqual(self.order.count('network-close'),1);self.assertTrue(self.runner.notify_attempted)
        self.assertFalse((self.runner.records/'host-finished.json').exists())

def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.update(Path(p) for p in chain.pins());paths.add(Path(__file__).resolve())
    return {str(p):sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}

if __name__=='__main__':
    OUTPUT=PRIVATE/'b_observed_three_start_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    before=pins();log=io.StringIO();run=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(log.getvalue(),encoding='utf-8');after=pins()
    report=dict(result='PASS' if run.wasSuccessful() and before==after else 'FAIL',tests=run.testsRun,sources=after,
        inputs_unchanged=before==after,cases=ROWS,actual_runner=True,actual_tls_service=True,actual_journals=True,
        actual_signed_formal_completion=True,actual_b_chain_session=True,actual_ready_and_cleanup_handshake=True,
        native_save_load_rules_snapshot_and_cleanup_doubles=True,production_preflight_executed=False,
        production_session_open_executed=False,game_access=False,native_gameplay_enabled=False,full_world_verified=False,
        failures=[(str(t),d) for t,d in run.errors+run.failures])
    report['artifacts']={str(p):sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue());print(OUTPUT/'result.json');raise SystemExit(report['result']!='PASS')
