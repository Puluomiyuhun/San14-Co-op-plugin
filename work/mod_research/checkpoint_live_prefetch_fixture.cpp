#include "checkpoint_live_prefetch_core.h"
#include "checkpoint_load_input_boundary_fixture_layout.h"
#include <cstdio>
#include <cstring>
#include <string>
static volatile LONG calls=0,failures=0;static bool shouldThrow=false;
extern "C" unsigned char CheckpointLivePrefetchFixtureSite;
static HANDLE bodyEntered=nullptr,bodyRelease=nullptr;
extern "C" std::uint64_t CheckpointLiveFixtureOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" void CheckpointLiveFixtureBody(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){InterlockedIncrement(&calls);if(!a||b!=2||c!=3||d!=4)InterlockedIncrement(&failures);if(bodyEntered&&bodyRelease){SetEvent(bodyEntered);WaitForSingleObject(bodyRelease,5000);}if(shouldThrow)RaiseException(0xE014A001,0,0,nullptr);}
static void check(bool b,const char* message){if(!b){InterlockedIncrement(&failures);printf("FAIL %s\n",message);}}
template<class T>static void put(std::uint64_t p,T v){memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
using Fn=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
static bool invoke(Fn fn,std::uint64_t user){__try{check(fn(user,2,3,4)==0xFEDCBA9876543210ull,"RAX result");return false;}__except(GetExceptionCode()==0xE014A001?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}}
struct Worker {Fn fn=nullptr;std::uint64_t user=0;HANDLE go=nullptr,done=nullptr,exit=nullptr;unsigned repeat=1;DWORD tid=0;};
static DWORD WINAPI work(void* p){auto&w=*static_cast<Worker*>(p);w.tid=GetCurrentThreadId();
    for(unsigned i=0;i<w.repeat;++i){check(WaitForSingleObject(w.go,5000)==WAIT_OBJECT_0,"worker go");check(!invoke(w.fn,w.user),"worker original forwards");SetEvent(w.done);}
    if(w.exit)check(WaitForSingleObject(w.exit,5000)==WAIT_OBJECT_0,"worker retained until all IDs collected");return 0;}
struct Installer{CheckpointLivePrefetchConfig* config;DWORD result=99;};
static DWORD WINAPI installWorker(void*p){auto&w=*static_cast<Installer*>(p);w.result=InstallCheckpointLivePrefetchObserver(w.config);return 0;}
struct Stopper{HANDLE entered=nullptr;DWORD result=99;};
static DWORD WINAPI stopWorker(void*p){auto&w=*static_cast<Stopper*>(p);SetEvent(w.entered);w.result=StopCheckpointLivePrefetchObserver(nullptr);return 0;}
static void threads(Fn fn,std::uint64_t user,unsigned count,unsigned repeat){
    Worker ws[129]{};HANDLE hs[129]{};HANDLE release=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    for(unsigned i=0;i<count;++i){ws[i].fn=fn;ws[i].user=user;ws[i].go=CreateEventW(nullptr,FALSE,FALSE,nullptr);ws[i].done=CreateEventW(nullptr,FALSE,FALSE,nullptr);ws[i].exit=release;ws[i].repeat=repeat;hs[i]=CreateThread(nullptr,0,work,&ws[i],0,nullptr);check(hs[i]!=nullptr,"real worker created");}
    for(unsigned j=0;j<repeat;++j)for(unsigned i=0;i<count;++i){SetEvent(ws[i].go);check(WaitForSingleObject(ws[i].done,5000)==WAIT_OBJECT_0,"alternating actual thread finished");}
    SetEvent(release);for(unsigned i=0;i<count;++i)check(WaitForSingleObject(hs[i],5000)==WAIT_OBJECT_0,"workers joined");
    for(unsigned i=0;i<count;++i){for(unsigned j=0;j<i;++j)check(ws[i].tid!=ws[j].tid,"simultaneously live IDs distinct");CloseHandle(hs[i]);CloseHandle(ws[i].go);CloseHandle(ws[i].done);}CloseHandle(release);
}
int wmain(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=3)return 2;const std::wstring scenario=argv[1];
    checkpoint_load_input_boundary_fixture::Layout layout;check(layout.initialize(),"owned layout");auto b=layout.config.base;
    put<std::uint64_t>(layout.manager+0x10,5);put<std::uint64_t>(layout.manager+0x48,layout.config.states[4]);
    put<std::uint64_t>(layout.config.root,b+0x12AA6B0);put<std::uint64_t>(layout.config.world,b+0x12AA638);
    auto slot=reinterpret_cast<void**>(b+0x12CC4A8+0x28);*slot=reinterpret_cast<void*>(&CheckpointLiveFixtureOriginal);
    CheckpointLivePrefetchConfig c{};c.pid=GetCurrentProcessId();FILETIME born{},e{},k{},u{};GetProcessTimes(GetCurrentProcess(),&born,&e,&k,&u);c.birth=(std::uint64_t(born.dwHighDateTime)<<32)|born.dwLowDateTime;
    c.base=b;c.attempt=19;memset(c.attachment,0x73,32);c.root=layout.config.root;c.world=layout.config.world;memcpy(c.states,layout.config.states,sizeof c.states);c.toolbar=layout.toolbar;c.panel=layout.panel;wcscpy_s(c.journal,argv[2]);c.reserved[0]=reinterpret_cast<std::uint64_t>(&CheckpointLiveFixtureOriginal);c.reserved[1]=reinterpret_cast<std::uint64_t>(&CheckpointLivePrefetchFixtureSite);
    c.cache=layout.config.cache;c.stack=layout.stack;c.stackCapacity=16;c.queue=0;c.queueCapacity=0;c.expectedMode=0;c.generation=1;
    put<std::uint64_t>(layout.manager+0x18,c.stackCapacity);put<std::uint64_t>(layout.manager+0x40,0);put<std::uint64_t>(layout.manager+0x38,0);put<DWORD>(c.cache+8,0);
    if(scenario==L"bad-birth")++c.birth;
    if(scenario==L"bad-mode")put<DWORD>(c.cache+8,1);
    if(scenario==L"pending")put<LONG>(layout.toolbar+0x88,6);
    if(scenario==L"wrong-thread")c.expectedUserThread=GetCurrentThreadId()+1;
    if(scenario==L"bad-path")wcscpy_s(c.journal,L"C:\\not-authorized\\live.jsonl");
    if(scenario==L"foreign-slot")*slot=reinterpret_cast<void*>(&wmain);
    if(scenario==L"idle-current-zero")put<std::uint64_t>(layout.manager+0x48,0);
    if(scenario==L"idle-current-other")put<std::uint64_t>(layout.manager+0x48,c.states[0]);
    DWORD install=99;CheckpointLivePrefetchReport r{};
    if(scenario==L"install-stop-race"){
        HANDLE ready=CreateEventW(nullptr,TRUE,FALSE,nullptr),release=CreateEventW(nullptr,TRUE,FALSE,nullptr);
        CheckpointLiveThreadsFixturePublishGate(ready,release);Installer installer{&c};auto ih=CreateThread(nullptr,0,installWorker,&installer,0,nullptr);
        check(WaitForSingleObject(ready,5000)==WAIT_OBJECT_0,"install paused before publication under control lock");
        Stopper stopper{CreateEventW(nullptr,TRUE,FALSE,nullptr)};auto sh=CreateThread(nullptr,0,stopWorker,&stopper,0,nullptr);
        check(WaitForSingleObject(stopper.entered,5000)==WAIT_OBJECT_0,"real Stop thread entered");
        check(WaitForSingleObject(sh,40)==WAIT_TIMEOUT,"Stop waits behind in-progress Install");
        check(*slot==reinterpret_cast<void*>(&CheckpointLiveFixtureOriginal),"not yet published while blocked");
        SetEvent(release);check(WaitForSingleObject(ih,5000)==WAIT_OBJECT_0&&WaitForSingleObject(sh,5000)==WAIT_OBJECT_0,"concurrent control joined");install=installer.result;
        check(install==0&&stopper.result==0,"install then stop success");GetCheckpointLivePrefetchReport(&r);
        check(r.installed&&r.stopped&&r.slotRestored&&*slot==reinterpret_cast<void*>(&CheckpointLiveFixtureOriginal),"no publication after completed Stop");
        check(!invoke(&CheckpointPushBridge0,c.states[4]),"old retained callback still forwards");GetCheckpointLivePrefetchReport(&r);check(r.lateBefore==1&&r.lateAfter==1&&!r.matchedPairs,"late forwarding classified separately");
        CloseHandle(ready);CloseHandle(release);CloseHandle(ih);CloseHandle(sh);CloseHandle(stopper.entered);
    }else if(scenario==L"stop-before-install"){
        StopCheckpointLivePrefetchObserver(nullptr);install=InstallCheckpointLivePrefetchObserver(&c);GetCheckpointLivePrefetchReport(&r);
        check(install==13&&r.stopped&&!r.installed&&*slot==reinterpret_cast<void*>(&CheckpointLiveFixtureOriginal),"Stop wins before Install permanently");
    }else if(scenario==L"two-threads"||scenario==L"thread-overflow"||scenario==L"active-stop"){
        install=InstallCheckpointLivePrefetchObserver(&c);check(install==0,"observer installed");auto cached=reinterpret_cast<Fn>(*slot);
        if(scenario==L"active-stop"){
            bodyEntered=CreateEventW(nullptr,TRUE,FALSE,nullptr);bodyRelease=CreateEventW(nullptr,TRUE,FALSE,nullptr);
            Worker w{cached,c.states[4],CreateEventW(nullptr,FALSE,FALSE,nullptr),CreateEventW(nullptr,FALSE,FALSE,nullptr)};auto h=CreateThread(nullptr,0,work,&w,0,nullptr);SetEvent(w.go);
            check(WaitForSingleObject(bodyEntered,5000)==WAIT_OBJECT_0,"original active after actual BEFORE");GetCheckpointLivePrefetchReport(&r);check(r.pendingPairs==1&&r.active==1,"pending visible while original active");
            check(StopCheckpointLivePrefetchObserver(nullptr)==0,"Stop restores while original active");GetCheckpointLivePrefetchReport(&r);check(r.pendingPairs==1&&!r.matchedPairs,"Stop does not forge pair completion");
            SetEvent(bodyRelease);check(WaitForSingleObject(h,5000)==WAIT_OBJECT_0,"active original completed after Stop");GetCheckpointLivePrefetchReport(&r);
            check(r.matchedPairs==1&&!r.pendingPairs&&r.matchingBefore==1&&r.matchingAfter==1&&!r.lateAfter,"in-flight AFTER finishes real earlier pair");
            CloseHandle(bodyEntered);CloseHandle(bodyRelease);bodyEntered=bodyRelease=nullptr;CloseHandle(w.go);CloseHandle(w.done);CloseHandle(h);
        }else{
            const unsigned n=scenario==L"two-threads"?2:129,repeats=scenario==L"two-threads"?3:1;threads(cached,c.states[4],n,repeats);GetCheckpointLivePrefetchReport(&r);
            check(r.threadCount==(n<128?n:128)&&r.threadOverflow==(n>128?1u:0u),"bounded actual thread census");
            check(r.matchedPairs==n*repeats&&!r.pendingPairs&&!r.pairErrors&&!r.pairOverflow,"every actual call paired");
            check(!r.error&&r.threadMigrations==n*repeats-1,"migration is observed without owner rejection");
            for(unsigned i=0;i<r.threadCount;++i)check(r.threads[i].before==repeats&&r.threads[i].after==repeats&&!r.threads[i].pending,"per-thread pairs preserved");
            check(StopCheckpointLivePrefetchObserver(nullptr)==0,"restore after thread census");
        }
        check(!invoke(cached,c.states[4]),"cached callback after Stop");GetCheckpointLivePrefetchReport(&r);check(r.lateBefore==1&&r.lateAfter==1&&!r.pairErrors,"late pair separate and metadata unobserved");check(r.slotRestored&&r.protectionRestored,"slot restored");
        if(scenario==L"two-threads"||scenario==L"thread-overflow")check(r.admissionStarted==1&&r.admissionFinished==1&&r.hardware.captured&&r.hardware.restored&&!r.admissionErrors,"only first actual native callback sampled across all threads");
        if(scenario==L"active-stop")check(r.admissionStarted==1&&r.admissionFinished==1&&r.hardware.restored&&r.admissionErrors>0,"in-flight Stop remains diagnostically incomplete after exact DR cleanup");
    }else{
    install=InstallCheckpointLivePrefetchObserver(&c);
    if(scenario==L"bad-birth"||scenario==L"pending"||scenario==L"bad-mode"||scenario==L"bad-path"||scenario==L"foreign-slot"){
        check(install!=0,"rejection before hook");check(calls==0,"no native call on reject");
    }else {
        check(install==0,"observer installed");auto cached=reinterpret_cast<Fn>(*slot);
        if(scenario==L"idle-current-zero"||scenario==L"idle-current-other"){
            check(!r.firstPair,"installation did not fabricate first callback");
            put<std::uint64_t>(layout.manager+0x48,c.states[4]);
        }
        if(scenario==L"callback-wrong-current")put<std::uint64_t>(layout.manager+0x48,c.states[2]);
        if(scenario==L"exception")shouldThrow=true;
        const auto thrown=invoke(cached,c.states[4]);shouldThrow=false;check(thrown==(scenario==L"exception"),"original exception propagates");
        GetCheckpointLivePrefetchReport(&r);check(r.bridgeStarted==1&&!r.active,"bridge active cleanup");check(!r.queueCalls&&!r.requestCas&&!r.loadRequested&&!r.fullInputHold&&!r.completeSessionInstalled,"observe only");
        if(scenario==L"exception")check(!r.firstPair&&r.bridgeAbnormal==1&&r.admissionStarted==1&&r.admissionFinished==1&&r.admissionAbnormal==1&&r.hardware.restored,"original exception propagates after hardware cleanup, no forged AFTER");
        else if(scenario==L"wrong-thread")check(!r.firstPair&&r.error==20,"wrong owner cannot become bootstrap");
        else if(scenario==L"callback-wrong-current")check(!r.firstPair&&!r.contextVerified&&r.error==23&&calls==1&&r.matchedPairs==1&&!r.pendingPairs,"wrong dispatch rejected but original forwarded and physically paired");
        else {check(r.admissionStarted==1&&r.admissionFinished==1&&r.admissionClosed==1&&!r.admissionErrors&&r.hardware.captured&&r.hardware.restored&&r.pendingBefore.decision==checkpoint_native_input_pending::Decision::QuiescentObserved&&r.hardware.pending.pending_admission_candidate&&r.pendingAfter.pending_admission_candidate&&!r.admissionResolverCalls,"real hardware three observations with mode0 empty native queue");check(r.firstPair&&r.contextVerified&&r.ownerThread==GetCurrentThreadId()&&r.firstRax==0xFEDCBA9876543210ull,"first actual owned-thread pair");for(auto x:r.firstXmm0)check(x==255,"XMM0 preserved");}
        check(InstallCheckpointLivePrefetchObserver(&c)!=0,"one-shot install");check(StopCheckpointLivePrefetchObserver(nullptr)==0,"restore owned slot");check(*slot==reinterpret_cast<void*>(&CheckpointLiveFixtureOriginal),"original slot restored");
        check(!invoke(cached,c.states[4]),"cached old bridge forwards after stop");GetCheckpointLivePrefetchReport(&r);check(r.modulePinned&&r.slotRestored&&r.protectionRestored&&r.stopped,"module retained and protection restored");check(r.bridgeStarted==2,"late cached call belongs to old bridge");
    }
    }
    if(scenario==L"success"){
        FILE* out=nullptr;auto path=std::wstring(argv[2])+L".report.bin";_wfopen_s(&out,path.c_str(),L"wb");if(out){fwrite(&r,sizeof r,1,out);fclose(out);}else check(false,"raw ABI report");
    }
    printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%ld,\"config_size\":%zu,\"report_size\":%zu,\"install_exit\":%lu,\"original_calls\":%ld,\"thread_count\":%u,\"matched_pairs\":%llu,\"pair_errors\":%u,\"pending_pairs\":%llu,\"late_before\":%llu,\"late_after\":%llu,\"game_access\":false}\n",scenario.c_str(),failures?"false":"true",failures,sizeof c,sizeof r,install,calls,r.threadCount,r.matchedPairs,r.pairErrors,r.pendingPairs,r.lateBefore,r.lateAfter);
    printf("{\"abi\":true,\"config_bytes\":%zu,\"report_bytes\":%zu,\"pending_bytes\":%zu,\"hardware_bytes\":%zu,\"pending_before_offset\":%zu,\"pending_after_offset\":%zu,\"hardware_offset\":%zu,\"admission_started_offset\":%zu}\n",sizeof c,sizeof r,sizeof r.pendingBefore,sizeof r.hardware,offsetof(CheckpointLivePrefetchReport,pendingBefore),offsetof(CheckpointLivePrefetchReport,pendingAfter),offsetof(CheckpointLivePrefetchReport,hardware),offsetof(CheckpointLivePrefetchReport,admissionStarted));
    return failures?1:0;
}

