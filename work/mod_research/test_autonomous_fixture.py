"""Run isolated simulated scheduling/guard tests. Never opens the actual game."""
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parent
results=[]
for case in ('dry','execute','wrong-command','resource-drift','wrong-owner','cancel'):
    run=subprocess.run([str(root/'autonomous_fixture.exe'),str(root/'autonomous_fixture.dll'),case],
                       capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15)
    if run.returncode:
        raise RuntimeError(f'{case}: exit={run.returncode}; stdout={run.stdout}; stderr={run.stderr}')
    result=json.loads(run.stdout)
    assert result['passed'] is True
    results.append(result)
(root/'autonomous-fixture-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
