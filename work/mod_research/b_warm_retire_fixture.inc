    b_warm_retire::Report retired{};b_warm_retire::Snapshot(retired);
    const bool expect=which==L"success-new"||which==L"restore-conflict";
    check(bool(retired.sealed)==expect,"completion and authenticated paired User AFTER required");
    check(bool(retired.restored)==(which==L"success-new"),"all six slots restoration exact");
    check(bool(retired.restoreFailed)==(which==L"restore-conflict"),"foreign slot retained as uncertain");
    if(expect){
        for(unsigned i=0;i<6;++i){const auto&h=s.hooks.entries[i];MEMORY_BASIC_INFORMATION m{};check(VirtualQuery(const_cast<void**>(h.binding.slot),&m,sizeof m)==sizeof m&&m.Protect==h.protection,"original slot page protection");check(*h.binding.slot==(which==L"restore-conflict"&&i==1?reinterpret_cast<void*>(0x12345678):h.binding.original),"exact restored pointer or retained foreign conflict");}
        check(retired.attempt==s.attempt&&retired.userCall==wire.planningUserCall&&retired.identityCall==s.identity.workerCall&&retired.loadCall==s.lifecycle.completedCall,"seal actual complete receipts");
        checkpoint_authorized_forward_admission::Report admissionBefore{},admissionAfter{};check(checkpoint_complete_live_owner::owner.admission.Snapshot(admissionBefore),"admission before late calls");
        DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(world),4096,PAGE_NOACCESS,&old)!=0,"old world protected");
        warmLate=true;
        const uintptr_t cached[]={uintptr_t(&CheckpointLoadDispatchBridge0),uintptr_t(&CheckpointLoadDispatchBridge1),uintptr_t(&CheckpointLoadDispatchBridge2),uintptr_t(&CheckpointLoadDispatchBridge3),uintptr_t(&CheckpointLoadWorkerBridge0),uintptr_t(&CheckpointLoadWorkerBridge1)};
        using Call=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
        for(unsigned i=0;i<6;++i){reinterpret_cast<Call>(cached[i])(world,world,world,world);check(warmLateBodies[i]==1,"cached original exactly once without observers");}
        ns::Report late{};session.Snapshot(late);check(!memcmp(&s.bytes,&late.bytes,sizeof s.bytes)&&!memcmp(&s.lifecycle,&late.lifecycle,sizeof s.lifecycle)&&!memcmp(&s.identity,&late.identity,sizeof s.identity),"completed receipts immutable after six cached calls");
        check(!memcmp(s.dispatchBefore,late.dispatchBefore,sizeof s.dispatchBefore)&&!memcmp(s.dispatchAfter,late.dispatchAfter,sizeof s.dispatchAfter)&&!late.activeDispatch&&!late.activeWorker&&!late.activeRead,"sealed Session never readmits");
        check(checkpoint_complete_live_owner::owner.admission.Snapshot(admissionAfter)&&!memcmp(&admissionBefore,&admissionAfter,sizeof admissionBefore),"admission unchanged by transparent User");
        check(!b_warm_retire::Bind(session,planning),"no reset or second Bind");
        b_warm_retire::Report afterRetire{};b_warm_retire::Snapshot(afterRetire);check(!memcmp(&retired,&afterRetire,sizeof retired),"retirement receipt frozen");
    }else{
        check(!s.hooksRestored,"failed completion keeps observations");
        for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==reinterpret_cast<void*>(wire.hooks[i].hook),"noncomplete source kept");
    }
    printf("WARM sealed=%u restored=%u uncertain=%u late=%u,%u,%u,%u,%u,%u\n",retired.sealed,retired.restored,retired.restoreFailed,warmLateBodies[0],warmLateBodies[1],warmLateBodies[2],warmLateBodies[3],warmLateBodies[4],warmLateBodies[5]);
