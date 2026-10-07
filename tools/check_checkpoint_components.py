"""Explicit offline native-component and TLS checks. Never attaches to SAN14.

Builds owned child-process fixtures using local private reference inputs. A
pass is not a two-game match or a successful game save/reload cycle. No legacy
live launcher, process enumeration, or automatic native installation is used.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'work' / 'mod_research'
STEPS = (
    ('codec', 'checkpoint_fresh_save_packet_test.py', 'checkpoint_fresh_save_packet_runs'),
    ('host_owner', 'a_save_user_owner_test.py', 'a_save_user_owner_runs'),
    ('guest_title_source', 'b_reload_title_source_test.py', 'b_reload_title_source_runs'),
    ('binding_and_tls', 'checkpoint_fresh_save_binding_test.py', 'checkpoint_fresh_save_binding_runs'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-root', type=Path,
                        default=os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT'),
                        help='Existing local private profiles/runtime/archive directory; read only.')
    args = parser.parse_args()
    if args.fixture_root is None or not args.fixture_root.is_dir():
        parser.error('An existing --fixture-root is required; no checks ran.')
    fixture_root = args.fixture_root.resolve()
    if os.name != 'nt':
        parser.error('Native fixtures require Windows; no checks ran.')
    for path in (ROOT, fixture_root):
        if any(c in str(path) for c in ('"', '\n', '\r', '%', '&', '|', '<', '>')):
            parser.error('Native build scripts cannot use this path; no checks ran.')
    folder = ROOT / '.local' / 'checkpoint-components' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    environment = dict(os.environ, SAN14_PRIVATE_FIXTURE_ROOT=str(fixture_root),
                       PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    summary = dict(schema='san14.offline-checkpoint-components.v1', result='RUNNING', steps=[],
        game_access=False, native_gameplay_enabled=False, actual_two_games=False,
        complete_game_pipeline_validated=False, user_actions_required=False,
        note='Owned native components and TLS artifacts; native game business and world observations are fixtures.')
    owner_run = None
    try:
        for name, script, prefix in STEPS:
            command = [sys.executable, str(RESEARCH/script)]
            if name == 'binding_and_tls':
                if owner_run is None:
                    raise RuntimeError('No successful host owner run to connect to transport')
                command += ['--owner-run', str(owner_run)]
            print('Checking ' + name, flush=True)
            completed = subprocess.run(command, cwd=ROOT, env=environment,
                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
            log = folder / (name + '.log')
            log.write_text(completed.stdout + completed.stderr, encoding='utf-8')
            row = dict(name=name, script=script, exit=completed.returncode, result='FAIL', log=str(log))
            summary['steps'].append(row)
            if completed.returncode != 0:
                raise RuntimeError(name + ' failed; see ' + str(log))
            notifications = []
            for line in completed.stdout.splitlines():
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                if type(value) is dict and 'path' in value:
                    notifications.append(value)
            if not notifications:
                raise RuntimeError(name + ' returned no result artifact')
            path = Path(notifications[-1]['path']).resolve()
            if not path.is_relative_to((RESEARCH/prefix).resolve()) or path.name != 'result.json':
                raise RuntimeError(name + ' returned a result outside its owned run directory')
            raw = path.read_bytes()
            report = json.loads(raw)
            if report.get('result') != 'PASS' or report.get('game_access') is not False:
                raise RuntimeError(name + ' did not pass an offline-only check')
            if name == 'binding_and_tls' and (report.get('actual_native_fixture_packets_checked') is not True
                                              or report.get('skipped') != 0):
                raise RuntimeError('Binding did not check this run\'s native fixture exports')
            row.update(result='PASS', report=str(path), result_sha256=hashlib.sha256(raw).hexdigest())
            if 'tests_run' in report:
                row['unittest_cases'] = report['tests_run']
            if 'cases' in report:
                row['native_scenarios'] = len(report['cases'])
            if name == 'host_owner':
                owner_run = path.parent
            print(name + ': PASS', flush=True)
        summary['result'] = 'PASS'
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        summary['result'], summary['error'] = 'FAIL', str(exc)
    target = folder / 'summary.json'
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': summary['result'], 'path': str(target),
                      'complete_game_pipeline_validated': False}))
    return 0 if summary['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
