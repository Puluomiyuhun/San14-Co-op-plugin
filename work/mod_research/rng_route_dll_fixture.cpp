#include "rng_route_native_fixture.h"
#include "rng_route_fixture_api.h"
#include <chrono>

extern "C" void* CallTextBridge(TextFunction,void*);
extern "C" int TailRandomBridge(RandomFunction,int);
extern "C" int CheckNonvolatileBridge(TextFunction,void*);
static ConfigureFunction configure;
static SnapshotFunction snapshot;
static TextFunction textScope;
static RandomFunction expressionRange,expressionPercentage,voiceRange;
static NativeRng* original;
static std::mutex originalMutex;
static std::atomic<unsigned> originalCalls{0};
static thread_local bool throwRandom=false;
static int nativeRange(int n){
    originalCalls++;if(throwRandom)throw std::runtime_error("random callback failure");
    std::lock_guard<std::mutex> l(originalMutex);return original->range(n);
}
static int nativePercentage(int n){
    originalCalls++;std::lock_guard<std::mutex> l(originalMutex);return original->percentage(n);
}
static RouteSnapshot state(){RouteSnapshot s{};s.size=sizeof(s);check(snapshot(&s)==1,"snapshot");return s;}
enum Kind {Draw,Nested,ThrowCpp,ThrowSeh,NewThread,Block,OneRange,OnePercentage,ThrowRandom};
struct Item {
    Kind kind=Draw;unsigned calls=0,expectedDepth=1;Item* nested=nullptr;
    int argument=7,result=0,percentage=0;void* text=nullptr;
};
static HANDLE enteredEvent,releaseEvent;
static void* originalText(void* ptr){
    auto& item=*static_cast<Item*>(ptr);item.calls++;
    check(state().local_depth==item.expectedDepth,"scope depth");
    switch(item.kind){
    case Draw:
        item.result=TailRandomBridge(expressionRange,item.argument);
        item.percentage=TailRandomBridge(expressionPercentage,42);break;
    case Nested:
        check(CallTextBridge(textScope,item.nested)==item.nested->text,"nested pointer return");
        check(state().local_depth==item.expectedDepth,"nested depth restored");
        item.result=TailRandomBridge(expressionRange,item.argument);break;
    case ThrowCpp:throw std::runtime_error("text callback failure");
    case ThrowSeh:RaiseException(0xE0427014,0,0,nullptr);break;
    case NewThread:{
        std::atomic<bool> ok{false};
        std::thread child([&]{ok=state().local_depth==0;item.result=TailRandomBridge(expressionRange,item.argument);});
        child.join();check(ok,"TLS leaked into child thread");break;
    }
    case Block:
        SetEvent(enteredEvent);
        check(WaitForSingleObject(releaseEvent,5000)==WAIT_OBJECT_0,"blocked callback timeout");break;
    case OneRange:item.result=TailRandomBridge(expressionRange,item.argument);break;
    case OnePercentage:item.result=TailRandomBridge(expressionPercentage,item.argument);break;
    case ThrowRandom:item.result=TailRandomBridge(expressionRange,item.argument);break;
    }
    return item.text;
}
static void setMode(unsigned mode,uint32_t seed){
    RouteConfig c{sizeof(RouteConfig),mode,seed,originalText,nativeRange,nativePercentage};
    check(configure(&c)==1,"configure while quiescent");originalCalls=0;
}
static bool catchSeh(Item* item){
    __try {CallTextBridge(textScope,item);}
    __except(GetExceptionCode()==0xE0427014?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}
    return false;
}
static void pass(const char* name,unsigned count){std::printf("{\"case\":\"%s\",\"checks\":%u,\"result\":\"PASS\"}\n",name,count);}
template<class T> static T symbol(HMODULE mod,const char* name){
    auto p=GetProcAddress(mod,name);check(p!=nullptr,"missing export");
    T t;static_assert(sizeof(t)==sizeof(p));std::memcpy(&t,&p,sizeof(t));return t;
}
int wmain(int argc,wchar_t** argv){try{
    check(argc==2,"need absolute fixture DLL path");
    HMODULE mod=LoadLibraryW(argv[1]);check(mod!=nullptr,"LoadLibrary fixture DLL");
    configure=symbol<ConfigureFunction>(mod,"Configure");snapshot=symbol<SnapshotFunction>(mod,"Snapshot");
    textScope=symbol<TextFunction>(mod,"TextScope");
    expressionRange=symbol<RandomFunction>(mod,"ExpressionRange");
    expressionPercentage=symbol<RandomFunction>(mod,"ExpressionPercentage");
    voiceRange=symbol<RandomFunction>(mod,"VoiceRange");
    NativeRng native(3823646826u),reference(3823646826u),visual(123);
    original=&native;
    std::vector<char> returnedText(64,'a');void* text=returnedText.data();
    check(reinterpret_cast<uintptr_t>(text)>UINT32_MAX,"fixture must exercise a 64-bit pointer");

    setMode(0,123);
    Item child;child.expectedDepth=2;child.text=text;
    Item parent;parent.kind=Nested;parent.nested=&child;parent.text=text;
    check(CallTextBridge(textScope,&parent)==text,"full pointer return");
    check(child.result==reference.range(7)&&child.percentage==reference.percentage(42),"pass-through child results");
    check(parent.result==reference.range(7),"pass-through parent result");
    check(TailRandomBridge(expressionRange,123)==reference.range(123),"unknown default native");
    check(voiceRange(11)==reference.range(11),"observe voice pass through");
    auto s=state();
    check(parent.calls==1&&child.calls==1&&originalCalls==5,"native callbacks exactly once");
    check(s.presentation_seed==123&&native.get()==reference.get()&&s.local_depth==0&&s.active==0,"pass-through state unchanged by wrapper");
    pass("dll-observe-mode-preserves-native-sequence-and-pointer",5);

    setMode(1,123);visual.set(123);auto before=native.get();
    child.calls=parent.calls=0;
    check(CallTextBridge(textScope,&parent)==text,"isolated pointer return");
    check(child.result==visual.range(7)&&child.percentage==visual.percentage(42),"isolated child outputs");
    check(parent.result==visual.range(7),"isolated parent output");
    check(voiceRange(11)==visual.range(11),"voice private output");
    check(native.get()==before&&originalCalls==0,"candidate draws touched native seed");
    check(TailRandomBridge(expressionRange,123)==reference.range(123),"unknown route after scope");
    check(state().presentation_seed==visual.get()&&state().local_depth==0,"isolated scope restoration");
    pass("dll-isolation-nested-scope-and-unknown-fallback",5);

    Item abi;abi.text=text;
    check(CheckNonvolatileBridge(textScope,&abi)==1,"nonvolatile RBX/RSI");
    check(abi.calls==1,"ABI callback count");
    pass("call-tail-jump-and-representative-nonvolatile-registers",3);

    unsigned checks=0;
    const uint32_t seeds[]={0,1,0xffffffff,0x80000000,4136155758u,3823646826u,1138287528u};
    const int bounds[]={INT_MIN,-1,0,1,2,3,100,INT_MAX};
    const int thresholds[]={INT_MIN,-1,0,1,50,99,100,101,INT_MAX};
    for(auto seed:seeds){
        setMode(1,seed);visual.set(seed);before=native.get();
        for(int n:bounds){
            Item i;i.kind=OneRange;i.argument=n;i.text=text;
            check(CallTextBridge(textScope,&i)==text&&i.result==visual.range(n),"isolated range boundary");
            check(state().presentation_seed==visual.get(),"range boundary seed");checks++;
        }
        for(int n:thresholds){
            Item i;i.kind=OnePercentage;i.argument=n;i.text=text;
            check(CallTextBridge(textScope,&i)==text&&i.result==visual.percentage(n),"isolated percent boundary");
            check(state().presentation_seed==visual.get(),"percent boundary seed");checks++;
        }
        check(native.get()==before&&state().private_advances==13,"private advances versus attempted draws");
    }pass("private-dll-results-match-native-boundaries",checks);

    setMode(1,123);
    Item exceptional;exceptional.kind=ThrowCpp;
    bool caught=false;try{CallTextBridge(textScope,&exceptional);}catch(const std::runtime_error& e){caught=std::strcmp(e.what(),"text callback failure")==0;}
    check(caught&&exceptional.calls==1&&state().local_depth==0&&state().active==0,"C++ exception cleanup");
    exceptional.kind=ThrowSeh;exceptional.calls=0;
    check(catchSeh(&exceptional)&&exceptional.calls==1&&state().local_depth==0&&state().active==0,"Windows SEH cleanup");
    pass("cpp-and-structured-exception-unwind-through-dll-and-call-bridge",2);

    setMode(0,123);exceptional.kind=ThrowRandom;throwRandom=true;caught=false;
    try{CallTextBridge(textScope,&exceptional);}catch(const std::runtime_error& e){caught=std::strcmp(e.what(),"random callback failure")==0;}
    throwRandom=false;
    check(caught&&state().local_depth==0&&state().active==0,"random helper exception cleanup");
    check(TailRandomBridge(expressionRange,73)==reference.range(73),"post-exception native return");
    pass("exception-from-native-random-through-tail-route",2);

    setMode(1,123);Item threaded;threaded.kind=NewThread;threaded.text=text;
    check(CallTextBridge(textScope,&threaded)==text,"thread callback return");
    check(threaded.result==reference.range(7)&&state().presentation_seed==123,"unmarked child must stay native");
    check(state().expression_native==1&&state().expression_private==0,"thread route counters");
    pass("child-thread-does-not-inherit-presentation-context",3);

    setMode(1,123);visual.set(123);
    std::atomic<bool> concurrentOk{true};
    std::thread uiA([&]{for(unsigned i=0;i<1000;i++){Item row;row.text=text;try{if(CallTextBridge(textScope,&row)!=text)concurrentOk=false;}catch(...){concurrentOk=false;}}});
    std::thread uiB([&]{for(unsigned i=0;i<1000;i++)voiceRange(13);});
    for(unsigned i=0;i<2000;i++)check(TailRandomBridge(expressionRange,1000003)==reference.range(1000003),"concurrent logic sequence");
    uiA.join();uiB.join();
    for(unsigned i=0;i<3000;i++)visual.unbounded();
    s=state();check(concurrentOk&&s.presentation_seed==visual.get()&&native.get()==reference.get(),"concurrent final state");
    check(s.private_advances==3000&&s.expression_native==2000&&s.active==0,"concurrent counters");
    pass("dll-two-presentation-workers-and-one-native-logic-stream",5000);

    setMode(1,123);
    enteredEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);releaseEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    check(enteredEvent&&releaseEvent,"fixture events");
    Item blocked;blocked.kind=Block;blocked.text=text;std::atomic<bool> returned{false};
    std::thread busy([&]{try{returned=CallTextBridge(textScope,&blocked)==text;}catch(...){returned=false;}});
    bool entered=WaitForSingleObject(enteredEvent,3000)==WAIT_OBJECT_0;
    RouteConfig replacement{sizeof(RouteConfig),0,999,originalText,nativeRange,nativePercentage};
    int replacementResult=entered?configure(&replacement):-1;
    SetEvent(releaseEvent);busy.join();CloseHandle(enteredEvent);CloseHandle(releaseEvent);
    check(entered&&replacementResult==0&&returned,"reject active replacement without deadlock");
    check(state().mode==1&&state().presentation_seed==123,"rejected replacement changed config");
    check(configure(&replacement)==1,"accept replacement after callback drains");
    pass("configuration-replacement-rejected-while-callback-active",3);

    auto invalid=replacement;invalid.mode=2;check(configure(&invalid)==0,"invalid mode accepted");
    invalid=replacement;invalid.range=nullptr;check(configure(&invalid)==0,"null original accepted");
    invalid=replacement;invalid.size=0;check(configure(&invalid)==0,"invalid ABI size accepted");
    check(state().mode==0&&state().presentation_seed==999,"invalid config altered state");
    pass("configuration-validation",3);

    check(state().active==0&&state().local_depth==0,"unload must be quiescent");
    check(FreeLibrary(mod)!=0,"fixture DLL unload");
    return 0;
}catch(const std::exception& e){std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}}
