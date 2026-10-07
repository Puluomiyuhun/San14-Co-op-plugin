#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstdio>
alignas(8) static volatile uint32_t words[8]={0,7,0,0,9,0,0,0};
static volatile LONG markerCalls=0,gateCalls=0;
__declspec(noinline) static void marker() { InterlockedIncrement(&markerCalls); }
__declspec(noinline) static void gate() { InterlockedIncrement(&gateCalls); }
static DWORD WINAPI worker(void*) { words[1]=66; return 0; }
int wmain(int argc,wchar_t** argv) {
    if(argc!=3)return 2;
    const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    FILE* f=nullptr;_wfopen_s(&f,argv[1],L"w");if(!f)return 2;
    std::fprintf(f,"{\"pid\":%lu,\"base\":%llu,\"rvas\":[%llu,%llu,%llu,%llu]}",GetCurrentProcessId(),base,
        reinterpret_cast<uintptr_t>(&words[1])-base,reinterpret_cast<uintptr_t>(&words[4])-base,
        reinterpret_cast<uintptr_t>(&marker)-base,reinterpret_cast<uintptr_t>(&gate)-base);std::fclose(f);
    auto deadline=GetTickCount64()+30000;
    while(GetFileAttributesW(argv[2])==INVALID_FILE_ATTRIBUTES) {if(GetTickCount64()>deadline)return 3;Sleep(20);}
    const auto initialRead=words[1]+words[4];
    words[0]=111; words[1]=11; words[1]=11;
    reinterpret_cast<volatile uint8_t*>(&words[1])[3]=1;
    reinterpret_cast<volatile uint16_t*>(&words[1])[1]=2;
    *reinterpret_cast<volatile uint64_t*>(&words[0])=(uint64_t(33)<<32)|44;
    words[4]=55;
    HANDLE th=CreateThread(nullptr,0,worker,nullptr,0,nullptr);if(!th)return 4;
    WaitForSingleObject(th,5000);CloseHandle(th);
    marker();gate();words[1]=77;
    CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;
    RtlCaptureContext(&c);
    std::printf("{\"initial_read\":%u,\"value\":%u,\"effect\":%u,\"adjacent\":%u,\"marker\":%ld,\"gate\":%ld}\n",
        initialRead,words[1],words[4],words[0],markerCalls,gateCalls);
    return initialRead==16&&words[1]==77&&words[4]==55&&words[0]==44&&markerCalls==1&&gateCalls==1?0:1;
}
