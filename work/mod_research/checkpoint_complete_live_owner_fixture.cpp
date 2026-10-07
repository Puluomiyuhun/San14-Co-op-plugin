// Includes the actual owner implementation. Fixture macros only affect native
// labels/environment in frozen components, never owner Stop/report logic.
#include "checkpoint_complete_live_owner.cpp"
#include "checkpoint_complete_live_owner_chain_authorized.inc"
#include <fstream>
#include <thread>
#include "checkpoint_live_runtime_guards_profile.h"
extern "C" {std::uint64_t BindingFixtureGeneration=1;void BindingFixtureContextInit();}
alignas(16) static uintptr_t ownerFactoryVtable[16]{},ownerFactoryStorage[2]{};
static void factoryEndpoint(checkpoint_live_storage_binding::Endpoint&endpoint,void*address){endpoint.address=uintptr_t(address);memcpy(endpoint.first32,address,32);}
static void factoryConfig(checkpoint_complete_live_owner::Config&c,wchar_t**argv){
    setup();scenario=L"player-pending";
    for(const auto&a:CheckpointLiveSessionAnchors)memcpy(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size);
    for(const auto&a:CheckpointNativeQueueAnchors)memcpy(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size);
    const auto manager=base+0x19e7310;put<std::uint64_t>(manager+0x10,5);put<std::uint64_t>(manager+0x18,16);put<std::uint64_t>(manager+0x30,0);put<std::uint64_t>(manager+0x38,0);put<uintptr_t>(manager+0x40,0);put<uintptr_t>(manager+0x48,0);put<DWORD>(cache+8,0);
    c.pid=GetCurrentProcessId();c.birth=checkpoint_complete_live_owner::processBirth();c.base=base;c.attempt=layout.config.attempt;c.epoch=17;c.generation=17;
    memset(c.attachment,0xa1,16);memset(c.attachment+16,0xb2,16);memset(c.ownerBinding,0x63,32);memset(c.nonce,0x37,32);memcpy(c.gameSha256,checkpoint_live_runtime_guards_profile::image_sha,32);
    memcpy(c.states,layout.config.states,sizeof c.states);c.root=root;c.world=world;c.cache=cache;c.keyboard=layout.config.keyboard;c.toolbar=layout.toolbar;c.panel=layout.panel;c.stack=stackArray;c.stackCapacity=16;c.rng=layout.config.expectedRng;
    wcscpy_s(c.localPath,argv[2]);wcscpy_s(c.requestIntent,argv[3]);wcscpy_s(c.identityIntent,argv[4]);const std::wstring install=std::wstring(argv[3])+L".install";wcscpy_s(c.installIntent,install.c_str());
    c.storageModuleCount=1;auto&m=c.storageModules[0];m.base=uintptr_t(GetModuleHandleW(nullptr));GetModuleFileNameW(nullptr,m.path,1024);
    const auto*pe=reinterpret_cast<const IMAGE_NT_HEADERS64*>(m.base+reinterpret_cast<const IMAGE_DOS_HEADER*>(m.base)->e_lfanew);m.sizeOfImage=pe->OptionalHeader.SizeOfImage;m.timestamp=pe->FileHeader.TimeDateStamp;
    std::ifstream ownFile(m.path,std::ios::binary);std::vector<unsigned char> exe((std::istreambuf_iterator<char>(ownFile)),{});m.fileSize=exe.size();check(native_storage_read::Sha256(exe.data(),exe.size(),m.fileSha256),"owned module file SHA");check(native_storage_read::Sha256(reinterpret_cast<void*>(m.base),4096,m.headerSha256),"owned module header SHA");
    factoryEndpoint(c.contextInit,reinterpret_cast<void*>(&BindingFixtureContextInit));factoryEndpoint(c.exists,reinterpret_cast<void*>(&exists));factoryEndpoint(c.fileSize,reinterpret_cast<void*>(&fileSize));factoryEndpoint(c.read,reinterpret_cast<void*>(&GuestSessionReadOriginal));factoryEndpoint(c.ownedReadBridge,reinterpret_cast<void*>(&CheckpointLoadWorkerBridge1));
    c.storage=uintptr_t(ownerFactoryStorage);c.storageVtable=uintptr_t(ownerFactoryVtable);c.storageCounter=uintptr_t(&BindingFixtureGeneration);c.cachedGeneration=1;ownerFactoryStorage[0]=c.storageVtable;ownerFactoryVtable[1]=c.read.address;ownerFactoryVtable[13]=c.exists.address;ownerFactoryVtable[15]=c.fileSize.address;
    memcpy(c.contextCode,reinterpret_cast<void*>(c.contextInit.address),sizeof c.contextCode);put<uintptr_t>(base+0x123cb28,c.contextInit.address);put<uintptr_t>(base+0x18d08b8,base+0x2fcb90);put<std::uint64_t>(base+0x18d08c0,1);put<uintptr_t>(base+0x18d08c8,c.storage);constexpr char version[]="STEAMREMOTESTORAGE_INTERFACE_VERSION014";memcpy(reinterpret_cast<void*>(base+0x12aa6b8),version,sizeof version);
    constexpr uintptr_t slots[]={0x12cc4d0,0x12db4e8,0x12cc9e0,0x12dbd90,0x138e8d0};constexpr uintptr_t orig[]={0x3f9b00,0x4aa200,0x3f8140,0x4a85c0,0x4fabc0};for(unsigned i=0;i<5;++i)put<uintptr_t>(base+slots[i],base+orig[i]);
    auto&fixture=checkpoint_complete_live_owner::fixtureAddresses;fixture.userOriginal=&GuestSessionUserOriginal;fixture.queueNative=queueNativeOwned;fixture.hardwareSite=uintptr_t(&HwbpFixtureBeforeCall);fixture.userCaller=uintptr_t(&GuestSessionUserReturn);
}
static bool writeReport(const wchar_t*path){
    checkpoint_complete_live_owner::Report r{};
    if(GetCheckpointCompleteLiveOwnerReport(&r))return false;
    std::ofstream file(path,std::ios::binary);file.write(reinterpret_cast<const char*>(&r),sizeof r);return bool(file);
}
int wmain(int argc,wchar_t**argv){
    if(argc!=6)return 2;const std::wstring which=argv[1];
    if(which==L"factory-arm-player-refusal"){
        using namespace checkpoint_complete_live_owner;Config c{};factoryConfig(c,argv);
        check(InstallCheckpointCompleteLiveOwner(&c)==0,"actual production factory order succeeds with real guards and Gate");
        Report initial{};check(!GetCheckpointCompleteLiveOwnerReport(&initial),"actual installed report");
        check(initial.value[unsigned(Value::Installed)]&&initial.value[unsigned(Value::Armed)]&&initial.value[unsigned(Value::InstallIntentDurable)]&&initial.value[unsigned(Value::StorageOpened)]&&!initial.value[unsigned(Value::GuardError)],"actual factory reaches durable Arm");
        GuestSessionSlots=reinterpret_cast<void**>(base+0x12cc4d0);put<uintptr_t>(base+0x19e7310+0x48,layout.config.states[4]);put<LONG>(layout.toolbar+0x88,6);
        check(!invokeInitialUser(),"actual first User forwards original with native HWBP site");
        Report observed{};check(!GetCheckpointCompleteLiveOwnerReport(&observed),"post User report");
        check(observed.value[unsigned(Value::ControllerOriginalCalls)]==1&&observed.value[unsigned(Value::HardwareCaptured)]==1&&observed.value[unsigned(Value::HardwareRestored)]==1&&!observed.value[unsigned(Value::QueueNativeCalls)]&&!observed.value[unsigned(Value::CasPublished)],"actual factory-wired pending rejects player's command without native load");
        check(RestoreCheckpointCompleteLiveOwnerBeforeCommit(nullptr)==0,"factory pre-CAS actual six-slot restore");check(writeReport(argv[5]),"binary factory report");
        printf("{\"owner_case\":\"%ls\",\"passed\":%s,\"game_access\":false,\"production_configure_success_tested\":true,\"guards_and_storage_gate\":\"real_implementations_owned_memory\",\"native_load_executed\":false}\n",argv[1],failures?"false":"true");return failures?1:0;
    }
    if(which==L"invalid-config"||which==L"stop-while-install-lock"){
        using namespace checkpoint_complete_live_owner;
        if(which==L"invalid-config"){
            Config invalid{};check(InstallCheckpointCompleteLiveOwner(&invalid)!=0,"production install refuses unbound config");
            check(InstallCheckpointCompleteLiveOwner(&invalid)!=0,"owner immutable once");
        }else{
            // Simulate an installer holding its control mutex. Stop must revoke
            // atomically BEFORE waiting for that mutex, not after publication.
            AcquireSRWLockExclusive(&owner.control);volatile LONG started=0,done=0;
            std::thread stopper([&]{InterlockedExchange(&started,1);StopCheckpointCompleteLiveOwner(nullptr);InterlockedExchange(&done,1);});
            while(!InterlockedCompareExchange(&started,0,0))Sleep(1);
            for(unsigned i=0;i<500&&!InterlockedCompareExchange(&owner.stop,0,0);++i)Sleep(1);
            check(InterlockedCompareExchange(&owner.stop,0,0)==1&&!InterlockedCompareExchange(&done,0,0),"Stop atomic revocation precedes serialized wait");
            ReleaseSRWLockExclusive(&owner.control);stopper.join();
            Config invalid{};check(InstallCheckpointCompleteLiveOwner(&invalid)!=0,"pre-install Stop cannot revive attempt");
        }
        Report r{};check(!GetCheckpointCompleteLiveOwnerReport(&r),"actual production report export");
        check(!r.value[unsigned(Value::Armed)]&&!r.value[unsigned(Value::QueueNativeCalls)]&&!r.value[unsigned(Value::CasPublished)],"no native drive on refusal");
        check(writeReport(argv[5]),"binary Report copied");printf("{\"owner_case\":\"%ls\",\"passed\":%s,\"game_access\":false,\"production_configure_success_tested\":false}\n",argv[1],failures?"false":"true");return failures?1:0;
    }
    const int result=CompleteOwnerChainMain(5,argv);
    ns::Report s{};session.Snapshot(s);
    // These are owner diagnostic binding fields, not fabricated upstream receipts.
    checkpoint_complete_live_owner::owner.config.attempt=s.attempt;
    checkpoint_complete_live_owner::owner.config.epoch=17;
    checkpoint_complete_live_owner::Report wire{};check(!GetCheckpointCompleteLiveOwnerReport(&wire),"actual Owner exports copy full chain receipts");
    using V=checkpoint_complete_live_owner::Value;
    check(wire.value[unsigned(V::CasPublished)]==s.casPublished&&wire.value[unsigned(V::IdentityReady)]==s.identity.receiptReady,"wire copies actual Session results");
    check(!memcmp(wire.bytesReceipt,&s.bytes,sizeof s.bytes)&&!memcmp(wire.lifecycleReceipt,&s.lifecycle,sizeof s.lifecycle)&&!memcmp(wire.identityReceipt,&s.identity,sizeof s.identity),"pointer-free full receipts copied exactly");
    check(!wire.value[unsigned(V::ReadyAuthorized)]&&!wire.value[unsigned(V::FullWorldVerified)]&&!wire.value[unsigned(V::InputExclusionProven)],"no readiness authority invented");
    if(s.casPublished){
        check(RestoreCheckpointCompleteLiveOwnerBeforeCommit(nullptr)!=0,"unified owner refuses post-CAS restore");
        ns::Report after{};session.Snapshot(after);check(after.stopRequested&&!after.hooksRestored,"unified Stop retains observers");
        for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==reinterpret_cast<void*>(wire.hooks[i].hook),"same six bridges retained");
    }
    check(writeReport(argv[5]),"binary actual owner Report written");
    printf("{\"owner_case\":\"%ls\",\"passed\":%s,\"game_access\":false,\"upstream_receipts_fabricated\":false,\"production_configure_success_tested\":false,\"environment_guards\":\"existing_owned_fixture_doubles\"}\n",argv[1],!failures&&!result?"true":"false");return failures||result?1:0;
}
