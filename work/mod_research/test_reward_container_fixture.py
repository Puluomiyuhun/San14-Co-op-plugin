"""Failure-injection tests in a separate synthetic process; never opens the game."""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
results=[]
for case in ('success','ctor-failure','append-failure','append-exception','wrong-count','wrong-order',
             'cycle','cleanup-leak','gold-drift','owner-drift','rewarded-drift','bad-config','wrong-pool-capacity','cancel'):
    run=subprocess.run([str(ROOT/'reward_container_fixture.exe'),str(ROOT/'reward_container_fixture.dll'),case],
                       capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15)
    if run.returncode:
        raise RuntimeError(f'{case}: exit={run.returncode}; stdout={run.stdout}; stderr={run.stderr}')
    row=json.loads(run.stdout)
    assert row['passed'] is True
    results.append(row)
(ROOT/'reward-container-fixtures.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'result':'PASS','tests':len(results),'cases':[r['case'] for r in results]},indent=2))
