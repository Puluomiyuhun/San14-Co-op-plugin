"""Development-only, evidence-gated substitution at ONE user-triggered native call.

Does not replay autonomously. On mismatch the original user command still proceeds.
Never run this before normal submission + native slot-34 reload have been verified.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'outputs' / 'san14-link'))
from battle_observer import BattleObserver
from sortie_reader import SortieReader
from pilot_evidence import (check_checkpoint, check_native_effect, check_native_trace,
                            check_restored, load_json, require)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--native-after', type=Path, required=True)
    parser.add_argument('--restored', type=Path, required=True)
    parser.add_argument('--arm', action='store_true', help='Attach the separate write-capable pilot after all gates pass')
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    require(10 <= args.timeout <= 600, 'Timeout must be between 10 and 600 seconds')
    rows = [json.loads(line) for line in args.trace.read_text(encoding='utf-8').splitlines() if line]
    recorded = check_native_trace(rows)
    metadata = load_json(args.trace.parent / 'metadata.json')
    before = load_json(ROOT / 'before-native-submit.json')
    effects = check_native_effect(before, load_json(args.native_after), recorded)
    restored = check_restored(before, load_json(args.restored))
    check_checkpoint(ROOT.parent / 'mod_test' / 'replay-checkpoint-34' / 'svdexSC34.s14')
    check_checkpoint(Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14'))
    observer = BattleObserver()
    try:
        current = observer.capture()
        check_restored(before, current)
        require(observer.pid == metadata['pid'], 'This pilot requires the same game session as the native capture')
        pid, base = observer.pid, observer.memory.base
        code = observer.memory.read(base + 0x1D1940, 32)
        require(code.hex() == metadata['runtime_prefix'], 'Native code fingerprint changed')
    finally:
        observer.close()
    reader = SortieReader(pid)
    try:
        draft = reader.sortie_snapshot()
        require(draft.get('draft_available') and draft.get('draft_stage') == 'destination-selection',
                'Prepare the 1000-man command and city destination first')
        order = draft['partial_order']
        require(order['source_city']['id'] == 19 and len(order['units']) == 1, 'Expected one unit from Wan')
        unit = order['units'][0]
        require(unit['officer_id'] == 666 and unit['soldiers'] == 1000 and
                unit['destination']['kind'] == 'city' and unit['destination']['id'] == 20,
                'Expected Zhang Lu 1000 -> Chang an')
        require(unit['formation']['id'] == recorded[3] and unit['naval_formation']['id'] == recorded[4]
                and [t['id'] for t in unit['tactics']] == recorded[5:8], 'Formation or tactics changed')
    finally:
        reader.close()
    expected = recorded.copy()
    expected[2] = 1000
    run = ROOT / 'replay-traces' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True, exist_ok=False)
    (run / 'expected.bin').write_bytes(struct.pack('<26I', *expected))
    (run / 'recorded.bin').write_bytes(struct.pack('<26I', *recorded))
    info = {'mode': 'native-call-command-substitution', 'autonomous_replay': False,
            'native_trace': str(args.trace.resolve()), 'pid': pid, 'base': hex(base),
            'effect_check': effects, 'restore_check': restored, 'draft': draft,
            'mismatch_behavior': 'Original user command proceeds unchanged; no cancellation is provided',
            'armed': args.arm}
    (run / 'metadata.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    if not args.arm:
        print(json.dumps({'prepared': True, 'armed': False, 'directory': str(run)}), flush=True)
        return
    log = run / 'trace.jsonl'
    process = subprocess.Popen([str(ROOT / 'replay_submit.exe'), str(pid), hex(base), '0x1d1940',
                                str(args.timeout), str(log), str(run / 'expected.bin'), str(run / 'recorded.bin')],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    deadline = time.monotonic() + 12
    armed = False
    while time.monotonic() < deadline and process.poll() is None:
        try:
            events = [json.loads(line) for line in log.read_text().splitlines() if line]
            if any(e['event'] == 'armed' for e in events):
                armed = True
                break
            if any(e['event'] == 'error' for e in events):
                break
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(.05)
    print(json.dumps({'armed': armed, 'probe_pid': process.pid, 'trace_path': str(log)}), flush=True)
    _, error = process.communicate(timeout=args.timeout + 20)
    print(log.read_text(), flush=True)
    if error:
        print(error.decode(errors='replace'), flush=True)
    raise SystemExit(process.returncode)


if __name__ == '__main__':
    main()
