"""Build one real consumer publisher; exercise only owned fixture processes."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

P = Path(__file__).resolve().parent
CASES = ('open', 'held', 'two-saves', 'release', 'stop-held', 'inflight-stop',
         'pending-menu', 'wrong-world', 'foreign-ui', 'unknown-modal',
         'ui-exception', 'stop-before-arm', 'source-drift', 'panel-bypass', 'source-conflict')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    private_text = os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT', '')
    if not private_text or any(c in private_text for c in ('"', '\n', '%', '&', '|', '<', '>')):
        raise SystemExit('Set SAN14_PRIVATE_FIXTURE_ROOT; no tests ran.')
    private = Path(private_text).resolve()
    profile = private / 'checkpoint_push_profile.h'
    if not profile.is_file():
        raise SystemExit('Missing private checkpoint_push_profile.h; no tests ran.')
    private_hash = sha(profile)
    run = P / 'a_save_input_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    units = dict(input='a_save_input.cpp', input_bridge='a_save_input_bridge.cpp',
        owner='a_save_user_owner.cpp', bridge='a_save_user_owner_bridge.cpp',
        driver='checkpoint_fresh_save.cpp', binding='checkpoint_live_storage_binding.cpp',
        gate='checkpoint_serialized_storage_gate.cpp', hooks='checkpoint_load_hook_set.cpp',
        storage='native_storage_read_core.cpp', inspector='checkpoint_native_input_pending_adapter.cpp',
        packet='checkpoint_fresh_save_packet.cpp')
    asm = dict(input_asm='a_save_input_bridge.asm', bridge_asm='a_save_user_owner_bridge.asm',
        fixture_asm='a_save_user_owner_fixture.asm', input_fixture_asm='a_save_input_fixture.asm',
        context_asm='checkpoint_live_storage_binding_fixture.asm')
    todo = [*units.values(), *asm.values(), 'a_save_input_test.py', 'a_save_input_fixture.cpp']
    sources = {}
    while todo:
        name = todo.pop()
        if name in sources or name == 'checkpoint_push_profile.h':
            continue
        path = P / name
        if not path.is_file():
            raise SystemExit('Missing source dependency: ' + name)
        sources[name] = sha(path)
        todo.extend(re.findall(r'^\s*#include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.M))
    vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags = f'/nologo /std:c++17 /EHa /W4 /WX /wd4324 /O2 /MT /I"{private}"'
    commands = [f'cl {flags} /c "{P / source}" /Fo:{name}.obj' for name, source in units.items()]
    commands += [f'ml64 /nologo /c /Fo {name}.obj "{P / source}"' for name, source in asm.items()]
    commands += ['lib /nologo /OUT:a_save_input.lib input.obj input_bridge.obj input_asm.obj hooks.obj inspector.obj storage.obj']
    defines = '/DA_SAVE_INPUT_FIXTURE /DA_SAVE_USER_OWNER_FIXTURE /DCHECKPOINT_FRESH_SAVE_FIXTURE'
    commands += [f'cl {flags} {defines} /c "{P / units[n]}" /Fo:fixture_{n}.obj' for n in ('input', 'owner', 'driver')]
    commands += [f'cl {flags} /DCHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE /c "{P / units["binding"]}" /Fo:fixture_binding.obj',
        f'cl {flags} {defines} /c "{P / "a_save_input_fixture.cpp"}" /Fo:fixture.obj',
        'link /nologo /OUT:fixture.exe fixture_input.obj fixture_owner.obj fixture_driver.obj fixture_binding.obj input_bridge.obj bridge.obj gate.obj hooks.obj storage.obj inspector.obj packet.obj fixture.obj ' + ' '.join(n+'.obj' for n in asm) + ' bcrypt.lib']
    build = run / 'build.cmd'
    build.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n' + '\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
    process = subprocess.run(['cmd', '/c', str(build)], cwd=run, capture_output=True, text=True, errors='replace')
    (run/'build.log').write_text(process.stdout+process.stderr, encoding='utf-8')
    if process.returncode:
        print(process.stdout+process.stderr)
        raise SystemExit(process.returncode)
    binary_sha = sha(run/'fixture.exe')
    rows = []
    for case in CASES:
        directory = run/case
        directory.mkdir()
        proc = subprocess.run([str(run/'fixture.exe'), case, str(directory), binary_sha], cwd=run,
                              capture_output=True, text=True, timeout=30)
        try:
            row = json.loads(proc.stdout)
        except ValueError:
            row = dict(case=case, result='FAIL', stdout=proc.stdout)
        row.update(exit=proc.returncode, stderr=proc.stderr)
        rows.append(row)
        print(case, row['result'], proc.stderr, flush=True)
    unchanged = sha(profile) == private_hash and all(sha(P/n) == h for n,h in sources.items())
    result = dict(schema='san14.a-save-input-global-ui-owned.v1',
        result='PASS' if unchanged and all(r['result']=='PASS' and r['exit']==0 for r in rows) else 'FAIL',
        cases=rows, sources=sources, sources_unchanged=unchanged,
        private_inputs={'checkpoint_push_profile.h':private_hash},
        production_sha256=sha(run/'a_save_input.lib'), fixture_sha256=binary_sha,
        game_access=False, steam_access=False, all_input_held=False, save_authorized=False,
        room_ready=False, actual_vtable_publication=True, actual_indirect_dispatch=True,
        existing_a_owner_two_saves_composed=True,
        scope='Actual independent Game/global-UI slot CAS, original page protection, PE bridges, scoped TLS/FINALLY; unchanged A Owner raw User/Save lifecycle and native API readback composed. Game/global-UI/User/Save business and Steam methods remain own-process doubles. One consumer source only, not full input exclusion.')
    path = run/'result.json'
    path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'result':result['result'], 'path':str(path)}))
    raise SystemExit(result['result']!='PASS')


if __name__ == '__main__':
    main()
