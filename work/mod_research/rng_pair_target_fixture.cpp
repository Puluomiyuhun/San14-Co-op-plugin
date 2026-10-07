#include "rng_pair_native_fixture.h"
#include "rng_route_fixture_api.h"
extern "C" int TailRandomBridge(RandomFunction,int);
struct Result {DWORD thread;bool range;int argument,result;};
static std::vector<Result> results;
static std::mutex resultsLock;
static void perform(NativeRng& r,bool range,int argument){
    auto fn=reinterpret_cast<RandomFunction>(r.fixtureAddress(range?0x200:0x100));
    int value=TailRandomBridge(fn,argument);
    std::lock_guard<std::mutex> lock(resultsLock);
    results.push_back({GetCurrentThreadId(),range,argument,value});
}
static void file(const wchar_t* name,const char* contents){
    FILE* f=nullptr;_wfopen_s(&f,name,L"w");check(f!=nullptr,"fixture file");std::fputs(contents,f);std::fclose(f);
}
int wmain(int argc,wchar_t** argv){try{
    check(argc==5,"ready go done release paths required");NativeRng r(1138287528);
    FILE* ready=nullptr;_wfopen_s(&ready,argv[1],L"w");check(ready!=nullptr,"fixture ready");
    std::fprintf(ready,"{\"pid\":%lu,\"base\":%llu,\"range_address\":%llu,\"percentage_address\":%llu,\"rng_address\":%llu}",
        GetCurrentProcessId(),reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr)),r.fixtureAddress(0x200),r.fixtureAddress(0x100),r.fixtureAddress(0x1000));std::fclose(ready);
    auto deadline=GetTickCount64()+30000;
    while(GetFileAttributesW(argv[2])==INVALID_FILE_ATTRIBUTES){check(GetTickCount64()<deadline,"fixture go timeout");Sleep(10);}
    const int ranges[]={INT_MIN,-1,0,1,2,3,100,INT_MAX};
    const int probabilities[]={INT_MIN,-1,0,1,50,99,100,101,INT_MAX};
    for(auto n:ranges)perform(r,true,n);
    for(auto n:probabilities)perform(r,false,n);
    r.set(r.get());r.unbounded(); // Writes outside both traced helper entries.
    std::thread newlyCreated([&]{perform(r,true,17);perform(r,false,77);});newlyCreated.join();
    std::thread a([&]{for(int i=0;i<32;i++)perform(r,true,10000+i);});
    std::thread b([&]{for(int i=0;i<32;i++)perform(r,true,11000+i);});a.join();b.join();
    file(argv[3],"done");
    while(GetFileAttributesW(argv[4])==INVALID_FILE_ATTRIBUTES){check(GetTickCount64()<deadline,"fixture release timeout");Sleep(10);}
    BOOL debugged=TRUE;check(CheckRemoteDebuggerPresent(GetCurrentProcess(),&debugged)!=0,"fixture debugger status");
    check(!debugged,"fixture still attached after release");
    std::printf("{\"rows\":[");
    for(size_t i=0;i<results.size();i++){
        auto& v=results[i];std::printf("%s{\"thread\":%lu,\"kind\":\"%s\",\"argument\":%d,\"result\":%d}",
            i?",":"",v.thread,v.range?"range":"percentage",v.argument,v.result);
    }
    std::printf("],\"debugger_detached\":true,\"final_rng\":%u}\n",r.get());return 0;
}catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
