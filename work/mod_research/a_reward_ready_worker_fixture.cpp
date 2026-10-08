#include "a_reward_save_owner.h"
#include "a_reward_save_owner_base.inc"
#include <array>
#include <iostream>
#include <sstream>
#include <algorithm>
#include <map>
#include <set>
#include <cctype>
namespace ar=a_reward_save_owner;namespace rw=checkpoint_reward_owned_replay;namespace ph=checkpoint_planning_hold;
struct RewardData;
static RewardData*rd=nullptr;
struct RewardData {
 std::array<unsigned char,0x100>tasks{},unit{},dummyForce{},dummyDistrict{};
 std::array<std::array<unsigned char,0x100>,2>forces{},districts{},cities{};
 std::array<std::array<unsigned char,0x1a0>,7>persons{};
 std::array<unsigned,7>ids{666,97,759,500,101,264,411};
 std::array<unsigned,2>forceIds{12,2},districtIds{11,2},cityIds{19,13},rulerIds{666,500};
 std::vector<uintptr_t>heads=std::vector<uintptr_t>(1024),tails=heads,counts=heads,phs=std::vector<uintptr_t>(0x14000),pts=phs,pcs=phs;
 std::array<std::array<uintptr_t,3>,2>dNodes{},cNodes{};unsigned dslot=1,cslot=2,handle=20;
 std::vector<std::array<uintptr_t,3>*>nodes;
 std::array<unsigned char,0x78>normal{};std::array<unsigned char,0x68>mouseBuffer{};std::array<unsigned char,0x258>raw{};
 ph::Binding binding{};unsigned ctors=0,dtors=0,bodies=0;bool attached=true;
 template<class T>static uintptr_t addr(T*p){return reinterpret_cast<uintptr_t>(p);}
 static ph::RewardArgs*ctor(ph::RewardArgs*a){auto&f=*rd;++f.ctors;a->vtable=b+0x123e210;a->handle=addr(&f.handle);put<std::uint64_t>(b+0x19e1c38+0x30,1);return a;}
 static uintptr_t append(uintptr_t pool,unsigned slot,unsigned char flag){auto&f=*rd;check(pool==b+0x19e1bf0&&slot==f.handle&&flag==1,"append ABI");auto*n=new std::array<uintptr_t,3>{};(*n)[2]=f.tails[slot];if(f.tails[slot])put<uintptr_t>(f.tails[slot]+8,addr(n));else f.heads[slot]=addr(n);f.tails[slot]=addr(n);++f.counts[slot];f.nodes.push_back(n);put<std::uint64_t>(b+0x19e1bf0+0x30,f.nodes.size());return addr(n);}
 static void dtor(ph::RewardArgs*a){auto&f=*rd;++f.dtors;for(auto*n:f.nodes)delete n;f.nodes.clear();f.heads[f.handle]=f.tails[f.handle]=f.counts[f.handle]=0;a->handle=0;put<std::uint64_t>(b+0x19e1c38+0x30,0);put<std::uint64_t>(b+0x19e1bf0+0x30,0);}
 static int predicate(uintptr_t p){return get<unsigned char>(p+0x120)<100?1:0;}
 static bool validate(void*,const ph::Binding&x){auto&f=*rd;return f.attached&&x.native.attempt==f.binding.native.attempt&&x.native.attachment==f.binding.native.attachment&&x.native.owner_generation==f.binding.native.owner_generation&&x.period==f.binding.period&&x.epoch==f.binding.epoch&&x.room_input_digest==f.binding.room_input_digest;}
 static void*sortie(unsigned*p,int){return p;}static unsigned mouse(const void*,unsigned){return 0;}
 static int reward(ph::RewardArgs*a){auto&f=*rd;++f.bodies;if(mode=="fence-active"){std::thread t([&]{check(!ar::ReadyFence(*session,f.binding,true,1),"active real callback denies foreign-thread fence");});t.join();}
  ar::Report now{};ar::Snapshot(*session,now);check(now.active==1&&now.created==f.ctors&&!f.nodes.empty(),"actual owner and pooled args in native body");
  check(!session->Submit(request(1))&&!session->SetUserHold(true,100)&&!ar::ReadyFence(*session,f.binding,true,100),"running reward excludes save hold ready");
  if(mode=="exception")RaiseException(0xE014AC01,0,0,nullptr);
  if(mode=="cancel-running"){std::thread t([&]{check(ar::Cancel(*session,f.binding,now.submitted),"cross thread cancel");});t.join();}
  const auto city=a->funding;const auto did=get<unsigned char>(city+0x30);const auto district=get<uintptr_t>(root+0xde40+did*8);
  put<unsigned>(city+0x34,get<unsigned>(city+0x34)-unsigned(f.counts[f.handle])*100);put<unsigned char>(district+0x14,get<unsigned char>(district+0x14)-1);
  for(auto n=f.heads[f.handle];n;n=get<uintptr_t>(n+8)){auto person=get<uintptr_t>(root+0x148+get<unsigned>(n)*8);put<unsigned char>(person+0x120,static_cast<unsigned char>((std::min)(100u,unsigned(get<unsigned char>(person+0x120))+4)));}
  return 1;
 }
 static bool sample(void*,uintptr_t u,unsigned actor,ar::Source&out){auto&f=*rd;unsigned k=actor==12?0:actor==2?1:2;if(k==2||u!=user)return false;
  auto&r=out.reward;r.binding=f.binding;r.base=b;r.root=root;r.world=world;r.user=user;r.authorized_force=static_cast<unsigned char>(actor);r.authorized_ruler=static_cast<unsigned short>(f.rulerIds[k]);r.ctor=ctor;r.append=append;r.dtor=dtor;r.predicate=predicate;r.validate_attachment=validate;
  auto&a=out.admission;a.binding=f.binding;inputSample(nullptr,a.pending);a.buffers={{f.normal.data(),f.normal.size()},{f.mouseBuffer.data(),f.mouseBuffer.size()},{f.raw.data(),f.raw.size()}};a.reward=reward;a.sortie=sortie;a.mouse=mouse;return true;
 }
 RewardData(){rd=this;binding.native=cfg.input_binding;binding.period=1;binding.epoch=7;binding.room_input_digest[0]=6;
  put<uintptr_t>(addr(normal.data()),addr(raw.data()));put<uintptr_t>(root+0x85128,addr(tasks.data()));put<uintptr_t>(addr(tasks.data())+0x10,b+0x129bb28);
  put<uintptr_t>(addr(unit.data()),b+0x123e288);put<uintptr_t>(addr(dummyForce.data()),b+0x129fe58);put<uintptr_t>(addr(dummyDistrict.data()),b+0x129fec8);
  for(unsigned i=0;i<=500;++i)put<uintptr_t>(root+0x7df60+i*8,addr(unit.data()));for(unsigned i=0;i<=51;++i){put<uintptr_t>(root+0xde40+i*8,addr(dummyDistrict.data()));put<uintptr_t>(root+0xdca0+i*8,addr(dummyForce.data()));}
  for(unsigned k=0;k<2;++k){auto f=addr(forces[k].data()),d=addr(districts[k].data()),c=addr(cities[k].data());
   put<uintptr_t>(f,b+0x129fe58);put<unsigned short>(f+0x10,static_cast<unsigned short>(rulerIds[k]));put<uintptr_t>(root+0xdca0+forceIds[k]*8,f);
   put<uintptr_t>(d,b+0x129fec8);put<unsigned char>(d+0x10,static_cast<unsigned char>(forceIds[k]));put<unsigned char>(d+0x11,1);put<unsigned short>(d+0x12,static_cast<unsigned short>(rulerIds[k]));put<unsigned char>(d+0x14,k?10:18);put<uintptr_t>(root+0xde40+districtIds[k]*8,d);
   put<uintptr_t>(c,b+0x129fd10);put<unsigned short>(c+0x10,static_cast<unsigned short>(cityIds[k]));put<unsigned char>(c+0x30,static_cast<unsigned char>(districtIds[k]));put<unsigned>(c+0x34,k?20804:83308);put<unsigned short>(c+0x4e,static_cast<unsigned short>(cityIds[k]));put<uintptr_t>(root+0xdaa8+cityIds[k]*8,c);
   dNodes[k][0]=d;cNodes[k][0]=c;if(k){dNodes[0][1]=addr(dNodes[1].data());dNodes[1][2]=addr(dNodes[0].data());cNodes[0][1]=addr(cNodes[1].data());cNodes[1][2]=addr(cNodes[0].data());}
  }
  for(unsigned i=0;i<ids.size();++i){unsigned k=i<3?0:1;auto x=addr(persons[i].data());put<uintptr_t>(x,b+0x12a00d0);put<unsigned short>(x+0x10,static_cast<unsigned short>(ids[i]));put<unsigned char>(x+0x118,static_cast<unsigned char>(districtIds[k]));put<unsigned short>(x+0x11a,static_cast<unsigned short>(cityIds[k]));put<unsigned char>(x+0x120,i<3?80:70);put<uintptr_t>(root+0x148+ids[i]*8,x);}
  for(auto pair:{std::make_pair(0x123e288+0x18,0x211420),std::make_pair(0x12a00d0+0x18,0x2119f0),std::make_pair(0x129fec8+0x18,0x211610),std::make_pair(0x129fe58+0x60,0x20b610),std::make_pair(0x129fd10+0x18,0x211540),std::make_pair(0x129fd10+0x80,0x209a00),std::make_pair(0x129fd10+0x90,0x20c2e0)})put<uintptr_t>(b+pair.first,b+pair.second);
  put<unsigned>(b+0x18ecf30,1);for(auto pair:{std::make_pair(0x19e1bf0,1024u),std::make_pair(0x201d3a0,0x14000u)}){bool ints=pair.second==1024;put<uintptr_t>(b+pair.first+8,addr(ints?heads.data():phs.data()));put<uintptr_t>(b+pair.first+0x10,addr(ints?heads.data():phs.data()));put<uintptr_t>(b+pair.first+0x18,addr(ints?tails.data():pts.data()));put<uintptr_t>(b+pair.first+0x28,addr(ints?counts.data():pcs.data()));put<unsigned>(b+pair.first+0x40,pair.second);put<std::uint64_t>(b+pair.first+0x38,10000);}
  put<std::uint64_t>(b+0x19e1c38+0x38,1024);phs[1]=addr(dNodes[0].data());pts[1]=addr(dNodes[1].data());phs[2]=addr(cNodes[0].data());pts[2]=addr(cNodes[1].data());pcs[1]=pcs[2]=2;
  put<uintptr_t>(root+0xc8,b+0x123f3f8);put<uintptr_t>(root+0xd0,addr(&dslot));put<uintptr_t>(root+0x78,b+0x123f3b8);put<uintptr_t>(root+0x80,addr(&cslot));
 }
 rw::Command command(unsigned actor,unsigned n){unsigned k=actor==12?0:1;rw::Command c{};c.nonce[0]=static_cast<unsigned char>(n);c.year=203;c.month=8;c.day=get<unsigned char>(world+0x37);c.viewer_force=get<unsigned char>(world+0x3A);c.command_force=static_cast<unsigned char>(actor);c.charged_district=static_cast<unsigned char>(districtIds[k]);c.ruler=static_cast<unsigned short>(rulerIds[k]);c.funding_city=static_cast<unsigned short>(cityIds[k]);c.count=1;c.officers[0]=k?101:97;c.expires_at_tick=GetTickCount64()+30000;return c;}
};
static DWORD rewardDispatch(){__try{return static_cast<DWORD>(FreshDispatch(0,user));}__except(EXCEPTION_EXECUTE_HANDLER){return GetExceptionCode();}}
static void rewardSummary(){ar::Report r{};ar::Snapshot(*session,r);ss::Report s{};session->Snapshot(s);check(!r.active&&!s.active_scopes&&!s.bridges[0].active&&!s.bridges[1].active,"all owned scopes finally drained");check(rd->ctors==rd->dtors&&rd->nodes.empty(),"owned pooled lists restored");printf("{\"result\":\"%s\",\"case\":\"%s\",\"checks\":%u,\"failures\":%u,\"submitted\":%llu,\"completed\":%llu,\"reward_calls\":%u,\"ctor\":%u,\"dtor\":%u,\"finally\":%llu,\"abnormal\":%llu,\"error\":%u,\"uncertain\":%s,\"game_access\":false,\"room_ready\":false}\n",failed?"FAIL":"PASS",mode.c_str(),passed,failed,r.submitted,r.completed,rd->bodies,rd->ctors,rd->dtors,r.finally,r.abnormal,unsigned(r.error),r.uncertain?"true":"false");}
// Strict bounded JSON subset for owned-process test transport only. No network listener.
struct WorkerInput {std::string op;unsigned force=0,district=0,revision=0;bool value=false;std::vector<unsigned>officers;};
static bool workerParse(const std::string&s,WorkerInput&out){
 if(s.size()>4096)return false;size_t i=0;std::set<std::string>keys;
 auto ws=[&]{while(i<s.size()&&std::isspace(static_cast<unsigned char>(s[i])))++i;};
 auto chr=[&](char c){ws();if(i>=s.size()||s[i]!=c)return false;++i;return true;};
 auto str=[&](std::string&v){ws();if(i>=s.size()||s[i++]!='"')return false;v.clear();while(i<s.size()&&s[i]!='"'){const char c=s[i++];if(!(std::isalnum(static_cast<unsigned char>(c))||c=='_'||c=='-'))return false;v+=c;}if(i>=s.size())return false;++i;return true;};
 auto num=[&](unsigned&v){ws();if(i>=s.size()||s[i]<'0'||s[i]>'9')return false;v=0;while(i<s.size()&&s[i]>='0'&&s[i]<='9'){if(v>100000)return false;v=v*10+unsigned(s[i++]-'0');}return true;};
 if(!chr('{'))return false;for(;;){std::string k;if(!str(k)||!keys.insert(k).second||!chr(':'))return false;
  if(k=="op"){if(!str(out.op))return false;}else if(k=="revision"){if(!num(out.revision))return false;}else if(k=="value"){ws();if(s.compare(i,4,"true")==0){out.value=true;i+=4;}else if(s.compare(i,5,"false")==0){out.value=false;i+=5;}else return false;}else if(k=="force_id"){if(!num(out.force))return false;}else if(k=="district_id"){if(!num(out.district))return false;}else if(k=="officer_ids"){if(!chr('['))return false;ws();if(i<s.size()&&s[i]==']')++i;else for(;;){unsigned id=0;if(out.officers.size()>=rw::MaxOfficers||!num(id))return false;out.officers.push_back(id);ws();if(i<s.size()&&s[i]==']'){++i;break;}if(!chr(','))return false;}}else return false;
  ws();if(i<s.size()&&s[i]=='}'){++i;break;}if(!chr(','))return false;
 }ws();if(i!=s.size())return false;
 if(out.op=="ready_fence")return keys==std::set<std::string>{"op","revision","value"};
 if(out.op=="fence_sample")return keys==std::set<std::string>{"op","revision"};
 if(out.op=="sample"||out.op=="close")return keys==std::set<std::string>{"op"};
 return out.op=="reward"&&keys==std::set<std::string>{"op","force_id","district_id","officer_ids"};
}
static void workerSample(){auto&f=*rd;printf("{\"date\":{\"year\":203,\"month\":8,\"day\":11},\"viewer_force_id\":%u,\"forces\":[",get<unsigned char>(world+0x3A));for(unsigned k=0;k<2;++k){if(k)printf(",");printf("{\"force_id\":%u,\"district_id\":%u,\"city_id\":%u,\"ruler_id\":%u,\"gold\":%u,\"action_points\":%u,\"officers\":[",f.forceIds[k],f.districtIds[k],f.cityIds[k],f.rulerIds[k],get<unsigned>(RewardData::addr(f.cities[k].data())+0x34),get<unsigned char>(RewardData::addr(f.districts[k].data())+0x14));bool first=true;for(unsigned n=k?4:1;n<(k?7u:3u);++n){if(!first)printf(",");first=false;printf("{\"id\":%u,\"loyalty\":%u}",f.ids[n],get<unsigned char>(RewardData::addr(f.persons[n].data())+0x120));}printf("]}");}printf("]}");}
// Observation belongs to this owned worker lifecycle; this is not a production installer.
struct ReadyEvidence {unsigned acceptedRevision=0,observedRevision=0;bool acceptedValue=false;std::uint64_t nativeDelta=0,returnedDelta=0,finallyDelta=0,heldDelta=0;DWORD thread=0;};
static ReadyEvidence readyEvidence;
static unsigned originalViewer=0;
static bool readyIdentity(){return get<uintptr_t>(b+0x1FCA1E0)==root&&get<uintptr_t>(root+0x85130)==world&&get<uintptr_t>(root)==b+0x12AA6B0&&get<uintptr_t>(world)==b+0x12AA638&&get<unsigned short>(world+0x34)==203&&get<unsigned char>(world+0x36)==8&&get<unsigned char>(world+0x37)==11&&get<unsigned char>(world+0x3A)==originalViewer;}
static bool cleanReady(ar::Report&r,ss::Report&s){if(!ar::Snapshot(*session,r))return false;session->Snapshot(s);return readyIdentity()&&r.bound&&r.error==ar::Error::None&&!r.uncertain&&!r.queued&&!r.active&&!s.active_scopes&&!s.bridges[0].active&&!s.bridges[1].active&&!s.save_lane&&!s.user_hold_requested&&s.error==ss::Error::None&&!s.stopped;}
static bool requestFence(bool value,unsigned revision,bool&duplicate){duplicate=false;ar::Report r{};ss::Report s{};if(!revision||!cleanReady(r,s))return false;
 if(revision==readyEvidence.acceptedRevision){duplicate=value==readyEvidence.acceptedValue&&r.readyRevision==revision&&r.readyFence==value;return duplicate;}
 if(revision<readyEvidence.acceptedRevision)return false;
 if(!ar::ReadyFence(*session,rd->binding,value,revision))return false;readyEvidence={};readyEvidence.acceptedRevision=revision;readyEvidence.acceptedValue=value;return true;
}
static bool observeFence(unsigned revision){readyEvidence.observedRevision=0;readyEvidence.nativeDelta=readyEvidence.returnedDelta=readyEvidence.finallyDelta=readyEvidence.heldDelta=0;
 ar::Report beforeReward{};ss::Report before{};if(!revision||!cleanReady(beforeReward,before)||!beforeReward.readyFence||beforeReward.readyRevision!=revision||readyEvidence.acceptedRevision!=revision||!readyEvidence.acceptedValue)return false;
 const auto code=rewardDispatch();ar::Report afterReward{};ss::Report after{};const bool clean=cleanReady(afterReward,after);
 if(after.bridges[0].native_started<before.bridges[0].native_started||after.bridges[0].native_returned<before.bridges[0].native_returned||after.bridges[0].finally_calls<before.bridges[0].finally_calls||after.held_scopes<before.held_scopes)return false;
 readyEvidence.nativeDelta=after.bridges[0].native_started-before.bridges[0].native_started;readyEvidence.returnedDelta=after.bridges[0].native_returned-before.bridges[0].native_returned;readyEvidence.finallyDelta=after.bridges[0].finally_calls-before.bridges[0].finally_calls;readyEvidence.heldDelta=after.held_scopes-before.held_scopes;readyEvidence.thread=GetCurrentThreadId();
 if(!clean||code||afterReward.readyRevision!=revision||!afterReward.readyFence||readyEvidence.nativeDelta||readyEvidence.returnedDelta||readyEvidence.finallyDelta!=1||readyEvidence.heldDelta!=1||after.bridges[0].abnormal_exits!=before.bridges[0].abnormal_exits||after.bridges[0].cleanup_faults!=before.bridges[0].cleanup_faults)return false;
 readyEvidence.observedRevision=revision;return true;
}
static void readyReply(bool ok,bool duplicate,bool observed){ar::Report r{};ar::Snapshot(*session,r);ss::Report s{};session->Snapshot(s);printf("{\"ok\":%s,\"source\":\"owned-native-fixture\",\"duplicate\":%s,\"requested\":%s,\"value\":%s,\"revision\":%llu,\"ready_revision\":%llu,\"observed\":%s,\"observed_revision\":%u,\"user_native_started_delta\":%llu,\"user_native_returned_delta\":%llu,\"user_finally_delta\":%llu,\"held_delta\":%llu,\"active\":%llu,\"queued\":%s,\"uncertain\":%s,\"owner_stopped\":%s,\"owner_error\":%u,\"reward_error\":%u,\"user_native_started\":%llu,\"user_native_returned\":%llu,\"user_finally\":%llu,\"held_scopes\":%llu,\"thread_id\":%lu,\"all_input_held\":false,\"room_ready\":false,\"full_world\":false,\"native_gameplay_enabled\":false}\n",ok?"true":"false",duplicate?"true":"false",r.readyFence?"true":"false",r.readyFence?"true":"false",r.readyRevision,r.readyRevision,observed?"true":"false",observed?readyEvidence.observedRevision:0,observed?readyEvidence.nativeDelta:0,observed?readyEvidence.returnedDelta:0,observed?readyEvidence.finallyDelta:0,observed?readyEvidence.heldDelta:0,r.active+s.active_scopes+s.bridges[0].active+s.bridges[1].active,r.queued?"true":"false",r.uncertain?"true":"false",s.stopped?"true":"false",unsigned(s.error),unsigned(r.error),s.bridges[0].native_started,s.bridges[0].native_returned,s.bridges[0].finally_calls,s.held_scopes,readyEvidence.thread);fflush(stdout);}

static int workerLoop(){std::string line;unsigned sequence=0;for(unsigned frame=0;frame<256&&std::getline(std::cin,line);++frame){WorkerInput q{};if(!workerParse(line,q)){puts("{\"ok\":false,\"error\":\"invalid_owned_fixture_request\"}");fflush(stdout);continue;}if(q.op=="close"){puts("{\"ok\":true,\"closed\":true}");fflush(stdout);return failed?1:0;}if(q.op=="sample"){printf("{\"ok\":true,\"source\":\"owned-native-fixture\",\"sample\":");workerSample();puts("}");fflush(stdout);continue;}
  if(q.op=="ready_fence"){bool duplicate=false;const bool ok=requestFence(q.value,q.revision,duplicate);readyReply(ok,duplicate,false);continue;}
  if(q.op=="fence_sample"){const bool ok=observeFence(q.revision);readyReply(ok,false,ok);continue;}
  readyEvidence.observedRevision=0;
  if((q.force!=12&&q.force!=2)||q.district>51||q.officers.empty()){puts("{\"ok\":false,\"error\":\"invalid_fixture_actor\"}");fflush(stdout);continue;}
  auto c=rd->command(q.force,sequence+1);c.charged_district=static_cast<unsigned char>(q.district);c.count=unsigned(q.officers.size());for(unsigned n=0;n<c.count;++n)c.officers[n]=q.officers[n];const bool submitted=ar::Submit(*session,rd->binding,sequence+1,c);DWORD exit=0;if(submitted){++sequence;exit=rewardDispatch();}ar::Report r{};ar::Snapshot(*session,r);const bool ok=submitted&&exit==0&&r.error==ar::Error::None&&r.completed==sequence&&!r.uncertain;
  printf("{\"ok\":%s,\"source\":\"owned-native-fixture\",\"sequence\":%u,\"submitted\":%s,\"error\":%u,\"exception\":%lu,\"uncertain\":%s,\"native_returned\":%s,\"args_released\":%s,\"owned_slot_cleared\":%s,\"capture_calls\":%u,\"native_calls\":%u,\"sample\":",ok?"true":"false",sequence,submitted?"true":"false",unsigned(r.error),exit,r.uncertain?"true":"false",r.reward.native_returned?"true":"false",r.reward.args_released?"true":"false",r.reward.owned_slot_cleared?"true":"false",r.reward.capture_calls,rd->bodies);workerSample();puts("}");fflush(stdout);
 }return failed?1:0;}
static int readyCases(){const auto name=mode;auto command=rd->command(2,1);bool duplicate=false;
 if(mode=="fence-queued"){check(ar::Submit(*session,rd->binding,1,command),"actual pending reward");check(!requestFence(true,1,duplicate),"queued reward denies fence");ar::Report r{};ar::Snapshot(*session,r);check(r.queued&&r.readyRevision==0,"refusal leaves pending command and revision");check(rewardDispatch()==0,"pending reward executes");}
 else if(mode=="fence-save"){check(session->Submit(request(1)),"save admitted");check(!requestFence(true,1,duplicate),"save lane denies fence");check(dispatch(0,user)==0,"actual Save User callback");completeSave();check(saveReport().status==fs::Status::Complete,"actual Save finishes");}
 else if(mode=="fence-active"){check(ar::Submit(*session,rd->binding,1,command)&&rewardDispatch()==0,"actual reward holds scope for concurrent setter rejection");}
 else if(mode=="fence-uncertain"){mode="cancel-running";check(ar::Submit(*session,rd->binding,1,command)&&rewardDispatch()==0,"actual active cancellation returns");mode=name;ar::Report r{};ar::Snapshot(*session,r);check(r.uncertain&&!requestFence(true,1,duplicate)&&!observeFence(1),"uncertainty refuses fence and observation");rewardSummary();return failed?1:0;}
 else if(mode=="fence-world"){check(requestFence(true,1,duplicate)&&!readyEvidence.observedRevision,"setter alone not observed");put<uintptr_t>(root+0x85130,world+0x2000);check(!observeFence(1)&&!readyEvidence.observedRevision,"changed world invalidates observation");rewardSummary();return failed?1:0;}
 else if(mode=="fence-original"){check(!observeFence(1),"ordinary native callback cannot be mislabeled fence");ss::Report before{},after{};session->Snapshot(before);check(dispatch(0,user)==0,"ordinary User callback really executes");session->Snapshot(after);check(after.bridges[0].native_started==before.bridges[0].native_started+1&&!readyEvidence.observedRevision,"native original return alone never means suppressed");check(!requestFence(true,1,duplicate),"upstream stopped ordinary scope cannot become Ready");rewardSummary();return failed?1:0;}
 check(requestFence(true,1,duplicate)&&!readyEvidence.observedRevision,"setter requests but never observes");check(requestFence(true,1,duplicate)&&duplicate&&!readyEvidence.observedRevision,"duplicate setter does not advance or observe");check(!requestFence(false,1,duplicate)&&!requestFence(true,0,duplicate),"same revision conflict and stale revision refuse");check(observeFence(1)&&readyEvidence.observedRevision==1&&readyEvidence.finallyDelta==1&&!readyEvidence.nativeDelta,"actual suppressed User scope supplies observation");check(observeFence(1)&&readyEvidence.finallyDelta==1,"fresh repeat observation no revision change");check(!ar::Submit(*session,rd->binding,2,command)&&!session->Submit(request(2)),"fenced owner denies commands/save");check(requestFence(false,2,duplicate)&&!readyEvidence.observedRevision&&!observeFence(1),"explicit release invalidates former receipt");check(!requestFence(true,1,duplicate),"late old setter cannot reclose");rewardSummary();return failed?1:0;}

int main(int argc,char**argv){SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4)return 2;mode=argv[1];setup();machinery();reportMachinery();upstreamMachinery();cfg.base=b;cfg.binder=uintptr_t(&binder);cfg.queue=uintptr_t(&queue);cfg.caller=uintptr_t(&FreshDispatchReturn);cfg.room_epoch=7;cfg.room_id[0]=1;cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;MultiByteToWideChar(CP_UTF8,0,argv[2],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[3]);cfg.storage.exists=endpoint(reinterpret_cast<void*>(&reportExists));storageVtable[0x68/8]=uintptr_t(&reportExists);
 RewardData data;if(mode=="worker-b")put<unsigned char>(world+0x3A,2);check(session->Initialize(cfg)&&session->Arm(),"single actual User/Save owner");ic.base=b;ic.root=root;ic.world=world;ic.saveOwner=session;ic.binding=cfg.input_binding;ic.sample=inputSample;ic.fixtureGameCaller=uintptr_t(&InputGameReturn);ic.fixtureUiCaller=uintptr_t(&InputUiReturn);check(input->Initialize(ic)&&input->PreparedPlan(plan),"upstream gate");publish();check(input->Arm()&&input->Hold(ic.binding,true,1),"same existing upstream held boundary");check(gameDispatch()==0,"actual Game boundary observed before Save");ar::Config rc{};rc.binding=data.binding;rc.sample=RewardData::sample;check(ar::Bind(*session,rc),"reward lane binds exact same owner");originalViewer=get<unsigned char>(world+0x3A);if(mode.rfind("fence-",0)==0)return failed?1:readyCases();if(mode=="worker"||mode=="worker-b")return failed?1:workerLoop();
 auto c=data.command(2,1);if(mode=="wrong-world")put<uintptr_t>(root+0x85130,world+0x2000);
 if(mode=="wrong-binding"){auto bad=data.binding;++bad.native.owner_generation;check(!ar::Submit(*session,bad,1,c),"wrong generation refused");rewardSummary();return failed?1:0;}
 if(mode=="hold"){check(session->SetUserHold(true,1)&&!ar::Submit(*session,data.binding,1,c),"hold excludes reward");check(rewardDispatch()==0,"actual hold skip");rewardSummary();return failed?1:0;}
 if(mode=="ready"){check(ar::ReadyFence(*session,data.binding,true,1)&&!ar::Submit(*session,data.binding,1,c)&&!session->Submit(request(1)),"local Ready fence excludes reward/save");check(rewardDispatch()==0,"real local Ready skip");check(ar::ReadyFence(*session,data.binding,false,2),"ready release");}
 if(mode=="save-first"){check(session->Submit(request(1))&&!ar::Submit(*session,data.binding,1,c),"active save excludes reward");check(dispatch(0,user)==0,"save User queues");completeSave();check(saveReport().status==fs::Status::Complete,"save finishes before reward");}
 check(ar::Submit(*session,data.binding,1,c),"reward queued");check(!session->Submit(request(1))&&!session->SetUserHold(true,1)&&!ar::ReadyFence(*session,data.binding,true,1),"queued reward excludes save hold ready");
 if(mode=="cancel"){check(ar::Cancel(*session,data.binding,1),"cancel queued");check(dispatch(0,user)==0&&!data.bodies,"cancelled never invokes reward");rewardSummary();return failed?1:0;}
 if(mode=="wrong-world")check(dispatch(0,user)==0&&!data.bodies,"world drift denies native reward");else {auto result=rewardDispatch();check(result==(mode=="exception"?0xE014AC01u:0),"reward scope return or exact exception");}
 ar::Report r{};ar::Snapshot(*session,r);
 if(mode=="wrong-world"||mode=="exception"||mode=="cancel-running"){check(r.error!=ar::Error::None&&!r.completed&&!ar::Submit(*session,data.binding,2,c),"terminal fault denies next task");if(mode=="exception")check(r.abnormal==1&&r.uncertain,"exception real FINALLY uncertain");}
 else{check(r.completed==1&&data.bodies==1,"first reward committed");auto second=data.command(12,2);check(ar::Submit(*session,data.binding,2,second)&&rewardDispatch()==0,"same owner second reward");ar::Snapshot(*session,r);check(r.completed==2&&data.bodies==2&&r.created==2&&r.destroyed==2,"two concrete owners synchronously cleaned");if(mode=="two-rewards-save"){check(session->Submit(request(1))&&dispatch(0,user)==0,"save after two rewards");completeSave();check(saveReport().status==fs::Status::Complete,"actual Save lifecycle complete");}}
 rewardSummary();return failed?1:0;
}
