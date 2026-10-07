"""Pure data preparation for a future repeatable native loader.

No filesystem/process/native imports or effects. Caller-supplied observations
and accepted offers are independent expectations, not signatures or authority.
Do not feed this output into the frozen, single-install Config ABI.
"""
from copy import deepcopy
import hashlib
import re

from checkpoint_session_configuration import GAME_SHA256, snapshot_sha256

SCHEMA = 'san14.repeat-load-profile.v1'
FIXED_SHA = '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
FIXED_A = {'force_id': 12, 'ruler_id': 666, 'district_id': 11}
FIXED_B = {'force_id': 2, 'ruler_id': 952, 'district_id': 2}


class ProfileError(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise ProfileError(why)


def shape(obj, keys, label):
    need(type(obj) is dict and set(obj) == set(keys.split()), label + ': exact schema required')


def uint(n, bits, label, minimum=0):
    need(type(n) is int and minimum <= n < 2**bits, label + ': unsigned integer required')


def hx(s, chars, label):
    need(type(s) is str and re.fullmatch('[0-9a-f]{%d}' % chars, s) is not None
         and int(s, 16) != 0, label + ': nonzero canonical hex required')


def ident(s, label):
    need(type(s) is str and re.fullmatch('[A-Za-z0-9_-]{1,128}', s) is not None, label + ': invalid identifier')


def date(d, label):
    need(type(d) is list and len(d) == 3, label + ': year/month/day list required')
    uint(d[0], 16, label + '.year', 1)
    need(type(d[1]) is int and 1 <= d[1] <= 12 and type(d[2]) is int and d[2] in (1, 11, 21),
         label + ': settled ten-day boundary required')
    return (d[0] * 12 + d[1] - 1) * 3 + (d[2] - 1) // 10


def identity(i, label):
    shape(i, 'force_id ruler_id district_id', label)
    # Storage field widths only; no claim that every value is a live faction.
    uint(i['force_id'], 8, label + '.force_id')
    uint(i['ruler_id'], 16, label + '.ruler_id')
    uint(i['district_id'], 8, label + '.district_id')


def build_plan(request, *, expected_current, expected_offer, expected_transaction):
    """Validate three separate sources and return a non-executable wiring plan.

    current: local read-only observation; offer: accepted host checkpoint plus
    room assignment; transaction: newly allocated local attempt binding. Caller
    must obtain these independently. Echoing request fields is not validation.
    No pointer or seed from an earlier load is admitted into this data schema.
    """
    shape(request, 'schema game_build_sha256 current offer transaction', 'request')
    need(request['schema'] == SCHEMA and request['game_build_sha256'] == GAME_SHA256, 'Unsupported schema/build')
    cur, offer, tx = request['current'], request['offer'], request['transaction']
    shape(cur, 'attachment_id pid birth base date identity phase', 'current')
    hx(cur['attachment_id'], 64, 'attachment_id')
    uint(cur['pid'], 32, 'pid', 1)
    for key in ('birth', 'base'):
        uint(cur[key], 64, key, 1)
    need(cur['base'] % 0x10000 == 0, 'base must be image aligned')
    current_date = date(cur['date'], 'current.date')
    identity(cur['identity'], 'current.identity')
    need(cur['phase'] == 'PLANNING_BOUNDARY', 'Local map must be settled')
    shape(offer, 'checkpoint_id scope_sha256 room_epoch period cut save date incoming_identity viewer_identity source_player recipient slot basename', 'offer')
    for key in ('checkpoint_id', 'scope_sha256'):
        hx(offer[key], 64, key)
    hx(offer['room_epoch'], 32, 'room_epoch')
    uint(offer['period'], 64, 'period', 1)
    shape(offer['cut'], 'sequence prefix_sha256', 'cut')
    uint(offer['cut']['sequence'], 53, 'cut.sequence')
    hx(offer['cut']['prefix_sha256'], 64, 'cut.prefix_sha256')
    shape(offer['save'], 'sha256 size', 'save')
    hx(offer['save']['sha256'], 64, 'save.sha256')
    uint(offer['save']['size'], 31, 'save.size', 1)
    incoming_date = date(offer['date'], 'offer.date')
    need(0 <= incoming_date - current_date <= 1, 'Checkpoint is old or skips a local period')
    # B may already have simulated to the same boundary, or be waiting one
    # boundary behind. Coordinator validates exact next_node against its seal.
    identity(offer['incoming_identity'], 'incoming_identity')
    identity(offer['viewer_identity'], 'viewer_identity')
    need(offer['source_player'] == 'A' and offer['recipient'] == 'B', 'Only A-authoritative B recipient supported')
    need(offer['incoming_identity']['force_id'] != offer['viewer_identity']['force_id'],
         'Already-viewer checkpoint needs a separately verified no-CAS identity path')
    uint(offer['slot'], 32, 'slot')
    need(type(offer['basename']) is str and re.fullmatch('svdex[A-Za-z0-9]{1,16}\\.s14', offer['basename']), 'Invalid save leaf')
    if offer['slot'] == 63:
        need(offer['basename'] == 'svdexccSC03.s14', 'Known slot/name pairing mismatch')
    if offer['basename'] == 'svdexccSC03.s14':
        need(offer['slot'] == 63, 'Known name/slot pairing mismatch')
    shape(tx, 'attachment_id attempt_id native_attempt native_epoch generation owner_binding previous_attempt_id', 'transaction')
    hx(tx['attachment_id'], 64, 'transaction.attachment_id')
    hx(tx['owner_binding'], 64, 'owner_binding')
    ident(tx['attempt_id'], 'attempt_id')
    for key in ('native_attempt', 'native_epoch', 'generation'):
        uint(tx[key], 64, key, 1)
    need(tx['attachment_id'] == cur['attachment_id'], 'Foreign process attachment')
    if tx['previous_attempt_id'] is not None:
        ident(tx['previous_attempt_id'], 'previous_attempt_id')
        need(tx['previous_attempt_id'] != tx['attempt_id'], 'Attempt replay')
        need(cur['identity']['force_id'] == offer['viewer_identity']['force_id'],
             'Repeat must begin in the assigned local B force')
        # Ruler/district may legitimately change in A's authoritative turn;
        # bind both values independently instead of forcing old==new.
    for actual, expected, name in ((cur, expected_current, 'current'), (offer, expected_offer, 'offer'),
                                   (tx, expected_transaction, 'transaction')):
        need(snapshot_sha256(actual) == snapshot_sha256(expected), name + ': independently bound expectation mismatch')

    frozen = (cur['identity'] == FIXED_A and cur['date'] == [203, 8, 11]
              and offer['incoming_identity'] == FIXED_A and offer['viewer_identity'] == FIXED_B
              and offer['date'] == [203, 8, 11] and offer['slot'] == 63
              and offer['save'] == {'sha256': FIXED_SHA, 'size': 274880}
              and tx['previous_attempt_id'] is None)
    blockers = ['Persistent owner generation routing and retirement are not proven by this profile',
                'Fresh callback-time pointers, RNG, storage, input boundary and hook ownership required',
                'Native profile parameterization must be compiled and independently tested',
                'Room receipt needs complete world/adapter verification; native planning alone is insufficient']
    if offer['slot'] != 63:
        blockers.append('This slot-to-native-name mapping has not been verified; never derive it by arithmetic')
    return {'schema': 'san14.repeat-load-plan.v1', 'profile_sha256': snapshot_sha256(request),
            'binding': deepcopy(tx), 'room_binding': {k: deepcopy(offer[k]) for k in
                ('checkpoint_id', 'scope_sha256', 'room_epoch', 'period', 'cut')},
            'preload_local': {'date': deepcopy(cur['date']), 'identity': deepcopy(cur['identity'])},
            'after_native_read_before_identity': {'date': deepcopy(offer['date']), 'identity': deepcopy(offer['incoming_identity'])},
            'after_identity_planning': {'date': deepcopy(offer['date']), 'identity': deepcopy(offer['viewer_identity'])},
            'identity_cas': {'expected': deepcopy(offer['incoming_identity']), 'replacement': deepcopy(offer['viewer_identity'])},
            'file_binding': {k: deepcopy(offer[k]) for k in ('save', 'slot', 'basename')},
            'matches_frozen_data_profile': frozen, 'live_authority': False, 'native_config_generated': False,
            'room_ready': False, 'world_verified': False, 'automatic_retry': False, 'blockers': blockers}


# Specific, frozen-source anchors. audit_sources consumes caller-supplied text;
# this module never opens a file. A changed source requires a new audit.
AUDIT_ANCHORS = (
    ('checkpoint_complete_live_owner_v2.cpp', 'InterlockedCompareExchange(&once,1,0)', 'single_install_owner'),
    ('checkpoint_complete_live_owner_v2.cpp', 'L"svdexccSC03.s14"', 'local_save_leaf'),
    ('checkpoint_complete_live_owner_v2.cpp', 'b.expectedRng=c.rng', 'new_request_boundary_rng'),
    ('checkpoint_complete_live_owner_v2.cpp', 'checkpoint_cc_load_observer::TargetSha256', 'intent_and_stamp_digest'),
    ('checkpoint_load_input_boundary.h', 'year=203', 'local_date_defaults'),
    ('checkpoint_load_input_boundary.h', 'force=12', 'local_identity_default'),
    ('checkpoint_live_runtime_guards_v2.cpp', 'c.initial.force!=12', 'initial_guard_identity'),
    ('checkpoint_live_runtime_guards_v2.cpp', 'c.world+0x3a)!=12', 'preload_current_identity'),
    ('checkpoint_live_runtime_guards_v2.cpp', 'world+0x34)!=203', 'loaded_checkpoint_date'),
    ('checkpoint_live_runtime_guards_v2.cpp', 'force=targetPair?2:12', 'loaded_vs_target_pair'),
    ('checkpoint_live_runtime_guards_profile.h', 'checkpoint_sha[32]', 'fixed_content_digest'),
    ('checkpoint_load_request_commit.cpp', 'targetSize=274880', 'preflight_file_size'),
    ('checkpoint_load_request_commit.cpp', 'targetSha[32]', 'preflight_file_digest'),
    ('checkpoint_load_request_commit.cpp', 'InterlockedCompareExchange(pending,63,-1)', 'native_request_slot'),
    ('checkpoint_cc_load_observer.h', 'TargetSlot=63,TargetSize=274880', 'actual_read_target'),
    ('checkpoint_cc_load_observer.cpp', 'TargetSha256[32]', 'actual_read_digest'),
    ('checkpoint_cc_load_lifecycle.cpp', 'title+0x47C)==63', 'lifecycle_slot'),
    ('checkpoint_title_identity_adapter.cpp', 'world+0x34)!=203', 'incoming_checkpoint_date'),
    ('checkpoint_title_identity_adapter.cpp', 'root+0xDCA0+12*8', 'incoming_source_identity'),
    ('checkpoint_title_identity_adapter.cpp', 'source.force+0x47)!=6', 'scenario_specific_force_fields'),
    ('checkpoint_title_identity_adapter.cpp', '952,2,2', 'viewer_ruler_and_district'),
    ('checkpoint_identity_pair_commit.cpp', 'equal(i.source,i.target)', 'same_identity_cas_rejected'),
    ('checkpoint_forward_planning_observer_v2.cpp', 'world+0x34)!=203', 'new_planning_checkpoint_date'),
    ('checkpoint_forward_planning_observer_v2.cpp', 'root+0x148+952*8', 'new_planning_viewer_identity'),
    ('checkpoint_complete_live_capture.py', 'force_id\']==12', 'launcher_initial_local_identity'),
)


def audit_sources(sources):
    need(type(sources) is dict, 'Source text mapping required')
    rows = []
    for filename, anchor, purpose in AUDIT_ANCHORS:
        text = sources.get(filename)
        need(type(text) is str, 'Missing source: ' + filename)
        lines = [n for n, line in enumerate(text.splitlines(), 1) if anchor in line]
        need(bool(lines), 'Audit anchor changed: ' + filename + ': ' + anchor)
        rows.append({'file': filename, 'lines': lines, 'anchor': anchor, 'purpose': purpose,
                     'source_text_sha256': hashlib.sha256(text.encode()).hexdigest()})
    return {'schema': 'san14.repeat-profile-audit.v1', 'anchors': rows, 'live_authority': False}


NETWORK_MAPPING = {
    'offer.checkpoint_id': 'CheckpointPackage.checkpoint_id (digest of complete manifest; NOT save SHA)',
    'offer.save': 'Verified CheckpointReceiver manifest.parts[world.s14] size/sha256 plus verified_parts bytes',
    'offer.date': 'manifest.node year/month/day, checked against coordinator next_node',
    'offer.room_epoch': 'manifest.epoch, a room string; never substitute native uint64 epoch',
    'offer.period/cut/scope_sha256': 'manifest fields, independently checked against coordinator seal/scope',
    'offer.viewer_identity': 'locked scope.bindings.B force plus freshly validated target ruler/district from incoming world',
    'offer.incoming_identity': 'decoded verified incoming save A identity, not local B identity or file name',
    'current': 'fresh local process observation tied to pid+birth+base+attachment',
    'transaction': 'local unique durable attempt allocation, never supplied by remote peer',
    'room_ack': 'NOT produced: finish native load then require full world/adapter receipt before acknowledge',
}
