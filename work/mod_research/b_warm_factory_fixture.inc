static void factoryNeed(bool ok,const char*stage){
    checkpoint_complete_live_owner::Report r{};GetCheckpointCompleteLiveOwnerReport(&r);
    checkpoint_live_runtime_guards_v2::Report g{};checkpoint_complete_live_owner::owner.guards.Snapshot(g);
    ns::Report s{};session.Snapshot(s);
    printf("FACTORY %s ok=%u Owner=%llu Session=%llu Guard=%u/%u req=%s bytes=%ld life=%ld identity=%ld planning=%llu\n",stage,unsigned(ok),r.value[1],r.value[13],unsigned(g.first_error),unsigned(g.last_error),s.request.stage,s.bytes.error,s.lifecycle.error,s.identity.error,r.value[unsigned(checkpoint_complete_live_owner::Value::PlanningError)]);
    if(!ok){for(unsigned i=0;i<29;++i)printf("G%u=%u/%u ",i,g.accepted[i],g.calls[i]);printf("\n");
        for(unsigned i=0;i<s.request.boundary.checkCount;++i){auto&c=s.request.boundary.checks[i];if(c.error!=bd::Error::None)printf("boundary %s observed=%llu expected=%llu\n",c.field,c.observed,c.expected);}
        fflush(stdout);ExitProcess(95);
    }
}
int wmain(int argc,wchar_t**argv){
    if(argc!=6)return 2;SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
    if(!configureProfile(argv[2]))return 3;
    std::ifstream input(argv[2],std::ios::binary);archive.assign(std::istreambuf_iterator<char>(input),{});buffer.resize(archive.size());
    checkpoint_complete_live_owner::Config c{};factoryConfig(c,argv);scenario=L"success-new";
    const auto&p=b_warm_profile::Get();layout.config.year=p.before.year;layout.config.month=p.before.month;layout.config.day=p.before.day;layout.config.force=p.currentForce;
    put<WORD>(world+0x34,p.before.year);put<BYTE>(world+0x36,p.before.month);put<BYTE>(world+0x37,p.before.day);put<BYTE>(world+0x3a,p.currentForce);
    storage=c.storage;originalList=layout.list;originalDialog=layout.dialog;
    const uintptr_t rv[]={0x12cc4d0,0x12db4e8,0x12cc9e0,0x12dbd90,0x138e8d0};
    void* originals[]={reinterpret_cast<void*>(&GuestSessionUserOriginal),reinterpret_cast<void*>(&GuestSessionMenuOriginal),reinterpret_cast<void*>(&GuestSessionGameOriginal),reinterpret_cast<void*>(&GuestSessionUpdateOriginal),reinterpret_cast<void*>(&GuestSessionWorkerOriginal),reinterpret_cast<void*>(&GuestSessionReadOriginal)};
    auto&f=checkpoint_complete_live_owner::fixtureAddresses;for(unsigned i=0;i<5;++i){f.originals[i]=originals[i];put<uintptr_t>(base+rv[i],uintptr_t(originals[i]));}
    f.menuCaller=uintptr_t(&GuestSessionMenuReturn);f.gameCaller=uintptr_t(&GuestSessionGameReturn);f.workerCaller=uintptr_t(&GuestSessionWorkerReturn);f.readCaller=uintptr_t(&GuestSessionReadReturn);f.updateCaller=uintptr_t(&GuestSessionUpdateReturn);f.parentCaller=0xAABBCC1234567890ull;GuestSessionParent=f.parentCaller;
    // Explicit self-owned ASM now dereferences these six *slot addresses*.
    GuestSessionSlots=reinterpret_cast<void**>(alloc(4096));for(unsigned i=0;i<6;++i)GuestSessionSlots[i]=reinterpret_cast<void*>(i<5?base+rv[i]:c.storageVtable+8);
    factoryNeed(!InstallCheckpointCompleteLiveOwner(&c),"Install configure reserve Arm");
    put<uintptr_t>(base+0x19e7310+0x48,layout.config.states[4]);
    factoryNeed(!invokeInitialUser(),"paired User native");ns::Report s{};session.Snapshot(s);factoryNeed(s.menuBound&&s.menuBound==1,"actual queue authorization and bind");
    put<std::uint64_t>(base+0x19e7310+0x10,6);put<uintptr_t>(stackArray+40,layout.config.menu);put<std::uint64_t>(base+0x19e7310+0x30,0);layout.setStage(bd::Stage::MenuAfter);
    GuestSessionMenuInvoke(layout.config.menu,0x1001,0x1002,0x1003);session.Snapshot(s);factoryNeed(s.request.menuObserved,"Menu AFTER full guards");
    const bool drift=std::wstring(argv[1])==L"guard-drift";
    if(drift)*reinterpret_cast<BYTE*>(base+CheckpointLiveSessionAnchors[0].rva)^=1;
    layout.setStage(bd::Stage::GameBefore);GuestSessionGameInvoke(layout.config.states[2],0x1001,0x1002,0x1003);session.Snapshot(s);
    if(drift){checkpoint_live_runtime_guards_v2::Report g{};checkpoint_complete_live_owner::owner.guards.Snapshot(g);b_warm_retire::Report retired{};b_warm_retire::Snapshot(retired);
        factoryNeed(g.first_error==checkpoint_live_runtime_guards_v2::Error::Image&&!s.casPublished&&!s.request.casAttempts&&!retired.sealed&&GetFileAttributesW(c.requestIntent)==INVALID_FILE_ATTRIBUTES,"actual source guard drift rejects before request CAS");
        factoryNeed(writeReport(argv[5]),"negative actual owner report");printf("{\"passed\":true,\"actual_guard_refused\":true,\"request_cas\":0}\n");return 0;
    }
    factoryNeed(s.casPublished&&s.request.read.matched,"Request CAS full guards storage");
    put<std::uint64_t>(base+0x19e7310+0x10,4);put<uintptr_t>(stackArray+16,title);put<uintptr_t>(stackArray+24,load);put<std::uint64_t>(base+0x19e7310+0x30,0);put<uintptr_t>(base+0x19e7310+0x48,load);
    invokeWorker(otherCallable);for(unsigned i=0;i<4;++i){GuestSessionUpdateInvoke(load,1,2,3);session.Snapshot(s);factoryNeed(!s.lifecycle.error&&!s.bytes.error,"Load update full guards");}
    session.Snapshot(s);factoryNeed(s.bytes.observedWorkerAndBytes&&s.lifecycle.receiptReady,"Bytes Load complete");
    DWORD prior=0;factoryNeed(VirtualProtect(reinterpret_cast<void*>(load),4096,PAGE_NOACCESS,&prior)!=0,"old Load protected");
    factoryNeed(!titleInvokeWithException(),"Title native");session.Snapshot(s);factoryNeed(s.identity.receiptReady,"Identity full guards");
    factoryNeed(VirtualProtect(reinterpret_cast<void*>(title),8192,PAGE_NOACCESS,&prior)!=0,"old Title protected");
    rebuildPlanning();factoryNeed(!invokePlanningUser(),"new User paired");session.Snapshot(s);b_warm_retire::Report retired{};b_warm_retire::Snapshot(retired);
    factoryNeed(retired.sealed&&retired.restored&&!retired.restoreFailed,"planning full guards seal restore");
    checkpoint_complete_live_owner::Report out{};GetCheckpointCompleteLiveOwnerReport(&out);checkpoint_live_runtime_guards_v2::Report guards{};checkpoint_complete_live_owner::owner.guards.Snapshot(guards);
    constexpr unsigned starts[]={0,6,13,18,21,27,29};
    for(unsigned family=0;family<6;++family){unsigned calls=0;for(unsigned i=starts[family];i<starts[family+1];++i){calls+=guards.calls[i];factoryNeed(guards.calls[i]==guards.accepted[i],"all called real guards accepted");}factoryNeed(calls>0,"each real guard family executed");printf("GUARD_FAMILY %u calls=%u\n",family,calls);}
    printf("FACTORY_RECEIPT installed=%llu state=%llu guards=%llu storage=%llu\n",out.value[unsigned(checkpoint_complete_live_owner::Value::Installed)],out.value[unsigned(checkpoint_complete_live_owner::Value::SessionState)],out.value[unsigned(checkpoint_complete_live_owner::Value::GuardChecks)],out.value[unsigned(checkpoint_complete_live_owner::Value::StorageValidations)]);
    factoryNeed(!guards.failures&&!out.value[unsigned(checkpoint_complete_live_owner::Value::GuardError)]&&!failures,"no guard or fixture failures");
    for(unsigned i=0;i<6;++i)factoryNeed(*reinterpret_cast<void**>(GuestSessionSlots[i])==originals[i],"restored actual separate slot");
    factoryNeed(writeReport(argv[5]),"actual full owner report output");
    printf("{\"passed\":true,\"actual_factory_install\":true,\"full_attachment_guards\":true,\"native_business_double\":true,\"game_access\":false}\n");return 0;
}
