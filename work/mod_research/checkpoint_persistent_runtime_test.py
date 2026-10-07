"""Two generations through real cores and shared bridges, in an owned process only."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,shutil
P=Path(__file__).resolve().parent
ARCHIVE=P/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
EXPECTED='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
UNITS=['checkpoint_persistent_physical_owner','checkpoint_load_hook_set','checkpoint_native_queue_adapter_core','checkpoint_dynamic_native_queue_bridge','checkpoint_persistent_authorized_controller','checkpoint_bound_input_pending_adapter','checkpoint_native_input_pending_adapter','checkpoint_native_input_core','checkpoint_persistent_input_hwbp','checkpoint_dynamic_file_profile','checkpoint_persistent_bridge','checkpoint_persistent_route_core','checkpoint_persistent_route_worker_adapter','checkpoint_persistent_route_six_adapter','checkpoint_persistent_logical_adapter','checkpoint_dynamic_native_session','native_storage_read_core','checkpoint_dynamic_cc_load_observer','checkpoint_dynamic_cc_load_lifecycle','checkpoint_dynamic_title_identity_adapter','checkpoint_identity_pair_commit','checkpoint_dynamic_load_request_commit','checkpoint_load_input_boundary','checkpoint_persistent_planning_observer','checkpoint_persistent_runtime_fixture']
FLAGS='/nologo /W4 /WX /EHa /std:c++17 /O2 /MT'
DEFS='/DCHECKPOINT_PERSISTENT_PHYSICAL_OWNER_FIXTURE /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_PERSISTENT_AUTHORIZED_FIXTURE /DCHECKPOINT_PERSISTENT_PLANNING_FIXTURE /DCHECKPOINT_DYNAMIC_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_DYNAMIC_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_PERSISTENT_NATIVE_SESSION_FIXTURE'
REMAP='/DCheckpointLoadWorkerClaim=CheckpointPersistentObserverClaim /DCheckpointLoadWorkerCurrentOwner=CheckpointPersistentObserverCurrentOwner'
CASES=['success', 'actual-byte-mismatch', 'load-exception', 'read-exception', 'title-exception', 'user-exception', 'stop-after-cas', 'post-cas-reject', 'alternate-factions', 'planning-wrong-date', 'planning-wrong-district', 'planning-wrong-hash', 'planning-source-generation', 'planning-source-drift', 'planning-missing-join', 'planning-native-exception', 'planning-old-report', 'planning-reuse-load', 'input-pending', 'input-missing-prefetch', 'queue-wrong-generation', 'queue-stale-ticket', 'queue-wrong-controller', 'queue-copied-frame', 'queue-stop-authorized', 'queue-stop-native', 'queue-native-exception']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert sha(ARCHIVE)==EXPECTED
 run=P/'checkpoint_persistent_runtime_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 sources=set()
 for name in UNITS:
  for ext in ('cpp','h'):
   if (P/f'{name}.{ext}').exists():sources.add(f'{name}.{ext}')
 sources.update(['checkpoint_native_queue_adapter_profile.h','checkpoint_persistent_runtime_admission.inc','checkpoint_persistent_authorized_bridge.asm','checkpoint_native_input_hwbp_fixture.asm','checkpoint_native_input_prefetch_archived.inc','checkpoint_persistent_bridge.asm','checkpoint_guest_native_session_fixture.asm','checkpoint_persistent_runtime_test.py','checkpoint_persistent_runtime_planning.inc','checkpoint_load_request_commit.h','checkpoint_cc_load_observer.h','checkpoint_cc_load_lifecycle.h','checkpoint_title_identity_adapter.h'])
 before={f:sha(P/f) for f in sorted(sources)}
 lines=['@echo off','setlocal','call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul','if errorlevel 1 exit /b 1',f'cd /d "{P}"']
 def command(c):lines.extend([c,'if errorlevel 1 exit /b 1'])
 command(f'cl {FLAGS} /c /Fo"{run / "production.obj"}" checkpoint_dynamic_native_queue_bridge.cpp')
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
  row['planning_observations']=[json.loads(x) for x in json_lines if 'planning_case' in x]
  row['admission_observations']=[json.loads(x) for x in json_lines if 'admission_generation' in x]
  row['exit_code']=proc.returncode;row['archive_unchanged']=sha(archive)==EXPECTED and sha(second)==second_sha
  row['passed']=bool(row['passed'] and proc.returncode==0 and row['archive_unchanged'])
  rows.append(row)
 result={'schema':'san14.persistent-runtime-integration.v1','result':'PASS' if all(x['passed'] for x in rows) else 'FAIL','cases':rows,'source_sha256':before,'sources_unchanged':before=={f:sha(P/f) for f in before},'game_access':False,'production_admission':False,'native_scheduler_fence':False,'actual_hardware_prefetch_and_authorized_controller_integrated':True,'dynamic_native_file_date_identity_tested':True,'repeated_real_game_load_proven':False,'world_verified':False,'scope':'One immutable six-entry installation, two fresh Session objects and generation logical adapters. Actual owned CPU hardware breakpoint/prefetch context and restored debug registers, real private pending-input tickets, authorized Controller and Session menu binding. Real own-memory request and identity CAS, durable intent creation, full archive byte hash, OS worker/join and dynamic observer/lifecycle cores via explicit logical-TLS symbol binding. Second generation starts at B; synthetic load body restores A before identity observer converts to B. Fixture external attachment/root guard is also synthetic and not production authority. Native QueueMenu/load/file-read/title bodies are synthetic; queue authorization, validation, span resolution, Stop and native exception handling use the frozen real native queue Adapter through the new per-generation bridge. Second generation uses different bytes, size, digest, date, rulers, districts and opaque fields; alternate-factions case also varies source/target force IDs. Planning observer receives actual Session snapshots through an immutable provider and runs in same physical User callback. Wrong date/district/hash/generation/missing join and native User exception controls are explicit. No game deserialization, full-world/READY proof, actual scheduler handoff, live-game owner installation or game presentation/input hold.'}
 result['persistent_physical_owner_integrated']=True
 result['scope'] += ' Real physical owner configures and publishes six protected slots once, verifies original forwarding/protection, and retains them across both fixture generations. Initial bootstrap forwards without exposing partially initialized Session; fixture publication occurs after Session Initialize/activation. Real game runtime guards and production scheduler handoff remain unintegrated.'
 if not result['sources_unchanged']:result['result']='FAIL'
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'result':result['result'],'cases':len(rows),'failed':[r['case'] for r in rows if not r['passed']],'path':str(run/'result.json')}))
 raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
