"""Build A's production pipe server and a fresh dynamic owned child fixture.

No game discovery/attachment or test execution. Local private profile is read
only. The flow test must subsequently reserve each request before native Submit.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    private = os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT', '')
    if not private or not (Path(private)/'checkpoint_push_profile.h').is_file():
        raise SystemExit('Missing private checkpoint_push_profile.h; nothing built.')
    private = Path(private).resolve()
    if any(c in str(private) + str(P) for c in ('"', '\n', '\r', '%', '&', '|', '<', '>')):
        raise SystemExit('Unsupported native build path; nothing built.')
    run = P / 'a_save_ipc_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    units = dict(owner='a_save_user_owner.cpp', driver='checkpoint_fresh_save.cpp',
        binding='checkpoint_live_storage_binding.cpp', gate='checkpoint_serialized_storage_gate.cpp',
        hooks='checkpoint_load_hook_set.cpp', bridge='a_save_user_owner_bridge.cpp',
        storage='native_storage_read_core.cpp', inspector='checkpoint_native_input_pending_adapter.cpp',
        packet='checkpoint_fresh_save_packet.cpp', ipc='a_save_ipc.cpp')
    names = set(units.values()) | {
        'a_save_ipc_test_build.py', 'a_save_ipc_fixture.cpp', 'a_save_ipc.h',
        'a_save_user_owner.h', 'a_save_user_owner_bridge.h', 'a_save_user_owner_bridge.asm',
        'a_save_user_owner_fixture.cpp', 'a_save_user_owner_fixture.asm',
        'checkpoint_fresh_save.h', 'checkpoint_persistent_bridge.h', 'checkpoint_load_worker_bridge.h',
        'checkpoint_push_pilot.h', 'checkpoint_live_storage_binding.h',
        'checkpoint_live_storage_binding_fixture.asm', 'checkpoint_serialized_storage_gate.h',
        'checkpoint_load_hook_set.h', 'native_storage_read_core.h',
        'checkpoint_native_input_pending_adapter.h', 'checkpoint_native_input_core.h',
        'checkpoint_load_dispatch_bridge.h', 'checkpoint_fresh_save_packet.h'}
    sources = {n: sha(P/n) for n in sorted(names)}
    profile_hash = sha(private/'checkpoint_push_profile.h')
    flags = f'/nologo /std:c++17 /EHa /W4 /WX /wd4324 /O2 /MT /I"{private}"'
    commands = [f'cl {flags} /c "{P/source}" /Fo:{name}.obj' for name, source in units.items()]
    commands += [f'ml64 /nologo /c /Fo bridge_asm.obj "{P/"a_save_user_owner_bridge.asm"}"',
        'lib /nologo /OUT:a_save_ipc.lib ' + ' '.join(f'{n}.obj' for n in units) + ' bridge_asm.obj']
    defines = '/DCHECKPOINT_FRESH_SAVE_FIXTURE /DA_SAVE_USER_OWNER_FIXTURE'
    commands += [f'cl {flags} {defines} /c "{P/units[n]}" /Fo:fixture_{n}.obj' for n in ('owner', 'driver')]
    commands += [f'cl {flags} /DCHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE /c "{P/units["binding"]}" /Fo:fixture_binding.obj',
        f'cl {flags} {defines} /c "{P/"a_save_ipc_fixture.cpp"}" /Fo:fixture.obj',
        f'ml64 /nologo /c /Fo fixture_asm.obj "{P/"a_save_user_owner_fixture.asm"}"',
        f'ml64 /nologo /c /Fo context_asm.obj "{P/"checkpoint_live_storage_binding_fixture.asm"}"',
        'link /nologo /OUT:fixture.exe fixture_owner.obj fixture_driver.obj fixture_binding.obj gate.obj hooks.obj bridge.obj bridge_asm.obj storage.obj inspector.obj packet.obj ipc.obj fixture.obj fixture_asm.obj context_asm.obj bcrypt.lib advapi32.lib']
    vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    build = run/'build.cmd'
    build.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+
        '\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
    built = subprocess.run(['cmd', '/c', str(build)], cwd=run, capture_output=True, text=True, errors='replace')
    (run/'build.log').write_text(built.stdout+built.stderr, encoding='utf-8')
    unchanged = all(sha(P/n)==s for n,s in sources.items()) and sha(private/'checkpoint_push_profile.h')==profile_hash
    report = dict(schema='san14.a-save-ipc-build.v1', result='PASS' if built.returncode==0 and unchanged else 'FAIL',
        sources=sources, sources_unchanged=unchanged, private_profile_sha256=profile_hash,
        game_access=False, tests_executed=False, production_sha256=sha(run/'a_save_ipc.lib') if (run/'a_save_ipc.lib').is_file() else None,
        fixture_sha256=sha(run/'fixture.exe') if (run/'fixture.exe').is_file() else None)
    (run/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    if built.returncode:
        print(built.stdout+built.stderr)
    print(json.dumps({'result':report['result'], 'path':str(run/'result.json'), 'fixture_sha256':report['fixture_sha256']}))
    return 0 if report['result']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
