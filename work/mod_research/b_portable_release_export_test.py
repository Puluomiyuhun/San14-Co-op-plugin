"""Real producer approvals and exact selected assets; never a native execution."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import contextlib,hashlib,io,json,shutil,sys,unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path.insert(0,str(HERE))
import b_portable_release_export as export
import portable_release as portable

OUTPUT=None;ROWS=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def spec():
    return dict(schema=export.SCHEMA,
        pair=dict(result=str(PRIVATE/'b_warm_refresh_pair_runs/20261009-215046-831686/result.json'),
                  sha256='2af0e06f5f0823450f3195be5feeae796f36cefc230e0fafa52b6dde0ea88a2d'),
        helper=dict(result=str(PRIVATE/'b_warm_coordinator_build_runs/20261009-181031-457801/result.json'),
                    sha256='4204df275c981b6c35c6bea01a25e040a0cea04be84e20ff2998079917e3b43a'),
        reward=dict(run=str(PRIVATE/'b_reward_owner_runs/20261010-095208-139540'),
                    sha256='028ce8040e91c1b3a1b8d27b4a1e55bbdbe22e728204dec0f717419884974478'),
        input=dict(run=str(PRIVATE/'player_input_lease_bootstrap_runs/20261010-101506-064151'),
                   sha256='55359a4455a267b98c59d247a10aefe4c6c479582329bdf6cef28c543d91fb2e'),
        rules=dict(stage=str(PRIVATE/'human_rules_activation_v2_runs/20261008-000431-509932/production.dll'),
                   publisher=str(PRIVATE/'human_rules_activation_publish_v2_runs/20261008-000527-938626/inputs/publisher-production.exe')))


class Cases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=spec();cls.selection=export.collect(cls.config)

    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir()

    def evidence(self,**extra):ROWS.append(dict(case=self._testMethodName,**extra))

    def test_real_producer_approvals_minimal_native_and_exact_source_subsets(self):
        selection=self.selection;metadata=selection['metadata'];assets=selection['assets']
        self.assertEqual(sum(x['role']=='native' for x in assets),7)
        self.assertEqual(sum(x['role']=='provenance' for x in assets),4)
        self.assertEqual(set(metadata['components']),{'pair','helper','reward','input','rules'})
        for name,count in [('pair',132),('helper',25),('reward',153),('input',15)]:
            c=metadata['components'][name];self.assertEqual(len(c['source_pins']),count)
            path=Path(self.config[name].get('result',str(Path(self.config[name].get('run',''))/'result.json')))
            old=json.loads(path.read_text());expected={}
            for source,h in old['sources'].items():
                p=Path(source);p=p if p.is_absolute() else HERE/p
                expected['repo/'+p.relative_to(ROOT).as_posix()]=h
            self.assertEqual(c['source_pins'],expected)
            self.assertTrue(c['producer_approval_verified']);self.assertFalse(c['recipient_native_execution_verified'])
        self.assertNotEqual(metadata['components']['pair']['source_pins'],metadata['source_pins'])
        forbidden={'.bin','.s14','.key','.pem','.pdb','.lib','.obj'}
        self.assertFalse([x['path'] for x in assets if Path(x['path']).suffix.lower() in forbidden])
        self.assertFalse([x['path'] for x in assets if Path(x['path']).name.lower() in ('steamclient64.dll','steam_api64.dll')])
        self.assertTrue(all(x['path'].startswith(('repo/','native/','provenance/')) for x in assets))
        self.assertFalse(metadata['install_permission']);self.assertTrue(metadata['producer_provenance_only'])
        self.evidence(asset_count=len(assets),source_count=len(metadata['source_pins']),native_count=7,provenance_count=4)

    def test_write_copy_new_absolute_root_and_preserve_original_record_bytes(self):
        producer=self.folder/'producer';relocated=self.folder/'other computer with spaces'
        made=portable.write_bundle(producer,self.selection['assets'],self.selection['metadata'])
        shutil.copytree(producer,relocated)
        release=portable.Release(relocated,made['manifest_sha256'])
        checked=[]
        for name,c in release.metadata['components'].items():
            if name=='rules':continue
            original=Path(self.config[name]['result']) if name in ('pair','helper') else Path(self.config[name]['run'])/'result.json'
            packaged=release.resolve(c['producer_provenance'])
            self.assertEqual(packaged.read_bytes(),original.read_bytes());checked.append(name)
            self.assertNotEqual(str(original),str(packaged))
        actual_read=Path.read_bytes
        def confined(path):
            self.assertTrue(path.resolve().is_relative_to(relocated.resolve()),'Recipient read producer path: '+str(path))
            return actual_read(path)
        with patch.object(Path,'read_bytes',confined):result=release.verify_all()
        self.assertEqual(result['result'],'PASS_RELEASE_FILES');self.assertFalse(result['native_permission'])
        self.evidence(bundle=made,relocated=str(relocated),unaltered_producer_provenance=checked,
                      recipient_legacy_approval_replayed=False,recipient_source_file_verification=result)

    def test_native_byte_change_rejected_after_relocation(self):
        made=portable.write_bundle(self.folder/'release',self.selection['assets'],self.selection['metadata'])
        release=portable.Release(made['root'],made['manifest_sha256'])
        p=release.resolve(release.metadata['components']['input']['production_dll'])
        raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        with self.assertRaisesRegex(ValueError,'asset changed'):portable.Release(made['root'],made['manifest_sha256'])
        self.evidence(tampered_file=str(p),changed_native_refused=True)

    def test_bad_receipt_hash_rejected_before_component_approval(self):
        c=deepcopy(self.config);c['pair']['sha256']='0'*64
        with patch.object(export,'approved_builds',side_effect=AssertionError('Must reject before approval')):
            with self.assertRaisesRegex(ValueError,'receipt identity'):export.collect(c)
        self.evidence(approval_invoked=False)

    def test_real_fixed_rules_approval_refuses_substituted_binary(self):
        c=deepcopy(self.config);bad=self.folder/'production.dll';bad.write_bytes(b'Not the approved native rules stage')
        c['rules']['stage']=str(bad)
        with self.assertRaisesRegex(ValueError,'rules build changed'):export.collect(c)
        self.evidence(actual_rules_check_rejected=True)

    def test_no_extra_private_source_or_unreviewed_dynamic_import(self):
        private=self.folder/'secret.py';private.write_text('secret = "owned only, never a credential"\n')
        with self.assertRaisesRegex(ValueError,'repository source'):export.python_closure([private])
        c=deepcopy(self.config);c['private_key']=str(private)
        with self.assertRaisesRegex(ValueError,'specification'):export.collect(c)
        # Parse the actual old script, do not import/execute its dynamic loader.
        with self.assertRaisesRegex(ValueError,'Unreviewed dynamic'):export.python_closure([HERE/'b_reload_bootstrap_queue_transform.py'])
        metadata=self.selection['metadata']
        self.assertIn('repo/work/mod_research/checkpoint-coverage-hex.py',metadata['runtime_sources'])
        self.assertEqual(metadata['external_dependencies']['modules'],['capstone','cryptography','pefile','unicorn'])
        self.evidence(explicit_dynamic_source=metadata['dynamic_sources'],external_dependencies=metadata['external_dependencies'])

    def test_help_does_not_read_approve_or_export(self):
        with patch.object(export,'collect',side_effect=AssertionError('No approval')), \
             patch.object(portable,'write_bundle',side_effect=AssertionError('No output')), \
             contextlib.redirect_stdout(io.StringIO()) as text:
            self.assertEqual(export.main([]),0)
        self.assertIn('--spec',text.getvalue());self.evidence(default_help_only=True)


def inputs(selection):
    sources={str(x['source']):x['sha256'] for x in selection['assets'] if x['role']=='source'}
    sources[str(Path(__file__).resolve())]=sha(__file__)
    for name in ('b_reload_bootstrap_queue_transform.py',):sources[str(HERE/name)]=sha(HERE/name)
    private={str(x['source']):x['sha256'] for x in selection['assets'] if x['role']!='source'}
    return sources,private


if __name__=='__main__':
    OUTPUT=PRIVATE/'b_portable_release_export_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    selected=export.collect(spec());before,private=inputs(selected);stream=io.StringIO()
    suite=unittest.TestSuite(Cases(n) for n in Cases.__dict__ if n.startswith('test_'))
    r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    unchanged=all(sha(n)==h for n,h in {**before,**private}.items())
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');print(stream.getvalue())
    result=dict(result='PASS' if r.wasSuccessful() and unchanged else 'FAIL',tests=r.testsRun,sources=before,
        private_inputs=private,sources_unchanged=unchanged,cases=ROWS,
        actual_original_build_approvals=True,actual_bundle_writer_and_relocation=True,
        game_access=False,steam_access=False,game_save_access=False,native_installed=False,
        local_native_approval_replayed=False,external_python_dependencies_bundled=False,
        failures=[(str(t),s) for t,s in r.failures+r.errors])
    result['artifacts']={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    path=OUTPUT/'result.json';path.write_text(json.dumps(result,indent=2)+'\n');print(path);raise SystemExit(result['result']!='PASS')
