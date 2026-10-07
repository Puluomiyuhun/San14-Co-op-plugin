// Isolated native DLL/vtable lifecycle fixture. Scanner is a synthetic callback;
// filename helper 328D20 executes the captured three-byte native body.
#define AUTO_CACHE_FIXTURE
#include "auto_cache_pilot.h"
#include "auto_cache_profile.h"
#include <vector>
#include <string>
#include <cstdio>
#include <cstring>
#include <stdexcept>
static unsigned char* module=nullptr;
static std::vector<unsigned char> root(0x85200),world(0x2200),manager(0x500),person(0x300),force(0x100),city(0x200),district(0x100),metadata(0x200);
static std::vector<std::vector<unsigned char>> states(5,std::vector<unsigned char>(0x700)),armies(501,std::vector<unsigned char>(0x200));
static std::vector<uint64_t> pointers(5);
static uint64_t sentinel[2]{};
static std::wstring test;
static unsigned originalCalls=0,scanCalls=0;
static bool argsCorrect=true;
template<class T>static void put(unsigned char* p,size_t off,T v){std::memcpy(p+off,&v,sizeof v);}
template<class T>static T get(unsigned char* p,size_t off){T v{};std::memcpy(&v,p+off,sizeof v);return v;}
static void need(bool ok,const char* what){if(!ok)throw std::runtime_error(what);}
static void __fastcall original(void* self,uintptr_t a2,uintptr_t a3,uintptr_t a4){
    ++originalCalls;argsCorrect=argsCorrect&&self==states[4].data()&&a2==11&&a3==22&&a4==33;
    if(test==L"state_changed_after_install")put(manager.data(),8,uint32_t(1));
}
static void __fastcall scan(void* self,int selector){
    ++scanCalls;need(self==manager.data()&&selector==0,"native scanner arguments");
    if(test==L"scanner_exception")RaiseException(0xE0001414,0,0,nullptr);
    if(test==L"missing_slot34")return;
    if(test==L"world_mutation")world[0x454]^=1;
    put(manager.data(),0x20+34*8,uint64_t(metadata.data()));
    if(test==L"reentrant_update"){
        auto fn=get<CacheUpdate>(module,0x12CC4A8+0x28);fn(states[4].data(),11,22,33);
    }
}
struct InstallContext {CacheInstall install;CacheConfig* config;DWORD result;};
static DWORD WINAPI installThread(void* argument){auto p=static_cast<InstallContext*>(argument);p->result=p->install(p->config);return 0;}
int wmain(int argc,wchar_t** argv){
    try{
        need(argc==5,"dll case once output required");test=argv[2];
        module=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x2240000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE));need(module!=nullptr,"module allocation");const auto b=uint64_t(module);
        for(const auto& p:CACHE_FINGERPRINTS)memcpy(module+p.rva,p.bytes,p.size);
        put(module,0x12CC4A8+0x28,&original);put(module,0x1FCA1E0,uint64_t(root.data()));put(root.data(),0,b+0x12AA6B0);put(root.data(),0x85130,uint64_t(world.data()));
        put(world.data(),0,b+0x12AA638);put(world.data(),0x34,uint16_t(203));world[0x36]=8;world[0x37]=11;world[0x3A]=12;put(world.data(),0x40,uint32_t(1));
        const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};for(unsigned i=0;i<5;++i){pointers[i]=uint64_t(states[i].data());strcpy_s(reinterpret_cast<char*>(states[i].data()+0x70),96,names[i]);}
        put(module,0x19E7310+0x10,uint64_t(5));put(module,0x19E7310+0x20,uint64_t(pointers.data()));
        put(states[4].data(),0,b+0x12CC4A8);put(states[4].data(),0x470,uint32_t(2));put(states[4].data(),0x478,uint64_t(0x1111));put(states[4].data(),0x618,uint64_t(0x2222));
        put(root.data(),0xDCA0+12*8,uint64_t(force.data()));put(force.data(),0x10,uint16_t(666));
        put(root.data(),0x148+666*8,uint64_t(person.data()));put(person.data(),0x10,uint16_t(666));person[0x118]=11;put(person.data(),0x11A,uint16_t(19));
        put(root.data(),0xDAA8+19*8,uint64_t(city.data()));put(city.data(),0x10,uint16_t(19));city[0x30]=11;put(city.data(),0x3C,uint32_t(15204));
        put(root.data(),0xDE40+11*8,uint64_t(district.data()));district[0x10]=12;district[0x14]=18;
        for(unsigned i=1;i<=500;++i){put(root.data(),0x7DF60+i*8,uint64_t(armies[i].data()));if(i<=56){armies[i][0x10]=1;put(armies[i].data(),0x12,uint16_t(i));}}
        put(module,0x2025318,uint64_t(manager.data()));put(manager.data(),0x3EC,int32_t(-1));sentinel[0]=sentinel[1]=uint64_t(sentinel);put(manager.data(),0x10,uint64_t(sentinel));
        // Native clear leaves the two automatic-save hint fields stale even when empty.
        put(manager.data(),0x3E4,int32_t(-1));put(manager.data(),0x3E8,int32_t(56));put(manager.data(),0x3F4,int32_t(-1));put(manager.data(),0x3F8,int32_t(114));
        memcpy(metadata.data()+0x128,"svdexSC34.s14",14);put(metadata.data(),0x138,uint64_t(13));put(metadata.data(),0x140,uint64_t(15));
        if(test==L"wrong_mode")put(manager.data(),8,uint32_t(1));
        if(test==L"wrong_pending")put(manager.data(),0x3EC,int32_t(34));
        if(test==L"cache_nonempty")put(manager.data(),0x20+5*8,uint64_t(metadata.data()));
        if(test==L"list_nonempty")put(manager.data(),0x18,uint64_t(1));
        if(test==L"wrong_date")world[0x37]=21;
        if(test==L"wrong_phase")put(states[4].data(),0x470,uint32_t(3));
        if(test==L"wrong_code")module[0x836EF0]^=1;
        if(test==L"pending_state_command")put(module,0x19E7310+0x30,uint64_t(1));
        if(test==L"wrong_metadata")metadata[0x130]='5';
        auto worldBefore=world;auto managerBefore=manager;
        HMODULE dll=LoadLibraryW(argv[1]);need(dll!=nullptr,"LoadLibrary fixture DLL");
        auto install=reinterpret_cast<CacheInstall>(GetProcAddress(dll,"InstallAutoCache"));auto cancel=reinterpret_cast<CacheInstall>(GetProcAddress(dll,"CancelAutoCache"));
        auto report=reinterpret_cast<CacheReportData*>(GetProcAddress(dll,"AutoCacheReport"));need(install&&cancel&&report,"exports");
        CacheConfig cfg{};cfg.magic=CACHE_MAGIC;cfg.version=1;cfg.execute=test!=L"dry";wcscpy_s(cfg.intentPath,argv[3]);cfg.testBase=b;cfg.testParameter=b+0x328D20;cfg.testScanner=uintptr_t(&scan);
        if(test==L"bad_magic")cfg.magic=0;
        if(test==L"existing_journal"){HANDLE file=CreateFileW(argv[3],GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);need(file!=INVALID_HANDLE_VALUE,"existing intent fixture");DWORD done;WriteFile(file,"prior",5,&done,nullptr);CloseHandle(file);}
        DWORD old=0;need(VirtualProtect(module+0x12CC000,4096,PAGE_READONLY,&old)!=FALSE,"vtable readonly");
        InstallContext args{install,&cfg,0};HANDLE thread=CreateThread(nullptr,0,installThread,&args,0,nullptr);need(thread!=nullptr,"installer thread");need(WaitForSingleObject(thread,5000)==WAIT_OBJECT_0,"installer timeout");CloseHandle(thread);
        bool armed=report->status==1;
        DWORD repeated=0;
        if(armed){
            if(test==L"cancel")need(cancel(nullptr)==0,"cancel pending");
            else {auto update=get<CacheUpdate>(module,0x12CC4A8+0x28);update(states[4].data(),11,22,33);}
            if(test==L"repeat_install")repeated=install(&cfg);
            auto update=get<CacheUpdate>(module,0x12CC4A8+0x28);update(states[4].data(),11,22,33);
        }
        bool expectedSuccess=test==L"execute"||test==L"repeat_install"||test==L"reentrant_update";
        bool uncertain=test==L"scanner_exception"||test==L"world_mutation"||test==L"missing_slot34"||test==L"wrong_metadata";
        LONG expected=expectedSuccess?4:test==L"dry"?3:test==L"cancel"?7:uncertain?6:5;
        need(report->status==expected,"unexpected report status");need(report->activeCallbacks==0,"callback leaked");need(get<CacheUpdate>(module,0x12CC4A8+0x28)==&original,"vtable not restored");
        MEMORY_BASIC_INFORMATION region{};VirtualQuery(module+0x12CC4A8,&region,sizeof region);need(region.Protect==PAGE_READONLY,"protection not restored");
        need(argsCorrect,"original ABI altered");
        need(scanCalls==report->scannerCalls&&scanCalls==(expectedSuccess||uncertain?1u:0u),"scanner called unexpectedly or repeatedly");
        if(test!=L"world_mutation")need(world==worldBefore,"fixture world unexpectedly changed");
        if(test==L"state_changed_after_install")put(managerBefore.data(),8,uint32_t(1));
        if(!scanCalls)need(manager==managerBefore,"cache mutated without native scanner");
        if(test==L"repeat_install")need(repeated==1001,"duplicate install accepted");
        if(report->scannerCalls)need(report->executorThread!=report->installerThread&&report->intentCreated&&report->intentFlushed,"wrong execution thread or missing durable intent");
        FILE* output=nullptr;need(_wfopen_s(&output,argv[4],L"wb")==0,"report file");fwrite(report,1,sizeof *report,output);fclose(output);
        std::printf("{\"result\":\"PASS\",\"status\":%ld,\"error\":%ld,\"native_scanner_calls\":%u,\"original_calls\":%u,\"report_original_calls\":%lu,\"intent_created\":%lu,\"intent_flushed\":%lu,\"world_unchanged\":%lu,\"slot34_matched\":%lu,\"hook_restored\":true,\"protection_restored\":true,\"game_process_access\":false}\n",report->status,report->error,scanCalls,originalCalls,report->originalCalls,report->intentCreated,report->intentFlushed,report->worldUnchanged,report->slot34Matched);
        VirtualFree(module,0,MEM_RELEASE);return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
}
