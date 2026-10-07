"""Rebuild and exercise Room -> A local pipe -> new bytes -> TLS, offline.

Only the two named tools below execute. Native game save functions and B load
receipts are fixtures; this never attaches to SAN14 or enables gameplay.
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-root', type=Path,
                        default=os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT'))
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('Owned native fixtures require Windows; no checks ran.')
    if args.fixture_root is None or not args.fixture_root.is_dir():
        parser.error('An existing private --fixture-root is required; no checks ran.')
    private = args.fixture_root.resolve()
    for path in (ROOT, private):
        if any(c in str(path) for c in ('"', '\n', '\r', '%', '&', '|', '<', '>')):
            parser.error('Unsupported native build path; no checks ran.')
    output = ROOT / '.local' / 'dynamic-save' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True)
    env = dict(os.environ, SAN14_PRIVATE_FIXTURE_ROOT=str(private),
               PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    report = dict(schema='san14.offline-dynamic-save.v1', result='RUNNING', steps=[],
        game_access=False, actual_two_games=False, complete_game_pipeline_validated=False,
        native_gameplay_enabled=False, user_actions_required=False,
        note='Dynamic A component requests; game business, world observations and B receipts remain fixtures.')
    build = None
    try:
        for name, script, prefix, schema in (
            ('build', 'a_save_ipc_test_build.py', 'a_save_ipc_runs', 'san14.a-save-ipc-build.v1'),
            ('flow', 'a_save_ipc_flow_test.py', 'a_save_ipc_flow_runs', 'san14.a-save-ipc-flow.v1')):
            command = [sys.executable, str(RESEARCH / script)]
            if name == 'flow':
                if build is None:
                    raise RuntimeError('Missing passing build for dynamic flow')
                command += ['--build-run', str(build)]
            print('Checking ' + name, flush=True)
            row = dict(name=name, script=script, result='FAIL')
            report['steps'].append(row)
            completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                text=True, encoding='utf-8', errors='replace', timeout=300)
            log = output / (name + '.log')
            log.write_text(completed.stdout + completed.stderr, encoding='utf-8')
            row.update(exit=completed.returncode, log=str(log))
            if completed.returncode:
                raise RuntimeError(name + ' failed; see ' + str(log))
            values = []
            for line in completed.stdout.splitlines():
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                if type(value) is dict and 'path' in value:
                    values.append(value)
            if not values:
                raise RuntimeError(name + ' produced no result artifact')
            path = Path(values[-1]['path']).resolve()
            if not path.is_relative_to((RESEARCH / prefix).resolve()) or path.name != 'result.json':
                raise RuntimeError(name + ' result is outside its owned output directory')
            raw = path.read_bytes()
            details = json.loads(raw)
            if details.get('schema') != schema or details.get('result') != 'PASS' or details.get('game_access') is not False:
                raise RuntimeError(name + ' did not produce a passing offline result')
            if name == 'build' and details.get('sources_unchanged') is not True:
                raise RuntimeError('Build sources changed')
            if name == 'flow' and (details.get('skipped') != 0 or not details.get('build_evidence')):
                raise RuntimeError('Native dynamic flow was skipped')
            row.update(result='PASS', report=str(path), result_sha256=hashlib.sha256(raw).hexdigest())
            if name == 'build':
                build = path.parent
            else:
                row['unittest_cases'] = details['tests_run']
            print(name + ': PASS', flush=True)
        report['result'] = 'PASS'
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        report.update(result='FAIL', error=str(exc))
    target = output / 'summary.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(result=report['result'], path=str(target),
                         complete_game_pipeline_validated=False)))
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
