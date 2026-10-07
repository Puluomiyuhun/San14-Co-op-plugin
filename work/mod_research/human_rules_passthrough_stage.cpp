#include "human_rules_passthrough_stage.h"
#include "human_rules_hook_transport.h"
#include "human_ai_runtime_profile.h"
#include "human_economy_runtime_profile.h"
#include <bcrypt.h>
#include <intrin.h>
#include <cstring>
#include <limits>
#pragma comment(lib,"bcrypt.lib")
#ifdef HUMAN_RULES_STAGE_FIXTURE
#include "human_rules_stage_fixture_image_profile.h"
#endif
using namespace human_rules_stage;
extern "C" __declspec(dllexport) Descriptor HumanRulesStageDescriptor{};
namespace {
volatile LONG state=New;DWORD error=0;
volatile LONG64 enters[6]{},exits[6]{},active=0,abnormal=0,unexpected=0;
human_rules_hook::Prepared original{};
using Ai=void(*)(void*,void*);using Income=int(*)(void*);
Income income=nullptr;
bool executable(DWORD p){return p==PAGE_EXECUTE_READ||p==PAGE_EXECUTE_READWRITE||p==PAGE_EXECUTE_WRITECOPY;}
bool hashModule(HMODULE module,const unsigned char*wanted){
    wchar_t path[32768]{};if(!GetModuleFileNameW(module,path,32768))return false;
    HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(f==INVALID_HANDLE_VALUE)return false;
    BCRYPT_ALG_HANDLE a=nullptr;BCRYPT_HASH_HANDLE h=nullptr;bool ok=false;
    if(BCryptOpenAlgorithmProvider(&a,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0&&BCryptCreateHash(a,&h,nullptr,0,nullptr,0,0)>=0){
        ok=true;unsigned char buffer[65536],digest[32]{};DWORD n=0;
        for(;;){if(!ReadFile(f,buffer,sizeof buffer,&n,nullptr)){ok=false;break;}if(!n)break;if(BCryptHashData(h,buffer,n,0)<0){ok=false;break;}}
        if(ok)ok=BCryptFinishHash(h,digest,32,0)>=0;
        ok=ok&&!std::memcmp(digest,wanted,32);
    }
    if(h)BCryptDestroyHash(h);if(a)BCryptCloseAlgorithmProvider(a,0);CloseHandle(f);return ok;
}
void jump(unsigned char*out,std::uint64_t address){out[0]=0xff;out[1]=0x25;std::memset(out+2,0,4);std::memcpy(out+6,&address,8);}
void call(unsigned n,void*manager,void*subject){
    if(InterlockedCompareExchange(&state,0,0)!=Prepared||!original.ai_originals[n])__fastfail(FAST_FAIL_INVALID_ARG);
    InterlockedIncrement64(&enters[n]);InterlockedIncrement64(&active);
    __try{reinterpret_cast<Ai>(original.ai_originals[n])(manager,subject);}
    __finally{if(AbnormalTermination())InterlockedIncrement64(&abnormal);InterlockedDecrement64(&active);InterlockedIncrement64(&exits[n]);}
}
}
void HumanRulesStageForce(void*m,void*s){call(0,m,s);}
void HumanRulesStageDistrict(void*m,void*s){call(1,m,s);}
void HumanRulesStageArmy(void*m,void*s){call(2,m,s);}
void HumanRulesStageGroup(void*m,void*s){call(3,m,s);}
int HumanRulesStageIncome(void*force){
    if(InterlockedCompareExchange(&state,0,0)!=Prepared||!income)__fastfail(FAST_FAIL_INVALID_ARG);
    auto caller=reinterpret_cast<std::uint64_t>(_ReturnAddress());unsigned route=6;
    for(unsigned i=0;i<2;++i)if(caller==HumanRulesStageDescriptor.image+san14_economy_runtime::Callsites[i].return_rva)route=4+i;
    if(route<6)InterlockedIncrement64(&enters[route]);else InterlockedIncrement64(&unexpected);
    InterlockedIncrement64(&active);int result=0;
    __try{result=income(force);}
    __finally{if(AbnormalTermination())InterlockedIncrement64(&abnormal);InterlockedDecrement64(&active);if(route<6)InterlockedIncrement64(&exits[route]);}
    return result;
}
DWORD WINAPI HumanRulesStagePrepare(void*input){
    if(InterlockedCompareExchange(&state,Preparing,New)!=New)return ERROR_ALREADY_INITIALIZED;
    InterlockedExchange(&HumanRulesStageDescriptor.preparation_state,Preparing);
    bool ok=false;
    __try{
        auto c=*static_cast<const Config*>(input);
        if(c.magic!=Magic||c.version!=1||c.size!=sizeof(Config)||c.image<0x10000||c.image>0x7fffffffffffULL-0x2238000){error=ERROR_INVALID_PARAMETER;__leave;}
        MEMORY_BASIC_INFORMATION m{};
        if(VirtualQuery(reinterpret_cast<void*>(c.image+0xC6660),&m,sizeof m)!=sizeof m||!executable(m.Protect)||reinterpret_cast<std::uint64_t>(m.AllocationBase)!=c.image){error=ERROR_BAD_EXE_FORMAT;__leave;}
#ifdef HUMAN_RULES_STAGE_FIXTURE
        if(m.Type!=MEM_PRIVATE&&(m.Type!=MEM_IMAGE||c.image!=0x10000000||!hashModule(reinterpret_cast<HMODULE>(c.image),FixtureImageSha))){error=ERROR_BAD_EXE_FORMAT;__leave;}
        HumanRulesStageDescriptor.fixture=1;
#else
        constexpr unsigned char wanted[]={0x42,0xd5,0x3b,0xb4,0x2c,0x03,0x3c,0x60,0x27,0xb6,0xda,0x75,0xe8,0x07,0x7f,0x41,0x70,0xf4,0xd6,0x84,0xab,0xb0,0xf5,0x74,0x83,0xa6,0x61,0x22,0x5d,0x05,0x20,0x25};
        if(m.Type!=MEM_IMAGE||c.image!=reinterpret_cast<std::uint64_t>(GetModuleHandleW(nullptr))||!hashModule(nullptr,wanted)){error=ERROR_BAD_EXE_FORMAT;__leave;}
#endif
        for(const auto&a:san14_economy_runtime::NativeAnchors)if(std::memcmp(reinterpret_cast<void*>(c.image+a.rva),a.bytes,a.size)){error=ERROR_REVISION_MISMATCH;__leave;}
        // Each failure above must leave the state terminal. The loop uses an
        // explicit error test because __leave exits its innermost try block.
        if(error)__leave;
        human_rules_hook::Config hc{};hc.image=c.image;
        void*entries[]={reinterpret_cast<void*>(&HumanRulesStageForce),reinterpret_cast<void*>(&HumanRulesStageDistrict),reinterpret_cast<void*>(&HumanRulesStageArmy),reinterpret_cast<void*>(&HumanRulesStageGroup)};
        for(unsigned i=0;i<4;++i)hc.ai_entries[i]=entries[i];hc.economy_entry=reinterpret_cast<void*>(&HumanRulesStageIncome);
        if(!human_rules_hook::Prepare(hc,original)){error=ERROR_INVALID_DATA;__leave;}
        income=reinterpret_cast<Income>(c.image+0x2110B0);
        auto&d=HumanRulesStageDescriptor;d.pid=GetCurrentProcessId();d.image=c.image;d.allocation=reinterpret_cast<std::uint64_t>(original.allocation);
        HMODULE module=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&HumanRulesStagePrepare),&module)){error=GetLastError();__leave;}d.module=reinterpret_cast<std::uint64_t>(module);
        FILETIME times[4]{};if(!GetProcessTimes(GetCurrentProcess(),&times[0],&times[1],&times[2],&times[3])){error=GetLastError();__leave;}d.birth=(std::uint64_t(times[0].dwHighDateTime)<<32)|times[0].dwLowDateTime;
        if(BCryptGenRandom(nullptr,d.nonce,32,BCRYPT_USE_SYSTEM_PREFERRED_RNG)<0){error=ERROR_GEN_FAILURE;__leave;}
        for(unsigned i=0;i<6;++i){auto&s=d.sites[i];
            if(i<4){const auto&p=san14_ai_runtime::HookSites[i];s.address=c.image+p.original.rva;s.patch_size=p.instruction_prefix;s.profile_size=unsigned(p.original.size);s.destination=reinterpret_cast<std::uint64_t>(entries[i]);s.original_target=reinterpret_cast<std::uint64_t>(original.ai_originals[i]);std::memcpy(s.expected,p.original.bytes,s.profile_size);std::memset(s.replacement,0x90,s.patch_size);jump(s.replacement,s.destination);}
            else {const auto&p=san14_economy_runtime::Callsites[i-4];s.address=c.image+p.call_rva;s.patch_size=s.profile_size=5;s.destination=reinterpret_cast<std::uint64_t>(original.economy_relays[i-4]);s.original_target=c.image+0x2110B0;std::memcpy(s.expected,p.original,5);const auto delta=static_cast<std::int64_t>(s.destination)-static_cast<std::int64_t>(s.address+5);if(delta<INT32_MIN||delta>INT32_MAX){error=ERROR_ARITHMETIC_OVERFLOW;__leave;}s.replacement[0]=0xe8;auto rel=static_cast<std::int32_t>(delta);std::memcpy(s.replacement+1,&rel,4);}
            MEMORY_BASIC_INFORMATION current{};if(VirtualQuery(reinterpret_cast<void*>(s.address),&current,sizeof current)!=sizeof current){error=GetLastError();__leave;}s.protection=current.Protect;
        }
        if(error)__leave;ok=true;
    }__except(EXCEPTION_EXECUTE_HANDLER){error=GetExceptionCode();}
    InterlockedExchange(&state,ok?Prepared:Rejected);
    InterlockedExchange(&HumanRulesStageDescriptor.preparation_state,ok?Prepared:Rejected);
    return ok?ERROR_SUCCESS:error?error:ERROR_INVALID_DATA;
}
void HumanRulesStageSnapshot(Report*out)noexcept{
    if(!out)return;*out={};out->state=InterlockedCompareExchange(&state,0,0);
    // Interlocked terminal publication orders the one writer's final error.
    // While Preparing, do not race that writer's non-atomic field.
    if(out->state==Prepared||out->state==Rejected)out->error=error;
    for(unsigned i=0;i<6;++i){out->counters.entered[i]=InterlockedCompareExchange64(&enters[i],0,0);out->counters.exited[i]=InterlockedCompareExchange64(&exits[i],0,0);}
    out->counters.active=InterlockedCompareExchange64(&active,0,0);out->counters.abnormal=InterlockedCompareExchange64(&abnormal,0,0);out->counters.unexpected_income_caller=InterlockedCompareExchange64(&unexpected,0,0);
}
