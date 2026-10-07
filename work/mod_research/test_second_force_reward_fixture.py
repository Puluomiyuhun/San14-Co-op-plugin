import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent
CASES=('dry','execute','eligibility-denied','eligibility-drift','query-exception',
       'precommit-gold-drift','gold-drift','foreign-owner','scope-drift','funding-drift','virtual-target','unknown-task',
       'ctor-failure','append-failure','append-exception','wrong-id','wrong-count','cycle','cleanup-leak',
       'submit-exception','submit-rejected','unexpected-effect','cancel','bad-config','host-resource-drift')
def main():
    results=[]
    for case in CASES:
        run=subprocess.run([str(ROOT/'second_force_reward_fixture.exe'),str(ROOT/'second_force_reward_fixture.dll'),case],
                           capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15)
        if run.returncode:raise RuntimeError(f'{case}: {run.returncode}, {run.stdout}, {run.stderr}')
        row=json.loads(run.stdout);assert row['passed'];results.append(row)
    (ROOT/'second-force-reward-fixtures.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({'result':'PASS','tests':len(results),'cases':[r['case'] for r in results]},indent=2))
if __name__=='__main__':main()
