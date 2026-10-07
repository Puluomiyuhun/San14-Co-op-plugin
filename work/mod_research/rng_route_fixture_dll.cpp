#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <atomic>
#include "rng_route_fixture_api.h"

static RouteConfig config{};
// -1 means configuration is being replaced; nonnegative values count calls.
static std::atomic<long> active{0};
static thread_local unsigned depth=0;
static SRWLOCK private_lock=SRWLOCK_INIT;
static uint32_t presentation_seed=0;
static volatile LONG64 text_calls=0, expression_native=0, expression_private=0;
static volatile LONG64 voice_native=0, voice_private=0, private_advances=0;

static void enter(){
    long n=active.load();
    for(;;){
        if(n<0){SwitchToThread();n=active.load();continue;}
        if(active.compare_exchange_weak(n,n+1))return;
    }
}
static void leave(){active.fetch_sub(1);}
static uint32_t next(uint32_t n){
    unsigned count=(n&15)+1;
    while(count--){n=(n-123u)*0x693d4b5u+123456u;n=(n<<16)|(n>>16);}
    n=n*0x41c64e6du+12345u;return (n<<16)|(n>>16);
}
static int private_draw(int argument,bool percentage){
    if(!percentage&&argument<2)return 0;
    AcquireSRWLockExclusive(&private_lock);
    presentation_seed=next(presentation_seed);
    uint32_t value=presentation_seed&0x7fffffff;
    InterlockedIncrement64(&private_advances);
    ReleaseSRWLockExclusive(&private_lock);
    return percentage ? (int(value%100)<argument) : int(value%uint32_t(argument));
}
extern "C" __declspec(dllexport) int Configure(const RouteConfig* c){
    if(!c||c->size!=sizeof(*c)||c->mode>1||!c->text||!c->range||!c->percentage)return 0;
    long expected=0;if(!active.compare_exchange_strong(expected,-1))return 0;
    config=*c;presentation_seed=c->presentation_seed;
    text_calls=expression_native=expression_private=voice_native=voice_private=private_advances=0;
    active.store(0);return 1;
}
extern "C" __declspec(dllexport) int Snapshot(RouteSnapshot* out){
    if(!out||out->size!=sizeof(*out))return 0;
    enter();
    AcquireSRWLockShared(&private_lock);
    out->mode=config.mode;out->local_depth=depth;out->presentation_seed=presentation_seed;
    ReleaseSRWLockShared(&private_lock);
    out->active=active.load()-1;
    out->text_calls=InterlockedCompareExchange64(&text_calls,0,0);
    out->expression_native=InterlockedCompareExchange64(&expression_native,0,0);
    out->expression_private=InterlockedCompareExchange64(&expression_private,0,0);
    out->voice_native=InterlockedCompareExchange64(&voice_native,0,0);
    out->voice_private=InterlockedCompareExchange64(&voice_private,0,0);
    out->private_advances=InterlockedCompareExchange64(&private_advances,0,0);
    leave();return 1;
}
extern "C" __declspec(dllexport) void* TextScope(void* item){
    enter();unsigned previous=depth;depth=previous+1;
    InterlockedIncrement64(&text_calls);
    __try {return config.text(item);}
    __finally {depth=previous;leave();}
}
static int route(int argument,bool percentage,bool voice){
    enter();
    __try {
        bool isolate=config.mode==1&&(voice||depth>0);
        if(voice)InterlockedIncrement64(isolate?&voice_private:&voice_native);
        else InterlockedIncrement64(isolate?&expression_private:&expression_native);
        if(isolate)return private_draw(argument,percentage);
        return (percentage?config.percentage:config.range)(argument);
    }
    __finally {leave();}
}
extern "C" __declspec(dllexport) int ExpressionRange(int n){return route(n,false,false);}
extern "C" __declspec(dllexport) int ExpressionPercentage(int n){return route(n,true,false);}
extern "C" __declspec(dllexport) int VoiceRange(int n){return route(n,false,true);}
