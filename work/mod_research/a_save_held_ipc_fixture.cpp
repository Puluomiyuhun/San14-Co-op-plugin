// Owned synchronous engine-thread fixture, not a production game scheduler.
#include "planning_checkpoint_save.h"
#include "planning_period_base_fixture.inc"
#include "a_save_held_ipc.h"
#include <fcntl.h>
#include <io.h>
namespace pcs=planning_checkpoint_save;namespace hi=a_save_held_ipc;
#pragma pack(push,1)
struct Bootstrap {unsigned char secret[32],room_id[32];std::uint64_t epoch;unsigned char nonce[16];};
#pragma pack(pop)
static_assert(sizeof(Bootstrap)==88);
static pcs::Evidence evidence;
static unsigned submitCalls=0,copyCalls=0;static HANDLE shutdownEvent=nullptr;static bool stopInPermit=false;
static bool permit(void*,const fs::Request&q,const unsigned char*)noexcept{
 if(stopInPermit)SetEvent(shutdownEvent);
 return q.generation==1&&q.period==1&&q.year==203&&q.month==8&&q.day==11&&q.force==12&&q.ruler==666;
}
static bool save(void*,const fs::Request&q,const unsigned char*)noexcept{
 ++submitCalls;check(!session->Submit(q),"ordinary Submit still refuses held Ready");
 if(!pcs::Submit(*session,*input,interlock,evidence,q))return false;
 // This owned thread plays both the trusted host and diagnostic engine. Real
 // games need owner-thread dispatch; a pipe service cannot invoke this directly.
 check(dispatch(0,user)==0,"held-save uses actual User bridge");completeSave();
 ar::Report reward{};ar::Snapshot(*session,reward);ag::Report gate{};input->Snapshot(gate);
 check(reward.readyFence&&reward.readyRevision==1&&gate.requested,"Ready and Gate remain held during native save");return !failed;
}
static bool copy(void*,std::uint64_t generation,fs::Artifact&artifact)noexcept{
 ++copyCalls;if(!pcs::Copy(*session,*input,interlock,evidence,generation,artifact))return false;
 ar::Report reward{};ar::Snapshot(*session,reward);ag::Report gate{};input->Snapshot(gate);
 check(reward.readyFence&&reward.readyRevision==1&&gate.requested,"Copy completes without releasing either hold");
 printf("{\"event\":\"HELD_SAVE_COPIED\",\"generation\":%llu,\"ready_held\":%s,\"gate_held\":%s,\"ready_revision\":%llu,\"game_access\":false,\"production_permit\":false}\n",generation,reward.readyFence?"true":"false",gate.requested?"true":"false",reward.readyRevision);fflush(stdout);return !failed;
}
int main(int argc,char**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4&&(argc!=5||strcmp(argv[4],"permit-stop")))return 2;
 _setmode(_fileno(stdin),_O_BINARY);mode="held-ipc";stopInPermit=argc==5;
 printf("{\"schema\":\"san14.a-save-ipc-fixture.v1\",\"event\":\"PREPARED\",\"pid\":%lu,\"birth\":\"%llu\",\"game_access\":false}\n",GetCurrentProcessId(),birth());fflush(stdout);
 Bootstrap init{};if(fread(&init,1,sizeof init,stdin)!=sizeof init)return 3;
 setup();machinery();reportMachinery();upstreamMachinery();cfg.base=b;cfg.binder=uintptr_t(&binder);cfg.queue=uintptr_t(&queue);cfg.caller=uintptr_t(&FreshDispatchReturn);
 cfg.room_epoch=init.epoch;memcpy(cfg.room_id,init.room_id,32);cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;
 MultiByteToWideChar(CP_UTF8,0,argv[1],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[2]);cfg.storage.exists=endpoint(reinterpret_cast<void*>(&reportExists));storageVtable[0x68/8]=uintptr_t(&reportExists);
 RewardData data;check(session->Initialize(cfg)&&session->Arm(),"one physical held-save Owner");
 ic.base=b;ic.root=root;ic.world=world;ic.saveOwner=session;ic.binding=cfg.input_binding;ic.sample=inputSample;ic.fixtureGameCaller=uintptr_t(&InputGameReturn);ic.fixtureUiCaller=uintptr_t(&InputUiReturn);
 check(input->Initialize(ic)&&input->PreparedPlan(plan),"matching held-save Gate");publish();check(input->Arm()&&input->Hold(ic.binding,true,1)&&gameDispatch()==0,"actual initial Game boundary");
 ar::Config rc{};rc.binding=data.binding;rc.sample=RewardData::sample;check(ar::Bind(*session,rc),"same reward lane");
 planning_input_interlock::Config pc{};pc.owner=session;pc.gate=input;pc.binding=data.binding;pc.base=b;pc.root=root;pc.world=world;bool duplicate=false;
 check(interlock.Initialize(pc)&&interlock.Request(true,1,duplicate)&&interlock.BeginObservation(1)&&gameDispatch()==0&&rewardDispatch()==0&&interlock.EndObservation(1),"actual Controller Ready observation before pipe admission");
 planning_input_interlock::Report ir{};interlock.Snapshot(ir);planning_period_owner::Report pr{};check(planning_period_owner::Snapshot(*session,pr),"current native period");
 evidence.binding=data.binding;evidence.date=pr.date;evidence.periodSerial=pr.serial;evidence.readyRevision=ir.revision;evidence.gateRevision=ir.gateRevision;evidence.observation=ir.observation;evidence.cut=0;if(failed)return 4;
 wchar_t name[180]=L"\\\\.\\pipe\\san14-a-save-";const auto prefix=wcslen(name);for(unsigned i=0;i<16;++i)swprintf_s(name+prefix+i*2,_countof(name)-prefix-i*2,L"%02x",init.nonce[i]);
 hi::Config c{};c.owner=session;c.pipeName=name;c.clientPid=strtoul(argv[3],nullptr,10);c.room_epoch=init.epoch;memcpy(c.room_id,init.room_id,32);memcpy(c.secret,init.secret,32);c.permit=permit;c.submit=save;c.copy=copy;
 // Missing execution ports cannot silently fall back to the legacy Owner API.
 {hi::Server absent;auto invalid=c;invalid.copy=nullptr;check(!absent.Open(invalid),"required complete trusted execution port pair");}
 // Failed Open's destructor calls Stop on c_.owner only after config acceptance;
 // the null-port refusal above must therefore leave the actual Owner alive.
 ss::Report alive{};session->Snapshot(alive);check(!alive.stopped,"null port refused before claiming live Owner");
 shutdownEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);if(!shutdownEvent)return 5;
 hi::Server server;if(!server.Open(c)){CloseHandle(shutdownEvent);return 6;}SecureZeroMemory(&init,sizeof init);SecureZeroMemory(c.secret,32);
 printf("{\"schema\":\"san14.a-save-ipc-fixture.v1\",\"event\":\"READY\",\"pid\":%lu,\"birth\":\"%llu\",\"source_kind\":\"FIXTURE_ONLY\",\"capabilities\":0,\"pipe_name\":\"",GetCurrentProcessId(),birth());for(const wchar_t*p=name;*p;++p){if(*p==L'\\')putchar('\\');putchar(char(*p));}puts("\"}");fflush(stdout);
 server.Run(shutdownEvent);CloseHandle(shutdownEvent);hi::Diagnostics d{};server.Inspect(d);ss::Report r{};session->Snapshot(r);ar::Report ar{};a_reward_save_owner::Snapshot(*session,ar);ag::Report g{};input->Snapshot(g);
 check(!r.active_scopes&&data.nodes.empty(),"actual callback scopes drained");
 printf("{\"event\":\"FINAL\",\"result\":\"%s\",\"game_access\":false,\"submits\":%llu,\"copies\":%llu,\"completed\":%u,\"owner_stopped\":%u,\"ipc_closed\":%s,\"active\":%llu,\"checks_failed\":%u,\"backend_submit_calls\":%u,\"backend_copy_calls\":%u,\"ready_held\":%s,\"gate_held\":%s,\"ready_revision\":%llu,\"full_input_held\":false,\"production_permit\":false}\n",failed?"FAIL":"PASS",d.submits,d.copies,r.save.completed_requests,r.stopped,d.closed?"true":"false",r.active_scopes,failed,submitCalls,copyCalls,ar.readyFence?"true":"false",g.requested?"true":"false",ar.readyRevision);fflush(stdout);return failed?7:0;
}
