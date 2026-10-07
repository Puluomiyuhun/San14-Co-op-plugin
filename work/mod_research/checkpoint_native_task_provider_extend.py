from pathlib import Path
p=Path('work/mod_research/checkpoint_native_task_provider_fixture.cpp');s=p.read_text()
s=s.replace('static unsigned generationIndex=0;', 'static unsigned generationIndex=0;\nstatic std::wstring providerCase;\nstatic uintptr_t sharedImage=0,reusedLoad=0,reusedTitle=0;')
s=s.replace('check(layout.initialize(bd::Stage::MenuAfter),"synthetic planning layout");base=layout.config.base;', '''check(layout.initialize(bd::Stage::MenuAfter),"synthetic planning layout");
    if(providerCase==L"reuse-full-addresses"&&generationIndex){memcpy(reinterpret_cast<void*>(sharedImage),reinterpret_cast<void*>(layout.config.base),0x2200000);layout.config.base=sharedImage;layout.manager=sharedImage+0x19E7310;}
    base=layout.config.base;if(!generationIndex)sharedImage=base;''')
s=s.replace('title=alloc(0x2000);load=alloc(0x1000);stackArray=', '''title=alloc(0x2000);load=alloc(0x1000);
    if(providerCase==L"reuse-full-addresses"&&generationIndex){DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(reusedTitle),0x2000,PAGE_READWRITE,&old)&&VirtualProtect(reinterpret_cast<void*>(reusedLoad),0x1000,PAGE_READWRITE,&old),"reuse historical address pages");title=reusedTitle;load=reusedLoad;memset(reinterpret_cast<void*>(title),0,0x2000);memset(reinterpret_cast<void*>(load),0,0x1000);}
    if(!generationIndex){reusedTitle=title;reusedLoad=load;}
    stackArray=''')
s=s.replace('    callbackPort();', '''    if(providerCase==L"missing-load-join"&&!generationIndex){
        uintptr_t sp[]={base+0x497134};auto denied=capture(base,0x4CC690);denied.rcx=title;denied.rdx=load;denied.rsp=uintptr_t(sp);
        check(!provider.Observe(denied)&&!provider.CloseCompletedWindow(2),"Load join omission prevents Title source and generation completion");
        session.Snapshot(r);check(r.lifecycle.receiptReady&&!r.identity.casAttempts,"actual Load receipt alone does not advance Title identity");return finishReport(r,true);
    }
    callbackPort();''')
s=s.replace('    check(provider.CloseCompletedWindow(generationIndex+2),"all THREE joins and real Session/planning receipts close creation window");', '''    if(providerCase==L"late-old-root"&&!generationIndex){lateOriginalSelf=planningContext->newUser;lateTask=prepareState(lateOriginalSelf);check(!provider.CloseCompletedWindow(2),"unentered old task prevents claiming fully closed generation");}
    const bool incomplete=(!generationIndex&&(providerCase==L"late-old-root"||providerCase==L"missing-title520-join"||providerCase==L"missing-title590-join"));
    check(provider.CloseCompletedWindow(generationIndex+2)==!incomplete,"all THREE joins and drained tasks required with actual Session/planning receipts");''')
s=s.replace('check(taskReport.closed&&taskReport.threeJoins&&!taskReport.productionPublication&&!taskReport.schedulerFence,', 'check(bool(taskReport.closed)==!incomplete&&bool(taskReport.threeJoins)==(!(!generationIndex&&(omitJoin[1]||omitJoin[2])))&&!taskReport.productionPublication&&!taskReport.schedulerFence,')
s=s.replace('    for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==bridges[i],"same persistent physical slot");', '''    for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==bridges[i],"same persistent physical slot");
    if(generationIndex&&providerCase==L"late-old-root"){
        ns::Report unchanged{},afterLate{};session.Snapshot(unchanged);enterState(*lateTask);
        GuestSessionUserInvoke(lateOriginalSelf,0x1001,0x1002,0x1003);leaveState(*lateTask,false);session.Snapshot(afterLate);
        check(!memcmp(&unchanged,&afterLate,sizeof unchanged)&&lateOriginalCalls==1,"old task entering AFTER new publication never reaches new Session");
        check(provider.CloseCompletedWindow(2),"old generation closes only after its delayed task actually returns");
        GuestSessionUserInvoke(lateOriginalSelf,0x1001,0x1002,0x1003);session.Snapshot(afterLate);
        check(!memcmp(&unchanged,&afterLate,sizeof unchanged)&&lateOriginalCalls==2,"unknown root transparently forwards without selecting latest Session");
    }''')
s=s.replace('    const std::wstring first=argv[1],folder=argv[3];', '    const std::wstring first=argv[1],folder=argv[3];providerCase=first;')
s=s.replace('    ns::Session* retired=nullptr;', '    tp::Report retiredProvider{};\n    ns::Session* retired=nullptr;')
s=s.replace('        std::wstring caseName=first==', '''        omitJoin[0]=!i&&first==L"missing-load-join";omitJoin[1]=!i&&first==L"missing-title520-join";omitJoin[2]=!i&&first==L"missing-title590-join";
        std::wstring caseName=first==''')
s=s.replace('        std::wstring req=folder+', '''        if(first==L"reuse-full-addresses"||first==L"late-old-root"||first.rfind(L"missing-",0)==0||first==L"idle-window")caseName=L"success";
        std::wstring req=folder+''')
s=s.replace('if(!i){retired=currentSession;', 'if(!i){provider.Snapshot(2,retiredProvider);retired=currentSession;')
s=s.replace('else {retired->Snapshot(after);check(!memcmp(&before,&after,sizeof before),', 'else {tp::Report oldNow{};provider.Snapshot(2,oldNow);if(first!=L"late-old-root")check(!memcmp(&retiredProvider,&oldNow,sizeof oldNow),"new-generation source events never mutate old provider counters");retired->Snapshot(after);check(first==L"late-old-root"||!memcmp(&before,&after,sizeof before),')
s=s.replace('if(scenario==L"success"||scenario==L"alternate-factions"||scenario==L"planning-reuse-load"){', 'if((scenario==L"success"||scenario==L"alternate-factions"||scenario==L"planning-reuse-load")&&!(providerCase==L"missing-load-join"&&!generationIndex)){')
s=s.replace('    verifyNoAdditionalAdmission();', '''    verifyNoAdditionalAdmission();
    if(providerCase==L"idle-window"){tp::Report start{},end{};provider.Snapshot(generationIndex+2,start);for(unsigned i=0;i<1000;++i){auto c0=capture(base,0x50B4B3);check(provider.Observe(c0),"closed idle window ignores even before dereferencing state source");}provider.Snapshot(generationIndex+2,end);check(end.creations==start.creations&&end.retainedTasks==start.retainedTasks&&end.ignored==start.ignored+1000,"idle frames consume no immutable task tickets after completed window");}''')
p.write_text(s)
p=Path('work/mod_research/checkpoint_native_task_provider_fixture_ports.inc');s=p.read_text().replace('static DWORD WINAPI parentPort', 'static StatePort* lateTask=nullptr;\nstatic DWORD WINAPI parentPort');p.write_text(s)
p=Path('work/mod_research/checkpoint_native_task_provider_test.py');s=p.read_text().replace("CASES=['success','alternate-factions','planning-reuse-load']", "CASES=['success','alternate-factions','planning-reuse-load','reuse-full-addresses','late-old-root','missing-load-join','missing-title520-join','missing-title590-join','idle-window']");p.write_text(s)
