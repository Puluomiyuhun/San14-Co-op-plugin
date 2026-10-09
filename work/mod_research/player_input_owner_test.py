"""Own hidden HWND + archived WndProc + actual reward Owner; never a game launcher."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys

P = Path(__file__).resolve().parent


CASES=('policy-normal','policy-pending','policy-binding','policy-thread','policy-source','policy-callback-source','policy-publish-race','policy-terminal','policy-drain')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(errors="backslashreplace")
    private_text = os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT', '')
    if not private_text or any(c in private_text for c in ('"', '\n', '%', '&', '|', '<', '>')):
        raise SystemExit('Set SAN14_PRIVATE_FIXTURE_ROOT; no tests ran.')
    private = Path(private_text).resolve()
    profile = private / 'checkpoint_push_profile.h'
    archive=private/'game-runtime-image.bin'
    archive_sha=sha(archive)
    if archive_sha!='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268':raise SystemExit('Archive hash mismatch')
    if not profile.is_file():
        raise SystemExit('Missing private checkpoint_push_profile.h; no tests ran.')
    private_hash = sha(profile)
    private_inputs = {str(path.resolve()):sha(path) for path in
                      (profile,archive,private/'checkpoint_planning_hold.lib',private/'checkpoint_planning_hold.dll')}
    run = P / 'player_input_owner_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    wnd=archive.read_bytes()[0x5122F0:0x512368]
    (run/'player_input_owner_profile.h').write_text('#pragma once\nstatic const unsigned char BoundaryWndBytes[]={'+','.join(hex(x) for x in wnd)+'};\n')
    # Relocate only fixture SaveState storage away from the real 2403C2 code
    # page required by the early report guard. Business remains explicit doubles.
    base_fixture=(P/'a_save_user_owner_fixture.cpp').read_text(encoding='utf-8').replace('0x240000','0x340000')
    (run/'a_save_upstream_base_fixture.inc').write_text(base_fixture,encoding='utf-8')
    action_fixture=(P/'a_save_action_gate_fixture.cpp').read_text(encoding='utf-8').replace('"a_save_user_owner_fixture.cpp"','"a_save_upstream_base_fixture.inc"').replace('int main(int argc,char**argv)', 'int ReportFrozenActionMain(int argc,char**argv)').replace('a_save_action_gate.h','planning_input_interlock_gate.h').replace('namespace ag=a_save_action_gate','namespace ag=a_save_upstream_gate').replace('t[1]={0x3F9DA8,0x3FA0A4,0x2200000};check(RtlAddFunctionTable(t,2,b)', 'check(RtlAddFunctionTable(t,1,b)').replace('void ASaveActionTailRestoreBegin();', 'void ASaveUpstreamForwardRestore();void ASaveUpstreamForwardFlagsPush();void ASaveUpstreamForwardFlagsPop();void ASaveUpstreamForwardEpilogue();void ASaveUpstreamForwardPopRbp();void ASaveUpstreamForwardJump();void ASaveActionTailRestoreBegin();').replace('verify(uintptr_t(&ASaveActionTailOriginalLoad),bottom,bottom+0x80);', 'verify(uintptr_t(&ASaveActionTailOriginalLoad),bottom,bottom+0x80);for(auto pc=uintptr_t(&ASaveUpstreamForwardRestore);pc<uintptr_t(&ASaveUpstreamForwardFlagsPop);++pc)verify(pc,bottom,bottom+0x80);verify(uintptr_t(&ASaveUpstreamForwardFlagsPop),bottom-8,bottom+0x80);verify(uintptr_t(&ASaveUpstreamForwardEpilogue),bottom,bottom+0x80);verify(uintptr_t(&ASaveUpstreamForwardPopRbp),bottom+0xF0,bottom+0x80);verify(uintptr_t(&ASaveUpstreamForwardJump),bottom+0xF8,oldRbp);')
    (run/'a_save_upstream_action_fixture.inc').write_text(action_fixture,encoding='utf-8')
    units = dict(policy='player_input_policy.cpp', boundary='player_input_owner.cpp', classifier='checkpoint_native_input_core.cpp', input='planning_input_interlock_gate.cpp', interlock='planning_input_interlock.cpp', input_bridge='a_save_action_gate_bridge.cpp',
        owner='a_reward_save_owner.cpp', bridge='a_reward_save_owner_bridge.cpp', early='a_save_early_guard.cpp',
        driver='checkpoint_fresh_save.cpp', binding='checkpoint_live_storage_binding.cpp',
        gate='checkpoint_serialized_storage_gate.cpp', hooks='checkpoint_load_hook_set.cpp',
        storage='native_storage_read_core.cpp', inspector='checkpoint_native_input_pending_adapter.cpp',
        packet='checkpoint_fresh_save_packet.cpp')
    asm = dict(input_asm='a_save_upstream_bridge.asm', bridge_asm='a_save_user_owner_bridge.asm',
        fixture_asm='a_save_user_owner_fixture.asm', input_fixture_asm='a_save_upstream_fixture.asm',
        context_asm='checkpoint_live_storage_binding_fixture.asm')
    todo = [*units.values(), *asm.values(), 'checkpoint_reward_owned_replay.cpp', 'player_input_owner_test.py', 'player_input_owner_fixture.cpp', 'planning_input_interlock_fixture.cpp', 'a_save_upstream_fixture.cpp', 'a_save_action_gate_fixture.cpp','a_save_user_owner_fixture.cpp']
    sources = {}
    while todo:
        name = todo.pop()
        if name in sources or name in ('checkpoint_push_profile.h','a_save_upstream_action_fixture.inc','a_save_upstream_base_fixture.inc','a_reward_save_owner_base.inc','player_input_owner_profile.h','player_input_owned_base.inc'):
            continue
        path = P / name
        if not path.is_file():
            raise SystemExit('Missing source dependency: ' + name)
        sources[name] = sha(path)
        todo.extend(re.findall(r'^\s*#include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.M))
    (run/'a_reward_save_owner_base.inc').write_text((P/'a_save_upstream_fixture.cpp').read_text(encoding='utf-8').replace('a_save_upstream_gate.h','planning_input_interlock_gate.h').replace('int main(int argc,char**argv)','int RewardFrozenMain(int argc,char**argv)'),encoding='utf-8')
    (run/'player_input_owned_base.inc').write_text((P/'planning_input_interlock_fixture.cpp').read_text(encoding='utf-8').replace('int main(int argc,char**argv)','int FrozenInterlockMain(int argc,char**argv)'),encoding='utf-8')
    vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags = f'/nologo /std:c++17 /EHa /W4 /WX /wd4324 /O2 /MT /I"{private}" /I"{run}" /I"{P}"'
    commands = [f'cl {flags} /c "{P / source}" /Fo:{name}.obj' for name, source in units.items()]
    commands += [f'ml64 /nologo /c /Fo {name}.obj "{P / source}"' for name, source in asm.items()]
    commands += [f'cl {flags} /DCHECKPOINT_REWARD_OWNED_FIXTURE /LD "{P/"checkpoint_reward_owned_replay.cpp"}" /Fo:reward.obj /Fe:reward.dll /link "{private/"checkpoint_planning_hold.lib"}" /IMPLIB:reward.lib']
    import shutil
    shutil.copy2(private/'checkpoint_planning_hold.dll',run/'checkpoint_planning_hold.dll')
    shutil.copy2(private/'checkpoint_planning_hold.lib',run/'planning.lib')
    commands += [f'cl {flags} /c "{P/"checkpoint_reward_owned_replay.cpp"}" /Fo:production_reward.obj']
    commands += ['lib /nologo /OUT:player_input_owner.lib input.obj interlock.obj input_bridge.obj input_asm.obj owner.obj early.obj bridge.obj bridge_asm.obj driver.obj binding.obj gate.obj hooks.obj inspector.obj storage.obj boundary.obj classifier.obj policy.obj']
    defines = '/DA_REWARD_SAVE_OWNER_FIXTURE /DA_SAVE_ACTION_FIXTURE /DA_SAVE_USER_OWNER_FIXTURE /DCHECKPOINT_FRESH_SAVE_FIXTURE /DA_SAVE_EARLY_FIXTURE'
    commands += [f'cl {flags} {defines} /c "{P / units[n]}" /Fo:fixture_{n}.obj' for n in ('input', 'owner', 'driver','early')]
    commands += [f'cl {flags} /DPLAYER_INPUT_OWNER_FIXTURE /c "{P / units["boundary"]}" /Fo:fixture_boundary.obj']
    commands += [f'cl {flags} /DCHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE /c "{P / units["binding"]}" /Fo:fixture_binding.obj',
        f'cl {flags} {defines} /c "{P / "player_input_owner_fixture.cpp"}" /Fo:fixture.obj',
        'link /nologo /OUT:fixture.exe fixture_input.obj interlock.obj policy.obj fixture_boundary.obj classifier.obj fixture_owner.obj fixture_driver.obj fixture_early.obj fixture_binding.obj input_bridge.obj bridge.obj gate.obj hooks.obj storage.obj inspector.obj packet.obj fixture.obj ' + ' '.join(n+'.obj' for n in asm) + ' bcrypt.lib user32.lib reward.lib planning.lib']
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
    unchanged = sha(profile) == private_hash and sha(archive)==archive_sha and all(sha(P/n) == h for n,h in sources.items()) and all(sha(Path(n))==h for n,h in private_inputs.items())
    result=dict(schema='san14.player-input-policy-owned.v1',result='PASS' if unchanged and all(r['result']=='PASS' and r['exit']==0 for r in rows) else 'FAIL',cases=rows,sources=sources,sources_unchanged=unchanged,archive_sha256=archive_sha,fixture_sha256=binary_sha,production_sha256=sha(run/'player_input_owner.lib'),planning_dll_sha256=sha(run/'checkpoint_planning_hold.dll'),reward_dll_sha256=sha(run/'reward.dll'),game_access=False,steam_access=False,actual_owned_window_thread=True,actual_archived_wndproc=True,original_message_business_is_fixture=True,actual_reward_owner_submit=True,reward_business_is_fixture=True,production_window_bootstrap_verified=False,full_input_hold=False,game_report_whitelist_verified=False,save_authorized=False,room_ready=False,native_gameplay_enabled=False,missing=['game_input_bootstrap_and_single_publisher','report_confirmation_vs_decision_source','unclassified_window_messages','device_root_other_consumers','cross_period_or_world_rebind','network_phase_driver'])
    path = run/'result.json'
    result['private_inputs'] = private_inputs
    result['artifacts'] = {str(f.resolve()):sha(f) for f in run.rglob('*') if f.is_file()}
    path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'result':result['result'], 'path':str(path)}))
    raise SystemExit(result['result']!='PASS')


if __name__ == '__main__':
    main()
