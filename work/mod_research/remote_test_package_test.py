"""Build actual tools package and run relocated help/verify without game access."""
from contextlib import redirect_stdout
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import zipfile

import remote_test_package as package
import remote_test_tools as entry
from b_portable_release_export_test import spec
from portable_release import Release

HERE = Path(__file__).resolve().parent
PRIVATE = HERE.parents[2]/'mod_research'
OUTPUT = None
MADE = None


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Cases(unittest.TestCase):
    def test_default_help_is_inert(self):
        with redirect_stdout(io.StringIO()), patch.object(entry, 'Release', side_effect=AssertionError('no files')):
            self.assertEqual(entry.main([]), 0)
        with redirect_stdout(io.StringIO()), patch.object(package, 'assemble', side_effect=AssertionError('no build')):
            self.assertEqual(package.main([]), 0)

    def test_actual_archive_moved_and_preparation_commands(self):
        root = OUTPUT/'另一台电脑 moved tools'; root.mkdir()
        with zipfile.ZipFile(MADE['archive']['path']) as archive:
            archive.extractall(root)
        release = Release(root, MADE['manifest_sha256'])
        tools = release.resolve('repo/work/mod_research/remote_test_tools.py')
        state = OUTPUT/'empty-localappdata'; state.mkdir()
        code = '''import sys,runpy
from pathlib import Path
script=Path(sys.argv[1]);sys.path.insert(0,str(script.parent));sys.argv=sys.argv[1:]
runpy.run_path(str(script),run_name='__main__')
'''
        for index, arguments in enumerate((['--tool', 'keys', '--', '--help'],
                                           ['--tool', 'network', '--', '--help'],
                                           ['--tool', 'prepare-b', '--', '--template'],
                                           ['--tool', 'environment', '--', '--role', 'B'])):
            result = subprocess.run([sys.executable, '-I', '-S', '-B', '-X', 'utf8', '-c', code, str(tools),
                                     '--release-root', str(root), '--release-sha256', MADE['manifest_sha256'],
                                     *arguments], capture_output=True, text=True, encoding='utf-8', timeout=40,
                                    env=dict(os.environ, LOCALAPPDATA=str(state)), cwd=root)
            (OUTPUT/('command-%d.stdout'%index)).write_text(result.stdout, encoding='utf-8')
            (OUTPUT/('command-%d.stderr'%index)).write_text(result.stderr, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stdout+'\n'+result.stderr)
        self.assertEqual(list(state.rglob('*')), [])
        release.verify_all()

    def test_selected_launcher_must_belong_to_release(self):
        # This test source is the producer checkout, not the packaged entry.
        with self.assertRaisesRegex(ValueError, 'selected release'):
            entry.main(['--release-root', str(MADE['root']), '--release-sha256', MADE['manifest_sha256'],
                        '--tool', 'keys', '--', '--help'])

    def test_existing_package_refused_before_collector(self):
        with patch.object(package.collector, 'collect', side_effect=AssertionError('must not run')):
            with self.assertRaisesRegex(ValueError, 'Fresh'):
                package.assemble(spec(), destination=MADE['root'], zip_path=OUTPUT/'new.zip')

    def test_packaged_tools_actual_two_path_network_check(self):
        import remote_link_probe as probe
        root = OUTPUT/'network recipient'; root.mkdir()
        with zipfile.ZipFile(MADE['archive']['path']) as archive: archive.extractall(root)
        owner = probe.serve(bind='127.0.0.1', advertise='127.0.0.1', control_port=0, download_port=0,
                            output=OUTPUT/'owned probe', lifetime=90, timeout=2)
        state = OUTPUT/'network-localappdata'; state.mkdir()
        script = root/'repo/work/mod_research/remote_test_tools.py'
        code = '''import sys,runpy
from pathlib import Path
script=Path(sys.argv[1]);sys.path.insert(0,str(script.parent));sys.argv=sys.argv[1:]
runpy.run_path(str(script),run_name='__main__')
'''
        try:
            args = [sys.executable, '-I', '-S', '-B', '-X', 'utf8', '-c', code, str(script),
                    '--release-root', str(root), '--release-sha256', MADE['manifest_sha256'],
                    '--tool', 'network', '--', 'check', '--invite', str(owner.folder/'invite.json')]
            result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', timeout=40,
                                    cwd=root, env=dict(os.environ, LOCALAPPDATA=str(state)))
            self.assertEqual(result.returncode, 0, result.stdout+'\n'+result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['result'], 'PASS_NETWORK_BOTH_PATHS')
            self.assertFalse(report['room_joined']); self.assertFalse(report['two_games'])
            (OUTPUT/'packaged-network-check.json').write_text(json.dumps(report, indent=2)+'\n')
            self.assertEqual(list(state.rglob('*')), [])
        finally: owner.close()
        self.assertTrue(json.loads((owner.folder/'host-report.json').read_text())['cleanup_complete'])
        Release(root, MADE['manifest_sha256']).verify_all()


if __name__ == '__main__':
    OUTPUT = PRIVATE/'remote_test_package_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f'); OUTPUT.mkdir(parents=True)
    selected = package.collector.collect(spec(), extra_sources=[HERE/'remote_test_tools.py', HERE/'b_portable_approval.py'])
    deps = package.collect_dependencies(); sources = {}; private = {}
    for asset in selected['assets']+deps['assets']:
        (sources if asset['role'] == 'source' else private)[str(asset['source'])] = asset['sha256']
    for name in ('remote_test_package.py', 'remote_test_package_test.py'):
        sources[str(HERE/name)] = sha(HERE/name)
    MADE = package.assemble(spec(), destination=OUTPUT/'runtime', zip_path=OUTPUT/'SAN14-Remote-Test.zip')
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(), encoding='utf-8')
    stable = all(sha(p) == h for p, h in {**sources, **private}.items())
    report = dict(result='PASS' if result.wasSuccessful() and stable else 'FAIL', tests=result.testsRun,
                  sources=sources, private_inputs=private, inputs_unchanged=stable, package=MADE,
                  game_access=False, network_opened=True, loopback_only=True, native_installed=False,
                  artifacts={str(p): sha(p) for p in OUTPUT.rglob('*') if p.is_file()})
    (OUTPUT/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(stream.getvalue()); print(OUTPUT/'result.json'); raise SystemExit(report['result'] != 'PASS')
