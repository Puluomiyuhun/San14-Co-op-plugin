"""Actual debugger tests against the dedicated owned fixture only."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,time
P=Path(__file__).resolve().parent
CHECKPOINT=P.parent/'mod_test/replay-checkpoint-34/svdexSC34.s14'
CASES=('complete','deserialize_id_map_unavailable','worker_id_map_unavailable','wrong_target','wrong_filename','wrong_code','deserialize_wrong_date','timeout','cancel','wrong_birth','initial_user_phase0','initial_ui_not_ready','invalid_user_phase')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
 try:return [json.loads(x) for x in p.read_text().splitlines() if x]
 except (OSError,json.JSONDecodeError):return []
def wait(f):
 end=time.monotonic()+10
 while time.monotonic()<end:
  result=f()
  if result:return result
  time.sleep(.02)
 raise AssertionError('owned fixture wait expired')
def main():
 assert sha(CHECKPOINT)=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
 run=P/'checkpoint_manual_reload_observe_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 build=subprocess.run(['cmd','/c',str(P/'checkpoint_manual_reload_observe_build.cmd')],capture_output=True,cwd=P)
 (run/'build.stdout.txt').write_bytes(build.stdout);(run/'build.stderr.txt').write_bytes(build.stderr)
 if build.returncode:print(build.stdout.decode(errors='replace'));raise SystemExit(build.returncode)
 result=[]
 for case in CASES:
  d=run/case;d.mkdir();ready=d/'ready.json';go=d/'go';trace=d/'trace.jsonl';observer=None
  fixture=subprocess.Popen([str(P/'checkpoint_manual_reload_observe_fixture.exe'),str(ready),str(go),case],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   info=wait(lambda:rows(ready))[0];birth=info['birth']+(1 if case=='wrong_birth' else 0)
   observer=subprocess.Popen([str(P/'checkpoint_manual_reload_observe.exe'),str(info['pid']),hex(info['base']),'1' if case=='timeout' else '10',str(trace),str(birth),str(CHECKPOINT)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
   wait(lambda:any(x.get('event')=='armed' for x in rows(trace)) or observer.poll() is not None)
   if case=='cancel':Path(str(trace)+'.stop').write_text('stop')
   elif case!='timeout':go.write_text('go')
   stdout,stderr=observer.communicate(timeout=20);go.write_text('go')
   fs,fe=fixture.communicate(timeout=10);events=rows(trace);event_names=[x.get('event') for x in events]
   (d/'observer.stderr.txt').write_bytes(stderr);(d/'fixture.stdout.txt').write_bytes(fs);(d/'fixture.stderr.txt').write_bytes(fe)
   assert fixture.returncode==0,(case,fs,fe,events)
   own=json.loads(fs);assert own['request']==-1 and not own['consumed'] and own['changed_request_bytes']==0 and not own['debugger_attached']
   complete=case in ('complete','deserialize_id_map_unavailable','initial_user_phase0','initial_ui_not_ready');timed=case in ('timeout','cancel')
   assert observer.returncode==(0 if complete else 4 if timed else 1),(case,observer.returncode,events)
   if complete or timed:assert events[-1]=={'event':'detached','captured':complete,'registers_restored':True},(case,events)
   elif 'attached' in event_names:assert events[-1]=={'event':'error_cleanup','registers_restored':True,'detached':True},(case,events)
   if complete:assert event_names.count('manual_same_player_reload_observed')==1 and event_names.count('deserialize_return')==1 and event_names.count('load_worker_result')==1
   if case=='deserialize_id_map_unavailable':assert own['semantic_maps_unavailable_at_deserialize'] and own['semantic_maps_restored_before_worker']
   if case in ('initial_user_phase0','initial_ui_not_ready'):assert event_names.count('rebuilt_user_waiting_for_planning')==1
   if case=='worker_id_map_unavailable':assert 'deserialize_return' in event_names and 'load_worker_result' not in event_names and any('address=0x11 ' in x.get('message','') for x in events)
   assert 'reload_request_written' not in event_names
   result.append({'case':case,'result':'PASS','exit_code':observer.returncode,'events':event_names,'fixture':own})
  finally:
   if observer and observer.poll() is None:Path(str(trace)+'.stop').write_text('stop');observer.wait(timeout=15)
   if fixture.poll() is None:go.write_text('go');fixture.wait(timeout=10)
 sources=['checkpoint_manual_reload_observe.cpp','checkpoint_manual_reload_observe_payload.inc','checkpoint_manual_reload_observe_fixture.cpp','checkpoint_manual_reload_observe_build.cmd','checkpoint_manual_reload_observe_test.py','auto_reload_profile.h','auto_reload_cleanup.inc']
 report={'schema':'san14.manual-reload-observe-fixtures.v1','result':'PASS','cases':result,'binary_sha256':sha(P/'checkpoint_manual_reload_observe.exe'),'fixture_binary_sha256':sha(P/'checkpoint_manual_reload_observe_fixture.exe'),'source_sha256':{x:sha(P/x) for x in sources},'game_access':False,'process_memory_write_api_used':False,'native_game_load_proven':False,'scope':'Actual Windows debugger/hardware breakpoint lifecycle against owned synthetic manual loader. Stage ordering, early unavailable semantic maps, later rebuilt maps, exact target rejection, PID birth, timeout/cancel/detach. No native full-world load or live attachment.'}
 (run/'result.json').write_text(json.dumps(report,indent=2)+'\n');(P/'checkpoint_manual_reload_observe_test_results.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'result':'PASS','cases':len(result),'path':str(run/'result.json')}))
if __name__=='__main__':main()
