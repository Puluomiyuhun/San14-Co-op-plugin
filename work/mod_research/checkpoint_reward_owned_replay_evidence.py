import pathlib,re,json,hashlib
p=pathlib.Path(__file__).resolve().parent
archive=p/'game-runtime-image.bin';data=archive.read_bytes();rows=[]
assert hashlib.sha256(data).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
for name in ['reward_probe_fingerprints.h','reward_eligibility_fingerprints.h','reward_execution_fingerprints.h']:
 text=(p/name).read_text()
 for m in re.finditer(r'\{(0x[0-9A-Fa-f]+),(?:(\d+),)?\{([^}]+)\}\}',text):
  address=int(m[1],16);expected=bytes(int(x,16) for x in re.findall(r'0x[0-9a-fA-F]+',m[3]));size=int(m[2]) if m[2] else 32
  assert len(expected)==size
  actual=data[address:address+size];assert actual==expected,(name,hex(address))
  rows.append({'source':name,'rva':hex(address),'size':size,'sha256':hashlib.sha256(actual).hexdigest(),'matches':True})
history=[]
for name in ['reward-execution-live-latest.json','second-force-reward-live-latest.json']:
 raw=(p/name).read_bytes();j=json.loads(raw);assert j['result']=='PASS' and j['executed']
 history.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'historical_stage':j['stage'],'historical_dll_sha256':j['dll_sha256'],'viewer_force':j.get('viewer_force_id',12),'command_force':j.get('command_force_id',12),'new_provider_live_execution':False})
out={'result':'PASS','archive':{'path':archive.name,'sha256':hashlib.sha256(data).hexdigest()},'exact_code_segments':rows,'historical_real_executions':history,'live_game_or_save_access':False,'claim':'Archived bytes plus historical earlier module runs establish layout and ABI; they do not prove this successor installed or ran in game.'}
(p/'checkpoint_reward_owned_replay_evidence.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'result':'PASS','segments':len(rows),'historical_executions':len(history)}))
