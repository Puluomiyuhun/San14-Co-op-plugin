"""Generate only the owned MEM_IMAGE fixture; frozen predecessors stay untouched."""
from pathlib import Path
import importlib.util,re
P=Path(__file__).resolve().parent
def module(name,file):
 s=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def once(text,old,new):
 if text.count(old)!=1:raise RuntimeError('transform requires one anchor: '+old[:100])
 return text.replace(old,new,1)
def expand(text):
 def f(m):
  name=m.group(1)
  if name.endswith('.inc') and (P/name).is_file():return expand((P/name).read_text(encoding='utf-8'))
  return m.group(0)
 return re.sub(r'#include "([^"]+)"',f,text)
def fixture_sources():
 old=module('bootstrap_queue_old','b_reload_lifecycle_queue_test.py')
 cpp,asm,machine,ports=old.fixture_sources()
 cpp=expand(cpp);machine=expand(machine);ports=expand(ports)
 cpp=cpp.replace('++failures;printf("FAIL: %s\\n",s);','++failures;printf("FAIL: %s\\n",s);fflush(stdout);ExitProcess(94);')
 cpp='#include "b_reload_bootstrap_queue.h"\n'+cpp
 cpp=once(cpp,'#include "checkpoint_load_input_boundary_fixture_layout.h"','#include "layout.h"')
 cpp=once(cpp,'static tp::Provider provider;', 'static auto& runtime=*new b_reload_bootstrap_queue::Runtime;\nstatic auto& provider=runtime.Provider();') if 'static tp::Provider provider;' in cpp else cpp
 ports=once(ports,'static tp::Provider provider;', 'static auto& runtime=*new b_reload_bootstrap_queue::Runtime;\nstatic auto& provider=runtime.Provider();') if 'static tp::Provider provider;' in ports else ports
 # The first Layout exists before Bootstrap; subsequent layouts bind only new
 # owned world/state objects to the SAME main image. Never copy an image.
 start=cpp.index('    check(layout.initialize(bd::Stage::MenuAfter),')
 end=cpp.index('    base=layout.config.base;',start)
 cpp=cpp[:start]+'    if(generationIndex)check(layout.initialize(bd::Stage::MenuAfter),"new owned world on retained main PE");\n'+cpp[end:]
 cpp=cpp.replace('pending=base+0x1000','pending=alloc(4096)')
 cpp=once(cpp,'g.owner_module=uintptr_t(GetModuleHandleW(nullptr));','HMODULE actualOwner=nullptr;check(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(&gd::Context::SessionGuard),&actualOwner),"actual retained DLL module");g.owner_module=uintptr_t(actualOwner);')
 cpp=once(cpp,'    prepareNativeMachine();','    check(base==uintptr_t(GetModuleHandleW(nullptr)),"same prepared primary PE");')
 cpp=once(cpp,'        generationIndex=i;currentSession=new ns::Session;currentLayout=new checkpoint_load_input_boundary_fixture::Layout;', '        generationIndex=i;currentSession=new ns::Session;if(i)currentLayout=new checkpoint_load_input_boundary_fixture::Layout;')
 cpp=once(cpp,'check(provider.Register(pcfg)&&provider.OpenWindow(generationIndex+2),"retained native-source bank and observation window");','if(!generationIndex){check(!runtime.OpenFirst(pcfg),"no registration before actual cold pool");auto*other=new b_reload_bootstrap_queue::Runtime;check(!other->OpenFirst(pcfg),"uninitialized different Runtime rejected");check(!runtime.OpenNext(pcfg),"no next generation before completed gate binding");}lifecyclePrepare();if(generationIndex){auto wrong=pcfg;wrong.base+=0x1000;check(!runtime.OpenNext(wrong),"other primary image cannot consume next gate");}else{auto*other=new b_reload_bootstrap_queue::Runtime;check(!other->OpenFirst(pcfg),"other Runtime rejected with actual pool already ready");}check(generationIndex?runtime.OpenNext(pcfg):runtime.OpenFirst(pcfg),"same Bootstrap Provider with gated next registration");check(generationIndex?!runtime.OpenNext(pcfg):!runtime.OpenFirst(pcfg),"already-consumed registration refuses duplicate");')
 cpp=once(cpp,'    }\n\n    lifecycleQueueFinish();','        if(!i)check(runtime.BindCompleted(2,*currentSession,admissionBundle->controller),"retain actual first Session/Input completion sources");\n    }\n\n    lifecycleQueueFinish();')
 # The deliberate source corruption from the isolated test cannot touch an
 # already-installed global entry. Normal source checks remain unchanged.
 start=cpp.index('    if(!generationIndex){DWORD protect=0;check(VirtualProtect')
 end=cpp.index('        check(activationRouter.Initialize(base)',start)
 cpp=cpp[:start]+'    if(!generationIndex){\n'+cpp[end:]
 # Source pages are prepared before the suspended host is resumed. Thereafter
 # each generation merely checks all shared anchors, never rewrites them.
 pattern=r'for\(const auto&a:CheckpointLiveSessionAnchors\)\{.*?\}\n'
 cpp,n=re.subn(pattern,'for(const auto&a:CheckpointLiveSessionAnchors)check(!memcmp(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size),"retained live-session anchor");\n',cpp,count=1);assert n==1
 pattern=r'for\(const auto& anchor:CheckpointNativeQueueAnchors\)\{.*?\}\n'
 cpp,n=re.subn(pattern,'for(const auto& anchor:CheckpointNativeQueueAnchors)check(!memcmp(reinterpret_cast<void*>(base+anchor.rva),anchor.bytes,anchor.size),"retained native queue anchor");\n',cpp,count=1);assert n==1
 anchor='printf("UNHANDLED code='
 start=cpp.index(anchor)
 cpp=cpp[:start]+'{auto c=*e->ContextRecord;printf("REG rcx=%llx rdx=%llx r8=%llx rbx=%llx rdi=%llx\\n",c.Rcx,c.Rdx,c.R8,c.Rbx,c.Rdi);for(unsigned i=0;i<8&&c.Rip;++i){DWORD64 b=0;auto*f=RtlLookupFunctionEntry(c.Rip,&b,nullptr);printf("FRAME %u rip=%llx base=%llx rva=%llx\\n",i,c.Rip,b,c.Rip-b);if(f){void*data=nullptr;DWORD64 frame=0;RtlVirtualUnwind(UNW_FLAG_NHANDLER,b,c.Rip,f,&c,&data,&frame,nullptr);}else {c.Rip=at<uintptr_t>(c.Rsp);c.Rsp+=8;}}}\n' +cpp[start:]
 cpp=once(cpp,'check(r.request.menuObserved&&menuBodies==1,"first native Menu Update paired");','if(!r.request.menuObserved||menuBodies!=1){gd::Report z{};runtimeGuards->context.Snapshot(z);printf("MENU details bodies=%u session=%ld request=%s boundary=%u guard_first=%u guard_last=%u\\n",menuBodies,r.error,r.request.stage,unsigned(r.request.boundary.error),unsigned(z.first_error),unsigned(z.last_error));}check(r.request.menuObserved&&menuBodies==1,"first native Menu Update paired");')
 cpp=once(cpp,'static void restoreMenuUiDouble(){auto&b=*admissionBundle;','static void restoreMenuUiDouble(){put<DWORD>(base+0x19E7510+0x13C,0);put<DWORD>(base+0x1A38EC8+0x28,1);auto&b=*admissionBundle;')
 cpp=once(cpp,'int wmain(int argc,wchar_t**argv)','static int queueMain(int argc,wchar_t**argv)')
 cpp+='\n#include "b_reload_bootstrap_queue_owned.inc"\n'
 # No resetting persistent queue/helper code between generations.
 machine=once(machine,'static void prepareNativeMachine(){','static void prepareNativeMachine(){')
 machine=machine.replace('put<uintptr_t>(base+0x123C328,uintptr_t(&nativeSyncDouble));if(!generationIndex)put<uintptr_t>(base+0x123C0D8,uintptr_t(&nativeSyncDouble));','put<uintptr_t>(base+0x123C328,uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"EnterCriticalSection")));put<uintptr_t>(base+0x123C0D8,uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"LeaveCriticalSection")));')
 machine=once(machine,'put<uintptr_t>(base+0x2025F50,alloc(4096));','put<uintptr_t>(base+0x2025F50,alloc(4096));InitializeCriticalSection(reinterpret_cast<CRITICAL_SECTION*>(at<uintptr_t>(base+0x2025F50)+0x90));')
 machine=once(machine,'put<uintptr_t>(base+0x2025268,alloc(4096));','put<uintptr_t>(base+0x2025268,alloc(4096));InitializeCriticalSection(reinterpret_cast<CRITICAL_SECTION*>(at<uintptr_t>(base+0x2025268)+0x10));')
 machine=once(machine,'put<uintptr_t>(control+8,alloc(4096));','put<uintptr_t>(control+8,alloc(4096));InitializeCriticalSection(reinterpret_cast<CRITICAL_SECTION*>(at<uintptr_t>(control+8)+0x10));')
 # Frozen fixture prepares Root code + unwind; remove its independent bridge
 # publication and fake critical sections. Bootstrap owns the only activation.
 start=ports.index('static void rootPrepareMachine(){');end=ports.index('static void rootProbe(',start)
 body=ports[start:end];cut=body.index(' put<uintptr_t>(base+0x123C1D8,')
 body=body[:cut]+'}\n'
 ports=ports[:start]+body+ports[end:]
 start=ports.index('static void lifecyclePrepare(){');end=ports.index('static std::uint64_t lifecycleBusiness',start)
 ports=ports[:start]+'''static void lifecyclePrepare(){if(lifecyclePrepared)return;lifecyclePrepared=true;
 b_reload_bootstrap::Report b{};b_reload_bootstrap::Snapshot(b);boundRequire(b.armed&&b.attempts==1&&!b.uncertain,"actual Bootstrap armed once before constructor");
 reinterpret_cast<void(*)(uintptr_t)>(base+0x1447B2)(base+0x1A24DA0);
 boundRequire(lifecycleConstructed==4,"same primary image created four workers once");}
'''+ports[end:]
 ports=once(ports,'t.ready=CreateEventW(nullptr,FALSE,FALSE,nullptr);t.done=CreateEventW', 'InitializeCriticalSection(reinterpret_cast<CRITICAL_SECTION*>(t.object+0x110));t.ready=CreateEventW(nullptr,FALSE,FALSE,nullptr);t.done=CreateEventW')
 start=ports.index(' // The startup constructor double has finished');end=ports.index(' aq::Report r{};life::Report s{};',start)
 ports=ports[:start]+ports[end:]
 # Keep every real critical section alive until all own threads finish.
 ports=ports.replace('static auto& provider=runtime.Provider();','static auto& provider=runtime.Provider();\nstatic std::vector<CRITICAL_SECTION*> ownedCompletionLocks;static SRWLOCK ownedLockRegistry=SRWLOCK_INIT;static unsigned ownedDummyLocks=0;static void ownedInitializeCS(uintptr_t p,bool dummy=false){auto*cs=reinterpret_cast<CRITICAL_SECTION*>(p);InitializeCriticalSection(cs);AcquireSRWLockExclusive(&ownedLockRegistry);ownedCompletionLocks.push_back(cs);ownedDummyLocks+=unsigned(dummy);ReleaseSRWLockExclusive(&ownedLockRegistry);}')
 for obj,which in [('machine','at<uintptr_t>(base+0x2025F50)+0x90'),('machine','at<uintptr_t>(base+0x2025268)+0x10'),('machine','at<uintptr_t>(control+8)+0x10'),('ports','t.object+0x110')]:
  value=machine if obj=='machine' else ports
  marker='InitializeCriticalSection(reinterpret_cast<CRITICAL_SECTION*>('+which+'));'
  value=once(value,marker,'ownedInitializeCS('+which+');')
  if obj=='machine':machine=value
  else:ports=value
 cpp=once(cpp,'put<uintptr_t>(dummy+0x10,dummy+0x100);','put<uintptr_t>(dummy+0x10,dummy+0x100);ownedInitializeCS(dummy+0x110,true);')
 ports=ports.replace('put<uintptr_t>(dummy+0x10,dummy+0x100);','put<uintptr_t>(dummy+0x10,dummy+0x100);ownedInitializeCS(dummy+0x110,true);').replace('put<uintptr_t>(worker+0x10,worker+0x100);','put<uintptr_t>(worker+0x10,worker+0x100);ownedInitializeCS(worker+0x110,true);')
 ports=once(ports,' lifecycleStopWorkers();\n aq::Report r{};life::Report s{};', ' lifecycleStopWorkers();\n for(unsigned i=0;i<4;++i){DWORD code=99;check(GetExitCodeThread(lifecycleThreads[i],&code)&&!code,"retained workers returned zero");}\n for(auto*cs:ownedCompletionLocks){check(cs->RecursionCount==0&&TryEnterCriticalSection(cs),"every actual system critical section balanced");LeaveCriticalSection(cs);DeleteCriticalSection(cs);}\n check(ownedCompletionLocks.size()==12+ownedDummyLocks&&ownedDummyLocks>0,"twelve real task locks plus all owned skipped-state locks");\n aq::Report r{};life::Report s{};')
 # Expand body included in generated cpp was separately emitted by ancestors.
 alltext=cpp+ports+machine
 # All small-offset unwind data moves out of the host's real PE/CRT region.
 slots=sorted(set(re.findall(r'base\+(0x[89ABab][0-9A-Fa-f]0)\b',alltext)))
 for slot in slots:
  replacement=hex(0x2300000+int(slot,16))
  cpp=cpp.replace('base+'+slot,'base+'+replacement);ports=ports.replace('base+'+slot,'base+'+replacement);machine=machine.replace('base+'+slot,'base+'+replacement)
  cpp=re.sub(r'(?<=[,{])'+re.escape(slot)+r'(?=})',replacement,cpp);ports=re.sub(r'(?<=[,{])'+re.escape(slot)+r'(?=})',replacement,ports);machine=re.sub(r'(?<=[,{])'+re.escape(slot)+r'(?=})',replacement,machine)
 # Every declared table is part of the host's static exception directory.
 tables={}
 for txt in (cpp,ports,machine):
  for a,b,c in re.findall(r'\{(0x[0-9A-Fa-f]+),(0x[0-9A-Fa-f]+(?:\+10\+sizeof tail)?),(0x[0-9A-Fa-f]+)\}',txt):
   av=int(a,16);bv=int(b.split('+')[0],16)+(33 if '+' in b else 0);cv=int(c,16)
   if 0x2300000<=cv<0x2310000:tables[av]=(av,bv,cv)
 tables[0x1447B2]=(0x1447B2,0x1447C0,0x2300C40);tables[0x509580]=(0x509580,0x509639,0x2300C00)
 unwind='option dotname\n.pdata SEGMENT READONLY ALIGN(4)\n'+''.join(' DD '+','.join('0%Xh'%v for v in x)+'\n' for x in sorted(tables.values()))+'.pdata ENDS\nEND\n'
 original='static bool parentAddFunctions(PRUNTIME_FUNCTION table,DWORD count,DWORD64 image){for(DWORD i=0;i<count;++i)if(!RtlAddFunctionTable(table+i,1,image))return false;return true;}'
 new='static bool parentAddFunctions(PRUNTIME_FUNCTION table,DWORD count,DWORD64 image){for(DWORD i=0;i<count;++i){DWORD64 b=0;auto*f=RtlLookupFunctionEntry(image+table[i].BeginAddress,&b,nullptr);if(!f||b!=image||memcmp(f,table+i,sizeof *f))return false;}return true;}'
 ports=once(ports,original,new)
 # The parent lookup assertion must follow the remapped static unwind RVA.
 ports=ports.replace('entry->UnwindData==0xA00','entry->UnwindData==0x2300A00')
 layout=(P/'checkpoint_load_input_boundary_fixture_layout.h').read_text(encoding='utf-8')
 layout=layout.replace('if(image)VirtualFree(image,0,MEM_RELEASE);','')
 layout=layout.replace('image=VirtualAlloc(nullptr,0x2200000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);','image=GetModuleHandleW(nullptr);')
 # Source vtable pages carry retained publication only at other offsets.
 layout=layout.replace('put<std::uintptr_t>(config.base+0x12F2440+0x10,config.base+0x50B730);','if(!get<std::uintptr_t>(config.base+0x12F2440+0x10))put<std::uintptr_t>(config.base+0x12F2440+0x10,config.base+0x50B730);')
 for name in ('rootSync','rootSetEvent','rootBefore','rootAfter','rootFinally'):
  ports=re.sub(r'static ([^\n{]*\b'+name+r'\()',r'[[maybe_unused]] static \1',ports)
 machine=machine.replace('static void nativeSyncDouble','[[maybe_unused]] static void nativeSyncDouble')
 return cpp,asm,machine,ports,layout,unwind
