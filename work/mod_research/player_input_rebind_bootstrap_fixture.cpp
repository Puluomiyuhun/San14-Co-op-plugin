#include <windows.h>
#define __declspec(x)
#include "player_input_rebind_bootstrap.h"
#undef __declspec
#include "player_input_rebind_bootstrap_profile.h"
#include <atomic>
#include <cstdio>
#include <cstring>
#include <string>
namespace b=player_input_rebind_bootstrap;namespace w=player_input_rebind_wire;
using Function=DWORD(WINAPI*)(void*);
static Function beginCall,snapshotCall,leaseSnapshot,requestCall,acquireCall,completeCall,rebindCall;
static uintptr_t base=0;static HWND window=nullptr;static HANDLE windowReady,pump,resume,peeked;
static DWORD tid=0;static std::string mode;static b::Config cfg{};static unsigned checks=0;static std::atomic<bool>identityOK{true};
static void need(bool v,const char*m){++checks;if(!v){fprintf(stderr,"FAIL %s\n",m);ExitProcess(3);}}
static uint64_t birth(){FILETIME b{},e{},k{},u{};need(GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u)!=0,"birth");return(uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;}
static LRESULT Body(uintptr_t engine,HWND h,UINT m,WPARAM wp,LPARAM lp){if(engine!=base+0x19055D0)identityOK=false;if(m==WM_KEYDOWN)return 17;if(m==WM_TIMER)return 23;if(m==WM_DESTROY)PostQuitMessage(0);return DefWindowProcA(h,m,wp,lp);}
static DWORD WINAPI windowMain(void*){
 WNDCLASSEXA c{};c.cbSize=sizeof c;c.lpfnWndProc=reinterpret_cast<WNDPROC>(base+0x5122F0);c.hInstance=GetModuleHandleW(nullptr);c.lpszClassName="OwnedInputBootstrapFixture";
 if(!RegisterClassExA(&c)){SetEvent(windowReady);return 1;}window=CreateWindowExA(0,c.lpszClassName,"",0,0,0,0,0,HWND_MESSAGE,nullptr,c.hInstance,nullptr);if(!window){SetEvent(windowReady);return 2;}
 *reinterpret_cast<uintptr_t*>(base+0x19055D0+0x18)=uintptr_t(window);SetEvent(windowReady);WaitForSingleObject(pump,5000);
 if(mode=="peek"){MSG m{};const auto msg=RegisterWindowMessageA("San14.Coop.PlayerInputRebind.Bootstrap.v1");PeekMessageA(&m,window,msg,msg,PM_NOREMOVE);SetEvent(peeked);WaitForSingleObject(resume,5000);}
 if(mode=="foreign"){MSG m{};GetMessageA(&m,window,RegisterWindowMessageA("San14.Coop.PlayerInputRebind.Bootstrap.v1"),RegisterWindowMessageA("San14.Coop.PlayerInputRebind.Bootstrap.v1"));DispatchMessageA(&m);SetEvent(peeked);WaitForSingleObject(resume,5000);}
 MSG m{};while(GetMessageA(&m,nullptr,0,0)>0){TranslateMessage(&m);DispatchMessageA(&m);}return 0;
}
static b::Report snapshot(){b::Report r{};r.header={b::Magic,1,sizeof r,unsigned(b::Op::Snapshot),0};memcpy(r.nonce,cfg.input.nonce,32);need(snapshotCall(&r)==0,"bootstrap snapshot");return r;}
static b::Report awaitResult(){for(unsigned i=0;i<1500;++i){auto r=snapshot();if((r.state==3||r.state==4||r.state==5)&&!r.callbackActive&&!r.hookInstalled)return r;Sleep(2);}need(false,"bounded terminal report");return {};}
template<class T>static T packet(w::Op op){T v{};v.header={w::Magic,1,sizeof v,unsigned(op),0};memcpy(v.nonce,cfg.input.nonce,32);return v;}
static void write(const char*path,const void*data,size_t size){FILE*f=nullptr;need(fopen_s(&f,path,"wb")==0&&f,"evidence file");need(fwrite(data,1,size,f)==size,"evidence bytes");fclose(f);}
int main(int argc,char**argv){need(argc==4,"args");mode=argv[1];auto module=LoadLibraryA(argv[2]);need(module!=nullptr,"actual DLL load");
 beginCall=Function(GetProcAddress(module,"PlayerInputBootstrapBegin"));snapshotCall=Function(GetProcAddress(module,"PlayerInputBootstrapSnapshot"));leaseSnapshot=Function(GetProcAddress(module,"PlayerInputSnapshot"));requestCall=Function(GetProcAddress(module,"PlayerInputRequest"));acquireCall=Function(GetProcAddress(module,"PlayerInputAcquire"));completeCall=Function(GetProcAddress(module,"PlayerInputComplete"));rebindCall=Function(GetProcAddress(module,"PlayerInputRebind"));need(rebindCall&&beginCall&&snapshotCall&&leaseSnapshot&&requestCall&&acquireCall&&completeCall,"real typed exports");
 base=uintptr_t(VirtualAlloc(nullptr,0x2300000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(base!=0,"owned native memory");memcpy(reinterpret_cast<void*>(base+0x5122F0),BoundaryWndBytes,sizeof BoundaryWndBytes);unsigned char jump[12]={0x48,0xb8};auto body=uintptr_t(&Body);memcpy(jump+2,&body,8);jump[10]=0xff;jump[11]=0xe0;memcpy(reinterpret_cast<void*>(base+0x510BE0),jump,12);*reinterpret_cast<uintptr_t*>(base+0x123C928)=uintptr_t(&GetWindowLongA);
 if(mode=="source")*reinterpret_cast<unsigned char*>(base+0x5122F0+0x77)^=1;
 DWORD old=0;need(VirtualProtect(reinterpret_cast<void*>(base+0x510000),0x3000,PAGE_EXECUTE_READ,&old)!=0,"owned source RX");FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base),0x2300000);
 windowReady=CreateEventW(nullptr,TRUE,FALSE,nullptr);pump=CreateEventW(nullptr,TRUE,FALSE,nullptr);resume=CreateEventW(nullptr,TRUE,FALSE,nullptr);peeked=CreateEventW(nullptr,TRUE,FALSE,nullptr);
 auto thread=CreateThread(nullptr,0,windowMain,nullptr,0,&tid);need(thread&&WaitForSingleObject(windowReady,5000)==WAIT_OBJECT_0&&window,"real target window");
 cfg.header={b::Magic,1,sizeof cfg,unsigned(b::Op::Begin),0};auto&i=cfg.input;i.header={w::Magic,1,sizeof i,unsigned(w::Op::Initialize),0};i.nonce[0]=71;i.pid=GetCurrentProcessId();i.birth=birth();i.base=base;i.window=uintptr_t(window);i.binding.room[0]=1;i.binding.attachment[0]=2;i.binding.epoch[0]=3;i.binding.period=1;cfg.windowThread=tid;cfg.timeoutMs=1000;
 if(mode=="birth")++i.birth;if(mode=="thread")++cfg.windowThread;if(mode=="late-timeout"||mode=="executing-timeout")cfg.timeoutMs=100;
 if(mode=="executing-timeout")SetEnvironmentVariableA("OWNED_INPUT_BOOTSTRAP_DELAY","1");
 if(mode=="foreign")need(PostMessageA(window,RegisterWindowMessageA("San14.Coop.PlayerInputRebind.Bootstrap.v1"),999,LPARAM(i.birth))!=0,"foreign nonce queued first");
 const auto status=beginCall(&cfg);const bool refusal=mode=="source"||mode=="birth"||mode=="thread";need((status!=0)==refusal,"Begin acceptance");
 b::Report r{};
 if(refusal){
  // Wrong birth cannot authenticate Snapshot: preserve Begin result, then no writes.
  if(mode!="birth"){r=snapshot();need(r.state==4&&!r.initializeAttempted&&!r.hookInstalled,"preflight failure before installation");}
  need(uintptr_t(GetWindowLongPtrA(window,GWLP_WNDPROC))==base+0x5122F0,"original window untouched");SetEvent(pump);
 }else if(mode=="late-timeout"){
  Sleep(150);r=snapshot();need(r.state==4&&r.error==7&&!r.initializeAttempted&&r.hookRemoved&&!r.hookInstalled&&!r.uncertain,"unclaimed timeout cancels hook");SetEvent(pump);Sleep(30);r=snapshot();need(!r.initializeAttempted&&r.callbackClaims==0&&uintptr_t(GetWindowLongPtrA(window,GWLP_WNDPROC))==base+0x5122F0,"late message cannot initialize");
 }else{
  SetEvent(pump);
  if(mode=="peek"||mode=="foreign"){need(WaitForSingleObject(peeked,5000)==WAIT_OBJECT_0,"real hook observation");r=snapshot();need(r.state==1&&!r.initializeAttempted&&!r.callbackClaims,"peek/foreign message grants no execution");SetEvent(resume);}
  if(mode=="executing-timeout"){for(unsigned n=0;n<1000;++n){r=snapshot();if(r.initializeAttempted)break;Sleep(1);}need(r.initializeAttempted,"actual Initialize entered");Sleep(150);r=snapshot();need(r.state==5&&r.uncertain&&r.initializeAttempted,"executing timeout unknown retained");}
  r=awaitResult();need(r.initializeAttempted&&r.initializeSucceeded&&r.initializeResult==0&&r.initializeThread==tid&&tid!=GetCurrentThreadId(),"Initialize ran on actual HWND thread");need(r.hookRemoved&&!r.hookInstalled&&r.modulePinned&&r.module==uintptr_t(module)&&r.callbackClaims==1&&!r.callbackActive,"hook retired module retained");
  need((r.state==5&&r.uncertain)==(mode=="executing-timeout"),"timeout cannot be overwritten by late success");
  if(mode!="executing-timeout"){
   need(r.state==3&&!r.error&&!r.uncertain,"known successful bootstrap");auto q=packet<w::Request>(w::Op::Request);q.binding=i.binding;q.phase=0;q.localReady=1;q.revision=1;need(requestCall(&q)==0,"original owner request");
   w::Snapshot s{};for(unsigned n=0;n<1000;++n){s=packet<w::Snapshot>(w::Op::Snapshot);need(leaseSnapshot(&s)==0,"original typed snapshot");if(s.acknowledged)break;Sleep(1);}need(s.acknowledged&&s.windowThread==tid,"actual policy ACK after bootstrap");auto lease=packet<w::Lease>(w::Op::Acquire);lease.binding=i.binding;lease.revision=1;lease.sequence=1;need(acquireCall(&lease)==0,"Ready remote lease");need(SendMessageA(window,WM_KEYDOWN,VK_RETURN,0)==0,"actual local input suppressed");lease.header.op=unsigned(w::Op::Complete);need(completeCall(&lease)==0,"lease complete");
   q=packet<w::Request>(w::Op::Request);q.binding=i.binding;q.phase=2;q.revision=2;need(requestCall(&q)==0,"LOAD before rebind");
   for(unsigned n=0;n<1000;++n){s=packet<w::Snapshot>(w::Op::Snapshot);need(leaseSnapshot(&s)==0,"LOAD snapshot");if(s.acknowledged&&s.acknowledgedRevision==2)break;Sleep(1);}need(s.acknowledgedRevision==2&&s.held,"LOAD ACK");
   auto rb=packet<w::Rebind>(w::Op::Rebind);rb.binding=i.binding;rb.nextBinding=i.binding;rb.nextBinding.period++;rb.nextBinding.epoch[0]++;rb.nextBinding.attachment[0]++;rb.revision=3;need(rebindCall(&rb)==0,"same bootstrapped owner rebind");
   for(unsigned n=0;n<1000;++n){s=packet<w::Snapshot>(w::Op::Snapshot);need(leaseSnapshot(&s)==0,"rebind snapshot");if(s.acknowledged&&s.acknowledgedRevision==3)break;Sleep(1);}need(s.acknowledgedRevision==3&&s.held&&s.phase==2&&!memcmp(&s.binding,&rb.nextBinding,sizeof s.binding)&&s.publicationWrites==1,"retained owner rebind ACK");

  }
 }
 cfg.header.result=0;need(beginCall(&cfg)!=0,"once cannot retry");if(mode!="birth"){r=snapshot();need(r.attempts==1,"one bootstrap attempt");write(argv[3],&r,sizeof r);}
 need(SendMessageA(window,WM_TIMER,0,0)==23,"original lifecycle available");need(identityOK,"archived wrapper body identity");need(PostMessageA(window,WM_CLOSE,0,0)!=0&&WaitForSingleObject(thread,5000)==WAIT_OBJECT_0,"normal owned window shutdown");DWORD code=1;need(GetExitCodeThread(thread,&code)&&!code,"thread exit0");CloseHandle(thread);CloseHandle(windowReady);CloseHandle(pump);CloseHandle(resume);CloseHandle(peeked);
 printf("{\"result\":\"PASS\",\"case\":\"%s\",\"checks\":%u,\"window_exit\":0,\"report_size\":%zu}\n",mode.c_str(),checks,sizeof(b::Report));return 0;
}
