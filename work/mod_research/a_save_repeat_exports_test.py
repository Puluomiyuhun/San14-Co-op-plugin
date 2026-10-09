"""Compile and execute additive ABI checks in an owned process; never touch game.

Pass --dll from a successful repeat Runtime production build. The frozen legacy
ABI/schema tests are also required by that build, independently of this test.
"""
import argparse
import ctypes as C
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

import a_save_repeat_contract as wire

P = Path(__file__).resolve().parent
PRIVATE = P.parents[2] / 'mod_research'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schema_source():
    lines = ['#include "a_save_repeat_exports.h"', '#include <cstdio>', '#include <cstddef>',
             'namespace rw=a_save_repeat_wire;', 'int main(){puts("{\\\"structures\\\":{");']
    for i, (name, kind) in enumerate(wire.TYPES.items()):
        cpp = 'rw::' + ('Snapshot' if name == 'RepeatSnapshot' else name)
        prefix = ',' if i else ''
        lines.append(f'printf("{prefix}\\\"{name}\\\":{{\\\"size\\\":%zu,\\\"fields\\\":{{",sizeof({cpp}));')
        for j, (field, _) in enumerate(kind._fields_):
            prefix = ',' if j else ''
            lines.append(f'printf("{prefix}\\\"{field}\\\":{{\\\"offset\\\":%zu,\\\"size\\\":%zu}}",offsetof({cpp},{field}),sizeof((({cpp}*)0)->{field}));')
        lines.append('printf("}}");')
    lines.append('puts("}}");return 0;}')
    return '\n'.join(lines).replace('\\\"', '\\"') + '\n'


def contract_checks(schema):
    for name, kind in wire.TYPES.items():
        native = schema['structures'][name]
        assert native['size'] == C.sizeof(kind), name
        assert set(native['fields']) == {f for f, _ in kind._fields_}
        for field, typ in kind._fields_:
            assert native['fields'][field] == dict(offset=getattr(kind, field).offset, size=C.sizeof(typ)), (name, field)
    nonce = bytes([0x37]) * 32
    obj = wire.envelope(wire.Snapshot, 'RepeatSnapshot', nonce)
    obj.state = 3
    decoded = wire.decode(wire.Snapshot, 'RepeatSnapshot', nonce, bytes(obj))
    description = wire.describe(decoded)
    assert description['waiting_for_native_date'] and not description['can_advance_game'] and not description['two_player_ready']
    def rejected(call):
        try:
            call()
        except ValueError:
            return
        raise AssertionError('Expected rejection')
    rejected(lambda: wire.decode(wire.Snapshot, 'RepeatSnapshot', bytes([1]) * 32, bytes(obj)))
    rejected(lambda: wire.decode(wire.Snapshot, 'RepeatSnapshot', nonce, bytes(obj)[:-1]))
    rejected(lambda: wire.envelope(wire.Next, 'RepeatSnapshot', nonce))
    obj.state = 4
    rejected(lambda: wire.describe(obj))
    obj.requested = 1
    obj.activeGeneration = 2
    obj.retiredCount = 1
    obj.retiredSerial = 1
    obj.hostThread = 123
    obj.previousArtifactMatched = 1
    obj.nativeDateMatched = 1
    obj.request.previousGeneration = 1
    obj.request.generation = 2
    assert wire.describe(obj)['second_save_binding_ready']
    obj.drainPending = 1
    assert not wire.describe(obj)['second_save_binding_ready']
    obj.drainPending = 0
    obj.bLoadedProven = 1
    rejected(lambda: wire.describe(obj))
    obj.bLoadedProven = 0
    obj.simulationEnabled = 1
    rejected(lambda: wire.describe(obj))
    obj.simulationEnabled = 0
    obj.header.result = 6
    rejected(lambda: wire.describe(obj))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dll', type=Path, required=True)
    args = parser.parse_args()
    dll = args.dll.resolve(strict=True)
    run = PRIVATE / 'a_save_repeat_exports_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    names = ('a_save_repeat_exports_test.py', 'a_save_repeat_exports_test.cpp',
             'a_save_repeat_exports.h', 'a_save_repeat_exports.cpp', 'a_save_repeat_contract.py',
             'a_save_runtime_exports.h', 'a_save_runtime_contract.py', 'a_save_repeat_runtime.h')
    pins = {name: sha(P / name) for name in names}
    result = dict(result='FAIL', game_process_access=False, steam_save_access=False,
                  sources=pins, dll=str(dll), dll_sha256=sha(dll), native_repeat_success_tested=False)
    try:
        cpp = run / 'schema.cpp'
        cpp.write_text(schema_source(), encoding='utf-8')
        vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
        cmd = run / 'build.cmd'
        cmd.write_text('@echo off\ncall "' + vc + '" >nul\nif errorlevel 1 exit /b 1\n'
            + 'cl /nologo /std:c++17 /W4 /WX /EHsc /MT /I"' + str(P) + '" "' + str(cpp) + '" /Fe:schema.exe\nif errorlevel 1 exit /b 1\n'
            + 'cl /nologo /std:c++17 /W4 /WX /EHsc /MT /I"' + str(P) + '" "' + str(P / 'a_save_repeat_exports_test.cpp') + '" /Fe:abi.exe\n', encoding='utf-8')
        child = subprocess.run(['cmd', '/c', str(cmd)], cwd=run, capture_output=True, text=True, errors='replace', timeout=90)
        (run / 'build.log').write_text(child.stdout + child.stderr, encoding='utf-8')
        assert child.returncode == 0, 'ABI compile'
        child = subprocess.run([str(run / 'schema.exe')], capture_output=True, text=True, timeout=10)
        assert child.returncode == 0
        schema = json.loads(child.stdout)
        (run / 'schema.json').write_text(json.dumps(schema, indent=2) + '\n', encoding='utf-8')
        contract_checks(schema)
        child = subprocess.run([str(run / 'abi.exe'), str(dll)], cwd=dll.parent, capture_output=True, text=True, errors='replace', timeout=30)
        (run / 'abi.log').write_text(child.stdout + child.stderr, encoding='utf-8')
        assert child.returncode == 0, 'actual DLL ABI checks'
        assert sha(dll) == result['dll_sha256'] and all(sha(P / n) == digest for n, digest in pins.items())
        result.update(result='PASS', abi_executed=True, schema_fields_verified=True, contract_checks_passed=True)
    except Exception as error:
        result['error'] = repr(error)
    result['generated'] = {p.name: sha(p) for p in run.iterdir() if p.is_file() and p.suffix in ('.cpp', '.cmd', '.exe', '.obj', '.json')}
    output = run / 'result.json'
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(result=result['result'], path=str(output))))
    return 0 if result['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
