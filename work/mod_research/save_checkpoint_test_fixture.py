"""Run private-process fixtures only; never opens SAN14 or its save directory."""
from pathlib import Path
from datetime import datetime
import json,subprocess
ROOT=Path(__file__).resolve().parent
CASES=('dry','queue','slot34','wrong-date','wrong-phase','wrong-owner','wrong-ruler','busy-queue','busy-request',
       'existing-local','late-local','remote-exists','remote-unavailable','storage-phase-drift','intent-exists',
       'cancel','original-drift','binder-mismatch','queue-failure','binder-exception')
run=ROOT/'save_checkpoint_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
run.mkdir(parents=True,exist_ok=False)
rows=[]
for case in CASES:
 folder=run/case;folder.mkdir()
 result=subprocess.run([str(ROOT/'save_checkpoint_fixture.exe'),str(ROOT/'save_checkpoint_fixture.dll'),case,str(folder)],capture_output=True,text=True,timeout=15)
 try:row=json.loads(result.stdout)
 except Exception:raise RuntimeError((case,result.returncode,result.stdout,result.stderr))
 assert result.returncode==0 and row['passed'],row
 rows.append(row)
report={'result':'PASS','cases':rows,'case_count':len(rows),'directory':str(run),
        'scope':'Own fixture process, stub binder/queue/storage query; actual save worker and disk backend are not executed.',
        'game_access':False,'native_saved':False,'native_queued':False}
(ROOT/'save_checkpoint_fixture_results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','cases':len(rows),'game_access':False}))
