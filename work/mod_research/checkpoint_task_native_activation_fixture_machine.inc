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
static BOOL nativeSetEventDouble(HANDLE){if(nativeFixtureTask)put<DWORD>(nativeFixtureTask->control+0x54,1);return TRUE;}
static DWORD nativeWaitDouble(HANDLE,DWORD){return WAIT_OBJECT_0;}
static void foreignExceptionInNativeBody(){__try{RaiseException(0xE0149A01,0,0,nullptr);}__except(GetExceptionCode()==0xE0149A01?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){++foreignSehCaught;}}
extern "C" void NativeLoadPayloadBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    if(scenario==L"ports-foreign-seh")foreignExceptionInNativeBody();TaskFixturePayloadBody(self,a,b,c);
}
static void nativeEndThreadDouble(unsigned){}
static void prepareNativeMachine(){
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
    auto*table=new RUNTIME_FUNCTION[3]{{0x508B40,0x508B40+10+sizeof tail,0x820},{0x834D10,0x834E75,0x800},{0x83A930,0x83AA2D,0x840}};
    check(RtlAddFunctionTable(table,3,base)!=FALSE,"native copied runner and payload have Win64 runtime unwind records");
    DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(base+0x83A000),4096,PAGE_EXECUTE_READ,&old)&&VirtualProtect(reinterpret_cast<void*>(base+0xF31000),4096,PAGE_EXECUTE_READ,&old),"owned native thread entry and endthread substitute RX");check(VirtualProtect(reinterpret_cast<void*>(base+0x834000),4096,PAGE_EXECUTE_READ,&old)&&VirtualProtect(reinterpret_cast<void*>(base+0x508000),4096,PAGE_EXECUTE_READ,&old),"owned native code RX before publishing hardware addresses");
    check(FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base+0x834000),4096)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base+0x508000),4096),"owned code instruction cache flushed");
}
static DWORD WINAPI embeddedEntry(void*p){auto&t=*static_cast<EmbeddedPort*>(p);if(t.role)return syntheticEmbeddedEntry(p);
    nativeFixtureTask=&t;put<DWORD>(t.control+0x50,0);put<DWORD>(t.control+0x68,1);
    // No Initialize/Begin/Finish here. The actual archived thread entry fetches
    // threadObject+38 only after its wait and invokes the production wrapper.
    __try {using Entry=DWORD(*)(void*);const DWORD result=reinterpret_cast<Entry>(base+0x83A930)(reinterpret_cast<void*>(t.object));check(result==0,"native runner DWORD result preserved across wrapper");}
    __except(GetExceptionCode()==0xE014CC91||GetExceptionCode()==0xE014CC92?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){t.abnormal=true;InterlockedExchange(&loadException,1);}
    check(activationRouter.Snapshot(generationIndex+2,activationReport),"snapshot automatic activation receipt");nativePortReport=activationReport.ports;
    check(activationReport.selected&&activationReport.beforeNative&&activationReport.finally&&(scenario==L"ports-stopped"||activationReport.caller==base+0x83A9DF),"native entry automatically selects same task before 834D98 and always finally");
    check(bool(activationReport.abnormal)==t.abnormal&&bool(activationReport.after)==!t.abnormal,"normal or exceptional original outcome preserved");
    if(scenario==L"ports-stopped"){check(activationReport.error==activation::Error::Stopped&&!activationReport.armed&&!nativePortReport.captured,"stopped automatic activation forwards without beginning");return 0;}
    check(activationReport.armed&&activationReport.error==activation::Error::None,"automatic Begin at original runner entry");
    check(nativePortReport.finished&&nativePortReport.restored&&!nativePortReport.uncertain&&nativePortReport.codeUnchanged&&
        !memcmp(nativePortReport.originalDr,nativePortReport.restoredDr,sizeof nativePortReport.originalDr),"automatic finally restores and verifies all six DR");
    const unsigned expected=t.abnormal?2u:4u;check(nativePortReport.captured==expected,"four native instruction hits without manual Begin");
    for(unsigned i=0;i<expected;++i){const auto&sample=nativePortReport.samples[i];check(sample.delivered&&sample.accepted&&sample.rip==base+ports::PointRvas[i]&&sample.thread==GetCurrentThreadId(),"real CONTEXT enters frozen Provider");}
    const auto& source=nativePortReport.samples[1];const auto& actual=TaskPortsPayloadSnapshot;
    for(unsigned i=1;i<16;++i)check(actual.gpr[i]==source.gpr[i]-(i==4?104:0),"native CONTEXT resumes GPR through hardware port");
    check(actual.gpr[0]==uintptr_t(&NativeLoadPayloadDouble)&&!memcmp(actual.xmm,source.xmm,sizeof actual.xmm)&&actual.mxcsr==source.mxcsr,"native context preserves XMM/MXCSR and explicit RAX tail");
    constexpr std::uint64_t arithmeticFlags=0x8D5,rf=0x10000;
    check((actual.flags&~(arithmeticFlags|rf))==(source.rawFlags&~(arithmeticFlags|rf)),"nonarithmetic flags retained");
    if(t.abnormal)check(nativePortReport.providerScopeAbandoned==1&&nativePortReport.error==ports::Error::Missing,"original exception abandons only incomplete attribution");
    else check(nativePortReport.error==ports::Error::None&&!activationReport.resultRax,"normal original result and capture");
    return t.abnormal?1:0;
}
static void verifyActivationUnbound(){
    tp::Report old{},after{};provider.Snapshot(generationIndex+2,old);activation::Statistics pre{},post{};activationRouter.SnapshotStatistics(pre);
    EmbeddedPort t{};t.control=alloc(4096);t.object=alloc(4096);t.callable=otherCallable;nativeFixtureTask=&t;
    put<uintptr_t>(t.object+0x30,t.control);put<uintptr_t>(t.object+0x38,uintptr_t(activation::Router::Entry()));put<LONG>(t.object+8,1);
    put<uintptr_t>(t.control+8,alloc(4096));put<uintptr_t>(t.control+0x48,t.callable);put<DWORD>(t.control+0x68,1);
    const unsigned priorBodies=otherBodies;nativeUnboundExecuting=true;using Entry=DWORD(*)(void*);check(reinterpret_cast<Entry>(base+0x83A930)(reinterpret_cast<void*>(t.object))==0,"unbound actual native thread entry forwards original");
    nativeUnboundExecuting=false;check(otherBodies==priorBodies+1,"unbound task body called exactly once with native RCX");nativeFixtureTask=nullptr;provider.Snapshot(generationIndex+2,after);activationRouter.SnapshotStatistics(post);
    check(!memcmp(&old,&after,sizeof old)&&post.unknownForwarded==pre.unknownForwarded+1&&post.bridge.native_started==pre.bridge.native_started+1&&post.bridge.native_returned==pre.bridge.native_returned+1&&post.bridge.finally_calls==pre.bridge.finally_calls+1&&!post.bridge.active&&!post.bridge.cleanup_faults,"unbound original once, native finally, no new provider receipt");
    const auto path=nativeReceiptFolder+L"/activation-"+std::to_wstring(generationIndex)+L".bin";FILE*f=nullptr;check(_wfopen_s(&f,path.c_str(),L"wb")==0&&f,"automatic activation raw receipt");if(f){check(fwrite(&activationReport,1,sizeof activationReport,f)==sizeof activationReport,"write automatic activation receipt");fclose(f);}
}
