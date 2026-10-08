// Included once after the explicit physical Owner implementation successor.
// All logical transitions use that Owner's existing control lock.
namespace planning_period_owner {
namespace {
namespace ag=a_save_upstream_gate;
struct State {bool tracked=false;DWORD thread=0;Date date{};const void*controller=nullptr;
 std::uint64_t serial=1,count=0;Receipt history[16]{};};
State periods;
bool sameDate(const Date&a,const Date&b){return a.year==b.year&&a.month==b.month&&a.day==b.day&&a.viewer==b.viewer;}
bool readDate(Date&d)noexcept {__try {auto&s=ar::lane;
 if(*reinterpret_cast<const uintptr_t*>(s.base+0x1FCA1E0)!=s.root||
    *reinterpret_cast<const uintptr_t*>(s.root+0x85130)!=s.world||
    *reinterpret_cast<const uintptr_t*>(s.user)!=s.base+0x12CC4A8)return false;
 const auto*w=reinterpret_cast<const unsigned char*>(s.world);
 d.year=*reinterpret_cast<const unsigned short*>(w+0x34);d.month=w[0x36];d.day=w[0x37];d.viewer=w[0x3A];
 return d.year&&d.month>=1&&d.month<=12&&(d.day==1||d.day==11||d.day==21)&&d.viewer<51;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool nextDate(const Date&a,const Date&b){auto next=a;if(a.day!=21)next.day=static_cast<unsigned char>(a.day+10);
 else {next.day=1;if(a.month!=12)++next.month;else{if(a.year==USHRT_MAX)return false;next.month=1;++next.year;}}
 return sameDate(next,b);}
bool quiet(){auto&s=ar::lane;return ar::healthy()&&s.report.bound&&!s.report.queued&&!s.report.active&&
 !s.report.uncertain&&!s.running&&!*s.scopes&&!*s.save&&!*s.hold&&s.report.submitted==s.report.completed;}
bool hookSlots(const checkpoint_load_hook_set::Report&h)noexcept {__try {
 if(!h.initialized||h.count!=2||h.exceptionCode)return false;
 for(unsigned i=0;i<2;++i){const auto&e=h.entries[i];if(!e.known||!e.published||e.error||!e.binding.slot||!e.binding.hook||*e.binding.slot!=e.binding.hook)return false;}return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool gateReport(a_save_user_owner::Owner&o,ag::Owner&gate,ag::Report&g,a_save_user_owner::Report&u){auto&s=ar::lane;
 if(!gate.MatchesOwner(&o,s.input,s.base,s.root,s.world))return false;
 gate.Snapshot(g);o.Snapshot(u);
 if(!g.armed||g.stopped||g.error!=ag::Error::None||!g.requested||g.active||!hookSlots(g.hooks)||
 !u.armed||u.stopped||u.error!=a_save_user_owner::Error::None||u.active_scopes||u.save_lane||u.user_hold_requested||!hookSlots(u.hooks))return false;
 for(const auto&b:g.bridges)if(b.active)return false;for(const auto&b:u.bridges)if(b.active)return false;return true;
}
// Fresh source spans, not an approval flag; no actual business calls.
bool fresh(const ar::Config&c)noexcept {__try {auto&s=ar::lane;ar::Source source{};
 Date now{};if(!c.sample||!readDate(now)||!c.sample(c.context,s.user,now.viewer,source))return false;
 if(!ar::binding(source.admission.binding,c.binding)||!ar::binding(source.reward.binding,c.binding)||
 source.reward.base!=s.base||source.reward.root!=s.root||source.reward.world!=s.world||source.reward.user!=s.user||
 source.reward.authorized_force!=now.viewer||source.admission.pending.profile_base!=s.base||source.admission.pending.states[4]!=s.user)return false;
#ifndef A_REWARD_SAVE_OWNER_FIXTURE
 if(uintptr_t(source.admission.reward)!=s.base+0x1D6DA0)return false;
#endif
 checkpoint_native_input_pending::Adapter a;if(a.Bind(source.admission.pending)!=checkpoint_native_input_pending::Error::None)return false;
 const auto r=a.InspectCurrent(s.input);return r.error==checkpoint_native_input_pending::Error::None&&
 r.decision==checkpoint_native_input_pending::Decision::QuiescentObserved&&r.stack_count==5&&r.user_phase==2;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
}
bool CurrentController(a_save_user_owner::Owner&o,const ar::ph::Binding&b,const void*controller,bool unclaimed)noexcept {
 auto&s=ar::lane;if(&o!=s.owner||!s.lock||!controller)return false;AcquireSRWLockShared(s.lock);bool ok=false;
 __try {Date now{};if(s.periodRetired||!ar::binding(b,s.config.binding)||!readDate(now))__leave;
 // Snapshot may run on the retained window thread. Mutating callers enforce
 // their execution thread separately; logical identity itself is read-only.
 if(periods.tracked&&!sameDate(now,periods.date))__leave;
 ok=unclaimed?!periods.controller:periods.controller==controller;
 }__finally{ReleaseSRWLockShared(s.lock);}return ok;
}
bool ClaimController(a_save_user_owner::Owner&o,const ar::ph::Binding&b,const void*controller)noexcept {
 auto&s=ar::lane;if(&o!=s.owner||!s.lock||!controller)return false;AcquireSRWLockExclusive(s.lock);bool ok=false;
 __try {Date now{};if(!quiet()||s.periodRetired||!ar::binding(b,s.config.binding)||!readDate(now)||!fresh(s.config)||periods.controller)__leave;
 if(periods.tracked&&(GetCurrentThreadId()!=periods.thread||!sameDate(now,periods.date)))__leave;
 periods.tracked=true;periods.thread=GetCurrentThreadId();periods.date=now;periods.controller=controller;ok=true;
 }__finally{ReleaseSRWLockExclusive(s.lock);}return ok;
}
bool Retire(a_save_user_owner::Owner&o,ag::Owner&gate,planning_input_interlock::Controller&controller,const ar::ph::Binding&b,Receipt&out)noexcept {
 out={};auto&s=ar::lane;if(&o!=s.owner||!s.lock||!periods.tracked||GetCurrentThreadId()!=periods.thread||periods.controller!=&controller)return false;
 planning_input_interlock::Report observed{};controller.Snapshot(observed);ag::Report g{};a_save_user_owner::Report u{};
 if(!observed.observed||observed.uncertain||observed.error!=planning_input_interlock::Error::None||
 observed.thread!=periods.thread||observed.coverage!=planning_input_interlock::BoundedCoverage||!observed.observation||
 !gateReport(o,gate,g,u)||observed.gateRevision!=g.revision)return false;
 AcquireSRWLockExclusive(s.lock);bool ok=false;__try {Date now{};
 if(!quiet()||s.periodRetired||!ar::binding(b,s.config.binding)||!s.report.readyFence||!readDate(now)||!sameDate(now,periods.date)||
 !fresh(s.config)||periods.count>=16||observed.revision!=s.report.readyRevision||
 observed.reward.submitted!=s.report.submitted||observed.reward.completed!=s.report.completed||
 !hookSlots(g.hooks)||!hookSlots(u.hooks))__leave;
 Receipt receipt{};receipt.serial=periods.serial;receipt.binding=s.config.binding;receipt.date=now;receipt.reward=s.report;
 receipt.gateRevision=g.revision;receipt.observation=observed.observation;periods.history[periods.count++]=receipt;
 s.periodRetired=true;out=receipt;ok=true;
 }__finally{ReleaseSRWLockExclusive(s.lock);}return ok;
}
bool Rebind(a_save_user_owner::Owner&o,ag::Owner&gate,const ar::Config&next,std::uint64_t retiredSerial)noexcept {
 auto&s=ar::lane;if(&o!=s.owner||!s.lock||!periods.tracked||GetCurrentThreadId()!=periods.thread)return false;
 ag::Report g{};a_save_user_owner::Report u{};if(!gateReport(o,gate,g,u))return false;
 AcquireSRWLockExclusive(s.lock);bool ok=false;__try {Date now{};const auto&old=s.config.binding;
 if(!quiet()||!s.periodRetired||!s.report.readyFence||retiredSerial!=periods.serial||!periods.count||
 periods.history[periods.count-1].serial!=retiredSerial||!readDate(now)||!nextDate(periods.date,now)||
 old.period==UINT64_MAX||next.binding.period!=old.period+1||next.binding.epoch<=old.epoch||
 next.binding.native.attempt!=old.native.attempt||next.binding.native.attachment!=old.native.attachment||
 next.binding.native.owner_generation!=old.native.owner_generation||
 next.binding.room_input_digest==old.room_input_digest||!fresh(next)||!hookSlots(g.hooks)||!hookSlots(u.hooks))__leave;
 bool digest=false;for(auto v:next.binding.room_input_digest)digest|=v!=0;if(!digest)__leave;
 // Replace the logical binding only. Never reset cumulative sequence/revision,
 // bridge claim, error, save driver, physical publication or historical receipts.
 s.config=next;s.periodRetired=false;periods.date=now;++periods.serial;periods.controller=nullptr;ok=true;
 }__finally{ReleaseSRWLockExclusive(s.lock);}return ok;
}
bool Snapshot(a_save_user_owner::Owner&o,Report&out)noexcept {out={};auto&s=ar::lane;if(&o!=s.owner||!s.lock)return false;
 AcquireSRWLockShared(s.lock);out.tracked=periods.tracked;out.retired=s.periodRetired;out.thread=periods.thread;
 out.serial=periods.serial;out.retiredCount=periods.count;out.binding=s.config.binding;out.date=periods.date;out.reward=s.report;
 ReleaseSRWLockShared(s.lock);return true;}
bool Historical(a_save_user_owner::Owner&o,std::uint64_t serial,Receipt&out)noexcept {out={};auto&s=ar::lane;if(&o!=s.owner||!s.lock)return false;
 AcquireSRWLockShared(s.lock);bool found=false;for(std::uint64_t i=0;i<periods.count;++i)if(periods.history[i].serial==serial){out=periods.history[i];found=true;break;}
 ReleaseSRWLockShared(s.lock);return found;}
}
