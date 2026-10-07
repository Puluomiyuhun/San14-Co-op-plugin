import subprocess,pathlib,json
p=pathlib.Path(__file__).resolve().parent
cases=['production-target-reject','existing-owner','hold-only','held-reward','two-workers','drain','forward-only','open-reward','hold-during-body','cancel-before','release-during-reward','disconnect-before','disconnect-during-reward','phase-reject','menu-reject','body-exception','reward-exception','unowned-call']
rows=[]
for case in cases:
 r=subprocess.run([str(p/('checkpoint_planning_dispatcher_production_fixture.exe' if case=='production-target-reject' else 'checkpoint_planning_dispatcher_fixture.exe')),case],cwd=p,capture_output=True,text=True,timeout=20)
 try: j=json.loads(r.stdout)
 except: j={'result':'FAIL','stdout':r.stdout,'stderr':r.stderr}
 j['exit']=r.returncode;rows.append(j);print(case,j)
out={'result':'PASS' if all(r['result']=='PASS' and r['exit']==0 for r in rows) else 'FAIL','count':len(rows),'cases':rows,'game_access':False,'native_helpers':'reward owned fixture DLL native-layout doubles; actual frozen PlanningHold DLL and six-slot FINALLY assembly bridge'}
(p/'checkpoint_planning_dispatcher_result.json').write_text(json.dumps(out,indent=2)+'\n');raise SystemExit(out['result']!='PASS')
