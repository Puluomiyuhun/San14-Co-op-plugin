"""Offline profile checks only; source audit reads code, never a game process."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import unittest

import checkpoint_repeat_load_profile as p


def example(repeat=True):
    return {'schema': p.SCHEMA, 'game_build_sha256': p.GAME_SHA256,
            'current': {'attachment_id': 'ab'*32, 'pid': 42, 'birth': 123456, 'base': 0x140000000,
                        'date': [203, 8, 11], 'identity': deepcopy(p.FIXED_B if repeat else p.FIXED_A),
                        'phase': 'PLANNING_BOUNDARY'},
            'offer': {'checkpoint_id': 'c1'*32, 'scope_sha256': 'd2'*32, 'room_epoch': 'e3'*16,
                      'period': 2, 'cut': {'sequence': 7, 'prefix_sha256': '98'*32},
                      'save': {'sha256': 'f4'*32 if repeat else p.FIXED_SHA, 'size': 280123 if repeat else 274880},
                      'date': [203, 8, 21] if repeat else [203, 8, 11],
                      'incoming_identity': deepcopy(p.FIXED_A), 'viewer_identity': deepcopy(p.FIXED_B),
                      'source_player': 'A', 'recipient': 'B', 'slot': 63, 'basename': 'svdexccSC03.s14'},
            'transaction': {'attachment_id': 'ab'*32, 'attempt_id': 'attempt_2' if repeat else 'attempt_1',
                            'native_attempt': 345, 'native_epoch': 456, 'generation': 2 if repeat else 1,
                            'owner_binding': '67'*32, 'previous_attempt_id': 'attempt_1' if repeat else None}}


def run_plan(r, expected=None):
    x = expected or deepcopy(r)
    return p.build_plan(r, expected_current=x['current'], expected_offer=x['offer'],
                        expected_transaction=x['transaction'])


class ProfileTests(unittest.TestCase):
    def test_initial_matches_fixed_data_but_no_authority(self):
        result = run_plan(example(False))
        self.assertTrue(result['matches_frozen_data_profile'])
        self.assertFalse(result['live_authority'])
        self.assertFalse(result['native_config_generated'])

    def test_repeat_keeps_local_b_incoming_a_and_cas_a_to_b(self):
        result = run_plan(example())
        self.assertEqual(result['preload_local']['identity'], p.FIXED_B)
        self.assertEqual(result['after_native_read_before_identity']['identity'], p.FIXED_A)
        self.assertEqual(result['identity_cas']['expected'], p.FIXED_A)
        self.assertEqual(result['identity_cas']['replacement'], p.FIXED_B)
        self.assertFalse(result['matches_frozen_data_profile'])
        self.assertFalse(result['room_ready'])

    def test_local_already_at_simulation_end(self):
        r = example();r['current']['date'] = [203, 8, 21]
        self.assertEqual(run_plan(r)['after_identity_planning']['date'], r['current']['date'])

    def test_year_rollover(self):
        r = example();r['current']['date'] = [203, 12, 21];r['offer']['date'] = [204, 1, 1]
        run_plan(r)

    def test_unknown_slot_is_explicit_blocker(self):
        r = example();r['offer']['slot'] = 64;r['offer']['basename'] = 'svdexunknown.s14'
        self.assertTrue(any('slot-to-native-name' in b for b in run_plan(r)['blockers']))

    def test_no_aliasing(self):
        r = example();result = run_plan(r);r['offer']['date'][0] = 999
        self.assertEqual(result['after_identity_planning']['date'], [203, 8, 21])

    def test_changed_ruler_is_preserved_not_fixed_to_952(self):
        r = example();r['current']['identity']['ruler_id'] = 999;r['offer']['viewer_identity']['ruler_id'] = 999
        self.assertEqual(run_plan(r)['after_identity_planning']['identity']['ruler_id'], 999)

    def test_authoritative_ruler_change_does_not_reuse_local_ruler(self):
        r = example();r['offer']['viewer_identity']['ruler_id'] = 999
        result = run_plan(r)
        self.assertEqual(result['preload_local']['identity']['ruler_id'], 952)
        self.assertEqual(result['identity_cas']['replacement']['ruler_id'], 999)

    def test_strict_failures(self):
        cases = {
            'old_date': lambda r: r['offer'].update(date=[203, 8, 1]),
            'skipped_date': lambda r: r['offer'].update(date=[203, 9, 1]),
            'mid_animation_date': lambda r: r['offer'].update(date=[203, 8, 17]),
            'bad_month': lambda r: r['offer'].update(date=[203, 13, 1]),
            'negative_size': lambda r: r['offer']['save'].update(size=-1),
            'bool_size': lambda r: r['offer']['save'].update(size=True),
            'uppercase_sha': lambda r: r['offer']['save'].update(sha256='A'*64),
            'foreign_attachment': lambda r: r['transaction'].update(attachment_id='fe'*32),
            'replay': lambda r: r['transaction'].update(attempt_id='attempt_1'),
            'zero_attempt': lambda r: r['transaction'].update(native_attempt=0),
            'room_epoch_as_native': lambda r: r['transaction'].update(native_epoch=r['offer']['room_epoch']),
            'native_epoch_as_room': lambda r: r['offer'].update(room_epoch=456),
            'b_checkpoint_no_cas': lambda r: r['offer'].update(incoming_identity=deepcopy(p.FIXED_B)),
            'local_not_b': lambda r: r['current'].update(identity=deepcopy(p.FIXED_A)),
            'wrong_slot_leaf': lambda r: r['offer'].update(basename='svdexccSC04.s14'),
            'wrong_leaf_slot': lambda r: r['offer'].update(slot=64),
            'path_traversal': lambda r: r['offer'].update(basename='../svdexccSC03.s14'),
            'extra_pointer': lambda r: r['current'].update(root=0x123456),
            'fake_authority': lambda r: r.update(live_authority=True),
            'unsettled': lambda r: r['current'].update(phase='BATTLE'),
            'peer_is_host': lambda r: r['offer'].update(recipient='A'),
            'bad_prefix': lambda r: r['offer'].update(cut=7),
            'wrong_build': lambda r: r.update(game_build_sha256='ff'*32),
        }
        for label, change in cases.items():
            with self.subTest(label=label):
                r = example();change(r)
                with self.assertRaises(p.ProfileError):run_plan(r)

    def test_independent_bindings_reject_stale_or_substituted_valid_values(self):
        cases = {
            'pid': lambda r: r['current'].update(pid=43),
            'birth': lambda r: r['current'].update(birth=123457),
            'attachment': lambda r: (r['current'].update(attachment_id='fe'*32),r['transaction'].update(attachment_id='fe'*32)),
            'checkpoint_id': lambda r: r['offer'].update(checkpoint_id='12'*32),
            'save_sha': lambda r: r['offer']['save'].update(sha256='34'*32),
            'scope': lambda r: r['offer'].update(scope_sha256='56'*32),
            'cut': lambda r: r['offer']['cut'].update(sequence=8),
            'room_epoch': lambda r: r['offer'].update(room_epoch='67'*16),
            'period': lambda r: r['offer'].update(period=3),
            'generation': lambda r: r['transaction'].update(generation=3),
            'native_epoch': lambda r: r['transaction'].update(native_epoch=457),
            'attempt_id': lambda r: r['transaction'].update(attempt_id='attempt_3'),
            'native_attempt': lambda r: r['transaction'].update(native_attempt=346),
        }
        for label, change in cases.items():
            with self.subTest(label=label):
                r = example();expected = deepcopy(r);change(r)
                with self.assertRaises(p.ProfileError):run_plan(r, expected)

    def test_complete_anchor_inventory(self):
        root = Path(__file__).parent
        source = {name: (root/name).read_text(encoding='utf-8-sig') for name, _, _ in p.AUDIT_ANCHORS}
        evidence = p.audit_sources(source)
        self.assertEqual(len(evidence['anchors']), len(p.AUDIT_ANCHORS))
        name, anchor, _ = p.AUDIT_ANCHORS[0]
        source[name] = source[name].replace(anchor, 'changed')
        with self.assertRaises(p.ProfileError):p.audit_sources(source)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProfileTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    root = Path(__file__).parent
    folder = root/'checkpoint_repeat_load_profile_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    source = {name: (root/name).read_text(encoding='utf-8-sig') for name, _, _ in p.AUDIT_ANCHORS}
    evidence = {'passed': result.wasSuccessful(), 'test_methods': result.testsRun,
                'invalid_scenarios': 36, 'audit': p.audit_sources(source),
                'repeat_example': run_plan(example()), 'network_mapping': p.NETWORK_MAPPING,
                'game_access': False, 'frozen_sources_modified': False}
    (folder/'result.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(folder/'result.json')
    raise SystemExit(0 if result.wasSuccessful() else 1)
