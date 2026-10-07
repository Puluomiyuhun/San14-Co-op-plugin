#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <thread>
#include <mutex>
#include <vector>
#include <atomic>
#include <climits>
#include "native_rng_fixture_code.h"
#include "observed_rng_states_fixture.h"

static void check(bool v,const char* text){if(!v)throw std::runtime_error(text);}
static uint32_t rotate(uint32_t x){return (x<<16)|(x>>16);}
static uint32_t referenceNext(uint32_t x){
    unsigned n=(x&15)+1;
    while(n--)x=rotate((x-123u)*0x693d4b5u+123456u);
    return rotate(x*0x41c64e6du+12345u);
}
class NativeRng {
    unsigned char* code=nullptr;
    std::vector<unsigned char> rootData,worldData;
public:
    explicit NativeRng(uint32_t state){
        code=(unsigned char*)VirtualAlloc(nullptr,8192,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
        check(code!=nullptr,"private allocation");std::memcpy(code,nativeRngCode,4096);
        DWORD old;check(VirtualProtect(code,4096,PAGE_EXECUTE_READ,&old)!=0,"code protection");
        check(FlushInstructionCache(GetCurrentProcess(),code,4096)!=0,"instruction cache");set(state);
    }
    NativeRng(const NativeRng&)=delete;NativeRng& operator=(const NativeRng&)=delete;
    ~NativeRng(){if(code)VirtualFree(code,0,MEM_RELEASE);}
    uint32_t get(){return reinterpret_cast<uint32_t(*)()>(code)();}
    void set(uint32_t n){reinterpret_cast<void(*)(uint32_t)>(code+0x40)(n);}
    int unbounded(){return reinterpret_cast<int(*)()>(code+0x80)();}
    int percentage(int n){return reinterpret_cast<int(*)(int)>(code+0x100)(n);}
    int range(int n){return reinterpret_cast<int(*)(int)>(code+0x200)(n);}
    int derivedPercentage(int threshold,int salt,uint32_t worldValue){
        if(rootData.empty()){rootData.resize(0x85138);worldData.resize(0x458);}
        auto rootPtr=rootData.data();auto worldPtr=worldData.data();
        std::memcpy(code+0x1010,&rootPtr,8);std::memcpy(rootPtr+0x85130,&worldPtr,8);
        std::memcpy(worldPtr+0x454,&worldValue,4);
        return reinterpret_cast<int(*)(int,int)>(code+0x300)(threshold,salt);
    }
};
enum class Domain { Logic, Presentation };
static thread_local Domain currentDomain=Domain::Logic;
class Scope {
    Domain old;
public:
    explicit Scope(Domain d):old(currentDomain){currentDomain=d;}
    ~Scope(){currentDomain=old;}
    Scope(const Scope&)=delete;Scope& operator=(const Scope&)=delete;
};
class Router {
    NativeRng logic,visual;std::mutex logicLock,visualLock;
public:
    Router(uint32_t a,uint32_t b):logic(a),visual(b){}
    int draw(unsigned kind,int n){
        bool v=currentDomain==Domain::Presentation;
        std::lock_guard<std::mutex> guard(v?visualLock:logicLock);
        auto& r=v?visual:logic;
        return kind==0?r.range(n):kind==1?r.percentage(n):r.unbounded();
    }
    uint32_t state(Domain d){std::lock_guard<std::mutex> guard(d==Domain::Logic?logicLock:visualLock);return d==Domain::Logic?logic.get():visual.get();}
};
static void passed(const char* name,unsigned n=1){std::printf("{\"case\":\"%s\",\"checks\":%u,\"result\":\"PASS\"}\n",name,n);}
static unsigned long long digest(unsigned long long h,uint32_t v){return (h^v)*1099511628211ULL;}

int main(){try{
    NativeRng captured(observedWrites[0].before);unsigned replayed=0;
    for(const auto& row:observedWrites){
        check(captured.get()==row.before,"recorded trace prior-state mismatch");
        if(row.sameValue)captured.set(row.after);else captured.unbounded();
        check(captured.get()==row.after,"recorded native state transition mismatch");replayed++;
    }passed("real-near-trace-state-sequence-native-replay",replayed);
    const uint32_t seeds[]={0,1,0xffffffff,0x80000000,4136155758u,3823646826u,1138287528u};
    unsigned checks=0;
    for(auto seed:seeds){NativeRng r(seed);uint32_t expected=seed;
        for(unsigned i=0;i<500;i++){
            expected=referenceNext(expected);int v=r.unbounded();
            check(r.get()==expected&&uint32_t(v)==(expected&0x7fffffff),"native recurrence mismatch");checks++;
        }
    }passed("native-unbounded-recurrence",checks);
    const int ranges[]={INT_MIN,-1,0,1,2,3,100,INT_MAX};checks=0;
    for(auto seed:seeds)for(auto n:ranges){NativeRng r(seed);int actual=r.range(n);uint32_t expected=n<2?seed:referenceNext(seed);
        check(r.get()==expected,"range state");check(actual==(n<2?0:int((expected&0x7fffffff)%uint32_t(n))),"range output");checks++;
    }passed("range-boundaries-and-no-draw-below-two",checks);
    const int thresholds[]={INT_MIN,-1,0,1,50,99,100,101,INT_MAX};checks=0;
    for(auto seed:seeds)for(auto n:thresholds){NativeRng r(seed);int actual=r.percentage(n);auto next=referenceNext(seed);
        check(r.get()==next,"percentage always advances");check(actual==(int((next&0x7fffffff)%100)<n),"percentage output");checks++;
    }passed("percentage-boundaries-still-consume",checks);

    checks=0;
    for(auto seed:seeds){NativeRng r(seed);
        for(int salt=-16;salt<16;salt++){
            auto derived=referenceNext(seed+uint32_t(salt)+220u);
            int actual=r.derivedPercentage(40,salt,220);
            check(actual==(int((derived&0x7fffffff)%100)<40),"derived probability input relation");
            check(r.get()==seed,"derived probability unexpectedly wrote seed");checks++;
        }
    }passed("native-derived-probability-reads-seed-without-writing",checks);
    NativeRng baseQuery(3823646826u),changedQuery(3823646826u);changedQuery.range(3);
    unsigned changedQueries=0;
    for(int salt=0;salt<128;salt++)if(baseQuery.derivedPercentage(50,salt,220)!=changedQuery.derivedPercentage(50,salt,220))changedQueries++;
    check(changedQueries>0,"read-only-query negative control ineffective");
    std::printf("{\"case\":\"one-extra-shared-draw-changes-read-only-queries\",\"checks\":128,\"changed_queries\":%u,\"result\":\"PASS\"}\n",changedQueries);

    // Isolated RNG scheduling experiment, NOT a replay of the game's battle logic.
    Router a(3823646826u,123),b(3823646826u,456);NativeRng sharedA(3823646826u),sharedB(3823646826u);
    unsigned differences=0;unsigned long long ha=1469598103934665603ULL,hb=ha;
    for(unsigned i=0;i<600;i++){
        {Scope visual(Domain::Presentation);for(unsigned j=0;j<i%7;j++){a.draw(j%3,3);sharedA.range(3);}for(unsigned j=0;j<(i*5+3)%11;j++){b.draw(j%3,5);sharedB.range(5);}}
        int va=a.draw(i%3,37),vb=b.draw(i%3,37);check(va==vb,"isolated logical output diverged");
        ha=digest(ha,uint32_t(va));hb=digest(hb,uint32_t(vb));
        if(sharedA.range(1000003)!=sharedB.range(1000003))differences++;
    }
    check(a.state(Domain::Logic)==b.state(Domain::Logic)&&ha==hb,"isolated final state");check(differences>0,"shared-stream negative control ineffective");
    std::printf("{\"case\":\"two-client-synthetic-draw-schedule\",\"checks\":600,\"logical_hash_a\":%llu,\"logical_hash_b\":%llu,\"shared_stream_divergent_outputs\":%u,\"result\":\"PASS\"}\n",ha,hb,differences);

    auto before=a.state(Domain::Logic);auto visualBefore=a.state(Domain::Presentation);
    try{Scope outer(Domain::Presentation);a.draw(0,3);{Scope inner(Domain::Presentation);a.draw(1,40);}throw std::runtime_error("test unwind");}catch(const std::runtime_error&){}
    check(currentDomain==Domain::Logic&&a.state(Domain::Logic)==before,"domain leaked through exception");
    check(a.state(Domain::Presentation)!=visualBefore,"visual calls missing");a.draw(0,3);check(a.state(Domain::Logic)==referenceNext(before),"default domain is not logic");
    passed("nested-scope-exception-and-conservative-default",4);

    Router concurrent(1138287528u,2468);NativeRng reference(1138287528u);std::atomic<bool> start{false};std::atomic<unsigned> visualCalls{0};
    std::thread t1([&]{while(!start.load())std::this_thread::yield();Scope scope(Domain::Presentation);for(unsigned i=0;i<4000;i++){concurrent.draw(i%3,51);visualCalls++;}});
    std::thread t2([&]{while(!start.load())std::this_thread::yield();Scope scope(Domain::Presentation);for(unsigned i=0;i<4000;i++){concurrent.draw(i%3,99);visualCalls++;}});
    start=true;bool equal=true;
    for(unsigned i=0;i<4000;i++){int x=concurrent.draw(0,123);int y=reference.range(123);equal=equal&&x==y;}
    t1.join();t2.join();check(equal&&visualCalls==8000&&concurrent.state(Domain::Logic)==reference.get(),"concurrent domains crossed");
    passed("two-presentation-workers-do-not-change-one-logic-stream",12000);

    // Deterministic interleaving demonstrates why saving/restoring a GLOBAL seed is unsafe.
    NativeRng unsafe(4136155758u),correct(4136155758u);auto saved=unsafe.get();
    unsafe.range(5);unsafe.range(97); // visual draw, then a legitimate logical draw
    unsafe.set(saved);correct.range(97); // naive visual cleanup erased the intervening logical state
    check(unsafe.get()!=correct.get(),"save-restore negative control ineffective");
    passed("global-save-restore-erases-interleaved-logical-draw");
    return 0;
}catch(const std::exception& e){std::fprintf(stderr,"RNG isolation fixture failed: %s\n",e.what());return 1;}}
