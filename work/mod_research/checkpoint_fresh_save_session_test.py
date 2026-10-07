"""Compile the production composition and run only child-process fixtures.

Requires SAN14_PRIVATE_FIXTURE_ROOT containing the private generated
checkpoint_push_profile.h. It is read via /I, never copied into this repo.
No game process, game directory or Steam API is opened by this test.
"""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import subprocess

P = Path(__file__).resolve().parent
CASES = (
    'success', 'suppress-original-refused', 'suppressed-no-return', 'entry-replaced-before-arm',
    'stop-before-arm', 'stop-before-binder', 'stop-in-binder', 'stop-in-read',
    'original-exception', 'save-exception', 'storage-generation-drift',
    'native-bytes-mismatch', 'phase-skip',
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    private = os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT', '')
    profile = Path(private) / 'checkpoint_push_profile.h'
    if not private or not profile.is_file():
        raise SystemExit('Missing private input: set SAN14_PRIVATE_FIXTURE_ROOT; no tests ran.')
    private = str(Path(private).resolve())
    if '"' in private or '\n' in private or '%' in private:
        raise SystemExit('Unsupported private input path')
    private_sha = sha(profile)
    run = P / 'checkpoint_fresh_save_session_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    names = [p.name for p in P.glob('checkpoint_fresh_save_session*') if p.is_file() and p.suffix in ('.h', '.cpp', '.asm', '.py')]
    dependencies = ('checkpoint_fresh_save.h', 'checkpoint_fresh_save.cpp',
                    'checkpoint_persistent_bridge.h', 'checkpoint_load_worker_bridge.h',
                    'checkpoint_push_pilot.h', 'checkpoint_live_storage_binding.h',
                    'checkpoint_live_storage_binding.cpp', 'checkpoint_live_storage_binding_fixture.asm',
                    'checkpoint_serialized_storage_gate.h', 'checkpoint_serialized_storage_gate.cpp',
                    'checkpoint_load_hook_set.h', 'checkpoint_load_hook_set.cpp',
                    'native_storage_read_core.h', 'native_storage_read_core.cpp')
    sources = {n: sha(P / n) for n in (*names, *dependencies)}
    vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags = f'/nologo /std:c++17 /EHa /W4 /WX /wd4324 /O2 /MT /I"{private}"'
    units = {
        'owner': 'checkpoint_fresh_save_session.cpp',
        'driver': 'checkpoint_fresh_save.cpp',
        'binding': 'checkpoint_live_storage_binding.cpp',
        'gate': 'checkpoint_serialized_storage_gate.cpp',
        'hooks': 'checkpoint_load_hook_set.cpp',
        'bridge': 'checkpoint_fresh_save_session_bridge.cpp',
        'storage': 'native_storage_read_core.cpp',
    }
    commands = [f'cl {flags} /c "{P / source}" /Fo:{name}.obj' for name, source in units.items()]
    commands += [f'ml64 /nologo /c /Fo bridge_asm.obj "{P / "checkpoint_fresh_save_session_bridge.asm"}"',
                 'lib /nologo /OUT:checkpoint_fresh_save_session.lib ' + ' '.join(f'{n}.obj' for n in units) + ' bridge_asm.obj']
    fixture_defines = '/DCHECKPOINT_FRESH_SAVE_FIXTURE /DCHECKPOINT_FRESH_SAVE_SESSION_FIXTURE'
    commands += [f'cl {flags} {fixture_defines} /c "{P / units[n]}" /Fo:fixture_{n}.obj' for n in ('owner', 'driver')]
    commands += [f'cl {flags} /DCHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE /c "{P / units["binding"]}" /Fo:fixture_binding.obj',
                 f'cl {flags} {fixture_defines} /c "{P / "checkpoint_fresh_save_session_fixture.cpp"}" /Fo:fixture.obj',
                 f'ml64 /nologo /c /Fo fixture_asm.obj "{P / "checkpoint_fresh_save_session_fixture.asm"}"',
                 f'ml64 /nologo /c /Fo context_asm.obj "{P / "checkpoint_live_storage_binding_fixture.asm"}"',
                 'link /nologo /OUT:fixture.exe fixture_owner.obj fixture_driver.obj fixture_binding.obj gate.obj hooks.obj bridge.obj bridge_asm.obj storage.obj fixture.obj fixture_asm.obj context_asm.obj bcrypt.lib']
    build = run / 'build.cmd'
    build.write_text('@echo off\ncall "' + vc + '" >nul\nif errorlevel 1 exit /b 1\n' + '\n'.join(c + '\nif errorlevel 1 exit /b 1' for c in commands) + '\n')
    process = subprocess.run(['cmd', '/c', str(build)], cwd=run, capture_output=True, text=True, errors='replace')
    (run / 'build.log').write_text(process.stdout + process.stderr, encoding='utf-8')
    if process.returncode:
        print(process.stdout + process.stderr)
        raise SystemExit(process.returncode)
    binary_sha = sha(run / 'fixture.exe')
    rows = []
    for case in CASES:
        directory = run / case
        directory.mkdir()
        proc = subprocess.run([str(run / 'fixture.exe'), case, str(directory), binary_sha], cwd=run, capture_output=True, text=True, timeout=30)
        try:
            row = json.loads(proc.stdout)
        except ValueError:
            row = {'case': case, 'result': 'FAIL', 'stdout': proc.stdout}
        row.update(exit=proc.returncode, stderr=proc.stderr)
        rows.append(row)
        print(case, row['result'], proc.stderr)
    unchanged = sha(profile) == private_sha and all(sha(P / n) == digest for n, digest in sources.items())
    result = {
        'schema': 'san14.fresh-save-session-owned.v1',
        'result': 'PASS' if unchanged and all(r['result'] == 'PASS' and r['exit'] == 0 for r in rows) else 'FAIL',
        'cases': rows, 'sources': sources, 'sources_unchanged': unchanged,
        'private_inputs': {'checkpoint_push_profile.h': private_sha},
        'production_sha256': sha(run / 'checkpoint_fresh_save_session.lib'),
        'fixture_sha256': binary_sha,
        'scope': 'Actual Owner factory, raw two-slot PE assembly bridge, HookSet publication, frozen Gate/Context/module hashes/TLS/SEH, and Win32 create-new intents and retained files. Native game business bodies and Steam file methods are explicit child-process doubles. ContextInit initialized leaf executes actual archived byte shape.',
        'game_access': False, 'steam_access': False, 'room_ready': False,
        'all_input_held': False, 'full_world': False,
    }
    path = run / 'result.json'
    path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': result['result'], 'path': str(path)}))
    raise SystemExit(result['result'] != 'PASS')


if __name__ == '__main__':
    main()
