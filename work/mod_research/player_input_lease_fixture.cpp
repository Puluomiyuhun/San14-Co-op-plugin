#include "player_input_lease_exports.h"
#include "player_input_lease_profile.h"
#include <atomic>
#include <thread>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
namespace w=player_input_lease_wire;
static uintptr_t base=0;static HWND window=nullptr;static HANDLE ready,paused,resume;
static std::atomic<unsigned>audited{0};static std::atomic<bool>bodyIdentity{true};static unsigned checks=0;
static w::Config cfg{};static DWORD initializeResult=99;static std::string mode;
static constexpr UINT Pause=WM_APP+41;
static void need(bool v,const char*s){++checks;if(!v){fprintf(stderr,"FAIL %s\n",s);ExitProcess(3);}}
template<class T>T packet(w::Op op){T v{};v.header={w::Magic,1,sizeof(T),unsigned(op),0};memcpy(v.nonce,cfg.nonce,32);return v;}
static uint64_t birth(){FILETIME b{},e{},k{},u{};need(GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u)!=0,"birth");return (uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;}
void PlayerInputLeaseBeforePublish(HWND){}
static LRESULT Body(uintptr_t engine,HWND h,UINT m,WPARAM wp,LPARAM lp){
 if(engine!=base+0x19055D0)bodyIdentity=false;
 if(m==Pause){SetEvent(paused);WaitForSingleObject(resume,5000);return 0;}
 if(m==WM_KEYDOWN){++audited;return 17;}if(m==WM_TIMER)return 23;if(m==WM_MOUSEWHEEL)return 31;
 if(m==WM_DESTROY)PostQuitMessage(0);return DefWindowProcA(h,m,wp,lp);
}
static DWORD WINAPI windowMain(void*){
 WNDCLASSEXA c{};c.cbSize=sizeof c;c.lpfnWndProc=reinterpret_cast<WNDPROC>(base+0x5122F0);c.hInstance=GetModuleHandleW(nullptr);c.lpszClassName="OwnedInputLeaseFixture";
 if(!RegisterClassExA(&c)){SetEvent(ready);return 1;}window=CreateWindowExA(0,c.lpszClassName,"",0,0,0,0,0,HWND_MESSAGE,nullptr,c.hInstance,nullptr);
 if(!window){SetEvent(ready);return 2;}*reinterpret_cast<uintptr_t*>(base+0x19055D0+0x18)=uintptr_t(window);cfg.window=uintptr_t(window);
 if(mode!="wrong-thread")initializeResult=PlayerInputInitialize(&cfg);SetEvent(ready);MSG m{};while(GetMessageA(&m,nullptr,0,0)>0){TranslateMessage(&m);DispatchMessageA(&m);}return 0;
}
static w::Snapshot snap(){auto s=packet<w::Snapshot>(w::Op::Snapshot);need(PlayerInputSnapshot(&s)==0,"snapshot");return s;}
static bool request(unsigned phase,bool local,uint64_t rev){auto q=packet<w::Request>(w::Op::Request);q.binding=cfg.binding;q.phase=phase;q.localReady=local;q.revision=rev;return PlayerInputRequest(&q)==0;}
static void ack(uint64_t rev){for(unsigned i=0;i<400;++i){auto s=snap();if(s.acknowledged&&s.acknowledgedRevision==rev)return;Sleep(2);}need(false,"actual HWND acknowledgement");}
static w::Lease acquire(uint64_t rev,uint64_t seq){auto q=packet<w::Lease>(w::Op::Acquire);q.binding=cfg.binding;q.revision=rev;q.sequence=seq;return q;}
static void blocked(){auto n=audited.load();need(SendMessageA(window,WM_KEYDOWN,VK_RETURN,0)==0&&audited.load()==n,"audited key suppressed");}
static void complete(w::Lease q,bool expected){q.header.op=unsigned(w::Op::Complete);q.header.result=0;need((PlayerInputComplete(&q)==0)==expected,"complete exact lease");}
int main(int argc,char**argv){need(argc==3,"arguments");mode=argv[1];base=uintptr_t(VirtualAlloc(nullptr,0x2300000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(base!=0,"owned memory");
 memcpy(reinterpret_cast<void*>(base+0x5122F0),BoundaryWndBytes,sizeof BoundaryWndBytes);unsigned char jump[12]={0x48,0xb8};auto body=uintptr_t(&Body);memcpy(jump+2,&body,8);jump[10]=0xff;jump[11]=0xe0;memcpy(reinterpret_cast<void*>(base+0x510BE0),jump,12);*reinterpret_cast<uintptr_t*>(base+0x123C928)=uintptr_t(&GetWindowLongA);
 DWORD old=0;need(VirtualProtect(reinterpret_cast<void*>(base+0x510000),0x3000,PAGE_EXECUTE_READ,&old)!=0,"RX source");FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base),0x2300000);
 cfg=packet<w::Config>(w::Op::Initialize);cfg.nonce[0]=91;cfg.pid=GetCurrentProcessId();cfg.birth=birth();cfg.base=base;cfg.binding.room[0]=1;cfg.binding.attachment[0]=2;cfg.binding.epoch[0]=3;cfg.binding.period=1;cfg.binding.seat=0;
 ready=CreateEventW(nullptr,TRUE,FALSE,nullptr);paused=CreateEventW(nullptr,TRUE,FALSE,nullptr);resume=CreateEventW(nullptr,TRUE,FALSE,nullptr);auto thread=CreateThread(nullptr,0,windowMain,nullptr,0,nullptr);need(thread&&WaitForSingleObject(ready,5000)==WAIT_OBJECT_0&&window,"real HWND thread");
 if(mode=="wrong-thread"){need(PlayerInputInitialize(&cfg)!=0,"initialize must be HWND thread");auto s=snap();need(!s.installed&&!s.initialized&&s.error,"no wrong-thread publication");}
 else {need(initializeResult==0,"initialize on HWND");need(request(0,false,1),"planning request");ack(1);need(SendMessageA(window,WM_KEYDOWN,VK_RETURN,0)==17,"local initially open");
 if(mode=="normal"){
  auto l=acquire(1,1);std::thread first([&]{need(PlayerInputAcquire(&l)==0,"remote control thread acquire");});first.join();blocked();auto s=snap();need(s.held&&s.leaseId==1&&!s.localCommandPolicyOpen&&!s.remoteExecutionPolicyOpen,"lease holds local policy");
  for(unsigned phase=0;phase<=5;++phase)need(!request(phase,phase==0,2),"lease blocks every new revision");need(snap().revision==1,"denied phase not consumed");
  std::thread second([&]{complete(l,true);});second.join();complete(l,false);need(SendMessageA(window,WM_KEYDOWN,VK_RETURN,0)==17,"completion restores local open");
  need(request(0,true,2),"ready request");ack(2);blocked();l=acquire(2,2);need(PlayerInputAcquire(&l)==0,"Ready permits remote");complete(l,true);blocked();
  for(unsigned phase=1;phase<=4;++phase){need(request(phase,false,phase+2),"critical phase request");ack(phase+2);auto q=acquire(phase+2,3);need(PlayerInputAcquire(&q)!=0,"critical phase veto");blocked();}
 }else if(mode=="pending"){
  need(PostMessageA(window,Pause,0,0)&&WaitForSingleObject(paused,5000)==WAIT_OBJECT_0,"paused real callback");need(request(0,true,2),"pending request");auto q=acquire(2,1);need(PlayerInputAcquire(&q)!=0,"unacked request rejects lease");auto s=snap();need(s.pending&&!s.acknowledged&&s.held,"pending held");SetEvent(resume);ack(2);q=acquire(2,1);need(PlayerInputAcquire(&q)==0,"lease after actual ACK");complete(q,true);blocked();
 }else if(mode=="binding"){
  auto q=acquire(1,1);q.binding.epoch[0]^=1;need(PlayerInputAcquire(&q)!=0,"wrong binding");q=acquire(1,1);q.nonce[0]^=1;need(PlayerInputAcquire(&q)!=0,"wrong nonce");q=acquire(2,1);need(PlayerInputAcquire(&q)!=0,"wrong revision");q=acquire(1,2);need(PlayerInputAcquire(&q)!=0,"skipped sequence");q=acquire(1,1);need(PlayerInputAcquire(&q)==0,"first exact lease");auto bad=q;bad.sequence++;complete(bad,false);auto other=acquire(1,2);need(PlayerInputAcquire(&other)!=0,"single active lease");complete(q,true);q=acquire(1,1);need(PlayerInputAcquire(&q)!=0,"old sequence cannot replay");
 }else if(mode=="unknown"){
  auto q=acquire(1,1);need(PlayerInputAcquire(&q)==0,"acquire before unknown");q.header.op=unsigned(w::Op::Unknown);need(PlayerInputUnknown(&q)==0,"unknown latch");auto s=snap();need(s.held&&s.uncertain&&s.leaseId==1&&s.phase==5&&!s.acknowledged,"unknown retains unresolved lease");complete(q,false);need(!request(0,false,2),"terminal cannot reopen");blocked();
 }else need(false,"known case");
 auto s=snap();need(!s.allInputHeld&&!s.osQueueDrained&&!s.nativeReceiptVerified,"coverage not fabricated");need(SendMessageA(window,WM_TIMER,0,0)==23&&SendMessageA(window,WM_MOUSEWHEEL,0,0)==31,"lifecycle and uncovered forwarded");need(bodyIdentity,"archived wrapper engine identity");s=snap();FILE*f=nullptr;need(fopen_s(&f,argv[2],"wb")==0&&f,"raw snapshot file");need(fwrite(&s,1,sizeof s,f)==sizeof s,"raw 328 bytes");fclose(f);
 }
 need(PostMessageA(window,WM_CLOSE,0,0)!=0&&WaitForSingleObject(thread,5000)==WAIT_OBJECT_0,"normal window shutdown");DWORD exitCode=1;need(GetExitCodeThread(thread,&exitCode)&&exitCode==0,"window thread exit zero");CloseHandle(thread);CloseHandle(ready);CloseHandle(paused);CloseHandle(resume);
 printf("{\"result\":\"PASS\",\"case\":\"%s\",\"checks\":%u,\"snapshot_size\":%zu,\"window_exit\":0}\n",mode.c_str(),checks,sizeof(w::Snapshot));return 0;
}
