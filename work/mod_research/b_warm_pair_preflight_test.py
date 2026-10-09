"""Read-only preflight on owned files; actual archived build approval reused.

Temporary Steam-named bytes replace only the immutable hash allowlist in these
tests. No actual Steam path, game PID, process reader, claim or native start.
"""
import ast
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_warm_pair_preflight as entry
import b_warm_coordinator as coordinator
import b_warm_start as start
import b_warm_staging as files

OUTPUT=None;EVIDENCE=[]
HELPER=PRIVATE/'b_warm_coordinator_build_runs/20261009-181031-457801/result.json'
PAIR=PRIVATE/'b_warm_factory_pair_runs/20261009-181448-912475/result.json'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Cases(unittest.TestCase):
    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir()
        self.target=self.folder/files.NAME;self.second=self.folder/'received-second.s14'
        self.target.write_bytes(b'explicit owned first archive model'*100)
        self.second.write_bytes(b'explicit owned second archive model'*101)
        steam={}
        for name in entry.STEAM_HASHES:
            p=self.folder/name;p.write_bytes(('owned DLL bytes '+name).encode()*100);steam[name]=str(p)
        def profile(path,before,loaded,current):
            return dict(file=dict(name=files.NAME,slot=63,size=path.stat().st_size,sha256=sha(path)),
                before=dict(year=203,month=8,day=before),loaded=dict(year=203,month=8,day=loaded),
                source=dict(ruler=666,force=12,district=11),target=dict(ruler=952,force=2,district=2),currentForce=current)
        self.plan=dict(profiles=[profile(self.target,11,11,12),profile(self.second,11,21,2)],
            target=str(self.target),second_source=str(self.second),expected_ruler=666,steam_paths=steam)
        self.planpath=self.folder/'plan.json';self.planpath.write_text(json.dumps(self.plan))
        self.fake_hashes={n:sha(p) for n,p in steam.items()}
        self.args=dict(helper_build=HELPER,helper_sha256=sha(HELPER),pair_build=PAIR,pair_sha256=sha(PAIR))

    def run_check(self,**overrides):
        with patch.object(entry,'STEAM_HASHES',self.fake_hashes), \
             patch.object(coordinator,'Resident',side_effect=AssertionError('No process owner may be constructed')) as resident, \
             patch.object(start,'refuse_prior_attempt',side_effect=AssertionError('No process claim scan here')) as claim, \
             patch.object(files,'apply',side_effect=AssertionError('No staging writes here')) as stage:
            result=entry.preflight(self.planpath,**{**self.args,**overrides})
            resident.assert_not_called();claim.assert_not_called();stage.assert_not_called();return result

    def test_valid_files_real_approved_builds_no_mutation(self):
        before={str(p):sha(p) for p in self.folder.rglob('*') if p.is_file()}
        r=self.run_check()
        self.assertEqual(r['normalized_plan'],self.plan);self.assertTrue(r['no_execute_authority']);self.assertTrue(r['game_checks_pending'])
        self.assertFalse(r['game_access']);self.assertFalse(r['claims_created']);self.assertFalse(r['native_load_permitted'])
        self.assertEqual(before,{str(p):sha(p) for p in self.folder.rglob('*') if p.is_file()})
        EVIDENCE.append(dict(case='real-component-closure',result=r,steam_files='EXPLICIT_TEMP_HASH_ALLOWLIST'))

    def test_missing_or_changed_first_file_refuses_before_build_or_process(self):
        self.target.write_bytes(b'changed first')
        for missing in (False,True):
            if missing:self.target.unlink()
            before={str(p):sha(p) for p in self.folder.rglob('*') if p.is_file()}
            with patch.object(entry,'approved_component',side_effect=AssertionError('Must reject file before build checks')) as approve:
                with self.assertRaises((ValueError,OSError)):self.run_check()
                approve.assert_not_called()
            self.assertEqual(before,{str(p):sha(p) for p in self.folder.rglob('*') if p.is_file()})
        EVIDENCE.append(dict(case='first-missing-or-mismatch',process_calls=0,build_callbacks=0,files_written=False))

    def test_second_file_and_steam_hash_are_strict(self):
        original=self.second.read_bytes();self.second.write_bytes(original+b'drift')
        with self.assertRaisesRegex(ValueError,'Second source'):self.run_check()
        self.second.write_bytes(original)
        steam=Path(self.plan['steam_paths']['steamclient64.dll']);steam.write_bytes(b'unapproved temp DLL')
        with self.assertRaisesRegex(ValueError,'Unapproved Steam'):self.run_check()
        EVIDENCE.append(dict(case='second-or-Steam-drift',process_calls=0))

    def test_bad_plan_and_build_hash_refuse(self):
        self.plan['profiles'][1]['before']['day']=21;self.planpath.write_text(json.dumps(self.plan))
        with self.assertRaisesRegex(ValueError,'Second current world'):self.run_check()
        self.plan['profiles'][1]['before']['day']=11;self.planpath.write_text(json.dumps(self.plan))
        with self.assertRaisesRegex(ValueError,'Component result identity'):self.run_check(helper_sha256='0'*64)
        EVIDENCE.append(dict(case='bad-date-or-build-hash',process_calls=0))

    def test_default_help_and_import_have_no_process_capability(self):
        tree=ast.parse((HERE/'b_warm_start_support.py').read_text())
        source_hashes=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and
            any(isinstance(t,ast.Name) and t.id=='STEAM_HASHES' for t in n.targets))
        self.assertEqual(entry.STEAM_HASHES,source_hashes)
        run=subprocess.run([sys.executable,str(HERE/'b_warm_pair_preflight.py')],capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stderr);self.assertIn('--plan',run.stdout)
        code="import sys;sys.path.insert(0,sys.argv[1]);import b_warm_pair_preflight;print([n for n in ('game_reader','run_autonomous_pilot','checkpoint_complete_live_capture','b_warm_start_support') if n in sys.modules])"
        check=subprocess.run([sys.executable,'-c',code,str(HERE)],capture_output=True,text=True,timeout=20)
        self.assertEqual(check.returncode,0,check.stderr);self.assertEqual(check.stdout.strip(),'[]')
        EVIDENCE.append(dict(case='default-and-import',process_capability_modules=[],steam_hash_parity=True))


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.update((Path(__file__).resolve(),HERE/'b_warm_start_support.py'))
    return {str(p):sha(p) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    OUTPUT=PRIVATE/'b_warm_pair_preflight_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    before=pins();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins();stable=all(sources.get(k)==v for k,v in before.items())
    report=dict(result='PASS' if result.wasSuccessful() and result.testsRun==5 and stable else 'FAIL',tests=result.testsRun,
        sources=sources,inputs_unchanged=stable,cases=EVIDENCE,game_access=False,actual_steam_access=False,
        private={str(p):sha(p) for p in (HELPER,PAIR)},failures=[(str(t),d) for t,d in result.failures+result.errors])
    report['artifacts']={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(0 if report['result']=='PASS' else 1)
