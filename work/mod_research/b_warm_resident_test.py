"""Actual Resident remote loading/control against one owned host; no game process."""
from pathlib import Path
from datetime import datetime
import ctypes as C
from ctypes import wintypes as W
import hashlib,json,os,shutil,subprocess,sys,threading,time
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
sys.path[:0]=[str(P),str(PRIVATE/'python_deps'),str(P.parents[1]/'outputs/san14-link')]
PRIOR=PRIVATE/'b_warm_factory_pair_runs/20261009-181448-912475'
HELPER=PRIVATE/'b_warm_coordinator_build_runs/20261009-181031-457801'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def change(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
class Memory:
 def __init__(self,pid):
  self.k=C.WinDLL('kernel32',use_last_error=True);self.k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];self.k.OpenProcess.restype=W.HANDLE;self.handle=self.k.OpenProcess(0x410,False,pid);assert self.handle
  self.k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];self.k.ReadProcessMemory.restype=W.BOOL
  self.k.CloseHandle.argtypes=[W.HANDLE];self.k.CloseHandle.restype=W.BOOL
 def read(self,address,size):
  buf=C.create_string_buffer(size);got=C.c_size_t();assert self.k.ReadProcessMemory(self.handle,address,buf,size,C.byref(got)) and got.value==size;return buf.raw
 def close(self):self.k.CloseHandle(self.handle)
class Reader:
 def __init__(self,pid):self.pid=pid;self.memory=Memory(pid)
def main():
 run=PRIVATE/'b_warm_resident_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 result=dict(result='FAIL',family='san14.b-warm-resident-owned.v1',game_process_access=False,steam_save_access=False,sources={},private={})
 process=reader=resident=None;lines=[]
 try:
  assert sha(PRIOR/'result.json')=='c13390840e1fbeaf54fde8822add15ef9c44a75967b8c57ea2da2af73247a990'
  prev=json.loads((PRIOR/'result.json').read_text());helper=json.loads((HELPER/'result.json').read_text())
  for origin in (prev,helper):
   for field in ('sources','private','generated','binaries'):
    for n,h in origin.get(field,{}).items():assert sha(n)==h
   result['sources'].update(origin['sources'])
  for q in P.glob('b_warm_resident_*'):
   if q.suffix in ('.py','.cpp','.inc','.h'):result['sources'][str(q)]=sha(q)
  old=PRIOR/'composition'
  for n in ('fixture.cpp','chain_body.inc','chain_authorized.inc','checkpoint_load_input_boundary_fixture_layout.h','guard_test.cpp','guard_test_access.h','host.def','build.cmd'):
   result['private'][str(old/n)]=sha(old/n);shutil.copyfile(old/n,run/n)
  result['private'][helper['production_dll']['path']]=helper['production_dll']['sha256']
  result['private'][str(old/'bank1/svdexccSC03.s14')]=sha(old/'bank1/svdexccSC03.s14')
  result['private'][str(PRIOR/'result.json')]=sha(PRIOR/'result.json');result['private'][str(HELPER/'result.json')]=sha(HELPER/'result.json')
  f=(run/'fixture.cpp').read_text();f=change(f,'#include "chain_authorized.inc"','static b_warm_profile::Profile ownedProfile{};\n#include "chain_authorized.inc"')
  f=change(f,'return b_warm_profile::Capture(p);','ownedProfile=p;return b_warm_profile::Validate(p);')
  a=f.index('extern "C" __declspec(dllexport) int RunBank(');body=f[a:];f=f[:a]
  start=body.index('    if(argc!=6)');cut=body.index('    factoryNeed(!InstallCheckpointCompleteLiveOwner')
  prepare=body[start:cut].replace('const auto&p=b_warm_profile::Get();','const auto&p=ownedProfile;')
  end=body.index('\n    put<uintptr_t>(base+0x19e7310+0x48',cut);frames=body[end:body.rfind('}')]
  declarations='\nstatic b_warm_profile::Config ownedConfig{};static std::wstring ownedStrings[6];static wchar_t*ownedArgs[6]{};\nextern "C" __declspec(dllexport) DWORD WINAPI PrepareResidentOwned(void*directory){\n std::wstring dir=static_cast<wchar_t*>(directory);ownedStrings[0]=L"owned";ownedStrings[1]=L"success-new";ownedStrings[2]=dir+std::wstring(1,wchar_t(92))+L"svdexccSC03.s14";ownedStrings[3]=dir+std::wstring(1,wchar_t(92))+L"request.intent";ownedStrings[4]=dir+std::wstring(1,wchar_t(92))+L"identity.intent";ownedStrings[5]=dir+std::wstring(1,wchar_t(92))+L"owner.report";for(unsigned i=0;i<6;++i)ownedArgs[i]=ownedStrings[i].data();auto argv=ownedArgs;int argc=6;\n'
  f+=declarations+prepare+'ownedConfig.profile=ownedProfile;ownedConfig.owner=c;return 0;}\n'
  f+='extern "C" __declspec(dllexport) DWORD WINAPI GetResidentOwnedConfig(void*p){*static_cast<b_warm_profile::Config*>(p)=ownedConfig;return 0;}\n'
  originals='void* originals[]={reinterpret_cast<void*>(&GuestSessionUserOriginal),reinterpret_cast<void*>(&GuestSessionMenuOriginal),reinterpret_cast<void*>(&GuestSessionGameOriginal),reinterpret_cast<void*>(&GuestSessionUpdateOriginal),reinterpret_cast<void*>(&GuestSessionWorkerOriginal),reinterpret_cast<void*>(&GuestSessionReadOriginal)};'
  f+='extern "C" __declspec(dllexport) DWORD WINAPI RunResidentOwnedFrames(void*){auto&c=ownedConfig.owner;auto argv=ownedArgs;'+originals+frames+'}\n'
  (run/'fixture.cpp').write_text(f)
  for n in ('chain_body.inc','chain_authorized.inc'):
   q=run/n;q.write_text(q.read_text().replace('b_warm_profile::Get()','ownedProfile'))
  cmd=(run/'build.cmd').read_text().replace(str(old),str(run)).replace('b_warm_factory_pair_host.cpp','b_warm_resident_host.cpp')
  (run/'build.cmd').write_text(cmd)
  env=os.environ.copy();env['PYTHONUTF8']='1'
  build=subprocess.run(['cmd','/d','/c',str(run/'build.cmd')],cwd=run,capture_output=True,timeout=180,env=env);(run/'build.log').write_bytes(build.stdout+build.stderr);assert build.returncode==0,('build',build.returncode)
  fixture=run/'environment';fixture.mkdir();shutil.copyfile(old/'bank1/svdexccSC03.s14',fixture/'svdexccSC03.s14')
  process=subprocess.Popen([str(run/'host.exe')],cwd=run,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
  ready=process.stdout.readline();lines.append(ready);assert ready.startswith('OWNED_READY ') and int(ready.split()[1])==process.pid
  def consume():
   for line in process.stdout:lines.append(line)
  thread=threading.Thread(target=consume,daemon=True);thread.start()
  import b_warm_coordinator as co
  import b_warm_profile_contract as wire
  import b_warm_coordinator_contract as hand
  import pefile
  import a_save_runtime_control,checkpoint_complete_live_capture,checkpoint_live_prefetch_start,run_autonomous_pilot,checkpoint_live_prefetch_contract
  reader=Reader(process.pid);resident=co.Resident(reader,run,run/'bank.dll',sha(run/'bank.dll'),Path(helper['production_dll']['path']),helper['production_dll']['sha256'],{},666,5)
  for name,m in list(sys.modules.items()):
   f=getattr(m,'__file__',None)
   if f and Path(f).is_file() and (Path(f).parent==P or Path(f).is_relative_to(P.parents[1]/'outputs') or Path(f).is_relative_to(PRIVATE/'python_deps')):result['sources'].setdefault(str(Path(f)),sha(f))
  bank=resident.open_bank(0);resident.current=bank
  def exports(path,base):
   pe=pefile.PE(str(path));r={x.name.decode():base+x.address for x in pe.DIRECTORY_ENTRY_EXPORT.symbols if x.name};pe.close();return r
  hostbase=next(b for b,p in resident.api.modules() if p.name.lower()=='host.exe');hostexports=exports(run/'host.exe',hostbase);be=exports(bank['path'],bank['module'])
  # These two owned-host functions accept a scalar LPVOID, not a buffer.
  def scalar(address,value):
   tid=W.DWORD();h=resident.api.k.CreateRemoteThread(resident.api.handle,None,0,address,value,0,C.byref(tid));assert h
   try:
    assert resident.api.k.WaitForSingleObject(h,10000)==0;code=W.DWORD();assert resident.api.k.GetExitCodeThread(h,C.byref(code)) and code.value==0
   finally:resident.api.k.CloseHandle(h)
  scalar(hostexports['HostSelectResidentBank'],bank['module']);scalar(hostexports['HostSetResidentSize'],(fixture/'svdexccSC03.s14').stat().st_size)
  assert resident.calls.call(be['PrepareResidentOwned'],str(fixture).encode('utf-16le')+b'\0\0')[0]==0
  code,raw=resident.calls.call(be['GetResidentOwnedConfig'],output_size=C.sizeof(wire.Config));assert code==0;cfg=wire.Config.from_buffer_copy(raw);(run/'config.bin').write_bytes(raw)
  resident.helper=resident._module(resident.helper_dll,resident.helper_sha,run/'coordinator.dll',co.HAND_EXPORTS)
  slots=[cfg.owner.base+x for x in (0x12cc4d0,0x12db4e8,0x12cc9e0,0x12dbd90,0x138e8d0)]+[cfg.owner.storageVtable+8]
  originals=[int.from_bytes(reader.memory.read(s,8),'little') for s in slots]
  resident.hand(hand.Prepare,pid=cfg.owner.pid,birth=cfg.owner.birth,first=bank['module'],slots=slots,originals=originals);resident.prepared=True
  before=resident.hand(hand.Observe);assert before.stage==1 and not before.firstCompleted
  code,_=resident.calls.call(bank['addresses']['InstallBWarmProfileOwner'],bytes(cfg));bank['install_completed']=True
  rc,diagnostic=resident.calls.call(bank['addresses']['GetCheckpointCompleteLiveOwnerReport'],output_size=C.sizeof(wire.old.Report));assert rc==0;(run/'after-install.bin').write_bytes(diagnostic)
  assert code==0,('actual remote typed install',code,wire.old.decode_report(diagnostic)['OwnerError'])
  process.stdin.write('r\n');process.stdin.flush();deadline=time.monotonic()+20
  while not any('OWNED_FRAMES_DONE' in row for row in lines):
   assert process.poll() is None and time.monotonic()<deadline,('frames',process.poll());time.sleep(.05)
  snapshots=[]
  for i in range(2):
   rawset={}
   for name,kind in [('GetCheckpointCompleteLiveOwnerReport',wire.old.Report),('GetBWarmProfileReport',wire.Report),('GetBWarmRetireReport',wire.RetireReport)]:
    code,raw=resident.calls.call(bank['addresses'][name],output_size=C.sizeof(kind));assert code==0;rawset[name]=raw;(run/f'{i}-{name}.bin').write_bytes(raw)
   r=wire.old.decode_report(rawset['GetCheckpointCompleteLiveOwnerReport']);retired=wire.decode(wire.RetireReport,rawset['GetBWarmRetireReport']);profile=wire.decode(wire.Report,rawset['GetBWarmProfileReport'])
   assert r['Installed']==1 and r['SessionState']==13 and r['HooksRestored']==1 and r['GuardChecks']==57 and r['StorageValidations']==72
   assert retired.sealed and retired.restored and not retired.restoreFailed and bytes(profile.profile)==bytes(cfg.profile)
   assert retired.thread==int(ready.split()[2])==r['hardware']['thread'],'actual host-main-thread original callbacks'
   snapshots.append(r)
  assert snapshots[1]['sequence']>snapshots[0]['sequence']
  observed=resident.hand(hand.Observe);assert observed.stage==1 and observed.firstCompleted==1 and observed.secondCompleted==0
  assert all(int.from_bytes(reader.memory.read(s,8),'little')==o for s,o in zip(slots,originals))
  result.update(result='PASS',actual_resident_remote_module_load=True,actual_remote_typed_install=True,actual_host_main_thread_complete_retire=True,actual_helper_dll=True,full_resident_load_method_tested=False,production_completion_classifier_passed=False,complete_banks=1,report_sequence=[r['sequence'] for r in snapshots],guard_checks=57,storage_validations=72,callback_main_thread=int(ready.split()[2]))
 except Exception as exc:result['error']=repr(exc)
 finally:
  if resident:
   if result['result']!='PASS':
    try:resident.abort()
    except Exception as exc:result['abort_error']=repr(exc)
   resident.close()
  if reader:reader.memory.close()
  if process:
   try:
    if process.poll() is None:process.stdin.write('x\n');process.stdin.flush()
    process.wait(timeout=5)
   except Exception:
    process.kill();process.wait();result['owned_child_terminated']=True;result['result']='FAIL'
   result['owned_child_exit']=process.returncode
   if process.returncode!=0:result['result']='FAIL'
   if 'thread' in locals():thread.join(timeout=2)
  (run/'host.log').write_text(''.join(lines))
  for name,m in list(sys.modules.items()):
   f=getattr(m,'__file__',None)
   if f and Path(f).is_file() and Path(f).parent==P:
    if str(Path(f)) not in result['sources']:result['result']='FAIL';result['late_source']=str(f)
  result['inputs_unchanged']=all(sha(n)==h for field in ('sources','private') for n,h in result[field].items())
  if not result['inputs_unchanged']:result['result']='FAIL'
  result['generated']={str(q):sha(q) for q in run.glob('*') if q.suffix in ('.cpp','.h','.inc','.cmd','.def')}
  result['binaries']={str(q):sha(q) for q in run.rglob('*') if q.suffix in ('.exe','.dll','.obj','.lib')}
  result['observations']={str(q):sha(q) for q in run.rglob('*') if q.is_file() and q.suffix in ('.bin','.log','.json') and q.name!='result.json'}
  (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(run/'result.json')}))
 return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
