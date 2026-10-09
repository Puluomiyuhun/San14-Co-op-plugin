"""Build the covered/queued Save successors with the real Runtime ABI.

Offline only. Frozen builders and implementations are never overwritten.
The generated builder diff and complete original failures remain private.
"""
from pathlib import Path
from datetime import datetime
import difflib
import hashlib
import json
import os
import subprocess
import sys

P = Path(__file__).resolve().parent
PRIVATE = P.parents[2] / 'mod_research'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(source, before, after):
    if source.count(before) != 1:
        raise RuntimeError('Frozen builder anchor changed: ' + before)
    return source.replace(before, after, 1)


def main():
    run = PRIVATE / 'a_save_repeat_runtime_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    names = ('a_save_repeat_runtime_build.py', 'a_save_runtime_exports_build.py',
             'a_save_local_runtime_build.py', 'a_save_abort_pending_owner.cpp',
             'a_save_covered_gate.cpp','a_save_abort_host.cpp','a_save_repeat_exports.cpp','a_save_repeat_runtime.h','a_save_repeat_runtime.cpp','a_save_repeat_parent.cpp','a_save_repeat_parent.h','a_save_abort_owner.h','a_save_pending_user_owner.cpp','a_save_pending_user_owner.h')
    pins = {name: sha(P / name) for name in names}
    old = (P / 'a_save_runtime_exports_build.py').read_text(encoding='utf-8')
    source = once(old, '\nP=Path(__file__).resolve().parent\n', '\nP=Path(' + repr(str(P)) + ')\n')
    source = once(source,
        "run=PRIVATE/'a_save_runtime_exports_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)",
        'run=Path(' + repr(str(run / 'abi')) + ');run.mkdir(parents=True)')
    marker = "    script=run/'production_build.py';"
    owner_line = ' s=s.replace("owner=\'planning_checkpoint_save_owner.cpp\'","owner=\'a_save_abort_pending_owner.cpp\'")\n'
    insertion = '''    s=s.replace("input='a_save_scoped_gate.cpp'","input='a_save_covered_gate.cpp'")
    s=s.replace("exports='a_save_runtime_exports.cpp'","exports='a_save_repeat_exports.cpp'")
    s=s.replace("'a_save_dispatch_host.cpp'","'a_save_abort_host.cpp'")
    s=s.replace("runtime='a_save_local_runtime.cpp'","runtime='a_save_repeat_runtime.cpp'")
    s=s.replace("parent='a_save_runtime_publish_parent.cpp'","parent='a_save_repeat_parent.cpp'")
    nested=" start=s.index('    asm = dict(')"
    assert s.count(nested)==1
''' + '    s=s.replace(nested,' + repr(owner_line) + '+nested)\n'
    source = once(source, marker, insertion + marker)
    script = run / 'generated_exports_build.py'
    script.write_text(source, encoding='utf-8')
    (run / 'builder.diff').write_text(''.join(difflib.unified_diff(
        old.splitlines(True), source.splitlines(True))), encoding='utf-8')
    result = dict(result='FAIL', game_access=False, sources=pins)
    try:
        env = os.environ.copy()
        env['PYTHONUTF8'] = '1'
        child = subprocess.run([sys.executable, str(script)], env=env,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
        (run / 'driver.log').write_text(child.stdout + child.stderr, encoding='utf-8')
        report = json.loads((run / 'abi/result.json').read_text(encoding='utf-8'))
        result['execution'] = report
        assert child.returncode == 0 and report['result'] == 'PASS'
        production = report['production']['sources']
        assert production['a_save_abort_pending_owner.cpp'] == pins['a_save_abort_pending_owner.cpp']
        assert production['a_save_covered_gate.cpp'] == pins['a_save_covered_gate.cpp']
        assert 'planning_checkpoint_save_owner.cpp' not in production
        assert 'a_save_scoped_gate.cpp' not in production
        assert all(sha(P / name) == digest for name, digest in pins.items())
        result['result'] = 'PASS'
    except Exception as error:
        result['error'] = repr(error)
    result['generated_sha256'] = sha(script)
    output = run / 'result.json'
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(result=result['result'], path=str(output))))
    return 0 if result['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
