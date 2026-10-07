namespace ports=checkpoint_task_native_ports;
static ports::Context* nativePortContext=nullptr;
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
static void prepareNativeMachine(){
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
    auto*table=new RUNTIME_FUNCTION[2]{{0x508B40,0x508B40+10+sizeof tail,0x820},{0x834D10,0x834E75,0x800}};
    check(RtlAddFunctionTable(table,2,base)!=FALSE,"native copied runner and payload have Win64 runtime unwind records");
    DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(base+0x834000),4096,PAGE_EXECUTE_READ,&old)&&VirtualProtect(reinterpret_cast<void*>(base+0x508000),4096,PAGE_EXECUTE_READ,&old),"owned native code RX before publishing hardware addresses");
    check(FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base+0x834000),4096)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base+0x508000),4096),"owned code instruction cache flushed");
}
static DWORD WINAPI embeddedEntry(void*p){auto&t=*static_cast<EmbeddedPort*>(p);if(t.role)return syntheticEmbeddedEntry(p);
    nativeFixtureTask=&t;put<DWORD>(t.control+0x50,0);put<DWORD>(t.control+0x68,1);nativePortContext=new ports::Context;
    ports::Config c{&provider,base,generationIndex+2,1000};
    if(scenario==L"ports-bad-profile"){
        DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(base+0x834000),4096,PAGE_READWRITE,&old),"fixture-only corrupt code candidate");*reinterpret_cast<unsigned char*>(base+0x834D10)^=1;
        check(VirtualProtect(reinterpret_cast<void*>(base+0x834000),4096,PAGE_EXECUTE_READ,&old),"corrupt candidate RX");auto*bad=new ports::Context;check(!ports::Initialize(*bad,c),"exact native profile rejects mismatching executable byte");
        check(VirtualProtect(reinterpret_cast<void*>(base+0x834000),4096,PAGE_READWRITE,&old),"restore owned candidate");*reinterpret_cast<unsigned char*>(base+0x834D10)^=1;
        check(VirtualProtect(reinterpret_cast<void*>(base+0x834000),4096,PAGE_EXECUTE_READ,&old)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base+0x834000),4096),"restored original RX fixture bytes");
    }
    check(ports::Initialize(*nativePortContext,c),"native capture binds actual previously recorded Load task");
    if(scenario==L"ports-stopped")ports::Stop(*nativePortContext);
    const bool armed=ports::Begin(*nativePortContext);check(armed==(scenario!=L"ports-stopped"),"actual target thread arms four execute-breakpoint slots");
    // The Windows context (not this function) supplies all captured registers.
    // No Provider::Observe call here, before, inside, or after the native runner.
    __try {__try {using Runner=DWORD(*)(void*,void*);reinterpret_cast<Runner>(base+0x834D10)(reinterpret_cast<void*>(t.object),reinterpret_cast<void*>(t.control));}
        __finally {if(armed)ports::Finish(*nativePortContext);}}
    __except(GetExceptionCode()==0xE014CC91||GetExceptionCode()==0xE014CC92?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){t.abnormal=true;InterlockedExchange(&loadException,1);}
    check(ports::Snapshot(*nativePortContext,nativePortReport),"copy actual hardware-port receipt");
    if(armed){check(nativePortReport.finished&&nativePortReport.restored&&!nativePortReport.uncertain&&nativePortReport.codeUnchanged&&
        !memcmp(nativePortReport.originalDr,nativePortReport.restoredDr,sizeof nativePortReport.originalDr),"all six DR values restored and exact archived code unchanged");
        const auto expected=t.abnormal?2u:4u;check(nativePortReport.captured==expected,"actual CPU hardware hits follow native vcall/payload/return/done order");
        for(unsigned i=0;i<expected;++i){const auto&sample=nativePortReport.samples[i];check(sample.delivered&&sample.accepted&&sample.rip==base+ports::PointRvas[i]&&sample.thread==GetCurrentThreadId()&&sample.gpr[4]!=0,"real CONTEXT delivered directly into production Provider");}
        const auto& source=nativePortReport.samples[1];const auto& actual=TaskPortsPayloadSnapshot;
        for(unsigned i=1;i<16;++i)check(actual.gpr[i]==source.gpr[i]-(i==4?104:0),"Windows CONTEXT resumes every GPR across VEH and actual native prologues");
        check(actual.gpr[0]==uintptr_t(&NativeLoadPayloadDouble),"RAX changed only by explicit fixture call tail");
        check(!memcmp(actual.xmm,source.xmm,sizeof actual.xmm)&&actual.mxcsr==source.mxcsr,"all sixteen XMM and MXCSR survive actual hardware capture");
        constexpr std::uint64_t arithmeticFlags=0x8D5,rf=0x10000;
        check((actual.flags&~(arithmeticFlags|rf))==(source.rawFlags&~(arithmeticFlags|rf)),"non-arithmetic native flags survive VEH; stack SUB legitimately changes arithmetic flags");
        if(t.abnormal)check(nativePortReport.providerScopeAbandoned==1&&nativePortReport.error==ports::Error::Missing,"native exception leaves incomplete source receipt and explicitly retires TLS attribution");
        else check(nativePortReport.error==ports::Error::None,"normal native runner port has no hidden capture error");
    }else check(nativePortReport.error==ports::Error::Stopped&&!nativePortReport.entered&&!nativePortReport.captured,"pre-arm Stop performs no native capture");
    return t.abnormal?1:0;
}
