"""Two-phase read-only observation around one ordinary in-game reward.

baseline/compare require an explicit current PID. No hook, DLL, debugger,
network, game writes, or reward call. The user performs the native operation
between samples. A matching delta is an observed candidate, not proof of a
business-function return or complete world coverage. Default help is inert.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT.parent/'mod_research/python_deps'), str(ROOT/'outputs/san14-link')]
from reward_observed_context import projection, reward, journal
from game_reader import GameReader, DATA_POINTER_RVA

SCHEMA = 'san14.passive-reward-sample.v1'


def need(ok, message):
    if not ok: raise ValueError(message)


def capture(reader, forces, *, actor, read_birth=None):
    """Real samplers on the given reader; injected birth is owned-test only."""
    need(type(reader) is GameReader and reader.sha256 == reward.SUPPORTED_SHA256, 'Exact supported reader required')
    need(type(forces) in (list, tuple) and len(forces) == 2 and len(set(forces)) == 2 and
         all(type(f) is int and 1 <= f <= 51 for f in forces) and type(actor) is int and actor in forces,
         'Explicit two forces and local acting force required')
    if read_birth is None:
        from checkpoint_complete_live_capture import process_birth
        read_birth = lambda: process_birth(reader)
    def identity():
        root = reader.pointer(reader.memory.base+DATA_POINTER_RVA)
        world = reader.pointer(root+0x85130)
        reader.require_type(root, 'CSan14Data'); reader.require_type(world, 'CWorldData')
        snap = reader.snapshot(); states = reader.state_objects()
        need([name for name, _ in states] == reward.PLANNING_STACK and snap['state_stack'] == reward.PLANNING_STACK,
             'Return to the planning map before taking a sample')
        need(snap['player']['force_id'] == actor, 'Local viewer is not the acting player')
        birth = read_birth(); need(type(birth) is int and 0 < birth < 2**64, 'Current process birth required')
        return dict(pid=reader.pid, birth=birth, game_sha256=reader.sha256, base=reader.memory.base,
                    root=root, world=world, states=[list(row) for row in states],
                    date=deepcopy(snap['date']), player=deepcopy(snap['player']))
    start = identity()
    def auxiliary():
        # Audited native reward callees: 2E6380 may update world+80 through
        # 1C1AA0, while 3AA2C0/2F0FC0 read +450/+45C. Semantics are not assumed.
        return {name: struct.unpack(fmt, reader.memory.read(start['world']+offset, struct.calcsize(fmt)))[0]
                for name, offset, fmt in (('world_7c_u32', 0x7C, '<I'), ('world_80_u32', 0x80, '<I'), ('world_bc_i32', 0xBC, '<i'),
                                          ('world_450_u32', 0x450, '<I'), ('world_45c_u32', 0x45C, '<I'),
                                          ('world_16a8_u32', 0x16A8, '<I'))}
    extra = auxiliary()
    first = {force: reward.capture_context(reader, force) for force in sorted(forces)}
    second = {force: reward.capture_context(reader, force) for force in sorted(forces)}
    need(first == second and identity() == start and auxiliary() == extra, 'Game changed during the two complete samples')
    for force, context in first.items():
        need(context['strategy_mode'] == 2 and context['state_stack'] == reward.PLANNING_STACK and
             context['viewer_force_id'] == actor and context['date'] == start['date'], 'Planning identity changed')
    value = projection(first)
    return dict(schema=SCHEMA, captured_at=datetime.now(timezone.utc).isoformat(), identity=start,
                actor=actor, forces=sorted(forces), contexts={str(k): v for k, v in first.items()},
                projection_sha256=journal.digest(value), auxiliary=extra, game_writes=0, native_calls=0,
                native_completion_observed=False, atomic_snapshot=False, full_world_verified=False)


def validate_sample(value):
    need(type(value) is dict and value.get('schema') == SCHEMA and
         value.get('game_writes') == 0 and value.get('native_calls') == 0 and
         value.get('native_completion_observed') is False and value.get('atomic_snapshot') is False and
         value.get('full_world_verified') is False, 'Read-only sample contract required')
    contexts = value['contexts']
    need(type(contexts) is dict and sorted(contexts) == sorted(str(f) for f in value['forces']), 'Sample force map differs')
    contexts = {int(k): v for k, v in contexts.items()}
    need(journal.digest(projection(contexts)) == value['projection_sha256'], 'Stored projection differs')
    return contexts


def compare_samples(before, after):
    from reward_result_delta import infer_delta
    b, a = validate_sample(before), validate_sample(after)
    need(before['identity'] == after['identity'] and before['forces'] == after['forces'] and
         before['actor'] == after['actor'], 'Process/world/date/viewer changed between samples')
    delta = infer_delta(b, a, actor_force_id=before['actor'])
    auxiliary_changes = {name: dict(before=value, after=after['auxiliary'][name])
                         for name, value in before['auxiliary'].items() if value != after['auxiliary'][name]}
    return dict(result='REWARD_SHAPED_CHANGE_OBSERVED', delta=delta, auxiliary_changes=auxiliary_changes,
                auxiliary_semantics_verified=False, full_reward_effects_verified=False, game_writes=0, native_calls=0,
                native_completion_observed=False, requires_completion_observer=True,
                network_sent=False, replica_applied=False, full_world_verified=False)


def capture_pid(pid, forces, actor):
    need(type(pid) is int and 0 < pid < 2**32, 'Explicit current PID required')
    reader = GameReader(pid=pid)
    try: return capture(reader, forces, actor=actor)
    finally: reader.close()


def write_new(path, value):
    path = Path(path)
    need(path.is_absolute(), 'Absolute fresh output file required')
    raw = (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    with path.open('xb') as stream: stream.write(raw)
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode')
    base = sub.add_parser('baseline'); base.add_argument('--forces', type=int, nargs=2, required=True)
    base.add_argument('--actor', type=int, required=True)
    compare = sub.add_parser('compare'); compare.add_argument('--before', type=Path, required=True)
    for p in (base, compare):
        p.add_argument('--pid', type=int, required=True); p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.mode is None: parser.print_help(); return 0
    need(args.output.is_absolute() and not args.output.exists(), 'Absolute new output required')
    if args.mode == 'baseline':
        result = capture_pid(args.pid, args.forces, args.actor)
        saved = write_new(args.output, result)
        print(json.dumps(dict(result='READ_ONLY_BASELINE_SAVED', **saved, game_writes=0, native_calls=0)))
        return 0
    before = json.loads(args.before.read_text(encoding='utf-8-sig')); validate_sample(before)
    need(args.pid == before['identity']['pid'], 'PID differs from selected baseline')
    after = capture_pid(args.pid, before['forces'], before['actor'])
    try: outcome = compare_samples(before, after)
    except Exception as exc:
        outcome = dict(result='NO_VERIFIED_REWARD_DELTA', error_type=type(exc).__name__, reason=str(exc),
                       game_writes=0, native_calls=0, network_sent=False, replica_applied=False)
    saved = write_new(args.output, dict(after=after, outcome=outcome))
    print(json.dumps(dict(result=outcome['result'], **saved, game_writes=0, native_calls=0), ensure_ascii=False))
    return 0 if outcome['result'] == 'REWARD_SHAPED_CHANGE_OBSERVED' else 1


if __name__ == '__main__': raise SystemExit(main())
