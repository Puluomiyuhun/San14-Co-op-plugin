#include "checkpoint_native_input_hwbp.h"
#include "checkpoint_native_input_prefetch_bridge.h" // Snapshot layout only; no legacy mid bridge is called.
#include "checkpoint_load_input_boundary_fixture_layout.h"
#include <cstring>
#include <cstdio>
#include <string>
#include <xmmintrin.h>
namespace hw=checkpoint_native_input_hwbp;namespace pd=checkpoint_native_input_pending;namespace mid=checkpoint_native_input_prefetch;
extern "C" {
std::uintptr_t HwbpFixtureUser=0;
mid::Frame HwbpFixtureBefore{},HwbpFixtureAfter{};
alignas(16) std::uint8_t HwbpFixtureSeed[256]{};
std::int32_t HwbpFixtureFetched=-99;
void HwbpFixtureSite();void HwbpFixtureClobber();
extern unsigned char HwbpFixtureBeforeCall,HwbpFixtureAfterNative;
}
static hw::Context provider;static pd::Config config;static pd::Adapter pending;
static hw::HardwareReceipt receipt;static pd::Report before{},after{};
static std::wstring scenario;static unsigned failures=0,original_calls=0,after_calls=0,observer_calls=0;
static bool beginOk=false;static CheckpointPushFrame saved;static void*faultPage=nullptr;
static DWORD WINAPI foreignFinish(void*){hw::Finish(provider);return 0;}
static void check(bool yes,const char* what){if(!yes){++failures;std::printf("FAIL %s\n",what);}}
template<class T>static void put(std::uintptr_t p,T v){std::memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
struct DebugChange{HANDLE target;CONTEXT result{};unsigned mode;bool okay=false;};
static DWORD WINAPI debugChange(void*p){
    auto&d=*static_cast<DebugChange*>(p);if(SuspendThread(d.target)==DWORD(-1))return 1;
    d.result.ContextFlags=CONTEXT_DEBUG_REGISTERS;d.okay=GetThreadContext(d.target,&d.result)!=0;
    if(d.okay&&d.mode){d.result.Dr1=d.mode==1?0x12345678:0xABCDEF00;if(d.mode==1)d.result.Dr7|=4;d.okay=SetThreadContext(d.target,&d.result)!=0;}
    if(ResumeThread(d.target)==DWORD(-1))d.okay=false;return 0;
}
static CONTEXT debug(unsigned mode=0){
    DebugChange d{};d.mode=mode;DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&d.target,0,FALSE,DUPLICATE_SAME_ACCESS);
    auto h=CreateThread(nullptr,0,debugChange,&d,0,nullptr);check(h&&WaitForSingleObject(h,5000)==WAIT_OBJECT_0&&d.okay,"owned helper debug context");
    if(h)CloseHandle(h);if(d.target)CloseHandle(d.target);return d.result;
}
static pd::Report observe(void*,const hw::Binding&b,std::uint64_t c,const void*u)noexcept{
    ++observer_calls;
    // Intentionally clobber legal observer state; OS CONTEXT restoration must
    // preserve the native instruction's interrupted live registers/flags.
    _mm_setcsr(_mm_getcsr()^0x6000);HwbpFixtureClobber();
    if(scenario==L"observer-fault")RaiseException(0xE0147101,0,0,nullptr);
    return pending.ObserveBeforeFetch(b,c,u);
}
static void beforeFn(const CheckpointPushFrame*f,void*)noexcept{saved=*f;before=pending.ObserveBefore(config.binding,*f);}
static void afterFn(const CheckpointPushFrame*f,void*)noexcept{++after_calls;after=pending.ObserveAfter(config.binding,*f);pending.CloseAfter(config.binding,f->call_id);}
static std::uint64_t original(std::uint64_t user,std::uint64_t b,std::uint64_t c,std::uint64_t d){
    ++original_calls;check(user==config.states[4]&&b==2&&c==3&&d==4,"original args");
    if(scenario==L"late-ui")put<LONG>(reinterpret_cast<std::uintptr_t>(config.toolbar.data)+0x88,13);
    auto binding=config.binding;if(scenario==L"wrong-binding")++binding.attachment[0];
    beginOk=hw::Begin(provider,observe,nullptr,binding,saved.call_id,reinterpret_cast<void*>(user));
    if(scenario==L"foreign-finish"){auto t=CreateThread(nullptr,0,foreignFinish,nullptr,0,nullptr);if(t){WaitForSingleObject(t,5000);CloseHandle(t);}}
    if(scenario==L"stop-active")hw::Stop(provider);
    if(scenario==L"native-fault")HwbpFixtureUser=reinterpret_cast<std::uintptr_t>(faultPage);
    if(scenario==L"wrong-user")HwbpFixtureUser+=0x10;
    try {
        if(scenario!=L"missing-site")HwbpFixtureSite();
        if(scenario==L"repeat-site")HwbpFixtureSite();
        if(scenario==L"foreign-exception")RaiseException(0xE014BEEF,0,0,nullptr);
        if(scenario==L"restore-conflict")debug(2);
    }catch(...){hw::Finish(provider);hw::Snapshot(provider,receipt);throw;}
    hw::Finish(provider);hw::Snapshot(provider,receipt);
    return 0xF123456789ABCDEFull;
}
static DWORD invoke(){__try {check(CheckpointLoadDispatchBridge0(config.states[4],2,3,4)==0xF123456789ABCDEFull,"original RAX");return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return GetExceptionCode();}}
int wmain(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=2)return 2;scenario=argv[1];
    checkpoint_load_input_boundary_fixture::Layout l;check(l.initialize(),"owned layout");
    config.binding.attempt[0]=1;config.binding.attachment[0]=2;config.binding.owner_generation=3;config.profile_base=l.config.base;
    std::memcpy(config.states,l.config.states,sizeof config.states);
    config.user={reinterpret_cast<const std::uint8_t*>(l.config.states[4]),0x700};config.toolbar={reinterpret_cast<const std::uint8_t*>(l.toolbar),0x100};
    config.game={reinterpret_cast<const std::uint8_t*>(l.config.states[2]),0x500};config.panel={reinterpret_cast<const std::uint8_t*>(l.panel),0x200};
    config.manager={reinterpret_cast<const std::uint8_t*>(l.manager),0x80};config.stack={reinterpret_cast<const std::uint8_t*>(l.stack),0x40};
    config.queue={reinterpret_cast<const std::uint8_t*>(l.stack+0x100),0x40};config.load_cache={reinterpret_cast<const std::uint8_t*>(l.config.cache),0x440};
    put<std::uint64_t>(l.manager+0x10,5);put<std::uintptr_t>(l.manager+0x48,l.config.states[4]);put<std::uintptr_t>(l.manager+0x40,reinterpret_cast<std::uintptr_t>(config.queue.data));put<std::uint64_t>(l.manager+0x38,4);put<DWORD>(l.config.cache+8,1);
    if(scenario==L"player-request")put<LONG>(l.toolbar+0x88,6);
    if(scenario==L"null-toolbar")put<std::uintptr_t>(l.config.states[4]+0x478,0);
    check(pending.Bind(config)==pd::Error::None,"adapter binds");
    HwbpFixtureUser=l.config.states[4];for(unsigned i=0;i<256;++i)HwbpFixtureSeed[i]=static_cast<std::uint8_t>((i*37+17)&255);
    hw::Config h{};h.binding=config.binding;h.site_rip=reinterpret_cast<std::uintptr_t>(&HwbpFixtureBeforeCall);
    if(scenario==L"arm-deadline")h.helper_deadline_ms=1;
    if(scenario==L"wrong-bytes")++h.site_rip;
    const bool initialized=hw::Initialize(provider,h);
    if(scenario==L"wrong-bytes"){check(!initialized,"wrong 33-byte site refused");std::printf("{\"case\":\"wrong-bytes\",\"passed\":%s,\"game_access\":false}\n",failures?"false":"true");return failures?1:0;}
    check(initialized,"provider initializes");
    if(scenario==L"arm-deadline")hw::FixtureHelperDelay(30);
    if(scenario==L"stop-before")hw::Stop(provider);
    if(scenario==L"occupied-dr")debug(1);
    if(scenario==L"native-fault")faultPage=VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_NOACCESS);
    const auto initial=debug();
    CheckpointLoadDispatchBridgeConfig b{};b.original=reinterpret_cast<void*>(&original);b.before=beforeFn;b.after=afterFn;check(CheckpointLoadDispatchBridgeConfigure(0,&b),"actual dispatch bridge configured");
    const DWORD exception=invoke();const auto final=debug();
    std::printf("DR initial %llx %llx %llx %llx %llx %llx final %llx %llx %llx %llx %llx %llx\n",initial.Dr0,initial.Dr1,initial.Dr2,initial.Dr3,initial.Dr6,initial.Dr7,final.Dr0,final.Dr1,final.Dr2,final.Dr3,final.Dr6,final.Dr7);
    const bool noArm=scenario==L"wrong-binding"||scenario==L"stop-before"||scenario==L"occupied-dr"||scenario==L"arm-deadline";
    if(!noArm)check(beginOk,"hardware armed");else check(!beginOk&&!receipt.captured&&!observer_calls,"guard rejected hardware admission");
    const bool nativeFault=scenario==L"native-fault",foreign=scenario==L"foreign-exception";
    check(exception==(nativeFault?EXCEPTION_ACCESS_VIOLATION:foreign?0xE014BEEF:0),"only original exception propagates");
    check(original_calls==1&&after_calls==((nativeFault||foreign)?0u:1u),"original/AFTER lifecycle");
    if(!noArm&&scenario!=L"restore-conflict")check(receipt.restored&&receipt.finished&&!receipt.restore_uncertain,"precise cleanup complete");
    if(scenario==L"restore-conflict")check(!receipt.restored&&receipt.restore_uncertain&&receipt.error==hw::Error::RestoreConflict&&final.Dr1==0xABCDEF00,"foreign debug owner not overwritten");
    else check(initial.Dr0==final.Dr0&&initial.Dr1==final.Dr1&&initial.Dr2==final.Dr2&&initial.Dr3==final.Dr3&&initial.Dr6==final.Dr6&&initial.Dr7==final.Dr7,"all six original debug registers exactly restored");
    if(scenario==L"success"||scenario==L"player-request"||scenario==L"late-ui"||scenario==L"observer-fault"||scenario==L"stop-active"||scenario==L"foreign-exception"||scenario==L"restore-conflict"){
        check(receipt.capture_kind==hw::CaptureKind::HardwareExecuteContext&&receipt.captured==1&&receipt.site_rip==h.site_rip&&receipt.thread==GetCurrentThreadId(),"actual hardware exception identity");
        for(unsigned i=0;i<16;++i)check(receipt.gpr[i]==HwbpFixtureBefore.gpr[i],"all native interrupted GPR captured");
        check((receipt.rflags&~0x10000ull)==HwbpFixtureBefore.rflags,"interrupted flags captured excluding RF resume machinery");
        check(!std::memcmp(receipt.xmm,HwbpFixtureBefore.xmm,256)&&receipt.mxcsr==HwbpFixtureBefore.mxcsr,"interrupt XMM/MXCSR captured");
        for(unsigned i=0;i<16;++i)if(i!=mid::Rax&&i!=mid::R14)check(HwbpFixtureBefore.gpr[i]==HwbpFixtureAfter.gpr[i],"unchanged native GPR preserved");
        check(!std::memcmp(HwbpFixtureBefore.xmm,HwbpFixtureAfter.xmm,256)&&HwbpFixtureBefore.mxcsr==HwbpFixtureAfter.mxcsr,"observer clobber does not leak XMM/MXCSR");
    }
    if(scenario==L"success")check(receipt.error==hw::Error::None&&receipt.observer_calls==1&&receipt.pending.pending_admission_candidate&&after.pending_admission_candidate,"actual hardware pending observation pairs");
    if(scenario==L"player-request"||scenario==L"late-ui")check(HwbpFixtureFetched==(scenario==L"player-request"?6:13)&&!after.pending_admission_candidate,"actual native request read-clear preserved");
    if(scenario==L"missing-site")check(receipt.error==hw::Error::MissingCapture&&!after.pending_admission_candidate,"missing hit not forged");
    if(scenario==L"null-toolbar")check(HwbpFixtureFetched==-1&&!after.pending_admission_candidate,"exact original null branch and pending rejection");
    if(scenario==L"wrong-user")check(receipt.error==hw::Error::WrongUser&&!observer_calls&&!after.pending_admission_candidate,"wrong native RSI cannot authorize");
    if(scenario==L"observer-fault")check(receipt.error==hw::Error::Observer&&receipt.exception_code==0xE0147101&&!after.pending_admission_candidate,"observer fault contained without success");
    if(scenario==L"repeat-site")check(receipt.error==hw::Error::Repeated&&receipt.observer_calls==1,"same native site repeat refused");
    if(scenario==L"stop-active")check(receipt.error==hw::Error::Stopped&&!observer_calls,"Stop declines observer but preserves native execution");
    if(scenario==L"arm-deadline")check(receipt.error==hw::Error::Deadline&&receipt.helper_deadline_exceeded&&receipt.restore_uncertain&&!receipt.entered&&!receipt.captured,"deadline cannot silently become success after cleanup join");
    if(scenario==L"foreign-finish")check(receipt.error==hw::Error::WrongThread&&receipt.restored&&!observer_calls,"foreign thread cannot restore; actual owner later cleans up");
    check(!receipt.queue_authorized&&!receipt.full_input_hold,"no drive authority");
    const auto prior=receipt;hw::Begin(provider,observe,nullptr,config.binding,999,reinterpret_cast<void*>(config.states[4]));hw::Snapshot(provider,receipt);check(receipt.error!=hw::Error::None,"attempt never rearms");receipt=prior;
    if(faultPage)VirtualFree(faultPage,0,MEM_RELEASE);
    std::printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"begin\":%s,\"kind\":%u,\"captured\":%u,\"restored\":%u,\"error\":%u,\"exception\":%lu,\"observer_calls\":%u,\"fetched\":%d,\"original_code_unchanged\":%s,\"game_access\":false}\n",scenario.c_str(),failures?"false":"true",failures,beginOk?"true":"false",unsigned(receipt.capture_kind),receipt.captured,receipt.restored,unsigned(receipt.error),exception,observer_calls,HwbpFixtureFetched,receipt.original_code_unchanged?"true":"false");
    return failures?1:0;
}
