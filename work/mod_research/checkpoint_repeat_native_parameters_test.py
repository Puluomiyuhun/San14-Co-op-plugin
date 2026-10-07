"""Offline conversion tests; no game access or frozen-source modification."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import unittest

import checkpoint_repeat_native_parameters as n
from checkpoint_repeat_load_profile_test import example


def admission(request):
    return {'schema': n.ADMISSION_SCHEMA, 'capture_id': 'a1'*32, 'challenge': 'a2'*32, 'sequence': 10,
            'profile_sha256': n.p.snapshot_sha256(request), 'binding': deepcopy(request['transaction']),
            'process': {k: request['current'][k] for k in ('attachment_id', 'pid', 'birth', 'base')},
            'game_build_sha256': n.p.GAME_SHA256, 'date': deepcopy(request['current']['date']),
            'identity': deepcopy(request['current']['identity']), 'phase': 'PLANNING_BOUNDARY',
            'quiet': {'stack_count': 5, 'queue_count': 0, 'user_phase': 2, 'cache_mode': 0,
                      'cache_pending': -1, 'cache_busy': 0},
            'pointers': {'states': [0x200000+i*0x1000 for i in range(5)], 'root': 0x300000,
                'world': 0x400000, 'cache': 0x500000, 'keyboard': 0x600000, 'toolbar': 0x700000,
                'panel': 0x800000, 'stack': 0x900000, 'stack_capacity': 16, 'queue': 0, 'queue_capacity': 0},
            'rng': 0x12345678, 'storage': {'storage': 0xa00000, 'vtable': 0xb00000,
                'original_read_method': 0xc01234, 'binding_sha256': 'a3'*32}}


def expectation(capture, after=9):
    return {'sha256': n.p.snapshot_sha256(capture), 'capture_id': capture['capture_id'],
            'challenge': capture['challenge'], 'after_sequence': after}


def prepare(request=None, capture=None, expected=None):
    r = request or example();c = capture or admission(r)
    return n.prepare(r, expected_current=deepcopy(r['current']), expected_offer=deepcopy(r['offer']),
        expected_transaction=deepcopy(r['transaction']), capture=c, expected_capture=expected or expectation(c))


def title(candidate):
    r = candidate['request']
    life = {'attempt': r['transaction']['native_attempt'], 'generation': r['transaction']['generation'],
            'attachment_id': r['current']['attachment_id'], 'checkpoint_sha256': r['offer']['save']['sha256'],
            'checkpoint_size': r['offer']['save']['size'], 'title': 0x204000, 'completion_call': 77,
            'native_result': 1, 'phase': 15}
    return {'schema': n.TITLE_SCHEMA, 'capture_id': 'b1'*32, 'challenge': 'b2'*32, 'sequence': 11,
            'profile_sha256': candidate['profile_sha256'], 'binding': deepcopy(r['transaction']),
            'process': {k: r['current'][k] for k in ('attachment_id', 'pid', 'birth', 'base')},
            'game_build_sha256': n.p.GAME_SHA256, 'date': deepcopy(r['offer']['date']),
            'root': 0x300000, 'world': 0x400000, 'title': 0x204000,
            'source': {'identity': deepcopy(r['offer']['incoming_identity']), 'force': 0xd00000,
                       'person': 0xd01000, 'district': 0xd02000, 'force_47': 21},
            'target': {'identity': deepcopy(r['offer']['viewer_identity']), 'force': 0xe00000,
                       'person': 0xe01000, 'district': 0xe02000, 'force_47': 22},
            'world_force': r['offer']['incoming_identity']['force_id'], 'control_before': 2,
            'lifecycle': life}


def bind(candidate, capture=None, expected=None, life=None, digest=None):
    c = capture or title(candidate)
    return n.bind_new_title(candidate, c, expected_candidate_sha256=digest or candidate['candidate_sha256'],
        expected_capture=expected or expectation(c, 10), expected_lifecycle=life or deepcopy(c['lifecycle']))


class NativeParametersTests(unittest.TestCase):
    def test_current_b_date_rng_go_to_boundary_not_loaded_a(self):
        c = prepare()
        self.assertEqual(c['request_candidate']['boundary']['force'], 2)
        self.assertEqual(c['request_candidate']['boundary']['day'], 11)
        self.assertEqual(c['request_candidate']['boundary']['expectedRng'], 0x12345678)
        self.assertEqual(c['identity_candidate']['source']['force_id'], 12)
        self.assertEqual(c['identity_candidate']['date'][2], 21)
        self.assertEqual(c['planning_candidate']['date'][2], 21)

    def test_file_binding_propagates_to_all_stages(self):
        c = prepare()
        for key in ('request_candidate', 'bytes_candidate', 'lifecycle_candidate', 'planning_candidate'):
            self.assertEqual(c[key]['target']['sha256'], 'f4'*32)
            self.assertEqual(c[key]['target']['size'], 280123)
            self.assertEqual(c[key]['target']['slot'], 63)

    def test_no_fabricated_force_flags_or_future_pointers(self):
        i = prepare()['identity_candidate']
        self.assertIsNone(i['source_force_47']);self.assertIsNone(i['target_force_47'])
        self.assertIsNone(i['resolved_pair']);self.assertTrue(i['requires_new_title_capture'])

    def test_title_binds_observed_flags_not_six_and_seven(self):
        c = bind(prepare());i = c['identity_candidate']
        self.assertEqual((i['source_force_47'], i['target_force_47']), (21, 22))
        self.assertEqual(i['resolved_pair']['source']['force'], 0xd00000)
        self.assertFalse(c['live_authority']);self.assertFalse(c['native_config_generated'])
        self.assertFalse(c['room_ready']);self.assertFalse(c['world_verified'])

    def test_legal_address_reuse_never_rejected_for_value_equality(self):
        c = prepare();t = title(c)
        self.assertEqual(t['root'], c['request_candidate']['boundary']['root'])
        self.assertEqual(t['title'], c['planning_candidate']['previousUser'])
        bind(c, t)

    def test_reread_may_have_same_rng_and_addresses_with_new_identity(self):
        r = example();a = admission(r);first = prepare(r, a)
        r['transaction'].update(attempt_id='attempt_3', native_attempt=346, generation=3, previous_attempt_id='attempt_2')
        newer = admission(r);newer.update(capture_id='cc'*32, challenge='cd'*32, sequence=20)
        next_candidate = prepare(r, newer, expectation(newer, 19))
        self.assertEqual(first['request_candidate']['boundary']['root'], next_candidate['request_candidate']['boundary']['root'])
        with self.assertRaises(n.p.ProfileError):prepare(r, a, expectation(a))

    def test_source_and_target_are_not_local_local(self):
        c = prepare();i = bind(c)['identity_candidate']
        self.assertEqual(i['source']['force_id'], 12);self.assertEqual(i['target']['force_id'], 2)

    def test_admission_reject_cases(self):
        changes = {
            'old_sequence': lambda c: c.update(sequence=9),
            'foreign_process': lambda c: c['process'].update(pid=43),
            'foreign_birth': lambda c: c['process'].update(birth=123457),
            'foreign_attempt': lambda c: c['binding'].update(native_attempt=347),
            'foreign_generation': lambda c: c['binding'].update(generation=3),
            'wrong_rng_type': lambda c: c.update(rng=True),
            'rng_overflow': lambda c: c.update(rng=2**32),
            'null_world': lambda c: c['pointers'].update(world=0),
            'unaligned_pointer': lambda c: c['pointers'].update(root=0x300001),
            'aliased_states': lambda c: c['pointers']['states'].__setitem__(2, c['pointers']['states'][1]),
            'nonempty_queue': lambda c: c['pointers'].update(queue=0x112200, queue_capacity=16),
            'old_local_a': lambda c: c.update(identity=deepcopy(n.p.FIXED_A)),
            'incoming_date_used_as_local': lambda c: c.update(date=[203, 8, 21]),
            'unsettled': lambda c: c.update(phase='BATTLE'),
            'storage_extra_api': lambda c: c['storage'].update(validate=123456),
            'pointer_extra_title': lambda c: c['pointers'].update(title=0x203000),
            'bad_profile': lambda c: c.update(profile_sha256='ee'*32),
            'cache_not_clear': lambda c: c['quiet'].update(cache_pending=63),
            'busy_cache': lambda c: c['quiet'].update(cache_busy=1),
            'wrong_user_phase': lambda c: c['quiet'].update(user_phase=3),
        }
        r = example()
        for label, change in changes.items():
            with self.subTest(label=label):
                a = admission(r);change(a)
                with self.assertRaises(n.p.ProfileError):prepare(r, a, expectation(a))

    def test_independent_capture_content_and_challenge(self):
        r = example();a = admission(r);e = expectation(a)
        for field, value in (('rng', 99), ('challenge', 'ee'*32), ('capture_id', 'ff'*32)):
            changed = deepcopy(a);changed[field] = value
            with self.assertRaises(n.p.ProfileError):prepare(r, changed, e)

    def test_title_reject_cases(self):
        changes = {
            'same_capture': lambda t: t.update(capture_id='a1'*32),
            'same_challenge': lambda t: t.update(challenge='a2'*32),
            'old_sequence': lambda t: t.update(sequence=10),
            'old_generation': lambda t: t['lifecycle'].update(generation=1),
            'wrong_bytes': lambda t: t['lifecycle'].update(checkpoint_sha256='12'*32),
            'partial_bytes': lambda t: t['lifecycle'].update(checkpoint_size=123),
            'no_completion': lambda t: t['lifecycle'].update(completion_call=0),
            'bool_completion': lambda t: t['lifecycle'].update(completion_call=True),
            'native_fail': lambda t: t['lifecycle'].update(native_result=0),
            'bool_native_success': lambda t: t['lifecycle'].update(native_result=True),
            'wrong_phase': lambda t: t['lifecycle'].update(phase=2),
            'wrong_title': lambda t: t.update(title=0x203000),
            'local_world_as_incoming': lambda t: t.update(world_force=2),
            'old_date': lambda t: t.update(date=[203, 8, 11]),
            'local_source_as_incoming': lambda t: t['source'].update(identity=deepcopy(n.p.FIXED_B)),
            'flag_not_byte': lambda t: t['target'].update(force_47=256),
            'flag_bool': lambda t: t['target'].update(force_47=True),
            'same_pair': lambda t: t['target'].update(force=t['source']['force']),
            'foreign_attachment': lambda t: t['lifecycle'].update(attachment_id='12'*32),
            'pair_alignment': lambda t: (t.update(title=0x204008), t['lifecycle'].update(title=0x204008)),
        }
        c = prepare()
        for label, change in changes.items():
            with self.subTest(label=label):
                t = title(c);change(t)
                with self.assertRaises(n.p.ProfileError):bind(c, t)

    def test_different_independent_lifecycle_receipt(self):
        c = prepare();t = title(c);life = deepcopy(t['lifecycle']);life['completion_call'] = 78
        with self.assertRaises(n.p.ProfileError):bind(c, t, life=life)

    def test_mutation_and_resigning_and_authority_escalation_rejected(self):
        c = prepare();original_digest = c['candidate_sha256'];t = title(c)
        c['identity_candidate']['source_force_47'] = 6
        with self.assertRaises(n.p.ProfileError):bind(c, t)
        c.pop('candidate_sha256');c['candidate_sha256'] = n.p.snapshot_sha256(c)
        with self.assertRaises(n.p.ProfileError):bind(c, t, digest=original_digest)
        c = prepare();c['live_authority'] = True;c.pop('candidate_sha256');c['candidate_sha256'] = n.p.snapshot_sha256(c)
        with self.assertRaises(n.p.ProfileError):bind(c, title(c))

    def test_cannot_rebind_title_or_modify_old_result(self):
        c = prepare();out = bind(c)
        with self.assertRaises(n.p.ProfileError):bind(out)
        self.assertIsNone(c['identity_candidate']['resolved_pair'])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeParametersTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    folder = Path(__file__).parent/'checkpoint_repeat_native_parameters_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    evidence = {'passed': result.wasSuccessful(), 'test_methods': result.testsRun,
                'admission_bad_rows': 20, 'title_bad_rows': 20, 'independent_binding_and_mutation_cases': True,
                'cpp_field_mapping': n.CPP_FIELD_MAPPING, 'candidate': prepare(), 'resolved_candidate': bind(prepare()),
                'game_access': False, 'frozen_sources_modified': False}
    (folder/'result.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(folder/'result.json')
    raise SystemExit(0 if result.wasSuccessful() else 1)
