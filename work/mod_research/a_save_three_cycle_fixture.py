"""Three generations in the predecessor's actual retained native host fixture."""
from a_save_repeat_fixture import transform as previous
from a_save_three_cycle_sources import replace

def transform(fixture):
    s=previous(fixture)
    s=replace(s,'gen<=2','gen<=3')
    s=replace(s,'payload[0]==(gen==1?11:21)','payload[0]==(gen==1?11:gen==2?21:1)')
    s=replace(s,'r.save.month=8;r.save.day=static_cast<unsigned char>(gen==1?11:21);',
              'r.save.month=static_cast<unsigned char>(gen<3?8:9);r.save.day=static_cast<unsigned char>(gen==1?11:gen==2?21:1);')
    s=replace(s,'drop=CreateEventW(&sa,TRUE,FALSE,nullptr)','drop=CreateEventW(&sa,FALSE,FALSE,nullptr)')
    s=replace(s,'if(gen==1){need(WaitForSingleObject(drop,5000)', 'if(gen<3){need(WaitForSingleObject(drop,5000)')
    s=replace(s,'static std::wstring repeatCase;', 'static std::wstring repeatCase;static unsigned faultAt=1;')
    s=replace(s,'repeatCase=caseName;', 'repeatCase=caseName;if(caseName==L"stop-third"){repeatCase=L"stop-gap";faultAt=2;}if(caseName==L"missing-third"){repeatCase=L"missing-after";faultAt=2;}')
    s=replace(s,'if(r.state!=a_save_local_runtime::RepeatState::Observing)',
              'if(r.activeGeneration!=faultAt||r.state!=a_save_local_runtime::RepeatState::Observing)',2)
    s=replace(s,'if(clientMode!=L"normal"){CloseHandle(pipe);',
              'if(clientMode!=L"normal"&&gen==((clientMode==L"stop-third"||clientMode==L"missing-third")?2u:1u)){CloseHandle(pipe);')
    start=s.index('  if(!state.requested&&m.count==1');end=s.index('  ownedParentWork=[&]{',start)
    s=s[:start]+r'''
  if(!state.requested&&state.activeGeneration<3&&m.count==state.activeGeneration&&m.records[m.count-1].state==mb::State::Delivered){
   const auto generation=unsigned(state.activeGeneration);wchar_t filename[64]{};swprintf_s(filename,L"\\mp%08x.s14",generation);
   auto path=std::wstring(argv[2])+filename;FILE*saved=nullptr;need(_wfopen_s(&saved,path.c_str(),L"rb")==0&&saved,"read delivered native Save file");unsigned char bytes[32]{};need(fread(bytes,1,32,saved)==32&&fgetc(saved)==EOF&&fclose(saved)==0,"exact diagnostic payload");
   a_save_local_runtime::Next next{};next.previousGeneration=generation;need(native_storage_read::Sha256(bytes,32,next.previousSha256),"actual previous artifact hash");
   next.generation=generation+1;next.period=generation+1;next.epoch=data.binding.epoch+generation;
   memcpy(next.inputDigest,data.binding.room_input_digest.data(),32);next.inputDigest[0]+=static_cast<unsigned char>(generation);
   next.year=203;next.month=static_cast<unsigned char>(generation==1?8:9);next.day=static_cast<unsigned char>(generation==1?21:1);
   auto bad=next;bad.previousGeneration=0;need(!runtime->RequestNext(bad),"zero predecessor rejected before retirement");
   bad=next;--bad.generation;need(!runtime->RequestNext(bad),"stale generation rejected");
   bad=next;bad.day=11;need(!runtime->RequestNext(bad),"skipped date rejected");
   bad=next;memcpy(bad.inputDigest,data.binding.room_input_digest.data(),32);need(!runtime->RequestNext(bad),"historical initial input digest rejected");
   need(runtime->RequestNext(next)&&!runtime->RequestNext(next),"new copied request accepted once");
  }
  if(state.state==a_save_local_runtime::RepeatState::RetiredWaitingDate){
   need(state.previousArtifactMatched&&!state.nativeDateMatched&&!state.bLoadedProven&&!state.simulationEnabled,"retired is not date advance or B loaded evidence");
   // Owned native-date business substitute. Runtime itself never advances dates.
   put<unsigned char>(world+0x36,state.request.month);put<unsigned char>(world+0x37,state.request.day);
  }
  static std::uint64_t signaledGeneration=1;
  if(state.state==a_save_local_runtime::RepeatState::ReadySecond&&state.activeGeneration>signaledGeneration){signaledGeneration=state.activeGeneration;SetEvent(drop);}
'''+s[end:]
    for field in ('observations','submits','copies','releases'):s=s.replace(f'h.{field}==2',f'h.{field}==3')
    for expr in ('d.submits==2','d.copies==2','u.save.completed_requests==2','nativeBinds==2','queuedWindows==2'):
        s=s.replace(expr,expr[:-1]+'3')
    for expr in ('coveredCalls==10','cr.selected==10','cr.claimed==10','cr.returned==10','cr.finally==10'):
        s=s.replace(expr,expr[:-2]+'15')
    s=replace(s,'repeated.retiredCount==1&&repeated.activeGeneration==2',
              'repeated.retiredCount==2&&repeated.activeGeneration==3')
    s=replace(s,'need(m.count==2&&m.records[0].state==mb::State::Delivered&&m.records[1].state==mb::State::Delivered',
              'need(m.count==3&&m.records[0].state==mb::State::Delivered&&m.records[1].state==mb::State::Delivered&&m.records[2].state==mb::State::Delivered')
    s=replace(s,'repeated.activeGeneration==1&&!repeated.retiredCount',
              'repeated.activeGeneration==faultAt&&repeated.retiredCount==faultAt-1')
    s=replace(s,'m.count==1&&m.records[0].state==mb::State::Delivered&&d.submits==1&&d.copies==1&&h.submits==1&&h.copies==1&&u.save.completed_requests==1',
              'm.count==faultAt&&m.records[faultAt-1].state==mb::State::Delivered&&d.submits==faultAt&&d.copies==faultAt&&h.submits==faultAt&&h.copies==faultAt&&u.save.completed_requests==faultAt')
    s=replace(s,'  need(h.observations==3',r'''  printf("THREE_DIAG host=%u/%u/%u/%u ipc=%llu/%llu saves=%u binds=%u covered=%llu/%llu/%llu/%llu reject=%llu\n",h.observations,h.submits,h.copies,h.releases,d.submits,d.copies,u.save.completed_requests,nativeBinds,cr.selected,cr.claimed,cr.returned,cr.finally,cr.rejected);
  need(h.observations==3''')
    at=' runtime->Stop();'
    checks=r'''
 if(repeatCase==L"normal"){
  planning_period_owner::Receipt second{};need(planning_period_owner::Historical(*session,2,second)&&second.serial==2&&second.date.month==8&&second.date.day==21,"second immutable retirement retained");
  a_save_local_runtime::Next fourth{};fourth.previousGeneration=3;fourth.generation=4;fourth.period=4;fourth.epoch=data.binding.epoch+3;fourth.previousSha256[0]=1;fourth.inputDigest[0]=9;fourth.year=203;fourth.month=9;fourth.day=11;
  need(!runtime->RequestNext(fourth),"bounded fourth cycle refused without reusing one-shot controllers");
  a_save_local_runtime::RepeatReport unchanged{};runtime->RepeatSnapshot(unchanged);need(unchanged.activeGeneration==3&&unchanged.retiredCount==2&&!unchanged.requested&&!unchanged.stopped,"fourth refusal preserves completed third generation");
 }
'''
    s=replace(s,at,checks+at)
    return s
