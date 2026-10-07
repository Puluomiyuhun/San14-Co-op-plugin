import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
result=subprocess.run([str(ROOT/'next_cell_payload_fixture.exe')],capture_output=True,text=True)
assert result.returncode==0,result.stderr
rows=[json.loads(s) for s in result.stdout.splitlines()]
assert rows[0]['working_ids']==[17] and rows[0]['pending_ids']==[] and rows[0]['progress_stage']==24
assert rows[0]['next_cell']==23804 and rows[0]['actual_cell']==24023 and not rows[0]['late']
assert rows[1]['late'] and rows[2]['result']=='PASS'
infra=json.loads((ROOT/'next-cell-fixtures.json').read_text(encoding='utf-8'))
sha=hashlib.sha256((ROOT/'observe_next_cell.exe').read_bytes()).hexdigest()
assert infra['result']=='PASS' and infra['observer_sha256']==sha
report={'result':'PASS','observer_sha256':sha,'payload_fixture_sha256':hashlib.sha256((ROOT/'next_cell_payload_fixture.exe').read_bytes()).hexdigest(),
    'scope':'Synthetic list/state/unit snapshot, late-date boundary and cycle rejection. Not an actual asynchronous game test.',
    'payload_cases':rows,'infrastructure':infra['cases']}
(ROOT/'next-cell-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'result':'PASS','payload_rows':len(rows),'observer_sha256':sha}))
