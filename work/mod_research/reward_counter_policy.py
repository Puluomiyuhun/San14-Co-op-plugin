"""Finite, read-only policy for two viewer-gated world counters.

No process is opened, native function called, packet applied, or load authorized.
The supplied read callable belongs to the caller; two equal reads are neither an
atomic snapshot nor a world/attachment lifetime proof. Chinese business names,
save serialization, and the complete set of counter writers remain unknown.
"""
from pathlib import Path
import hashlib
import struct

SCHEMA = 'san14.reward-counter-observation.v1'
ARCHIVE_SHA256 = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
U32 = 0xffffffff
FIELDS = (
    ('world_3a_u8', 0x3A, '<B'),
    ('world_7c_u32', 0x7C, '<I'), ('world_80_u32', 0x80, '<I'),
    # 1C0CD0 sign-extends ONE byte. Reading an i32 changes its -1 condition.
    ('world_bc_i8', 0xBC, '<b'),
    ('world_450_u32', 0x450, '<I'), ('world_45c_u32', 0x45C, '<I'),
    ('world_16a8_u32', 0x16A8, '<I'))
COUNTERS = ('world_7c_u32', 'world_80_u32')
CAPS = {'world_7c_u32': 10000, 'world_80_u32': 1000}

# Hashes, not complete game functions. Offsets refer to the private mapped image.
SECTIONS = (
    ('optional_context', 0x1C1A70, 0x1C1A78, '8c0bc5d9cbf05dff4e3eb2077b3c7ffb26a2a2ad9b6a67c21c98d5810bfc4dba'),
    ('signed_context_byte', 0x1C0CD0, 0x1C0CEF, '3752ecb7a87cc8838a91b2e927b5c3f9b2c62bd99a0fa1d3cd3f4d84b5165461'),
    ('world_plus_78', 0x1C1AA0, 0x1C1AB9, '67c4431e615370a3e1fecc1abdd3fcb791fe9b56dd3e6f0c5fc57945fa62323c'),
    ('viewer_force', 0x2F21E0, 0x2F220A, '1ba080e15bf51de4cf05c9be45f611ac0c21ae6ba535fffa2a4e88300a4d8b40'),
    ('force_index', 0x20B610, 0x20B63A, 'b6401e519422e7518e8c9417d427279c846095f0ec46c7299013edcf3c3fb6f6'),
    ('force_vtable_60', 0x129FEB8, 0x129FEC0, '49b0e7ad85fce9191c7c1e2ce6beb04ba7668d33e24a5cff340cd8bb62833cdf'),
    ('district_viewer_gate', 0x211260, 0x21130D, '17cbb983d3cce366023118c85e2cdc8fe8f2b790bc0372bb6311e72971fa7455'),
    ('reward_counter_call', 0x1D7005, 0x1D703A, '70926eb9c8ab335450e1cd485f0b2359668be529b1683130261c555a6e0d175a'),
    ('counter_80', 0x2E6380, 0x2E63F0, 'c547b9cad0c5b0acdd77be37a5894f11d059550ee6b31ddf6b9a62dbefac6d03'),
    ('counter_7c', 0x2E63F0, 0x2E6460, '57017265b619073314f586539af0235313600ff67b1c3b4561d734cb6078096d'),
    ('ap_assignment_call', 0x2334C9, 0x233520, '1cd0ce70315b67d1452b41bff46b5f594714f27f88a842f9b15d8f7ccfc3d833'),
    ('ratio_reader', 0x2E87EC, 0x2E8829, '6f378ca6c10dccc608c5e51e5f8fe9b91883c851717ff570219dbb8f2e3abf9b'),
    ('formatted_ui_reader', 0x3F22BE, 0x3F22F7, 'ec628cfc2f3fbd2957fe21007c61632088f3d7fa8f1643ff3b3c3cdccadf6bc8'))


def _need(ok, message):
    if not ok:
        raise ValueError(message)


def _u32(value):
    _need(type(value) is int and 0 <= value <= U32, 'Exact unsigned 32-bit value required')
    return value


def native_counter_add(field, before, increment_bits):
    """Model ADD EAX,EBX then unsigned CMOVA, including 32-bit wraparound.

    increment_bits is the register bit pattern, not a presumed positive cost.
    This arithmetic model neither proves a native call occurred nor permits one.
    """
    _need(field in CAPS, 'Only the two audited counter fields are supported')
    return min((_u32(before) + _u32(increment_bits)) & U32, CAPS[field])


def capture(read, *, world):
    """Read only these seven fields twice through a retained caller-owned reader."""
    _need(callable(read) and type(world) is int and 0 < world <= 2**64-0x16B0,
          'Read callable and bounded nonzero world address required')
    def sample():
        result = {}
        for name, offset, fmt in FIELDS:
            size = struct.calcsize(fmt)
            raw = read(world+offset, size)
            _need(type(raw) is bytes and len(raw) == size, 'Exact field bytes required: '+name)
            result[name] = struct.unpack(fmt, raw)[0]
        return result
    first = sample()
    _need(first == sample(), 'Counter observation changed between reads')
    return dict(schema=SCHEMA, world=world, fields=first, repeated_equal=True,
                atomic_snapshot=False, attachment_verified=False,
                native_completion_observed=False, full_world_verified=False,
                production_permit=False, load_restore_permit=False)


def _fields(observation):
    _need(type(observation) is dict and observation.get('schema') == SCHEMA,
          'Counter observation schema required')
    data = observation.get('fields')
    _need(type(data) is dict and set(data) == {row[0] for row in FIELDS}, 'Exact finite fields required')
    for name, _, fmt in FIELDS:
        value = data[name]
        low, high = (-128, 127) if fmt == '<b' else ((0, 255) if fmt == '<B' else (0, U32))
        _need(type(value) is int and low <= value <= high, 'Invalid raw field: '+name)
    return data


def reward_branch_gate(observation, *, optional_context_present=None,
                       current_force_valid=None, district_force_id=None,
                       district_leader_valid=None, district_leader_rank=None):
    """Classify supplied observations of the audited branch, never authenticate.

    Unknown object validity/global context stays unknown. Caller-supplied facts
    are diagnostic inputs only; they are not boolean execution permissions.
    """
    data = _fields(observation)
    for value in (optional_context_present, current_force_valid, district_leader_valid):
        _need(value is None or type(value) is bool, 'Validity observations must be bool or unknown')
    for value in (district_force_id, district_leader_rank):
        _need(value is None or type(value) is int and 0 <= value <= 255, 'Raw byte or unknown required')
    conditions = dict(context_present=optional_context_present,
        context_byte_enabled=data['world_bc_i8'] != -1,
        world_flag_allows=(data['world_16a8_u32'] & 0x100) == 0,
        current_force_valid=current_force_valid,
        district_is_viewer=None if district_force_id is None else district_force_id == data['world_3a_u8'],
        leader_valid=district_leader_valid,
        leader_rank_one=None if district_leader_rank is None else district_leader_rank == 1)
    status = ('AUDITED_BRANCH_BLOCKED' if False in conditions.values() else
              'UNKNOWN' if None in conditions.values() else 'AUDITED_CONDITIONS_OBSERVED_TRUE')
    return dict(status=status, conditions=conditions, native_call_observed=False,
                conditions_stable_during_native_call=False, all_writers_known=False,
                production_permit=False)


def shared_delta_exclusion(before, after):
    """Exclude both counters even if unchanged; never extract an applicable patch."""
    a, b = _fields(before), _fields(after)
    same_local = before.get('world') == after.get('world') and a['world_3a_u8'] == b['world_3a_u8']
    return dict(schema='san14.reward-counter-exclusion.v1',
        excluded_fields=list(COUNTERS), shared_delta_inclusion_allowed=False,
        changes={key: dict(before=a[key], after=b[key]) for key in a if a[key] != b[key]},
        same_local_address_and_viewer=same_local, attachment_verified=False,
        reward_attribution_proven=False, all_writers_known=False, business_name='UNKNOWN',
        reason='Audited writes depend on local viewer; counters also have non-reward readers and writers.',
        native_apply_permit=False, load_restore_permit=False, full_world_verified=False)


def checkpoint_impact():
    """A planning note returned as data, not an instruction to change the loader."""
    return dict(schema='san14.reward-counter-checkpoint-risk.v1', business_name='UNKNOWN',
        serialized_in_save=None, copied_by_authority_checkpoint=None,
        local_viewer_write_gate_observed=True,
        conditional_risk='If serialized/copied, A checkpoint may replace B viewer statistics; replacing the ruler alone does not prove remapping.',
        unconditional_preserve_is_safe=False, unconditional_authority_overwrite_is_safe=False,
        required_evidence=['save/load mapping of world+78 structure',
            'which fields are derived/reset at load or turn transition',
            'B viewer history versus A authority history semantics'],
        proposed_next_step='Observe before/after native save/load under separate authorized testing; do not restore raw bytes automatically.',
        game_write_permit=False, load_restore_permit=False, production_permit=False)


def audit_archive(image):
    """Verify the exact private archive and finite source intervals; no execution."""
    image = Path(image).resolve(strict=True)
    raw = image.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    _need(digest == ARCHIVE_SHA256, 'Pinned offline archive required')
    sections = []
    for name, start, end, wanted in SECTIONS:
        actual = hashlib.sha256(raw[start:end]).hexdigest()
        _need(actual == wanted, 'Archived source differs: '+name)
        sections.append(dict(name=name, rva=start, size=end-start, sha256=actual))
    return dict(schema='san14.reward-counter-static-evidence.v1', result='PASS',
        private_inputs={str(image): digest}, sections=sections,
        call_graph=[
            '1D7005..1D7035 -> 1C1A70,1C0CD0,211260 -> 2E6380 -> 1C1AA0 -> world+80',
            '2334F1 assigns district+14; 2334F4..23351B -> same local gates -> 2E63F0 -> world+7C',
            '211260 -> 2F21E0(world+3A) -> force.vtable+60; compare district+10; leader+11E==1',
            '2E87EC reads world+7C/+80 for a ratio; 3F22BE reads both for formatted UI'],
        inference='Related to local-viewer action-point allocation/use; exact business name unknown.',
        complete_writer_inventory=False, save_mapping_verified=False,
        game_access=False, native_execution=False, production_permit=False)
