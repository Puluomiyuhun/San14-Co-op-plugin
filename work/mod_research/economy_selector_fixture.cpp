#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <intrin.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <stdexcept>
#include <initializer_list>
#include "economy_selector_fixture_code.h"
#include "../../outputs/san14-link/human_economy_policy.h"
using namespace san14_link;
// This program allocates only its own memory and never opens a game process.
alignas(16) static unsigned char root[0x86000],world[0x1700],forces[52][0x1D0];
static uintptr_t forceVtable[13];
static unsigned char* code;
static unsigned viewer,difficulty,hookCalls,stubCalls;
static bool adapted;
static EconomyRules rules{(uint64_t(1)<<2)|(uint64_t(1)<<12),7,1,true,true};
using Predicate=int(*)(void*);
using Selector=int(*)(void*,int);
static Predicate nativePredicate;
template<class T> static void wr(void* p,size_t o,T v){std::memcpy(static_cast<char*>(p)+o,&v,sizeof v);}
static void check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
// Stub mistakes abort instead of unwinding through dynamically copied code.
static void boundary(bool ok){if(!ok)std::abort();++stubCalls;}
static void* regionForce(void* p){boundary(p!=nullptr);return *static_cast<void**>(p);}
static void* settingsRoot(){++stubCalls;return &difficulty;}
static void* settingsValue(void* p){boundary(p==&difficulty);return p;}
static void settingsCopy(void* dest,void* source){boundary(dest&&source==&difficulty);wr(dest,0,difficulty);}
static int settingsRead(void* p,unsigned key){boundary(p&&key==5);unsigned v;std::memcpy(&v,p,sizeof v);boundary(v==difficulty);return int(v);}
static void settingsDestroy(void* p){boundary(p!=nullptr);}
__declspec(noinline) static int routedPredicate(void* force){
    const auto at=reinterpret_cast<uintptr_t>(_ReturnAddress())-reinterpret_cast<uintptr_t>(code);
    uint32_t original=0;for(const auto& c:callers)if(c.offset==at)original=c.rva;
    boundary(original!=0);++hookCalls;
    if(!adapted)return nativePredicate(force);
    const auto delta=reinterpret_cast<uintptr_t>(force)-reinterpret_cast<uintptr_t>(forces);
    boundary(delta%0x1D0==0 && delta/0x1D0<52);
    const EconomySubject subject{unsigned(delta/0x1D0),viewer,7,true};
    switch(economy_predicate(rules,original,subject)){
        case EconomyPredicate::NativeLocal:return nativePredicate(force);
        case EconomyPredicate::RoomHuman:return 1;
        case EconomyPredicate::RoomAI:return 0;
        default:std::abort();
    }
}
static void putThunk(unsigned offset,uintptr_t target){code[offset]=0x48;code[offset+1]=0xB8;wr(code,offset+2,target);code[offset+10]=0xFF;code[offset+11]=0xE0;}
static void putWrapper(unsigned slot,unsigned body,unsigned length,bool second){
    // Preserve all nonvolatile registers used by the copied tails and provide
    // aligned shadow/local space for the explicit settings stubs.
    const unsigned char prefix[]={0x53,0x56,0x57,0x41,0x56,0x48,0x81,0xEC,0xA8,0x01,0,0,0x49,0x89,0xCE};
    std::memcpy(code+slot,prefix,sizeof prefix);unsigned n=slot+sizeof prefix;
    code[n++]=0x89;code[n++]=second?0xD3:0xD6; // base -> EBX (1) or ESI (0)
    if(second){code[n++]=0xBE;wr(code,n,uint32_t(100));n+=4;}
    code[n++]=0xE9;wr(code,n,int32_t(body)-int32_t(n+4));
    const unsigned char suffix[]={0x89,0xD8,0x48,0x81,0xC4,0xA8,0x01,0,0,0x41,0x5E,0x5F,0x5E,0x5B,0xC3};
    std::memcpy(code+body+length,suffix,sizeof suffix);
}
static unsigned negativeChecks(){
    unsigned count=0;
    const EconomySubject valid{2,viewer,7,true};
    auto hold=[&](EconomyRules r,EconomySubject s){
        for(uint32_t site:{0x28DE76u,0x28DAAAu}){
            check(economy_predicate(r,site,s)==EconomyPredicate::Hold,"unsafe selector context not held");++count;
        }
    };
    auto r=rules;r.human_force_mask=0;hold(r,valid);
    r=rules;r.human_force_mask=uint64_t(1)<<viewer;hold(r,valid);
    r=rules;r.human_force_mask|=uint64_t(1)<<8;hold(r,valid);
    r=rules;r.human_force_mask=(uint64_t(1)<<viewer)|1;hold(r,valid);
    r=rules;r.human_force_mask=(uint64_t(1)<<viewer)|(uint64_t(1)<<63);hold(r,valid);
    r=rules;r.binding_epoch=0;hold(r,valid);
    r=rules;r.binding_epoch=8;hold(r,valid);
    r=rules;r.version=2;hold(r,valid);
    r=rules;r.shared_settings_verified=false;hold(r,valid);
    r=rules;r.native_profile_verified=false;hold(r,valid);
    auto s=valid;s.identity_verified=false;hold(rules,s);
    s=valid;s.force_id=0;hold(rules,s);
    s=valid;s.force_id=52;hold(rules,s);
    s=valid;s.local_viewer_id=0;hold(rules,s);
    s=valid;s.local_viewer_id=52;hold(rules,s);
    s=valid;s.local_viewer_id=8;hold(rules,s);
    for(uint32_t other:{0u,0x28DE71u,0x28DAA5u,0x3F6B0Fu}){
        check(economy_predicate(rules,other,valid)==EconomyPredicate::NativeLocal,"unclassified caller redirected");++count;
    }
    return count;
}
int main(int argc,char** argv){
    FILE* output=nullptr;
    try{
        check(argc==3,"usage: economy_selector_fixture viewer output.json");
        viewer=unsigned(std::strtoul(argv[1],nullptr,10));check(viewer==2||viewer==12,"invalid viewer");
        code=static_cast<unsigned char*>(VirtualAlloc(nullptr,0xB000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));check(code,"allocation");
        for(const auto& b:blocks)std::memcpy(code+b.offset,b.bytes,b.size);
        for(const auto& s:slots){std::memcpy(code+s.offset,s.bytes,8);if(s.rva==0x1FCA1E0)wr(code,s.offset,reinterpret_cast<uintptr_t>(root));}
        for(const auto& p:patches)wr(code,p.at,int32_t(p.target)-int32_t(p.next));
        const uintptr_t hooks[]={uintptr_t(&regionForce),uintptr_t(&settingsRoot),uintptr_t(&settingsValue),
            uintptr_t(&settingsCopy),uintptr_t(&settingsRead),uintptr_t(&settingsDestroy),uintptr_t(&routedPredicate)};
        for(unsigned i=0;i<7;++i)putThunk(0x8000+i*0x20,hooks[i]);
        putWrapper(0,fn_component0,sizeof bytes_component0,false);
        putWrapper(0x1000,fn_component1,sizeof bytes_component1,true);
        forceVtable[12]=uintptr_t(code+fn_force_id);wr(root,0x85130,uintptr_t(world));
        for(unsigned i=0;i<52;++i){wr(root,0xDCA0+i*8,uintptr_t(forces[i]));wr(forces[i],0,uintptr_t(forceVtable));}
        world[0x3A]=static_cast<unsigned char>(viewer);
        DWORD old;check(VirtualProtect(code,0xA000,PAGE_EXECUTE_READ,&old)!=FALSE,"code protection");
        check(FlushInstructionCache(GetCurrentProcess(),code,0xA000)!=FALSE,"cache flush");
        nativePredicate=reinterpret_cast<Predicate>(code+fn_is_player);
        const unsigned holds=negativeChecks();
        check(fopen_s(&output,argv[2],"wb")==0&&output,"output file");
        std::fprintf(output,"{\"viewer\":%u,\"pid\":%lu,\"rows\":[",viewer,GetCurrentProcessId());
        unsigned checked=0,menus=0;
        for(unsigned component=0;component<2;++component)for(difficulty=0;difficulty<=5;++difficulty)
            for(unsigned force=1;force<=51;++force)for(int base:{-101,0,1,99,100,101,2000,10000}){
                void* region=forces[force];auto fn=reinterpret_cast<Selector>(code+component*0x1000);
                const auto rate=[&](bool human){return human?(difficulty<4?originalRates[component][difficulty]:100):
                    (difficulty==3?originalRates[component][4]:difficulty>=4?originalRates[component][5]:100);};
                adapted=false;const int original=fn(&region,base);
                check(original==base*rate(force==viewer)/100,"copied native percentage mismatch");
                adapted=true;const int shared=fn(&region,base);
                check(shared==base*rate(force==2||force==12)/100,"room selector percentage mismatch");
                check(world[0x3A]==viewer,"viewer identity changed");
                std::fprintf(output,"%s[%u,%u,%u,%d,%d,%d]",checked?",":"",component,difficulty,force,base,original,shared);++checked;
            }
        for(unsigned force=1;force<=51;++force){check(nativePredicate(forces[force])==int(force==viewer),"native UI identity leaked to remote force");++menus;}
        check(hookCalls==2*checked,"native call count mismatch");
        std::fprintf(output,"],\"result\":\"PASS\",\"cases\":%u,\"guard_cases\":%u,\"native_local_predicate_cases\":%u,\"hook_calls\":%u,\"stub_calls\":%u,\"game_access\":false,\"full_city_calculation\":false}\n",checked,holds,menus,hookCalls,stubCalls);
        fclose(output);output=nullptr;
        std::printf("{\"result\":\"PASS\",\"viewer\":%u,\"cases\":%u,\"guard_cases\":%u,\"local_predicates\":%u,\"game_access\":false}\n",viewer,checked,holds,menus);
        VirtualFree(code,0,MEM_RELEASE);return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"FAILED: %s\n",e.what());if(output)fclose(output);if(code)VirtualFree(code,0,MEM_RELEASE);return 1;}
}
