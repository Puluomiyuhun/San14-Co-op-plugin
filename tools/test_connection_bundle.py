"""Portable public-source diagnostic tests; actual loopback TLS, no game."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
import zipfile
from contextlib import redirect_stdout
import io

import prepare_connection_check as builder

ROOT = Path(__file__).resolve().parents[1]
RUN = None
EVIDENCE = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.folder = RUN / self._testMethodName
        self.folder.mkdir()
        self.bundle = self.folder / 'package with spaces'
        self.manifest = builder.prepare(self.bundle)

    def run_cli(self, *args, package=None):
        package = package or self.bundle
        result = subprocess.run([sys.executable, '-I', str(package / 'run.py'), *args],
            cwd=self.folder, capture_output=True, timeout=15, text=True, encoding='utf-8',
            errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return result

    def test_allowlisted_bundle_has_no_private_inputs(self):
        names = set(p.name for p in self.bundle.iterdir())
        self.assertEqual(names, set(self.manifest['files']) | {'bundle.json'})
        self.assertEqual(len(names), 10)
        result = self.run_cli('check')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['game_version']['status'], 'NOT_CONFIGURED')
        self.assertFalse(report['native_backend_connected'])
        self.assertFalse((self.bundle / 'private-runs').exists())

    def test_source_change_rejected_before_protocol_import_or_listener(self):
        (self.bundle / 'room_transport.py').write_text('raise RuntimeError("MUST_NOT_IMPORT")\n')
        result = self.run_cli('host', '--bind', '127.0.0.1', '--port', '0', '--timeout', '10')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Bundle file missing or changed', result.stdout)
        self.assertNotIn('MUST_NOT_IMPORT', result.stdout + result.stderr)
        self.assertFalse((self.bundle / 'private-runs').exists())

    def test_local_config_create_is_non_overwriting(self):
        result = self.run_cli('init')
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.bundle / 'local-config.json'
        before = config.read_bytes()
        result = self.run_cli('init')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(config.read_bytes(), before)
        self.assertEqual(self.run_cli('check').returncode, 0)

    def test_explicit_wrong_game_version_refuses_before_network(self):
        fake = self.folder / 'not a game.exe'
        fake.write_bytes(b'own diagnostic fixture, never executed')
        before = sha(fake)
        self.assertEqual(self.run_cli('init', '--game-exe', str(fake)).returncode, 0)
        result = self.run_cli('host', '--bind', '127.0.0.1', '--port', '0')
        self.assertEqual(result.returncode, 1)
        value = json.loads(result.stdout)
        self.assertEqual(value['game_version']['status'], 'MISMATCH')
        self.assertFalse(value['game_process_access'])
        self.assertEqual(sha(fake), before)
        self.assertFalse((self.bundle / 'private-runs').exists())

    def test_unsupported_address_and_duplicate_config_refused(self):
        for ip in ('0.0.0.0', '8.8.8.8', '::1'):
            result = self.run_cli('host', '--bind', ip, '--port', '0', '--timeout', '10')
            self.assertEqual(result.returncode, 1)
        (self.bundle / 'local-config.json').write_text('{"schema":"x","schema":"y"}')
        result = self.run_cli('check')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Duplicate JSON field', result.stdout)
        self.assertFalse((self.bundle / 'private-runs').exists())

    def test_existing_bundle_is_never_overwritten(self):
        before = {p.name: sha(p) for p in self.bundle.iterdir()}
        with self.assertRaises(FileExistsError):
            builder.prepare(self.bundle)
        self.assertEqual(before, {p.name: sha(p) for p in self.bundle.iterdir()})

    def test_concurrent_extra_file_is_excluded_from_manifest_and_zip(self):
        output = self.folder / 'new raced package'
        archive = self.folder / 'allowlist.zip'
        actual_copy = shutil.copyfile
        def copy_with_extra(source, target):
            result = actual_copy(source, target)
            (Path(target).parent / 'unexpected-private.key').write_bytes(b'private diagnostic fixture')
            return result
        with patch.object(builder.shutil, 'copyfile', side_effect=copy_with_extra), \
             patch.object(sys, 'argv', ['prepare', '--output', str(output), '--zip', str(archive)]), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(builder.main(), 0)
        manifest = json.loads((output / 'bundle.json').read_bytes())
        self.assertNotIn('unexpected-private.key', manifest['files'])
        with zipfile.ZipFile(archive) as zipped:
            self.assertEqual(set(zipped.namelist()),
                {'SAN14-Connection-Check/' + n for n in (*manifest['files'], 'bundle.json')})
            self.assertEqual(len(zipped.namelist()), 10)

    def test_relocated_independent_processes_tls_and_wrong_pin(self):
        guest_bundle = self.folder / 'guest relocated'
        shutil.copytree(self.bundle, guest_bundle)
        logs = [(self.folder / (name + '.log')).open('wb') for name in ('host', 'guest')]
        host = guest = None
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        # No repository paths in PYTHONPATH. Isolated mode additionally ignores
        # user site and PYTHON* variables; entry establishes only its own path.
        env = dict(os.environ, PYTHONPATH='', PYTHONHOME='')
        try:
            host = subprocess.Popen([sys.executable, '-I', str(self.bundle / 'run.py'), 'host',
                '--bind', '127.0.0.1', '--port', '0', '--timeout', '20', '--sample-kib', '129'],
                cwd=self.folder, stdout=logs[0], stderr=subprocess.STDOUT, env=env, creationflags=flags)
            deadline = time.monotonic() + 8
            invites = []
            while time.monotonic() < deadline:
                invites = list((self.bundle / 'private-runs').glob('host-*/invite.json'))
                if invites or host.poll() is not None:
                    break
                time.sleep(.03)
            self.assertTrue(invites, 'Host failed before producing invitation; see host.log')
            invite = json.loads(invites[0].read_bytes())
            bad = dict(invite, fingerprint='0' * 64)
            badpath = self.folder / 'wrong-pin-invite.json'
            badpath.write_text(json.dumps(bad))
            result = self.run_cli('guest', '--invite', str(badpath), '--timeout', '10', package=guest_bundle)
            self.assertEqual(result.returncode, 1)
            # An invitation from another source build is rejected before joining.
            other = dict(invite, profile=dict(invite['profile'], rules_sha256='0' * 64))
            badpath.write_text(json.dumps(other))
            result = self.run_cli('guest', '--invite', str(badpath), '--timeout', '10', package=guest_bundle)
            self.assertEqual(result.returncode, 1)
            self.assertIn('different tool build', result.stdout)
            guest = subprocess.Popen([sys.executable, '-I', str(guest_bundle / 'run.py'), 'guest',
                '--invite', str(invites[0]), '--timeout', '15'], cwd=self.folder,
                stdout=logs[1], stderr=subprocess.STDOUT, env=env, creationflags=flags)
            self.assertEqual(guest.wait(18), 0)
            self.assertEqual(host.wait(5), 0)
            reports = [json.loads(p.read_bytes()) for folder in (self.bundle, guest_bundle)
                       for p in (folder / 'private-runs').glob('*/report.json')]
            self.assertEqual(len(reports), 2)
            a = next(x for x in reports if x['role'] == 'A')
            b = next(x for x in reports if x['role'] == 'B')
            self.assertEqual(b['payload_bytes'], 129 * 1024)
            self.assertEqual(a['guest_report']['payload_sha256'], b['payload_sha256'])
            for report in reports:
                self.assertEqual(report['result'], 'NETWORK_BYTES_PASS_WAITING_NATIVE_BACKEND')
                self.assertFalse(report['native_backend_connected'])
                self.assertFalse(report['two_computers_proven'])
            EVIDENCE.append(dict(case='RELOCATED_TWO_PROCESS_TLS', bytes=b['payload_bytes'],
                bytes_verified=True, wrong_pin_rejected=True, wrong_build_rejected=True,
                actual_two_computers=False, native_backend_connected=False))
        finally:
            for process in (guest, host):
                if process and process.poll() is None:
                    process.terminate()
                    process.wait(5)
            for log in logs:
                log.close()


def main():
    global RUN
    RUN = ROOT / '.local' / 'connection-check-tests' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    RUN.mkdir(parents=True)
    sources = [ROOT / p for p in builder.SOURCES.values()] + [Path(__file__), ROOT / 'tools/prepare_connection_check.py']
    before = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in sources}
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BundleTests)
    methods = [x.id().split('.', 1)[-1] for x in suite]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    unchanged = all(sha(ROOT / p) == h for p, h in before.items())
    report = dict(schema='san14.connection-bundle-tests.v1',
        result='PASS' if result.wasSuccessful() and unchanged else 'FAIL', tests_run=result.testsRun,
        errors=len(result.errors), failures=len(result.failures), skipped=len(result.skipped),
        test_methods=methods, sources_sha256=before, sources_unchanged=unchanged, cases=EVIDENCE,
        game_process_access=False, native_backend_connected=False, actual_two_computers=False,
        network_configuration_changed=False)
    path = RUN / 'result.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(result=report['result'], path=str(path))))
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
