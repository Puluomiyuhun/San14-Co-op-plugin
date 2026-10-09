"""Explicit-PID read-only turn identity samples. No arguments prints help only."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys
import time

P = Path(__file__).resolve().parent
PRIVATE = P.parents[2] / 'mod_research'
MANAGER = 0x19E7310
ROOT = 0x1FCA1E0


def pointer(value, nullable=False):
    if nullable and value == 0:
        return value
    if not 0x10000 <= value < 0x7FFFFFFFFFFF or value % 8:
        raise RuntimeError('Invalid sampled object pointer')
    return value


def once(reader):
    m = reader.memory
    def number(address, fmt='<Q'):
        return struct.unpack(fmt, m.read(address, struct.calcsize(fmt)))[0]
    root = reader.pointer(m.base + ROOT)
    reader.require_type(root, 'CSan14Data')
    world = reader.pointer(root + 0x85130)
    reader.require_type(world, 'CWorldData')
    date = m.read(world + 0x34, 8)
    year, month, day = struct.unpack_from('<HBB', date)
    force = date[6]
    if not (1 <= year <= 9999 and 1 <= month <= 12 and 1 <= day <= 30 and force <= 51):
        raise RuntimeError('World date/force is not readable in supported shape')
    manager = m.base + MANAGER
    count, capacity, stack = (number(manager + off) for off in (0x10, 0x18, 0x20))
    qcount, qcapacity, queue = (number(manager + off) for off in (0x30, 0x38, 0x40))
    current = pointer(number(manager + 0x48), True)
    if not 1 <= count <= 64 or not count <= capacity <= 4096:
        raise RuntimeError('Unsupported state stack bounds')
    pointer(stack)
    if not 0 <= qcount <= qcapacity <= 4096 or bool(queue) != bool(qcapacity):
        raise RuntimeError('Inconsistent native queue bounds')
    pointer(queue, True)
    raw_stack = m.read(stack, count * 8)
    states = []
    for address in struct.unpack('<' + 'Q' * count, raw_stack):
        pointer(address)
        name = m.read(address + 0x70, 96).split(b'\0', 1)[0].decode('ascii')
        if not name.startswith('C') or not all(c.isalnum() or c in '_<>:, ' for c in name):
            raise RuntimeError('Invalid state name')
        reader.require_type(address, name)
        states.append(dict(name=name, address=address, vtable=reader.pointer(address),
                           task=pointer(number(address + 0x50), True)))
    raw_queue = m.read(queue, qcount * 16) if qcount else b''
    entries = [dict(kind=struct.unpack_from('<I', raw_queue, i * 16)[0],
                    state=pointer(struct.unpack_from('<Q', raw_queue, i * 16 + 8)[0], True))
               for i in range(qcount)]
    return dict(root=root, world=world, date=dict(year=year, month=month, day=day),
                force=force, date_raw=date.hex(), states=states,
                manager=dict(address=manager, current=current, count=count, capacity=capacity,
                             stack=stack, queue=queue, queue_count=qcount, queue_capacity=qcapacity,
                             queue_raw=raw_queue.hex(), entries=entries))


def capture(reader, birth_reader):
    """No retries masking churn; require two complete equal reads and birth checks."""
    start_birth = birth_reader(reader.memory.handle)
    first, second = once(reader), once(reader)
    if first != second or start_birth != birth_reader(reader.memory.handle):
        raise RuntimeError('Identity changed during double read; sample rejected')
    return dict(schema='san14.turn-identity.sample.v1', pid=reader.pid, birth=start_birth,
                base=reader.memory.base, exe_sha256=reader.sha256, **second,
                atomic=False, same_object_lifetime_proven=False, game_writes=0,
                native_calls=0, sampled_utc=datetime.now().astimezone().isoformat())


def compare(first, last):
    same_process = all(first[k] == last[k] for k in ('pid', 'birth', 'base', 'exe_sha256'))
    return dict(same_process=same_process, same_root_address=first['root'] == last['root'],
                same_world_address=first['world'] == last['world'],
                first_date=first['date'], last_date=last['date'],
                same_state_name_address_sequence=same_process and
                [(s['name'], s['address']) for s in first['states']] ==
                [(s['name'], s['address']) for s in last['states']],
                same_object_lifetime_proven=False,
                limit='Equal addresses may be reused allocations; differing addresses do not identify destruction time.')


def birth(handle):
    import ctypes as c
    from ctypes import wintypes as w
    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.GetProcessTimes.argtypes = [w.HANDLE] + [c.POINTER(w.FILETIME)] * 4
    kernel.GetProcessTimes.restype = w.BOOL
    values = [w.FILETIME() for _ in range(4)]
    if not kernel.GetProcessTimes(handle, *[c.byref(v) for v in values]):
        raise c.WinError(c.get_last_error())
    return values[0].dwHighDateTime << 32 | values[0].dwLowDateTime


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, help='Explicit current game PID; never discovered automatically')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--capture', action='store_true')
    modes.add_argument('--watch', type=float, metavar='SECONDS')
    parser.add_argument('--interval', type=float, default=.25)
    args = parser.parse_args(argv)
    if not args.capture and args.watch is None:
        parser.print_help()
        return 0
    if not args.pid or args.pid < 1 or not .1 <= args.interval <= 60:
        parser.error('Explicit positive --pid and interval 0.1..60 required')
    if args.watch is not None and not 1 <= args.watch <= 3600:
        parser.error('--watch requires 1..3600 seconds')
    # Import alone does not open a process. The explicit PID prevents fallback discovery.
    sys.path.insert(0, str(P.parents[1] / 'outputs' / 'san14-link'))
    from game_reader import GameReader
    run = PRIVATE / 'a_turn_identity_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    sources = [Path(__file__), P.parents[1] / 'outputs/san14-link/game_reader.py',
               P.parents[1] / 'outputs/san14-link/readonly_probe.py']
    (run / 'intent.json').write_text(json.dumps(dict(pid=args.pid, watch=args.watch,
        interval=args.interval, game_writes=0, debugger=False,
        sources={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}), indent=2)+'\n')
    reader = None
    first = last = None
    accepted = rejected = 0
    error = None
    try:
        reader = GameReader(args.pid)
        deadline = time.monotonic() + (args.watch or 0)
        with (run / 'samples.jsonl').open('x', encoding='utf-8') as out:
            while True:
                try:
                    sample = capture(reader, birth)
                    first = first or sample
                    last = sample
                    accepted += 1
                    row = dict(accepted=True, sample=sample)
                except Exception as exc:
                    rejected += 1
                    row = dict(accepted=False, error=str(exc), time=time.time())
                out.write(json.dumps(row, ensure_ascii=False)+'\n')
                out.flush()
                if args.capture or time.monotonic() >= deadline:
                    break
                time.sleep(min(args.interval, max(0, deadline-time.monotonic())))
    except (Exception, KeyboardInterrupt) as exc:
        error = repr(exc)
    finally:
        if reader:
            reader.close()
    result = dict(result='OBSERVATIONS_RECORDED' if accepted else 'NO_STABLE_SAMPLE',
                  accepted=accepted, rejected=rejected, error=error, game_writes=0,
                  comparison=compare(first, last) if first else None)
    (run / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(path=str(run), **result)))
    return 0 if accepted and error is None else 2


if __name__ == '__main__':
    raise SystemExit(main())
