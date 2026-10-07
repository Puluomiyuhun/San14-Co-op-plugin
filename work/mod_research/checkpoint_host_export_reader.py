"""Pinned historical A export -> artifact bytes; never a current-world provider.

Only fixed files beneath this workspace are opened. Paths inside old receipts
are data, never read targets. No game/Steam/process/native imports or writes.
The retired replacement-state save entry is neither imported nor executed.
"""
from dataclasses import dataclass
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat
import struct

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
GAME_SHA = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
ARCHIVE_SHA = '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
ARCHIVE_SIZE = 274880
NODE = {'year': 203, 'month': 8, 'day': 11, 'phase': 'PLANNING_BOUNDARY'}
STACK = ['CRootState', 'CMotorGameState', 'CGameState', 'CStrategyState', 'CUserStrategyState']
# Values copied from independently reviewed, completed historical evidence.
# No caller-supplied digest may approve a replacement receipt or archive.
SOURCES = {
    'archive': ('checkpoint_push_archives/20261006-204306-581930/mppush01.s14', 274880, ARCHIVE_SHA),
    'archive_receipt': ('checkpoint_push_archives/20261006-204306-581930/result.json', 3487,
        'b51a72a6c7bfc9b4e71ccc1f30d25a53d68169cc910d0c38ae7db4cf746e1cb7'),
    'save_receipt': ('checkpoint_push_runs/20261006-203111-687580/result.json', 60122,
        '1653c91651f5d43b2173a185c72845a2631923173dd07b1c266641ce5cf2e0a4'),
    'save_intent': ('checkpoint_push_once.intent', 64,
        '26720bd66884ed52565f91a095e861a03887448a5bea3c7aa9cf3d333c216a1f'),
    'publish_receipt': ('checkpoint_cc_publish_runs/20261007-011018-444185/result.json', 102466,
        '3af19be5c7d44e40e41c872622adf26ecbfcb0f72a2017b9b2df1033858fb4c3'),
    'publish_intent': ('checkpoint_cc_publish_native_once.intent', 176,
        'f9459bad4f4c42c8f095a7b859c326a5c0a6e2bffce97a192e3573a600cbefe6'),
    'publish_binding': ('checkpoint_cc_publish_binding.json', 842,
        '1a1b1f68e3afb75b1f0be086b375bf2e1bb8ae826c3901a1f7505af945f7152b'),
    'stage_receipt': ('checkpoint_cc_stage_result.json', 96112,
        'edd07e29cc9a8ed549d038af5392cbb38bf2b0ff5d23708512d67cb6ecc09c06'),
    'retirement': ('private_checkpoint_save_RETIRED.json', 1133,
        'b328f6f4acb1140c864fd94b6fbcf06e98f8ffa786bd236a84a5b0e91683b1b8'),
}


class HostExportError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise HostExportError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(',', ':')).encode('ascii')


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_evidence_key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(HostExportError('nonfinite_evidence')))


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_workspace_file(path, expected_size, expected_sha256):
    """Read an explicit workspace file, with size/hash and ordinary drift checks.

    This is a byte snapshot, not a filesystem lease or an atomic multi-file
    snapshot. Fixed hashes bind each retained byte array independently.
    """
    path = Path(path).absolute()
    require(path.is_relative_to(WORKSPACE), 'outside_workspace')
    require('..' not in path.parts, 'relative_parent_not_allowed')
    for item in (path, *path.parents):
        if not item.is_relative_to(WORKSPACE):
            break
        info = item.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, 'st_file_attributes', 0) & 0x400),
                'reparse_source_not_allowed')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size == expected_size, 'source_size_changed')
        raw = stream.read(expected_size + 1)
        after = os.fstat(stream.fileno())
    require(_signature(before) == _signature(after) == _signature(path.stat()), 'source_changed_during_read')
    require(len(raw) == expected_size and sha(raw) == expected_sha256, 'source_sha256_changed')
    return raw


def _eq_int(value, expected, reason):
    require(type(value) is int and value == expected, reason)


def _ones(row, keys, reason):
    require(all(type(row[k]) is int and row[k] == 1 for k in keys), reason)


def _zeros(row, keys, reason):
    require(all(type(row[k]) is int and row[k] == 0 for k in keys), reason)


def _coverage(row):
    require(all(row[k] is True for k in ('valid_inputs', 'matched', 'context_equal',
        'all_objects_except_allocator_pools_equal', 'all_48400_hex_serialized_fields_equal',
        'global_rng_equal', 'world_rng_fields_equal')), 'incomplete_historical_coverage')
    require(row['full_world_verified'] is False, 'unsupported_full_world_claim')
    require(row['missing_records'] == row['extra_records'] == row['changed_records'] == [],
            'historical_records_changed')
    _eq_int(row['record_count_before'], 783, 'wrong_historical_record_count')
    _eq_int(row['record_count_after'], 783, 'wrong_historical_record_count')
    _eq_int(row['hex_payload_bytes'], 242000, 'wrong_historical_hex_count')


def _boundary(row):
    require(row['result'] == 'PASS' and row['reasons'] == [], 'historical_boundary_failed')
    s = row['context']['snapshot']
    require(s['exe_sha256'] == GAME_SHA and s['state_stack'] == STACK and
            s['in_player_strategy'] is True, 'historical_build_or_planning_mismatch')
    require({k: s['date'][k] for k in ('year', 'month', 'day')} == {k: NODE[k] for k in ('year', 'month', 'day')},
            'historical_date_mismatch')
    _eq_int(s['player']['force_id'], 12, 'historical_force_mismatch')
    _eq_int(s['player']['ruler_id'], 666, 'historical_ruler_mismatch')
    _eq_int(row['context']['state_sample']['phase_raw'], 2, 'historical_phase_mismatch')
    _eq_int(row['pending_vector']['count'], 0, 'historical_pending_request')
    require(all(r['size'] == 0 and r['text'] == '' for r in row['request_strings']), 'historical_save_request_busy')
    return {k: row[k] for k in ('pid', 'process_birth', 'base', 'pinned_user', 'pinned_game', 'pinned_world')}


def _validate_semantics(blobs):
    """Internal schema/relationship checks AFTER all independently pinned hashes.

    Kept separate for fault tests; production calls only _validated_bundle.
    """
    a, s, p, b, t, retired = (_json(blobs[k]) for k in (
        'archive_receipt', 'save_receipt', 'publish_receipt', 'publish_binding', 'stage_receipt', 'retirement'))
    require(retired['status'] == 'RETIRED_UNSAFE_STATE_ENTRY' and retired['native_export_success'] is False
            and retired['automatic_retry'] is False, 'retired_entry_policy_changed')
    require(a['schema'] == 'san14.checkpoint-push-archive.v1' and a['result'] == 'PASS'
            and a['passing_bounded_A_export'] is True, 'archive_receipt_failed')
    require(a['filename'] == 'mppush01.s14' and a['size'] == ARCHIVE_SIZE and a['sha256'] == ARCHIVE_SHA
            and sha(blobs['archive']) == ARCHIVE_SHA, 'archive_binding_mismatch')
    require(a['export_result_sha256'] == sha(blobs['save_receipt']), 'archive_save_receipt_unbound')
    require(a['date'] == {k: NODE[k] for k in ('year', 'month', 'day')} and a['file_format_version'] == 92
            and a['native_parser_success'] is True and a['full_world_verified'] is False
            and a['load_authorized'] is False, 'archive_header_or_scope_mismatch')
    require(sha(bytes.fromhex(a['parsed_header_hex'])) == a['parsed_header_sha256'] and
            sha(blobs['archive'][:a['header_bytes_consumed']]) == a['raw_header_prefix_sha256'],
            'archived_header_evidence_mismatch')
    require(s['schema'] == 'san14.checkpoint-push-result.v2' and s['result'] == 'PASS'
            and s['mode'] == 'execute' and s['native_save_complete'] is True and s['capture_error'] is None,
            'save_not_completed')
    require(s['old_pilot_reenabled'] is False and s['load_performed'] is False
            and s['native_worker_directly_called'] is False and s['full_world_sync_proven'] is False,
            'unsafe_or_overstated_save')
    sa = s['adapter']
    _eq_int(sa['status'], 8, 'save_not_terminal')
    _ones(sa, ('accepted', 'binder_calls', 'queue_calls', 'intent_created', 'intent_flushed',
        'binder_returned', 'queue_returned', 'slot_restored', 'protection_restored', 'save_association_ok',
        'save_worker_started', 'save_worker_joined', 'save_native_success', 'save_finalizer_called',
        'save_finalizer_returned', 'save_globals_cleared', 'save_observation_done', 'save_slot_restored',
        'save_protection_restored', 'return_seen', 'return_matched'), 'save_not_single_complete_return')
    _zeros(sa, ('error', 'exception_code', 'active_callbacks', 'save_active_callbacks',
        'save_observation_error', 'stop_requested'), 'save_uncertain_or_not_drained')
    require(sa['queued_at'] < sa['finalized_at'] < sa['returned_at'], 'save_return_order')
    identities = [_boundary(row) for row in (s['before'], s['after'], p['before'], p['after'])]
    require(all(row == identities[0] for row in identities), 'historical_attachment_changed')
    require(all(sa[k] == int(s['before'][k], 16) for k in ('pinned_user', 'pinned_game', 'pinned_world')),
            'save_pinned_objects_mismatch')
    require(sa['before_rng'] == sa['after_rng'] == s['before']['global_rng'] == s['after']['global_rng'],
            'save_rng_changed')
    intent = struct.unpack('<Q9I16s4x', blobs['save_intent'])
    require(intent == (0x53414e1450534832, 2, identities[0]['pid'], sa['executor_thread'], 0xffffffff,
                      203, 8, 11, 12, 666, b'mppush01.s14\0\0\0\0'), 'save_intent_identity_mismatch')
    f, done = s['file'], s['completion_evidence']
    require(f['size'] == ARCHIVE_SIZE and f['sha256'] == ARCHIVE_SHA and f['stable'] is True
            and f['samples'] >= 3 and f['span_seconds'] >= 1 and f['first_seen_after_queue'] is True,
            'saved_file_not_stable_or_bound')
    require(done['complete'] is True and done['native_lifecycle_ok'] is True
            and done['ordinary_saves_unchanged'] is True and done['full_world_verified'] is False
            and done['B_load_authorized'] is False and s['hooks_restored_from_memory'] is True,
            'save_cleanup_or_coverage_incomplete')
    _coverage(done['coverage'])
    require(p['schema'] == 'san14.checkpoint-cc-publish-live.v1' and p['result'] == 'PASS'
            and p['mode'] == 'publish' and p['native_publish_complete'] is True
            and p['stable_terminal_observed'] is True and p['actual_hook_slots_restored'] is True
            and p['existing_files_unchanged'] is True and p['two_observed_native_reads_matched'] is True,
            'publish_not_completed')
    require(all(p[k] is False for k in ('load_requested', 'B_load_authorized',
        'future_load_byte_identity_proven', 'full_world_verified')), 'publish_unsupported_authority')
    pa, write = p['adapter'], p['adapter']['publish']
    _eq_int(pa['state'], 5, 'publish_not_terminal')
    _zeros(pa, ('error', 'stopRequested', 'exceptionCode', 'osError', 'callbackActive', 'callbackFaults',
               'reentrantClaims', 'nativeLoadAuthorized', 'fullWorldVerified'), 'publish_uncertain_or_not_drained')
    _ones(pa, ('originalReturned', 'verifyAttempts', 'slotRestored', 'protectionRestored',
               'identityMatched', 'localPinReleased', 'bridgeDrainedSnapshot'), 'publish_not_single_complete_return')
    _ones(pa['bridge'], ('started', 'native_started', 'native_returned', 'before_calls', 'after_calls'),
          'publish_bridge_not_once')
    _zeros(pa['bridge'], ('abnormal_exits', 'active'), 'publish_bridge_not_drained')
    _ones(write, ('writeAttempts', 'writeReturned', 'nativeWriteReturn', 'intentCreated', 'intentDurable',
                 'localPinReleased', 'sourceMatched', 'matched', 'publishAttempts'), 'publish_write_not_once')
    _eq_int(write['state'], 5, 'publish_write_not_terminal')
    _zeros(write, ('osError', 'exceptionCode'), 'publish_write_uncertain')
    require(pa['readCalls'] == 2 and pa['readReturns'] == [ARCHIVE_SIZE] * 2
            and pa['sizes'] == [ARCHIVE_SIZE] * 3 and pa['verifiedSize'] == ARCHIVE_SIZE
            and pa['expectedSha256'] == pa['localSha256'] == write['sourceSha256'] == ARCHIVE_SHA
            and pa['nativeSha256'] == [ARCHIVE_SHA] * 2, 'published_native_bytes_mismatch')
    _coverage(p['known_coverage']); _coverage(p['source_known_coverage'])
    require(p['stage_receipt_sha256'] == b['stage_sha256'] == sha(blobs['stage_receipt'])
            and t['result'] == 'PASS' and t['native_slot'] == 63 and t['target_sha256'] == ARCHIVE_SHA
            and t['bytes'] == ARCHIVE_SIZE and t['added_files'] == ['svdexccSC03.s14']
            and t['existing_files_unchanged'] is True and t['load_requested'] is False,
            'publish_stage_unbound')
    for key in ('pid', 'process_birth', 'base', 'pinned_user', 'pinned_world'):
        require(b['attachment'][key] == identities[0][key], 'publish_owner_attachment_mismatch')
    pi = struct.unpack('<32sIII16s5I32s32s32s', blobs['publish_intent'])
    require(pi[:5] == (b'san14.cc03.publish.intent.v1'.ljust(32, b'\0'), 1, 176, ARCHIVE_SIZE,
                      b'svdexccSC03.s14'.ljust(16, b'\0'))
            and list(pi[5:10]) == b['identity'] and pi[10].hex() == b['ownerBinding']
            and pi[11].hex() == ARCHIVE_SHA, 'publish_intent_identity_mismatch')
    return identities[0], a['created']


@dataclass(frozen=True)
class ArchivedHostExport:
    """Retained immutable bytes and serialized evidence; no load/save permission."""
    _world: bytes
    _adapter: bytes

    @property
    def archive_sha256(self): return sha(self._world)

    @property
    def archive_size(self): return len(self._world)

    @property
    def receipt(self): return json.loads(self._adapter)

    def parts_for_archive_replay(self, node):
        require(type(node) is dict and set(node) == set(NODE) and node == NODE and
                all(type(node[k]) is int for k in ('year', 'month', 'day')),
                'historical_archive_cannot_represent_another_boundary')
        return {'world.s14': self._world, 'adapter.json': self._adapter}


def _validated_bundle(blobs):
    require(type(blobs) is dict and set(blobs) == set(SOURCES), 'incomplete_source_bundle')
    for key, (_, size, digest) in SOURCES.items():
        require(type(blobs[key]) is bytes and len(blobs[key]) == size and sha(blobs[key]) == digest,
                'unapproved_source_' + key)
    try:
        identity, archived_at = _validate_semantics(blobs)
    except (KeyError, TypeError, ValueError, struct.error) as exc:
        if isinstance(exc, HostExportError): raise
        raise HostExportError('malformed_historical_evidence') from exc
    receipt = {
        'schema': 'san14.host-archive-replay-adapter.v1', 'provenance': 'HISTORICAL_REVIEWED_ARCHIVE',
        'use': 'OFFLINE_ARCHIVE_REPLAY_ONLY', 'archive_created': archived_at,
        'archive': {'size': ARCHIVE_SIZE, 'sha256': ARCHIVE_SHA, 'node': dict(NODE),
                    'force_id': 12, 'ruler_id': 666, 'game_build_sha256': GAME_SHA},
        'historical_attachment': identity,
        'historical_save_return_observed': True, 'historical_save_request_count': 1,
        'historical_publish_write_count': 1, 'historical_native_full_reads': 2,
        'historical_native_bytes_matched': True,
        'source_evidence': {key: {'workspace_relative_path': 'work/mod_research/' + path,
            'size': size, 'sha256': digest} for key, (path, size, digest) in SOURCES.items()},
        'coverage': {'historical_sampled_object_records': 783, 'historical_hex_serialized_bytes': 242000,
                     'historical_known_fields_unchanged': True, 'full_world_verified': False},
        'current_A_world_verified': False, 'current_attachment_verified': False,
        'full_world_verified': False, 'native_load_authorized': False, 'native_gameplay_enabled': False,
        'native_save_called_this_read': False, 'game_access': False, 'old_entry_reenabled': False,
        'limits': ['Historical evidence only; no current room/epoch/cut is attested.',
                   'Two past native reads do not identify a future native load.',
                   'Known field equality is incomplete world coverage.',
                   'No input exclusion, display cover, or second-game readiness proof.',
                   'Repeated reads/package transfers do not repeat a native save or consume a new save intent.'],
    }
    return ArchivedHostExport(blobs['archive'], canonical(receipt))


def load_reviewed_host_export():
    """Read only the reviewed fixed workspace bundle; never follow receipt paths."""
    try:
        blobs = {key: _read_workspace_file(HERE / path, size, digest)
                 for key, (path, size, digest) in SOURCES.items()}
        return _validated_bundle(blobs)
    except OSError as exc:
        raise HostExportError('workspace_evidence_unavailable') from exc
