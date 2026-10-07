#include "checkpoint_native_task_provider.h"
#include <cstring>
namespace checkpoint_native_task_provider {
thread_local Provider::Record* Provider::active_=nullptr;
namespace {
template<class T>T rd(uintptr_t p){return *reinterpret_cast<const T*>(p);}
struct Forward {Provider* owner=nullptr;const CheckpointLoadWorkerFrame* frame=nullptr;CheckpointPersistentBridgeConfig callback{};};
thread_local Forward forward[64];thread_local unsigned depth=0,overflow=0;
constexpr uintptr_t payloads[]={0x508B40,0x4DA390,0x466600};
constexpr uintptr_t callers[]={0x4DA2F4,0x4BEEC2,0x4BEF2B};
constexpr uintptr_t offsets[]={0x478,0x520,0x590};
constexpr uintptr_t joins[]={0x4F7079,0x4AAF64,0x4AAF89};
}
bool Provider::reject(Bank*b,Error e,DWORD x) noexcept {if(b){++b->report.rejected;if(b->report.error==Error::None)b->report.error=e;if(x)b->report.exception=x;}return false;}
bool Provider::Register(const Config&c) noexcept {
    AcquireSRWLockExclusive(&lock_);bool ok=false;
    __try {
        if(count_==2||!c.base||c.base>UINTPTR_MAX-0x3000000||!c.session||!c.planning||
           c.file.slot!=63||memcmp(c.file.name,"svdexccSC03.s14",sizeof "svdexccSC03.s14")||!c.file.size||c.file.size>INT32_MAX)__leave;
        unsigned char digest=0;for(auto x:c.file.sha256)digest|=x;if(!digest)__leave;
        for(unsigned i=0;i<count_;++i)if(banks_[i].config.generation.callbacks.id==c.generation.callbacks.id)__leave;
        auto&b=banks_[count_];if(!b.core.Initialize(c.base)||!b.core.RegisterGeneration(c.generation)||!b.adapter.Initialize(b.core))__leave;
        b.config=c;b.report.generation=c.generation.callbacks.id;b.report.attempt=c.generation.attempt;b.report.epoch=c.generation.epoch;b.report.registered=1;++count_;ok=true;
    }__except(EXCEPTION_EXECUTE_HANDLER){ok=false;}
    ReleaseSRWLockExclusive(&lock_);return ok;
}
bool Provider::OpenWindow(std::uint64_t generation) noexcept {
    AcquireSRWLockExclusive(&lock_);bool ok=false;
    for(unsigned i=0;i<count_;++i)if(banks_[i].report.generation==generation){auto&b=banks_[i];
        if(!b.report.windowOpen&&!b.report.closed&&!b.count){b.report.windowOpen=1;current_=i;ok=true;}break;}
    ReleaseSRWLockExclusive(&lock_);return ok;
}
bool Provider::formal(Bank&b,bool requireLoad){
    const auto base=b.config.base,m=base+0x19E7310,n=rd<std::uint64_t>(m+0x10),a=rd<uintptr_t>(m+0x20);
    if(!a||!((requireLoad&&n==4)||(!requireLoad&&(n==3||n==4)))||rd<uintptr_t>(a+16)!=b.report.title)return false;
    if(n==4&&rd<uintptr_t>(a+24)!=b.report.load)return false;
    // Historical Load is only an address comparison after its join.
    return rd<uintptr_t>(b.report.title)==base+0x12DAAF0&&rd<int>(b.report.title+0x47C)==int(b.config.file.slot);
}
bool Provider::stateFormal(Bank&b,uintptr_t state,uintptr_t slot,ta::Kind&kind){
    const auto base=b.config.base,m=base+0x19E7310,a=rd<uintptr_t>(m+0x20),n=rd<std::uint64_t>(m+0x10);
    if(!a||n<3||n>6||slot<a||slot-a>=n*8||(slot-a)%8||rd<uintptr_t>(slot)!=state||rd<uintptr_t>(m+0x48)!=state||rd<DWORD>(state+0x68))return false;
    const auto vt=rd<uintptr_t>(state);
    if(vt==base+0x12CC4A8)kind=ta::Kind::User;
    else if(vt==base+0x12DB4C0)kind=ta::Kind::Menu;
    else if(vt==base+0x12CC9B8)kind=ta::Kind::Game;
    else if(vt==base+0x12DBD68)kind=ta::Kind::Load;
    else return false;
    return true;
}
Provider::Record* Provider::record(Bank&b,const ta::Creation&c){
    if(b.report.error!=Error::None)return nullptr;
    for(unsigned i=0;i<count_;++i)for(unsigned j=0;j<banks_[i].count;++j){const auto&r=banks_[i].records[j];
        if(!r.complete&&(r.creation.worker==c.worker||r.creation.callable==c.callable)){reject(&b,Error::Order);return nullptr;}}
    if(b.count==256){reject(&b,Error::Capacity);b.report.windowOpen=0;return nullptr;}
    auto&r=b.records[b.count];if(!b.core.RecordCreation(b.report.generation,c,r.ticket)){reject(&b,Error::Attribution);return nullptr;}
    r.creation=c;r.bank=unsigned(&b-banks_);r.owner=this;++b.count;++b.report.creations;b.report.retainedTasks=b.count;return &r;
}
Provider::Record* Provider::matching(uintptr_t worker,DWORD thread,bool enteredOnly){
    Record* result=nullptr;for(unsigned i=0;i<count_;++i)for(unsigned j=0;j<banks_[i].count;++j){auto&r=banks_[i].records[j];
        if(!r.complete&&!r.abnormal&&r.creation.worker==worker&&r.creation.workerThread==thread&&(!enteredOnly||r.entered)){
            if(result)return nullptr;result=&r;}}
    return result;
}
#define NEED(test,err) do{if(!(test))return reject(b,Error::err);}while(0)
bool Provider::body(const Capture&c){
    Bank*b=current_<count_?&banks_[current_]:nullptr;
    NEED(c.thread==GetCurrentThreadId(),Thread);
    // Find the bank by captured native image range. A late callback must never
    // use the latest bank merely because it is latest.
    auto* active=active_&&active_->owner==this?active_:nullptr;
    if(active)b=&banks_[active->bank];
    const auto candidateBase=b?b->config.base:0;std::uint64_t rva=c.rip-candidateBase;
    Bank*roleMatch=nullptr;std::uint64_t roleRva=0;
    if(!active){for(unsigned i=0;i<count_;++i){auto&v=banks_[i];const auto off=c.rip-v.config.base;
        if(off==0x50B730||off==0x834D98||off==0x834DB4||off==0x50B632||off==0x50B4AE){
            b=&v;rva=off;break;}
        if(off==0x834B60||off==0x4CC690||off==0x4F7079||off==0x4AAF64||off==0x4AAF89){
            bool belongs=off==0x4CC690?c.rcx==v.report.title:off==0x834B60?(c.rcx==v.report.load+0x478||c.rcx==v.report.title+0x520||c.rcx==v.report.title+0x590):c.rbx==(off==0x4F7079?v.report.load:v.report.title);
            if(v.report.loadBound&&belongs&&!v.report.closed){
                const unsigned role=off==0x4F7079?0:off==0x4AAF64?1:2;
                if((off==0x4CC690&&v.report.titleCallback)||((off==0x4F7079||off==0x4AAF64||off==0x4AAF89)&&v.report.roles[role].joined))continue;
                if(roleMatch)return reject(&v,Error::Order);roleMatch=&v;roleRva=off;}}
        if(off==0x50B598&&v.selected&&v.selectionThread==c.thread){b=&v;rva=off;break;}
    }}
    if(roleMatch){b=roleMatch;rva=roleRva;}
    NEED(b,Window);++sequence_;
    if(rva==0x50B4B3){
        if(!b->report.windowOpen){++b->report.ignored;return true;}
        NEED(!b->selected,Order);auto slot=rd<uintptr_t>(c.rsp+0x40),state=rd<uintptr_t>(slot);ta::Kind kind{};
        const auto vt=rd<uintptr_t>(state),image=b->config.base;
        if(vt!=image+0x12CC4A8&&vt!=image+0x12DB4C0&&vt!=image+0x12CC9B8&&vt!=image+0x12DBD68){InterlockedIncrement64(&unknown_);return true;}
        NEED(stateFormal(*b,state,slot,kind),Formal);++b->report.events;b->selected=true;b->selectionThread=c.thread;b->selectionState=state;b->selectionSlot=slot;return true;
    }
    if(rva==0x50B598){
        if(!b->selected){++b->report.ignored;return true;}
        NEED(c.thread==b->selectionThread&&rd<uintptr_t>(c.rsp+0x40)==b->selectionSlot,Thread);
        ta::Creation t{};NEED(stateFormal(*b,b->selectionState,b->selectionSlot,t.kind),Formal);
        t.state=b->selectionState;t.formalSlot=b->selectionSlot;t.worker=c.rdi;
        NEED(t.worker&&rd<uintptr_t>(t.state+0x50)==t.worker,Native);t.callable=rd<uintptr_t>(t.worker+0x50);
        NEED(t.callable&&rd<uintptr_t>(t.callable)==b->config.base+0x12F2440&&rd<uintptr_t>(b->config.base+0x12F2440+0x10)==b->config.base+0x50B730,Native);
        NEED(rd<uintptr_t>(rd<uintptr_t>(t.callable+8))==t.formalSlot,Native);
        t.workerThread=rd<DWORD>(rd<uintptr_t>(t.worker+8)+0x10);t.parentThread=c.thread;t.serial=++serial_;
        t.payload=b->config.base+0x50B730;t.creationSite=c.rip;t.selectionSite=b->config.base+0x50B4B3;
        ++b->report.events;b->selected=false;return record(*b,t)!=nullptr;
    }
    if(rva==0x4DA240){
        NEED(!b->report.loadBound&&b->report.windowOpen,Order);
        checkpoint_dynamic_native_session::Report s{};b->config.session->Snapshot(s);
        NEED(s.attempt==b->report.attempt&&s.casPublished,Receipt);
        NEED(rd<uintptr_t>(c.rcx)==b->config.base+0x12DBD68&&rd<DWORD>(c.rcx+0x470)==1,Native);
        auto closure=rd<uintptr_t>(c.rcx+0x48);NEED(closure&&rd<uintptr_t>(closure)==b->config.base+0x12EA4D0&&rd<uintptr_t>(b->config.base+0x12EA4D0+0x10)==b->config.base+0x4FAC30,Native);
        auto source=b->config.base+0x201ECE0,n=rd<std::uint64_t>(source+16),cap=rd<std::uint64_t>(source+24);
        NEED(n==strlen(b->config.file.name)&&cap>=n&&cap<=8192&&(cap>=16||cap==15),Source);
        NEED(!memcmp(reinterpret_cast<void*>(cap>=16?rd<uintptr_t>(source):source),b->config.file.name,size_t(n+1)),Source);
        NEED(rd<DWORD>(b->config.base+0x201ECD0)==b->config.file.slot&&!rd<DWORD>(b->config.base+0x201ECD4)&&!rd<DWORD>(b->config.base+0x201ECD8),Source);
        b->report.load=c.rcx;b->report.closure=closure;b->report.title=rd<uintptr_t>(closure+8);
        NEED(formal(*b,true),Formal);NEED(rd<uintptr_t>(b->config.base+0x19E7310+0x48)==c.rcx,Native);
        NEED(rd<DWORD>(rd<uintptr_t>(rd<uintptr_t>(c.rcx+0x50)+8)+0x10)==c.thread,Thread);
        ++b->report.events;b->report.loadBound=1;return true;
    }
    if(rva==0x4CC690){
        NEED(b->report.roles[0].joined&&!b->report.titleCallback&&c.rdx==b->report.load&&rd<uintptr_t>(c.rsp)==b->config.base+0x497134,Order);
        NEED(formal(*b,true)&&rd<DWORD>(b->config.base+0x201EC08)==1,Native);++b->report.events;b->report.titleCallback=1;return true;
    }
    if(rva==0x834B60){
        int role=-1;for(unsigned i=0;i<3;++i)if(c.rcx==(i?b->report.title:b->report.load)+offsets[i])role=int(i);
        NEED(role>=0,Source);auto&w=b->report.roles[role];NEED(!w.start&&rd<uintptr_t>(c.rsp)==b->config.base+callers[role],Order);
        NEED(formal(*b,role<2),Formal);
        if(role){NEED(b->report.titleCallback&&b->report.roles[0].joined,Order);NEED(rd<DWORD>(b->report.title+0x470)==(role==1?13u:15u),Native);}
        if(role==2)NEED(b->report.roles[1].done,Order);
        w.control=c.rcx;w.threadObject=rd<uintptr_t>(c.rcx);w.callable=rd<uintptr_t>(c.rcx+0x48);w.method=rd<uintptr_t>(b->config.base+0x138E8D0);w.payload=b->config.base+payloads[role];
        NEED(w.threadObject&&rd<uintptr_t>(c.rcx+8)&&w.callable&&rd<uintptr_t>(w.callable)==b->config.base+0x138E8C0&&rd<uintptr_t>(w.callable+8)==w.payload&&!rd<DWORD>(c.rcx+0x54),Native);
        w.workerThread=rd<DWORD>(w.threadObject+0x10);w.startThread=c.thread;
        ta::Creation t{};t.kind=static_cast<ta::Kind>(unsigned(ta::Kind::EmbeddedLoad)+role);t.serial=++serial_;t.state=role?b->report.title:b->report.load;t.worker=w.control;t.callable=w.callable;t.payload=w.payload;t.parentThread=c.thread;t.workerThread=w.workerThread;t.creationSite=b->config.base+callers[role]-5;
        NEED(record(*b,t),Attribution);++b->report.events;w.creation=t.serial;w.start=sequence_;return true;
    }
    if(rva==0x50B730||rva==0x834D98){
        uintptr_t worker=rva==0x50B730?rd<uintptr_t>(rd<uintptr_t>(rd<uintptr_t>(rd<uintptr_t>(c.rcx+8)))+0x50):c.rbx;
        auto*t=matching(worker,c.thread,false);if(!t){InterlockedIncrement64(&unknown_);return true;}NEED(!t->entered,Order);b=&banks_[t->bank];
        NEED(c.rip==b->config.base+rva&&t->creation.callable==c.rcx,Native);
        if(rva==0x50B730)NEED(rd<uintptr_t>(c.rsp)==b->config.base+0x834D9B,Native);
        else {NEED(c.rdi==rd<uintptr_t>(worker)&&rd<uintptr_t>(worker+0x48)==c.rcx&&!rd<DWORD>(worker+0x50)&&!rd<DWORD>(worker+0x54),Native);
            auto role=unsigned(t->creation.kind)-unsigned(ta::Kind::EmbeddedLoad);b->report.roles[role].invoke=sequence_;}
        // Core's 4FABC0 is its canonical generic-callable ABI label, not this
        // capture's RIP. Actual source capture is the validated 834D98 vcall.
        ta::Entry e{t->creation.serial,b->config.base+(rva==0x50B730?0x50B730:0x4FABC0),b->config.base+0x834D9B,t->creation.state,worker,c.rcx,c.thread};
        NEED(b->core.Enter(t->ticket,e,t->execution),Attribution);++b->report.events;t->entered=true;t->previous=active_;active_=t;return true;
    }
    if(rva==0x508B40||rva==0x4DA390||rva==0x466600){
        if(!active){InterlockedIncrement64(&unknown_);return true;}
        NEED(active&&active->creation.callable==c.rcx&&active->creation.payload==c.rip,Order);
        auto role=unsigned(active->creation.kind)-unsigned(ta::Kind::EmbeddedLoad);NEED(role<3&&!b->report.roles[role].payloadEntry,Order);
        ++b->report.events;b->report.roles[role].payloadEntry=sequence_;return true;
    }
    if(rva==0x50B690){NEED(active&&b->core.RecordYield(active->ticket,c.rip,c.thread),Attribution);return true;}
    if(rva==0x50B4AE){
        auto state=rd<uintptr_t>(rd<uintptr_t>(c.rsp+0x40)),worker=rd<uintptr_t>(state+0x50);
        Record*t=nullptr;for(unsigned i=0;i<count_;++i)for(unsigned j=0;j<banks_[i].count;++j){auto&q=banks_[i].records[j];if(!q.complete&&q.creation.worker==worker&&q.creation.parentThread==c.thread)t=&q;}
        NEED(t&&banks_[t->bank].core.RecordResume(t->ticket,c.rip,c.thread),Attribution);return true;
    }
    if(rva==0x834D9B){
        if(!active){InterlockedIncrement64(&unknown_);return true;}const bool embedded=unsigned(active->creation.kind)>=4;auto control=embedded?active->creation.worker:active->creation.worker+8;
        NEED(c.rbx==control&&c.rdi==rd<uintptr_t>(control)&&!rd<DWORD>(control+0x50),Native);
        if(embedded){auto&w=b->report.roles[unsigned(active->creation.kind)-4];NEED(w.payloadEntry&&!w.returned,Order);w.returned=sequence_;}
        NEED(b->core.Leave(active->execution,ta::Outcome::Returned),Attribution);++b->report.events;active->returned=true;active_=active->previous;return true;
    }
    if(rva==0x834DB4){
        Record*t=matching(c.rbx,c.thread,true);if(!t)t=matching(c.rbx-8,c.thread,true);if(!t){InterlockedIncrement64(&unknown_);return true;}NEED(t->returned&&!t->done,Order);b=&banks_[t->bank];
        NEED(c.rip==b->config.base+0x834DB4&&rd<DWORD>(c.rbx+0x50)==1&&!rd<DWORD>(c.rbx+0x54),Native);
        ++b->report.events;t->done=true;if(unsigned(t->creation.kind)>=4)b->report.roles[unsigned(t->creation.kind)-4].done=sequence_;return true;
    }
    if(rva==0x50B632){
        Record*t=nullptr;for(unsigned i=0;i<count_;++i)for(unsigned j=0;j<banks_[i].count;++j){auto&q=banks_[i].records[j];if(!q.complete&&q.creation.worker==c.rdi&&q.creation.parentThread==c.thread)t=&q;}
        if(!t){InterlockedIncrement64(&unknown_);return true;}NEED(t->done,Order);b=&banks_[t->bank];NEED(!rd<uintptr_t>(t->creation.state+0x50),Native);
        ta::Completion done{t->creation.serial,c.rip,t->creation.worker,t->creation.callable,0,c.thread,rd<DWORD>(c.rdi+0x58),rd<DWORD>(c.rdi+0x78)};
        NEED(b->core.RecordCompletion(t->ticket,done),Attribution);++b->report.events;t->complete=true;return true;
    }
    for(unsigned role=0;role<3;++role)if(rva==joins[role]){
        auto&w=b->report.roles[role];NEED(w.done&&w.returned&&!w.joined&&c.rbx==(role?b->report.title:b->report.load),Order);
        NEED(formal(*b,role==0),Formal);NEED(!rd<uintptr_t>(w.control)&&!rd<uintptr_t>(w.control+8)&&!rd<uintptr_t>(w.control+0x60)&&rd<DWORD>(w.control+0x50)==1,Native);
        if(!role)NEED(rd<DWORD>(b->report.load+0x470)==2&&rd<DWORD>(b->config.base+0x201EC08)==1,Native);
        else NEED(rd<DWORD>(b->report.title+0x470)==16,Native);
        auto*t=matching(w.control,w.workerThread,true);NEED(t,Order);
        ta::Completion done{w.creation,c.rip,w.control,w.callable,0,c.thread,1,0};NEED(b->core.RecordCompletion(t->ticket,done),Attribution);
        ++b->report.events;t->complete=true;w.joined=sequence_;w.joinThread=c.thread;b->report.threeJoins=b->report.roles[0].joined&&b->report.roles[1].joined&&b->report.roles[2].joined;return true;
    }
    ++b->report.ignored;return true;
}
#undef NEED
bool Provider::Observe(const Capture&c) noexcept {
    AcquireSRWLockExclusive(&lock_);bool ok=false;
    __try {__try {ok=body(c);}__except(EXCEPTION_EXECUTE_HANDLER){ok=reject(current_<count_?&banks_[current_]:nullptr,Error::Memory,GetExceptionCode());}}
    __finally {ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Provider::Abnormal() noexcept {
    AcquireSRWLockExclusive(&lock_);bool ok=false;auto*r=active_;
    if(r&&r->owner==this){auto&b=banks_[r->bank];ok=b.core.Leave(r->execution,ta::Outcome::Abnormal);r->abnormal=true;active_=r->previous;reject(&b,Error::Native);}
    ReleaseSRWLockExclusive(&lock_);return ok;
}
bool Provider::CloseCompletedWindow(std::uint64_t generation) noexcept {
    AcquireSRWLockExclusive(&lock_);bool ok=false;
    for(unsigned i=0;i<count_;++i){auto&b=banks_[i];if(b.report.generation!=generation)continue;
        checkpoint_dynamic_native_session::Report s{};b.config.session->Snapshot(s);checkpoint_persistent_planning::Report p{};checkpoint_persistent_planning::Snapshot(*b.config.planning,p);
        bool drained=!b.selected;for(unsigned j=0;j<b.count;++j)drained=drained&&b.records[j].complete;
        if(drained&&b.report.threeJoins&&p.planningBoundaryObserved&&!p.error&&!p.inFlight&&p.attempt==b.report.attempt&&p.epoch==b.report.epoch&&p.generation==generation&&
            s.attempt==b.report.attempt&&s.bytes.observedWorkerAndBytes&&s.lifecycle.receiptReady&&s.identity.receiptReady&&p.historicalLoad==b.report.load&&p.historicalTitle==b.report.title&&
            p.expected.byteSize==b.config.file.size&&!memcmp(p.expected.sha256,b.config.file.sha256,32)&&b.report.error==Error::None){
            b.report.planning=1;b.report.windowOpen=0;b.report.closed=1;ok=true;}break;
    }ReleaseSRWLockExclusive(&lock_);return ok;
}
bool Provider::Snapshot(std::uint64_t generation,Report&r) noexcept {r={};AcquireSRWLockShared(&lock_);bool ok=false;for(unsigned i=0;i<count_;++i)if(banks_[i].report.generation==generation){r=banks_[i].report;ok=true;break;}ReleaseSRWLockShared(&lock_);return ok;}
checkpoint_persistent_route::Generation Provider::ProxyGeneration(std::uint64_t id) noexcept{return {id,Before,After,Finally,this};}
void Provider::Before(const CheckpointLoadWorkerFrame*f,void*p){
    auto*o=static_cast<Provider*>(p);if(depth==64||overflow){++overflow;return;}auto&v=forward[depth++];v={};v.owner=o;v.frame=f;
    if(active_&&active_->owner==o){v.callback=o->banks_[active_->bank].adapter.Configuration(nullptr);v.callback.before(f,v.callback.context);}
    else InterlockedIncrement64(&o->unknown_);
}
void Provider::After(const CheckpointLoadWorkerFrame*f,void*p){if(overflow||!depth)return;auto&v=forward[depth-1];if(v.owner==p&&v.frame==f&&v.callback.after)v.callback.after(f,v.callback.context);}
void Provider::Finally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*x,void*p){
    if(overflow){--overflow;return;}if(!depth)return;auto&v=forward[depth-1];if(v.owner!=p||v.frame!=f)return;
    __try {if(v.callback.finally)v.callback.finally(f,x,v.callback.context);}__finally{v={};--depth;}
}
}
