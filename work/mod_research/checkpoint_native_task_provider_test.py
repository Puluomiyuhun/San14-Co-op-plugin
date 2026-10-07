"""Two generations through real cores and shared bridges, in an owned process only."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,shutil,re
P=Path(__file__).resolve().parent
ARCHIVE=P/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
EXPECTED='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
UNITS=['checkpoint_dynamic_runtime_guards','checkpoint_persistent_physical_owner','checkpoint_load_hook_set','checkpoint_native_queue_adapter_core','checkpoint_dynamic_native_queue_bridge','checkpoint_persistent_authorized_controller','checkpoint_bound_input_pending_adapter','checkpoint_native_input_pending_adapter','checkpoint_native_input_core','checkpoint_persistent_input_hwbp','checkpoint_dynamic_file_profile','checkpoint_persistent_bridge','checkpoint_persistent_route_core','checkpoint_persistent_route_worker_adapter','checkpoint_persistent_route_six_adapter','checkpoint_persistent_logical_adapter','checkpoint_dynamic_native_session','native_storage_read_core','checkpoint_dynamic_cc_load_observer','checkpoint_dynamic_cc_load_lifecycle','checkpoint_dynamic_title_identity_adapter','checkpoint_identity_pair_commit','checkpoint_dynamic_load_request_commit','checkpoint_load_input_boundary','checkpoint_persistent_planning_observer','checkpoint_task_attribution_core','checkpoint_task_attribution_adapter','checkpoint_native_task_provider','checkpoint_native_task_provider_fixture']
FLAGS='/nologo /W4 /WX /EHa /std:c++17 /O2 /MT'
DEFS='/DCHECKPOINT_DYNAMIC_RUNTIME_GUARDS_FIXTURE /DCHECKPOINT_PERSISTENT_PHYSICAL_OWNER_FIXTURE /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_PERSISTENT_AUTHORIZED_FIXTURE /DCHECKPOINT_PERSISTENT_PLANNING_FIXTURE /DCHECKPOINT_DYNAMIC_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_DYNAMIC_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_PERSISTENT_NATIVE_SESSION_FIXTURE'
REMAP='/DCheckpointLoadWorkerClaim=CheckpointPersistentObserverClaim /DCheckpointLoadWorkerCurrentOwner=CheckpointPersistentObserverCurrentOwner'
CASES=['success','alternate-factions','planning-reuse-load','reuse-full-addresses','late-old-root','missing-load-join','missing-title520-join','missing-title590-join','idle-window','user-exception']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert sha(ARCHIVE)==EXPECTED
 run=P/'checkpoint_native_task_provider_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 sources=set()
 for name in UNITS:
  for ext in ('cpp','h'):
   if (P/f'{name}.{ext}').exists():sources.add(f'{name}.{ext}')
 sources.update(['checkpoint_native_queue_adapter_profile.h','checkpoint_live_runtime_guards_profile.h','checkpoint_live_prefetch_profile.h','checkpoint_native_task_provider_fixture_admission.inc','checkpoint_native_task_provider_fixture_ports.inc','checkpoint_persistent_authorized_bridge.asm','checkpoint_native_input_hwbp_fixture.asm','checkpoint_native_input_prefetch_archived.inc','checkpoint_persistent_bridge.asm','checkpoint_guest_native_session_fixture.asm','checkpoint_native_task_provider_test.py','checkpoint_native_task_provider_fixture_planning.inc','checkpoint_load_request_commit.h','checkpoint_cc_load_observer.h','checkpoint_cc_load_lifecycle.h','checkpoint_title_identity_adapter.h'])
 todo=list(sources)
 while todo:
  for name in re.findall(r'^\s*#include\s+"([^"]+)"',(P/todo.pop()).read_text(encoding='utf-8-sig'),re.M):
   if name not in sources and (P/name).is_file():sources.add(name);todo.append(name)
 before={f:sha(P/f) for f in sorted(sources)}
 lines=['@echo off','setlocal','call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul','if errorlevel 1 exit /b 1',f'cd /d "{P}"']
 def command(c):lines.extend([c,'if errorlevel 1 exit /b 1'])
 command(f'cl {FLAGS} /c /Fo"{run / "production.obj"}" checkpoint_native_task_provider.cpp')
 command(f'cl {FLAGS} /c /Fo"{run / "production_queue_core.obj"}" checkpoint_native_queue_adapter_core.cpp')
 objs=[]
 for name in UNITS:
  obj=run/f'{name}.obj';objs.append(obj)
  remap=REMAP if name in ('checkpoint_dynamic_cc_load_observer',) else ''
  command(f'cl {FLAGS} {DEFS} {remap} /c /Fo"{obj}" {name}.cpp')
 for name in ['checkpoint_persistent_bridge','checkpoint_guest_native_session_fixture','checkpoint_persistent_authorized_bridge','checkpoint_native_input_hwbp_fixture']:
  obj=run/f'{name}_asm.obj';objs.append(obj)
  command(f'ml64 /nologo /c /Fo "{obj}" {name}.asm')
 binary=run/'fixture.exe'
 command(f'link /nologo /incremental:no /OUT:"{binary}" '+' '.join(f'"{o}"' for o in objs))
 build=run/'build.cmd';build.write_text('\n'.join(lines)+'\n')
 proc=subprocess.run(['cmd','/c',str(build)],cwd=P,capture_output=True)
 (run/'build.stdout.txt').write_bytes(proc.stdout);(run/'build.stderr.txt').write_bytes(proc.stderr)
 if proc.returncode:print(proc.stdout.decode(errors='replace'));raise SystemExit(proc.returncode)
 rows=[]
 for case in CASES:
  folder=run/case;folder.mkdir();archive=folder/'0'/'svdexccSC03.s14';archive.parent.mkdir();shutil.copyfile(ARCHIVE,archive)
  second=folder/'1'/'svdexccSC03.s14';second.parent.mkdir();payload=bytearray(ARCHIVE.read_bytes());payload[77]^=0x5a;payload.extend(bytes(range(128)));second.write_bytes(payload)
  second_sha=sha(second)
  proc=subprocess.run([str(binary),case,str(archive),str(folder)],cwd=P,capture_output=True,timeout=30)
  (folder/'stdout.txt').write_bytes(proc.stdout);(folder/'stderr.txt').write_bytes(proc.stderr)
  json_lines=[x for x in proc.stdout.decode(errors='replace').splitlines() if x.startswith('{')]
  row=json.loads(json_lines[-1]) if json_lines else {'case':case,'passed':False}
  row['provider_observations']=[json.loads(x) for x in json_lines if 'provider_generation' in x]
  row['planning_observations']=[json.loads(x) for x in json_lines if 'planning_case' in x]
  row['guard_observations']=[json.loads(x) for x in json_lines if 'guard_generation' in x]
  row['admission_observations']=[json.loads(x) for x in json_lines if 'admission_generation' in x]
  row['exit_code']=proc.returncode;row['archive_unchanged']=sha(archive)==EXPECTED and sha(second)==second_sha
  row['passed']=bool(row['passed'] and proc.returncode==0 and row['archive_unchanged'])
  rows.append(row)
 result={'schema':'san14.native-task-provider-integration.v1','result':'PASS' if all(x['passed'] for x in rows) else 'FAIL','cases':rows,'source_sha256':before,'sources_unchanged':before=={f:sha(P/f) for f in before},'game_access':False,'source_ports_installed_in_game':False,'production_admission':False,'native_scheduler_fence':False,'repeated_real_game_load_proven':False,'world_verified':False,
 'fixture_binary_sha256':sha(binary),'production_provider_object_sha256':sha(run/'production.obj'),'production_queue_object_sha256':sha(run/'production_queue_core.obj'),
 'scope':'Two retained task-attribution banks drive the actual frozen six-entry physical owner, logical adapter, dynamic Session/runtime guards, hardware input prefetch, private admission ticket, native queue Adapter, request CAS, full archive byte observer, Load lifecycle, identity pair CAS and planning observer. Native instruction source ports and all game load/queue/file/Title bodies remain explicit owned-memory doubles. Embedded workers use three real owned OS threads and native-layout descriptors; Title520 creator differs from join caller. One case reuses the exact image base, Load and Title allocations across both generations. A delayed old state creation enters after new proxy publication and cannot mutate the new Session; unowned physical/native entries do not select the latest Session. Missing each of the three joins blocks completion. Native User SEH propagates and hardware state restores. Historical Load/Title pages are NOACCESS on later paths. Closed windows ignore 1000 idle fresh-selection events without consuming tickets. Banks and tickets are never recycled; fixed capacity is two banks of 256 tasks, not indefinite repeated loading. Host-module/Steam authentication, actual native source interception, process-global quiescence, production publication and full-world/input/pixel readiness are not proved.'}
 if not result['sources_unchanged']:result['result']='FAIL'
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'result':result['result'],'cases':len(rows),'failed':[r['case'] for r in rows if not r['passed']],'path':str(run/'result.json')}))
 raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
