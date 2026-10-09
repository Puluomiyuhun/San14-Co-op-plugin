// Only linked into the owned diagnostic DLL. No game discovery or interaction.
#undef session
#include <TlHelp32.h>
static unsigned char ownedPublishedCall[5]{};static uintptr_t ownedLeave=0;static const void* ownedProvider=nullptr;
static void ownedCtor(uintptr_t control,uintptr_t payload,uintptr_t name,uintptr_t flags){
 if(control>=base+0x1A24DA0+0x10&&control<=base+0x1A24DA0+0x190)lifecycleCtor(control,payload,name,flags);
 else nativeCtorDouble(control,payload,name,flags);
}
static bool ownedSeed(uintptr_t image){
 printf("SEED entered\n");fflush(stdout);
 const auto start=uintptr_t(GetProcAddress(GetModuleHandleW(nullptr),"BReloadBootstrapQueueSpace"));
 printf("SEED range=%llx base=%llx\n",start,image);fflush(stdout);
 if(image!=uintptr_t(GetModuleHandleW(nullptr))||!start||start>image+0xF000||start+0x2400000<image+0x2310000)return false;
 currentLayout=new checkpoint_load_input_boundary_fixture::Layout;
 if(!layout.initialize(bd::Stage::MenuAfter))return false;
 base=image;sharedImage=image;printf("SEED layout\n");fflush(stdout);
 // All original identity ranges are seeded only before Bootstrap publication.
 for(const auto&a:CheckpointLiveSessionAnchors)memcpy(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size);
 for(const auto&a:CheckpointNativeQueueAnchors)memcpy(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size);
 printf("SEED anchors\n");fflush(stdout);prepareNativeMachine();printf("SEED native\n");fflush(stdout);rootPrepareMachine();printf("SEED root\n");fflush(stdout);yieldPrepare();
 DWORD old=0;
 if(!VirtualProtect(reinterpret_cast<void*>(base+0x50B000),4096,PAGE_EXECUTE_READ,&old))return false;
 if(!VirtualProtect(reinterpret_cast<void*>(base+0x509580),sizeof b_reload_lifecycle_profile::InitBytes,PAGE_READWRITE,&old))return false;
 memcpy(reinterpret_cast<void*>(base+0x509580),b_reload_lifecycle_profile::InitBytes,sizeof b_reload_lifecycle_profile::InitBytes);
 if(!VirtualProtect(reinterpret_cast<void*>(base+0x509580),sizeof b_reload_lifecycle_profile::InitBytes,PAGE_EXECUTE_READ,&old))return false;
 const unsigned char head[]={0x48,0x83,0xec,0x28},tail[]={0x48,0x83,0xc4,0x28,0xc3};
 memcpy(reinterpret_cast<void*>(base+0x1447B2),head,4);memcpy(reinterpret_cast<void*>(base+0x1447B6),b_reload_lifecycle_profile::InitCall,5);memcpy(reinterpret_cast<void*>(base+0x1447BB),tail,5);
 const unsigned char initUw[]={1,0x14,8,0,0x14,0xd2,0x10,0x70,0x0f,0x64,0x13,0,0x0b,0x54,0x12,0,0x07,0x34,0x11,0},caller[]={1,4,1,0,4,0x42,0,0};
 memcpy(reinterpret_cast<void*>(base+0x2300C00),initUw,sizeof initUw);memcpy(reinterpret_cast<void*>(base+0x2300C40),caller,sizeof caller);
 if(!VirtualProtect(reinterpret_cast<void*>(base+0x144000),4096,PAGE_EXECUTE_READ,&old))return false;
 parentJump(0x833CB0,uintptr_t(&ownedCtor));parentJump(0x160F0,uintptr_t(&activatedSwap));
 put<uintptr_t>(base+0x12F2440,uintptr_t(&activatedCopy));put<uintptr_t>(base+0x12F2440+0x10,base+0x50B730);put<uintptr_t>(base+0x12F2440+0x20,uintptr_t(&parentNoop));
 put<uintptr_t>(base+0x123C1D8,uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"SetEvent")));put<uintptr_t>(base+0x123C1E0,uintptr_t(&lifecycleWait));
 for(unsigned i=0;i<4;++i)*reinterpret_cast<volatile uintptr_t*>(base+0x1A24DA0+0x10+i*0x80)=0;
 if(!VirtualProtect(reinterpret_cast<void*>(base+0x123C000),4096,PAGE_READONLY,&old))return false;
 FlushInstructionCache(GetCurrentProcess(),nullptr,0);return failures==0;
}
extern "C" __declspec(dllexport) DWORD WINAPI BReloadLifecycleBootstrap(void*p){
 if(!p)return 1;bool ok=false;
 __try {const auto i=*static_cast<BReloadLifecycleBootstrapInfo*>(p);if(!ownedSeed(i.imageBase))return 2;HANDLE snap=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);THREADENTRY32 te{};te.dwSize=sizeof te;for(BOOL more=Thread32First(snap,&te);more;more=Thread32Next(snap,&te))if(te.th32OwnerProcessID==GetCurrentProcessId()){using Query=LONG(NTAPI*)(HANDLE,ULONG,PVOID,ULONG,PULONG);auto query=reinterpret_cast<Query>(GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"NtQueryInformationThread"));auto thread=OpenThread(THREAD_QUERY_INFORMATION|SYNCHRONIZE,FALSE,te.th32ThreadID);uintptr_t entry=0;HMODULE module=nullptr;wchar_t name[512]{};if(query&&thread)query(thread,9,&entry,sizeof entry,nullptr);if(entry&&GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(entry),&module))GetModuleFileNameW(module,name,512);printf("THREAD tid=%lu main=%lu self=%lu start=%llx module=%ls rva=%llx\n",te.th32ThreadID,i.primaryThread,GetCurrentThreadId(),entry,name,entry-uintptr_t(module));if(thread){if(te.th32ThreadID!=i.primaryThread&&te.th32ThreadID!=GetCurrentThreadId()){const auto began=GetTickCount64();const auto wait=WaitForSingleObject(thread,30000);printf("THREAD natural_exit=%lu waited_ms=%llu\n",wait,GetTickCount64()-began);fflush(stdout);if(wait!=WAIT_OBJECT_0){CloseHandle(thread);CloseHandle(snap);return 5;}}CloseHandle(thread);}}CloseHandle(snap);fflush(stdout);ok=runtime.InitializeAndArm(i,{&coldProducerLock,&coldTaskStarts,uintptr_t(&coldUnifiedEntry),2000});}
 __except(EXCEPTION_EXECUTE_HANDLER){printf("SEED exception=%lx\n",GetExceptionCode());fflush(stdout);return 3;}
 if(ok){memcpy(ownedPublishedCall,reinterpret_cast<void*>(base+0x1447B6),5);ownedLeave=at<uintptr_t>(base+0x123C0D8);ownedProvider=&runtime.Provider();}
 b_reload_cold_bootstrap::Report b{};b_reload_cold_bootstrap::Snapshot(b);
 printf("{\"actual_bootstrap\":true,\"ok\":%s,\"attempts\":%u,\"error\":%u}\n",ok?"true":"false",b.attempts,unsigned(b.error));fflush(stdout);
 return ok?BReloadLifecycleBootstrapSuccess:4;
}
extern "C" __declspec(dllexport) DWORD WINAPI BReloadQueueOwnedRun(void*){
 wchar_t which[80]{},folder[4096]{};
 if(!GetEnvironmentVariableW(L"SAN14_OWNED_CASE",which,80)||!GetEnvironmentVariableW(L"SAN14_OWNED_FOLDER",folder,4096))return 90;
 wchar_t first[]=L"owned",unused[]=L"unused";wchar_t*args[]={first,which,unused,folder};
 printf("{\"owned_main_started\":true}\n");fflush(stdout);
 const int result=queueMain(4,args);
 b_reload_cold_bootstrap::Report b{};b_reload_lifecycle::Report l{};b_reload_root_activation::Report a{};b_reload_lifecycle_fault_guard::Report g{};
 runtime.Snapshot(b,l,a,g);
 check(base==uintptr_t(GetModuleHandleW(nullptr))&&ownedProvider==&runtime.Provider()&&ownedLeave==at<uintptr_t>(base+0x123C0D8)&&!memcmp(ownedPublishedCall,reinterpret_cast<void*>(base+0x1447B6),5),"Bootstrap primary image Provider IAT and initialization call unchanged");
 check(at<uintptr_t>(base+0x123C328)==uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"EnterCriticalSection"))&&!memcmp(reinterpret_cast<void*>(base+0x509580),b_reload_lifecycle_profile::InitBytes,sizeof b_reload_lifecycle_profile::InitBytes)&&!memcmp(reinterpret_cast<void*>(base+0x834D10),b_reload_root_worker_profile::RunnerBytes,sizeof b_reload_root_worker_profile::RunnerBytes)&&!memcmp(reinterpret_cast<void*>(base+0x83A930),activation::ThreadEntryBytes,sizeof activation::ThreadEntryBytes),"real synchronization and archived worker sources unchanged");
 check(!at<DWORD>(base+0x2025270),"all retained worker task counts drained");
 check(b.attempts==1&&b.armed&&a.initialWaitVerified==4&&a.outerFinally==4&&g.opened&&g.attempts==1&&g.registerCalls==1&&g.openCalls==1,"same Bootstrap Runtime completes one gated transition");
 const auto&cold=b_reload_cold_registration::Snapshot();check(cold.oldCalls==1&&cold.registered==1&&cold.provider==uintptr_t(&runtime.Provider())&&cold.base==base&&cold.wait.pending&&cold.wait.initialWaitVerified==4&&!cold.wait.uncertain,"same Bootstrap cold registration and queue Provider through final return");
 printf("{\"cold_bootstrap_composed\":true,\"old_register_calls\":%u,\"registered\":%u,\"pending\":%u,\"suspends\":%u,\"resumes\":%u,\"same_provider\":true,\"constructor_initial_wait_removed\":true,\"fixture_set_service_transition\":true}\n",cold.oldCalls,cold.registered,cold.wait.pending,cold.wait.suspends,cold.wait.resumes);
 printf("{\"bootstrap_queue_composed\":true,\"passed\":%s,\"same_pe\":true,\"same_provider\":true,\"cold_workers\":%u,\"root_tasks\":%u,\"gate_attempts\":%u,\"critical_sections_checked\":%zu,\"owned_skipped_state_locks\":%u,\"actual_two_legal_saves\":false,\"game_access\":false}\n",!result&&!failures?"true":"false",a.initialWaitVerified,a.taskCount,g.attempts,ownedCompletionLocks.size(),ownedDummyLocks);fflush(stdout);
 return result||failures?1:0;
}
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID){return TRUE;}
