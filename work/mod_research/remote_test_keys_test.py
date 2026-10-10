"""Owned Windows key files only; no game, Steam, or network."""
from contextlib import redirect_stdout
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

import remote_test_keys as tool

HERE = Path(__file__).resolve().parent
PRIVATE = HERE.parents[2]/'mod_research'
OUTPUT = None


class Cases(unittest.TestCase):
    def setUp(self):
        self.root = OUTPUT/self._testMethodName
        self.root.mkdir()

    def test_create_export_recipient_import_and_exact_role_mapping(self):
        a = tool.create(self.root/'A')
        b = tool.export_set(self.root/'A', self.root/'transfer')
        shutil.copytree(self.root/'transfer', self.root/'received')
        c = tool.import_set(self.root/'received', self.root/'B')
        self.assertEqual(a['fingerprints'], c['fingerprints'])
        self.assertEqual(a['set_id'], c['set_id'])
        self.assertTrue(b['contains_shared_secrets'])
        self.assertNotEqual(a['a_config_fields']['adapter_key_path'], c['b_config_fields']['adapter_key_path'])
        for name in tool.NAMES:
            self.assertEqual(tool.keys.load_key(self.root/'A'/(name+'.key')), tool.keys.load_key(self.root/'B'/(name+'.key')))
        for result in (a, b, c):
            self.assertFalse(result['remote_key_pairing_verified'])
            self.assertFalse(result['secret_disclosed'])

    def test_foreign_fingerprint_and_role_swap_refused_before_destination(self):
        tool.create(self.root/'A')
        folder = self.root/'A'
        doc = json.loads((folder/'key-set.json').read_text())
        doc['fingerprints']['report'], doc['fingerprints']['cut'] = doc['fingerprints']['cut'], doc['fingerprints']['report']
        (folder/'key-set.json').write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'fingerprints'):
            tool.import_set(folder, self.root/'B')
        self.assertFalse((self.root/'B').exists())

    def test_duplicate_keys_refused(self):
        tool.create(self.root/'A')
        folder = self.root/'A'
        doc = json.loads((folder/'key-set.json').read_text())
        key = tool.keys.load_key(folder/'adapter.key')
        (folder/'cut.key').unlink()
        tool.keys.Native().write_new(folder/'cut.key', key)
        doc['fingerprints']['cut'] = doc['fingerprints']['adapter']
        (folder/'key-set.json').write_text(json.dumps(doc))
        with self.assertRaises(ValueError): tool.inspect(folder)

    def test_compare_peer_before_any_game_or_network(self):
        tool.create(self.root/'A'); tool.export_set(self.root/'A', self.root/'B')
        matched = tool.compare_peer(self.root/'B', self.root/'A'/'key-set.json')
        self.assertTrue(matched['peer_manifest_matches'])
        self.assertFalse(matched['live_peer_checked'])
        tool.create(self.root/'wrong')
        with self.assertRaisesRegex(ValueError, 'fingerprints differ'):
            tool.compare_peer(self.root/'wrong', self.root/'A'/'key-set.json')

    def test_existing_directory_is_never_overwritten(self):
        original = tool.create(self.root/'A')
        with self.assertRaises(ValueError): tool.create(self.root/'A')
        self.assertEqual(tool.inspect(self.root/'A'), original)
        checkout = self.root/'checkout'; checkout.mkdir(); (checkout/'.git').write_text('owned test marker')
        with self.assertRaisesRegex(ValueError, 'outside Git'): tool.create(checkout/'keys')
        self.assertFalse((checkout/'keys').exists())

    def test_no_secret_in_cli_or_public_manifest(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(tool.main(['create', '--output', str(self.root/'A')]), 0)
            self.assertEqual(tool.main(['check', '--folder', str(self.root/'A')]), 0)
            self.assertEqual(tool.main(['create', '--output', str(self.root/'A')]), 1)
        public = output.getvalue()+(self.root/'A'/'key-set.json').read_text()
        for name in tool.NAMES:
            self.assertNotIn(tool.keys.load_key(self.root/'A'/(name+'.key')).hex(), public)

    def test_default_help_never_opens_key_api(self):
        with patch.object(tool.keys, 'Native', side_effect=AssertionError('must remain inert')), redirect_stdout(io.StringIO()):
            self.assertEqual(tool.main([]), 0)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if __name__ == '__main__':
    OUTPUT = PRIVATE/'remote_test_keys_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True)
    sources = {str(p): sha(p) for p in (Path(__file__), HERE/'remote_test_keys.py', HERE/'b_warm_adapter_key.py')}
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    # Remove only the ephemeral keys created by this test, including failures.
    removed = 0
    for p in OUTPUT.rglob('*.key'):
        assert p.resolve().is_relative_to(OUTPUT.resolve())
        p.unlink(); removed += 1
    log = OUTPUT/'test.log'; log.write_text(stream.getvalue(), encoding='utf-8')
    stable = all(sha(p) == h for p, h in sources.items())
    report = dict(result='PASS' if result.wasSuccessful() and stable else 'FAIL', tests=result.testsRun,
                  sources=sources, inputs_unchanged=stable, actual_windows_acl=True, game_access=False,
                  network_access=False, test_keys_removed=removed, artifacts={str(log): sha(log)})
    (OUTPUT/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(stream.getvalue()); print(OUTPUT/'result.json')
    raise SystemExit(report['result'] != 'PASS')
