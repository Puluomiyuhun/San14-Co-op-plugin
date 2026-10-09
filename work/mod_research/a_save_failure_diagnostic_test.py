"""Actual RPM against an owned child/DLL; never enumerate or attach to a game."""
import ctypes as C
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
PRIVATE = P.parents[2] / 'mod_research'
sys.path.insert(0, str(PRIVATE / 'python_deps'))
import a_save_failure_diagnostic as d
from a_save_runtime_control import save_new


def worker(path):
    dll = C.WinDLL(path)
    value = (C.c_ubyte * d.FORMAT.size).in_dll(dll, d.EXPORT.decode())
    probe = d.ReadOnlyProcess(os.getpid())
    try:
        birth, image = probe.identity()
    finally:
        probe.close()
    print(json.dumps(dict(pid=os.getpid(), birth=birth, image=str(image), module=dll._handle)), flush=True)
    for line in sys.stdin:
        command = line.strip()
        if command == 'exit':
            break
        if command == 'publish':
            # Only the child writes its own fixture DATA. The diagnostic reader
            # receives no write handle and cannot execute a target export.
            fields = (d.FORMAT.size, 1, 5, 1, 0x10000, 0x20000, 0x30000, 1, 1, 3, 1, 11, 27, 4)
            value[:] = d.FORMAT.pack(*fields)
        elif command == 'badversion':
            value[4] = 2
        else:
            raise RuntimeError('Unknown fixture command')
        print('OK', flush=True)


def rejects(callback, fragment):
    try:
        callback()
    except RuntimeError as error:
        assert fragment in str(error), (fragment, error)
    else:
        raise AssertionError('Expected refusal: ' + fragment)


def main():
    run = PRIVATE / 'a_save_failure_diagnostic_test_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    names = ('a_save_failure_diagnostic.py', 'a_save_failure_diagnostic_test.py',
             'a_save_diagnostic_start.py', 'a_save_covered_gate.h', 'a_save_runtime_control.py')
    pins = {n: d.digest(P / n) for n in names}
    report = dict(result='FAIL', game_access=False, target_calls=0, target_writes=0,
                  cases=[], sources=pins, owned_child_exited=False)
    child = None
    try:
        cpp = run / 'diagnostic_data.cpp'
        cpp.write_text('''#include "a_save_covered_gate.h"
#include <cstdio>
extern "C" {alignas(8) ASaveCoveredGateFailure ASaveCoveredGateFirstFailure={sizeof(ASaveCoveredGateFailure),1};}
int main(){std::printf("%zu %zu\\n",sizeof(ASaveCoveredGateFailure),offsetof(ASaveCoveredGateFailure,stage));}
''', encoding='utf-8')
        vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
        cmd = run / 'build.cmd'
        cmd.write_text('@echo off\ncall "' + vc + '" >nul\nif errorlevel 1 exit /b 1\n'
            'cl /nologo /std:c++17 /W4 /WX /EHsc /MT /I"' + str(P) + '" diagnostic_data.cpp /Fe:schema.exe\n'
            'if errorlevel 1 exit /b 1\n'
            'cl /nologo /std:c++17 /W4 /WX /EHsc /MT /LD /I"' + str(P) + '" diagnostic_data.cpp /Fe:diagnostic_data.dll\n', encoding='utf-8')
        build = subprocess.run(['cmd', '/c', str(cmd)], cwd=run, capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=60)
        (run / 'build.log').write_text(build.stdout + build.stderr, encoding='utf-8')
        assert build.returncode == 0, 'Fixture build failed'
        schema = subprocess.run([str(run / 'schema.exe')], capture_output=True, text=True, timeout=10, check=True)
        assert schema.stdout.strip() == f'{d.FORMAT.size} 80'
        report['cases'].append('actual_cpp_packed_layout_matches')
        dll = run / 'diagnostic_data.dll'
        dll_hash = d.digest(dll)
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--worker', str(dll)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
        identity = json.loads(child.stdout.readline())
        assert identity['pid'] == child.pid
        image = Path(identity['image'])
        args = (child.pid, identity['birth'], image, d.digest(image), identity['module'], dll, dll_hash)
        not_yet = d.observe(*args)
        save_new(run / 'not-published.json', not_yet)
        assert not_yet['status'] == 'NOT_PUBLISHED' and not_yet['first_failure'] is None
        report['cases'].append('actual_unpublished_export_not_reported_as_success')
        child.stdin.write('publish\n'); child.stdin.flush()
        assert child.stdout.readline().strip() == 'OK'
        found = d.observe(*args)
        save_new(run / 'published.json', found)
        assert found['status'] == 'FIRST_FAILURE_OBSERVED'
        assert found['first_failure']['stage'] == 4 and found['first_failure']['queueCount'] == 1
        assert found['restore_permission'] is False and found['save_accepted'] is False
        assert found['target_calls'] == 0 and d.READ_RIGHTS == 0x100410
        report['cases'].append('actual_data_export_observed_with_query_read_wait_only')
        bad = list(args); bad[1] += 1
        rejects(lambda: d.observe(*bad), 'process identity changed')
        report['cases'].append('wrong_process_birth_rejected')
        bad = list(args); bad[4] += 4096
        rejects(lambda: d.observe(*bad), 'module identity changed')
        report['cases'].append('wrong_loaded_module_rejected')
        bad = list(args); bad[6] = '0' * 64
        rejects(lambda: d.observe(*bad), 'DLL file identity differs')
        report['cases'].append('wrong_dll_file_rejected')
        bad = list(args); bad[3] = '0' * 64
        rejects(lambda: d.observe(*bad), 'process image differs')
        report['cases'].append('wrong_executable_rejected')
        child.stdin.write('badversion\n'); child.stdin.flush()
        assert child.stdout.readline().strip() == 'OK'
        rejects(lambda: d.observe(*args), 'layout/version differs')
        report['cases'].append('actual_unknown_data_version_rejected')
        empty = d.FORMAT.pack(84, 1, *([0] * 12))
        final = bytes.fromhex(found['raw_samples'][0])
        assert d.decode_pair(empty, final)['status'] == 'UNSTABLE'
        assert d.decode_pair(final, empty)['status'] == 'UNSTABLE'
        half = bytearray(empty); half[16] = 1
        assert d.decode_pair(empty, bytes(half))['status'] == 'NOT_PUBLISHED'
        report['cases'].append('publication_transition_never_promoted_to_stable_failure')
        rejects(lambda: d.decode_pair(empty[:-1], empty), 'Incomplete')
        report['cases'].append('short_read_rejected')
        child.stdin.write('exit\n'); child.stdin.flush()
        stdout, stderr = child.communicate(timeout=10)
        assert child.returncode == 0 and not stdout and not stderr, (stdout, stderr)
        report['owned_child_exited'] = True
        assert all(d.digest(P / n) == h for n, h in pins.items())
        report.update(result='PASS', sources_unchanged=True,
                      fixture_dll_sha256=dll_hash, read_rights=d.READ_RIGHTS)
    except Exception as error:
        report['error'] = repr(error)
    finally:
        if child and child.poll() is None:
            # This is only our disposable fixture; request its normal exit.
            try:
                child.stdin.write('exit\n'); child.stdin.flush()
                child.communicate(timeout=10)
                report['owned_child_exited'] = child.returncode == 0
            except Exception as error:
                report['cleanup_error'] = repr(error)
        save_new(run / 'result.json', report)
    print(json.dumps(dict(result=report['result'], cases=len(report['cases']), path=str(run / 'result.json'))))
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        worker(sys.argv[2])
    else:
        raise SystemExit(main())
