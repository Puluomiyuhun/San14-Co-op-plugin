#include "human_rules_activation_v2.h"
#include "human_rules_activation_profile.h"
#include "human_rules_hook_transport.h"
#include "human_ai_runtime_profile.h"
#include "human_economy_runtime_profile.h"
#include <bcrypt.h>
#include <intrin.h>
#include <cstring>
#include <initializer_list>
#pragma comment(lib,"bcrypt.lib")
namespace ac=human_rules_activation;namespace ai=san14_ai_runtime;namespace eco=san14_economy_runtime;
using namespace human_rules_stage;
extern "C" __declspec(dllexport) Descriptor HumanRulesActivationDescriptor{};
extern "C" __declspec(dllexport) volatile LONG HumanRulesActivationState=ac::New;
extern "C" __declspec(dllexport) ac::Config HumanRulesActivationBinding{};
extern "C" __declspec(align(8)) void* volatile HumanRulesActivationIncomeTarget=nullptr;
#ifdef HUMAN_RULES_ACTIVATION_FIXTURE
HANDLE sealEntered=nullptr,sealContinue=nullptr;
extern "C" __declspec(dllexport) void HumanRulesActivationFixturePauseSeal(HANDLE entered,HANDLE proceed){sealEntered=entered;sealContinue=proceed;}
#endif
namespace {
volatile LONG&state=HumanRulesActivationState;volatile LONG firstFault=0;volatile LONG64 blocked=0,preCalls=0;DWORD error=0;
ac::Config&binding=HumanRulesActivationBinding;human_rules_hook::Prepared original{};HANDLE fatalEvent=nullptr;std::uint64_t mask=0;
LONG status(){return InterlockedCompareExchange(&state,0,0);}
template<class T>bool eq(std::uint64_t p,T wanted){T v{};return ai::ReadLocal(nullptr,p,&v,sizeof v)&&v==wanted;}
bool bytes(std::uint64_t p,const void*v,size_t n){unsigned char b[256]{};return n<=sizeof b&&ai::ReadLocal(nullptr,p,b,n)&&!memcmp(b,v,n);}
bool nonzero(const unsigned char*p,size_t n){unsigned all=0;for(size_t i=0;i<n;i++)all|=p[i];return all!=0;}
bool nativeSettings(){
 LONG guard=0;return ai::ReadLocal(nullptr,binding.image+0x1FD0C5C,&guard,4)&&guard!=0&&guard!=-1&&eq<unsigned>(binding.image+0x18EB628,binding.income_key5);
}
bool bindingCurrent(){
 unsigned option=0;return status()!=ac::Faulted&&eq(binding.image+0x1FCA1E0,binding.root)&&eq(binding.root+0x85130,binding.world)&&
 ai::ReadLocal(nullptr,binding.world+0x16A8,&option,4)&&((option>>8)&1)==binding.world_option8&&nativeSettings();
}
bool reader(void*,std::uint64_t p,void*out,size_t n)noexcept{return bindingCurrent()&&ai::ReadLocal(nullptr,p,out,n)&&bindingCurrent();}
// Permanent, non-alertable fatal retention. It never retries, returns Native,
// signals success, releases a Ready barrier, throws into game code, or exits the
// process. It can freeze the calling game thread/UI. Only process restart is
// supported recovery. Other threads already past these gates are NOT stopped.
__declspec(noreturn) void fatal(){
 InterlockedExchange(&state,ac::Faulted);InterlockedCompareExchange(&firstFault,LONG(GetCurrentThreadId()),0);InterlockedIncrement64(&blocked);
 for(;;){if(WaitForSingleObject(fatalEvent,INFINITE)!=WAIT_OBJECT_0)Sleep(INFINITE);}
}
void aiHold(void*,const ai::HeldCall&){fatal();}void incomeHold(void*,const eco::HeldCall&){fatal();}
bool humans(){
 for(unsigned i=0;i<2;++i){std::uint64_t f=0;if(!reader(nullptr,binding.root+0xDCA0+binding.force[i]*8,&f,8))return false;
 auto s=ai::ResolveSubject({nullptr,reader},{binding.image,binding.root,f,mask,ai::Route::Force});
 if(s.fault!=ai::Fault::None||s.decision!=ai::Decision::BypassHumanDecision||s.humans.main_district[binding.force[i]]!=binding.main_district[i])return false;}return true;
}
bool idle(){
 auto b=binding.image,m=b+0x19E7310;std::uint64_t stack=0,cache=0;
 if(!bindingCurrent()||!eq<std::uint64_t>(m+0x10,5)||!eq<std::uint64_t>(m+0x30,0)||!ai::ReadLocal(nullptr,m+0x20,&stack,8))return false;
 const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
 const std::uint64_t vt[]={0,0x12F22D8,0x12CC9B8,0x12CD400,0x12CC4A8};std::uint64_t states[5]{};
 for(unsigned i=0;i<5;++i){auto&s=states[i];if(!ai::ReadLocal(nullptr,stack+i*8,&s,8)||!s||!bytes(s+0x70,names[i],strlen(names[i])+1)||!eq<DWORD>(s+0x68,0)||(i&&!eq(s,b+vt[i]))||(i!=4&&!eq<std::uint64_t>(s+0x50,0)))return false;for(unsigned j=0;j<i;++j)if(s==states[j])return false;}
// world+165D is rank-table-derived UI array count (2BBBC0 -> min(rank+B3,5)),
 // not an idle/planning flag. It is intentionally absent from this gate.
 // m+48 is a transient dispatcher field, NOT persistent User identity. The
 // formal stack supplies User; idle UI requests are checked independently.
 auto user=states[4];std::uint64_t toolbar=0,panel=0,special=0,control=0,capacity=0,data=0;
 if(!ai::ReadLocal(nullptr,user+0x478,&toolbar,8)||!toolbar||!ai::ReadLocal(nullptr,states[2]+0x480,&panel,8)||!panel||
 !eq<LONG>(toolbar+0x88,-1)||!eq<DWORD>(states[2]+0x47C,0)||!eq<DWORD>(panel+0x1B0,0)||
 !ai::ReadLocal(nullptr,user+0x618,&control,8)||!control)return false;
 for(auto offset:{0x4A8,0x4B0,0x4B8})if(!eq<std::uint64_t>(user+offset,0))return false;
 if(!ai::ReadLocal(nullptr,b+0x201EC70,&special,8)||(special&&!eq<DWORD>(special,0))||!eq<DWORD>(b+0x1A38EC8+0x28,0)||!eq<DWORD>(b+0x19E7510+0x13C,1))return false;
 if(!ai::ReadLocal(nullptr,m+0x38,&capacity,8)||!ai::ReadLocal(nullptr,m+0x40,&data,8)||capacity>4096||((capacity==0)!=(data==0))||(data&&(data<0x10000||data>0x7FFFFFFFFFFFULL-capacity*16)))return false;
 return eq(binding.root,b+0x12AA6B0)&&eq(binding.world,b+0x12AA638)&&eq<DWORD>(states[4]+0x470,2)&&eq<WORD>(binding.world+0x34,WORD(binding.year))&&eq<BYTE>(binding.world+0x36,BYTE(binding.month))&&eq<BYTE>(binding.world+0x37,BYTE(binding.day))&&eq<BYTE>(binding.world+0x3A,BYTE(binding.viewer))&&eq<DWORD>(binding.world+0x40,1)&&
 ai::ReadLocal(nullptr,b+0x2025318,&cache,8)&&cache&&eq<LONG>(cache+0x3EC,-1)&&eq<DWORD>(cache+0x3F0,0)&&eq<DWORD>(cache+8,0);
}
bool sourceOriginal(){for(const auto&s:HumanRulesActivationDescriptor.sites)if(!bytes(s.address,s.expected,s.profile_size))return false;return true;}
bool settingsProfile(){
 for(const auto&a:human_rules_activation_profile::SettingsAnchors)if(!bytes(binding.image+a.rva,a.bytes,a.size))return false;return true;
}
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
void route(unsigned i,void*m,void*o){
 auto s=status();if(s==ac::Faulted)fatal();if(s!=ac::Sealed){if(s!=ac::Prepared)fatal();InterlockedIncrement64(&preCalls);reinterpret_cast<ai::Wrapper>(original.ai_originals[i])(m,o);return;}
 const ai::Wrapper f[]={HumanAiForceEntry,HumanAiDistrictEntry,HumanAiArmyEntry,HumanAiGroupEntry};f[i](m,o);
}
}
void HumanRulesActivationForce(void*m,void*o){route(0,m,o);}void HumanRulesActivationDistrict(void*m,void*o){route(1,m,o);}
void HumanRulesActivationArmy(void*m,void*o){route(2,m,o);}void HumanRulesActivationGroup(void*m,void*o){route(3,m,o);}
DWORD WINAPI HumanRulesActivationPrepare(void*input){
 if(InterlockedCompareExchange(&state,ac::Preparing,ac::New)!=ac::New)return ERROR_ALREADY_INITIALIZED;
 InterlockedExchange(&HumanRulesActivationDescriptor.preparation_state,Preparing);bool ok=false;
 __try{
 const auto c=*static_cast<const ac::Config*>(input);
 if(c.version!=1||c.size!=sizeof c||c.image<0x10000||c.image>0x7fffffffffffULL-0x2238000||!c.root||!c.world||!nonzero(c.room,16)||!nonzero(c.epoch,16)||!nonzero(c.rules_digest,32)||c.force[0]<1||c.force[0]>51||c.force[1]<1||c.force[1]>51||c.force[0]==c.force[1]||c.main_district[0]<1||c.main_district[0]>51||c.main_district[1]<1||c.main_district[1]>51||c.main_district[0]==c.main_district[1]||(c.viewer!=c.force[0]&&c.viewer!=c.force[1])||!c.year||c.year>65535||!c.month||c.month>12||(c.day!=1&&c.day!=11&&c.day!=21)||c.income_key5>3||c.world_option8>1){error=ERROR_INVALID_PARAMETER;__leave;}
 binding=c;mask=(std::uint64_t(1)<<c.force[0])|(std::uint64_t(1)<<c.force[1]);
 if(!settingsProfile()||!idle()||!humans()){error=ERROR_INVALID_DATA;__leave;}
 fatalEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);if(!fatalEvent){error=GetLastError();__leave;}
        MEMORY_BASIC_INFORMATION m{};
        if(VirtualQuery(reinterpret_cast<void*>(c.image+0xC6660),&m,sizeof m)!=sizeof m||!executable(m.Protect)||reinterpret_cast<std::uint64_t>(m.AllocationBase)!=c.image){error=ERROR_BAD_EXE_FORMAT;__leave;}
#ifdef HUMAN_RULES_ACTIVATION_FIXTURE
        if(m.Type!=MEM_PRIVATE){error=ERROR_BAD_EXE_FORMAT;__leave;}
        HumanRulesActivationDescriptor.fixture=1;
#else
        constexpr unsigned char wanted[]={0x42,0xd5,0x3b,0xb4,0x2c,0x03,0x3c,0x60,0x27,0xb6,0xda,0x75,0xe8,0x07,0x7f,0x41,0x70,0xf4,0xd6,0x84,0xab,0xb0,0xf5,0x74,0x83,0xa6,0x61,0x22,0x5d,0x05,0x20,0x25};
        if(m.Type!=MEM_IMAGE||c.image!=reinterpret_cast<std::uint64_t>(GetModuleHandleW(nullptr))||!hashModule(nullptr,wanted)){error=ERROR_BAD_EXE_FORMAT;__leave;}
#endif
        for(const auto&a:san14_economy_runtime::NativeAnchors)if(std::memcmp(reinterpret_cast<void*>(c.image+a.rva),a.bytes,a.size)){error=ERROR_REVISION_MISMATCH;__leave;}
        // Each failure above must leave the state terminal. The loop uses an
        // explicit error test because __leave exits its innermost try block.
        if(error)__leave;
        human_rules_hook::Config hc{};hc.image=c.image;
        void*entries[]={reinterpret_cast<void*>(&HumanRulesActivationForce),reinterpret_cast<void*>(&HumanRulesActivationDistrict),reinterpret_cast<void*>(&HumanRulesActivationArmy),reinterpret_cast<void*>(&HumanRulesActivationGroup)};
        for(unsigned i=0;i<4;++i)hc.ai_entries[i]=entries[i];hc.economy_entry=reinterpret_cast<void*>(&HumanRulesActivationIncome);
        if(!human_rules_hook::Prepare(hc,original)){error=ERROR_INVALID_DATA;__leave;}
        InterlockedExchangePointer(&HumanRulesActivationIncomeTarget,reinterpret_cast<void*>(c.image+0x2110B0));
        auto&d=HumanRulesActivationDescriptor;d.pid=GetCurrentProcessId();d.image=c.image;d.allocation=reinterpret_cast<std::uint64_t>(original.allocation);
        HMODULE module=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&HumanRulesActivationPrepare),&module)){error=GetLastError();__leave;}d.module=reinterpret_cast<std::uint64_t>(module);
        FILETIME times[4]{};if(!GetProcessTimes(GetCurrentProcess(),&times[0],&times[1],&times[2],&times[3])){error=GetLastError();__leave;}d.birth=(std::uint64_t(times[0].dwHighDateTime)<<32)|times[0].dwLowDateTime;
        if(BCryptGenRandom(nullptr,d.nonce,32,BCRYPT_USE_SYSTEM_PREFERRED_RNG)<0){error=ERROR_GEN_FAILURE;__leave;}
        for(unsigned i=0;i<6;++i){auto&s=d.sites[i];
            if(i<4){const auto&p=san14_ai_runtime::HookSites[i];s.address=c.image+p.original.rva;s.patch_size=p.instruction_prefix;s.profile_size=unsigned(p.original.size);s.destination=reinterpret_cast<std::uint64_t>(entries[i]);s.original_target=reinterpret_cast<std::uint64_t>(original.ai_originals[i]);std::memcpy(s.expected,p.original.bytes,s.profile_size);std::memset(s.replacement,0x90,s.patch_size);jump(s.replacement,s.destination);}
            else {const auto&p=san14_economy_runtime::Callsites[i-4];s.address=c.image+p.call_rva;s.patch_size=s.profile_size=5;s.destination=reinterpret_cast<std::uint64_t>(original.economy_relays[i-4]);s.original_target=c.image+0x2110B0;std::memcpy(s.expected,p.original,5);const auto delta=static_cast<std::int64_t>(s.destination)-static_cast<std::int64_t>(s.address+5);if(delta<INT32_MIN||delta>INT32_MAX){error=ERROR_ARITHMETIC_OVERFLOW;__leave;}s.replacement[0]=0xe8;auto rel=static_cast<std::int32_t>(delta);std::memcpy(s.replacement+1,&rel,4);}
            MEMORY_BASIC_INFORMATION current{};if(VirtualQuery(reinterpret_cast<void*>(s.address),&current,sizeof current)!=sizeof current){error=GetLastError();__leave;}s.protection=current.Protect;
        }

 if(error)__leave;
 ai::Config a{};a.reader={nullptr,reader};a.image=c.image;a.root=c.root;a.human_mask=mask;a.hold=aiHold;
 for(unsigned i=0;i<4;++i)a.original[i]=reinterpret_cast<ai::Wrapper>(original.ai_originals[i]);
 if(!ai::Configure(a)){error=ERROR_INVALID_DATA;__leave;}
 std::uint64_t epoch=0;std::memcpy(&epoch,c.epoch,8);if(!epoch)epoch=1;
 eco::Config e{};e.reader={nullptr,reader};e.image=c.image;e.root=c.root;e.rules={mask,epoch,1,true,true};e.hold=incomeHold;
 // flags derive from exact native settings comparison + supported image and
 // profile checks above. The room digest is binding data, never their proof.
 if(!eco::Configure(e)||!idle()||!humans()){error=ERROR_INVALID_DATA;__leave;}ok=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){error=GetExceptionCode();}
 if(InterlockedCompareExchange(&state,ok?ac::Prepared:ac::Rejected,ac::Preparing)!=ac::Preparing)ok=false;InterlockedExchange(&HumanRulesActivationDescriptor.preparation_state,ok?Prepared:Rejected);
 return ok?0:error?error:ERROR_INVALID_DATA;
}
DWORD WINAPI HumanRulesActivationSeal(void*input){
 if(InterlockedCompareExchange(&state,ac::Sealing,ac::Prepared)!=ac::Prepared)return ERROR_INVALID_STATE;
 bool ok=false;
 __try{const auto q=*static_cast<const ac::Seal*>(input);ai::Report a{};eco::Report e{};ai::Snapshot(a);eco::Snapshot(e);
 if(q.version!=1||q.size!=sizeof q||memcmp(q.nonce,HumanRulesActivationDescriptor.nonce,32)||memcmp(q.room,binding.room,16)||memcmp(q.epoch,binding.epoch,16)||a.active||a.exits||e.entries||InterlockedCompareExchange64(&preCalls,0,0)||!sourceOriginal()||!idle()||!humans())__leave;
#ifdef HUMAN_RULES_ACTIVATION_FIXTURE
 if(sealEntered&&sealContinue){SetEvent(sealEntered);WaitForSingleObject(sealContinue,INFINITE);}
#endif
 InterlockedExchangePointer(&HumanRulesActivationIncomeTarget,reinterpret_cast<void*>(HumanEconomyIncomePredicate));ok=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){error=GetExceptionCode();}
 if(!ok){InterlockedCompareExchange(&state,ac::Rejected,ac::Sealing);return ERROR_INVALID_DATA;}
 // Descriptor final policy bit is published before final Sealed state. External
 // installer must require Sealed via ReadReport both sides of its copy.
 HumanRulesActivationDescriptor.policy_enabled=1;if(InterlockedCompareExchange(&state,ac::Sealed,ac::Sealing)!=ac::Sealing)return ERROR_OPERATION_ABORTED;return 0;
}
DWORD WINAPI HumanRulesActivationRevoke(void*input){
 __try{const auto q=*static_cast<const ac::Seal*>(input);if(q.version!=1||q.size!=sizeof q||memcmp(q.nonce,HumanRulesActivationDescriptor.nonce,32)||memcmp(q.room,binding.room,16)||memcmp(q.epoch,binding.epoch,16))return ERROR_INVALID_DATA;
 const auto s=status();if(s!=ac::Sealed&&s!=ac::Faulted)return ERROR_INVALID_STATE;InterlockedExchange(&state,ac::Faulted);return 0;
 }__except(EXCEPTION_EXECUTE_HANDLER){return GetExceptionCode();}
}
DWORD WINAPI HumanRulesActivationReadReport(void*output){
 auto&r=*static_cast<ac::Report*>(output);r={};r.state=status();
 if(r.state==ac::Prepared||r.state==ac::Sealed||r.state==ac::Faulted||r.state==ac::Rejected){r.binding=binding;r.error=error;}
 r.blocked=InterlockedCompareExchange64(&blocked,0,0);r.first_fault_thread=DWORD(InterlockedCompareExchange(&firstFault,0,0));ai::Snapshot(r.ai);eco::Snapshot(r.income);return 0;
}
