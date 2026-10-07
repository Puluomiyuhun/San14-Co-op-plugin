#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstdint>
static volatile LONG calls=0;
__declspec(noinline) void observed(uint32_t* value) {
    InterlockedIncrement(&calls);
    *value += 10;
}
int wmain(int argc,wchar_t** argv) {
    if(argc!=3) return 2;
    auto base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    FILE* f=nullptr;_wfopen_s(&f,argv[1],L"w");if(!f)return 2;
    std::fprintf(f,"{\"pid\":%lu,\"base\":%llu,\"rva\":%llu}",GetCurrentProcessId(),base,reinterpret_cast<uintptr_t>(&observed)-base);std::fclose(f);
    auto deadline=GetTickCount64()+30000;
    while(GetFileAttributesW(argv[2])==INVALID_FILE_ATTRIBUTES) {if(GetTickCount64()>deadline)return 3;Sleep(25);}
    uint32_t v=1;
    for(unsigned i=0;i<3;i++) {observed(&v);Sleep(50);}
    std::printf("{\"calls\":%ld,\"value\":%u}\n",calls,v);
    return calls==3 && v==31?0:1;
}
