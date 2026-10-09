"""Compose actual Runtime turn controls with explicitly owned native business."""
from a_save_repeat_fixture import transform as previous


def transform(fixture):
    fixture=previous(fixture).replace('a_save_repeat_runtime.h','a_native_turn_runtime.h')
    fixture=fixture.replace('static std::function<void()> ownedParentWork;',
                            'static unsigned turnSteps=0;static uintptr_t oldTurnUser=0;\nstatic std::function<void()> ownedParentWork;')
    fixture=fixture.replace('rejectCurrent(0,"parent original body is not a Host boundary");',
                            'if(!turnSteps&&!a_native_turn::Running())rejectCurrent(0,"parent original body is not a Host boundary");')
    fixture=fixture.replace('   put<unsigned char>(world+0x37,21);','   // Date changes only in the owned native business body below.')
    at='   if(repeat.stopped)return;'
    body=r'''
   if(a_native_turn::Running()&&!repeat.stopped){
    need(repeat.drainPending&&!repeat.lease&&!repeat.frame,"native running not restore-ready and no cross-turn producer lease");
    bool acquired=false;std::thread writer([&]{acquired=TryAcquireSRWLockShared(&producer)!=FALSE;if(acquired)ReleaseSRWLockShared(&producer);});writer.join();need(acquired,"native business writer can run");
    const auto manager=b+0x19E7310,stack=get<uintptr_t>(manager+0x20);
    if(turnSteps==0){
     oldTurnUser=user;
     auto denied=request(ip::Op::Submit,999,2);need(!session->Submit(fs::Request{}),"retired ordinary Save cannot reopen during turn");(void)denied;
     ss::Report beforeUser{};session->Snapshot(beforeUser);ag::Report beforeGame{};input->Snapshot(beforeGame);
     put<unsigned>(user+0x470,5);(void)scopedUser();(void)scopedGame();
     ss::Report afterUser{};session->Snapshot(afterUser);ag::Report afterGame{};input->Snapshot(afterGame);
     need(afterUser.bridges[0].native_started==beforeUser.bridges[0].native_started+1&&!afterUser.stopped&&afterUser.error==ss::Error::None,"original phase5 User forwarded while retired");
     need(afterGame.uiForwarded>beforeGame.uiForwarded&&afterGame.panelForwarded>beforeGame.panelForwarded&&afterGame.error==ag::Error::None,"Game UI/panel original calls forwarded");
     put<std::uint64_t>(manager+0x10,3); // Strategy and User genuinely absent in owned scheduler model.
    }else if(turnSteps==1){
     need(get<std::uint64_t>(manager+0x10)==3,"running parent tolerates native transition stack");
     (void)scopedGame();
     if(repeatCase==L"stop-running"){
      std::thread remote([&]{runtime->Stop();});remote.join();runtime->RepeatSnapshot(repeat);
      need(repeat.stopped&&repeat.drainPending&&!repeat.lease,"Stop while running keeps unresolved turn evidence");SetEvent(drop);++turnSteps;return;
     }
    }else if(turnSteps==2){
     need(repeat.activeGeneration==1&&!repeat.nativeDateMatched,"next date alone cannot rebind absent planning stack");put<unsigned char>(world+0x37,21);
    }else if(turnSteps==3){
     const auto oldStrategy=get<uintptr_t>(stack+24),newStrategy=b+0x452000,newUser=b+0x450000;
     memcpy(reinterpret_cast<void*>(newStrategy),reinterpret_cast<void*>(oldStrategy),0x1000);
     memcpy(reinterpret_cast<void*>(newUser),reinterpret_cast<void*>(user),0x1000);
     memset(reinterpret_cast<void*>(oldStrategy),0,0x1000);memset(reinterpret_cast<void*>(user),0,0x1000);
     user=newUser;put<unsigned>(user+0x470,2);put<uintptr_t>(stack+24,newStrategy);put<uintptr_t>(stack+32,user);put<std::uint64_t>(manager+0x10,5);
     put<unsigned char>(user+0x660,1); // Report still open on the newly constructed User.
    }else if(turnSteps==4){
     need(repeat.activeGeneration==1&&!repeat.nativeDateMatched,"new User plus next date still waits for reports");put<unsigned char>(user+0x660,0);
    }
    ++turnSteps;return;
   }
'''
    assert fixture.count(at)==1
    fixture=fixture.replace(at,body+at)
    fixture=fixture.replace('if(repeatFault){need(WaitForSingleObject(serverDone,3000)',
        'if(repeatCase==L"stop-running"&&turnSteps==2){need(WaitForSingleObject(serverDone,3000)==WAIT_OBJECT_0,"running Stop client exits");break;}if(repeatFault){need(WaitForSingleObject(serverDone,3000)')
    start=fixture.index(' }else{\n  a_save_local_runtime::RepeatReport repeated{};runtime->RepeatSnapshot(repeated);')
    end=fixture.index(' runtime->Stop();',start)
    fixture=fixture[:start]+r'''
 }else{
  a_save_local_runtime::RepeatReport repeated{};runtime->RepeatSnapshot(repeated);
  need(repeatCase==L"stop-running"&&turnSteps==2&&repeated.stopped&&repeated.drainPending&&!repeated.lease&&!repeated.frame&&a_native_turn::Running(),"unresolved running Stop never grants restoration");
  need(m.count==1&&m.records[0].state==mb::State::Delivered&&d.submits==1&&d.copies==1&&h.copies==1&&!h.lease&&!h.frame,"stopped turn retains delivered artifact and creates no second request");
 }
 if(repeatCase==L"normal")need(turnSteps>=5&&user!=oldTurnUser&&get<uintptr_t>(oldTurnUser)==0&&!a_native_turn::Running(),"second actual Save bound new User; old object invalidated");
'''+fixture[end:]
    fixture=fixture.replace('!repeatFault&&parentReport.error==a_save_parent_adapter::Error::None','!repeatFault&&(parentReport.error==a_save_parent_adapter::Error::None||(repeatCase==L"stop-running"&&parentReport.error==a_save_parent_adapter::Error::Stopped))')
    return fixture
