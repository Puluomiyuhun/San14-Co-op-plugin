"""Compile production core; owned files/cache only, no game or Steam access."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT.parents[2] / 'mod_research' / 'b_warm_storage_refresh_runs'
CASES = ('two-generations', 'wrong-previous', 'wrong-name', 'previous-second-no-write', 'target-read-lock', 'readback-corrupt')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    out = PRIVATE / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True)
    names = ('b_warm_storage_refresh_core.h', 'b_warm_storage_refresh_core.cpp',
             'b_warm_storage_refresh_fixture.cpp', 'b_warm_storage_refresh_test.py',
             'native_storage_read_core.h', 'native_storage_read_core.cpp')
    sources = {str(ROOT/n): sha(ROOT/n) for n in names}
    cmd = out / 'build.cmd'
    cmd.write_text('@echo off\ncall "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\nif errorlevel 1 exit /b 1\npushd "%~dp0"\n'
                   + ''.join(f'cl /nologo /W4 /EHa /std:c++17 /O2 /MT /c /Fo:{obj} "{ROOT/src}"\nif errorlevel 1 exit /b 1\n' for src, obj in (
                       ('native_storage_read_core.cpp', 'read.obj'),
                       ('b_warm_storage_refresh_core.cpp', 'refresh.obj'),
                       ('b_warm_storage_refresh_fixture.cpp', 'fixture.obj')))
                   + 'link /nologo /out:fixture.exe /incremental:no fixture.obj refresh.obj read.obj bcrypt.lib\nexit /b %errorlevel%\n')
    report = {'schema': 'san14.b-warm-storage-refresh.v1', 'result': 'FAIL',
              'sources': sources, 'cases': [], 'game_process_access': False,
              'steam_access': False, 'production_wired': False,
              'native_steam_methods_are_doubles': True}
    try:
        p = subprocess.run(['cmd', '/c', str(cmd)], capture_output=True, text=True, errors='replace', timeout=90)
        (out/'build.log').write_text(p.stdout+p.stderr)
        if p.returncode:
            raise RuntimeError('production core/fixture build failed')
        for case in CASES:
            p = subprocess.run([str(out/'fixture.exe'), case, str(out/case)], capture_output=True, text=True, errors='replace', timeout=20)
            (out/(case+'.log')).write_text(p.stdout+p.stderr)
            row = {'case': case, 'returncode': p.returncode, 'passed': p.returncode == 0}
            if p.returncode == 0:
                row.update(json.loads(p.stdout))
            report['cases'].append(row)
        report['inputs_unchanged'] = all(sha(Path(p)) == h for p, h in sources.items())
        if report['inputs_unchanged'] and all(r['passed'] for r in report['cases']):
            report['result'] = 'PASS'
    except BaseException as exc:
        report['error'] = repr(exc)
    finally:
        report['binaries'] = {str(p): sha(p) for p in out.glob('*') if p.suffix in ('.obj', '.exe')}
        report['generated'] = {str(cmd): sha(cmd)}
        report['artifacts'] = {str(p): sha(p) for p in out.rglob('*') if p.is_file() and p.suffix in ('.log', '.intent', '.s14')}
        (out/'result.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({'result': report['result'], 'path': str(out/'result.json'), 'sha256': sha(out/'result.json')}))
    return report['result'] != 'PASS'

if __name__ == '__main__':
    raise SystemExit(main())
