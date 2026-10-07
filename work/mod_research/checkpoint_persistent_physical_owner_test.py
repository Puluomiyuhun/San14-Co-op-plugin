from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
P=Path(__file__).resolve().parent
UNITS=['checkpoint_persistent_physical_owner','checkpoint_load_hook_set','checkpoint_persistent_bridge','checkpoint_persistent_route_core','checkpoint_persistent_route_worker_adapter','checkpoint_persistent_route_six_adapter','checkpoint_persistent_physical_owner_fixture']
CASES=['success','stop','drift','exception','stale-generation','guard-before','guard-partial','guard-after','publish-conflict','duplicate-slot','wrong-hook','original-bridge','forward-bridge','nonresident-original','existing-bridge']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 run=P/'checkpoint_persistent_physical_owner_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 sources=[f'{u}.{e}' for u in UNITS for e in ['cpp','h'] if (P/f'{u}.{e}').exists()]+['checkpoint_persistent_bridge.asm','checkpoint_persistent_physical_owner_test.py']
 hashes={f:sha(P/f) for f in sources}
 lines=['@echo off','setlocal','call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul','if errorlevel 1 exit /b 1',f'cd /d "{P}"']
 def command(c):lines.extend([c,'if errorlevel 1 exit /b 1'])
 for mode in ['fixture','production']:
  objs=[]
  for u in UNITS:
   obj=run/f'{mode}_{u}.obj';objs.append(obj)
   define='/DCHECKPOINT_PERSISTENT_PHYSICAL_OWNER_FIXTURE' if mode=='fixture' else ''
   command(f'cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT {define} /c /Fo"{obj}" {u}.cpp')
  obj=run/f'{mode}_asm.obj';objs.append(obj);command(f'ml64 /nologo /c /Fo "{obj}" checkpoint_persistent_bridge.asm')
  command(f'link /nologo /incremental:no /OUT:"{run / (mode+".exe")}" '+' '.join(f'"{o}"' for o in objs))
 build=run/'build.cmd';build.write_text('\n'.join(lines)+'\n')
 proc=subprocess.run(['cmd','/c',str(build)],cwd=P,capture_output=True);(run/'build.txt').write_bytes(proc.stdout+proc.stderr)
 if proc.returncode:print(proc.stdout.decode(errors='replace'));raise SystemExit(proc.returncode)
 rows=[]
 for mode,case in [('fixture',x) for x in CASES]+[('production','production')]:
  proc=subprocess.run([str(run/(mode+'.exe')),case],cwd=P,capture_output=True,timeout=15);(run/f'{mode}_{case}.txt').write_bytes(proc.stdout+proc.stderr)
  parsed=[json.loads(x) for x in proc.stdout.decode(errors='replace').splitlines() if x.startswith('{')];row=parsed[-1] if parsed else {'case':case,'passed':False}
  row.update(mode=mode,exit_code=proc.returncode);row['passed']=row['passed'] and proc.returncode==0;rows.append(row)
 result={'result':'PASS' if all(x['passed'] for x in rows) else 'FAIL','cases':rows,'source_sha256':hashes,'sources_unchanged':all(sha(P/f)==s for f,s in hashes.items()),'game_access':False,'production_generation_publication':False,'scope':'Real own-process protected six-slot publication, immutable bridge configuration, retained native forwarding, SEH/Finally, route generation composition. Production transitions refuse. Does not prove native scheduler handoff, game-specific validation or load authorization.'}
 if not result['sources_unchanged']:result['result']='FAIL'
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'cases':len(rows),'failed':[x['case'] for x in rows if not x['passed']],'path':str(run/'result.json')}));raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
