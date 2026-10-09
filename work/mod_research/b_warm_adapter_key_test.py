"""Actual Windows temporary files/ACLs and CLI checks; no game/network access."""
from datetime import datetime
from pathlib import Path
import hashlib
import io
import json
import os
import secrets
import subprocess
import sys
import unittest

import b_warm_adapter_key as keyfile

HERE = Path(__file__).resolve().parent
PRIVATE = HERE.parents[2] / 'mod_research'
OUTPUT = PRIVATE / 'b_warm_adapter_key_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
OUTPUT.mkdir(parents=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Cases(unittest.TestCase):
    def setUp(self):
        self.folder = OUTPUT / self._testMethodName
        self.folder.mkdir()

    def test_create_load_status_export_and_exclusive_target(self):
        a = self.folder / 'a.key'; b = self.folder / 'b.key'
        report = keyfile.create(a); key = keyfile.load_key(a)
        self.assertEqual(len(key), 32)
        self.assertEqual(report, keyfile.status(a))
        self.assertEqual(keyfile.export_file(a, b), report)
        self.assertTrue(secrets.compare_digest(keyfile.load_key(b), key))
        before = a.read_bytes()
        with self.assertRaises(keyfile.KeyFileError): keyfile.create(a)
        with self.assertRaises(keyfile.KeyFileError): keyfile.export_file(b, a)
        self.assertTrue(secrets.compare_digest(a.read_bytes(), before))
        self.assertTrue(key.hex() not in json.dumps(report), 'Secret leaked in status')

    def test_malformed_encoding_exact_length_and_zero_refused(self):
        raw = keyfile.encode(secrets.token_bytes(32))
        invalid = [raw + b'\n', raw[:-1], raw.replace(b'\n', b'\r\n'), raw[:-65] + b'0'*64+b'\n',
                   raw[:-65]+b'G'*64+b'\n', raw[:-65]+b'A'*64+b'\n', b'\xef\xbb\xbf'+raw]
        for i, body in enumerate(invalid):
            p = self.folder / ('bad%d.key' % i); p.write_bytes(body)
            with self.assertRaises(keyfile.KeyFileError): keyfile.import_file(p, self.folder / ('out%d.key' % i))
            self.assertFalse((self.folder / ('out%d.key' % i)).exists())

    def test_explicit_import_reprotects_broad_transferred_file(self):
        key = secrets.token_bytes(32); source = self.folder / 'transfer.key'; source.write_bytes(keyfile.encode(key))
        with self.assertRaises(keyfile.KeyFileError): keyfile.load_key(source)
        target = self.folder / 'private.key'
        self.assertEqual(keyfile.import_file(source, target), keyfile.public(key))
        self.assertTrue(secrets.compare_digest(keyfile.load_key(target), key))
        self.assertTrue(secrets.compare_digest(source.read_bytes(), keyfile.encode(key)))

    def test_directory_hardlink_and_nonlocal_paths_refused(self):
        a = self.folder / 'a.key'; keyfile.create(a); link = self.folder / 'link.key'
        os.link(a, link)
        with self.assertRaises(keyfile.KeyFileError): keyfile.load_key(a)
        with self.assertRaises(keyfile.KeyFileError): keyfile.load_key(link)
        with self.assertRaises(keyfile.KeyFileError): keyfile.status(self.folder)
        for path in ('relative.key', r'\\server\share\key', str(a)+':stream', str(self.folder/'CON'), str(self.folder/'bad.')):
            with self.assertRaises(keyfile.KeyFileError): keyfile.create(path)

    def test_git_worktree_targets_refused(self):
        folder = self.folder / 'worktree'; folder.mkdir()
        (folder / '.git').write_text('gitdir: elsewhere', encoding='ascii')
        with self.assertRaises(keyfile.KeyFileError): keyfile.create(folder / 'private.key')
        self.assertFalse((folder / 'private.key').exists())

    def test_cli_reports_only_public_fingerprint_and_no_key_argument(self):
        path = self.folder / 'cli.key'
        script = str(HERE / 'b_warm_adapter_key.py')
        a = subprocess.run([sys.executable, script, 'create', '--file', str(path)], capture_output=True, text=True)
        self.assertEqual(a.returncode, 0, a.stderr)
        key = keyfile.load_key(path)
        b = subprocess.run([sys.executable, script, 'status', '--file', str(path)], capture_output=True, text=True)
        c = subprocess.run([sys.executable, script, 'create', '--file', str(path)], capture_output=True, text=True)
        for row in (a, b, c):
            self.assertTrue(key.hex() not in row.stdout + row.stderr, 'Secret leaked in CLI output')
            self.assertTrue(keyfile.encode(key).decode() not in row.stdout + row.stderr, 'Secret leaked in CLI output')
        self.assertEqual(json.loads(a.stdout)['fingerprint'], json.loads(b.stdout)['fingerprint'])
        self.assertEqual(c.returncode, 2)
        self.assertEqual(set(json.loads(c.stdout)), {'ok', 'operation', 'error'})
        self.assertTrue(secrets.compare_digest(keyfile.load_key(path), key))


def main():
    sources = {str(p): sha(p) for p in (Path(__file__), HERE / 'b_warm_adapter_key.py')}
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT / 'test.log').write_text(stream.getvalue(), encoding='utf-8')
    # Never serialize private key bytes or hashes of key files as test artifacts.
    # Only these generated test secrets are removed, irrespective of assertions.
    removed = 0
    for p in OUTPUT.rglob('*.key'):
        p.unlink(); removed += 1
    stable = all(sha(p) == digest for p, digest in sources.items())
    report = dict(result='PASS' if result.wasSuccessful() and stable else 'FAIL', tests=result.testsRun,
                  family='san14.local-adapter-key.v1', sources=sources, inputs_unchanged=stable,
                  test_secret_files_removed=removed, remaining_secret_files=len(list(OUTPUT.rglob('*.key'))),
                  actual_windows_acl=True, game_access=False, network_access=False,
                  artifacts={str(OUTPUT / 'test.log'):sha(OUTPUT / 'test.log')})
    (OUTPUT / 'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(OUTPUT / 'result.json'); print(stream.getvalue())
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
