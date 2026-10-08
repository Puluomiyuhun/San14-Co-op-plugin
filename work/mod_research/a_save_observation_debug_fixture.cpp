#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstdint>
#include <share.h>
#include <cwchar>
static volatile LONG calls=0;
static unsigned handled=0;
static volatile LONG barrier=0;
__declspec(noinline) static void tick(unsigned* value){InterlockedIncrement(&calls);*value+=10;}
__declspec(noinline) static void tickB(unsigned* value){InterlockedIncrement(&calls);*value+=10;}
__declspec(noinline) static void unused(){Sleep(0);}
static DWORD WINAPI waiting(void* event){WaitForSingleObject(static_cast<HANDLE>(event),INFINITE);return 0;}
static DWORD WINAPI adaptive(void* value){
    InterlockedIncrement(&barrier);while(InterlockedCompareExchange(&barrier,0,0)!=2)YieldProcessor();
    for(unsigned i=0;i<256;++i){tick(static_cast<unsigned*>(value));tickB(static_cast<unsigned*>(value));}
    return 0;
}
static void exceptions(){
    __try{RaiseException(0xE0421234,0,0,nullptr);}__except(GetExceptionCode()==0xE0421234?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){++handled;}
    __try{__debugbreak();}__except(GetExceptionCode()==EXCEPTION_BREAKPOINT?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){++handled;}
}
int wmain(int argc,wchar_t** argv){
    if(argc!=4)return 2;
    const bool foreign=!wcscmp(argv[3],L"foreign"),dual=!wcscmp(argv[3],L"adaptive");HANDLE event=nullptr,thread=nullptr;
    if(foreign){
        event=CreateEventW(nullptr,TRUE,FALSE,nullptr);thread=CreateThread(nullptr,0,waiting,event,CREATE_SUSPENDED,nullptr);
        if(!event||!thread)return 3;CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;
        if(!GetThreadContext(thread,&c))return 4;c.Dr0=uint64_t(&unused);c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|1;
        if(!SetThreadContext(thread,&c)||ResumeThread(thread)==DWORD(-1))return 5;
    }
    FILE* f=_wfsopen(argv[1],L"w",_SH_DENYNO);if(!f)return 6;
    const auto base=uint64_t(GetModuleHandleW(nullptr));
    std::fprintf(f,"{\"pid\":%lu,\"base\":%llu,\"rva\":%llu,\"rva2\":%llu}\n",GetCurrentProcessId(),base,uint64_t(&tick)-base,uint64_t(&tickB)-base);std::fclose(f);
    for(unsigned i=0;GetFileAttributesW(argv[2])==INVALID_FILE_ATTRIBUTES;++i){if(i>12000)return 7;Sleep(5);}
    if(!foreign&&!dual)exceptions();
    unsigned value=1,second=1;
    if(dual){
        HANDLE a=CreateThread(nullptr,0,adaptive,&value,CREATE_SUSPENDED,nullptr),b=CreateThread(nullptr,0,adaptive,&second,CREATE_SUSPENDED,nullptr);
        if(!a||!b)return 8;SetThreadAffinityMask(a,1);SetThreadAffinityMask(b,2);ResumeThread(a);ResumeThread(b);
        WaitForSingleObject(a,30000);WaitForSingleObject(b,30000);CloseHandle(a);CloseHandle(b);
    }else for(unsigned i=0;i<3;++i)tick(&value);
    if(foreign){SetEvent(event);WaitForSingleObject(thread,5000);CloseHandle(thread);CloseHandle(event);}
    std::printf("{\"calls\":%ld,\"value\":%u,\"second\":%u,\"handled\":%u}\n",calls,value,second,handled);return 0;
}
