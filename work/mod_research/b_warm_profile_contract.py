"""Data-only Windows x64 warm-bank ABI; configuration is never load permission."""
import ctypes as C
import checkpoint_complete_live_owner_contract as old

U8, U16, U32, U64 = C.c_uint8, C.c_uint16, C.c_uint32, C.c_uint64
MAGIC = 0x53414E1457504631


class FileProfile(C.Structure):
    _fields_ = [('name', C.c_char * 32), ('slot', U32), ('size', U32), ('sha256', U8 * 32)]


class Date(C.Structure):
    _fields_ = [('year', U16), ('month', U8), ('day', U8)]


class Identity(C.Structure):
    _fields_ = [('ruler', U16), ('force', U8), ('district', U8)]


class Profile(C.Structure):
    _fields_ = [('file', FileProfile), ('before', Date), ('loaded', Date),
                ('source', Identity), ('target', Identity), ('currentForce', U8), ('reserved', U8 * 7)]


class Config(C.Structure):
    _fields_ = [('magic', U64), ('size', U32), ('version', U32), ('profile', Profile), ('owner', old.Config)]

    def __init__(self):
        super().__init__()
        self.magic, self.size, self.version = MAGIC, C.sizeof(type(self)), 1
        self.owner = old.Config()


class Description(C.Structure):
    _fields_ = [('magic', U64), ('size', U32), ('version', U32), ('configSize', U32),
                ('profileSize', U32), ('reportSize', U32), ('reserved', U32), ('bank', old.Description)]


class Report(C.Structure):
    _fields_ = [('magic', U64), ('size', U32), ('version', U32), ('configured', U32),
                ('ready', U32), ('error', U32), ('reserved', U32), ('profile', Profile)]


class RetireReport(C.Structure):
    _fields_ = [(n, U32) for n in 'version size bound sealed restored restoreFailed eligibleChecks completionSeen refusalStage'.split()]
    _fields_ += [(n, U64) for n in 'attempt userCall identityCall loadCall'.split()]
    _fields_ += [('thread', U32)]


TYPES = {'FileProfile': FileProfile, 'Date': Date, 'Identity': Identity, 'Profile': Profile,
         'Config': Config, 'Description': Description, 'Report': Report, 'RetireReport': RetireReport}


def validate_profile(p):
    raw_name = bytes(p.file)[:32]
    if raw_name != b'svdexccSC03.s14'.ljust(32, b'\0') or p.file.slot != 63:
        raise ValueError('Only verified native slot63/name mapping is supported')
    if not 1 <= p.file.size <= 16 * 1024 * 1024 or not any(p.file.sha256):
        raise ValueError('File size/hash')
    for d in (p.before, p.loaded):
        if not (1 <= d.year <= 9999 and 1 <= d.month <= 12 and d.day in (1, 11, 21)):
            raise ValueError('Planning date')
    for i in (p.source, p.target):
        if not (0 < i.force < 52 and 0 < i.ruler < 6000 and 0 < i.district < 52):
            raise ValueError('Identity')
    if any(getattr(p.source, k) == getattr(p.target, k) for k in ('force', 'ruler', 'district')):
        raise ValueError('Source and target identities must differ')
    if not 0 < p.currentForce < 52 or any(p.reserved):
        raise ValueError('Current force/reserved')
    return p


def decode(kind, raw):
    if kind not in (Description, Report, RetireReport) or len(raw) != C.sizeof(kind):
        raise ValueError('Report type/length')
    out = kind.from_buffer_copy(raw)
    if (out.size, out.version) != (C.sizeof(kind), 1):
        raise ValueError('Report ABI')
    if kind is not RetireReport and (out.magic != MAGIC or out.reserved):
        raise ValueError('Magic/reserved')
    if kind is Description:
        if (out.configSize, out.profileSize, out.reportSize) != (C.sizeof(Config), C.sizeof(Profile), C.sizeof(Report)):
            raise ValueError('Described profile layout')
        old.decode_description(bytes(out.bank))
    elif kind is Report:
        if out.configured not in (0, 1) or out.ready not in (0, 1) or out.error not in (0, 1, 2):
            raise ValueError('Profile state')
        if out.error and not out.configured:
            raise ValueError('Profile error without an attempted capture')
        if out.ready:
            if not out.configured or out.error:
                raise ValueError('Inconsistent captured profile')
            validate_profile(out.profile)
        elif any(bytes(out.profile)):
            raise ValueError('Uncaptured profile must be empty')
    else:
        if any(getattr(out, k) not in (0, 1) for k in ('bound', 'sealed', 'restored', 'restoreFailed', 'completionSeen')) or out.refusalStage > 3:
            raise ValueError('Retirement state')
        if out.completionSeen and not out.bound:
            raise ValueError('Completion without an immutable binding')
        if out.sealed:
            if not out.bound or not out.completionSeen or out.refusalStage or not all(getattr(out, k) for k in ('attempt', 'userCall', 'identityCall', 'loadCall', 'thread')):
                raise ValueError('Retirement completion binding')
            if out.restored + out.restoreFailed != 1:
                raise ValueError('Sealed bank must retain exact restoration outcome')
        elif out.restored or out.restoreFailed:
            raise ValueError('Restoration without seal')
    return out


def status(profile_report, retire_report):
    """Interpret separately verified local samples; cannot authorize a next bank."""
    p, r = decode(Report, bytes(profile_report)), decode(RetireReport, bytes(retire_report))
    return dict(profile_captured=bool(p.ready), business_sealed=bool(r.sealed),
                six_slots_restored=bool(r.restored), restore_uncertain=bool(r.restoreFailed),
                missed_completion_boundary=bool(r.completionSeen and not r.sealed),
                can_install_next_bank=False, load_completed_proven=False, two_player_ready=False)
