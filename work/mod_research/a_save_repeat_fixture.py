"""Bounded fixture transformation: actual repeat Runtime, diagnostic Save body."""
def transform(fixture):
    fixture='#include "a_save_repeat_runtime.h"\n'+fixture
    fixture=fixture.replace('gen<=1','gen<=2')
    fixture=fixture.replace('p.selected==1&&p.claimed==1&&p.returned==1&&p.finally==1','p.selected==queuedWindows&&p.claimed==queuedWindows&&p.returned==queuedWindows&&p.finally==queuedWindows')
    fixture=fixture.replace('need(copied,"artifact delivered");}', 'need(copied,"artifact delivered");if(gen==1)need(WaitForSingleObject(drop,5000)==WAIT_OBJECT_0,"wait for real Runtime ReadySecond");}')
    begin=fixture.index(' RewardData data;need(session->Initialize')
    end=fixture.index(' bool wrongAccepted=',begin)
    setup=r'''
 RewardData data;parentLayout();put<std::uint64_t>(b+0x19E7310+0x18,16);
 auto*runtime=new a_save_local_runtime::Runtime;a_save_local_runtime::Config conf{};
 conf.pid=GetCurrentProcessId();conf.birth=cfg.storage.attachment.birth;conf.base=b;conf.nativeRoomEpoch=7;conf.roomId[0]=1;
 conf.source.binding=cfg.input_binding;conf.source.base=b;conf.source.root=root;conf.source.world=world;conf.source.cache=get<uintptr_t>(b+0x2025318);
 for(unsigned i=0;i<5;++i)conf.source.states[i]=get<uintptr_t>(b+0x210000+i*8);
 conf.storage=cfg.storage;conf.storage.checkOwner=nullptr;conf.storage.owner=nullptr;conf.planning=data.binding;
 conf.year=203;conf.month=8;conf.day=11;conf.force=12;conf.ruler=666;wcscpy_s(conf.saveDirectory,argv[2]);wcscpy_s(conf.intentDirectory,argv[2]);
 conf.fixtureBinder=cfg.binder;conf.fixtureQueue=cfg.queue;conf.fixtureUserCaller=cfg.caller;conf.fixtureGameCaller=uintptr_t(&InputGameReturn);conf.fixtureUiCaller=uintptr_t(&InputUiReturn);
 a_save_local_runtime::Plans runtimePlans{};need(runtime->Prepare(conf,runtimePlans),"actual Runtime Prepare");session=runtime->FixtureOwner();input=runtime->FixtureGate();plan=runtimePlans.gate;
 need(runtime->ArmOwner(),"actual Runtime ArmOwner");publish();
 auto&parent=runtime->FixtureParent();auto&host=runtime->FixtureHost();auto&box=runtime->FixtureMailbox();auto&producer=runtime->FixtureProducer();auto patch=runtimePlans.parent;
 DWORD protection=0;need(VirtualProtect(reinterpret_cast<void*>(patch.site),5,PAGE_READWRITE,&protection),"owned publisher");memcpy(reinterpret_cast<void*>(patch.site),patch.after,5);DWORD ignored=0;need(VirtualProtect(reinterpret_cast<void*>(patch.site),5,protection,&ignored)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(patch.site),5)&&runtime->ArmPublishedSources(),"Runtime sources published and armed");
 rejectCurrent(0,"unclaimed current zero rejected");rejectCurrent(b+0x200000,"wrong current rejected");a_save_parent_adapter::Report beforeParent{};parent.Snapshot(beforeParent);need(!beforeParent.hostInitialized&&!beforeParent.hostThread,"installer does not initialize Controller");parentDispatch();parent.Snapshot(beforeParent);need(beforeParent.hostInitialized&&beforeParent.hostThread==GetCurrentThreadId(),"natural parent initializes actual Runtime Host");
'''
    fixture=fixture[:begin]+setup+fixture[end:]
    begin=fixture.index(' ip::Config c{};c.owner=session;')
    end=fixture.index('\n ip::Server server;',begin)
    fixture=fixture[:begin]+''' ip::Config c{};c.pipeName=name;c.clientPid=child.dwProcessId;c.idleTimeoutMs=5000;c.secret[0]=0x5A;need(runtime->ConfigureTransport(c),"actual Runtime ports and permit");'''+fixture[end:]
    fixture=fixture.replace('static bool permit(', '[[maybe_unused]] static bool permit(').replace('static void executionStop(', '[[maybe_unused]] static void executionStop(')
    fixture=fixture.replace('host.Snapshot(h);\n   if(h.state==dh::State::Observing)', 'host.Snapshot(h);a_save_local_runtime::RepeatReport repeat{};runtime->RepeatSnapshot(repeat);\n   if(h.state==dh::State::Observing||repeat.state==a_save_local_runtime::RepeatState::Observing)')
    fixture=fixture.replace('h.state==dh::State::Submitted&&!nativeBinds','h.state==dh::State::Submitted&&nativeBinds<h.serial')
    fixture=fixture.replace('saveReport().binds==1&&saveReport().status', 'saveReport().binds==1&&saveReport().status')
    at='  ownedParentWork=[&]{'
    inject=r'''
  a_save_local_runtime::RepeatReport state{};runtime->RepeatSnapshot(state);
  if(!state.requested&&m.count==1&&m.records[0].state==mb::State::Delivered){
   auto path=std::wstring(argv[2])+L"\\mp00000001.s14";FILE*saved=nullptr;need(_wfopen_s(&saved,path.c_str(),L"rb")==0&&saved,"read owned first Save file");unsigned char bytes[32]{};need(fread(bytes,1,32,saved)==32&&fgetc(saved)==EOF&&fclose(saved)==0,"exact owned diagnostic payload");
   a_save_local_runtime::Next next{};next.previousGeneration=1;need(native_storage_read::Sha256(bytes,32,next.previousSha256),"actual prior payload hash");next.generation=2;next.period=2;next.epoch=data.binding.epoch+1;memcpy(next.inputDigest,data.binding.room_input_digest.data(),32);++next.inputDigest[0];next.year=203;next.month=8;next.day=21;
   need(runtime->RequestNext(next)&&!runtime->RequestNext(next),"one copied Runtime next request; duplicate rejected");
  }
  if(state.state==a_save_local_runtime::RepeatState::RetiredWaitingDate){
   need(state.previousArtifactMatched&&!state.nativeDateMatched&&!state.bLoadedProven&&!state.simulationEnabled,"retired distinct from actual date and B loaded");
   // Explicit native-date business substitute. Runtime never writes game date.
   put<unsigned char>(world+0x37,21);
  }
  if(state.state==a_save_local_runtime::RepeatState::ReadySecond)SetEvent(drop);
'''
    assert fixture.count(at)==1;fixture=fixture.replace(at,inject+at)
    fixture=fixture.replace('coveredCalls==5&&queuedWindows==1','coveredCalls==10&&queuedWindows==2')
    fixture=fixture.replace('h.observations==1&&h.submits==1&&h.copies==1&&h.releases==1&&d.submits==1&&d.copies==1&&u.save.completed_requests==1&&nativeBinds==1&&cr.selected==5&&cr.claimed==5&&cr.returned==5&&cr.finally==5','h.observations==2&&h.submits==2&&h.copies==2&&h.releases==2&&d.submits==2&&d.copies==2&&u.save.completed_requests==2&&nativeBinds==2&&cr.selected==10&&cr.claimed==10&&cr.returned==10&&cr.finally==10')
    before=' printf('
    tail=r'''
 a_save_local_runtime::RepeatReport repeated{};runtime->RepeatSnapshot(repeated);planning_period_owner::Receipt historical{};
 need(repeated.state==a_save_local_runtime::RepeatState::ReadySecond&&repeated.retiredCount==1&&repeated.activeGeneration==2&&repeated.hostThread==GetCurrentThreadId()&&!repeated.lease&&!repeated.frame&&!repeated.drainPending&&planning_period_owner::Historical(*session,1,historical)&&historical.serial==1&&historical.date.day==11,"same real Owner history and host after second save");
 need(m.count==2&&m.records[0].state==mb::State::Delivered&&m.records[1].state==mb::State::Delivered&&u.bridges[0].native_started>5,"retained mailbox and physical bridge history");
 runtime->Stop();
'''
    position=fixture.rfind(before);assert position>=0;fixture=fixture[:position]+tail+fixture[position:]
    return faults(fixture)

def faults(fixture):
    fixture=fixture.replace('coveredCase=caseName;', 'coveredCase=L"normal";repeatCase=caseName;')
    hook=r'''
static std::wstring repeatCase;
static a_save_local_runtime::Runtime* repeatRuntime=nullptr;
static bool repeatFault=false,repeatRemoteHeld=false;
extern "C" bool ASaveRepeatFixtureSkipAfter(){
 if(!repeatRuntime||repeatCase!=L"missing-after"||repeatFault)return false;
 a_save_local_runtime::RepeatReport r{};repeatRuntime->RepeatSnapshot(r);if(r.state!=a_save_local_runtime::RepeatState::Observing)return false;
 repeatFault=true;need(r.lease&&r.frame,"actual AFTER deliberately omitted with observation active");return true;
}
extern "C" void ASaveRepeatFixtureBeforeHost(){
 if(!repeatRuntime||repeatCase!=L"stop-gap"||repeatFault)return;
 a_save_local_runtime::RepeatReport r{};repeatRuntime->RepeatSnapshot(r);if(r.state!=a_save_local_runtime::RepeatState::Observing)return;
 repeatFault=true;need(r.lease&&r.frame,"repeat observation acquired before remote stop");
 std::thread remote([]{repeatRuntime->Stop();});remote.join();repeatRuntime->RepeatSnapshot(r);
 repeatRemoteHeld=r.lease&&r.frame&&r.drainPending;need(repeatRemoteHeld,"remote Stop did not unlock original host lease");
}
'''
    fixture=fixture.replace('static std::function<void()> ownedParentWork;',hook+'\nstatic std::function<void()> ownedParentWork;')
    fixture=fixture.replace('int wmain(int argc',r'''static bool parentDispatchCaught(){__try{parentDispatch();return false;}__except(GetExceptionCode()==0xE0140010?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}}
int wmain(int argc''')
    fixture=fixture.replace('auto*runtime=new a_save_local_runtime::Runtime;', 'auto*runtime=new a_save_local_runtime::Runtime;repeatRuntime=runtime;')
    fixture=fixture.replace('if(gen==1)need(WaitForSingleObject(drop,5000)==WAIT_OBJECT_0,"wait for real Runtime ReadySecond");',r'''if(gen==1){need(WaitForSingleObject(drop,5000)==WAIT_OBJECT_0,"wait for real Runtime ReadySecond or fault drain");if(clientMode!=L"normal"){CloseHandle(pipe);SetEvent(closed);need(WaitForSingleObject(finish,5000)==WAIT_OBJECT_0,"fault client finish");return 0;}}''')
    fixture=fixture.replace('if(h.state==dh::State::Observing||repeat.state==a_save_local_runtime::RepeatState::Observing){',r'''if(repeatCase==L"missing-after"&&!repeatFault&&repeat.state==a_save_local_runtime::RepeatState::Observing){need(repeat.lease&&repeat.frame,"repeat lease before omitted AFTER");}
   if(repeat.stopped)return;
   if(h.state==dh::State::Observing||repeat.state==a_save_local_runtime::RepeatState::Observing){''')
    fixture=fixture.replace('};parentDispatch();ownedParentWork={};', r'''};const bool caught=parentDispatchCaught();ownedParentWork={};need(!caught,"native body returned; fixture omits AFTER handler only");
  a_save_local_runtime::RepeatReport afterRepeat{};runtime->RepeatSnapshot(afterRepeat);if(repeatFault){need(afterRepeat.stopped&&!afterRepeat.lease&&!afterRepeat.frame&&!afterRepeat.drainPending,"same-host AFTER or FINALLY drains repeat observation");SetEvent(drop);}''')
    start=fixture.index('need((parentReport.error==');end=fixture.index(';',start)
    fixture=fixture[:start]+r'''need(!parentReport.active&&parentReport.before==parentReport.finally&&((!repeatFault&&parentReport.error==a_save_parent_adapter::Error::None&&parentReport.before==parentReport.after)||(repeatFault&&parentReport.error!=a_save_parent_adapter::Error::None&&parentReport.before-parentReport.after==(repeatCase==L"missing-after"?1u:0u))),"actual original parent completion or deliberate missing AFTER")'''+fixture[end:]
    fixture=fixture.replace('if(WaitForSingleObject(serverDone,0)==WAIT_OBJECT_0&&!h.lease)break;', 'if(repeatFault){need(WaitForSingleObject(serverDone,3000)==WAIT_OBJECT_0,"fault server drains EOF");break;}if(WaitForSingleObject(serverDone,0)==WAIT_OBJECT_0&&!h.lease)break;')
    start=fixture.index(' if(coveredCase==L"normal"){\n  need(writerBlocked');end=fixture.index(' runtime->Stop();',start)
    normal=fixture[start:end]
    fixture=fixture[:start]+' if(repeatCase==L"normal"){\n'+normal+r'''
 }else{
  a_save_local_runtime::RepeatReport repeated{};runtime->RepeatSnapshot(repeated);
  need(repeatFault&&repeated.stopped&&repeated.state==a_save_local_runtime::RepeatState::Failed&&!repeated.lease&&!repeated.frame&&!repeated.drainPending&&repeated.activeGeneration==1&&!repeated.retiredCount,"failed repeat neither retires nor rebinds");
  need(m.count==1&&m.records[0].state==mb::State::Delivered&&d.submits==1&&d.copies==1&&h.submits==1&&h.copies==1&&u.save.completed_requests==1&&!u.save.active&&!u.active_scopes&&!h.lease,"failure retains first artifact and creates no second save");
  need((repeatCase==L"stop-gap"&&repeatRemoteHeld&&!h.frame)||(repeatCase==L"missing-after"&&h.frame),"Stop-gap closes frame; missing AFTER retains old Host unresolved frame");
  bool acquired=false;std::thread writer([&]{acquired=TryAcquireSRWLockShared(&producer)!=FALSE;if(acquired)ReleaseSRWLockShared(&producer);});writer.join();need(acquired,"repeat lease released by same host after failure");
 }
'''+fixture[end:]
    return fixture
