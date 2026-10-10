"""Release transport/relocation checks only; no game or native execution."""
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import shutil
import unittest
import zipfile
import portable_release as release

HERE=Path(__file__).resolve().parent
PRIVATE=HERE.parents[2]/'mod_research'
OUTPUT=None


class Cases(unittest.TestCase):
    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir()
        self.source=self.folder/'source.py';self.source.write_bytes(b'# owned release test\n')
        self.asset=dict(source=self.source,path='repo/work/mod_research/owned.py',sha256=release.sha(self.source.read_bytes()),role='source')

    def make(self):
        self.record=release.write_bundle(self.folder/'export',[self.asset],dict(kind='owned-test',local_game_verified=False))
        return release.Release(self.record['root'],self.record['manifest_sha256'])

    def test_moved_package_never_depends_on_producer_source_path(self):
        original=self.make();moved=self.folder/'另一目录'/'远端副本'
        shutil.copytree(original.root,moved)
        self.source.rename(self.folder/'producer-unavailable.py')
        other=release.Release(moved,self.record['manifest_sha256'])
        self.assertEqual(other.resolve(self.asset['path']).read_bytes(),b'# owned release test\n')
        metadata=other.metadata;metadata['local_game_verified']=True
        self.assertFalse(other.metadata['local_game_verified'])

    def test_tampered_asset_and_manifest_rejected(self):
        bundle=self.make()
        bundle.resolve(self.asset['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):bundle.verify_all()
        (bundle.root/'release.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):release.Release(bundle.root,self.record['manifest_sha256'])

    def test_missing_asset_rejected(self):
        bundle=self.make();bundle.resolve(self.asset['path']).rename(self.folder/'removed-source.py')
        with self.assertRaises((ValueError,FileNotFoundError)):bundle.verify_all()

    def test_unlisted_import_file_rejected_but_local_records_separate(self):
        bundle=self.make()
        (bundle.root/'mod_research').mkdir()
        (bundle.root/'mod_research'/'local-record.json').write_text('{}')
        bundle.verify_all()
        (bundle.root/'repo'/'injected.py').write_text('')
        with self.assertRaises(ValueError):bundle.verify_all()

    def test_windows_path_escapes_reserved_names_and_collisions_rejected(self):
        for name in ('../bad','/abs/file','repo/../bad','repo/C:bad','repo/a\\b','repo/NUL.txt','repo/a.','repo/a//b','release.json'):
            with self.subTest(name=name),self.assertRaises(ValueError):release.relative(name)
        second={**self.asset,'path':self.asset['path'].upper()}
        with self.assertRaises(ValueError):release.write_bundle(self.folder/'bad',[self.asset,second],{})

    def test_archive_contains_only_verified_files_and_can_relocate(self):
        bundle=self.make();target=self.folder/'release.zip'
        result=release.archive(bundle,target)
        self.assertEqual(result['sha256'],release.sha(target.read_bytes()))
        moved=self.folder/'unpacked'
        with zipfile.ZipFile(target) as packed:
            self.assertEqual(set(packed.namelist()),{'release.json',self.asset['path']})
            packed.extractall(moved)
        release.Release(moved,self.record['manifest_sha256'])
        with self.assertRaises(ValueError):release.archive(bundle,target)

    def test_export_drift_refuses_completed_manifest(self):
        self.source.write_text('drift')
        destination=self.folder/'bad'
        with self.assertRaises(ValueError):release.write_bundle(destination,[self.asset],{})
        self.assertFalse((destination/'release.json').exists())

    def test_explicit_digest_and_duplicate_json_keys_required(self):
        bundle=self.make()
        for digest in (None,'','f'*64):
            with self.subTest(digest=digest),self.assertRaises(ValueError):release.Release(bundle.root,digest)
        with self.assertRaises(ValueError):release.strict_json(b'{"schema":1,"schema":2}')


if __name__=='__main__':
    OUTPUT=PRIVATE/'portable_release_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    sources={str(HERE/n):release.sha((HERE/n).read_bytes()) for n in ('portable_release.py','portable_release_test.py')}
    record=dict(result='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,sources=sources,game_access=False,native_execution=False)
    (OUTPUT/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(OUTPUT);raise SystemExit(not result.wasSuccessful())
