"""Local state/configuration lifetime, without process or native operations."""
from datetime import datetime
import io,json,os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_portable_guest as entry
import b_observed_start as startup
import b_warm_start as claims
import portable_release as core
OUTPUT=None


class Cases(unittest.TestCase):
    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir()
        self.env=patch.dict(os.environ,LOCALAPPDATA=str(self.folder/'user-local'));self.env.start();self.addCleanup(self.env.stop)

    def test_persistent_claim_survives_new_binding_and_state_restores(self):
        old=claims.PRIVATE
        with entry.state_binding() as first:
            records=first/'b_warm_start_claims';records.mkdir(parents=True)
            (records/'prior.json').write_text(json.dumps(dict(pid=4242,birth=999)))
            with self.assertRaisesRegex(ValueError,'Existing process attempt'):claims.refuse_prior_attempt(4242,999)
        self.assertEqual(claims.PRIVATE,old)
        with entry.state_binding() as second:
            self.assertEqual(first,second)
            with self.assertRaisesRegex(ValueError,'Existing process attempt'):claims.refuse_prior_attempt(4242,999)
            claims.refuse_prior_attempt(4242,1000)
        self.assertEqual(claims.PRIVATE,old)

    def test_state_restores_on_failure_without_deleting_claims(self):
        before=claims.PRIVATE
        with self.assertRaises(RuntimeError):
            with entry.state_binding():raise RuntimeError('Owned failure')
        self.assertEqual(claims.PRIVATE,before)

    def make(self):
        assets=[];components={}
        for name in ('pair','helper','reward','input'):
            src=self.folder/(name+'.json');src.write_text('{}')
            path='native/'+name+'/result.json';digest=core.sha(src.read_bytes())
            assets.append(dict(source=src,path=path,sha256=digest,role='provenance'))
            components[name]=dict(producer_provenance=path,producer_result_sha256=digest)
        components['rules']={}
        for name in ('stage','publisher'):
            src=self.folder/(name+'.bin');src.write_bytes(b'owned-not-native')
            path='native/rules/'+name+'.bin';assets.append(dict(source=src,path=path,sha256=core.sha(src.read_bytes()),role='native'))
            components['rules'][name]=path
        record=core.write_bundle(self.folder/'release',assets,dict(components=components))
        return core.Release(record['root'],record['manifest_sha256'])

    def local(self):
        machine={key:'local-test-value' for key in startup.LOCAL_KEYS-entry.GENERATED}
        machine.update(pid=4242,birth=1000)
        return dict(schema=entry.LOCAL_SCHEMA,network={},local=machine,window={},report_key_path='report',cut_key_path='cut')

    def test_generated_paths_are_local_and_source_manifest_is_explicit_producer_view(self):
        release=self.make();local=self.local();binding=SimpleNamespace(source_pins={'owned-source.py':'a'*64})
        config=entry.materialize(release,local,binding);v=config['startup']['local']
        self.assertEqual(v['pid'],4242);self.assertEqual(v['birth'],1000)
        self.assertTrue(Path(v['records']).is_relative_to(entry.local_state_root()))
        self.assertFalse(Path(v['records']).exists())
        value=json.loads(Path(v['source_manifest']['path']).read_text())
        self.assertEqual(value['approval_kind'],'producer_verified_release')
        self.assertFalse(value['recipient_native_execution_verified'])
        second=entry.materialize(release,local,binding)
        self.assertEqual(v['source_manifest'],second['startup']['local']['source_manifest'])
        self.assertNotEqual(v['records'],second['startup']['local']['records'])
        self.assertEqual(config['reward_build']['run'],str(release.root/'native/reward'))

    def test_producer_build_fields_cannot_be_smuggled_into_local_config(self):
        release=self.make();local=self.local();local['local']['pair_build']={}
        with self.assertRaises(ValueError):entry.materialize(release,local,SimpleNamespace(source_pins={}))

    def test_default_and_missing_execute_condition_never_open_release(self):
        with patch.object(entry,'Release',side_effect=AssertionError('No release access')),patch('sys.stdout',new=io.StringIO()):
            self.assertEqual(entry.main([]),0)
            with patch('sys.stderr',new=io.StringIO()),self.assertRaises(SystemExit):
                entry.main(['--execute','--release-root','x','--release-sha256','a'*64,'--local-config','x'])


if __name__=='__main__':
    OUTPUT=PRIVATE/'b_portable_guest_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    report=dict(result='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,
        sources={str(HERE/n):core.sha((HERE/n).read_bytes()) for n in ('b_portable_guest.py','b_portable_guest_test.py','portable_release.py')},
        game_access=False,native_execution=False,config_fixture_only=True,actual_persistent_claim_check=True)
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(OUTPUT);raise SystemExit(not result.wasSuccessful())
