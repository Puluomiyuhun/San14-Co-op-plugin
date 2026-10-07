#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstdio>
alignas(8) static volatile uint16_t words[4]={0,7,0,0};
static volatile LONG entries=0,returns=0,consumes=0;
__declspec(noinline) static void enterMarker(){InterlockedIncrement(&entries);}
__declspec(noinline) static void returnMarker(){InterlockedIncrement(&returns);}
__declspec(noinline) static void consumeMarker(){InterlockedIncrement(&consumes);}
static DWORD WINAPI worker(void*){enterMarker();words[1]=66;returnMarker();return 0;}
int wmain(int argc,wchar_t** argv){
    if(argc!=3)return 2;
    auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    FILE* f=nullptr;_wfopen_s(&f,argv[1],L"w");if(!f)return 2;
    std::fprintf(f,"{\"pid\":%lu,\"base\":%llu,\"watch\":%llu,\"rvas\":[%llu,%llu,%llu]}",GetCurrentProcessId(),base,
        reinterpret_cast<uintptr_t>(&words[1]),reinterpret_cast<uintptr_t>(enterMarker)-base,
        reinterpret_cast<uintptr_t>(returnMarker)-base,reinterpret_cast<uintptr_t>(consumeMarker)-base);std::fclose(f);
    auto deadline=GetTickCount64()+30000;
    while(GetFileAttributesW(argv[2])==INVALID_FILE_ATTRIBUTES){if(GetTickCount64()>deadline)return 3;Sleep(20);}
    auto initial=words[1];words[0]=111;words[2]=55;words[1]=11;words[1]=11;
    reinterpret_cast<volatile uint8_t*>(&words[1])[1]=1;
    *reinterpret_cast<volatile uint32_t*>(&words[0])=(uint32_t(33)<<16)|44;
    HANDLE th=CreateThread(nullptr,0,worker,nullptr,0,nullptr);if(!th)return 4;
    WaitForSingleObject(th,5000);CloseHandle(th);consumeMarker();words[1]=77;
    std::printf("{\"initial\":%u,\"value\":%u,\"left\":%u,\"right\":%u,\"entries\":%ld,\"returns\":%ld,\"consumes\":%ld}\n",initial,words[1],words[0],words[2],entries,returns,consumes);
    return initial==7&&words[1]==77&&words[0]==44&&words[2]==55&&entries==1&&returns==1&&consumes==1?0:1;
}
