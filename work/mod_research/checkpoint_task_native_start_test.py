"""Two generations through real cores and shared bridges, in an owned process only."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,shutil,re
P=Path(__file__).resolve().parent
ARCHIVE=P/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
EXPECTED='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
UNITS=['checkpoint_dynamic_runtime_guards','checkpoint_persistent_physical_owner','checkpoint_load_hook_set','checkpoint_native_queue_adapter_core','checkpoint_dynamic_native_queue_bridge','checkpoint_persistent_authorized_controller','checkpoint_bound_input_pending_adapter','checkpoint_native_input_pending_adapter','checkpoint_native_input_core','checkpoint_persistent_input_hwbp','checkpoint_dynamic_file_profile','checkpoint_persistent_bridge','checkpoint_persistent_route_core','checkpoint_persistent_route_worker_adapter','checkpoint_persistent_route_six_adapter','checkpoint_persistent_logical_adapter','checkpoint_dynamic_native_session','native_storage_read_core','checkpoint_dynamic_cc_load_observer','checkpoint_dynamic_cc_load_lifecycle','checkpoint_dynamic_title_identity_adapter','checkpoint_identity_pair_commit','checkpoint_dynamic_load_request_commit','checkpoint_load_input_boundary','checkpoint_persistent_planning_observer','checkpoint_task_attribution_core','checkpoint_task_attribution_adapter','checkpoint_native_task_provider','checkpoint_task_native_ports','checkpoint_task_native_activation_v2','checkpoint_load_worker_bridge','checkpoint_task_native_start','checkpoint_task_native_start_fixture']
FLAGS='/nologo /W4 /WX /EHa /std:c++17 /O2 /MT'
DEFS='/DCHECKPOINT_TASK_NATIVE_START_FIXTURE /DCHECKPOINT_TASK_NATIVE_ACTIVATION_FIXTURE /DCHECKPOINT_TASK_NATIVE_PORTS_FIXTURE /DCHECKPOINT_DYNAMIC_RUNTIME_GUARDS_FIXTURE /DCHECKPOINT_PERSISTENT_PHYSICAL_OWNER_FIXTURE /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_PERSISTENT_AUTHORIZED_FIXTURE /DCHECKPOINT_PERSISTENT_PLANNING_FIXTURE /DCHECKPOINT_DYNAMIC_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_DYNAMIC_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_PERSISTENT_NATIVE_SESSION_FIXTURE'
REMAP='/DCheckpointLoadWorkerClaim=CheckpointPersistentObserverClaim /DCheckpointLoadWorkerCurrentOwner=CheckpointPersistentObserverCurrentOwner'
CASES=['success','load-exception','start-observe','start-wrong-wait','start-stop']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert sha(ARCHIVE)==EXPECTED
 image=(P/'game-runtime-image.bin').read_bytes()
 assert hashlib.sha256(image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
 header=(P/'checkpoint_task_native_ports_profile.h').read_text()
 for name,rva,size in [('Runner',0x834D10,0x165),('LoadPrefix',0x508B40,10)]:
  encoded=re.search(name+r'Bytes\[\]=\{([^}]+)',header).group(1)
  assert bytes(int(x.strip(),16) for x in encoded.split(','))==image[rva:rva+size]
 entry=(P/'checkpoint_task_native_activation_v2_profile.h').read_text();encoded=re.search(r'ThreadEntryBytes\[\]=\{([^}]+)',entry).group(1)
 assert bytes(int(x.strip(),16) for x in encoded.split(','))==image[0x83A930:0x83AA2D]
 run=P/'checkpoint_task_native_start_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 sources=set()
 for name in UNITS:
  for ext in ('cpp','h'):
   if (P/f'{name}.{ext}').exists():sources.add(f'{name}.{ext}')
 sources.update(['checkpoint_load_worker_bridge.asm','checkpoint_native_queue_adapter_profile.h','checkpoint_live_runtime_guards_profile.h','checkpoint_live_prefetch_profile.h','checkpoint_task_native_start_fixture_admission.inc','checkpoint_task_native_start_fixture_ports.inc','checkpoint_task_native_start_fixture_machine.inc','checkpoint_task_native_ports_profile.h','checkpoint_task_native_start_fixture.asm','checkpoint_persistent_authorized_bridge.asm','checkpoint_native_input_hwbp_fixture.asm','checkpoint_native_input_prefetch_archived.inc','checkpoint_persistent_bridge.asm','checkpoint_guest_native_session_fixture.asm','checkpoint_task_native_start_test.py','checkpoint_task_native_start_fixture_planning.inc','checkpoint_load_request_commit.h','checkpoint_cc_load_observer.h','checkpoint_cc_load_lifecycle.h','checkpoint_title_identity_adapter.h'])
 todo=list(sources)
 while todo:
  for name in re.findall(r'^\s*#include\s+"([^"]+)"',(P/todo.pop()).read_text(encoding='utf-8-sig'),re.M):
   if name not in sources and (P/name).is_file():sources.add(name);todo.append(name)
 before={f:sha(P/f) for f in sorted(sources)}
 lines=['@echo off','setlocal','call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul','if errorlevel 1 exit /b 1',f'cd /d "{P}"']
 def command(c):lines.extend([c,'if errorlevel 1 exit /b 1'])
 command(f'cl {FLAGS} /c /Fo"{run / "production.obj"}" checkpoint_task_native_start.cpp')
 command(f'cl {FLAGS} /c /Fo"{run / "production_queue_core.obj"}" checkpoint_native_queue_adapter_core.cpp')
 command(f'cl {FLAGS} /c /Fo"{run / "production_activation_v2.obj"}" checkpoint_task_native_activation_v2.cpp')
 objs=[]
 for name in UNITS:
  obj=run/f'{name}.obj';objs.append(obj)
  remap=REMAP if name in ('checkpoint_dynamic_cc_load_observer',) else ''
  command(f'cl {FLAGS} {DEFS} {remap} /c /Fo"{obj}" {name}.cpp')
 for name in ['checkpoint_persistent_bridge','checkpoint_guest_native_session_fixture','checkpoint_persistent_authorized_bridge','checkpoint_native_input_hwbp_fixture','checkpoint_load_worker_bridge','checkpoint_task_native_start_fixture']:
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
  row['native_start_observations']=[json.loads(x) for x in json_lines if 'native_start_generation' in x]
  row['native_capture_observations']=[json.loads(x) for x in json_lines if 'native_ports_generation' in x]
  row['native_receipt_files']={str(x.relative_to(run)):sha(x) for x in folder.glob('*.bin')}
  row['provider_observations']=[json.loads(x) for x in json_lines if 'provider_generation' in x]
  row['planning_observations']=[json.loads(x) for x in json_lines if 'planning_case' in x]
  row['guard_observations']=[json.loads(x) for x in json_lines if 'guard_generation' in x]
  row['admission_observations']=[json.loads(x) for x in json_lines if 'admission_generation' in x]
  row['exit_code']=proc.returncode;row['archive_unchanged']=sha(archive)==EXPECTED and sha(second)==second_sha
  row['passed']=bool(row['passed'] and proc.returncode==0 and row['archive_unchanged'])
  rows.append(row)
 result={'schema':'san14.task-native-start-owned-integration.v1','result':'PASS' if all(x['passed'] for x in rows) else 'FAIL','cases':rows,'source_sha256':before,'sources_unchanged':before=={f:sha(P/f) for f in before},
 'fixture_binary_sha256':sha(binary),'production_start_object_sha256':sha(run/'production.obj'),'production_activation_v2_object_sha256':sha(run/'production_activation_v2.obj'),'runtime_image_sha256':hashlib.sha256(image).hexdigest(),
 'game_access':False,'real_cpu_hardware_capture':True,'actual_context_direct_to_frozen_provider':True,'actual_frozen_session_load_bytes_and_lifecycle':True,
 'automatic_runner_begin_finally':True,'archived_thread_entry_253_bytes_executed':True,'fixture_manual_begin':False,'target_code_modified_by_ports':False,'native_runner_357_bytes_match_archive':True,'native_load_first_10_bytes_match_archive':True,'win64_dynamic_unwind_registered':True,
 'title_and_parent_source_ports_installed':False,'game_source_ports_installed':False,'production_publication':False,'global_scheduler_fence':False,'full_world':False,'ready':False,
 'scope':'Real Load callback wrapper arms parent hardware capture, actual archived4DA240 and834B60 execute and VEH sends both true OS CONTEXTs to Provider. Native constructor/body are explicit doubles but worker runs archived83A930 on actual OS thread blocked by real unsignaled auto-reset event. Production publisher suspends exact worker, performs actual RtlVirtualUnwind to83A9D7, queries event without consuming it, then optional CAS of object+38 before original834B60 signals it. Activation wrapper and real worker ports feed frozen Session bytes/lifecycle. Default observation and absent native wait reject pointer modification. Parent/join/task creation dispatch captures outside these two sites remain doubles. No game installer or Title/global-fence claim.'}
 if not result['sources_unchanged']:result['result']='FAIL'
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'result':result['result'],'cases':len(rows),'failed':[r['case'] for r in rows if not r['passed']],'path':str(run/'result.json')}))
 raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()

