    ns::Config c{};c.request.boundary=layout.config;c.request.boundary.menu=0;c.request.localPath=argv[2];c.request.intentPath=argv[3];memset(c.request.ownerBinding,0x63,32);c.request.validate=requestGuard;
    c.request.storage={reinterpret_cast<void*>(storage),exists,fileSize,reinterpret_cast<native_storage_read::FileRead>(&GuestSessionReadOriginal),storageValid,nullptr};
    c.bytes.base=base;c.bytes.storage=storage;c.bytes.storageVtable=storage+16;c.bytes.readMethod=uintptr_t(&GuestSessionReadOriginal);c.bytes.attemptToken=layout.config.attempt;c.bytes.validateAttachment=byteGuard;c.bytes.fixtureWorkerCaller=uintptr_t(&GuestSessionWorkerReturn);c.bytes.fixtureReadCaller=uintptr_t(&GuestSessionReadReturn);c.bytes.fixtureParentCaller=0xAABBCC1234567890ull;GuestSessionParent=c.bytes.fixtureParentCaller;
    c.lifecycle.base=base;c.lifecycle.attemptToken=layout.config.attempt;c.lifecycle.validateAttachment=lifeGuard;c.lifecycle.fixtureUpdateCaller=uintptr_t(&GuestSessionUpdateReturn);
    c.identity.base=base;c.identity.attemptToken=layout.config.attempt;c.identity.intentPath=argv[4];memset(c.identity.ownerBinding,0x63,32);c.identity.validateAttachment=identityGuard;c.identity.fixtureWorkerCaller=uintptr_t(&GuestSessionWorkerReturn);
    c.validate=sessionGuard;c.userAfter=ad::Controller::UserAfter;c.context=&admission;
    pr::Config planningConfig{};planningConfig.base=base;planningConfig.attempt=layout.config.attempt;planningConfig.epoch=17;
    planningConfig.persistentRootState=layout.config.states[0];planningConfig.persistentMotorState=layout.config.states[1];planningConfig.previousUser=layout.config.states[4];planningConfig.session=&session;planningConfig.validate=planningGuard;planningConfig.fixtureCaller=uintptr_t(&GuestSessionUserReturn);
    if(scenario==L"stale-attempt")++planningConfig.attempt;
    check(planningConfig.syntheticReceipt==nullptr,"no synthetic upstream report supplied");
    check(pr::Initialize(planning,planningConfig),"observer bound to actual Session before hook installation");
    ad::Config ac{};ac.session=&session;ac.attempt=layout.config.attempt;ac.original=&GuestSessionUserOriginal;
    ac.expected_prefetch_site=uintptr_t(&HwbpFixtureBeforeCall)+(scenario==L"wrong-site"?1:0);
    ac.queue=nativeQueueDouble;ac.next_before=captureBefore;ac.next_after=pr::After;ac.next_context=&planning;ac.trace=admissionEvent;
    ac.pending.binding.attempt.fill(0xA1);ac.pending.binding.attachment.fill(0xB2);ac.pending.binding.owner_generation=17;
    ac.pending.profile_base=base;memcpy(ac.pending.states,layout.config.states,sizeof ac.pending.states);
    const auto span=[](uintptr_t address,size_t size){return pd::Span{reinterpret_cast<const std::uint8_t*>(address),size};};
    ac.pending.user=span(layout.config.states[4],0x668);ac.pending.toolbar=span(layout.toolbar,0x8C);
    ac.pending.game=span(layout.config.states[2],0x488);ac.pending.panel=span(layout.panel,0x1F8);
    ac.pending.manager=span(base+0x19E7310,0x50);ac.pending.stack=span(stackArray,0x30);ac.pending.queue={};ac.pending.load_cache=span(cache,0x3F4);
    ac.pending.expected_initial_cache_mode=0;
    ac.pending.resolve_created_queue=[](void*,uintptr_t address,std::size_t bytes)noexcept->pd::Span{++resolvedQueues;if(address!=pending||bytes!=16)return {};return {reinterpret_cast<const std::uint8_t*>(pending),16};};
    put<std::uint64_t>(base+0x19E7310+0x30,0);put<std::uint64_t>(base+0x19E7310+0x38,0);put<uintptr_t>(base+0x19E7310+0x40,0);
    put<uintptr_t>(base+0x19E7310+0x48,layout.config.states[4]);put<DWORD>(cache+8,0);
    hw::Config hardware{};hardware.binding=ac.pending.binding;hardware.site_rip=uintptr_t(&HwbpFixtureBeforeCall);
    check(hw::Initialize(hardwareContext,hardware),"hardware provider initialized for actual owned native site");ac.prefetch_provider=hw::MakeProvider(hardwareContext);
    if(scenario==L"player-pending"||scenario==L"restore-native-slot")put<LONG>(layout.toolbar+0x88,6);
    check(admission.Initialize(ac),"shared admission controller binds actual pending buffers");
    c.userObservationBefore=ad::Controller::Before;c.userObservationAfter=ad::Controller::After;c.userObservationContext=&admission;
    uintptr_t labels[]={uintptr_t(&GuestSessionUserReturn),uintptr_t(&GuestSessionMenuReturn),uintptr_t(&GuestSessionGameReturn),uintptr_t(&GuestSessionUpdateReturn)};memcpy(c.fixtureDispatchCaller,labels,sizeof labels);
    void* originals[]={reinterpret_cast<void*>(&GuestSessionUserOriginal),reinterpret_cast<void*>(&GuestSessionMenuOriginal),reinterpret_cast<void*>(&GuestSessionGameOriginal),reinterpret_cast<void*>(&GuestSessionUpdateOriginal),reinterpret_cast<void*>(&GuestSessionWorkerOriginal),reinterpret_cast<void*>(&GuestSessionReadOriginal)};
    void* bridges[]={reinterpret_cast<void*>(&CheckpointLoadDispatchBridge0),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge1),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge2),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge3),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge0),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge1)};
    GuestSessionSlots=reinterpret_cast<void**>(alloc(0x1000));for(unsigned i=0;i<6;++i){GuestSessionSlots[i]=originals[i];c.hooks[i]={GuestSessionSlots+i,originals[i],bridges[i]};}
    check(GuestSessionSlots[0]==reinterpret_cast<void*>(&GuestSessionUserOriginal),"fixture never preinstalls wrapper");
    c.dispatchForwardTargets[0]=reinterpret_cast<void*>(&CheckpointAuthorizedForwardAdmissionOriginal);
    if(scenario==L"default-forward"){
        c.dispatchForwardTargets[0]=nullptr;c.userObservationBefore=nullptr;c.userObservationAfter=nullptr;c.userObservationContext=nullptr;c.userAfter=defaultUserAfter;
    }
    if(scenario==L"bad-native-original")c.hooks[0].original=reinterpret_cast<void*>(&GuestSessionGameOriginal);
    if(scenario==L"forward-hook-cycle")c.dispatchForwardTargets[0]=bridges[0];
    DWORD protection=0;check(VirtualProtect(GuestSessionSlots,4096,PAGE_READONLY,&protection)!=0,"fixture slot page readonly");
    if(scenario==L"bad-native-original"||scenario==L"forward-hook-cycle"){
        check(!session.Initialize(c),"invalid native expectation or recursive target rejected before arm");
        for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==originals[i],"rejected initialization leaves native slots untouched");
        ns::Report rejected{};session.Snapshot(rejected);check(!rejected.armed&&!rejected.casPublished&&!userBodies&&!queueBodies&&!rejected.dispatchStats[0].configured,"no forwarding publication or native call on invalid config");
        return finishReport(rejected,true);
    }
    check(session.Initialize(c),"Session initializes before menu exists");
    for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==originals[i],"Initialize does not preinstall a wrapper");
    if(scenario==L"pre-admission-original-forward"){
        const auto configured=reinterpret_cast<ad::Original>(bridges[0]);
        check(configured(layout.config.states[4],1,2,3)==0xFEDCBA9876543210ull,"configured not-yet-accepting dispatcher forwards native once");
        ++preAdmissionCalls;ad::Report early{};admission.Snapshot(early);ns::Report earlySession{};session.Snapshot(earlySession);
        check(userBodies==1&&!early.blocked&&early.error==ad::Error::None&&!early.active&&!early.scope_started&&!early.callback_bindings&&!early.provider_begin&&!early.prefetch.entered&&!queueBodies&&!earlySession.userControllerCalls,"no BEFORE means no provider or authorization and no poisoned attempt");
        check(admissionTrace.size()==2&&admissionTrace[0]==100&&admissionTrace[1]==101,"pre-admission native body alone executes");admissionTrace.clear();
    }
    check(session.ArmHooks(),"all six hook slots armed");for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==bridges[i],"correct published slot");
    if(scenario==L"stop-before-user")session.Stop();
    if(scenario==L"controller-stop-before")admission.Stop();
    authorizeForeign=scenario==L"authorize-foreign-after";
    return true;
