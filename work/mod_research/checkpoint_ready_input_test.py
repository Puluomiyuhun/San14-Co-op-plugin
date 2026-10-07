import pathlib,subprocess,json
p=pathlib.Path(__file__).resolve().parent
cases=['production-reject','open','ui-posts-panel','held','held-reward','release','disconnect','phase-drift','menu-pending','late-panel','wrong-binding','ui-exception']
rows=[]
for case in cases:
 r=subprocess.run([str(p/('checkpoint_ready_input_production_fixture.exe' if case=='production-reject' else 'checkpoint_ready_input_fixture.exe')),case],cwd=p,capture_output=True,text=True,timeout=20)
 try:j=json.loads(r.stdout)
 except:j={'result':'FAIL','stdout':r.stdout,'stderr':r.stderr}
 j['exit']=r.returncode;rows.append(j);print(case,j)
out={'result':'PASS' if all(x['result']=='PASS' and x['exit']==0 for x in rows) else 'FAIL','count':len(rows),'cases':rows,'game_access':False,'scope':'actual two assembly caller return sites + Game/User six-slot bridge + frozen dispatcher and concrete reward DLL; UI/native world fixture doubles'}
(p/'checkpoint_ready_input_result.json').write_text(json.dumps(out,indent=2)+'\n');raise SystemExit(out['result']!='PASS')
