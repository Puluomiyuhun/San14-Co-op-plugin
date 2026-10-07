"""Manual-only load34 observer. Default precheck; --observe never submits a load.

Prints READY only after DebugActiveProcess, kill-on-exit disabled, all enumerated
threads armed, and the initial debug breakpoint has been processed. Then the user
may manually load slot34. All results are written to a fresh workspace directory.
"""
from pathlib import Path
from datetime import datetime
import argparse,ctypes as C,hashlib,json,os,struct,subprocess,sys,time
from ctypes import wintypes as W
P=Path(__file__).resolve().parent
CHECKPOINT=Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14')
EXPECTED='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
BUILD='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,value):
 with p.open('x',encoding='utf8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def rows(p):
 try:return [json.loads(x) for x in p.read_text().splitlines() if x]
 except (OSError,json.JSONDecodeError):return []
def precheck():
 sys.path.insert(0,str(P.parents[1]/'outputs/san14-link'))
 from game_reader import GameReader
 from startup_identity_reader import capture_startup_context
 reader=GameReader()
 try:
  m=reader.memory;k=m.k;context=capture_startup_context(reader);snapshot=context['snapshot'];reasons=[]
  need=lambda ok,reason:reasons.append(reason) if not ok else None
  k.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)];k.CheckRemoteDebuggerPresent.restype=W.BOOL
  debugger=W.BOOL();need(k.CheckRemoteDebuggerPresent(m.handle,C.byref(debugger)) and not debugger.value,'debugger_present_or_query_failed')
  times=[W.FILETIME() for _ in range(4)];k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.GetProcessTimes.restype=W.BOOL
  need(k.GetProcessTimes(m.handle,*[C.byref(x) for x in times]),'birth_query_failed');birth=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime
  need(reader.sha256==BUILD,'unsupported_build');need(snapshot['player']['force_id']==12 and snapshot['player']['ruler_id']==666,'not_Zhang_Lu')
  need(snapshot['date']=={'year':203,'month':8,'day':11,'period':'中旬'},'not_checkpoint34_date')
  need(snapshot['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'],'not_idle_planning')
  need(context['state_sample'] is not None and context['state_sample']['phase_raw']==2 and context['world_mode']==1,'not_planning_phase2')
  need(CHECKPOINT.stat().st_size==274920 and sha(CHECKPOINT)==EXPECTED,'checkpoint34_changed')
  image=(P/'game-runtime-image.bin').read_bytes()
  for guard in load(P/'auto_reload_profile.json')['ranges']:
   need(m.read(m.base+guard['start'],guard['end']-guard['start'])==image[guard['start']:guard['end']],'code_mismatch_'+hex(guard['start']))
  u64=lambda at:struct.unpack('<Q',m.read(at,8))[0];i32=lambda at:struct.unpack('<i',m.read(at,4))[0]
  slots=[(0x12CC9B8+0x28,0x3F8140),(0x12CC4A8+0x28,0x3F9B00)]
  for slot,original in slots:need(u64(m.base+slot)==m.base+original,'original_update_slot_mismatch_'+hex(slot))
  manager=u64(m.base+0x2025318);need(i32(manager+0x3EC)==-1,'pending_load_request');need(u64(m.base+0x19E7310+0x30)==0,'pending_state_command')
  need(context==capture_startup_context(reader),'context_changed_during_precheck')
  return {'result':'PASS' if not reasons else 'BLOCKED','reasons':reasons,'pid':reader.pid,'process_birth':birth,'base':hex(m.base),'context':context,'cache_mode_diagnostic':i32(manager+8),'game_data_writes':0,'debugger_attached':False,'cache_and_slot_metadata_required':False}
 finally:reader.close()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--observe',action='store_true');p.add_argument('--seconds',type=int,default=600);args=p.parse_args()
 assert 1<=args.seconds<=900
 run=P/'checkpoint_manual_reload_observe_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 before=precheck();save(run/'before.json',before)
 if not args.observe or before['result']!='PASS':print(json.dumps({'directory':str(run),**before},ensure_ascii=False));return
 binary=P/'checkpoint_manual_reload_observe.exe';tests=load(P/'checkpoint_manual_reload_observe_test_results.json')
 assert tests['result']=='PASS' and len(tests['cases'])==13 and tests['binary_sha256']==sha(binary),'exact observer binary must pass owned debugger fixtures'
 assert all(sha(P/name)==expected for name,expected in tests['source_sha256'].items()),'tested sources changed'
 intent={'schema':'san14.manual-reload-observation-intent.v1','pid':before['pid'],'birth':before['process_birth'],'base':before['base'],'binary_sha256':sha(binary),'native_request_submitted':False,'load_action':'manual user selection only','duration_seconds':args.seconds,'outcome':'not_yet_observed'}
 save(run/'observation.once.json',intent)
 trace=run/'trace.jsonl';proc=None;interrupted=None;ready=False
 with (run/'stdout.log').open('xb') as out,(run/'stderr.log').open('xb') as err:
  try:
   proc=subprocess.Popen([str(binary),str(before['pid']),before['base'],str(args.seconds),str(trace),str(before['process_birth']),str(CHECKPOINT)],stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
   end=time.monotonic()+15
   while proc.poll() is None and time.monotonic()<end:
    events=rows(trace)
    if any(x.get('event')=='attached' for x in events) and any(x.get('event')=='armed' for x in events):
     ready=True;print(json.dumps({'status':'READY_FOR_MANUAL_LOAD34','observer_pid':proc.pid,'game_pid':before['pid'],'directory':str(run),'trace':str(trace),'seconds':args.seconds,'game_data_writes':0},ensure_ascii=False),flush=True);break
    time.sleep(.1)
   if not ready and proc.poll() is None:raise RuntimeError('observer did not become ready; stopping')
   proc.wait(timeout=args.seconds+20)
  except BaseException as exc:interrupted=type(exc).__name__+': '+str(exc)
  finally:
   if proc and proc.poll() is None:
    Path(str(trace)+'.stop').write_text('stop',encoding='ascii')
    try:proc.wait(timeout=20)
    except subprocess.TimeoutExpired:interrupted=(interrupted or '')+'; observer cleanup still running; do not terminate or retry'
 events=rows(trace);exit_code=proc.poll() if proc else None
 success=exit_code==0 and bool(events) and events[-1]=={'event':'detached','captured':True,'registers_restored':True} and any(x.get('event')=='manual_same_player_reload_observed' for x in events)
 result={'schema':'san14.manual-reload-observation-result.v1','result':'PASS' if success else 'NOT_COMPLETED','ready_seen':ready,'before':before,'binary_sha256':sha(binary),'observer_exit':exit_code,'interrupted':interrupted,'trace':events,'stdout':(run/'stdout.log').read_text(errors='replace'),'stderr':(run/'stderr.log').read_text(errors='replace'),'game_data_writes':0,'automatic_load_requests':0,'full_world_verified':False,'native_file_read_bytes_verified':False,'guest_identity_transfer_proven':False,'old_auto_once_reused':False}
 save(run/'result.json',result)
 print(json.dumps({'result':result['result'],'directory':str(run),'result_path':str(run/'result.json'),'observer_exit':exit_code,'cleanup_pending':exit_code is None},ensure_ascii=False),flush=True)
 if not success:raise SystemExit(1)
if __name__=='__main__':main()
