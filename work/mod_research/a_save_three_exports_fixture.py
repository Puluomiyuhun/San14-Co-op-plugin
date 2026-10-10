"""Owned three-cycle native-turn/exports fixture. No production installation."""
from a_native_turn_fixture import transform as previous
from a_save_three_cycle_sources import replace


def transform(fixture):
    s=previous(fixture)
    s=replace(s,'static unsigned turnSteps=0;','static unsigned turnSteps=0;static bool turnEverStarted=false;')
    s=replace(s,'if(!turnSteps&&!a_native_turn::Running())','if(!turnEverStarted&&!a_native_turn::Running())')
    s='#include "a_save_repeat_exports.h"\n'+s
    at='static std::function<void()> ownedParentWork;'
    helper=r'''
extern "C" void ASaveThreeFixtureBind(a_save_local_runtime::Runtime*,uintptr_t)noexcept;
static bool exportedNext(const a_save_local_runtime::Next&n){
 a_save_repeat_wire::Next q{};q.header={a_save_runtime_wire::Magic,1,sizeof(q),9,0};memset(q.nonce,0x37,32);
 q.request.previousGeneration=n.previousGeneration;memcpy(q.request.previousSha256,n.previousSha256,32);
 q.request.generation=n.generation;q.request.period=n.period;q.request.epoch=n.epoch;memcpy(q.request.inputDigest,n.inputDigest,32);
 q.request.year=n.year;q.request.month=n.month;q.request.day=n.day;
 return ASaveRuntimeRequestNext(&q)==0;
}
static void exportedSnapshot(unsigned generation){
 a_save_runtime_wire::Snapshot q{};q.header={a_save_runtime_wire::Magic,1,sizeof(q),5,0};memset(q.nonce,0x37,32);
 need(!ASaveRuntimeSnapshot(&q),"actual exported Snapshot success");
 need(q.header.magic==0x33585241&&q.mailboxCount==generation&&q.saveGeneration==generation&&q.saveStatus==5&&!q.error&&!q.stopped,"actual exported three-slot identity and save status");
 for(unsigned i=0;i<3;++i)need(q.mailboxStates[i]==(i<generation?5u:0u),"actual exported mailbox lanes");
 need(!q.productionPermit&&!q.allWritersProven&&!q.restoreReady,"export does not fabricate gameplay or cleanup");
 a_save_repeat_wire::Snapshot r{};r.header={a_save_runtime_wire::Magic,1,sizeof(r),10,0};memset(r.nonce,0x37,32);
 need(!ASaveRuntimeRepeatSnapshot(&r)&&r.activeGeneration==generation&&r.retiredCount==generation-1&&!r.requested&&!r.bLoadedProven&&!r.simulationEnabled,"actual exported repeat generation and retirement");
 FILE*f=nullptr;char name[64]{};sprintf_s(name,"snapshot-%u.bin",generation);need(!fopen_s(&f,name,"wb")&&f&&fwrite(&q,1,sizeof q,f)==sizeof q&&!fclose(f),"write owned snapshot evidence");
 sprintf_s(name,"repeat-%u.bin",generation);need(!fopen_s(&f,name,"wb")&&f&&fwrite(&r,1,sizeof r,f)==sizeof r&&!fclose(f),"write owned repeat evidence");
}
'''
    s=replace(s,at,helper+at)
    s=replace(s,'need(runtime->Prepare(conf,runtimePlans),"actual Runtime Prepare");',
        'need(runtime->Prepare(conf,runtimePlans),"actual Runtime Prepare");ASaveThreeFixtureBind(runtime,b);')
    s=replace(s,'gen<=2','gen<=3')
    s=replace(s,'payload[0]==(gen==1?11:21)','payload[0]==(gen==1?11:gen==2?21:1)')
    s=replace(s,'r.save.month=8;r.save.day=static_cast<unsigned char>(gen==1?11:21);',
        'r.save.month=static_cast<unsigned char>(gen<3?8:9);r.save.day=static_cast<unsigned char>(gen==1?11:gen==2?21:1);')
    s=replace(s,'drop=CreateEventW(&sa,TRUE,FALSE,nullptr)','drop=CreateEventW(&sa,FALSE,FALSE,nullptr)')
    s=replace(s,'if(gen==1){need(WaitForSingleObject(drop,5000)','if(gen<3){need(WaitForSingleObject(drop,5000)')
    start=s.index('  if(!state.requested&&m.count==1');end=s.index('  ownedParentWork=[&]{',start)
    s=s[:start]+r'''
  if(!state.requested&&state.activeGeneration<3&&m.count==state.activeGeneration&&m.records[m.count-1].state==mb::State::Delivered){
   const auto generation=unsigned(state.activeGeneration);exportedSnapshot(generation);wchar_t filename[64]{};swprintf_s(filename,L"\\mp%08x.s14",generation);
   auto path=std::wstring(argv[2])+filename;FILE*saved=nullptr;need(_wfopen_s(&saved,path.c_str(),L"rb")==0&&saved,"read delivered Save file");unsigned char bytes[32]{};need(fread(bytes,1,32,saved)==32&&fgetc(saved)==EOF&&fclose(saved)==0,"exact owned payload");
   a_save_local_runtime::Next next{};next.previousGeneration=generation;need(native_storage_read::Sha256(bytes,32,next.previousSha256),"prior native hash");next.generation=generation+1;next.period=generation+1;next.epoch=data.binding.epoch+generation;
   memcpy(next.inputDigest,data.binding.room_input_digest.data(),32);next.inputDigest[0]+=static_cast<unsigned char>(generation);
   next.year=203;next.month=static_cast<unsigned char>(generation==1?8:9);next.day=static_cast<unsigned char>(generation==1?21:1);
   auto bad=next;bad.previousGeneration=0;need(!exportedNext(bad),"bad predecessor rejected by exported API");
   need(exportedNext(next)&&!exportedNext(next),"exported next accepted only once");turnSteps=0;turnEverStarted=true;
  }
  static std::uint64_t signaledGeneration=1;
  if(state.state==a_save_local_runtime::RepeatState::ReadySecond&&state.activeGeneration>signaledGeneration){signaledGeneration=state.activeGeneration;SetEvent(drop);}
'''+s[end:]
    s=replace(s,'repeat.activeGeneration==1&&!repeat.nativeDateMatched','repeat.activeGeneration<3&&!repeat.nativeDateMatched',2)
    s=replace(s,'put<unsigned char>(world+0x37,21);','put<unsigned char>(world+0x36,repeat.request.month);put<unsigned char>(world+0x37,repeat.request.day);')
    s=replace(s,'newStrategy=b+0x452000,newUser=b+0x450000',
        'newStrategy=b+0x442000+repeat.activeGeneration*0x10000,newUser=b+0x440000+repeat.activeGeneration*0x10000')
    for field in ('observations','submits','copies','releases'):s=s.replace(f'h.{field}==2',f'h.{field}==3')
    for expr in ('d.submits==2','d.copies==2','u.save.completed_requests==2','nativeBinds==2','queuedWindows==2'):
        s=s.replace(expr,expr[:-1]+'3')
    for expr in ('coveredCalls==10','cr.selected==10','cr.claimed==10','cr.returned==10','cr.finally==10'):
        s=s.replace(expr,expr[:-2]+'15')
    s=replace(s,'repeated.retiredCount==1&&repeated.activeGeneration==2','repeated.retiredCount==2&&repeated.activeGeneration==3')
    s=replace(s,'need(m.count==2&&m.records[0].state==mb::State::Delivered&&m.records[1].state==mb::State::Delivered',
        'need(m.count==3&&m.records[0].state==mb::State::Delivered&&m.records[1].state==mb::State::Delivered&&m.records[2].state==mb::State::Delivered')
    checks=r'''
 if(repeatCase==L"normal"){
  exportedSnapshot(3);a_save_local_runtime::Next n{};n.previousGeneration=3;n.generation=4;n.period=4;n.epoch=data.binding.epoch+3;n.previousSha256[0]=1;n.inputDigest[0]=9;n.year=203;n.month=9;n.day=11;
  need(!exportedNext(n),"fourth native export request refused");exportedSnapshot(3);
 }
'''
    s=replace(s,' runtime->Stop();',checks+' runtime->Stop();')
    return s
