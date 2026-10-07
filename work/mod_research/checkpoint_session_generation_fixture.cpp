#include "checkpoint_session_generation_owner.h"
#include "checkpoint_load_input_boundary_fixture_layout.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
namespace sg=checkpoint_session_generation;namespace ns=checkpoint_guest_native_session;namespace bd=checkpoint_load_input_boundary;
namespace by=checkpoint_cc_load_observer;namespace lc=checkpoint_cc_load_lifecycle;namespace ti=checkpoint_title_identity_adapter;namespace rq=checkpoint_load_request_commit;
static sg::Owner owner;static checkpoint_load_input_boundary_fixture::Layout layout;
static std::wstring scenario;static std::vector<unsigned char> archive;static void** slots;
static unsigned errors=0,originalCalls[6]{},callbackDuringSwitch=0;static bool throwOriginal=false,rotateInside=false;
static std::uintptr_t pending=0,storage=0;static HANDLE entered=nullptr,releaseOriginal=nullptr;
static void check(bool c,const char*s){if(!c){++errors;std::printf("FAIL %s\n",s);}}
template<class T>static void put(std::uintptr_t p,T x){std::memcpy(reinterpret_cast<void*>(p),&x,sizeof x);}
template<class T>static T at(std::uintptr_t p){return *reinterpret_cast<T*>(p);}
using Invoke=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
using FrameInvoke=void(*)(unsigned,CheckpointPushFrame*);
struct Node {unsigned generation=0,controllers=0,before=0,after=0;bool bindMenu=false;const sg::BankApi*api=nullptr;sg::Description desc{};ns::Config config{};std::wstring request,identity;};
static Node nodes[2];
static constexpr std::uint64_t ReturnValue=0xA1B2C3D445566778ull;
static std::uint64_t userOriginal(std::uint64_t,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    ++originalCalls[0];check(a==1&&b==2&&c==3,"original four args");
    if(rotateInside){rotateInside=false;++callbackDuringSwitch;check(!owner.Activate(1),"in-flight old callback prevents rotation");}
    if(entered){SetEvent(entered);WaitForSingleObject(releaseOriginal,5000);}
    if(throwOriginal)RaiseException(0xE0146701,0,0,nullptr);
    return ReturnValue;
}
static std::uint64_t menuOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t){++originalCalls[1];return ReturnValue;}
static std::uint64_t gameOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t){++originalCalls[2];return ReturnValue;}
static std::uint64_t loadOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t){++originalCalls[3];return ReturnValue;}
static std::uint64_t workerOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t){++originalCalls[4];return ReturnValue;}
static std::int32_t readOriginal(void*,const char*,void*data,std::int32_t amount){++originalCalls[5];if(amount!=std::int32_t(archive.size()))return 0;std::memcpy(data,archive.data(),archive.size());return amount;}
static bool validate(void*,ns::Point){return true;}
static bool requestValidate(void*,rq::Point){return true;}
static bool bytesValidate(void*,by::Point,std::uintptr_t,std::uintptr_t){return true;}
static bool lifeValidate(void*,lc::Point,std::uintptr_t,std::uintptr_t){return true;}
static bool titleValidate(void*,ti::Point,std::uintptr_t,std::uintptr_t,std::uintptr_t){return true;}
static bool storageValidate(void*){return true;}
static bool exists(void*,const char*n){return !std::strcmp(n,by::TargetName);}
static std::int32_t fileSize(void*,const char*){return by::TargetSize;}
static void before(const CheckpointPushFrame*,void* p) noexcept {++static_cast<Node*>(p)->before;}
static void after(const CheckpointPushFrame*,void* p) noexcept {++static_cast<Node*>(p)->after;}
static void control(void*p,ns::Session&s,const CheckpointPushFrame*f){
    auto&n=*static_cast<Node*>(p);++n.controllers;check(&s==n.desc.session,"controller exact bank owner");
    if(n.bindMenu){put<std::uint64_t>(layout.manager+0x30,1);put<DWORD>(pending,0);put<std::uintptr_t>(pending+8,layout.config.menu);
        ns::QueueReceipt r{};r.attempt=n.config.request.boundary.attempt;r.userCall=f->call_id;r.thread=f->thread_id;r.user=layout.config.states[4];r.menu=layout.config.menu;r.nativeQueueReturned=true;
        check(n.api->bindQueuedMenu(&r),"actual Session binds same callback menu");
    }
}
static sg::Identity identity(unsigned i){sg::Identity id{};id.generation=i+1;id.attempt=0x700+i;std::memset(id.attachment,0x63,32);return id;}
static bool setupNode(unsigned i,HMODULE m,const std::wstring& dir,const wchar_t* path){
    auto&n=nodes[i];n.generation=i+1;auto get=reinterpret_cast<sg::GetBankApi>(GetProcAddress(m,"CheckpointSessionGenerationGetApi"));check(get!=nullptr,"bank export");if(!get)return false;n.api=get();
    auto&c=n.config;c.request.boundary=layout.config;c.request.boundary.menu=0;c.request.boundary.attempt=identity(i).attempt;
    n.request=dir+L"/request-"+std::to_wstring(i)+L".once";n.identity=dir+L"/identity-"+std::to_wstring(i)+L".once";
    c.request.localPath=path;c.request.intentPath=n.request.c_str();c.request.validate=requestValidate;std::memset(c.request.ownerBinding,0x63,32);
    c.request.storage={reinterpret_cast<void*>(storage),exists,fileSize,readOriginal,storageValidate,nullptr};
    c.bytes.base=layout.config.base;c.bytes.attemptToken=identity(i).attempt;c.bytes.storage=storage;c.bytes.storageVtable=storage+16;c.bytes.readMethod=reinterpret_cast<std::uintptr_t>(&readOriginal);c.bytes.validateAttachment=bytesValidate;c.bytes.fixtureWorkerCaller=0x12340000;c.bytes.fixtureReadCaller=0x12340001;c.bytes.fixtureParentCaller=0x12340002;
    c.lifecycle.base=layout.config.base;c.lifecycle.attemptToken=identity(i).attempt;c.lifecycle.validateAttachment=lifeValidate;c.lifecycle.fixtureUpdateCaller=0x12340003;
    c.identity.base=layout.config.base;c.identity.attemptToken=identity(i).attempt;c.identity.validateAttachment=titleValidate;c.identity.intentPath=n.identity.c_str();std::memset(c.identity.ownerBinding,0x63,32);c.identity.fixtureWorkerCaller=0x12340000;
    c.validate=validate;c.context=&n;c.userAfter=control;c.userObservationBefore=before;c.userObservationAfter=after;c.userObservationContext=&n;
    void* originals[]={reinterpret_cast<void*>(&userOriginal),reinterpret_cast<void*>(&menuOriginal),reinterpret_cast<void*>(&gameOriginal),reinterpret_cast<void*>(&loadOriginal),reinterpret_cast<void*>(&workerOriginal),reinterpret_cast<void*>(&readOriginal)};
    for(unsigned j=0;j<6;++j){c.hooks[j]={slots+j,originals[j],nullptr};c.fixtureDispatchCaller[j<4?j:0]=layout.config.base+0x50B785;}
    const bool ok=owner.Prepare(m,identity(i),c);if(ok)check(n.api->describe(&n.desc),"description");return ok;
}
static std::uint64_t call(void*p){return reinterpret_cast<Invoke>(p)(layout.config.states[4],1,2,3);}
static bool exceptionCall(void*p){__try{call(p);return false;}__except(GetExceptionCode()==0xE0146701?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}}
static void dispatch(HMODULE m,unsigned slot){auto invoke=reinterpret_cast<FrameInvoke>(GetProcAddress(m,"CheckpointSessionGenerationFixtureDispatch"));check(invoke!=nullptr,"fixture-only dispatch adaptation");
    CheckpointPushFrame f{};for(unsigned j=0;j<4;++j)f.args[j]=layout.call.args[j];f.caller_entry_rsp=layout.call.callerEntryRsp;invoke(slot,&f);check(f.result_rax==ReturnValue,"real bridge original result preserved");}
static DWORD WINAPI wrongThread(void*){sg::Report r{};return !owner.Activate(1)&&!owner.Snapshot(r)&&!owner.StopRetaining(0)?0:1;}
int wmain(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=6)return 2;scenario=argv[1];
    FILE*f=nullptr;_wfopen_s(&f,argv[5],L"rb");if(!f)return 3;archive.resize(by::TargetSize);check(fread(archive.data(),1,archive.size(),f)==archive.size()&&fgetc(f)==EOF,"complete archived workspace input");fclose(f);
    check(layout.initialize(bd::Stage::MenuAfter),"own synthetic memory");put<std::uint64_t>(layout.manager+0x10,5);pending=reinterpret_cast<std::uintptr_t>(layout.arena)+0x80000;storage=pending+0x100;put<std::uintptr_t>(layout.manager+0x40,pending);
    slots=reinterpret_cast<void**>(VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));check(slots!=nullptr,"owned six-slot page");
    void* originals[]={reinterpret_cast<void*>(&userOriginal),reinterpret_cast<void*>(&menuOriginal),reinterpret_cast<void*>(&gameOriginal),reinterpret_cast<void*>(&loadOriginal),reinterpret_cast<void*>(&workerOriginal),reinterpret_cast<void*>(&readOriginal)};
    std::memcpy(slots,originals,sizeof originals);DWORD old=0;check(VirtualProtect(slots,4096,PAGE_READONLY,&old)!=0,"readonly slots");
    auto m0=LoadLibraryExW(argv[3],nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_SYSTEM32);auto m1=LoadLibraryExW(argv[4],nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_SYSTEM32);check(m0&&m1&&m0!=m1,"distinct owned modules same process");if(!m0||!m1)return 4;
    check(setupNode(0,m0,argv[2],argv[5]),"prepare first frozen Session");
    if(scenario==L"binding-rejections"){
        auto id=identity(1);id.attempt=identity(0).attempt;check(!owner.Prepare(m1,id,nodes[0].config),"duplicate attempt refuses");
        id=identity(1);auto c=nodes[0].config;c.request.boundary.attempt=id.attempt;id.attachment[0]^=1;check(!owner.Prepare(m1,id,c),"attachment change refuses");
        check(!owner.Prepare(m0,identity(0),nodes[0].config),"same bank refuses");
        check(!nodes[0].api->initialize(&id,&c),"same bank cannot reset Session");
    }
    check(setupNode(1,m1,argv[2],argv[5]),"prepare second frozen Session before either publishes");
    for(unsigned k=0;k<6;++k)check(nodes[0].desc.hooks[k].hook!=nodes[1].desc.hooks[k].hook,"six immutable per-generation entry addresses");
    check(owner.Activate(0),"activate first bank");auto oldUser=nodes[0].desc.hooks[0].hook;auto newUser=nodes[1].desc.hooks[0].hook;
    if(scenario==L"post-cas-retained"||scenario==L"menu-outstanding")nodes[0].bindMenu=true;
    if(scenario==L"active-frame")rotateInside=true;
    if(scenario==L"native-exception"){
        throwOriginal=true;check(exceptionCall(oldUser),"native SEH preserved");throwOriginal=false;check(!owner.Activate(1),"abnormal old frame forbids switching");
    }else check(call(slots[0])==ReturnValue,"real published bridge forwards original");
    if(scenario==L"post-cas-retained"){
        put<std::uint64_t>(layout.manager+0x10,6);put<std::uint64_t>(layout.manager+0x30,0);layout.setStage(bd::Stage::MenuAfter);dispatch(m0,1);
        layout.setStage(bd::Stage::GameBefore);dispatch(m0,2);
        ns::Report beforeStop{};nodes[0].api->snapshot(&beforeStop);check(beforeStop.casPublished&&beforeStop.mayHavePublished&&beforeStop.request.casAttempts==1&&beforeStop.request.intentDurable,"actual request CAS and durable once, not injected receipt");
        check(!owner.Activate(1),"published Session cannot switch");
        const auto candidate=pending+0x200;put<std::uintptr_t>(candidate+8,layout.config.base+0x1234);auto worker=reinterpret_cast<Invoke>(nodes[0].desc.hooks[4].hook);check(worker(candidate,0,0,0)==ReturnValue,"old worker still forwards after Stop");
        ns::Report r{};nodes[0].api->snapshot(&r);check(r.stopRequested&&r.state==ns::State::RetainingObservation&&r.bytes.otherWorkers==1&&!r.hooksRestored,"old observer remains live for old worker");
        check(!nodes[0].api->restoreBeforeCommit(),"frozen Session post-CAS restore refuses");for(unsigned k=0;k<6;++k)check(slots[k]==nodes[0].desc.hooks[k].hook,"all old observers retained");
    }else if(scenario==L"menu-outstanding")check(!owner.Activate(1),"queued menu forbids even pre-CAS rotation");
    else if(scenario==L"foreign-slot"){
        VirtualProtect(slots,4096,PAGE_READWRITE,&old);slots[3]=reinterpret_cast<void*>(&gameOriginal);VirtualProtect(slots,4096,PAGE_READONLY,&old);
        check(!owner.Activate(1),"foreign slot prevents next arm");check(slots[3]==reinterpret_cast<void*>(&gameOriginal),"foreign slot never overwritten");
    }else if(scenario==L"native-exception"){}
    else {
        if(scenario==L"wrong-thread"){HANDLE h=CreateThread(nullptr,0,wrongThread,nullptr,0,nullptr);check(h&&WaitForSingleObject(h,5000)==WAIT_OBJECT_0,"owned wrong-thread test joined");DWORD code=1;GetExitCodeThread(h,&code);CloseHandle(h);check(code==0,"owner thread enforced");}
        check(owner.Activate(1),"pre-CAS slots restore then second arm");
        ns::Report oldBefore{},newBefore{};nodes[0].api->snapshot(&oldBefore);nodes[1].api->snapshot(&newBefore);
        const auto newCount=nodes[1].before,oldControllers=nodes[0].controllers;
        check(call(oldUser)==ReturnValue&&call(oldUser)==ReturnValue,"prefetched old pointer repeats transparently");
        ns::Report oldAfter{},newAfter{};nodes[0].api->snapshot(&oldAfter);nodes[1].api->snapshot(&newAfter);
        check(nodes[1].before==newCount&&newAfter.dispatchStats[0].started==newBefore.dispatchStats[0].started,"late old calls never enter new Session");
        check(oldAfter.dispatchStats[0].started==oldBefore.dispatchStats[0].started+2&&nodes[0].controllers==oldControllers,"old bank remains own address and cannot drive");
        check(call(newUser)==ReturnValue&&call(slots[0])==ReturnValue,"new pointer real bridge callbacks");
        check(nodes[1].controllers==1,"new Session once independent; duplicate suppressed");
        check(nodes[0].controllers==(scenario==L"active-frame"?0u:1u),"old once never reset");
        check(!owner.Activate(0)&&!owner.Activate(1),"no generation rollback or rearm");
        check(!owner.Prepare(m0,identity(0),nodes[0].config),"fixed bank capacity cannot recycle");
        check(owner.StopRetaining(1),"stop next bank retains immutable observer address");check(call(newUser)==ReturnValue&&nodes[1].controllers==1,"stopped new callback no additional request");
    }
    sg::Report report{};check(owner.Snapshot(report),"owner snapshot");check(report.count==2&&report.entries[0].pinned&&report.entries[1].pinned,"bounded pinned lifetime");
    check(!report.schedulerFenceProven&&!report.admissionAuthorized&&!report.postCasRotationSupported,"no release or full runtime proof");
    check(!report.entries[1].session.casPublished,"second bank never loads");
    if(scenario==L"active-frame")check(callbackDuringSwitch==1,"active frame refusal exercised");
    std::printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"banks\":%u,\"old_once\":%u,\"new_once\":%u,\"old_cas\":%u,\"new_cas\":%u,\"last_error\":%u,\"game_access\":false,\"two_complete_loads\":false}\n",scenario.c_str(),errors?"false":"true",errors,report.count,nodes[0].controllers,nodes[1].controllers,report.entries[0].session.casPublished,report.entries[1].session.casPublished,unsigned(report.lastError));
    // Modules/Session/context/source objects are intentionally not reclaimed
    // before process exit. The fixture process is the lifetime boundary.
    return errors?1:0;
}
