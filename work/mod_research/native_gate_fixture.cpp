#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include "native_gate_fixture_code.h"

// This process never opens or calls the game. Buffers and executable pages are local.
alignas(16) static unsigned char manager[0xA0],effects[0xA0],pairs[0xD0];
static unsigned builds,processes,presentations;
static bool hasPairs,processProducesEffect;
template<class T> void setAt(unsigned char* p,unsigned offset,T value) {std::memcpy(p+offset,&value,sizeof(value));}
template<class T> T getAt(unsigned char* p,unsigned offset) {T v;std::memcpy(&v,p+offset,sizeof(v));return v;}
extern "C" void* effectAccessor() {return effects;}
extern "C" void* pairAccessor() {return pairs;}
extern "C" int buildStub(void* p) {if(p!=pairs)std::abort();builds++;return hasPairs?1:0;}
extern "C" int processStub(void* p) {if(p!=pairs)std::abort();processes++;if(processProducesEffect)setAt<uint32_t>(effects,0x98,1);return 1;}
extern "C" void presentStub(void* p) {if(p!=pairs)std::abort();presentations++;}
using Gate=int(*)(void*);
static void check(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
static void scenario(Gate f,const char* name,unsigned pending,uint64_t queued,bool available,bool newEffect,
                     unsigned expectedBuild,unsigned expectedProcess,unsigned expectedPresentation,int expectedReturn,unsigned expectedPending) {
    std::memset(manager,0,sizeof(manager));std::memset(effects,0,sizeof(effects));std::memset(pairs,0,sizeof(pairs));
    setAt<uint32_t>(manager,0x94,pending);setAt<uint64_t>(effects,0x38,queued);setAt<uint32_t>(effects,0x98,pending);
    hasPairs=available;processProducesEffect=newEffect;builds=processes=presentations=0;
    int result=f(manager);unsigned after=getAt<uint32_t>(manager,0x94);
    check(builds==expectedBuild&&processes==expectedProcess&&presentations==expectedPresentation&&result==expectedReturn&&after==expectedPending,"Unexpected native branch result");
    std::printf("{\"case\":\"%s\",\"result\":\"PASS\",\"pending_before\":%u,\"queued_effects\":%llu,\"build_calls\":%u,\"process_calls\":%u,\"presentation_calls\":%u,\"return_value\":%d,\"pending_after\":%u}\n",
                name,pending,queued,builds,processes,presentations,result,after);
}
int main() {
    unsigned char* local=nullptr;
    try {
        local=static_cast<unsigned char*>(VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
        check(local!=nullptr,"Local allocation failed");
        std::memcpy(local,originalCode,sizeof(originalCode));
        const uint64_t stubs[]={reinterpret_cast<uint64_t>(&effectAccessor),reinterpret_cast<uint64_t>(&pairAccessor),
            reinterpret_cast<uint64_t>(&buildStub),reinterpret_cast<uint64_t>(&processStub),reinterpret_cast<uint64_t>(&presentStub)};
        for(unsigned i=0;i<5;i++) {
            unsigned char* thunk=local+0x200+i*16;
            thunk[0]=0x48;thunk[1]=0xb8;std::memcpy(thunk+2,&stubs[i],8);thunk[10]=0xff;thunk[11]=0xe0;
        }
        for(const auto& p:callPatches) {
            check(local[p.offset]==0xe8,"Unexpected call opcode");
            int32_t rel=static_cast<int32_t>(0x200+p.target*16)-static_cast<int32_t>(p.offset+5);
            std::memcpy(local+p.offset+1,&rel,4);
        }
        DWORD old=0;check(VirtualProtect(local,4096,PAGE_EXECUTE_READ,&old)!=FALSE,"Local page protection failed");
        check(FlushInstructionCache(GetCurrentProcess(),local,4096)!=FALSE,"Local cache flush failed");
        Gate gate=reinterpret_cast<Gate>(local);
        scenario(gate,"clean-ready",0,0,true,false,1,1,1,0,0);
        scenario(gate,"pending-queue-empty",1,0,true,false,0,0,1,0,0);
        // Preserve that same manager for a second call: the first call only cleared its flag.
        builds=processes=presentations=0;
        int second=gate(manager);
        check(second==0&&builds==1&&processes==1&&presentations==1,"Second call did not resume normal processing");
        std::printf("{\"case\":\"second-call-after-clearing\",\"result\":\"PASS\",\"build_calls\":%u,\"process_calls\":%u}\n",builds,processes);
        scenario(gate,"pending-queue-nonempty",1,2,true,false,0,0,0,1,1);
        scenario(gate,"empty-pair-result",0,0,false,false,1,0,0,0,0);
        scenario(gate,"batch-produces-effect",0,0,true,true,1,1,0,1,1);
        VirtualFree(local,0,MEM_RELEASE);return 0;
    } catch(const std::exception& e) {
        std::fprintf(stderr,"Fixture failed: %s\n",e.what());
        if(local)VirtualFree(local,0,MEM_RELEASE);return 1;
    }
}
