namespace ports=checkpoint_task_native_ports;

static ports::Report nativePortReport{};
static unsigned foreignSehCaught=0;
extern "C" {
struct NativePayloadSnapshot {std::uint64_t gpr[16]{},flags=0,reserved=0;unsigned char xmm[256]{};DWORD mxcsr=0,pad[3]{};};
NativePayloadSnapshot TaskPortsPayloadSnapshot{};
void NativeLoadPayloadDouble(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
}
static thread_local EmbeddedPort* nativeFixtureTask=nullptr;
extern "C" void TaskFixturePayloadBody(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
static void nativeSyncDouble(void*){}
static BOOL nativeSetEventDouble(HANDLE h){return SetEvent(h);}
static DWORD nativeWaitDouble(HANDLE h,DWORD ms){if(nativeFixtureTask&&h==nativeFixtureTask->wake)SetEvent(nativeFixtureTask->ready);return WaitForSingleObject(h,ms);}
static void foreignExceptionInNativeBody(){__try{RaiseException(0xE0149A01,0,0,nullptr);}__except(GetExceptionCode()==0xE0149A01?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){++foreignSehCaught;}}
extern "C" void NativeLoadPayloadBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    if(scenario==L"ports-foreign-seh")foreignExceptionInNativeBody();TaskFixturePayloadBody(self,a,b,c);
}
static void nativeEndThreadDouble(unsigned){}
static void nativeCtorDouble(uintptr_t,uintptr_t,uintptr_t,uintptr_t);
static uintptr_t nativeNullDouble(){return 0;}
static void prepareNativeMachine(){
    memcpy(reinterpret_cast<void*>(base+0x4DA240),nativeStart::BindBytes,sizeof nativeStart::BindBytes);
    memcpy(reinterpret_cast<void*>(base+0x834B60),nativeStart::StartBytes,sizeof nativeStart::StartBytes);
    for(auto target: {std::pair<uintptr_t,uintptr_t>{0x50C710,uintptr_t(&nativeNullDouble)},{0x194A90,uintptr_t(&nativeNullDouble)},{0x833CB0,uintptr_t(&nativeCtorDouble)}}){unsigned char jump[]={0x48,0xB8,0,0,0,0,0,0,0,0,0xFF,0xE0};memcpy(jump+2,&target.second,8);memcpy(reinterpret_cast<void*>(base+target.first),jump,sizeof jump);}
    put<uintptr_t>(base+0x123C2B8,uintptr_t(&ResetEvent));
    memcpy(reinterpret_cast<void*>(base+0x83A930),activation::ThreadEntryBytes,sizeof activation::ThreadEntryBytes);
    put<uintptr_t>(base+0x2025F50,alloc(4096));
    unsigned char endStub[]={0x48,0xB8,0,0,0,0,0,0,0,0,0xFF,0xE0};
    const uintptr_t endAddress=uintptr_t(&nativeEndThreadDouble);memcpy(endStub+2,&endAddress,8);memcpy(reinterpret_cast<void*>(base+0xF31158),endStub,sizeof endStub);
    // Exact archived full runner, not a surrogate instruction reporting a fake
    // RIP. Only its external synchronization/IAT services are owned doubles.
    memcpy(reinterpret_cast<void*>(base+0x834D10),ports::RunnerBytes,sizeof ports::RunnerBytes);
    auto payload=reinterpret_cast<unsigned char*>(base+0x508B40);memcpy(payload,ports::LoadPrefixBytes,sizeof ports::LoadPrefixBytes);
    // The fixture payload executes the real ten-byte native prologue, then its
    // explicit C++ body substitute and matching epilogue. Register exact unwind.
    const unsigned char tail[]={0x48,0xB8,0,0,0,0,0,0,0,0,0xFF,0xD0,0x48,0x83,0xC4,0x30,0x5F,0x48,0x8B,0x5C,0x24,0x08,0xC3};
    memcpy(payload+10,tail,sizeof tail);put<uintptr_t>(base+0x508B40+12,uintptr_t(&NativeLoadPayloadDouble));
    put<uintptr_t>(base+0x123C328,uintptr_t(&nativeSyncDouble));put<uintptr_t>(base+0x123C0D8,uintptr_t(&nativeSyncDouble));
    put<uintptr_t>(base+0x123C1D8,uintptr_t(&nativeSetEventDouble));put<uintptr_t>(base+0x123C1E0,uintptr_t(&nativeWaitDouble));put<uintptr_t>(base+0x2025268,alloc(4096));
    const unsigned char runnerUnwind[]={1,10,4,0,10,0x32,6,0x70,5,0x34,6,0};
    const unsigned char payloadUnwind[]={1,10,4,0,10,0x52,6,0x70,5,0x34,8,0};
    memcpy(reinterpret_cast<void*>(base+0x800),runnerUnwind,sizeof runnerUnwind);memcpy(reinterpret_cast<void*>(base+0x820),payloadUnwind,sizeof payloadUnwind);
    const unsigned char entryUnwind[]={1,12,4,0,12,0x72,8,0x70,7,0x60,6,0x30};
    memcpy(reinterpret_cast<void*>(base+0x840),entryUnwind,sizeof entryUnwind);
    const unsigned char bindUnwind[]={1,10,4,0,10,0x72,6,0x70,5,0x34,10,0};
    const unsigned char startUnwind[]={1,6,2,0,6,0x32,2,0x30};
    memcpy(reinterpret_cast<void*>(base+0x860),bindUnwind,sizeof bindUnwind);memcpy(reinterpret_cast<void*>(base+0x880),startUnwind,sizeof startUnwind);
    auto*table=new RUNTIME_FUNCTION[5]{{0x4DA240,0x4DA313,0x860},{0x508B40,0x508B40+10+sizeof tail,0x820},{0x834B60,0x834BA9,0x880},{0x834D10,0x834E75,0x800},{0x83A930,0x83AA2D,0x840}};
    check(RtlAddFunctionTable(table,5,base)!=FALSE,"native copied runner and payload have Win64 runtime unwind records");
    DWORD old=0;for(uintptr_t pageRva:{0x4DA000u,0x50C000u,0x194000u,0x833000u})check(VirtualProtect(reinterpret_cast<void*>(base+pageRva),4096,PAGE_EXECUTE_READ,&old),"owned native initializer and explicit constructor stubs RX");check(VirtualProtect(reinterpret_cast<void*>(base+0x83A000),4096,PAGE_EXECUTE_READ,&old)&&VirtualProtect(reinterpret_cast<void*>(base+0xF31000),4096,PAGE_EXECUTE_READ,&old),"owned native thread entry and endthread substitute RX");check(VirtualProtect(reinterpret_cast<void*>(base+0x834000),4096,PAGE_EXECUTE_READ,&old)&&VirtualProtect(reinterpret_cast<void*>(base+0x508000),4096,PAGE_EXECUTE_READ,&old),"owned native code RX before publishing hardware addresses");
    check(FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base+0x834000),4096)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base+0x508000),4096),"owned code instruction cache flushed");
}
static DWORD WINAPI embeddedEntry(void*p){auto&t=*static_cast<EmbeddedPort*>(p);if(t.role)return syntheticEmbeddedEntry(p);
    nativeFixtureTask=&t;
    if(scenario==L"start-wrong-wait"){SetEvent(t.ready);WaitForSingleObject(t.wake,INFINITE);SetEvent(t.wake);} // Native entry has not begun: no valid83A9D7 frame.
    __try {using Entry=DWORD(*)(void*);const DWORD result=reinterpret_cast<Entry>(base+0x83A930)(reinterpret_cast<void*>(t.object));check(result==0,"native runner DWORD result preserved");}
    __except(GetExceptionCode()==0xE014CC91||GetExceptionCode()==0xE014CC92?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){t.abnormal=true;InterlockedExchange(&loadException,1);}
    check(activationRouter.Snapshot(generationIndex+2,activationReport),"retained activation report");nativePortReport=activationReport.ports;
    if(scenario==L"start-observe"||scenario==L"start-wrong-wait"||scenario==L"start-stop"){check(!activationReport.selected&&!nativePortReport.captured,"refused/default start retains original834D10");return 0;}
    check(activationReport.selected&&activationReport.beforeNative&&activationReport.finally&&activationReport.caller==base+0x83A9DF,"native start published activation before native runner");
    check(bool(activationReport.abnormal)==t.abnormal&&bool(activationReport.after)==!t.abnormal&&activationReport.armed,"normal or exceptional original outcome preserved");
    check(nativePortReport.finished&&nativePortReport.restored&&!nativePortReport.uncertain&&!memcmp(nativePortReport.originalDr,nativePortReport.restoredDr,sizeof nativePortReport.originalDr),"worker sixDR restored");
    check(nativePortReport.captured==(t.abnormal?2u:4u),"actual worker four source points follow real parent captures");
    if(t.abnormal)check(nativePortReport.providerScopeAbandoned==1,"worker exception abandons incomplete task attribution");return t.abnormal?1:0;
}
static void nativeCtorDouble(uintptr_t control,uintptr_t payload,uintptr_t,uintptr_t){
    check(control==load+0x478&&payload==base+0x508B40,"actual archived native initializer passes Load constructor args");
    auto*t=new EmbeddedPort;embeddedPorts[0]=t;t->image=base;t->owner=load;t->control=control;t->callable=loadCallable;t->object=alloc(4096);
    t->ready=CreateEventW(nullptr,TRUE,FALSE,nullptr);t->wake=CreateEventW(nullptr,FALSE,FALSE,nullptr);t->completion=CreateEventW(nullptr,FALSE,TRUE,nullptr);
    put<uintptr_t>(control,t->object);put<uintptr_t>(control+8,alloc(4096));put<uintptr_t>(control+0x48,t->callable);put<DWORD>(control+0x50,1);put<DWORD>(control+0x54,0);put<DWORD>(control+0x68,1);put<uintptr_t>(control+0x60,uintptr_t(t->completion));
    put<uintptr_t>(t->object+0x30,control);put<uintptr_t>(t->object+0x38,base+0x834D10);put<LONG>(t->object+8,1);put<uintptr_t>(t->object+0x20,uintptr_t(t->wake));
    t->handle=CreateThread(nullptr,0,embeddedEntry,t,CREATE_SUSPENDED,&t->tid);put<DWORD>(t->object+0x10,t->tid);put<uintptr_t>(t->object+0x18,uintptr_t(t->handle));
    if(scenario==L"start-stop")startAdapter->Stop();
    check(ResumeThread(t->handle)!=DWORD(-1)&&WaitForSingleObject(t->ready,10000)==WAIT_OBJECT_0,"real worker reaches its unsignaled wait before original native start");
}
static void runNativeLoadStart(){using Start=void(*)(void*);reinterpret_cast<Start>(base+0x4DA240)(reinterpret_cast<void*>(load));}
static void verifyStartReceipt(){
    check(startAdapter->Snapshot(startReport),"actual native parent capture receipt");
    check(startReport.armed&&startReport.captured==(scenario==L"start-stop"?1u:2u)&&startReport.samples[0].accepted&&(scenario==L"start-stop"||startReport.samples[1].accepted)&&startReport.finally&&startReport.restored&&!startReport.uncertain&&
        !memcmp(startReport.originalDr,startReport.restoredDr,sizeof startReport.originalDr),"two actual source contexts and parent sixDR restoration");
    check(startReport.samples[0].rip==base+0x4DA240&&startReport.samples[0].rcx==load&&(scenario==L"start-stop"||(startReport.samples[1].rip==base+0x834B60&&startReport.samples[1].rcx==load+0x478)),"actual bind/start captured CPU arguments");
    if(scenario==L"start-stop")check(startReport.error==nativeStart::Error::Stopped&&startReport.stopped&&!startReport.publicationClaimed&&!startReport.published,"Stop before start closes atomic publication claim and forwards original");
    else if(scenario==L"start-wrong-wait")check(startReport.error==nativeStart::Error::WaitStack&&!startReport.published&&startReport.workerSuspended&&startReport.workerResumed,"worker without exact native initial wait continuation rejected without changing runner");
    else check(startReport.error==nativeStart::Error::None&&startReport.waitStackVerified&&startReport.eventUnsignaled&&startReport.workerResumed&&startReport.eventType==1&&startReport.eventState==0&&bool(startReport.published)==(scenario!=L"start-observe"),"suspended native wait+real auto-reset nonsignaled event controls opt-in CAS");
    const auto file=nativeReceiptFolder+L"/start-"+std::to_wstring(generationIndex)+L".bin";FILE*f=nullptr;check(_wfopen_s(&f,file.c_str(),L"wb")==0&&f,"start raw receipt file");if(f){check(fwrite(&startReport,1,sizeof startReport,f)==sizeof startReport,"entire native-start report persisted");fclose(f);}
    printf("{\"native_start_generation\":%u,\"captured\":%u,\"published\":%u,\"restored\":%u,\"wait_verified\":%u,\"error\":%u,\"unwind_frames\":%u}\n",generationIndex+2,startReport.captured,startReport.published,startReport.restored,startReport.waitStackVerified,unsigned(startReport.error),startReport.unwindFrames);
}
