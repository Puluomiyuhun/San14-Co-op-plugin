"""Fresh profile-bound B planning samples. Explicit --capture --pid; otherwise help.

Read-only preparation, never an installation/retirement/load permit. No file staging,
remote calls, process discovery, writes to the game or fallback to a historical PID.
"""
import argparse
import ctypes as C
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys

import b_warm_profile_contract as abi

P = Path(__file__).resolve().parent
PRIVATE = P.parents[2] / 'mod_research'
GAME_SHA = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
NAMES = ['CRootState', 'CMotorGameState', 'CGameState', 'CStrategyState', 'CUserStrategyState']
SLOTS = [(0x12cc4d0, 0x3f9b00), (0x12db4e8, 0x4aa200), (0x12cc9e0, 0x3f8140),
         (0x12dbd90, 0x4a85c0), (0x138e8d0, 0x4fabc0)]
BINDINGS = ('pid', 'birth', 'base', 'root', 'world', 'cache', 'keyboard', 'toolbar',
            'panel', 'stack', 'stackCapacity', 'queue', 'queueCapacity', 'rng', 'expectedMode')


def require(value, reason):
    if not value:
        raise ValueError(reason)


def integer(value, lo, hi):
    require(type(value) is int and lo <= value <= hi, 'Integer out of range (no ABI truncation)')
    return value


def profile_from_dict(row):
    """Strict caller-supplied expectations, not claims that a save contains them."""
    require(type(row) is dict and set(row) == {'file', 'before', 'loaded', 'source', 'target', 'currentForce'}, 'Profile keys')
    p = abi.Profile()
    f = row['file']
    require(type(f) is dict and set(f) == {'name', 'slot', 'size', 'sha256'}, 'File keys')
    require(f['name'] == 'svdexccSC03.s14' and type(f['sha256']) is str and len(f['sha256']) == 64, 'File mapping/hash')
    p.file.name = f['name'].encode('ascii')
    p.file.slot = integer(f['slot'], 63, 63)
    p.file.size = integer(f['size'], 1, 16 * 1024 * 1024)
    digest = bytes.fromhex(f['sha256'])
    require(len(digest) == 32, 'Hash length')
    p.file.sha256[:] = digest
    for name in ('before', 'loaded'):
        d = row[name]
        require(type(d) is dict and set(d) == {'year', 'month', 'day'}, 'Date keys')
        setattr(p, name, abi.Date(integer(d['year'], 1, 9999), integer(d['month'], 1, 12), integer(d['day'], 1, 21)))
    for name in ('source', 'target'):
        i = row[name]
        require(type(i) is dict and set(i) == {'ruler', 'force', 'district'}, 'Identity keys')
        setattr(p, name, abi.Identity(integer(i['ruler'], 1, 5999), integer(i['force'], 1, 51), integer(i['district'], 1, 51)))
    p.currentForce = integer(row['currentForce'], 1, 51)
    return abi.validate_profile(p)


def capture_planning(reader, profile, expected_ruler, *, context_reader=None, birth_reader=None, range_check=None):
    """Two complete equal samples, including current/task fields. Never reuse old addresses.

    Injected readers support offline tests only; production defaults are read-only.
    The sixth (Steam Read) slot belongs to separately captured storage bindings.
    """
    p = abi.Profile.from_buffer_copy(bytes(abi.validate_profile(profile)))
    integer(expected_ruler, 1, 5999)
    integer(reader.pid, 1, 0xffffffff)
    require(reader.sha256 == GAME_SHA, 'Unsupported game image')
    if context_reader is None:
        from startup_identity_reader import capture_startup_context
        context_reader = capture_startup_context
    if birth_reader is None or range_check is None:
        from checkpoint_complete_live_capture import process_birth, readable
        birth_reader = birth_reader or process_birth
        range_check = range_check or readable
    birth = birth_reader(reader)
    m = reader.memory
    b = m.base

    def once():
        def number(at, fmt='<Q'):
            return struct.unpack(fmt, m.read(at, struct.calcsize(fmt)))[0]
        def q(at):
            return number(at)
        def u(at):
            return number(at, '<I')
        def s(at):
            return number(at, '<i')
        context = context_reader(reader)
        snap = context['snapshot']
        require(tuple(snap['date'][k] for k in ('year', 'month', 'day')) == (p.before.year, p.before.month, p.before.day), 'Current date differs from bank profile')
        require((snap['player']['force_id'], snap['player']['ruler_id']) == (p.currentForce, expected_ruler), 'Current player differs from explicit expectations')
        state_rows = reader.state_objects()
        require([n for n, _ in state_rows] == NAMES, 'Not the five planning states')
        states = [a for _, a in state_rows]
        require(len(set(states)) == 5, 'Aliased state objects')
        for n, a in state_rows:
            reader.require_type(a, n)
            range_check(reader, a, 0x90)
        manager = b + 0x19e7310
        head = m.read(manager, 0x50)
        count, cap, stack = struct.unpack_from('<3Q', head, 0x10)
        qc, qcap, queue = struct.unpack_from('<3Q', head, 0x30)
        require(count == 5 and 5 <= cap <= 4096 and qc == qcap == queue == 0, 'Current owner requires exact empty queue')
        range_check(reader, stack, cap * 8)
        require(list(struct.unpack('<5Q', m.read(stack, 40))) == states, 'Stack changed')
        root = reader.pointer(b + 0x1fca1e0)
        world = reader.pointer(root + 0x85130)
        cache = reader.pointer(b + 0x2025318)
        reader.require_type(root, 'CSan14Data')
        reader.require_type(world, 'CWorldData')
        toolbar = reader.pointer(states[4] + 0x478)
        panel = reader.pointer(states[2] + 0x480)
        keyboard = reader.pointer(b + 0x1fca0a0)
        for a, size in ((states[4], 0x668), (states[2], 0x488), (cache, 0x3f4), (toolbar, 0x8c), (panel, 0x1f8), (keyboard, 0x258)):
            range_check(reader, a, size)
        pending = dict(userPhase=u(states[4]+0x470), command=s(toolbar+0x88),
                       gameTransition=u(states[2]+0x474), loadQueued=u(states[2]+0x478),
                       advance=u(states[2]+0x47c), panelAdvance=u(panel+0x1b0),
                       userTransition=u(states[4]+0x660), cacheSelection=s(cache+0x3ec),
                       cachePending=u(cache+0x3f0), selections=[u(a+0x68) for a in states])
        require(pending['userPhase'] == 2 and pending['command'] == pending['cacheSelection'] == -1, 'Not idle planning UI/cache')
        require(not any(pending[k] for k in ('gameTransition', 'loadQueued', 'advance', 'panelAdvance', 'userTransition', 'cachePending')) and not any(pending['selections']), 'Pending input/transition')
        mode = u(cache+8)
        require(mode == 0, 'Current owner requires cache mode zero')
        slots = [(b+slot, b+original) for slot, original in SLOTS]
        require(all(q(slot) == original for slot, original in slots), 'An observed native slot is still hooked')
        return dict(pid=reader.pid, birth=birth, base=b, states=states, root=root, world=world, cache=cache,
                    keyboard=keyboard, toolbar=toolbar, panel=panel, stack=stack, stackCapacity=cap,
                    queue=queue, queueCapacity=qcap, rng=u(b+0x18eb8b0), expectedMode=mode,
                    context=context, nativeSlots=slots, gameSha256=GAME_SHA, pending=pending,
                    managerHead=head.hex(), current=struct.unpack_from('<Q', head, 0x48)[0],
                    tasks=[q(a+0x50) for a in states], atomic_snapshot=False,
                    profileSha256=hashlib.sha256(bytes(p)).hexdigest())
    first, second = once(), once()
    require(first == second and birth_reader(reader) == birth, 'Attachment/planning changed during capture')
    return first


def wrap_owner_config(owner, profile, planning):
    """Combine already built local ABI inputs; deliberately does not authorize install."""
    require(type(owner) is abi.old.Config, 'Exact owner ABI required')
    require((owner.magic, owner.size, owner.version) == (abi.old.MAGIC, C.sizeof(abi.old.Config), 1), 'Owner ABI header')
    p = abi.Profile.from_buffer_copy(bytes(abi.validate_profile(profile)))
    require(planning['profileSha256'] == hashlib.sha256(bytes(p)).hexdigest(), 'Profile differs from captured expectations')
    require(planning['gameSha256'] == GAME_SHA and bytes(owner.gameSha256).hex() == GAME_SHA, 'Game fingerprint')
    require(all(getattr(owner, k) == planning[k] for k in BINDINGS) and list(owner.states) == planning['states'], 'Owner contains stale local bindings')
    require(owner.attempt and owner.epoch and owner.generation == owner.attempt, 'Generation binding')
    require(all(any(getattr(owner, k)) for k in ('attachment', 'ownerBinding', 'nonce')), 'Empty attempt tokens')
    result = abi.Config()
    result.profile, result.owner = p, owner
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--pid', type=int)
    parser.add_argument('--profile', type=Path, help='Private JSON expectation file; not a game save')
    parser.add_argument('--expected-ruler', type=int)
    args = parser.parse_args(argv)
    if not args.capture:
        parser.print_help()
        return 0
    if not args.pid or args.pid < 1 or not args.profile or not args.expected_ruler:
        parser.error('Explicit positive PID, profile and expected ruler required')
    profile = profile_from_dict(json.loads(args.profile.read_text(encoding='utf-8-sig')))
    integer(args.pid, 1, 0xffffffff)
    integer(args.expected_ruler, 1, 5999)
    sys.path[:0] = [str(PRIVATE/'python_deps'), str(P.parents[1]/'outputs/san14-link')]
    from game_reader import GameReader
    from a_save_local_binding import source_hashes
    import startup_identity_reader
    import checkpoint_complete_live_capture
    pins = source_hashes()
    run = PRIVATE/'b_warm_profile_capture_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    result = dict(schema='san14.b-warm-profile-capture.v1', result='BLOCKED', game_writes=0,
                  native_calls=0, installation_permit=False, two_player_ready=False,
                  profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(), sources=pins)
    reader = None
    try:
        reader = GameReader(pid=args.pid)
        result['planning'] = capture_planning(reader, profile, args.expected_ruler)
        result['result'] = 'PASS_READ_ONLY'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        if reader:
            reader.close()
    result['sources_unchanged'] = all(hashlib.sha256((P.parents[1]/name).read_bytes()).hexdigest() == digest for name, digest in pins.items())
    if not result['sources_unchanged']:
        result.update(result='BLOCKED', error='Source changed during capture')
    with (run/'result.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(dict(result=result['result'], path=str(run/'result.json')), ensure_ascii=False))
    return 0 if result['result'] == 'PASS_READ_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
