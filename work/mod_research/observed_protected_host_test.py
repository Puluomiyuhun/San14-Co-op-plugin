"""Protected CLI composition: real local TLS, explicitly doubled native lifecycle.
Does not discover or open SAN14/Steam. Native rule coexistence is tested by the
separate a_protected suite, not inferred from this orchestration test.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,io,json,sys,threading,time,unittest
import observed_protected_host as host
import observed_room_service as service
import checkpoint_complete_live_capture as capture_module
from checkpoint_fresh_save_binding_test import manifest
from human_rules_activation_room import GAME_SHA,rules
from authoritative_sync import digest

ROOT=Path(__file__).resolve().parents[2];PRIVATE=ROOT.parent/'mod_research';OUTPUT=None

def configuration(folder):
    m=manifest();m['profile']['game_sha256']=GAME_SHA;m['profile']['rules_sha256']=digest(rules(0,0))
    return dict(schema='san14.a-protected-host.v1',manifest=m,rules=rules(0,0),
        adapter_key_path=str(folder/'key'),network_entry_test_run=str(folder/'prior-test'),
        rules_build=dict(stage=str(folder/'rules.dll'),publisher=str(folder/'rules-publisher.exe')),
        network=dict(listen_host='127.0.0.1',advertise_host='127.0.0.1',control_port=42141,
                     download_port=42142,directory=str(folder/'room')),
        native=dict(pid=123,wait_seconds=3,**{k:str(folder/k) for k in host.NATIVE_PATHS}))


class Tests(unittest.TestCase):
    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir();self.c=configuration(self.folder)

    def test_exact_config_rejects_old_schema_and_unapproved_rules_options(self):
        host.validate_config(self.c)
        for field,value in [('schema','san14.a-observed-host.v1'),('rules_build',dict(stage='relative.dll',publisher='relative.exe')),
                            ('rules_build',{**self.c['rules_build'],'source_kind':'OWNED_FIXTURE'}),
                            ('network_entry_test_run','relative')]:
            bad=deepcopy(self.c);bad[field]=value
            with self.assertRaises(ValueError):host.validate_config(bad)
        for key in ('reward_flow','input_fence'):
            bad=deepcopy(self.c);bad[key]=True
            with self.assertRaises(ValueError):host.validate_config(bad)

    def test_default_and_check_do_not_capture_or_join(self):
        with patch.object(host.native,'capture',side_effect=AssertionError('no game')),             patch.object(host,'HostService',side_effect=AssertionError('no network')),             patch.object(host,'read_config',return_value=self.c),patch.object(host,'check',return_value=(None,None,None)),             patch('sys.stdout',new=io.StringIO()):
            self.assertEqual(host.main([]),0)
            self.assertEqual(host.main(['--check','--config','unused']),0)
        with patch.object(host,'read_config',side_effect=AssertionError('not before flag')),             patch('sys.stderr',new=io.StringIO()),self.assertRaises(SystemExit):
            host.main(['--execute','--config','unused'])

    def test_check_validates_native_and_rule_artifacts_before_capture(self):
        calls=[];build=SimpleNamespace(check=lambda:calls.append('rules-check'))
        def previous(c):
            self.assertEqual(c['schema'],'san14.a-observed-host.v1')
            self.assertNotIn('rules_build',c);self.assertNotIn('network_entry_test_run',c)
            calls.append('native-check');return SimpleNamespace(entry_test_run='approved-protected'),b'key'
        with patch.object(host,'verify_network_tests',side_effect=lambda p:calls.append('network-tests')),             patch.object(host.predecessor,'check',side_effect=previous),patch.object(host,'RulesBuild',return_value=build),patch.object(host.native,'verify_entry_tests',side_effect=lambda p:calls.append('protected-tests')),             patch.object(host.native,'capture',side_effect=AssertionError('no game')):
            args,key,actual=host.check(self.c);self.assertEqual(args.entry_test_run,'approved-protected');self.assertEqual(key,b'key');self.assertIs(actual,build)
        self.assertEqual(calls,['network-tests','native-check','protected-tests','rules-check'])
        with patch.object(host,'verify_network_tests',return_value=None),patch.object(host.predecessor,'check',side_effect=previous),patch.object(host.native,'verify_entry_tests',return_value=None):
            with self.assertRaises(FileNotFoundError):host.check(self.c)

    def test_test_source_drift_refuses_launch(self):
        folder=self.folder/'approval';folder.mkdir();source=self.folder/'source.py';source.write_text('before')
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        value=dict(schema='san14.protected-host-tests.v1',result='PASS',sources_unchanged=True,actual_TLS=True,
                   game_access=False,sources={str(Path(host.__file__).resolve()):sha(Path(host.__file__)),str(source):sha(source)})
        (folder/'result.json').write_text(json.dumps(value))
        host.verify_network_tests(folder);source.write_text('after')
        with self.assertRaisesRegex(ValueError,'source changed'):host.verify_network_tests(folder)

    def run_network(self,*,fail=False,cleanup=False):
        owner=self;services=[];threads=[];errors=[];seen={};guest_ready=threading.Event();original=service.HostService
        source=self.folder/'owned-save';source.write_bytes(b'owned source checkpoint double')
        self.c['manifest']['profile']['checkpoint_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
        # Explicit ephemeral ports only in this owned test factory. Production
        # validation still requires separately configured nonzero ports.
        def factory(*args,**kwargs):
            kwargs.update(control_port=0,download_port=0);s=original(*args,**kwargs);services.append(s)
            def guest():
                g=None
                try:
                    g=service.join_guest(s.invitation);g.wait_context(3);guest_ready.set()
                    if fail:
                        deadline=time.monotonic()+4
                        while not seen.get("called") and time.monotonic()<deadline:time.sleep(.01)
                        return
                    deadline=time.monotonic()+4
                    while len(s.coordinator.applied_receipts)!=2:
                        if time.monotonic()>deadline:raise AssertionError('native fixture did not complete')
                        time.sleep(.01)
                    reply=g.control.request(dict(action='pilot_guest_finished',formal_completions=2,
                        native_cleanup_verified=True,retained_native_state=False))
                    owner.assertTrue(reply['ok'],reply)
                    while not g.control.request(dict(action='pilot_host_finished'))['host_finished']:
                        if time.monotonic()>deadline:raise AssertionError('host barrier missing')
                        time.sleep(.01)
                except BaseException as e:errors.append(repr(e))
                finally:
                    if g:g.close()
            t=threading.Thread(target=guest);threads.append(t);t.start();return s
        class Entry:
            def __init__(self,room,coordinator,key,*,no_new_commands):
                self.room,self.coordinator=room,coordinator;owner.assertIs(no_new_commands,True)
            def status(self):
                return dict(protection=dict(installed_once=True,restore_verified=cleanup,retained_or_unknown=not cleanup))
        build=object()
        def execute(args,path,captured,*,entry,on_event,rules_build,settings):
            owner.assertIs(rules_build,build);owner.assertEqual(settings,owner.c['rules']);owner.assertTrue(guest_ready.wait(4));seen['called']=True
            if fail:raise RuntimeError('owned native unknown; no retry')
            # Lifecycle substitute only. These markers test the real cleanup
            # barrier and must never be counted as native/Journal proof.
            with entry.room.lock,entry.coordinator.lock:
                entry.coordinator.applied_receipts.update({'owned-fixture-1':{},'owned-fixture-2':{}})
                entry.coordinator.period=3
            return 0
        with ExitStack() as stack:
            for target,name,value in [(host,'check',lambda c:(SimpleNamespace(pid=123,wait_seconds=3),b'k'*32,build)),
                (host.native,'capture',lambda pid:(source,dict(planning={'context':{'snapshot':dict(date=dict(year=203,month=8,day=11),player=dict(force_id=12,ruler_id=666))}}))),
                (host,'HostService',factory),(host.native,'ProtectedRoomEntry',Entry),(host.native,'execute',execute),
                (capture_module,'SOURCE',source),(capture_module,'SOURCE_SHA',self.c['manifest']['profile']['checkpoint_sha256'])]:
                stack.enter_context(patch.object(target,name,value))
            stack.enter_context(patch('sys.stdout',new=io.StringIO()))
            code=host.run(self.c,no_new_commands=True)
        for t in threads:t.join(5);self.assertFalse(t.is_alive())
        self.assertFalse(errors,errors);self.assertTrue(seen['called']);self.assertTrue(services[0]._closed)
        report=json.loads((Path(self.c['network']['directory'])/'host-result.json').read_text())
        self.assertFalse(report['reward_flow_enabled']);self.assertFalse(report['complete_input_fence_proven'])
        return code,report

    def test_real_tls_cleanup_barrier_with_explicit_native_double(self):
        code,report=self.run_network(cleanup=True)
        self.assertEqual(code,0,report);self.assertTrue(report['guest_disconnect']['guest_control_disconnected'])

    def test_native_failure_closes_network_without_retry(self):
        code,report=self.run_network(fail=True)
        self.assertEqual(code,1);self.assertIn('owned native unknown',report['error'])
        self.assertFalse(report['automatic_retry']);self.assertTrue(report['a_human_ai_rules_installed']);self.assertFalse(report['a_human_ai_rules_restored'])

    def test_native_zero_without_rules_restore_cannot_pass(self):
        code,report=self.run_network(cleanup=False)
        self.assertEqual(code,1,report)


if __name__=='__main__':
    OUTPUT=PRIVATE/'observed_protected_host_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve());sources={str(p):sha(p) for p in paths if p.is_relative_to(ROOT) and p.suffix=='.py'}
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    stable=all(sha(Path(p))==h for p,h in sources.items())
    value=dict(schema='san14.protected-host-tests.v1',result='PASS' if r.wasSuccessful() and r.testsRun==7 and stable else 'FAIL',
        tests=r.testsRun,sources=sources,sources_unchanged=stable,actual_TLS=True,game_access=False,
        native_lifecycle_double=True,formal_receipts_double=True,two_real_clients_proven=False,
        failures=[(str(t),v) for t,v in r.errors+r.failures])
    value['artifacts']={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(OUTPUT/'result.json');raise SystemExit(value['result']!='PASS')
