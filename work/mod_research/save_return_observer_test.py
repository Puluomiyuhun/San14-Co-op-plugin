"""Native observer tests against our dedicated process, never SAN14."""
from pathlib import Path
from datetime import datetime
import subprocess,time,json,hashlib
P=Path(__file__).resolve().parent;folder=P/'save_return_observer_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
def rows(p):
 try:return [json.loads(s) for s in p.read_text(encoding='utf8').splitlines() if s]
 except (OSError,json.JSONDecodeError):return []
def wait(f,seconds=10):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  value=f()
  if value:return value
  time.sleep(.01)
 raise AssertionError('wait timeout')
cases=[]
for name in ('paired','threads','reentry','nested','timeout','cancel','stall'):
 out=folder/name;out.mkdir();ready=out/'ready.json';go=out/'go';log=out/'trace.jsonl';done=Path(str(go)+'.done');stop=Path(str(log)+'.stop')
 fp=subprocess.Popen([str(P/'save_return_observer_fixture.exe'),str(ready),str(go),name],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
 op=None
 try:
  info=wait(lambda:rows(ready))[0]
  op=subprocess.Popen([str(P/'save_return_observer.exe'),str(info['pid']),hex(info['base']),'1' if name in ('timeout','stall') else '15',str(log),'--fixture'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
  wait(lambda:any(x['event']=='armed' for x in rows(log)) or op.poll() is not None)
  assert op.poll() is None,(name,rows(log),op.communicate())
  if name=='cancel':stop.write_text('stop',encoding='ascii')
  elif name!='timeout':go.write_text('go',encoding='ascii')
  if name in ('paired','threads'):
   wait(lambda:done.exists() or fp.poll() is not None)
   assert done.exists(),(name,fp.communicate())
   stop.write_text('stop',encoding='ascii')
  stdout,stderr=op.communicate(timeout=20)
  if name in ('timeout','cancel'):go.write_text('go',encoding='ascii')
  fs,fe=fp.communicate(timeout=15);trace=rows(log)
  assert fp.returncode==0,(name,fs,fe,trace[-3:])
  fixture=json.loads(fs);assert fixture['result']=='PASS' and not fixture['debugger_attached'] and fixture['rax_and_four_arguments_preserved']
  success=name in ('paired','threads');anomaly=name in ('reentry','nested')
  assert op.returncode==(0 if success else 1 if anomaly else 4),(name,op.returncode,stderr,trace[-3:])
  last=trace[-1];assert last['registers_restored'] and (last['event']=='detached' or last.get('detached')),(name,last)
  assert last['complete']==success
  callbacks=[x for x in trace if x['event']=='callback'];pairs={}
  for row in callbacks:pairs.setdefault(row['call_id'],[]).append(row)
  if success:
   assert len(pairs)==(8 if name=='threads' else 4)
   for values in pairs.values():
    assert [x['boundary'] for x in values]==['entry','native_ret','returned']
    assert len({x['thread'] for x in values})==1
    assert values[1]['rax']==values[2]['rax']
    assert int(values[1]['rsp'],16)==int(values[0]['rsp'],16)
    assert int(values[2]['rsp'],16)==int(values[0]['rsp'],16)+8
   if name=='threads':assert len({x['thread'] for x in callbacks})==2
  if anomaly:
   error=next(x for x in trace if x['event']=='incomplete_error')
   assert error['message']==('ret_stack_mismatch_reentry_or_unwind' if name=='reentry' else 'nested_callback_incomplete'),error
  if name=='stall':assert last['open_calls']==1
  cases.append({'case':name,'result':'PASS','observer_exit':op.returncode,'callback_records':len(callbacks),'trace':str(log),'fixture':fixture,'stderr':stderr.decode(errors='replace')})
  print(json.dumps({'case':name,'result':'PASS'}),flush=True)
 finally:
  if op and op.poll() is None:stop.write_text('stop',encoding='ascii');op.wait(timeout=20)
  if fp.poll() is None:go.write_text('go',encoding='ascii');fp.wait(timeout=15)
cleanup=subprocess.run([str(P/'save_return_observer_cleanup_fixture.exe')],capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
c=json.loads(cleanup.stdout);assert c['result']=='PASS' and c['cases']==6
report={'result':'PASS','game_access':False,'cases':cases,'cleanup':c,'binary_sha256':hashlib.sha256((P/'save_return_observer.exe').read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256((P/'save_return_observer_fixture.exe').read_bytes()).hexdigest(),
        'limits':['Synthetic functions emulate ABI and return points only; no real game callback execution','Hardware debugging affects timing','Main loop is not hooked; coarse samples are asynchronous and labeled as such','No live install or export was tested']}
result=folder/'result.json'
with result.open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
print(json.dumps({'result':'PASS','cases':len(cases),'cleanup_cases':6,'evidence':str(result),'game_access':False}))
