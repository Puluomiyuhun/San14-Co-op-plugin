import pathlib,subprocess,json
p=pathlib.Path(__file__).resolve().parent
cases=['pool-replaced','links-corrupted','remote-force-while-local-held','cost-change','success','node-change','funding-change','officer-change','cross-force-officer','attachment-change','date-change','cancel','cancel-during','foreign-close','exception','seh-exception','zero-result','cross-force-command','append-failure','expired','expires-after-prepare','consume-change','consume-cancel','production-refuses-fixture']
results=[]
for case in cases:
 r=subprocess.run([str(p/'checkpoint_reward_owned_replay_fixture.exe'),case],cwd=p,text=True,capture_output=True,timeout=20)
 try: result=json.loads(r.stdout)
 except: result={'result':'FAIL','case':case,'stdout':r.stdout,'stderr':r.stderr}
 result['exit']=r.returncode;results.append(result);print(result)
out={'result':'PASS' if all(x['result']=='PASS' and x['exit']==0 for x in results) else 'FAIL','cases':results,'count':len(results),'game_access':False,'native_helpers':'Own-process doubles with archived SAN14 pooled-list layout; not real-game execution','frozen_adapter':'Normally loaded checkpoint_planning_hold.dll, actual exported authorize/replay and capture callback'}
(p/'checkpoint_reward_owned_replay_result.json').write_text(json.dumps(out,indent=2)+'\n')
raise SystemExit(out['result']!='PASS')
