"""One manual Save observation. No arguments: help, no game access.

--preflight reads the current supported game only. --record requires the exact
passing owned-process build, and never submits a Save/Load or gameplay command.
All native registers must be restored and pending debugger events drained before
detach. A stuck cleanup is retained, never killed by a launcher timeout.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
GAME_SHA = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
STACK = ['CRootState', 'CMotorGameState', 'CGameState', 'CStrategyState', 'CUserStrategyState']
SOURCES = ('a_save_observation.cpp', 'a_save_observation_payload.inc', 'a_save_observation_binding.inc',
           'a_save_observation_anchors.h', 'a_save_observation_debug_fixture.cpp',
           'a_save_observation_semantic_fixture.cpp', 'a_save_observation.py', 'a_save_observation_test.py',
           'a_save_native_coordination_events.py', '../../outputs/san14-link/game_reader.py',
           '../../outputs/san14-link/readonly_probe.py', '../../outputs/san14-link/startup_identity_reader.py')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def birth(handle):
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.GetProcessTimes.argtypes = [W.HANDLE]+[C.POINTER(W.FILETIME)]*4
    kernel.GetProcessTimes.restype = W.BOOL
    values = [W.FILETIME() for _ in range(4)]
    if not kernel.GetProcessTimes(handle, *[C.byref(v) for v in values]):
        raise C.WinError(C.get_last_error())
    return (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime


def anchors():
    text = (P/'a_save_observation_anchors.h').read_text(encoding='utf-8')
    result = [(int(a, 16), bytes(int(b, 16) for b in re.findall(r'0x[0-9a-f]+', raw)))
              for a, raw in re.findall(r'\{(0x[0-9a-f]+),\{([^}]+)\}\}', text)]
    if len(result) != 15 or any(len(raw) != 16 for _, raw in result):
        raise RuntimeError('Missing exact observation anchors')
    return result


def preflight(pid=None):
    sys.path.insert(0, str(ROOT/'outputs/san14-link'))
    from game_reader import GameReader
    from startup_identity_reader import capture_startup_context
    reader = GameReader(pid)
    try:
        m = reader.memory
        before = capture_startup_context(reader)
        snapshot = before['snapshot']; reasons = []
        def require(ok, name):
            if not ok: reasons.append(name)
        require(reader.sha256 == GAME_SHA, 'unsupported_executable')
        debugger = W.BOOL()
        m.k.CheckRemoteDebuggerPresent.argtypes = [W.HANDLE, C.POINTER(W.BOOL)]
        m.k.CheckRemoteDebuggerPresent.restype = W.BOOL
        require(m.k.CheckRemoteDebuggerPresent(m.handle, C.byref(debugger)) and not debugger.value, 'another_debugger_or_query_failure')
        require(snapshot['state_stack'] == STACK, 'not_idle_planning')
        require(snapshot['date'] == {'year':203, 'month':8, 'day':11, 'period':'中旬'}, 'not_slot34_baseline_date')
        require(snapshot['player']['force_id'] == 12 and snapshot['player']['ruler_id'] == 666, 'not_Zhang_Lu_baseline')
        require(before['world_mode'] == 1 and before['state_sample'] and before['state_sample']['phase_raw'] == 2, 'not_planning_phase2')
        u64 = lambda p: int.from_bytes(m.read(p, 8), 'little')
        states = reader.state_objects()
        user = states[-1][1]; stack = u64(m.base+0x19E7310+0x20)
        require(u64(m.base+0x19E7310+0x30) == 0, 'pending_state_command')
        for slot, entry in ((0x12CC4D0,0x3F9B00), (0x12CC9E0,0x3F8140)):
            require(u64(m.base+slot) == m.base+entry, 'modified_update_slot_'+hex(slot))
        for rva, expected in anchors():
            require(m.read(m.base+rva, len(expected)) == expected, 'modified_source_'+hex(rva))
        require(snapshot == reader.snapshot() and states == reader.state_objects(), 'context_changed')
        return dict(schema='san14.a-save-observation-preflight.v1', result='PASS_READ_ONLY' if not reasons else 'BLOCKED',
                    reasons=reasons, pid=reader.pid, birth=birth(m.handle), base=m.base, user=user, stack=stack,
                    snapshot=snapshot, game_data_writes=0, native_requests=0, debugger_attached=False,
                    authorization=False, full_world=False)
    finally:
        reader.close()


def tested_build(folder):
    folder = Path(folder).resolve()
    result = json.loads((folder/'result.json').read_text(encoding='utf-8'))
    if result.get('schema') != 'san14.a-save-observation-owned-tests.v1' or result.get('result') != 'PASS':
        raise RuntimeError('Exact owned-process tests must pass before live observation')
    if set(result['sources']) != set(SOURCES):
        raise RuntimeError('Incomplete tested source identity')
    for name, digest in result['sources'].items():
        if sha(P/name) != digest: raise RuntimeError('Source differs from tested build: '+name)
    binary = folder/'observer.exe'
    if sha(binary) != result['production_sha256']:
        raise RuntimeError('Production observer differs from tested build')
    return binary, result


def records(path, allow_partial=True):
    if not path.exists(): return []
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines()
    rows = []
    for n, line in enumerate(lines):
        try: rows.append(json.loads(line))
        except json.JSONDecodeError:
            if not (allow_partial and n == len(lines)-1 and not text.endswith('\n')): raise
    return rows


def capture_status(rows, ready, code):
    clean = bool(rows and rows[-1].get('event') == 'detached' and
                 rows[-1].get('registers_restored') is True and rows[-1].get('owned_queue_drained') is True)
    failures = {'error', 'forwarded_exception', 'process_exit', 'unowned_debug_status',
                'cleanup_pending_owned_frozen', 'cleanup_owned_exception_drained',
                'cleanup_foreign_exception_forwarded', 'cleanup_process_exit',
                'restoration_uncertain_debugger_retained', 'continue_failed_debugger_retained'}
    errors = [r['event'] for r in rows if r.get('event') in failures]
    summaries = [r for r in rows if r.get('event') == 'summary']
    selected = [r for r in rows if 'seq' in r]
    if len(summaries) != 1:
        errors.append('missing_or_multiple_summaries')
    else:
        summary = summaries[0]
        if summary.get('reason') in ('hardware_event_limit', 'debug_event_limit'):
            errors.append('observation_limit_reached')
        if summary.get('lost_events') != 0 or summary.get('selected_records') != len(selected):
            errors.append('selected_record_count_or_loss_mismatch')
    # Completion describes the debugger lifecycle. Pairing and presence of a
    # Save are decided by the analyzer, never inferred from a clean detach.
    return dict(capture_complete=bool(ready and code in (0, 4) and clean and not errors),
                capture_errors=errors), clean


def record(folder, pid, seconds):
    binary, tests = tested_build(folder)
    before = preflight(pid)
    run = P/'a_save_observation_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f'); run.mkdir(parents=True)
    write(run/'before.json', before)
    if before['result'] != 'PASS_READ_ONLY':
        print(json.dumps(dict(result='BLOCKED', run=str(run), reasons=before['reasons']))); return 2
    run_id = secrets.token_hex(16)
    metadata = {k:before[k] for k in ('pid','birth','base')}; metadata['run_id'] = run_id
    write(run/'intent.json', dict(metadata, source_hashes=tests['sources'], production_sha256=tests['production_sha256'],
                                 manual_save_only=True, save_filename_attested=False, duration_seconds=seconds))
    trace = run/'trace.jsonl'; process = None; ready = False; interrupted = None
    with (run/'stdout.log').open('xb') as out, (run/'stderr.log').open('xb') as err:
        try:
            process = subprocess.Popen([str(binary), str(before['pid']), hex(before['base']), '0x2f7c28', str(seconds),
                str(trace), str(before['birth']), str(before['user']), str(before['stack']), run_id],
                stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
            deadline = time.monotonic()+20
            while process.poll() is None and time.monotonic() < deadline:
                rows = records(trace)
                if any(r.get('event') == 'armed' for r in rows):
                    ready = True
                    print(json.dumps(dict(status='READY_FOR_ONE_MANUAL_SAVE', run=str(run), observer_pid=process.pid,
                        game_pid=before['pid'], seconds=seconds, native_requests=0), ensure_ascii=False), flush=True); break
                time.sleep(.1)
            if not ready and process.poll() is None: raise RuntimeError('Recorder did not become ready')
            process.wait(timeout=seconds+30)
        except BaseException as error:
            interrupted = type(error).__name__+': '+str(error)
        finally:
            if process is not None and process.poll() is None:
                Path(str(trace)+'.stop').write_text('stop', encoding='ascii')
                try: process.wait(timeout=20)
                except subprocess.TimeoutExpired: interrupted = (interrupted or '')+'; cleanup retained, do not terminate'
    code = process.poll() if process is not None else None
    rows = records(trace, allow_partial=code is None)
    lifecycle, clean = capture_status(rows, ready, code)
    metadata.update(lifecycle)
    from a_save_native_coordination_events import analyze
    analysis = analyze([r for r in rows if 'seq' in r], metadata)
    result = dict(schema='san14.a-save-observation-live.v1', ready_seen=ready, observer_exit=code,
                  cleanup_pending=code is None, cleanup_verified=clean, interrupted=interrupted,
                  metadata=metadata, analysis=analysis, game_data_writes=0, native_requests=0,
                  full_world=False, production_permit=False, save_filename_attested=False)
    write(run/'result.json', result)
    print(json.dumps(dict(result=analysis, run=str(run), cleanup_pending=code is None), ensure_ascii=False), flush=True)
    return 0 if analysis['classification'] in ('WORKER_SCOPE_OVERLAP_OBSERVED','NO_WORKER_SCOPE_OVERLAP_OBSERVED') else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--preflight', action='store_true')
    action.add_argument('--record', action='store_true')
    parser.add_argument('--pid', type=int)
    parser.add_argument('--tested-build', type=Path)
    parser.add_argument('--seconds', type=int, default=1800)
    args = parser.parse_args()
    if not (1 <= args.seconds <= 3600): parser.error('seconds must be 1..3600')
    if not args.preflight and not args.record: parser.print_help(); return 0
    if args.preflight:
        result = preflight(args.pid); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result['result'] == 'PASS_READ_ONLY' else 2
    if args.tested_build is None: parser.error('--record requires --tested-build')
    return record(args.tested_build, args.pid, args.seconds)


if __name__ == '__main__':
    raise SystemExit(main())
