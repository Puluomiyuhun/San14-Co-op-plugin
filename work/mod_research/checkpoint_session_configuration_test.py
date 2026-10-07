"""Offline parser tests over a root-created archived snapshot; no process IO."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import unittest

import checkpoint_session_configuration as c

P = Path(__file__).resolve().parent
SNAPSHOT = P / 'checkpoint_session_binding_snapshot_20261007-141015-074261.json'
SNAPSHOT_SHA = '6c8a910b33bd415fe0e433f5a336669909470298f9726f9f55afbd23988386f0'
STORAGE_SNAPSHOT = P / 'checkpoint_session_binding_snapshot_20261007-141555-245678.json'
STORAGE_SHA = '732ae0ff6fe5a1c6db48ce00afe88d6b8e821b45ec5406565a12219fb2a3b5da'


def load():
    raw = SNAPSHOT.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SNAPSHOT_SHA
    return json.loads(raw)


def load_storage():
    raw = STORAGE_SNAPSHOT.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == STORAGE_SHA
    return json.loads(raw)


def build(s, **kw):
    return c.build_manifest(s, expected_attachment=kw.pop('expected_attachment', s['attachment']),
                            expected_snapshot_sha256=kw.pop('digest', c.snapshot_sha256(s)), **kw)


def patch(s, label, offset, value, size=8):
    row = next(x for x in s['reads'] if x['label'] == label)
    raw = bytearray.fromhex(row['data_hex'])
    raw[offset:offset+size] = value.to_bytes(size, 'little')
    row['data_hex'] = raw.hex()


class Tests(unittest.TestCase):
    def test_real_archive_projects_identity_and_all_known_values(self):
        s = load(); m = build(s)
        self.assertEqual(m['request']['boundary']['states'][4], 2206474877488)
        self.assertEqual(m['request']['boundary']['menu'], 0)
        self.assertEqual(m['request']['boundary']['expectedRng'], 664502686)
        self.assertEqual(m['request']['boundary']['root'], 2203319480400)
        self.assertEqual(m['request']['boundary']['world'], 2207519469792)
        self.assertEqual([h['original_observed'] == h['original'] for h in m['hooks'][:3]], [True]*3)
        self.assertEqual({x['field'] for x in m['missing_observations']},
                         {'hooks.Load.original', 'hooks.Callable.original', 'storage_binding'})
        self.assertFalse(m['arm_allowed']); self.assertFalse(m['runtime_config_constructed'])

    def test_actual_empty_queue_is_preserved_not_fake_span(self):
        m = build(load())
        self.assertNotIn('queue', m['admission']['spans'])
        self.assertEqual(m['observations']['queue']['value'], 0)
        self.assertEqual({x['field'] for x in m['guard_conflicts']},
                         {'admission.initial_queue_span', 'admission.initial_cache_mode'})
        self.assertIsNone(m['bytes']['storage'])
        self.assertIsNone(m['session_callbacks']['validate'])

    def test_exact_digest_and_attachment_required(self):
        s = load()
        with self.assertRaises(c.ConfigurationError): build(s, digest='0'*64)
        for name in ('id', 'pid', 'birth', 'base', 'epoch'):
            bad = copy.deepcopy(s['attachment'])
            bad[name] = '1'*64 if name == 'id' else bad[name]+1
            with self.subTest(name=name), self.assertRaises(c.ConfigurationError):
                build(s, expected_attachment=bad)

    def test_version_build_provenance_and_authority_cannot_be_upgraded(self):
        original = load()
        for key, value in [('schema', 'san14.session-config-snapshot.v2'),
                           ('game_build_sha256', '0'*64), ('authorize_arm', True),
                           ('atomic_snapshot', True), ('game_writes', True)]:
            s = copy.deepcopy(original); s[key] = value
            with self.subTest(key=key), self.assertRaises(c.ConfigurationError): build(s)
        s = load(); s['capture']['source'] = 'FIXTURE_ONLY'
        with self.assertRaises(c.ConfigurationError): build(s)

    def test_mixed_empty_vector_shape_and_wrong_original_report_conflicts(self):
        s = load(); patch(s, 'manager', 0x38, 16)
        patch(s, 'slot_user', 0, s['attachment']['base']+0x3F9B08)
        m = build(s)
        self.assertIn('manager.queue_shape', {x['field'] for x in m['guard_conflicts']})
        self.assertIn('hooks.User.original', {x['field'] for x in m['guard_conflicts']})
        self.assertFalse(m['arm_allowed'])

    def test_missing_fields_not_borrowed_from_fixture_or_old_receipt(self):
        s = load(); s['reads'] = [r for r in s['reads'] if r['label'] != 'world_pointer']
        m = build(s)
        self.assertIsNone(m['request']['boundary']['world'])
        self.assertIsNone(m['request']['boundary']['year'])
        self.assertFalse(m['snapshot_fields_consistent'])

    def test_malformed_or_overlapping_raw_reads_rejected(self):
        s = load(); s['reads'].append(dict(s['reads'][0], label='duplicate_address'))
        with self.assertRaises(c.ConfigurationError): build(s)
        s = load(); s['reads'][0]['address'] = True
        with self.assertRaises(c.ConfigurationError): build(s)
        s = load(); s['attachment']['epoch'] = True
        with self.assertRaises(c.ConfigurationError): build(s)

    def test_attempt_binding_preserved_without_native_receipt(self):
        s = load(); a = {'token': 2**63+99, 'owner_binding': 'a1'*32,
                         'attempt_id': 'attempt_explicit_full_identifier',
                         'intent_id': 'intent_explicit_full_identifier', 'checkpoint_id': 'b2'*32}
        m = build(s, attempt=a)
        self.assertEqual(m['attempt'], a)
        self.assertEqual(m['request']['boundary']['attempt'], a['token'])
        self.assertEqual(m['identity']['ownerBinding'], a['owner_binding'])
        self.assertFalse(m['load_authorized'])
        bad = dict(a, token=True)
        with self.assertRaises(c.ConfigurationError): build(s, attempt=bad)

    def test_archived_vtable_records_match_extracted_profile(self):
        raw = (P/'game-runtime-image.bin').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268')
        for name, slot, original in c.HOOK_PROFILE:
            self.assertEqual(int.from_bytes(raw[slot:slot+8], 'little'), 0x7FF749440000+original, name)

    def test_actual_current_cached_storage_and_six_originals_do_not_authorize_arm(self):
        s = load_storage(); m = build(s)
        self.assertEqual(m['missing_observations'], [])
        self.assertEqual(m['storage']['holder'], s['attachment']['base']+0x18D08B8+16)
        self.assertTrue(m['storage']['cached_fastpath_observed'])
        self.assertEqual(m['storage']['cached_counter_address'],
                         next(r['address'] for r in s['reads'] if r['label'] == 'storage_context_generation'))
        self.assertEqual(m['hooks'][5]['original'], 140714057373840)
        self.assertEqual(m['hooks'][5]['slot'], 140714069754312+8)
        self.assertFalse(m['arm_allowed']); self.assertFalse(m['load_authorized'])
        self.assertTrue(m['unresolved_runtime_bindings'])

    def test_storage_cached_generation_and_code_are_checked(self):
        s = load_storage(); patch(s, 'storage_context_generation', 0, 2**63+91)
        m = build(s)
        self.assertIn('storage.cached_generation', {x['field'] for x in m['guard_conflicts']})
        s = load_storage(); patch(s, 'storage_context_init_code', 23, 0x75, 1)
        m = build(s)
        self.assertIn('storage.context_init_cached_code', {x['field'] for x in m['guard_conflicts']})


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    folder = P/'checkpoint_session_configuration_tests'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    sources = {name: hashlib.sha256((P/name).read_bytes()).hexdigest()
               for name in ('checkpoint_session_configuration.py', 'checkpoint_session_configuration_test.py')}
    evidence = {'schema': 'san14.session-config-data-only-tests.v1',
                'result': 'PASS' if result.wasSuccessful() else 'FAIL', 'tests': result.testsRun,
                'snapshot': str(SNAPSHOT), 'snapshot_file_sha256': SNAPSHOT_SHA,
                'snapshot_canonical_sha256': c.snapshot_sha256(load()),
                'storage_snapshot': str(STORAGE_SNAPSHOT), 'storage_snapshot_file_sha256': STORAGE_SHA,
                'source_sha256': sources, 'game_access': False, 'steam_access': False,
                'process_access': False, 'native_code_executed': False,
                'scope': 'Parser/projection of archived root snapshot and deliberate negative mutations; no native configuration or Arm permission.'}
    (folder/'result.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
    print(folder/'result.json')
    raise SystemExit(0 if result.wasSuccessful() else 1)
