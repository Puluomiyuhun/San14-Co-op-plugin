#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstdint>
#include <string>
static volatile LONG calls=0;
__declspec(noinline) void* submit(uint32_t* words,int flags) {
    InterlockedIncrement(&calls);
    return flags==1 && words[0]==666 && words[2]==1300 ? words : nullptr;
}
int wmain(int argc,wchar_t** argv) {
    if(argc!=3 && argc!=4) return 2;
    const auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    FILE* file=nullptr; _wfopen_s(&file,argv[1],L"w"); if(!file) return 2;
    std::fprintf(file,"{\"pid\":%lu,\"base\":%llu,\"rva\":%llu}",GetCurrentProcessId(),base,reinterpret_cast<uintptr_t>(&submit)-base); std::fclose(file);
    const auto deadline=GetTickCount64()+30000;
    while(GetFileAttributesW(argv[2])==INVALID_FILE_ATTRIBUTES) { if(GetTickCount64()>deadline) return 3; Sleep(50); }
    uint32_t words[26]{}; words[0]=666; words[2]=argc==4?1000:1300; words[15]=20;
    auto result=submit(words,1);
    std::printf("{\"calls\":%ld,\"original_function_returned\":%s}\n",calls,result==words?"true":"false");
    Sleep(500);
    return result==words && calls==1 ? 0 : 1;
}
