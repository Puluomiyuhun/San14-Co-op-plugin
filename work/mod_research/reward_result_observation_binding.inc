#include "reward_result_observation_anchors.h"
static uint64_t systemBreakpoint=0,systemBreakin=0;
static void bindSystemBreakpoints(HANDLE process,DWORD pid) {
    const auto local=GetModuleHandleW(L"ntdll.dll");
    const auto breakpoint=GetProcAddress(local,"DbgBreakPoint"),breakin=GetProcAddress(local,"DbgUiRemoteBreakin");
    if(!local||!breakpoint||!breakin)throw std::runtime_error("Missing local debugger entry exports");
    HANDLE list=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32,pid);
    check(list!=INVALID_HANDLE_VALUE,"Read target module list");
    MODULEENTRY32W module{};module.dwSize=sizeof(module);bool found=false;
    if(Module32FirstW(list,&module))do {if(!_wcsicmp(module.szModule,L"ntdll.dll")){
        const auto remote=uint64_t(module.modBaseAddr),start=uint64_t(local);
        systemBreakpoint=remote+uint64_t(breakpoint)-start;systemBreakin=remote+uint64_t(breakin)-start;found=true;break;
    }}while(Module32NextW(list,&module));
    CloseHandle(list);if(!found)throw std::runtime_error("Missing remote ntdll");
    unsigned char code[16];readExact(process,systemBreakpoint,code,sizeof code);
    if(memcmp(code,reinterpret_cast<const void*>(breakpoint),sizeof code))throw std::runtime_error("Remote debugger breakpoint bytes mismatch");
    readExact(process,systemBreakin,code,sizeof code);
    if(memcmp(code,reinterpret_cast<const void*>(breakin),sizeof code))throw std::runtime_error("Remote debugger breakin bytes mismatch");
}
struct HashResources {
    HANDLE file=INVALID_HANDLE_VALUE;BCRYPT_ALG_HANDLE algorithm=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;
    ~HashResources(){if(hash)BCryptDestroyHash(hash);if(algorithm)BCryptCloseAlgorithmProvider(algorithm,0);if(file!=INVALID_HANDLE_VALUE)CloseHandle(file);}
};
static void requireExeHash(const wchar_t* path) {
    HashResources h;h.file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    check(h.file!=INVALID_HANDLE_VALUE,"Open executable for hash");
    if(BCryptOpenAlgorithmProvider(&h.algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)throw std::runtime_error("SHA algorithm failed");
    DWORD length=0,written=0;
    if(BCryptGetProperty(h.algorithm,BCRYPT_OBJECT_LENGTH,reinterpret_cast<PUCHAR>(&length),sizeof(length),&written,0)<0||written!=sizeof(length))throw std::runtime_error("SHA object length failed");
    std::vector<unsigned char> object(length);unsigned char digest[32]{};
    if(BCryptCreateHash(h.algorithm,&h.hash,object.data(),length,nullptr,0,0)<0)throw std::runtime_error("SHA create failed");
    unsigned char buffer[65536];DWORD got=0;
    do {check(ReadFile(h.file,buffer,sizeof buffer,&got,nullptr),"Read executable for hash");if(got&&BCryptHashData(h.hash,buffer,got,0)<0)throw std::runtime_error("SHA update failed");}while(got);
    if(BCryptFinishHash(h.hash,digest,sizeof digest,0)<0)throw std::runtime_error("SHA final failed");
    const unsigned char expected[]={0x42,0xd5,0x3b,0xb4,0x2c,0x03,0x3c,0x60,0x27,0xb6,0xda,0x75,0xe8,0x07,0x7f,0x41,0x70,0xf4,0xd6,0x84,0xab,0xb0,0xf5,0x74,0x83,0xa6,0x61,0x22,0x5d,0x05,0x20,0x25};
    if(memcmp(digest,expected,32))throw std::runtime_error("Unsupported executable SHA256");
}
static void validateBinding(HANDLE process,const wchar_t* path,uint64_t base,uint64_t birth,uint64_t rva) {
    FILETIME a{},b{},c{},d{};check(GetProcessTimes(process,&a,&b,&c,&d),"Read process creation time");
    if(!birth||((uint64_t(a.dwHighDateTime)<<32)|a.dwLowDateTime)!=birth)throw std::runtime_error("Process birth mismatch");
    if(fixtureMode)return;
    if(rva!=0x67A930||!selectedUser||!selectedStack)throw std::runtime_error("Unsupported entry or missing formal User binding");
    requireExeHash(path);
    if(rd<uint16_t>(process,base)!=0x5A4D)throw std::runtime_error("Module DOS header mismatch");
    const auto nt=base+rd<uint32_t>(process,base+0x3C);
    if(rd<uint32_t>(process,nt)!=0x4550||rd<uint16_t>(process,nt+4)!=0x8664||rd<uint16_t>(process,nt+24)!=0x20B)throw std::runtime_error("Module PE machine mismatch");
    for(const auto& anchor:menuObservationAnchors){unsigned char bytes[16];readExact(process,base+anchor.rva,bytes,sizeof bytes);if(memcmp(bytes,anchor.bytes,sizeof bytes))throw std::runtime_error("Exact instruction anchor changed");}
    if(!formalUser(process,base))throw std::runtime_error("Not selected idle formal User");
}
