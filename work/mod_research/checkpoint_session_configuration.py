"""Data-only projection of an explicitly supplied, hash-pinned memory archive.

No process, file, ctypes, native call, import of game readers, or authorization.
The output is an incomplete wiring manifest, never a native Config/Arm permit.
Addresses are derived from archived bytes; callbacks and future objects stay
unresolved. Even a complete snapshot cannot prove current pointer lifetime.
"""
import hashlib
import json
import re
import struct

SCHEMA = 'san14.session-config-snapshot.v1'
GAME_SHA256 = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
TARGET_SHA256 = '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
TARGET = {'basename': 'svdexccSC03.s14', 'slot': 63, 'size': 274880,
          'sha256': TARGET_SHA256, 'date': [203, 8, 11],
          'source_force': 12, 'source_ruler': 666, 'source_district': 11,
          'target_force': 2, 'target_ruler': 952, 'target_district': 2}
STATE_NAMES = ('CRootState', 'CMotorGameState', 'CGameState',
               'CStrategyState', 'CUserStrategyState')
# Extracted from the supported archived image, not any fixture layout.
HOOK_PROFILE = (
    ('User', 0x12CC4D0, 0x3F9B00),
    ('Menu', 0x12DB4E8, 0x4AA200),
    ('Game', 0x12CC9E0, 0x3F8140),
    ('Load', 0x12DBD90, 0x4A85C0),
    ('Callable', 0x138E8D0, 0x4FABC0),
)
SPAN_MINIMUM = {'user': 0x668, 'toolbar': 0x8C, 'game': 0x488,
                'panel': 0x1F8, 'manager': 0x50, 'stack': 0x30,
                'queue': 0x10, 'load_cache': 0x3F4}
MAX_PTR = 0x00007FFFFFFFFFFF


class ConfigurationError(ValueError):
    pass


def _require(ok, message):
    if not ok:
        raise ConfigurationError(message)


def _uint(value, bits, name, nonzero=False):
    _require(type(value) is int and (1 if nonzero else 0) <= value < 2**bits,
             name + ': strict unsigned integer required')
    return value


def _hex(value, length, name):
    _require(type(value) is str and re.fullmatch('[0-9a-f]{%d}' % length, value),
             name + ': canonical lowercase hexadecimal required')
    return value


def _pointer(value, name):
    _uint(value, 64, name, True)
    _require(0x10000 <= value <= MAX_PTR and value % 8 == 0, name + ': pointer range/alignment')
    return value


def snapshot_sha256(snapshot):
    """Canonical JSON digest, distinct from a pretty-printed file SHA."""
    try:
        raw = json.dumps(snapshot, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (ValueError, TypeError) as exc:
        raise ConfigurationError('snapshot is not canonical JSON') from exc
    return hashlib.sha256(raw).hexdigest()


class _Reads:
    def __init__(self, reads):
        _require(type(reads) is list and len(reads) <= 256, 'reads must be bounded list')
        self.rows = []
        labels = set()
        total = 0
        for row in reads:
            _require(type(row) is dict and set(row) == {'label', 'address', 'data_hex'}, 'read row schema')
            label = row['label']
            _require(type(label) is str and re.fullmatch('[A-Za-z0-9_.-]{1,96}', label)
                     and label not in labels, 'read label invalid/duplicate')
            labels.add(label)
            address = _uint(row['address'], 64, label + '.address')
            raw = row['data_hex']
            if address == 0 and raw == '' and label == 'queue':
                continue  # Explicit empty-vector observation, never a readable Span.
            _require(type(raw) is str and re.fullmatch('(?:[0-9a-f]{2})+', raw)
                     and len(raw) <= 262144, label + ': invalid/big bytes')
            data = bytes.fromhex(raw)
            _require(address >= 0x10000 and address + len(data) - 1 <= MAX_PTR, 'read address range')
            total += len(data)
            _require(total <= 2**20, 'snapshot byte limit')
            self.rows.append((address, address + len(data), data, label))
        self.rows.sort()
        for a, b in zip(self.rows, self.rows[1:]):
            _require(a[1] <= b[0], 'overlapping reads are ambiguous; supply one disjoint capture')

    def raw(self, address, size):
        if address is None:
            return None
        for begin, end, data, label in self.rows:
            if begin <= address and address + size <= end:
                return data[address-begin:address-begin+size]
        return None

    def integer(self, address, size, signed=False):
        raw = self.raw(address, size)
        return None if raw is None else int.from_bytes(raw, 'little', signed=signed)


def build_manifest(snapshot, *, expected_attachment, expected_snapshot_sha256, attempt=None):
    """Project observed Config fields; list every unavailable native dependency.

    expected_attachment is the exact dict {id,pid,birth,base,epoch} approved by
    the caller, never inferred from an old receipt. Optional attempt is exactly
    {token,owner_binding,attempt_id,intent_id,checkpoint_id}; identifiers are
    passed through without truncating them to the native 64-bit token. It is a
    new transaction binding, not a durable-intent or ownership proof.
    """
    _require(type(snapshot) is dict, 'snapshot object required')
    _require(set(snapshot) <= {'schema', 'game_build_sha256', 'attachment', 'capture',
                             'reads', 'storage_binding', 'atomic_snapshot',
                             'callback_boundary_observed', 'game_writes', 'authorize_arm'}, 'unknown snapshot keys')
    for key in ('atomic_snapshot', 'callback_boundary_observed', 'authorize_arm'):
        if key in snapshot:
            _require(snapshot[key] is False, key + ': no authorization/atomicity upgrade accepted')
    if 'game_writes' in snapshot:
        _require(type(snapshot['game_writes']) is int and snapshot['game_writes'] == 0, 'snapshot game_writes')
    _require(snapshot.get('schema') == SCHEMA, 'unsupported snapshot schema')
    _require(snapshot.get('game_build_sha256') == GAME_SHA256, 'unsupported game build')
    _hex(expected_snapshot_sha256, 64, 'expected_snapshot_sha256')
    _require(snapshot_sha256(snapshot) == expected_snapshot_sha256, 'snapshot digest mismatch')
    attachment = snapshot.get('attachment')
    _require(type(attachment) is dict and set(attachment) == {'id', 'pid', 'birth', 'base', 'epoch'}, 'attachment schema')
    _hex(attachment['id'], 64, 'attachment.id')
    _require(int(attachment['id'], 16) != 0, 'zero attachment')
    _uint(attachment['pid'], 32, 'pid', True)
    for key in ('birth', 'epoch'):
        _uint(attachment[key], 64, key, True)
    base = _pointer(attachment['base'], 'base')
    _require(type(expected_attachment) is dict and
             snapshot_sha256(attachment) == snapshot_sha256(expected_attachment), 'attachment mismatch')
    capture = snapshot.get('capture')
    _require(type(capture) is dict and set(capture) == {'source', 'sequence', 'captured_utc'}, 'capture schema')
    _require(capture['source'] == 'root-read-only', 'fixture/non-root provenance rejected')
    _uint(capture['sequence'], 64, 'capture.sequence', True)
    _require(type(capture['captured_utc']) is str and
             re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)', capture['captured_utc']), 'capture timestamp')
    if attempt is not None:
        _require(type(attempt) is dict and set(attempt) == {'token', 'owner_binding', 'attempt_id', 'intent_id', 'checkpoint_id'}, 'attempt schema')
        _uint(attempt['token'], 64, 'attempt.token', True)
        for key in ('owner_binding', 'checkpoint_id'):
            _hex(attempt[key], 64, key)
        _require(int(attempt['owner_binding'], 16) != 0, 'empty owner binding')
        for key in ('attempt_id', 'intent_id'):
            _require(type(attempt[key]) is str and re.fullmatch('[A-Za-z0-9_-]{1,128}', attempt[key]), key + ': invalid ID')
        attempt = json.loads(json.dumps(attempt))

    reads = _Reads(snapshot.get('reads'))
    missing, conflicts, observations = [], [], {}

    def observed(name, address, size=8, signed=False):
        value = reads.integer(address, size, signed)
        if value is None:
            missing.append({'field': name, 'address': address, 'size': size})
        else:
            observations[name] = {'address': address, 'size': size, 'value': value}
        return value

    def ptr(name, address):
        value = observed(name, address)
        return None if value is None else _pointer(value, name)

    def check(name, address, want, size=8, signed=False):
        value = observed(name, address, size, signed)
        if value is not None and value != want:
            conflicts.append({'field': name, 'observed': value, 'expected': want})
        return value

    manager = base + 0x19E7310
    root = ptr('root', base + 0x1FCA1E0)
    world = ptr('world', root + 0x85130 if root else None)
    cache = ptr('cache', base + 0x2025318)
    keyboard = ptr('keyboard', base + 0x1FCA0A0)
    stack = ptr('stack', manager + 0x20)
    queue = observed('queue', manager + 0x40)
    if queue:
        _pointer(queue, 'queue')
    check('manager.stack_count', manager + 0x10, 5)
    check('manager.queue_count', manager + 0x30, 0)
    # This is diagnostic only. Dispatch changes it during a stable planning map.
    observed('manager.current_diagnostic', manager + 0x48)
    capacities = {key: observed('manager.' + key + '_capacity', manager + off)
                  for key, off in (('stack', 0x18), ('queue', 0x38))}
    for name, value in capacities.items():
        if value is not None:
            _require((0 if name == 'queue' else 1) <= value <= 4096, name + ' capacity outside supported bound')
    if capacities['stack'] is not None:
        _require(capacities['stack'] >= 6, 'stack cannot contain sixth menu entry')
    if queue == 0 and capacities['queue'] == 0:
        conflicts.append({'field': 'admission.initial_queue_span', 'observed': 'EMPTY_NATIVE_VECTOR',
                          'expected': 'frozen pending adapter requires a non-null readable >=0x10 queue Span',
                          'normal_native_shape': True})
    elif queue == 0 or capacities['queue'] == 0:
        conflicts.append({'field': 'manager.queue_shape', 'observed': [queue, capacities['queue']],
                          'expected': 'both zero or both nonzero'})
    states = [ptr('state.' + name, stack + i*8 if stack else None) for i, name in enumerate(STATE_NAMES)]
    for state, name in zip(states, STATE_NAMES):
        raw = reads.raw(state + 0x70 if state else None, len(name)+1)
        if raw is None:
            missing.append({'field': name + '.name', 'address': state+0x70 if state else None, 'size': len(name)+1})
        elif raw != name.encode('ascii') + b'\0':
            conflicts.append({'field': name + '.name', 'observed_hex': raw.hex(), 'expected': name})
        check(name + '.disabled', state+0x68 if state else None, 0, 4)
    game, user = states[2], states[4]
    toolbar = ptr('toolbar', user+0x478 if user else None)
    panel = ptr('panel', game+0x480 if game else None)
    for key, address, wanted in [('root.vtable', root, base+0x12AA6B0),
                                 ('world.vtable', world, base+0x12AA638),
                                 ('User.vtable', user, base+0x12CC4A8),
                                 ('Game.vtable', game, base+0x12CC9B8)]:
        check(key, address, wanted)
    check('User.phase', user+0x470 if user else None, 2, 4)
    check('User.pending', user+0x660 if user else None, 0, 4)
    check('User.menu_command', toolbar+0x88 if toolbar else None, -1, 4, True)
    for off in (0x4A8, 0x4B0, 0x4B8):
        check('User.selection.' + hex(off), user+off if user else None, 0)
    for off in (0x474, 0x478, 0x47C):
        check('Game.pending.' + hex(off), game+off if game else None, 0, 4)
    check('Game.panel_advance', panel+0x1B0 if panel else None, 0, 4)
    check('cache.pending', cache+0x3EC if cache else None, -1, 4, True)
    check('cache.secondary', cache+0x3F0 if cache else None, 0, 4)
    # The frozen pending adapter requires mode 1 BEFORE its queue operation.
    cache_mode = check('admission.initial_cache_mode', cache+8 if cache else None, 1, 4)
    date = [check('world.' + key, world+off if world else None, want, size)
            for key, off, want, size in [('year', 0x34, 203, 2), ('month', 0x36, 8, 1), ('day', 0x37, 11, 1)]]
    check('world.force', world+0x3A if world else None, 12, 1)
    check('world.planning', world+0x40 if world else None, 1, 4)
    rng = observed('global_rng', base+0x18EB8B0, 4)

    spans = {}
    addresses = dict(user=user, toolbar=toolbar, game=game, panel=panel,
                     manager=manager, stack=stack, queue=queue, load_cache=cache)
    for key, address in addresses.items():
        if key == 'queue' and queue == 0 and capacities['queue'] == 0:
            continue
        size = SPAN_MINIMUM[key]
        if key in capacities:
            if capacities[key] is None:
                missing.append({'field': 'pending.spans.' + key + '.capacity'})
                continue
            size = capacities[key] * (8 if key == 'stack' else 16)
        raw = reads.raw(address, size)
        if raw is None:
            missing.append({'field': 'pending.spans.' + key, 'address': address, 'size': size})
        else:
            spans[key] = {'address': address, 'size': size, 'captured_sha256': hashlib.sha256(raw).hexdigest(),
                          'allocation_extent_proven': False, 'current_readability_proven': False}
    ordered = sorted(spans.items(), key=lambda kv: kv[1]['address'])
    for (a, av), (b, bv) in zip(ordered, ordered[1:]):
        _require(av['address'] + av['size'] <= bv['address'], 'pending spans overlap: ' + a + '/' + b)

    hooks = []
    for i, (name, slot_rva, original_rva) in enumerate(HOOK_PROFILE):
        slot, original = base+slot_rva, base+original_rva
        got = check('hooks.' + name + '.original', slot, original)
        hooks.append({'index': i, 'name': name, 'slot': slot, 'original': original,
                      'original_observed': got, 'hook': None,
                      'hook_symbol': ('CheckpointLoadDispatchBridge' + str(i)) if i < 4 else 'CheckpointLoadWorkerBridge0'})
    storage = None
    sb = snapshot.get('storage_binding')
    if sb is None:
        missing.append({'field': 'storage_binding', 'reason': 'No old probe addresses adopted automatically'})
    else:
        _require(type(sb) is dict and set(sb) == {'holder', 'storage', 'vtable', 'exists', 'size', 'read'}, 'storage_binding schema')
        storage = {key: _pointer(value, 'storage.'+key) for key, value in sb.items()}
        for name, address, expected in [('holder', storage['holder'], storage['storage']),
                                        ('vtable', storage['storage'], storage['vtable']),
                                        ('exists', storage['vtable']+0x68, storage['exists']),
                                        ('size', storage['vtable']+0x78, storage['size']),
                                        ('read', storage['vtable']+8, storage['read'])]:
            check('storage.'+name, address, expected)
        check('storage.context_token', base+0x18D08B8, base+0x2FCB90)
        version = b'STEAMREMOTESTORAGE_INTERFACE_VERSION014\0'
        raw = reads.raw(base+0x12AA6B8, len(version))
        if raw is None:
            missing.append({'field': 'storage.interface_version', 'address': base+0x12AA6B8, 'size': len(version)})
        elif raw != version:
            conflicts.append({'field': 'storage.interface_version', 'observed_hex': raw.hex()})
        storage['context_init'] = ptr('storage.context_init', base+0x123CB28)
        # The observed initialized ContextInit returns token+16 only when the
        # token generation equals its RIP-relative global counter. Decode the
        # real captured instruction, not a guessed global or old pointer.
        if storage['holder'] != base+0x18D08B8+16:
            conflicts.append({'field': 'storage.cached_holder', 'observed': storage['holder'],
                              'expected': base+0x18D08B8+16})
        context_init = storage['context_init']
        code = reads.raw(context_init, 0x65)
        if code is None:
            missing.append({'field': 'storage.context_init_cached_code', 'address': context_init, 'size': 0x65})
        elif (code[:16] != bytes.fromhex('40534883ec20488b5108488bd9488b05') or
              code[20:25] != bytes.fromhex('483bd07442') or
              code[0x5B:0x65] != bytes.fromhex('488d41104883c4205bc3')):
            conflicts.append({'field': 'storage.context_init_cached_code',
                              'reason': 'Observed code does not prove generation-equal return token+16'})
        else:
            counter = context_init+20+struct.unpack_from('<i', code, 16)[0]
            generation = observed('storage.token_generation', base+0x18D08B8+8)
            actual_generation = observed('storage.context_generation', counter)
            if generation is not None and actual_generation is not None and generation != actual_generation:
                conflicts.append({'field': 'storage.cached_generation', 'observed': actual_generation,
                                  'expected': generation})
            storage['cached_counter_address'] = counter
            storage['cached_generation'] = generation
            storage['cached_fastpath_observed'] = generation is not None and generation == actual_generation
    hooks.append({'index': 5, 'name': 'FileRead', 'slot': storage['vtable']+8 if storage else None,
                  'original': storage['read'] if storage else None, 'hook': None,
                  'hook_symbol': 'CheckpointLoadWorkerBridge1'})

    unresolved = [
        'Approved production Session/forward-controller module plus exact source and binary hashes; six pinned bridge entry addresses and optional dispatchForwardTargets are runtime-local, not supplied here.',
        'Production nonthrowing validators for request, bytes, lifecycle, identity, Session and planning; they must track this attachment/attempt and each lifecycle phase, not a constant true.',
        'Callback-scoped admission with actual in-original prefetch observation, real pending spans and current page/lifetime validation; no installer-thread ownership inference.',
        'Single queue adapter: invoke supported 411980 only at admitted User AFTER, preserve live queue capacity/identity, capture exact newly queued menu and validate its >=0x480 readable span; no preregistered menu.',
        'Fresh Steam v014 binding/module identity and lifetime pin, callback-safe validation accepting only this owned FileRead hook, and full same-attempt CC63 reads. Historical native read PASS is not this load buffer proof.',
        'Trusted local fixed-CC63 source path and complete SHA, fresh workspace CREATE_NEW request/identity paths, durable once ownership and room/checkpoint/epoch binding.',
        'Paired Menu AFTER and parent Game BEFORE native worker/callable/input guards, expectedRng refreshed or proven invariant at that boundary; capture time alone cannot authorize CAS.',
        'Post-CAS observers retained through errors/Stop; no retry/unload based on false return; rebuild identity and fresh new-User planning receipt before any final verdict.',
    ]
    if attempt is None:
        unresolved.insert(0, 'New attempt token/IDs/ownerBinding and checkpoint/intent binding not supplied; no invented transaction identity.')
    return {
        'schema': 'san14.session-config-manifest.v1', 'result': 'DATA_ONLY_INCOMPLETE',
        'game_build_sha256': GAME_SHA256, 'snapshot_sha256': expected_snapshot_sha256,
        'attachment': dict(attachment), 'capture': dict(capture), 'attempt': attempt,
        'target_profile': dict(TARGET),
        'request': {'boundary': {'base': base, 'root': root, 'world': world,
            'states': states, 'menu': 0, 'cache': cache, 'keyboard': keyboard,
            'attempt': attempt['token'] if attempt else None, 'expectedRng': rng,
            'year': date[0], 'month': date[1], 'day': date[2], 'force': 12},
            'localPath': None, 'intentPath': None,
            'ownerBinding': attempt['owner_binding'] if attempt else None, 'validate': None, 'context': None},
        'bytes': {'base': base, 'attemptToken': attempt['token'] if attempt else None,
            'storage': storage['storage'] if storage else None,
            'storageVtable': storage['vtable'] if storage else None,
            'readMethod': storage['read'] if storage else None, 'validateAttachment': None, 'validationContext': None},
        'lifecycle': {'base': base, 'attemptToken': attempt['token'] if attempt else None,
            'bytes': 'SESSION_WIRES_OWN_OBSERVER', 'validateAttachment': None, 'validationContext': None},
        'identity': {'base': base, 'attemptToken': attempt['token'] if attempt else None,
            'bytes': 'SESSION_WIRES_OWN_OBSERVER', 'lifecycle': 'SESSION_WIRES_OWN_LIFECYCLE',
            'intentPath': None, 'ownerBinding': attempt['owner_binding'] if attempt else None,
            'validateAttachment': None, 'validationContext': None},
        'hooks': hooks, 'storage': storage,
        'session_callbacks': {'validate': None, 'context': None, 'userAfter': None,
            'userObservationBefore': None, 'userObservationAfter': None,
            'userObservationContext': None},
        'successor_dispatchForwardTargets': [None, None, None, None],
        'admission': {'profile_base': base, 'states': states, 'spans': spans,
            'observed_initial_cache_mode': cache_mode, 'required_initial_cache_mode': 1,
            'binding_16byte_attempt_attachment_and_owner_generation': None,
            'queue': None, 'original': base+0x3F9B00, 'expected_prefetch_return': None},
        'queue_recipe': {'rva': 0x411980, 'manager': manager, 'name': base+0x12DD6E0,
            'mode_dwords': [0, 0], 'empty_callback_bytes': 64,
            'return_type': 'void; read exact created menu from the normal queue afterwards',
            'native_call_authorized': False},
        'planning': {'base': base, 'persistentRootState': states[0], 'persistentMotorState': states[1],
            'previousUser': states[4], 'attempt': attempt['token'] if attempt else None,
            'epoch': attachment['epoch'], 'session': None, 'validate': None, 'context': None},
        'missing_observations': missing, 'guard_conflicts': conflicts,
        'observations': observations, 'unresolved_runtime_bindings': unresolved,
        'snapshot_fields_consistent': not missing and not conflicts,
        'runtime_config_constructed': False, 'arm_allowed': False, 'load_authorized': False,
        'input_exclusion_proven': False, 'presentation_proven': False,
        'full_world_verified': False, 'current_attachment_verified_by_this_module': False,
        'limitations': ['Source provenance is caller-authenticated via the expected digest and attachment; strings are not cryptographic attestation.',
                       'Captured byte spans do not prove allocation extent, fresh readability, synchronization or ownership.',
                       'The fixed identity adapter supports only 203-08-11 Zhang Lu12/666 district11 to Liu Bei2/952 district2.',
                       'Planning/input/world/display release remains separate, even after native Session identity succeeds.']}
