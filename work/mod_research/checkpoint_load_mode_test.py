"""Own-process fixtures for the mode-only DLL. Never discovers a game PID."""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
CASES = (
    'dry', 'execute', 'capacity-zero',
    'initial-mode', 'initial-pending', 'initial-selection', 'initial-foreign-table',
    'initial-group-cycle', 'initial-group-count', 'initial-head-node-overlap',
    'initial-node-node-overlap', 'initial-head-head-overlap', 'existing-journal',
    'stop-before-user', 'stop-during-user', 'user-after-drift', 'user-original-seh', 'user-original-cpp',
    'queue-seh', 'queue-wrong-kind', 'queue-wrong-state', 'stop-during-queue',
    'menu-before-selection', 'menu-wrong-top', 'menu-table-alias', 'menu-after-selection', 'menu-load-pending',
    'native-cancel', 'native-double-cancel', 'menu-original-seh', 'menu-original-cpp',
    'menu-worker-migration', 'return-worker-migration', 'both-worker-migration', 'stop-during-menu',
    'duplicate-menu', 'cancel-seh', 'cancel-wrong-kind', 'stop-during-cancel', 'return-rng-drift', 'report-lock-seh',
)
SOURCES = (
    'checkpoint_load_mode_pilot.h', 'checkpoint_load_mode_pilot.cpp',
    'checkpoint_load_mode_callbacks.inc', 'checkpoint_load_mode_guard.inc',
    'checkpoint_load_mode_profile.h', 'checkpoint_load_mode_profile.json',
    'checkpoint_load_mode_fixture.cpp', 'checkpoint_load_mode_build.cmd', 'checkpoint_load_mode_test.py',
    'checkpoint_push_bridge.h', 'checkpoint_push_bridge.cpp', 'checkpoint_push_bridge.asm',
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint():
    return {name: sha(ROOT / name) for name in SOURCES}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--skip-build', action='store_true')
    args = p.parse_args()
    run = ROOT / 'checkpoint_load_mode_fixtures' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True, exist_ok=False)
    source_before = fingerprint()
    if not args.skip_build:
        built = subprocess.run(['cmd.exe', '/d', '/c', str(ROOT / 'checkpoint_load_mode_build.cmd')],
              cwd=ROOT, capture_output=True, text=True, encoding='utf8', errors='replace', timeout=60)
        (run / 'build.txt').write_text(built.stdout + built.stderr, encoding='utf8')
        assert built.returncode == 0, str(run / 'build.txt')
    binary_hashes = {name: sha(ROOT / name) for name in ('checkpoint_load_mode_pilot.dll',
                    'checkpoint_load_mode_fixture.dll', 'checkpoint_load_mode_fixture.exe')}
    rows = []
    for case in CASES:
        folder = run / case
        folder.mkdir()
        row = {'case': case, 'passed': False, 'exit_code': None, 'game_access': False}
        try:
            got = subprocess.run([str(ROOT / 'checkpoint_load_mode_fixture.exe'), case, str(folder / 'once.intent')],
                  cwd=ROOT, capture_output=True, text=True, encoding='utf8', errors='replace', timeout=15)
            (folder / 'stdout.txt').write_text(got.stdout + got.stderr, encoding='utf8')
            lines = [line for line in got.stdout.splitlines() if line.startswith('{')]
            if lines:
                row.update(json.loads(lines[-1]))
            row['exit_code'] = got.returncode
            row['passed'] = bool(got.returncode == 0 and row['passed'] and row.get('failures') == 0 and
                row.get('callback_active') == 0 and row.get('game_access') is False and
                row.get('fixture_config_bytes') == 1120 and row.get('report_bytes') == 592)
        except subprocess.TimeoutExpired as error:
            row['error'] = 'OWN_PROCESS_FIXTURE_TIMEOUT'
            text = error.stdout or b''
            (folder / 'timeout.txt').write_bytes(text if isinstance(text, bytes) else text.encode('utf8'))
        rows.append(row)
    consistent = source_before == fingerprint() and all(sha(ROOT / n) == h for n, h in binary_hashes.items())
    result = {'schema': 'san14.checkpoint-load-mode-fixtures.v1',
        'result': 'PASS' if consistent and all(row['passed'] for row in rows) else 'FAIL',
        'source_sha256': source_before, 'sources_and_binaries_stable': consistent,
        'dll_sha256': binary_hashes['checkpoint_load_mode_pilot.dll'],
        'fixture_dll_sha256': binary_hashes['checkpoint_load_mode_fixture.dll'],
        'fixture_binary_sha256': binary_hashes['checkpoint_load_mode_fixture.exe'],
        'production_config_bytes': 1104, 'report_bytes': 592, 'cases': rows,
        'game_process_access': False, 'native_gameplay_enabled': False,
        'scope': 'Own EXE and isolated fake memory. Real bridge and pilot guards execute; game dispatcher/UI are fixture actions. Native instruction lifecycle has separate VM evidence.'}
    with (run / 'result.json').open('x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'result': result['result'], 'cases': len(rows), 'failed': [r['case'] for r in rows if not r['passed']], 'path': str(run / 'result.json'), 'game_process_access': False}))
    if result['result'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
