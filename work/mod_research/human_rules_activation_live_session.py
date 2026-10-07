"""Managed local-room, one-world AI-rule smoke. No save/load/advance command.

Two local TLS clients are diagnostic seats, not a real second game. The owner
keeps both peers alive, supervises native Faulted, and accepts only explicit
workspace control files: install, inspect, restore, close. No automatic expiry.
The stage stays pinned. Old stage/source claims are never reset or reused.
"""
from pathlib import Path
from datetime import datetime
import argparse,ctypes as C,hashlib,json,os,secrets,shutil,struct,subprocess,sys,threading,time
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P),str(P/'python_deps'),str(P.parents[1]/'outputs/san14-link')]
from battle_observer import BattleObserver
from checkpoint_push_start import process_birth
from run_autonomous_pilot import ProcessAPI,pefile
from checkpoint_live_prefetch_start import invoke,RemoteCallError
from checkpoint_complete_live_capture import known_snapshot,module_approval,readable
from human_rules_stage_live_start import profiles,same_known_data,GAME_SHA
from human_rules_activation_room import Config,export_config,require_current,rules
from room_session import Room,PROTOCOL,digest
from room_transport import Client,Server,make_certificate

DLL=P/'human_rules_activation_runs/20261007-233145-854344/production.dll'
DLL_SHA='fffd793bfd65c7082c838f11aec15506d193fc489f45ee50bd53f22455b3222d'
PUBLISHER=P/'human_rules_activation_publish_runs/20261007-234339-022744/inputs/publisher-production.exe'
PUB_SHA='b4cc81568ab6a17712369f246739fdef38cc902661bd10fafad77cffe50ab90f'
HANDOFF_SHA='4b1fd5938ac509c37730d021721751f580be0d10200fed71fe45881f192415fa'
REVIEW_SHA='2f55da881e4f6144a94e8d4825549afc7b7d223258277211269a2ed8783f6e41'
SOURCE=Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14')
SOURCE_SHA='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'

class Ai(C.Structure):
 _fields_=[('configured',C.c_bool),('installed',C.c_bool)]+[(k,C.c_uint64*4)for k in ('entered','native','bypassed','held')]+[(k,C.c_uint64)for k in ('active','exits','abnormal_exits')]
class Income(C.Structure):
 _fields_=[('configured',C.c_bool),('installed',C.c_bool)]+[(k,C.c_uint64)for k in ('entries','native','human','ai','held','active','exits','abnormal')]
class Report(C.Structure):
 _fields_=[('state',C.c_int32),('error',C.c_uint32),('blocked',C.c_uint64),('first_fault_thread',C.c_uint32),('binding',Config),('ai',Ai),('income',Income)]
assert (C.sizeof(Ai),C.sizeof(Income),C.sizeof(Report),Report.binding.offset)==(160,72,392,24)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(x,s):
 if not x:raise RuntimeError(s)
def write(path,value,exclusive=True):
 text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
 if exclusive:
  with path.open('x',encoding='utf8')as f:f.write(text);f.flush();os.fsync(f.fileno())
 else:
  temp=path.with_suffix('.tmp');temp.write_text(text,encoding='utf8');os.replace(temp,path)
def event(run,kind,**value):
 row={'time':datetime.now().astimezone().isoformat(), 'kind':kind,**value}
 with (run/'events.jsonl').open('a',encoding='utf8')as f:f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
 print(json.dumps(row,ensure_ascii=True),flush=True)
def report(api,address):
 code,raw=invoke(api,address,output_size=C.sizeof(Report));need(code==0,'Report export rejected')
 r=Report.from_buffer_copy(raw)
 def plain(v):return {n:list(getattr(v,n)) if isinstance(getattr(v,n),C.Array)else getattr(v,n)for n,_ in v._fields_}
 return {'state':r.state,'error':r.error,'blocked':r.blocked,'first_fault_thread':r.first_fault_thread,'binding_hex':bytes(r.binding).hex(),'ai':plain(r.ai),'income':plain(r.income)}
def descriptor(reader,address):
 raw=reader.memory.read(address,1208);need(raw==reader.memory.read(address,1208),'Descriptor changed')
 magic,version,size,pid,fixture,birth,base,module,allocation=struct.unpack_from('<Q4I4Q',raw)
 need((magic,version,size,fixture)==(0x31544753524C5548,1,1208,0),'Wrong descriptor ABI/build')
 need(struct.unpack_from('<4I',raw,1192)==(6,1,2,0),'Not sealed policy descriptor')
 return {'address':address,'pid':pid,'birth':birth,'base':base,'module':module,'allocation':allocation,'nonce':raw[56:88].hex(),'raw_sha256':hashlib.sha256(raw).hexdigest()}
def native_data(reader):
 m=reader.memory;b=m.base
 def v(a,f):return struct.unpack(f,m.read(a,struct.calcsize(f)))[0]
 root=v(b+0x1FCA1E0,'<Q');world=v(root+0x85130,'<Q');snap=reader.snapshot()
 need(reader.sha256==GAME_SHA,'Unsupported game build')
 need(snap['date']=={'year':203,'month':8,'day':11,'period':'中旬'} and snap['player']['force_id']==12,'Need restored slot34 Zhang Lu planning')
 need(snap['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'],'Need formal planning')
 need(sha(SOURCE)==SOURCE_SHA,'Original slot34 changed')
 need(all(m.read(b+rva,len(raw))==raw for rva,_,raw in profiles()),'A source hook is already installed')
 force_rows=[]
 for force,name in ((12,'张鲁'),(2,'刘备')):
  f=v(root+0xDCA0+force*8,'<Q');ruler=v(f+0x10,'<H');matches=[]
  for i in range(1,52):
   d=v(root+0xDE40+i*8,'<Q');ff,kind,leader=struct.unpack('<BBH',m.read(d+0x10,4))
   if ff==force and kind and leader and (kind==1 or leader==ruler):matches.append(i)
  # For this diagnostic only, unique match. Native canonical list resolver
  # independently revalidates the exact main district before Prepare/Seal.
  need(len(matches)==1,'Main district is not uniquely identified')
  force_rows.append({'id':force,'name':name,'main_district_id':matches[0]})
 return b,root,world,snap,force_rows,rules(v(b+0x18EB628,'<I'),(v(world+0x16A8,'<I')>>8)&1)

def publish(run,operation,reader,birth,desc,copied,binding):
 need(sha(PUBLISHER)==PUB_SHA and sha(copied)==DLL_SHA,'Published executable/module hash drift')
 intent=run/(operation+'-intent.json');write(intent,{'pid':reader.pid,'birth':birth,'descriptor':desc,'operation':operation})
 log=(run/(operation+'-publisher.log')).open('xb')
 args=[str(PUBLISHER),operation,str(reader.pid),str(birth),str(reader.memory.base),str(desc['address']),str(copied),desc['nonce'],str(binding)]
 child=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 write(run/(operation+'-publisher-process.json'),{'pid':child.pid,'args':args})
 try:child.wait(timeout=20)
 except subprocess.TimeoutExpired:
  log.close();raise RuntimeError(f'Publisher {child.pid} still running: preserve it; no automatic termination or target call')
 log.close();rows=[json.loads(s)for s in (run/(operation+'-publisher.log')).read_text().splitlines()if s.startswith('{')]
 need(rows,'No publisher result');last=rows[-1];write(run/(operation+'-publisher-result.json'),{'exit':child.returncode,'publisher':last})
 need(child.returncode==0 and last['detached'] and not last['uncertain'],'Publisher did not finish cleanly')
 need(last['status']==('INSTALLED_HUMAN_RULES' if operation=='install' else 'RESTORED'),'Unexpected publication state')
 return last

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--local-smoke',action='store_true');args=ap.parse_args()
 reader=BattleObserver();api=None
 try:
  b,root,world,snap,forces,settings=native_data(reader);birth=process_birth(reader)
  need(sha(DLL)==DLL_SHA and sha(PUBLISHER)==PUB_SHA,'Candidate binary hashes differ')
  need(sha(P/'human_rules_activation_publish_handoff.json')==HANDOFF_SHA,'Publisher evidence differs')
  if not args.local_smoke:
   print(json.dumps({'result':'PASS_READ_ONLY_PREFLIGHT','pid':reader.pid,'birth':birth,'settings':settings,'forces':forces,'game_writes':0},ensure_ascii=False));return
  need(sha(P/'human_rules_activation_publish_independent_review.json')==REVIEW_SHA,'Independent publisher review changed')
  review=json.loads((P/'human_rules_activation_publish_independent_review.json').read_text(encoding='utf8'))
  need(review.get('game_access')is False and review.get('handoff_sha256')==HANDOFF_SHA and review.get('production_binary_sha256')==PUB_SHA,'Need matching independent publisher review')
  run=P/'human_rules_activation_live_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
  claim=P/f'human_rules_activation_live_{reader.pid}_{birth}_once.json'
  write(claim,{'run':str(run),'pid':reader.pid,'birth':birth,'automatic_retry':False,'coordinator_sha256':sha(Path(__file__))})
  event(run,'starting',pid=reader.pid,local_diagnostic_peers=2,real_guest_game=False)
  manifest={'profile':{'protocol':PROTOCOL,'game_sha256':GAME_SHA,'adapter_contract':'research-no-native-room-adapter.v1','checkpoint_sha256':SOURCE_SHA,'rules_sha256':digest(settings)},'forces':forces,'source':{'mode':'local-native-rule-smoke','pid':reader.pid}}
  room=Room(manifest);cert,key,fp=make_certificate(run/'private-room');api=ProcessAPI(reader)
  with Server(('127.0.0.1',0),room,cert,key)as server:
   server_thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05},daemon=True);server_thread.start()
   clients=[];closed=False;installed=False;uncertain=False;sealed_completed=False;seal=None;exports={};desc=None;copied=None
   try:
    for method,credential in (('host',room.host_token),('join',room.invite)):
     clients.append(Client('127.0.0.1',server.server_address[1],fp,{'method':method,'credential':credential,'profile':manifest['profile']}))
    for client,force in zip(clients,(12,2)):
     for action,extra in (('select_force',{'force_id':force}),('confirm_force',{})):
      state=client.request({'action':'status'})['state'];need(client.request({'action':action,'request_id':secrets.token_hex(16),'expected_revision':state['revision'],**extra})['ok'],'Room faction binding rejected')
    with room.lock:
     c=export_config(room,settings,'A',image=b,root=root,world=world,read=reader.memory.read);require_current(room,settings,c)
     binding=run/'room-config.bin';binding.write_bytes(bytes(c));write(run/'room-binding.json',{'room':room.room_id,'epoch':room.binding_epoch,'settings':settings,'forces':forces,'real_guest_game':False})
     prior=reader.pointer(b+0x12CC4D0);before=known_snapshot(reader,expected_user_hook=prior);write(run/'prepare-before.json',before)
     copied=run/('san14-human-activation-'+run.name+'.dll');shutil.copy2(DLL,copied)
     pe=pefile.PE(str(copied));rvas={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name};pe.close()
     invoke(api,api.load_library_address(),str(copied).encode('utf-16le')+b'\0\0')
     modules=[a for a,p in api.modules()if p==copied];need(len(modules)==1,'Loaded candidate module mismatch');module=modules[0]
     exports={n:module+r for n,r in rvas.items()};write(run/'module.json',module_approval(reader,module,copied,DLL_SHA))
     for name in ('HumanRulesActivationPrepare','HumanRulesActivationSeal','HumanRulesActivationRevoke','HumanRulesActivationReadReport'):
      readable(reader,exports[name],32,allocation=module,execute=True)
     code,_=invoke(api,exports['HumanRulesActivationPrepare'],bytes(c));event(run,'prepared',exit=code);need(code==0,'Prepare rejected; no retry')
     raw=reader.memory.read(exports['HumanRulesActivationDescriptor'],1208)
     seal=struct.pack('<II',1,72)+raw[56:88]+bytes(c.room)+bytes(c.epoch)
     require_current(room,settings,c);code,_=invoke(api,exports['HumanRulesActivationSeal'],seal);need(code==0,'Seal rejected; no retry');sealed_completed=True
     desc=descriptor(reader,exports['HumanRulesActivationDescriptor']);need((desc['pid'],desc['birth'],desc['base'],desc['module'])==(reader.pid,birth,b,module),'Descriptor process mismatch')
     need(reader.memory.read(exports['HumanRulesActivationBinding'],136)==bytes(c),'Immutable native binding mismatch')
     initial=report(api,exports['HumanRulesActivationReadReport']);write(run/'prepared-report.json',initial)
     need(initial['state']==4 and initial['error']==0 and initial['ai']['exits']==0 and initial['income']['entries']==0,'Candidate ran before publication')
     after=known_snapshot(reader,expected_user_hook=prior);write(run/'prepare-after.json',after);need(same_known_data(before,after),'Known data changed during prepare/seal')
     need(all(reader.memory.read(b+rva,len(raw))==raw for rva,_,raw in profiles()),'Sources changed during prepare')
     write(run/'prepared.json',{'result':'PASS_SEALED_NOT_INSTALLED','pid':reader.pid,'birth':birth,'module':module,'exports':exports,'descriptor':desc,'dll':str(copied),'config':str(binding),'review_sha256':sha(P/'human_rules_activation_publish_independent_review.json')})
    event(run,'ready_for_install',run=str(run))
    seen=set();heartbeat=0;fault_reported=False
    while not closed:
     now=time.monotonic()
     if now-heartbeat>5:
      for client in clients:need(client.request({'action':'status'})['ok'],'Local diagnostic peer lost')
      with room.lock:require_current(room,settings,c)
      heartbeat=now
     native_state=struct.unpack('<i',reader.memory.read(exports['HumanRulesActivationState'],4))[0]
     if native_state==6 and not fault_reported:
      event(run,'NATIVE_FAULTED_RESTART_ONLY');fault_reported=True
     for action in ('install','inspect','restore','close'):
      path=run/f'command-{action}.json'
      if action in seen or not path.exists():continue
      need(json.loads(path.read_text())=={'action':action},'Bad local control file');seen.add(action)
      if action in ('install','restore'):
       need((action=='install' and not installed)or(action=='restore' and installed),'Invalid publication order')
       with room.lock:
        require_current(room,settings,c)
        checkpoint=known_snapshot(reader,expected_user_hook=prior);write(run/(action+'-before.json'),checkpoint)
        uncertain=True
        result=publish(run,action,reader,birth,desc,copied,binding)
        installed=action=='install';uncertain=False
        after=known_snapshot(reader,expected_user_hook=prior);write(run/(action+'-after.json'),after)
        need(same_known_data(checkpoint,after),'Known data changed across short publication')
        current=report(api,exports['HumanRulesActivationReadReport']);write(run/(action+'-report.json'),current)
        event(run,action+'_complete',publisher=result,counters=current)
      elif action=='inspect':
       need(not uncertain,'Publisher pending; no remote inspection')
       current=report(api,exports['HumanRulesActivationReadReport']);write(run/'round-report.json',current)
       write(run/'round-state.json',known_snapshot(reader,expected_user_hook=prior));event(run,'round_captured',counters=current)
      else:
       need(not installed and not uncertain,'Restore six sources before closing room')
       need(all(reader.memory.read(b+rva,len(raw))==raw for rva,_,raw in profiles()),'Six sources not restored')
       code,_=invoke(api,exports['HumanRulesActivationRevoke'],seal)
       need(code==0 and struct.unpack('<i',reader.memory.read(exports['HumanRulesActivationState'],4))[0]==6,'Native room retirement not confirmed')
       sealed_completed=False;closed=True;event(run,'closed_with_sources_original',revoke_exit=code)
     time.sleep(.1)
   except BaseException as exc:
    event(run,'OWNER_ERROR',error=repr(exc),installed=installed,uncertain=uncertain)
    if isinstance(exc,RemoteCallError):uncertain=not exc.completed
    # No automatic retry, force-detach, kill, or module unload. Preserve a
    # potentially attached publisher and its event; never call target then.
    if not uncertain and sealed_completed and seal:
     try:
      code,_=invoke(api,exports['HumanRulesActivationRevoke'],seal)
      need(code==0 and struct.unpack('<i',reader.memory.read(exports['HumanRulesActivationState'],4))[0]==6,'Native revoke not confirmed')
      sealed_completed=False;event(run,'fault_revoked',exit=code)
     except BaseException as revoke_error:
      uncertain=True;event(run,'REVOKE_UNCERTAIN',error=repr(revoke_error))
    if installed or uncertain:
     event(run,'RECOVERY_REQUIRED_OWNER_RETAINED')
     while True:time.sleep(1)
    raise
   finally:
    for client in clients:client.close()
    server.shutdown();server_thread.join(2)
 finally:
  if api:api.close()
  reader.close()
if __name__=='__main__':main()
