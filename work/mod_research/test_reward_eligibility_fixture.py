import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent
results=[]
for case in ('success','duplicate-person','wrong-person-type','wrong-count','cycle','unknown-task','virtual-target',
             'gold-drift','cancel','bad-config','query-exception','invalid-result'):
    run=subprocess.run([str(ROOT/'reward_eligibility_fixture.exe'),str(ROOT/'reward_eligibility_fixture.dll'),case],
                       capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15)
    if run.returncode:raise RuntimeError(f'{case}: {run.returncode}, {run.stdout}, {run.stderr}')
    row=json.loads(run.stdout);assert row['passed'];results.append(row)
(ROOT/'reward-eligibility-fixtures.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'result':'PASS','tests':len(results),'cases':[r['case'] for r in results]},indent=2))
