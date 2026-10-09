// Original Owner/Gate/Controller/Driver implementations are linked. Native
// business, storage/world and trusted parent schedule remain owned doubles.
#include "planning_checkpoint_save.h"
#include "planning_period_base_fixture.inc"
#include "a_save_dispatch_host.h"
#include "a_save_parent_adapter.h"
#include <functional>
#include "a_save_dispatch_ipc.h"
#include <thread>
namespace ip=a_save_dispatch_ipc;namespace mb=a_save_dispatch_mailbox;namespace dh=a_save_dispatch_host;
static void need(bool ok,const char*why){if(!ok){printf("FAIL %s\n",why);fflush(stdout);ExitProcess(90);}}
static bool permit(void*,const fs::Request&q,const unsigned char*)noexcept{return q.generation>=1&&q.generation<=2&&q.period==q.generation;}
static void executionStop(void*p)noexcept{static_cast<mb::Adapter*>(p)->Stop();}
static bool io(HANDLE h,bool write,void*p,DWORD size){auto*buf=static_cast<unsigned char*>(p);DWORD at=0;while(at<size){DWORD n=0;BOOL ok=write?WriteFile(h,buf+at,size-at,&n,nullptr):ReadFile(h,buf+at,size-at,&n,nullptr);if(!ok||!n)return false;at+=n;}return true;}
static ip::Request request(ip::Op op,std::uint64_t seq,unsigned gen=0){ip::Request r{};r.magic=ip::Magic;r.version=ip::Version;r.opcode=unsigned(op);r.sequence=seq;r.secret[0]=0x5A;if(gen){r.binding[0]=static_cast<unsigned char>(gen);r.save.generation=gen;if(op==ip::Op::Submit){r.save.room_epoch=7;r.save.period=gen;r.save.room_id[0]=1;r.save.year=203;r.save.month=8;r.save.day=static_cast<unsigned char>(gen==1?11:21);r.save.force=12;r.save.ruler=666;sprintf_s(r.save.filename,"mp%08x.s14",gen);}}return r;}
static bool response(HANDLE h,const ip::Request&q,ip::Header&head,std::vector<unsigned char>&body){if(!io(h,false,&head,sizeof head))return false;need(head.magic==ip::Magic&&head.version==ip::Version&&head.opcode==q.opcode&&head.sequence==q.sequence&&head.payload_size>=sizeof(ip::Snapshot)&&head.payload_size<20*1024*1024&&!memcmp(head.binding,q.binding,32),"wire response identity");body.resize(head.payload_size);return io(h,false,body.data(),head.payload_size);}
static HANDLE number(const wchar_t*s){return reinterpret_cast<HANDLE>(_wcstoui64(s,nullptr,10));}
static int client(int argc,wchar_t**argv){need(argc==9,"client args");const std::wstring clientMode=argv[2],pipeName=argv[3];const auto parent=wcstoul(argv[4],nullptr,10);HANDLE drop=number(argv[5]),closed=number(argv[6]),finish=number(argv[7]);(void)argv[8];
 auto until=GetTickCount64()+5000;HANDLE pipe=INVALID_HANDLE_VALUE;while(GetTickCount64()<until){pipe=CreateFileW(pipeName.c_str(),GENERIC_READ|GENERIC_WRITE,0,nullptr,OPEN_EXISTING,0,nullptr);if(pipe!=INVALID_HANDLE_VALUE)break;Sleep(5);}need(pipe!=INVALID_HANDLE_VALUE,"child connects actual named pipe");ULONG server=0;need(GetNamedPipeServerProcessId(pipe,&server)&&server==parent,"kernel server PID identity");
 std::uint64_t seq=0;const bool normal=clientMode==L"normal";ip::Header head{};std::vector<unsigned char>body;
 if(normal){for(unsigned gen=1;gen<=2;++gen){auto q=request(ip::Op::Submit,++seq,gen);need(io(pipe,true,&q,sizeof q)&&response(pipe,q,head,body)&&head.status==unsigned(ip::Status::Ok),"real Submit transaction accepted");ip::Snapshot snap{};memcpy(&snap,body.data(),sizeof snap);need(snap.generation==gen&&!snap.stopped&&!snap.owner_error&&!snap.capabilities,"same generation Owner snapshot required by frozen client");
   bool copied=false;for(unsigned retry=0;retry<100&&!copied;++retry){q=request(ip::Op::Copy,++seq,gen);need(io(pipe,true,&q,sizeof q)&&response(pipe,q,head,body),"real Copy transaction");if(head.status==unsigned(ip::Status::NotReady)){Sleep(5);continue;}need(head.status==unsigned(ip::Status::Ok),"Copy status");
    need(body.size()==sizeof(ip::Snapshot)+checkpoint_fresh_save_packet::HeaderBytes+32,"encoded packet exact length");const auto*packet=body.data()+sizeof(ip::Snapshot);need(!memcmp(packet,"S14FSV01",8),"real packet encoder magic");const auto*payload=packet+checkpoint_fresh_save_packet::HeaderBytes;unsigned char hash[32]{};need(payload[0]==(gen==1?11:21)&&native_storage_read::Sha256(payload,32,hash)&&!memcmp(packet+checkpoint_fresh_save_packet::HeaderBytes-32,hash,32),"client verifies actual diagnostic Save bytes and SHA");char output[40]{};sprintf_s(output,"normal-%u.packet",gen);FILE*f=nullptr;need(fopen_s(&f,output,"wb")==0&&f,"owned received packet output");need(fwrite(packet,1,checkpoint_fresh_save_packet::HeaderBytes+32,f)==checkpoint_fresh_save_packet::HeaderBytes+32&&fclose(f)==0,"persist actual wire packet for frozen Python decoder");copied=true;}
   need(copied,"artifact delivered");if(gen==1)need(WaitForSingleObject(drop,5000)==WAIT_OBJECT_0,"actual next period rebind ready");}
  auto q=request(ip::Op::Stop,++seq);need(io(pipe,true,&q,sizeof q)&&response(pipe,q,head,body)&&head.status==unsigned(ip::Status::Ok),"Stop response drains before EOF");
 }else {auto q=request(ip::Op::Submit,++seq,1);need(io(pipe,true,&q,sizeof q),"send pending Submit");if(clientMode.find(L"disconnect")!=std::wstring::npos)need(WaitForSingleObject(drop,5000)==WAIT_OBJECT_0,"await requested pipe-only disconnect");else {const bool replied=response(pipe,q,head,body);need(!replied||head.status!=unsigned(ip::Status::Ok),"shutdown cannot report accepted Save");}}
 CloseHandle(pipe);SetEvent(closed);need(WaitForSingleObject(finish,5000)==WAIT_OBJECT_0,"client remains alive after pipe EOF");return 0;
}

static void completeOwnedSave(){
 put<std::uint64_t>(b+0x19E7310+0x30,0);put<std::uint64_t>(b+0x19E7310+0x10,6);put<uintptr_t>(b+0x210000+40,b+0x340000);
 for(unsigned i=0;i<5;++i){
  fs::Artifact pending{};check(!session->CopyArtifact(saveReport().generation,pending)&&pending.bytes.empty(),"IPC-style Copy poll in actual six-state Save returns NotReady");
  check(dispatch(1,b+0x340000)==0,"actual original Save callback returns through Owner");
 }
 check(get<std::uint64_t>(b+0x19E7310+0x10)==5,"Save double leaves actual planning layout");
 fs::Artifact pending{};check(!session->CopyArtifact(saveReport().generation,pending),"finalized but not returned User remains ordinary NotReady");
 check(dispatch(0,user)==0,"actual original post-save User callback returned");
}


static std::function<void()> ownedParentWork;
static std::uint64_t parentOriginal(std::uint64_t manager,std::uint64_t,std::uint64_t,std::uint64_t){need(manager==b+0x19E7310,"actual parent manager argument");if(ownedParentWork)ownedParentWork();return 0x1234567812345678ULL;}
static void parentLayout(){
 auto*code=reinterpret_cast<unsigned char*>(b+0x13DBF0);memset(code,0x90,0x23);const unsigned char prolog[]={0x48,0x83,0xEC,0x28};memcpy(code,prolog,4);
 const unsigned char call[]={0xe8,0xd2,0xc3,0x3c,0};memcpy(reinterpret_cast<void*>(b+0x13DC09),call,5);const unsigned char tail[]={0x48,0x83,0xC4,0x28,0xC3};memcpy(reinterpret_cast<void*>(b+0x13DC0E),tail,5);
 jump(b+0x509FE0,reinterpret_cast<void*>(&parentOriginal));DWORD old=0;need(VirtualProtect(reinterpret_cast<void*>(b+0x13D000),4096,PAGE_EXECUTE_READ,&old)&&VirtualProtect(reinterpret_cast<void*>(b+0x509000),4096,PAGE_EXECUTE_READ,&old),"owned exact parent source RX");
}
static void parentDispatch(){auto call=reinterpret_cast<CheckpointLoadWorkerEntry>(b+0x13DBF0);need(call(b+0x19E7310,0,0,0)==0x1234567812345678ULL,"bridge preserves full native return");}
int wmain(int argc,wchar_t**argv){if(argc>1&&!wcscmp(argv[1],L"--client"))return client(argc,argv);need(argc==4,"host case folder sha");
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);const std::wstring caseName=argv[1];const bool normal=caseName==L"normal";mode="held-ipc";
 char exeSha[65]{};WideCharToMultiByte(CP_UTF8,0,argv[3],-1,exeSha,65,nullptr,nullptr);
 setup();machinery();reportMachinery();upstreamMachinery();cfg.base=b;cfg.binder=uintptr_t(&binder);cfg.queue=uintptr_t(&queue);cfg.caller=uintptr_t(&FreshDispatchReturn);
 cfg.room_epoch=7;cfg.room_id[0]=1;cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;
 wcscpy_s(cfg.save_directory,argv[2]);wcscpy_s(cfg.intent_directory,argv[2]);storageSetup(exeSha);cfg.storage.exists=endpoint(reinterpret_cast<void*>(&reportExists));storageVtable[0x68/8]=uintptr_t(&reportExists);
 RewardData data;need(session->Initialize(cfg)&&session->Arm(),"actual unique Owner");
 ic.base=b;ic.root=root;ic.world=world;ic.saveOwner=session;ic.binding=cfg.input_binding;ic.sample=inputSample;ic.fixtureGameCaller=uintptr_t(&InputGameReturn);ic.fixtureUiCaller=uintptr_t(&InputUiReturn);
 need(input->Initialize(ic)&&input->PreparedPlan(plan),"actual Gate");publish();need(input->Arm()&&input->Hold(ic.binding,true,1)&&gameDispatch()==0,"initial Game boundary");
 ar::Config rc{};rc.binding=data.binding;rc.sample=RewardData::sample;need(ar::Bind(*session,rc),"reward binding");
 planning_input_interlock::Config pc{};pc.owner=session;pc.gate=input;pc.binding=data.binding;pc.base=b;pc.root=root;pc.world=world;bool duplicate=false;
 (void)duplicate; // Controller initialization is now performed by actual parent BEFORE.
 mb::Mailbox box;mb::Adapter adapter{&box,5000};SRWLOCK producer=SRWLOCK_INIT;
 dh::Host host;parentLayout();a_save_parent_adapter::Adapter parent;
 a_save_parent_adapter::Config parentCfg{pc,&interlock,&box,&host,&producer,1};need(parent.Initialize(parentCfg),"prepare actual parent adapter");a_save_parent_adapter::Plan patch{};need(parent.PreparedPlan(patch),"exact source patch plan");
 DWORD protection=0;need(VirtualProtect(reinterpret_cast<void*>(patch.site),5,PAGE_READWRITE,&protection),"owned publisher");memcpy(reinterpret_cast<void*>(patch.site),patch.after,5);DWORD ignored=0;need(VirtualProtect(reinterpret_cast<void*>(patch.site),5,protection,&ignored)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(patch.site),5)&&parent.Arm(),"owned plan published and armed");
 a_save_parent_adapter::Report beforeParent{};parent.Snapshot(beforeParent);need(!beforeParent.hostInitialized&&!beforeParent.hostThread,"installer does not initialize Controller or guess TID");parentDispatch();parent.Snapshot(beforeParent);need(beforeParent.hostInitialized&&beforeParent.hostThread==GetCurrentThreadId()&&beforeParent.before==1&&beforeParent.after==1&&beforeParent.finally==1,"actual native parent initializes fixed Host thread");
 bool wrongAccepted=true;std::thread wrong([&]{dh::Report rr{};wrongAccepted=host.BeforeFrame()||host.AfterFrame()||host.Snapshot(rr);});wrong.join();need(!wrongAccepted,"wrong thread no Controller execution");
 SECURITY_ATTRIBUTES sa{sizeof sa,nullptr,TRUE};HANDLE drop=CreateEventW(&sa,TRUE,FALSE,nullptr),closed=CreateEventW(&sa,TRUE,FALSE,nullptr),finish=CreateEventW(&sa,TRUE,FALSE,nullptr),shutdown=CreateEventW(nullptr,TRUE,FALSE,nullptr),serverDone=CreateEventW(nullptr,TRUE,FALSE,nullptr);need(drop&&closed&&finish&&shutdown&&serverDone,"owned events");
 wchar_t name[180]{},exe[2048]{},command[4096]{};swprintf_s(name,L"\\\\.\\pipe\\san14-a-save-%016llx%016llx",static_cast<unsigned long long>(GetCurrentProcessId()),GetTickCount64());need(GetModuleFileNameW(nullptr,exe,2048)>0,"owned EXE path");swprintf_s(command,L"\"%s\" --client %s %s %lu %llu %llu %llu owned",exe,caseName.c_str(),name,GetCurrentProcessId(),reinterpret_cast<unsigned long long>(drop),reinterpret_cast<unsigned long long>(closed),reinterpret_cast<unsigned long long>(finish));
 STARTUPINFOW si{};si.cb=sizeof si;PROCESS_INFORMATION child{};need(CreateProcessW(exe,command,nullptr,nullptr,TRUE,CREATE_NO_WINDOW,nullptr,nullptr,&si,&child),"owned actual pipe client");CloseHandle(child.hThread);
 ip::Config c{};c.owner=session;c.pipeName=name;c.clientPid=child.dwProcessId;c.idleTimeoutMs=5000;c.secret[0]=0x5A;c.room_id[0]=1;c.room_epoch=7;c.permit=permit;c.submit=mb::Adapter::SubmitPort;c.copy=mb::Adapter::CopyPort;c.executionContext=&adapter;c.executionStop=executionStop;
 ip::Server server;need(server.Open(c),"real Server same physical Owner");std::thread service([&]{server.Run(shutdown);SetEvent(serverDone);});
 planning_input_interlock::Controller second;auto*current=&interlock;bool rebound=false,triggered=false,writerBlocked=false,writerReleased=false;unsigned nativeBinds=0;ULONGLONG cancelMs=0;
 auto until=GetTickCount64()+12000;
 while(GetTickCount64()<until){dh::Report h{};host.Snapshot(h);mb::Report m{};box.Snapshot(m);
  if(normal&&h.state==dh::State::Complete&&m.count==1&&m.records[0].state==mb::State::Delivered&&!rebound){
   need(current->BeginObservation(1)&&gameDispatch()==0&&rewardDispatch()==0&&current->EndObservation(1),"real clean retire observation");planning_period_owner::Receipt receipt{};
   need(planning_period_owner::Retire(*session,*input,*current,data.binding,receipt),"retire original period");++data.binding.period;++data.binding.epoch;++data.binding.room_input_digest[0];rc.binding=data.binding;put<unsigned char>(world+0x37,21);
   need(planning_period_owner::Rebind(*session,*input,rc,receipt.serial),"real Rebind same physical Owner");pc.binding=data.binding;need(second.Initialize(pc)&&host.BindPeriod(second),"new Controller same Host second period");current=&second;rebound=true;SetEvent(drop);
  }
  ownedParentWork=[&]{
   host.Snapshot(h);
   if(h.state==dh::State::Observing){bool acquired=true;std::thread writer([&]{acquired=TryAcquireSRWLockShared(&producer)!=FALSE;if(acquired)ReleaseSRWLockShared(&producer);});writer.join();need(!acquired,"cooperating other writer blocked during observation");writerBlocked=true;need(!host.BeforeFrame(),"nested parent frame refuses");need(gameDispatch()==0&&rewardDispatch()==0,"actual Game/User bridges and FINALLY");}
   else if(h.state==dh::State::Submitted){need(dispatch(0,user)==0,"actual User AFTER queues Save");++nativeBinds;need(saveReport().binds==1&&saveReport().status==fs::Status::Queued,"actual native Driver bound before optional disconnect");
    if(!normal&&!triggered){triggered=true;auto at=GetTickCount64();SetEvent(drop);need(WaitForSingleObject(closed,2000)==WAIT_OBJECT_0&&WaitForSingleObject(child.hProcess,0)==WAIT_TIMEOUT,"live child EOF");
     do{box.Snapshot(m);if(m.stopped)break;Sleep(1);}while(GetTickCount64()-at<1500);cancelMs=GetTickCount64()-at+1;need(m.stopped&&m.records[0].state==mb::State::Unknown&&cancelMs<1500,"accepted EOF Unknown before native drain");
     dh::Report held{};host.Snapshot(held);need(held.lease&&held.releases==0,"monitor cannot unlock host lease");bool acquired=true;std::thread writer([&]{acquired=TryAcquireSRWLockShared(&producer)!=FALSE;if(acquired)ReleaseSRWLockShared(&producer);});writer.join();need(!acquired,"writer still excluded after remote Stop");
    }
    completeOwnedSave();
   }
  };parentDispatch();ownedParentWork={};
  a_save_parent_adapter::Report parentReport{};parent.Snapshot(parentReport);need(parentReport.error==a_save_parent_adapter::Error::None&&parentReport.before==parentReport.after&&parentReport.after==parentReport.finally&&!parentReport.active,"native parent callbacks all paired");
  host.Snapshot(h);if(h.releases&&!h.lease){bool acquired=false;std::thread writer([&]{acquired=TryAcquireSRWLockShared(&producer)!=FALSE;if(acquired)ReleaseSRWLockShared(&producer);});writer.join();need(acquired&&h.lastReleaseThread==GetCurrentThreadId(),"only host releases completed producer lease");writerReleased=true;}
  if(WaitForSingleObject(serverDone,0)==WAIT_OBJECT_0)break;Sleep(1);
 }
 need(WaitForSingleObject(serverDone,0)==WAIT_OBJECT_0,"server terminated");service.join();SetEvent(finish);need(WaitForSingleObject(child.hProcess,3000)==WAIT_OBJECT_0,"client exits");DWORD code=99;need(GetExitCodeProcess(child.hProcess,&code)&&!code,"client checks");
 dh::Report h{};host.Snapshot(h);mb::Report m{};box.Snapshot(m);ss::Report u{};session->Snapshot(u);ip::Diagnostics d{};server.Inspect(d);
 need(writerBlocked&&writerReleased&&!h.lease&&!h.frame&&!u.active_scopes&&!u.save.active&&u.save.status==fs::Status::Complete&&!failed,"actual Driver completes and host drains");
 if(normal)need(rebound&&h.observations==2&&h.submits==2&&h.copies==2&&h.releases==2&&d.submits==2&&d.copies==2&&u.save.completed_requests==2&&nativeBinds==2,"two real Controller/Owner/IPC generations");
 else need(triggered&&h.submits==1&&h.copies==0&&h.releases==1&&m.records[0].state==mb::State::Unknown&&d.copies==0&&u.save.stop_after_commit&&u.save.completed_requests==1&&!box.Enqueue(request(1),m.records[0].message.binding),"native drain does not deliver or retry Unknown");
 printf("{\"case\":\"%ls\",\"passed\":true,\"observations\":%u,\"submits\":%u,\"copies\":%u,\"releases\":%u,\"cancellation_ms\":%llu,\"actual_parent_adapter\":true,\"actual_owner\":true,\"actual_controller\":true,\"actual_pipe\":true,\"native_business_double\":true,\"game_access\":false}\n",caseName.c_str(),h.observations,h.submits,h.copies,h.releases,cancelMs);
 CloseHandle(child.hProcess);CloseHandle(drop);CloseHandle(closed);CloseHandle(finish);CloseHandle(shutdown);CloseHandle(serverDone);return 0;
}
