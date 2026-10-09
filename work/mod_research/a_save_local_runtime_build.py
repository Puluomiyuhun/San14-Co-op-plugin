"""Compile/link controlled Runtime production path; never load/run the DLL."""
from pathlib import Path
from datetime import datetime
import os,sys,json,hashlib,subprocess,difflib
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 run=PRIVATE/'a_save_local_runtime_build_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 old=(P/'a_save_held_ipc_build.py').read_text(encoding='utf-8');s=old.replace('P = Path(__file__).resolve().parent','P = Path('+repr(str(P))+')')
 s=s.replace("run = P / 'a_save_held_ipc_build_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')",'run = Path('+repr(str(run/'build'))+')')
 s=s.replace("input='planning_checkpoint_save_gate.cpp'","input='a_save_scoped_gate.cpp'").replace("inspector='checkpoint_native_input_pending_adapter.cpp'","inspector='a_save_scoped_input.cpp'")
 s=s.replace("ipc='a_save_held_ipc.cpp', held=", "ipc='a_save_dispatch_ipc.cpp', runtime='a_save_local_runtime.cpp', sampler='a_save_local_binding.cpp', parent='a_save_parent_adapter.cpp', parent_bridge='b_reload_parent_bridge.cpp', scope='a_save_native_input_scope.cpp', host='a_save_dispatch_host.cpp', mailbox='a_save_dispatch_mailbox.cpp', held=")
 start=s.index('    asm = dict(');end=s.index('    todo = ',start)
 s=s[:start]+"    asm = dict(input_asm='a_save_upstream_bridge.asm',bridge_asm='a_save_user_owner_bridge.asm',parent_asm='b_reload_parent_bridge.asm')\n"+s[end:]
 s=s.replace("'a_save_held_ipc_flow_test.py'","'a_save_local_runtime_build.py'")
 s=s.replace('packet.obj ipc.obj held.obj','packet.obj ipc.obj runtime.obj sampler.obj parent.obj parent_bridge.obj parent_asm.obj scope.obj host.obj mailbox.obj held.obj')
 start=s.index('    defines = ');end=s.index('    build = run',start)
 s=s[:start]+"    commands += ['link /nologo /DLL /OUT:a_save_local_runtime.dll /WHOLEARCHIVE:a_save_held_ipc.lib production_reward.obj planning.lib bcrypt.lib advapi32.lib']\n"+s[end:]
 s=s.replace("    commands += [f'cl {flags} /DCHECKPOINT_REWARD_OWNED_FIXTURE /LD", "    unused_fixture_command = [f'cl {flags} /DCHECKPOINT_REWARD_OWNED_FIXTURE /LD")
 script=run/'generated_build.py';script.write_text(s,encoding='utf-8');(run/'builder.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True))),encoding='utf-8')
 env=os.environ.copy();env['SAN14_PRIVATE_FIXTURE_ROOT']=str(PRIVATE);private={n:sha(PRIVATE/n) for n in ('checkpoint_push_profile.h','checkpoint_planning_hold.dll','checkpoint_planning_hold.lib')};result=dict(result='FAIL',game_access=False,executed=False)
 try:
  r=subprocess.run([sys.executable,str(script)],env=env,capture_output=True,text=True,errors='replace',timeout=180);(run/'build-driver.log').write_text(r.stdout+r.stderr,encoding='utf-8')
  build=json.loads((run/'build'/'result.json').read_text());result['sources']=build['sources'];assert r.returncode==0 and build['result']=='PASS','production build failed'
  assert (run/'build'/'a_save_local_runtime.dll').is_file();assert all(sha(P/n)==h for n,h in build['sources'].items());assert all(sha(PRIVATE/n)==h for n,h in private.items())
  result['result']='PASS'
 except Exception as e:
  result['error']=repr(e);(run/'failure.log').write_text(repr(e)+'\n'+str(getattr(e,'stdout',''))+'\n'+str(getattr(e,'stderr','')),encoding='utf-8')
 result.update(private_inputs=private,build_generator_sha256=sha(script),binaries={p.name:sha(p) for p in (run/'build').glob('*') if p.suffix in ('.obj','.dll','.lib')},generated={p.name:sha(p) for p in (run/'build').glob('*') if p.suffix in ('.inc','.cmd')})
 out=run/'result.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=result['result'],path=str(out))));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
