"""Build the actual early Gate successor composed with the report-aware Owner."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys

P = Path(__file__).resolve().parent
CASES_UNUSED = ('two-saves','pending-flag','pending-queue','entry-flag','entry-queue','late-flag','late-queue','consumed','local-aba-blocked','external-aba','early-bypass','storage-append','during-save','copy-flag','copy-cursor','competing-initialize','submit-unreadable','release-report','release-quiet','tail-av','unwind','source-conflict','suffix-drift','no-install','partial-install','updater-write','release-updater','upstream-exception','prefix-drift')


CASES=('interlock-slot-drift','interlock-after-drift','interlock-date','interlock-missing-game','interlock-missing-user','interlock-thread','interlock-gate-drift','interlock-identity-owner','interlock-full-refusal','interlock-release','fence-queued','fence-save','fence-active','fence-uncertain','fence-world','fence-original')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(errors="backslashreplace")
    private_text = os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT', '')
    if not private_text or any(c in private_text for c in ('"', '\n', '%', '&', '|', '<', '>')):
        raise SystemExit('Set SAN14_PRIVATE_FIXTURE_ROOT; no tests ran.')
    private = Path(private_text).resolve()
    profile = private / 'checkpoint_push_profile.h'
    if not profile.is_file():
        raise SystemExit('Missing private checkpoint_push_profile.h; no tests ran.')
    private_hash = sha(profile)
    run = P / 'planning_input_interlock_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    # Relocate only fixture SaveState storage away from the real 2403C2 code
    # page required by the early report guard. Business remains explicit doubles.
    base_fixture=(P/'a_save_user_owner_fixture.cpp').read_text(encoding='utf-8').replace('0x240000','0x340000')
    (run/'a_save_upstream_base_fixture.inc').write_text(base_fixture,encoding='utf-8')
    action_fixture=(P/'a_save_action_gate_fixture.cpp').read_text(encoding='utf-8').replace('"a_save_user_owner_fixture.cpp"','"a_save_upstream_base_fixture.inc"').replace('int main(int argc,char**argv)', 'int ReportFrozenActionMain(int argc,char**argv)').replace('a_save_action_gate.h','planning_input_interlock_gate.h').replace('namespace ag=a_save_action_gate','namespace ag=a_save_upstream_gate').replace('t[1]={0x3F9DA8,0x3FA0A4,0x2200000};check(RtlAddFunctionTable(t,2,b)', 'check(RtlAddFunctionTable(t,1,b)').replace('void ASaveActionTailRestoreBegin();', 'void ASaveUpstreamForwardRestore();void ASaveUpstreamForwardFlagsPush();void ASaveUpstreamForwardFlagsPop();void ASaveUpstreamForwardEpilogue();void ASaveUpstreamForwardPopRbp();void ASaveUpstreamForwardJump();void ASaveActionTailRestoreBegin();').replace('verify(uintptr_t(&ASaveActionTailOriginalLoad),bottom,bottom+0x80);', 'verify(uintptr_t(&ASaveActionTailOriginalLoad),bottom,bottom+0x80);for(auto pc=uintptr_t(&ASaveUpstreamForwardRestore);pc<uintptr_t(&ASaveUpstreamForwardFlagsPop);++pc)verify(pc,bottom,bottom+0x80);verify(uintptr_t(&ASaveUpstreamForwardFlagsPop),bottom-8,bottom+0x80);verify(uintptr_t(&ASaveUpstreamForwardEpilogue),bottom,bottom+0x80);verify(uintptr_t(&ASaveUpstreamForwardPopRbp),bottom+0xF0,bottom+0x80);verify(uintptr_t(&ASaveUpstreamForwardJump),bottom+0xF8,oldRbp);')
    (run/'a_save_upstream_action_fixture.inc').write_text(action_fixture,encoding='utf-8')
    units = dict(input='planning_input_interlock_gate.cpp', interlock='planning_input_interlock.cpp', input_bridge='a_save_action_gate_bridge.cpp',
        owner='a_reward_save_owner.cpp', bridge='a_reward_save_owner_bridge.cpp', early='a_save_early_guard.cpp',
        driver='checkpoint_fresh_save.cpp', binding='checkpoint_live_storage_binding.cpp',
        gate='checkpoint_serialized_storage_gate.cpp', hooks='checkpoint_load_hook_set.cpp',
        storage='native_storage_read_core.cpp', inspector='checkpoint_native_input_pending_adapter.cpp',
        packet='checkpoint_fresh_save_packet.cpp')
    asm = dict(input_asm='a_save_upstream_bridge.asm', bridge_asm='a_save_user_owner_bridge.asm',
        fixture_asm='a_save_user_owner_fixture.asm', input_fixture_asm='a_save_upstream_fixture.asm',
        context_asm='checkpoint_live_storage_binding_fixture.asm')
    todo = [*units.values(), *asm.values(), 'checkpoint_reward_owned_replay.cpp', 'planning_input_interlock_test.py', 'planning_input_interlock_fixture.cpp', 'a_save_upstream_fixture.cpp', 'a_save_action_gate_fixture.cpp','a_save_user_owner_fixture.cpp']
    sources = {}
    while todo:
        name = todo.pop()
        if name in sources or name in ('checkpoint_push_profile.h','a_save_upstream_action_fixture.inc','a_save_upstream_base_fixture.inc','a_reward_save_owner_base.inc'):
            continue
        path = P / name
        if not path.is_file():
            raise SystemExit('Missing source dependency: ' + name)
        sources[name] = sha(path)
        todo.extend(re.findall(r'^\s*#include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.M))
    (run/'a_reward_save_owner_base.inc').write_text((P/'a_save_upstream_fixture.cpp').read_text(encoding='utf-8').replace('a_save_upstream_gate.h','planning_input_interlock_gate.h').replace('int main(int argc,char**argv)','int RewardFrozenMain(int argc,char**argv)'),encoding='utf-8')
    vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags = f'/nologo /std:c++17 /EHa /W4 /WX /wd4324 /O2 /MT /I"{private}" /I"{run}" /I"{P}"'
    commands = [f'cl {flags} /c "{P / source}" /Fo:{name}.obj' for name, source in units.items()]
    commands += [f'ml64 /nologo /c /Fo {name}.obj "{P / source}"' for name, source in asm.items()]
    commands += [f'cl {flags} /DCHECKPOINT_REWARD_OWNED_FIXTURE /LD "{P/"checkpoint_reward_owned_replay.cpp"}" /Fo:reward.obj /Fe:reward.dll /link "{private/"checkpoint_planning_hold.lib"}" /IMPLIB:reward.lib']
    import shutil
    shutil.copy2(private/'checkpoint_planning_hold.dll',run/'checkpoint_planning_hold.dll')
    shutil.copy2(private/'checkpoint_planning_hold.lib',run/'planning.lib')
    commands += [f'cl {flags} /c "{P/"checkpoint_reward_owned_replay.cpp"}" /Fo:production_reward.obj']
    commands += ['lib /nologo /OUT:a_save_upstream.lib input.obj interlock.obj input_bridge.obj input_asm.obj owner.obj early.obj bridge.obj bridge_asm.obj driver.obj binding.obj gate.obj hooks.obj inspector.obj storage.obj']
    defines = '/DA_REWARD_SAVE_OWNER_FIXTURE /DA_SAVE_ACTION_FIXTURE /DA_SAVE_USER_OWNER_FIXTURE /DCHECKPOINT_FRESH_SAVE_FIXTURE /DA_SAVE_EARLY_FIXTURE'
    commands += [f'cl {flags} {defines} /c "{P / units[n]}" /Fo:fixture_{n}.obj' for n in ('input', 'owner', 'driver','early')]
    commands += [f'cl {flags} /DCHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE /c "{P / units["binding"]}" /Fo:fixture_binding.obj',
        f'cl {flags} {defines} /c "{P / "planning_input_interlock_fixture.cpp"}" /Fo:fixture.obj',
        'link /nologo /OUT:fixture.exe fixture_input.obj interlock.obj fixture_owner.obj fixture_driver.obj fixture_early.obj fixture_binding.obj input_bridge.obj bridge.obj gate.obj hooks.obj storage.obj inspector.obj packet.obj fixture.obj ' + ' '.join(n+'.obj' for n in asm) + ' bcrypt.lib reward.lib planning.lib']
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
    for viewer in ('worker','worker-b'):
        directory=run/viewer;directory.mkdir()
        messages=[{'op':'sample'},{'op':'reward','force_id':2,'district_id':2,'officer_ids':[101,264]},
            {'op':'ready_fence','value':True,'revision':1},{'op':'ready_fence','value':True,'revision':1},
            {'op':'fence_sample','revision':1},{'op':'fence_sample','revision':1},
            {'op':'ready_fence','value':False,'revision':1},{'op':'ready_fence','value':True,'revision':0},
            {'op':'reward','force_id':12,'district_id':11,'officer_ids':[97]},
            {'op':'ready_fence','value':False,'revision':2},{'op':'fence_sample','revision':1},
            {'op':'reward','force_id':12,'district_id':11,'officer_ids':[97]},{'op':'sample'},{'op':'close'}]
        child=subprocess.run([str(run/'fixture.exe'),viewer,str(directory),binary_sha],input=''.join(json.dumps(m)+'\n' for m in messages),capture_output=True,text=True,timeout=30,cwd=run)
        (directory/'stdout.jsonl').write_text(child.stdout);(directory/'stderr.txt').write_text(child.stderr)
        try:
            replies=[json.loads(line) for line in child.stdout.splitlines()]
            first,r1,set1,dup,obs1,obs2,conflict,stale,blocked,release,oldobs,r2,after,closed=replies
            expected_viewer=12 if viewer=='worker' else 2
            ok=child.returncode==0 and first['sample']['viewer_force_id']==expected_viewer
            ok=ok and all(replies[i]['ok'] for i in (0,1,2,3,4,5,9,11,12,13)) and all(not replies[i]['ok'] for i in (6,7,8,10))
            ok=ok and not set1['observed'] and not dup['observed'] and dup['duplicate'] and set1['revision']==dup['revision']==1
            ok=ok and all(o['observed'] and o['observed_revision']==1 and o['user_native_started_delta']==o['user_native_returned_delta']==o['active']==0 and o['user_finally_delta']==o['held_delta']==1 and not o['queued'] and not o['uncertain'] for o in (obs1,obs2))
            ok=ok and all(o['input_coverage_mask']==7 and o['input_missing_mask']==31 and o['game_finally_delta']==o['global_ui_suppressed_delta']==o['panel_suppressed_delta']==1 and not o['all_input_held'] for o in (obs1,obs2))
            ok=ok and obs2['user_finally']==obs1['user_finally']+1 and obs2['revision']==1
            ok=ok and not release['observed'] and not release['value'] and release['revision']==2
            ok=ok and r2['native_calls']==2 and after['sample']['forces'][0]['gold']==83208 and after['sample']['forces'][1]['gold']==20604
        except (ValueError,KeyError,TypeError):ok=False;replies=[]
        rows.append(dict(case=viewer,result='PASS' if ok else 'FAIL',exit=child.returncode,replies=replies));print(viewer,'PASS' if ok else 'FAIL',child.stderr,flush=True)
    unchanged = sha(profile) == private_hash and all(sha(P/n) == h for n,h in sources.items())
    result = dict(schema='san14.planning-input-interlock-owned.v1',result='PASS' if unchanged and all(r['result']=='PASS' and r['exit']==0 for r in rows) else 'FAIL',cases=rows,sources=sources,sources_unchanged=unchanged,fixture_sha256=binary_sha,production_sha256=sha(run/'a_save_upstream.lib'),planning_dll_sha256=sha(run/'checkpoint_planning_hold.dll'),reward_dll_sha256=sha(run/'reward.dll'),game_access=False,steam_access=False,room_ready=False,full_world=False,production_permit=False,same_user_slot=True,original_reward_business_fixture=True,input_coverage_mask=7,input_missing_mask=31,all_input_held=False,native_gameplay_enabled=False,save_authorized=False,same_owner_gate_identity_checked=True,actual_game_ui_panel_and_user_observation=True)
    path = run/'result.json'
    path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'result':result['result'], 'path':str(path)}))
    raise SystemExit(result['result']!='PASS')


if __name__ == '__main__':
    main()
