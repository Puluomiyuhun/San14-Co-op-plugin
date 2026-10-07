"""Data-only candidates for a successor C++ load Session; never native Config.

Two distinct captures are required: current local admission and the newly read
checkpoint's Title identity boundary. Capture hashes/challenges are independently
supplied expectations, not authentication or a native scheduling fence. There is
no clock/process/filesystem access and no reuse/reset/Arm operation here.
"""
from copy import deepcopy

import checkpoint_repeat_load_profile as p

SCHEMA = 'san14.repeat-native-parameters.v1'
ADMISSION_SCHEMA = 'san14.repeat-admission-capture.v1'
TITLE_SCHEMA = 'san14.repeat-title-capture.v1'
MAX_POINTER = 0x00007fffffffffff


def same(a, b):
    return p.snapshot_sha256(a) == p.snapshot_sha256(b)


def pointer(value, label, aligned=True):
    p.uint(value, 64, label, 1)
    p.need(0x10000 <= value <= MAX_POINTER and (not aligned or value % 8 == 0), label + ': pointer range/alignment')


def capture_binding(capture, expected, request, schema):
    p.shape(expected, 'sha256 capture_id challenge after_sequence', 'expected_capture')
    for key in ('sha256', 'capture_id', 'challenge'):
        p.hx(expected[key], 64, 'expected_capture.' + key)
    p.uint(expected['after_sequence'], 64, 'after_sequence')
    p.need(capture['schema'] == schema, 'Wrong capture schema')
    p.hx(capture['capture_id'], 64, 'capture_id')
    p.hx(capture['challenge'], 64, 'challenge')
    p.uint(capture['sequence'], 64, 'sequence', 1)
    p.need(capture['sequence'] > expected['after_sequence'], 'Capture predates independently issued boundary')
    p.need(capture['capture_id'] == expected['capture_id'] and capture['challenge'] == expected['challenge'],
           'Capture id/challenge mismatch')
    p.need(p.snapshot_sha256(capture) == expected['sha256'], 'Capture content differs from independent expectation')
    p.need(capture['profile_sha256'] == p.snapshot_sha256(request), 'Capture belongs to another load profile')
    p.need(same(capture['binding'], request['transaction']), 'Capture native transaction binding mismatch')
    p.need(same(capture['process'], {k: request['current'][k] for k in ('attachment_id', 'pid', 'birth', 'base')}),
           'Capture process attachment mismatch')
    p.need(capture['game_build_sha256'] == p.GAME_SHA256, 'Capture unsupported build')


def prepare(request, *, expected_current, expected_offer, expected_transaction, capture, expected_capture):
    """Map fresh current-world observations to explicit successor field names.

    expected_capture must originate from the locally issued capture operation,
    not be reconstructed from a remote reply. Sequence/challenge metadata only
    rejects stale packages; native callback-time guards still recheck every read.
    """
    plan = p.build_plan(request, expected_current=expected_current, expected_offer=expected_offer,
                        expected_transaction=expected_transaction)
    p.shape(capture, 'schema capture_id challenge sequence profile_sha256 binding process game_build_sha256 date identity phase pointers quiet rng storage', 'admission_capture')
    capture_binding(capture, expected_capture, request, ADMISSION_SCHEMA)
    p.need(same(capture['date'], request['current']['date']) and same(capture['identity'], request['current']['identity'])
           and capture['phase'] == 'PLANNING_BOUNDARY', 'Fresh local date/identity/phase mismatch')
    quiet = {'stack_count': 5, 'queue_count': 0, 'user_phase': 2, 'cache_mode': 0,
             'cache_pending': -1, 'cache_busy': 0}
    p.need(same(capture['quiet'], quiet), 'Admission is not the supported quiet native shape')
    ptr = capture['pointers']
    p.shape(ptr, 'states root world cache keyboard toolbar panel stack stack_capacity queue queue_capacity', 'pointers')
    p.need(type(ptr['states']) is list and len(ptr['states']) == 5, 'Five formal states required')
    for n, address in enumerate(ptr['states']):
        pointer(address, 'state.' + str(n))
    p.need(len(set(ptr['states'])) == 5, 'Formal states cannot alias one another')
    for key in ('root', 'world', 'cache', 'keyboard', 'toolbar', 'panel', 'stack'):
        pointer(ptr[key], key)
    p.uint(ptr['stack_capacity'], 32, 'stack_capacity', 6)
    p.need(ptr['stack_capacity'] <= 4096, 'Unbounded stack capacity')
    # Current proven queue factory requires the genuinely empty vector. A
    # future nonempty-capacity policy must be separately implemented/reviewed.
    p.need(type(ptr['queue']) is int and ptr['queue'] == 0 and
           type(ptr['queue_capacity']) is int and ptr['queue_capacity'] == 0, 'Only initial empty native queue supported')
    p.uint(capture['rng'], 32, 'rng')
    storage = capture['storage']
    p.shape(storage, 'storage vtable original_read_method binding_sha256', 'storage')
    for key in ('storage', 'vtable'):
        pointer(storage[key], 'storage.' + key)
    pointer(storage['original_read_method'], 'original_read_method', False)
    p.hx(storage['binding_sha256'], 64, 'storage binding_sha256')
    base, attempt = request['current']['base'], request['transaction']['native_attempt']
    offer = request['offer']
    p.uint(offer['slot'], 31, 'native LONG slot')
    target = {'name': offer['basename'], 'slot': offer['slot'], 'size': offer['save']['size'],
              'sha256': offer['save']['sha256']}
    date = capture['date']
    boundary = {'base': base, 'states': deepcopy(ptr['states']), 'menu': 0,
                **{k: ptr[k] for k in ('root', 'world', 'cache', 'keyboard')},
                'attempt': attempt, 'expectedRng': capture['rng'], 'year': date[0], 'month': date[1],
                'day': date[2], 'force': capture['identity']['force_id']}
    result = {'schema': SCHEMA, 'request': deepcopy(request), 'profile_sha256': plan['profile_sha256'],
              'generation_binding': deepcopy(request['transaction']), 'admission_capture': {
                  'id': capture['capture_id'], 'challenge': capture['challenge'], 'sequence': capture['sequence'],
                  'sha256': expected_capture['sha256']},
              'request_candidate': {'boundary': boundary, 'ownerBinding': request['transaction']['owner_binding'],
                  'target': deepcopy(target), 'runtime_graph': deepcopy(ptr), 'quiet': deepcopy(quiet),
                  'storage_binding_sha256': storage['binding_sha256']},
              'bytes_candidate': {'base': base, 'attemptToken': attempt, 'storage': storage['storage'],
                  'storageVtable': storage['vtable'], 'readMethod': storage['original_read_method'], 'target': deepcopy(target)},
              'lifecycle_candidate': {'base': base, 'attemptToken': attempt, 'target': deepcopy(target),
                  'bytes_observer': 'bind same-generation observer object in C++ owner'},
              'identity_candidate': {'base': base, 'attemptToken': attempt, 'ownerBinding': request['transaction']['owner_binding'],
                  'date': deepcopy(offer['date']), 'source': deepcopy(offer['incoming_identity']),
                  'target': deepcopy(offer['viewer_identity']), 'native_slot': offer['slot'],
                  'source_force_47': None, 'target_force_47': None, 'resolved_pair': None, 'control_after': 1,
                  'requires_new_title_capture': True},
              'planning_candidate': {'base': base, 'attempt': attempt, 'epoch': request['transaction']['native_epoch'],
                  'persistentRootState': ptr['states'][0], 'persistentMotorState': ptr['states'][1],
                  'previousUser': ptr['states'][4], 'date': deepcopy(offer['date']),
                  'identity': deepcopy(offer['viewer_identity']), 'target': deepcopy(target), 'control_mode': 1},
              'live_authority': False, 'native_config_generated': False, 'room_ready': False,
              'world_verified': False, 'input_exclusion_proved': False, 'automatic_retry': False,
              'blockers': deepcopy(plan['blockers']) + [
                  'Resolve source/target pointers and force+0x47 only from same-generation newly read Title world',
                  'C++ owner must allocate immutable per-generation observers and bind storage/callback/object ownership',
                  'force+0x47 semantics and nonfixture values still need native-profile validation; capturing a byte is not that proof',
                  'Local paths and three CREATE_NEW durable intents remain owner-local allocations',
                  'Native slots, memory ranges, storage methods and input boundary need actual callback-time guards']}
    result['candidate_sha256'] = p.snapshot_sha256(result)
    return result


def _validate_candidate(candidate):
    p.need(type(candidate) is dict and candidate.get('schema') == SCHEMA, 'Invalid candidate')
    copy = deepcopy(candidate)
    digest = copy.pop('candidate_sha256', None)
    p.need(digest == p.snapshot_sha256(copy), 'Candidate content changed')
    for flag in ('live_authority', 'native_config_generated', 'room_ready', 'world_verified',
                 'input_exclusion_proved', 'automatic_retry'):
        p.need(candidate.get(flag) is False, 'Candidate must not confer authority: ' + flag)
    return candidate['request']


def bind_new_title(candidate, capture, *, expected_candidate_sha256, expected_capture, expected_lifecycle):
    """Resolve identity fields after actual checkpoint read in the new world.

    expected_lifecycle is an independently checked native receipt projection,
    never a field derived from this capture. This function only compares data;
    receipt provenance, memory lifetime and callback ownership remain external.
    Rebinding an already resolved candidate is rejected.
    """
    request = _validate_candidate(candidate)
    p.hx(expected_candidate_sha256, 64, 'expected_candidate_sha256')
    p.need(candidate['candidate_sha256'] == expected_candidate_sha256, 'Candidate differs from independently retained preparation')
    p.need(candidate['identity_candidate']['requires_new_title_capture'] is True, 'Title already resolved; no rebinding')
    p.shape(capture, 'schema capture_id challenge sequence profile_sha256 binding process game_build_sha256 date root world title source target world_force control_before lifecycle', 'title_capture')
    capture_binding(capture, expected_capture, request, TITLE_SCHEMA)
    p.need(capture['capture_id'] != candidate['admission_capture']['id'] and
           capture['challenge'] != candidate['admission_capture']['challenge'] and
           capture['sequence'] > candidate['admission_capture']['sequence'], 'Title requires a new later capture operation')
    p.shape(expected_lifecycle, 'attempt generation attachment_id checkpoint_sha256 checkpoint_size title completion_call native_result phase', 'expected_lifecycle')
    p.need(same(capture['lifecycle'], expected_lifecycle), 'Title is not bound to independently checked lifecycle')
    life = expected_lifecycle
    for key in ('attempt', 'generation'):
        p.uint(life[key], 64, 'lifecycle.' + key, 1)
    p.uint(life['checkpoint_size'], 31, 'checkpoint_size', 1)
    for key in ('attachment_id', 'checkpoint_sha256'):
        p.hx(life[key], 64, 'lifecycle.' + key)
    p.need(life['attempt'] == request['transaction']['native_attempt'] and
           life['generation'] == request['transaction']['generation'] and
           life['attachment_id'] == request['current']['attachment_id'], 'Stale lifecycle generation')
    p.need(life['checkpoint_sha256'] == request['offer']['save']['sha256'] and
           life['checkpoint_size'] == request['offer']['save']['size'], 'Lifecycle loaded different bytes')
    p.uint(life['completion_call'], 64, 'completion_call', 1)
    p.need(type(life['native_result']) is int and life['native_result'] == 1 and
           type(life['phase']) is int and life['phase'] in (13, 15), 'Incomplete title/lifecycle phase')
    for key in ('root', 'world', 'title'):
        pointer(capture[key], key)
    p.need((capture['title'] + 0x4a0) % 16 == 0, 'Title selection pair requires native 16-byte CAS alignment')
    p.need(life['title'] == capture['title'], 'Different title instance')
    p.need(same(capture['date'], request['offer']['date']) and
           type(capture['world_force']) is int and capture['world_force'] == request['offer']['incoming_identity']['force_id'],
           'New world is not incoming checkpoint A')
    p.uint(capture['control_before'], 8, 'control_before')
    addresses = []
    for role, identity_key in (('source', 'incoming_identity'), ('target', 'viewer_identity')):
        row = capture[role]
        p.shape(row, 'identity force person district force_47', 'new_title.' + role)
        p.need(same(row['identity'], request['offer'][identity_key]), 'Title identity differs from incoming/viewer binding')
        for key in ('force', 'person', 'district'):
            pointer(row[key], role + '.' + key)
            addresses.append(row[key])
        p.uint(row['force_47'], 8, role + '.force_47')
    p.need(len(set(addresses)) == len(addresses), 'Different identity objects alias')
    # No numerical comparison against old-world pointers: allocator address
    # reuse is legal. This capture's phase/lifecycle/binding owns these reads.
    result = deepcopy(candidate)
    result.pop('candidate_sha256')
    identity = result['identity_candidate']
    identity.update(source_force_47=capture['source']['force_47'], target_force_47=capture['target']['force_47'],
        resolved_pair={role: {key: capture[role][key] for key in ('force', 'person', 'district')} for role in ('source', 'target')},
        requires_new_title_capture=False, new_root=capture['root'], new_world=capture['world'], title=capture['title'],
        control_before=capture['control_before'], completion_call=life['completion_call'])
    result['title_capture'] = {'id': capture['capture_id'], 'sequence': capture['sequence'],
                               'sha256': expected_capture['sha256'], 'challenge': capture['challenge']}
    result['blockers'].remove('Resolve source/target pointers and force+0x47 only from same-generation newly read Title world')
    result['blockers'].append('Resolved title candidate is only valid at its owned callback; revalidate pair before CAS and never export it as a reusable pointer cache')
    result['candidate_sha256'] = p.snapshot_sha256(result)
    return result


CPP_FIELD_MAPPING = {
    'request_candidate.boundary': 'checkpoint_load_input_boundary::Config exact field names; current local world only',
    'request_candidate.target': 'NEW immutable target profile needed by Request; replaces .cpp constants',
    'bytes_candidate.target': 'NEW immutable file profile; actual FileRead length/name/digest',
    'lifecycle_candidate.target': 'NEW shared profile; validate slot and frozen bytes against same target',
    'identity_candidate': 'NEW profile plus deferred Title resolution; no pointers from admission world',
    'planning_candidate': 'successor planning Config plus incoming date/target identity and bytes profile',
    'storage_binding_sha256': 'reference to independently validated module/endpoint binding, NOT an Api function pointer',
    'resolved_pair': 'same-generation callback-only identity objects; force+0x47 from current incoming world observation',
}

PARAMETER_TYPES = {
    'base/states/root/world/cache/keyboard/toolbar/panel/stack/readMethod': 'uint64 / uintptr_t; local only, never remote authority',
    'attempt/attemptToken/epoch/generation': 'uint64; never parse through an imprecise floating-point JSON number',
    'year': 'uint16', 'month/day/force/control_mode/force_47': 'uint8',
    'expectedRng': 'uint32', 'target.slot': 'nonnegative int32 (native LONG CAS)',
    'target.size': 'positive int32 (native FileRead argument/result)',
    'target.name': 'ASCII basename only; known slot 63 maps exactly to svdexccSC03.s14',
    'sha256/ownerBinding': '32 bytes represented as 64 lowercase hexadecimal characters',
    'source/target identity': 'IDs until same-generation Title callback resolves force/person/district objects',
    'callbacks/context/observer objects/Api': 'NOT serialized; must be owned and bound within resident C++ session',
    'localPath/installIntent/requestIntent/identityIntent': 'NOT peer-provided; owner allocates absolute paths and durable unique intents',
}
