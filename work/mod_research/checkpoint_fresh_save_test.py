"""Build production component and exercise real bridge scopes in owned processes."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
P=Path(__file__).resolve().parent
CASES=('success','cancel','stop-before-binder','stop-in-binder','stop-in-worker','stop-in-read','selection','unowned','date-drift','storage-drift','remote-exists','remote-null','binder-exception','wrong-binder','wrong-type','original-exception','wrong-save','phase-skip','save-exception','save-failure','uncleared','return-drift','stall','native-bytes-mismatch','native-short-read','native-validation-loss')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 run=P/'checkpoint_fresh_save_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 sources={name:sha(P/name) for name in ('checkpoint_fresh_save.h','checkpoint_fresh_save.cpp','checkpoint_fresh_save_fixture.cpp','checkpoint_fresh_save_fixture.asm','checkpoint_persistent_bridge.h','checkpoint_persistent_bridge.cpp','checkpoint_persistent_bridge.asm','checkpoint_load_worker_bridge.h','checkpoint_push_pilot.h','checkpoint_push_profile.h','native_storage_read_core.cpp','native_storage_read_core.h')}
 vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
 flags='/nologo /std:c++17 /EHa /W4 /WX /wd4324 /O2 /MT'
 commands=[f'cl {flags} /c "{P}/checkpoint_fresh_save.cpp" /Fo:production.obj',
 f'cl {flags} /c "{P}/native_storage_read_core.cpp" /Fo:storage.obj',
 f'lib /nologo /OUT:checkpoint_fresh_save.lib production.obj storage.obj',
 f'cl {flags} /DCHECKPOINT_FRESH_SAVE_FIXTURE /c "{P}/checkpoint_fresh_save.cpp" /Fo:driver.obj',
 f'cl {flags} /DCHECKPOINT_FRESH_SAVE_FIXTURE /c "{P}/checkpoint_fresh_save_fixture.cpp" /Fo:fixture.obj',
 f'cl {flags} /c "{P}/checkpoint_persistent_bridge.cpp" /Fo:bridge.obj',
 f'ml64 /nologo /c /Fo bridge_asm.obj "{P}/checkpoint_persistent_bridge.asm"',
 f'ml64 /nologo /c /Fo fixture_asm.obj "{P}/checkpoint_fresh_save_fixture.asm"',
 'link /nologo /OUT:fixture.exe driver.obj fixture.obj storage.obj bridge.obj bridge_asm.obj fixture_asm.obj bcrypt.lib']
 build=run/'build.cmd';build.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
 compiled=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True,text=True,errors='replace')
 (run/'build.log').write_text(compiled.stdout+compiled.stderr,encoding='utf8')
 if compiled.returncode:print(compiled.stdout+compiled.stderr);raise SystemExit(compiled.returncode)
 rows=[]
 for case in CASES:
  directory=run/case;directory.mkdir()
  process=subprocess.run([str(run/'fixture.exe'),case,str(directory)],cwd=run,capture_output=True,text=True,timeout=20)
  try: row=json.loads(process.stdout)
  except ValueError: row={'case':case,'result':'FAIL','stdout':process.stdout}
  row.update(exit=process.returncode,stderr=process.stderr);rows.append(row)
  print(case,row['result'],row.get('error'),process.stderr)
 unchanged=sources=={name:sha(P/name) for name in sources}
 result={'schema':'san14.fresh-save-owned.v1','result':'PASS' if unchanged and all(r['result']=='PASS' and r['exit']==0 for r in rows) else 'FAIL','cases':rows,'sources':sources,'sources_unchanged':unchanged,'production_sha256':sha(run/'checkpoint_fresh_save.lib'),'fixture_sha256':sha(run/'fixture.exe'),'game_access':False,'native_business_bodies':'Explicit fixture substitutes; actual immutable assembly bridge, ownership TLS, native-layout reads, Win32 intent/file writes and exception unwind. Not actual SAN14 serialization.','game_installer':False,'full_world':False,'room_ready':False}
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps({'result':result['result'],'path':str(run/'result.json')}));raise SystemExit(result['result']!='PASS')
if __name__=='__main__':main()
