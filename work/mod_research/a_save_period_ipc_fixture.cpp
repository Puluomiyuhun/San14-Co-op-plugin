// Owned-process integration only. Reuses frozen diagnostic business doubles;
// no game discovery, attachment, real date engine, or production save permit.
#include "planning_period_owner.h"
#include "planning_period_base_fixture.inc"
#include "a_save_ipc.h"
#include <atomic>
#include <fcntl.h>
#include <io.h>
namespace pp=planning_period_owner;
#pragma pack(push,1)
struct Bootstrap {unsigned char secret[32],room_id[32];std::uint64_t epoch;unsigned char nonce[16];};
#pragma pack(pop)
static_assert(sizeof(Bootstrap)==88);
static std::atomic<unsigned> expectedPeriod{1};
static bool admission(void*,const fs::Request&q,const unsigned char*)noexcept {
 // Fixture scheduling only. No assertion of full input/writer exclusion.
 const auto p=expectedPeriod.load();return p&&q.generation==p&&q.period==p&&q.year==203&&q.month==8&&
  q.day==(p==1?11:21)&&q.force==12&&q.ruler==666;
}
static void event(unsigned period,const pp::Report&r){
 printf("{\"event\":\"PERIOD_BOUNDARY\",\"period\":%u,\"serial\":%llu,\"retired_count\":%llu,\"retired\":%s,\"command_sequence\":%llu,\"ready_revision\":%llu,\"game_access\":false,\"fixture_date_transition\":true,\"same_owner\":true,\"production_permit\":false}\n",period,r.serial,r.retiredCount,r.retired?"true":"false",r.reward.submitted,r.reward.readyRevision);fflush(stdout);
}
int main(int argc,char**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4)return 2;
 _setmode(_fileno(stdin),_O_BINARY);mode="period-ipc";
 printf("{\"schema\":\"san14.a-save-ipc-fixture.v1\",\"event\":\"PREPARED\",\"pid\":%lu,\"birth\":\"%llu\",\"game_access\":false}\n",GetCurrentProcessId(),birth());fflush(stdout);
 Bootstrap init{};if(fread(&init,1,sizeof init,stdin)!=sizeof init)return 3;
 setup();machinery();reportMachinery();upstreamMachinery();cfg.base=b;cfg.binder=uintptr_t(&binder);cfg.queue=uintptr_t(&queue);cfg.caller=uintptr_t(&FreshDispatchReturn);
 cfg.room_epoch=init.epoch;memcpy(cfg.room_id,init.room_id,32);cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;
 MultiByteToWideChar(CP_UTF8,0,argv[1],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[2]);
 cfg.storage.exists=endpoint(reinterpret_cast<void*>(&reportExists));storageVtable[0x68/8]=uintptr_t(&reportExists);
 RewardData data;check(session->Initialize(cfg)&&session->Arm(),"one retained physical Owner");
 ic.base=b;ic.root=root;ic.world=world;ic.saveOwner=session;ic.binding=cfg.input_binding;ic.sample=inputSample;ic.fixtureGameCaller=uintptr_t(&InputGameReturn);ic.fixtureUiCaller=uintptr_t(&InputUiReturn);
 check(input->Initialize(ic)&&input->PreparedPlan(plan),"same upstream Gate");publish();
 check(input->Arm()&&input->Hold(ic.binding,true,1)&&gameDispatch()==0,"actual Game hold observation");
 ar::Config rc{};rc.binding=data.binding;rc.sample=RewardData::sample;check(ar::Bind(*session,rc),"same reward lane");
 auto command=data.command(2,1);check(ar::Submit(*session,data.binding,1,command)&&rewardDispatch()==0,"first cumulative reward");if(failed)return 4;
 wchar_t name[180]=L"\\\\.\\pipe\\san14-a-save-";const auto prefix=wcslen(name);
 for(unsigned i=0;i<16;++i)swprintf_s(name+prefix+i*2,_countof(name)-prefix-i*2,L"%02x",init.nonce[i]);
 a_save_ipc::Config c{};c.owner=session;c.pipeName=name;c.clientPid=strtoul(argv[3],nullptr,10);c.room_epoch=init.epoch;
 memcpy(c.room_id,init.room_id,32);memcpy(c.secret,init.secret,32);c.permit=admission;
 HANDLE end=CreateEventW(nullptr,TRUE,FALSE,nullptr);if(!end)return 5;
 a_save_ipc::Server server;if(!server.Open(c)){CloseHandle(end);return 6;}
 SecureZeroMemory(&init,sizeof init);SecureZeroMemory(c.secret,32);std::thread service([&]{server.Run(end);});
 printf("{\"schema\":\"san14.a-save-ipc-fixture.v1\",\"event\":\"READY\",\"pid\":%lu,\"birth\":\"%llu\",\"source_kind\":\"FIXTURE_ONLY\",\"capabilities\":0,\"pipe_name\":\"",GetCurrentProcessId(),birth());
 for(const wchar_t*p=name;*p;++p){if(*p==L'\\')putchar('\\');putchar(char(*p));}puts("\"}");fflush(stdout);
 planning_input_interlock::Controller controllers[2];pp::Receipt firstReceipt{};unsigned transitioned=0;
 const auto deadline=GetTickCount64()+90000;
 while(GetTickCount64()<deadline&&!failed){
  a_save_ipc::Diagnostics d{};server.Inspect(d);if(d.closed)break;
  auto saved=saveReport();if(saved.status==fs::Status::Armed){check(dispatch(0,user)==0,"pipe request reaches real User boundary");completeSave();}
  // Copy has encoded bytes and sampled the current Owner before incrementing
  // this counter. The parent waits for our boundary event before next Submit.
  if(d.copies>transitioned&&transitioned<2){
   expectedPeriod.store(0);auto&controller=controllers[transitioned];planning_input_interlock::Config pc{};
   pc.owner=session;pc.gate=input;pc.binding=data.binding;pc.base=b;pc.root=root;pc.world=world;
   const auto revision=transitioned?3u:1u;bool duplicate=false;pp::Receipt receipt{};
   check(controller.Initialize(pc)&&controller.Request(true,revision,duplicate)&&!duplicate&&controller.BeginObservation(revision)&&gameDispatch()==0&&rewardDispatch()==0&&controller.EndObservation(revision),"actual callbacks observe retirement hold");
   const auto oldBinding=data.binding;check(pp::Retire(*session,*input,controller,oldBinding,receipt),"formal period retirement after native Copy");
   check(!ar::Submit(*session,oldBinding,transitioned+2,command),"retired command rejected");
   if(!transitioned){
    firstReceipt=receipt;++data.binding.period;++data.binding.epoch;++data.binding.room_input_digest[0];rc.binding=data.binding;
    // Explicit owned world fixture write, NOT a simulated battle or B load.
    put<unsigned char>(world+0x37,21);check(pp::Rebind(*session,*input,rc,1),"same-world logical rebind");
    check(ar::ReadyFence(*session,data.binding,false,2),"explicit reward release retains upstream Gate hold");
    check(!controller.Request(false,2,duplicate),"retired Controller cannot release current Gate");
    command=data.command(12,2);check(ar::Submit(*session,data.binding,2,command)&&rewardDispatch()==0,"second cumulative reward on same physical Owner");
    expectedPeriod.store(2);
   }else{
    pp::Receipt historical{};check(pp::Historical(*session,1,historical)&&memcmp(&historical,&firstReceipt,sizeof historical)==0,"first receipt unchanged after second saved period");
    check(binds==2&&queues==2&&nativeReads==4&&data.bodies==2,"two actual diagnostic saves and two rewards");
   }
   ++transitioned;pp::Report period{};check(pp::Snapshot(*session,period),"current period report");event(transitioned,period);
  }
  Sleep(1);
 }
 SetEvent(end);service.join();CloseHandle(end);a_save_ipc::Diagnostics d{};server.Inspect(d);ss::Report r{};session->Snapshot(r);
 pp::Report period{};pp::Snapshot(*session,period);check(!r.active_scopes&&data.nodes.empty(),"native scopes and lists drained");
 printf("{\"event\":\"FINAL\",\"result\":\"%s\",\"game_access\":false,\"submits\":%llu,\"copies\":%llu,\"completed\":%u,\"owner_stopped\":%u,\"ipc_closed\":%s,\"active\":%llu,\"checks_failed\":%u,\"period_serial\":%llu,\"retired_periods\":%llu,\"reward_sequence\":%llu,\"native_reads\":%u,\"full_input_held\":false,\"production_permit\":false}\n",failed?"FAIL":"PASS",d.submits,d.copies,r.save.completed_requests,r.stopped,d.closed?"true":"false",r.active_scopes,failed,period.serial,period.retiredCount,period.reward.submitted,nativeReads);fflush(stdout);return failed?7:0;
}
