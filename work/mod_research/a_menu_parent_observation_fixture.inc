  // These are actual Runtime Parent callbacks; only environment/native bodies
  // are the retained owned fixture. No observer method replaces the callback.
  {
   namespace mo=a_menu_parent_observation;
   mo::Record quiet{};mo::Snapshot(quiet);
   need(quiet.state==unsigned(mo::State::QuietObserved)&&quiet.thread==GetCurrentThreadId()&&quiet.parentCall&&quiet.current==0&&quiet.stackCount==5,"real Parent BEFORE finite quiet record");
   need(!quiet.uiPermission&&!quiet.rewardPermission&&!quiet.fullInputHold,"observer never issues permission");
   mo::Record copy{};
   need(mo::Read(quiet.binding,0,quiet.tick,100,copy),"fresh exact observation readable");
   need(!mo::Read(quiet.binding,std::uint64_t(quiet.sequence),quiet.tick,100,copy),"same sequence is stale");
   need(!mo::Read(quiet.binding,0,quiet.tick+101,100,copy),"expired observation refused");
   auto foreign=quiet.binding;++foreign.epoch;need(!mo::Read(foreign,0,quiet.tick,100,copy),"wrong epoch refused");
   foreign=quiet.binding;++foreign.birth;need(!mo::Read(foreign,0,quiet.tick,100,copy),"wrong process incarnation refused");
   if(which==L"observe-menu"||which==L"observe-selection"||which==L"observe-sample"||which==L"observe-six"){
    // The old fixture's outside-parent helper expects Pointer precedence only
    // for QUIET input. Menu/selection legitimately return their earlier reason.
    // Disable that auxiliary assertion, never any production check.
    modeFault=true;
    const auto toolbar=get<uintptr_t>(user+0x478);
    if(which==L"observe-menu")put<int>(toolbar+0x88,9);
    if(which==L"observe-selection")put<uintptr_t>(user+0x4a8,user);
    if(which==L"observe-sample")put<std::uint64_t>(b+0x19E7310+0x10,7);
    if(which==L"observe-six"){put<std::uint64_t>(b+0x19E7310+0x10,6);put<uintptr_t>(get<uintptr_t>(b+0x19E7310+0x20)+40,user);}
    const bool pendingOnly=which==L"observe-menu"||which==L"observe-selection";
    ownedParentWork=[&]{mo::Snapshot(copy);if(pendingOnly){scopedGame();scopedUser();}};
    parentDispatch();
    const auto expected=which==L"observe-sample"?mo::State::Unknown:which==L"observe-six"?mo::State::Blocked:mo::State::BusyObserved;
    need(copy.state==unsigned(expected)&&copy.sequence>quiet.sequence&&copy.parentCall!=quiet.parentCall&&copy.thread==GetCurrentThreadId(),"actual Parent publishes busy or unknown before original work");
    if(which==L"observe-menu")need(copy.decision==unsigned(checkpoint_native_input_pending::Decision::PlayerMenuPending)&&copy.menuCommand==9,"actual inspector toolbar decision");
    if(which==L"observe-selection")need(copy.decision==unsigned(checkpoint_native_input_pending::Decision::SelectionPending)&&copy.selection[0]==user,"actual inspector selection decision");
    if(which==L"observe-sample")need(copy.reason==unsigned(mo::Reason::Sample)&&!mo::Read(copy.binding,0,copy.tick,100,quiet),"unknown sampler shape is not fresh readiness");
    if(which==L"observe-six")need(copy.stackCount==6&&copy.decision==unsigned(checkpoint_native_input_pending::Decision::UnownedLoadMenu)&&!mo::Read(copy.binding,0,copy.tick,100,quiet),"unowned sixth-state model is neither quiet nor permitted");
    if(pendingOnly) {need(copy.stackCount==5&&!copy.queueCount,"busy fixture is five-state pending input, not an opened submenu");a_save_user_owner::Report u{};a_save_upstream_gate::Report g{};runtime.FixtureOwner()->Snapshot(u);runtime.FixtureGate()->Snapshot(g);need(g.error==a_save_upstream_gate::Error::Input&&u.stopped,"old native guards still refuse menus; diagnostic does not allow UI");}
    need(!data.bodies&&!copy.uiPermission&&!copy.rewardPermission,"no reward executes and no new permit");
    FILE*f=nullptr;need(!fopen_s(&f,"observation.bin","wb")&&f,"observation binary file");need(fwrite(&copy,1,sizeof copy,f)==sizeof copy&&!fclose(f),"whole observation recorded");
    printf("{\"passed\":true,\"case\":\"%ls\",\"state\":%u,\"reason\":%u,\"decision\":%u,\"sequence\":%llu,\"record_size\":%zu,\"sequence_offset\":%zu,\"actual_parent\":true,\"actual_inspector\":true,\"reward_bodies\":%u,\"ui_permission\":false}\n",which.c_str(),copy.state,copy.reason,copy.decision,std::uint64_t(copy.sequence),sizeof copy,offsetof(mo::Record,sequence),data.bodies);
    runtime.Stop();return 0;
   }
  }
