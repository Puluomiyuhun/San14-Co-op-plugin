"""Two generations through real cores and shared bridges, in an owned process only."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,shutil
P=Path(__file__).resolve().parent
ARCHIVE=P/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
EXPECTED='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
UNITS=['checkpoint_persistent_bridge','checkpoint_persistent_route_core','checkpoint_persistent_route_worker_adapter','checkpoint_persistent_route_six_adapter','checkpoint_persistent_logical_adapter','checkpoint_persistent_native_session','native_storage_read_core','checkpoint_cc_load_observer','checkpoint_cc_load_lifecycle','checkpoint_title_identity_adapter','checkpoint_identity_pair_commit','checkpoint_load_request_commit','checkpoint_load_input_boundary','checkpoint_persistent_native_session_fixture']
FLAGS='/nologo /W4 /WX /EHa /std:c++17 /O2 /MT'
DEFS='/DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_PERSISTENT_NATIVE_SESSION_FIXTURE'
REMAP='/DCheckpointLoadWorkerClaim=CheckpointPersistentObserverClaim /DCheckpointLoadWorkerCurrentOwner=CheckpointPersistentObserverCurrentOwner'
CASES=['success','actual-byte-mismatch','load-exception','read-exception','title-exception','user-exception','stop-after-cas','post-cas-reject']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert sha(ARCHIVE)==EXPECTED
 run=P/'checkpoint_persistent_native_session_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 sources=set()
 for name in UNITS:
  for ext in ('cpp','h'):
   if (P/f'{name}.{ext}').exists():sources.add(f'{name}.{ext}')
 sources.update(['checkpoint_persistent_bridge.asm','checkpoint_guest_native_session_fixture.asm','checkpoint_persistent_native_session_test.py'])
 before={f:sha(P/f) for f in sorted(sources)}
 lines=['@echo off','setlocal','call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul','if errorlevel 1 exit /b 1',f'cd /d "{P}"']
 def command(c):lines.extend([c,'if errorlevel 1 exit /b 1'])
 command(f'cl {FLAGS} /c /Fo"{run / "production.obj"}" checkpoint_persistent_native_session.cpp')
 objs=[]
 for name in UNITS:
  obj=run/f'{name}.obj';objs.append(obj)
  remap=REMAP if name in ('checkpoint_cc_load_observer','checkpoint_title_identity_adapter') else ''
  command(f'cl {FLAGS} {DEFS} {remap} /c /Fo"{obj}" {name}.cpp')
 for name in ['checkpoint_persistent_bridge','checkpoint_guest_native_session_fixture']:
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
  folder=run/case;folder.mkdir();archive=folder/'svdexccSC03.s14';shutil.copyfile(ARCHIVE,archive)
  proc=subprocess.run([str(binary),case,str(archive),str(folder)],cwd=P,capture_output=True,timeout=30)
  (folder/'stdout.txt').write_bytes(proc.stdout);(folder/'stderr.txt').write_bytes(proc.stderr)
  json_lines=[x for x in proc.stdout.decode(errors='replace').splitlines() if x.startswith('{')]
  row=json.loads(json_lines[-1]) if json_lines else {'case':case,'passed':False}
  row['exit_code']=proc.returncode;row['archive_unchanged']=sha(archive)==EXPECTED
  row['passed']=bool(row['passed'] and proc.returncode==0 and row['archive_unchanged'])
  rows.append(row)
 result={'schema':'san14.persistent-session-core-integration.v1','result':'PASS' if all(x['passed'] for x in rows) else 'FAIL','cases':rows,'source_sha256':before,'sources_unchanged':before=={f:sha(P/f) for f in before},'game_access':False,'production_admission':False,'native_scheduler_fence':False,'repeated_real_game_load_proven':False,'world_verified':False,'scope':'One immutable six-entry installation, two fresh Session objects and generation logical adapters. Real own-memory request and identity CAS, durable intent creation, full archive byte hash, OS worker/join and actual frozen observer/lifecycle cores via explicit logical-TLS symbol binding. Second generation starts at B; synthetic load body restores A before real identity observer converts to B. Native queue/load/file-read/title bodies are synthetic. Fixed historical file/date/factions; no game deserialization, changing checkpoint parameters, planning readiness or controller integration.'}
 if not result['sources_unchanged']:result['result']='FAIL'
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'result':result['result'],'cases':len(rows),'failed':[r['case'] for r in rows if not r['passed']],'path':str(run/'result.json')}))
 raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
