"""Trusted Room-side configuration export. No native RPC, process access or writes.

The local loader supplies its bound ReadProcessMemory reader. Config bytes are
not an authorization receipt: the native module re-reads all supported settings,
identities and planning graph. Peers share rules through existing greeting hash.
No method added here makes Room ready, starts time, or acknowledges input Hold.
"""
from pathlib import Path
import ctypes as C
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'outputs/san14-link'))
from room_session import Room, RoomError, digest, require

GAME_SHA = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'


class Config(C.Structure):
    _fields_ = [('version', C.c_uint32), ('size', C.c_uint32),
                ('image', C.c_uint64), ('root', C.c_uint64), ('world', C.c_uint64),
                ('room', C.c_ubyte*16), ('epoch', C.c_ubyte*16),
                ('rules_digest', C.c_ubyte*32), ('force', C.c_uint32*2),
                ('main_district', C.c_uint32*2), ('viewer', C.c_uint32),
                ('year', C.c_uint32), ('month', C.c_uint32), ('day', C.c_uint32),
                ('income_key5', C.c_uint32), ('world_option8', C.c_uint32)]


def rules(income_key5, world_option8):
    require(type(income_key5) is int and 0 <= income_key5 <= 3, 'Unsupported native income key 5')
    require(type(world_option8) is int and world_option8 in (0, 1), 'Unsupported native option bit 8')
    return {'schema': 'san14.human-rules-activation.v1', 'players': 2,
            'ai': 'human-main-district-only;delegated-native',
            'income_callers': ['28DE76', '28DAAA'], 'income': 'both-room-humans',
            'native_income_key5': income_key5, 'native_world_option8': world_option8,
            'fault': 'fatal-retain-current-call;restart-only'}


def _bound(room, settings):
    require(type(room) is Room, 'Require the actual trusted Room object')
    require(settings == rules(settings.get('native_income_key5'), settings.get('native_world_option8')),
            'Unsupported rules content')
    require(room.manifest['profile']['game_sha256'] == GAME_SHA, 'Unsupported game build')
    require(room.manifest['profile']['rules_sha256'] == digest(settings), 'Rules differ from authenticated greeting')
    require(room.bindings is not None and set(room.players) == {'A', 'B'} and
            all(r['connection'] is not None and r['confirmed'] for r in room.players.values()),
            'Both authenticated peers must remain connected and bound')
    return room.native_control_config()


def export_config(room, settings, side, *, image, root, world, read):
    """Read exact native fields through caller-owned reader, while Room locked.

    This checks this local native side only. It does not certify the other PC's
    loaded world, all shared settings, a paused scheduler, or a complete world.
    """
    require(side in ('A', 'B'), 'Unknown local side')
    require(callable(read), 'Missing bound native reader')
    def value(address, fmt):
        n = struct.calcsize(fmt)
        raw = read(address, n)
        require(type(raw) is bytes and len(raw) == n, 'Incomplete native field')
        return struct.unpack(fmt, raw)[0]
    with room.lock:
        _bound(room, settings)
        config = Config(version=1, size=C.sizeof(Config), image=image, root=root, world=world)
        for field, raw in [('room', bytes.fromhex(room.room_id)), ('epoch', bytes.fromhex(room.binding_epoch)),
                           ('rules_digest', bytes.fromhex(digest(settings)))]:
            getattr(config, field)[:] = raw
        for i, player in enumerate(('A', 'B')):
            config.force[i] = room.bindings[player]['force_id']
            config.main_district[i] = room.bindings[player]['main_district_id']
        require(value(image+0x1FCA1E0, '<Q') == root and value(root+0x85130, '<Q') == world,
                'Stale native world pointers')
        require(value(image+0x1FD0C5C, '<i') not in (0, -1), 'Native settings singleton uninitialized')
        config.viewer = value(world+0x3A, '<B')
        require(config.viewer == room.bindings[side]['force_id'], 'Local viewer is not this room seat')
        config.year, config.month, config.day = (value(world+0x34, '<H'), value(world+0x36, '<B'), value(world+0x37, '<B'))
        config.income_key5 = value(image+0x18EB628, '<I')
        config.world_option8 = (value(world+0x16A8, '<I') >> 8) & 1
        require(config.income_key5 == settings['native_income_key5'] and
                config.world_option8 == settings['native_world_option8'], 'Actual native settings disagree with room')
        # Native Prepare and Seal independently enforce planning graph/date/main
        # districts and repeat exact reads. This exporter cannot replace either.
        require(value(image+0x1FCA1E0, '<Q') == root and value(root+0x85130, '<Q') == world,
                'Native world changed while exporting')
        return config


def require_current(room, settings, config):
    """Call under the Room lock immediately before local Prepare/Seal/publication.

    The loader must call native Revoke on disconnect/room destruction or any
    failure after Seal. No automatic watchdog or game connection exists here.
    """
    with room.lock:
        _bound(room, settings)
        require(bytes(config.room).hex() == room.room_id and bytes(config.epoch).hex() == room.binding_epoch and
                bytes(config.rules_digest).hex() == digest(settings) and
                config.income_key5 == settings['native_income_key5'] and config.world_option8 == settings['native_world_option8'] and
                list(config.force) == [room.bindings[p]['force_id'] for p in ('A', 'B')] and
                list(config.main_district) == [room.bindings[p]['main_district_id'] for p in ('A', 'B')],
                'Stale or altered exported binding')


assert C.sizeof(Config) == 136
