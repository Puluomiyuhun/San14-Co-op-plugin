// Thread-directed one-shot installation. No engine calls or external callbacks.
#include "player_input_rebind_bootstrap.h"
#include "native_storage_read_core.h"
#include <cstring>
namespace {
namespace b=player_input_rebind_bootstrap;namespace w=player_input_rebind_wire;
SRWLOCK mutex=SRWLOCK_INIT;b::Config config{};b::Report report{};HHOOK hook=nullptr;bool attempted=false,removing=false;
constexpr uintptr_t Wnd=0x5122F0,Body=0x510BE0,Window=0x19055D0+0x18;
const unsigned char WndHash[32]={0xac,0x9f,0x1f,0xc2,0x7b,0x57,0xc6,0x56,0xe8,0xa0,0xcf,0x57,0x11,0xe5,0xa0,0x7f,0x19,0x71,0x68,0x62,0x6d,0x38,0x23,0xbf,0x7f,0x3f,0x12,0xb9,0xf6,0xa6,0xe1,0xd4};
const unsigned char BodyHash[32]={0x81,0xec,0xfc,0x93,0xcc,0x2e,0x74,0x94,0xd5,0x0c,0xf5,0x87,0x8b,0x76,0x6e,0x37,0x96,0x34,0x9a,0x1e,0x9d,0x85,0x16,0xfd,0xe7,0x85,0xc3,0xf8,0xcd,0xfd,0x6c,0xd2};
bool copy(void*d,const void*s,size_t n)noexcept{__try{memcpy(d,s,n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
uint64_t birth()noexcept{FILETIME a{},e{},k{},u{};return GetProcessTimes(GetCurrentProcess(),&a,&e,&k,&u)?(uint64_t(a.dwHighDateTime)<<32)|a.dwLowDateTime:0;}
bool header(const w::Header&h,unsigned size,b::Op op)noexcept{return h.magic==b::Magic&&h.version==1&&h.size==size&&h.op==unsigned(op)&&!h.result;}
bool bytes(const unsigned char*p,size_t n)noexcept{unsigned a=0;for(size_t i=0;i<n;++i)a|=p[i];return a!=0;}
bool identity()noexcept{__try{auto&c=config.input;DWORD pid=0;auto window=HWND(uintptr_t(c.window));return c.pid==GetCurrentProcessId()&&c.birth==birth()&&IsWindow(window)&&!IsWindowUnicode(window)&&GetWindowThreadProcessId(window,&pid)==config.windowThread&&pid==c.pid&&uintptr_t(GetClassLongPtrA(window,GCLP_WNDPROC))==c.base+Wnd&&uintptr_t(GetWindowLongPtrA(window,GWLP_WNDPROC))==c.base+Wnd&&*reinterpret_cast<const uintptr_t*>(uintptr_t(c.base)+Window)==c.window;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool range(uintptr_t base,uintptr_t address,size_t size)noexcept{if(address>UINTPTR_MAX-size)return false;auto end=address+size;while(address<end){MEMORY_BASIC_INFORMATION m{};if(VirtualQuery(reinterpret_cast<void*>(address),&m,sizeof m)!=sizeof m||uintptr_t(m.AllocationBase)!=base||m.State!=MEM_COMMIT||(m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef PLAYER_INPUT_REBIND_BOOTSTRAP_FIXTURE
 if(m.Type!=MEM_IMAGE)return false;
#endif
 auto next=uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=address)return false;address=next;}return true;}
bool source()noexcept{__try{const auto base=uintptr_t(config.input.base);unsigned char hash[32]{};if(!range(base,base+Wnd,0x78)||!range(base,base+Body,0x591)||!native_storage_read::Sha256(reinterpret_cast<void*>(base+Wnd),0x78,hash)||memcmp(hash,WndHash,32))return false;
#ifndef PLAYER_INPUT_REBIND_BOOTSTRAP_FIXTURE
 if(!native_storage_read::Sha256(reinterpret_cast<void*>(base+Body),0x591,hash)||memcmp(hash,BodyHash,32))return false;
#endif
 return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
void failed(b::Error error,bool unknown=false)noexcept{if(!report.error)report.error=unsigned(error);report.state=unsigned(unknown?b::State::Unknown:b::State::Failed);report.uncertain=report.uncertain||unknown;report.endTick=GetTickCount64();}
// Never hold mutex while UnhookWindowsHookEx executes. An already running
// callback may survive unhook; its active/attempted/result fields stay visible.
void removeHook()noexcept{HHOOK value=nullptr;AcquireSRWLockExclusive(&mutex);if(hook&&!removing){value=hook;hook=nullptr;removing=true;}ReleaseSRWLockExclusive(&mutex);if(!value)return;const bool ok=UnhookWindowsHookEx(value)!=0;AcquireSRWLockExclusive(&mutex);removing=false;if(ok){report.hookInstalled=0;report.hookRemoved=1;}else failed(b::Error::Unhook,true);ReleaseSRWLockExclusive(&mutex);}
void expire()noexcept{bool remove=false;AcquireSRWLockExclusive(&mutex);if(attempted&&report.deadlineTick&&GetTickCount64()>=report.deadlineTick&&(report.state==unsigned(b::State::Queued)||report.state==unsigned(b::State::Executing))){failed(b::Error::Timeout,report.initializeAttempted!=0||report.state==unsigned(b::State::Executing));remove=true;}ReleaseSRWLockExclusive(&mutex);if(remove)removeHook();}
LRESULT CALLBACK callback(int code,WPARAM wp,LPARAM lp){
 bool claim=false,matched=false;AcquireSRWLockExclusive(&mutex);++report.callbackActive;ReleaseSRWLockExclusive(&mutex);
 __try{
  if(code>=0&&wp==PM_REMOVE){MSG m{};if(copy(&m,reinterpret_cast<void*>(lp),sizeof m)){
   uint64_t token=0;memcpy(&token,config.input.nonce,8);
   AcquireSRWLockExclusive(&mutex);
   if(report.state==unsigned(b::State::Queued)&&m.hwnd==HWND(uintptr_t(config.input.window))&&m.message==report.controlMessage&&uint64_t(m.wParam)==token&&uint64_t(m.lParam)==config.input.birth){
    matched=true;
    if(GetTickCount64()>=report.deadlineTick)failed(b::Error::Timeout);
    else {report.state=unsigned(b::State::Executing);++report.callbackClaims;claim=true;}
   }
   ReleaseSRWLockExclusive(&mutex);
   if(claim){
    const bool id=GetCurrentThreadId()==config.windowThread&&identity();const bool validSource=id&&source();
    if(!id||!validSource){AcquireSRWLockExclusive(&mutex);failed(id?b::Error::Source:b::Error::Identity);ReleaseSRWLockExclusive(&mutex);}
    else {
     bool execute=false;AcquireSRWLockExclusive(&mutex);
     if(report.state==unsigned(b::State::Executing)){report.initializeAttempted=1;report.initializeThread=GetCurrentThreadId();execute=true;}ReleaseSRWLockExclusive(&mutex);
     if(execute){auto input=config.input;const DWORD result=PlayerInputInitialize(&input);AcquireSRWLockExclusive(&mutex);report.initializeResult=result;report.initializeSucceeded=result==0;
      if(report.state==unsigned(b::State::Executing)){if(result)failed(b::Error::Initialize);else {report.state=unsigned(b::State::Complete);report.endTick=GetTickCount64();}}ReleaseSRWLockExclusive(&mutex);}
    }
    removeHook();
   }else if(matched)removeHook();else expire();
  }}
  return CallNextHookEx(nullptr,code,wp,lp);
 }__finally{AcquireSRWLockExclusive(&mutex);--report.callbackActive;++report.callbackFinally;ReleaseSRWLockExclusive(&mutex);}
}
}
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputBootstrapBegin(void*ptr)noexcept{
 b::Config value{};if(!ptr||!copy(&value,ptr,sizeof value)||!header(value.header,sizeof value,b::Op::Begin))return 1;
 AcquireSRWLockExclusive(&mutex);DWORD result=2;
 __try{__try{
  if(attempted)__leave;attempted=true;config=value;report.attempts=1;report.pid=value.input.pid;report.birth=value.input.birth;report.window=value.input.window;report.windowThread=value.windowThread;report.timeoutMs=value.timeoutMs;memcpy(report.nonce,value.input.nonce,32);report.initializeResult=MAXDWORD;
  auto&c=value.input;if(c.header.magic!=w::Magic||c.header.version!=1||c.header.size!=sizeof c||c.header.op!=unsigned(w::Op::Initialize)||c.header.result||!bytes(c.nonce,32)||!bytes(c.binding.room,16)||!bytes(c.binding.attachment,16)||!bytes(c.binding.epoch,16)||!c.binding.period||c.binding.seat>1||!c.base||c.base>UINTPTR_MAX-0x2300000||!value.windowThread||value.timeoutMs<50||value.timeoutMs>5000){failed(b::Error::Config);__leave;}
  if(!identity()){failed(b::Error::Identity);__leave;}if(!source()){failed(b::Error::Source);__leave;}
  HMODULE module=nullptr;if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCSTR>(&callback),&module)){failed(b::Error::Pin);__leave;}report.modulePinned=1;report.module=uintptr_t(module);
  report.controlMessage=RegisterWindowMessageA("San14.Coop.PlayerInputRebind.Bootstrap.v1");if(!report.controlMessage){failed(b::Error::Post);__leave;}
  report.startTick=GetTickCount64();report.deadlineTick=report.startTick+value.timeoutMs;report.state=unsigned(b::State::Queued);
  hook=SetWindowsHookExA(WH_GETMESSAGE,callback,module,value.windowThread);if(!hook){failed(b::Error::Hook);__leave;}report.hookInstalled=1;
  uint64_t token=0;memcpy(&token,c.nonce,8);if(!PostMessageA(HWND(uintptr_t(c.window)),report.controlMessage,WPARAM(token),LPARAM(c.birth))){failed(b::Error::Post);__leave;}result=0;
 }__except(EXCEPTION_EXECUTE_HANDLER){failed(b::Error::Exception,true);result=3;}}
 __finally{ReleaseSRWLockExclusive(&mutex);}if(result)removeHook();value.header.result=result;return copy(ptr,&value,sizeof value)?result:1;
}
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputBootstrapSnapshot(void*ptr)noexcept{
 b::Report value{};if(!ptr||!copy(&value,ptr,sizeof value)||!header(value.header,sizeof value,b::Op::Snapshot))return 1;
 AcquireSRWLockShared(&mutex);const bool valid=attempted&&!memcmp(value.nonce,config.input.nonce,32)&&config.input.pid==GetCurrentProcessId()&&config.input.birth==birth();ReleaseSRWLockShared(&mutex);if(!valid)return 2;
 expire();AcquireSRWLockShared(&mutex);const auto h=value.header;value=report;value.header=h;ReleaseSRWLockShared(&mutex);return copy(ptr,&value,sizeof value)?0:1;
}
