"""Build/schema checks and two local production-DLL instances; zero game loads."""
import argparse
import ctypes as C
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import b_warm_profile_contract as wire

P = Path(__file__).resolve().parent
PRIVATE = P.parents[2] / 'mod_research'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def schema_source():
    lines = ['#include "b_warm_profile.h"', '#include "b_warm_retire_session.h"',
             '#include <cstdio>', '#include <cstddef>', 'int main(){puts("{");']
    for i, (name, kind) in enumerate(wire.TYPES.items()):
        cpp = {'FileProfile': 'checkpoint_dynamic_file_profile::Profile',
               'RetireReport': 'b_warm_retire::Report'}.get(name, 'b_warm_profile::' + name)
        prefix = ',' if i else ''
        lines.append('printf(' + json.dumps(prefix + '"' + name + '":{"size":%zu,"fields":{') + f',sizeof({cpp}));')
        for j, (field, _) in enumerate(kind._fields_):
            label = (',' if j else '') + '"' + field + '":{"offset":%zu,"size":%zu}'
            lines.append('printf(' + json.dumps(label) + f',offsetof({cpp},{field}),sizeof((({cpp}*)0)->{field}));')
        lines.append('printf("}}");')
    lines.append('puts("}");return 0;}')
    return '\n'.join(lines) + '\n'


def rejected(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('Expected validation rejection')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    dll = args.dll.resolve(strict=True)
    if not re.fullmatch('[0-9a-f]{64}', args.expected_sha256) or sha(dll) != args.expected_sha256:
        parser.error('Exact approved build hash required')
    run = PRIVATE / 'b_warm_profile_abi_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    pins = {}

    def pin(p):
        p = p.resolve()
        if str(p) in pins:
            return
        pins[str(p)] = sha(p)
        if p.suffix in ('.h', '.cpp'):
            for name in re.findall(r'#include "([^"]+)"', p.read_text()):
                include = P / name
                if include.exists():
                    pin(include)

    for name in ('b_warm_profile_contract.py', 'b_warm_profile_abi_test.py', 'b_warm_profile_abi_test.cpp',
                 'b_warm_profile.h', 'b_warm_retire_session.h', 'checkpoint_complete_live_owner_contract.py'):
        pin(P / name)
    result = dict(result='FAIL', game_access=False, successful_native_loads=0,
                  same_six_slots_handoff_tested=False, production_dll=str(dll), dll_sha256=sha(dll))
    try:
        (run / 'schema.cpp').write_text(schema_source())
        build = ['@echo off', 'call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul',
                 'if errorlevel 1 exit /b 1']
        for source, output in ((run / 'schema.cpp', 'schema'), (P / 'b_warm_profile_abi_test.cpp', 'runner')):
            build += [f'cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /I"{P}" /Fe:"{run / (output + ".exe")}" /Fo:"{run / (output + ".obj")}" "{source}"', 'if errorlevel 1 exit /b 1']
        (run / 'build.cmd').write_text('\n'.join(build) + '\n')
        proc = subprocess.run(['cmd', '/c', str(run / 'build.cmd')], capture_output=True, timeout=120, cwd=run)
        (run / 'build.log').write_bytes(proc.stdout + proc.stderr)
        assert proc.returncode == 0, 'ABI test build'
        proc = subprocess.run([str(run / 'schema.exe')], capture_output=True, timeout=15)
        (run / 'schema.json').write_bytes(proc.stdout)
        assert proc.returncode == 0
        schema = json.loads(proc.stdout)
        for name, kind in wire.TYPES.items():
            assert schema[name]['size'] == C.sizeof(kind), name
            assert set(schema[name]['fields']) == {n for n, _ in kind._fields_}
            for field, typ in kind._fields_:
                assert schema[name]['fields'][field] == dict(offset=getattr(kind, field).offset, size=C.sizeof(typ)), (name, field)
        copies = []
        for name in ('bank1', 'bank2'):
            directory = run / name
            directory.mkdir()
            copy = directory / 'warm_profile.dll'
            shutil.copyfile(dll, copy)
            assert sha(copy) == args.expected_sha256
            copies.append(copy)
        proc = subprocess.run([str(run / 'runner.exe'), *map(str, copies), str(run / 'reports.bin')], capture_output=True, timeout=25)
        (run / 'run.log').write_bytes(proc.stdout + proc.stderr)
        assert proc.returncode == 0, 'actual local DLL ABI/independence checks'
        raw = (run / 'reports.bin').read_bytes()
        offset = 0
        observed = {}
        for kind in (wire.Description, wire.Report, wire.RetireReport):
            observed[kind] = []
            for _ in range(2):
                size = C.sizeof(kind)
                chunk = raw[offset:offset + size]
                observed[kind].append(wire.decode(kind, chunk))
                rejected(lambda: wire.decode(kind, chunk[:-1]))
                offset += size
        assert offset == len(raw)
        assert observed[wire.Description][0].bank.module != observed[wire.Description][1].bank.module
        first, second = observed[wire.Report]
        assert first.configured == 1 and first.ready == 0 and first.error != 0
        assert second.configured == second.ready == 1 and second.profile.currentForce == 2 and second.profile.loaded.day == 21
        valid = bytes(second)
        second.ready = 2
        rejected(lambda: wire.decode(wire.Report, bytes(second)))
        second = wire.decode(wire.Report, valid)
        for field, value in (('slot', 64), ('size', 0)):
            changed = wire.Profile.from_buffer_copy(bytes(second.profile))
            setattr(changed.file, field, value)
            rejected(lambda: wire.validate_profile(changed))
        initial_retire = observed[wire.RetireReport][1]
        status = wire.status(second, initial_retire)
        assert status['profile_captured'] and not any(status[k] for k in ('load_completed_proven', 'can_install_next_bank', 'two_player_ready'))
        bad_retire = wire.RetireReport.from_buffer_copy(bytes(initial_retire))
        bad_retire.restored = 1
        rejected(lambda: wire.decode(wire.RetireReport, bytes(bad_retire)))
        assert all(sha(Path(p)) == h for p, h in pins.items()) and sha(dll) == args.expected_sha256
        result.update(result='PASS', schema_types=len(wire.TYPES), actual_distinct_dlls=2,
                      independent_once_and_stop=True, exact_captured_profile=True,
                      captured_profile_not_load_success=True, child_exit=proc.returncode)
    except Exception as exc:
        result['error'] = repr(exc)
    result['source_sha256'] = pins
    result['sources_unchanged'] = all(sha(Path(p)) == h for p, h in pins.items())
    result['generated_sha256'] = {p.name: sha(p) for p in run.iterdir() if p.suffix in ('.cpp', '.cmd', '.json')}
    result['binary_sha256'] = {str(p.relative_to(run)): sha(p) for p in run.rglob('*') if p.suffix in ('.exe', '.dll', '.obj')}
    (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(result=result['result'], path=str(run / 'result.json'), error=result.get('error'))))
    return 0 if result['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
