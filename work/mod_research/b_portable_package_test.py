"""Pinned dependency and real archive composition checks, no native execution."""
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import argparse,contextlib,hashlib,io,json,os,shutil,subprocess,sys,unittest,zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
import b_portable_package as package
from b_portable_release_export_test import spec
from portable_release import Release

OUTPUT=None;ROWS=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Cases(unittest.TestCase):
    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir()
    def evidence(self,**extra):ROWS.append(dict(case=self._testMethodName,**extra))
    def copy_deps(self):
        selection=package.collect_dependencies();root=self.folder/'python libraries';root.mkdir()
        for asset in selection['assets']:
            p=root/Path(asset['path']).relative_to('deps');p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(asset['source'],p)
        return root

    def test_exact_real_record_files_license_and_no_compiled_caches(self):
        value=package.collect_dependencies();paths={x['path'] for x in value['assets']}
        self.assertEqual(len(paths),13);self.assertEqual(paths,{'deps/'+n for n in package.EXPECTED})
        self.assertTrue(all(x['role']=='dependency' for x in value['assets']))
        self.assertFalse(any('__pycache__' in p or p.endswith('.pyc') for p in paths))
        self.assertEqual(value['metadata']['producer_record_sha256'],package.RECORD_SHA)
        self.evidence(metadata=value['metadata'],files=sorted(paths))

    def test_surprise_keys_and_other_distributions_never_selected(self):
        root=self.copy_deps();(root/'private.key').write_text('not a real secret')
        for name in ('capstone','unicorn','cryptography'):
            p=root/name;p.mkdir();(p/'__init__.py').write_text('raise AssertionError("must not be imported")')
        (root/'ordlookup'/'extra.py').write_text('not exported')
        value=package.collect_dependencies(root)
        self.assertEqual({x['path'] for x in value['assets']},{'deps/'+n for n in package.EXPECTED})
        self.evidence(selected_count=len(value['assets']),unexpected_adjacent_files_copied=False)

    def test_record_tamper_and_missing_dependency_rejected(self):
        root=self.copy_deps();record=root/package.DIST/'RECORD';original=record.read_bytes()
        record.write_bytes(original+b'private.key,,\n')
        with self.assertRaisesRegex(ValueError,'distribution RECORD'):package.collect_dependencies(root)
        record.write_bytes(original);missing=root/'ordlookup/ws2_32.py';missing.rename(root/'withheld.py')
        with self.assertRaises(FileNotFoundError):package.collect_dependencies(root)
        self.evidence(record_tamper_rejected=True,missing_dependency_rejected=True)

    def test_dependency_bytes_must_match_original_record(self):
        root=self.copy_deps();p=root/'pefile.py';raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        with self.assertRaisesRegex(ValueError,'bytes differ'):package.collect_dependencies(root)
        self.evidence(changed_python_dependency_rejected=True)

    def test_isolated_relocated_pefile_ordlookup_and_peutils_import(self):
        root=self.copy_deps()
        code='''import sys,json,pathlib
sys.path.insert(0,sys.argv[1])
import pefile,peutils,ordlookup,ordlookup.oleaut32,ordlookup.ws2_32,ordlookup.wsock32
root=pathlib.Path(sys.argv[1]).resolve()
names=('pefile','peutils','ordlookup','ordlookup.oleaut32','ordlookup.ws2_32','ordlookup.wsock32')
assert all(pathlib.Path(sys.modules[n].__file__).resolve().is_relative_to(root) for n in names)
assert not any(n in sys.modules for n in ('capstone','unicorn','cryptography'))
print(json.dumps(dict(imported=list(names),version=pefile.__version__,native_executed=False)))
'''
        child=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(root)],capture_output=True,text=True,timeout=15,cwd=self.folder)
        self.assertEqual(child.returncode,0,child.stderr);row=json.loads(child.stdout)
        self.assertEqual(row['version'],'2024.8.26');self.assertFalse(list(root.rglob('*.pyc')))
        self.evidence(isolated_child=row,only_bundled_dependencies=True)

    def test_default_help_and_existing_outputs_no_approval(self):
        with patch.object(package,'assemble',side_effect=AssertionError('No package')), \
             contextlib.redirect_stdout(io.StringIO()) as text:
            self.assertEqual(package.main([]),0)
        self.assertIn('--zip',text.getvalue())
        old=self.folder/'existing.zip';old.write_bytes(b'Owned previous output')
        with patch.object(package.collector,'collect',side_effect=AssertionError('No build approval')):
            with self.assertRaisesRegex(ValueError,'both be fresh'):package.assemble(spec(),destination=self.folder/'new',zip_path=old)
        self.assertEqual(old.read_bytes(),b'Owned previous output');self.evidence(old_output_unchanged=True)

    def test_full_archive_relocation_and_actual_guest_verify(self):
        made=package.assemble(spec(),destination=self.folder/'producer package',zip_path=self.folder/'B-portable.zip')
        destination=self.folder/'another computer'/'runtime';destination.mkdir(parents=True)
        with zipfile.ZipFile(made['archive']['path']) as archive:
            names=archive.namelist();self.assertEqual(len(names),len(set(names)))
            self.assertEqual(len(names),made['file_count']+1)
            self.assertFalse(any('__pycache__' in n or Path(n).suffix in ('.key','.pem','.s14','.bin','.pyc') for n in names))
            archive.extractall(destination)
        release=Release(destination,made['manifest_sha256']);guest=release.resolve('repo/work/mod_research/b_portable_guest.py')
        state=self.folder/'empty localappdata';state.mkdir()
        code='''import runpy,sys
from pathlib import Path
guest=Path(sys.argv[1]);sys.path.insert(0,str(guest.parent));sys.argv=sys.argv[1:]
runpy.run_path(str(guest),run_name='__main__')
'''
        env=dict(os.environ,LOCALAPPDATA=str(state))
        args=[sys.executable,'-I','-S','-B','-X','utf8','-c',code,str(guest),'--verify','--release-root',str(destination),'--release-sha256',made['manifest_sha256']]
        child=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=30,cwd=self.folder,env=env)
        (self.folder/'recipient.stdout').write_text(child.stdout,encoding='utf-8');(self.folder/'recipient.stderr').write_text(child.stderr,encoding='utf-8')
        self.assertEqual(child.returncode,0,child.stdout+'\n'+child.stderr)
        verified=json.loads(child.stdout);self.assertEqual(verified['result'],'PASS_PORTABLE_FILES')
        self.assertFalse(verified['game_access']);self.assertFalse(verified['recipient_native_execution_verified'])
        self.assertFalse(list(state.rglob('*')));release.verify_all()
        self.evidence(package=made,relocated=str(destination),actual_guest_files_verify=verified,local_native_execution=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dependencies-only',action='store_true');args=parser.parse_args()
    OUTPUT=PRIVATE/'b_portable_package_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    deps=package.collect_dependencies();sources={str(HERE/n):sha(HERE/n) for n in (
        'b_portable_package.py','b_portable_package_test.py','b_portable_release_export.py','b_portable_release_export_test.py','portable_release.py')}
    private={str(a['source']):a['sha256'] for a in deps['assets']}
    if not args.dependencies_only:
        selection=package.collector.collect(spec(),extra_sources=[HERE/'b_portable_guest.py',HERE/'b_portable_approval.py'])
        for a in selection['assets']:(sources if a['role']=='source' else private)[str(a['source'])]=a['sha256']
    names=[n for n in Cases.__dict__ if n.startswith('test_') and (not args.dependencies_only or n!='test_full_archive_relocation_and_actual_guest_verify')]
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(Cases(n) for n in names))
    unchanged=all(sha(p)==h for p,h in {**sources,**private}.items());(OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');print(stream.getvalue())
    result=dict(result='PASS' if r.wasSuccessful() and unchanged else 'FAIL',tests=r.testsRun,sources=sources,private_inputs=private,
        inputs_unchanged=unchanged,dependency_only=args.dependencies_only,cases=ROWS,
        game_access=False,steam_access=False,native_executed=False,claims_created=False,
        failures=[(str(t),s) for t,s in r.failures+r.errors])
    result['artifacts']={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    p=OUTPUT/'result.json';p.write_text(json.dumps(result,indent=2)+'\n');print(p);raise SystemExit(result['result']!='PASS')
