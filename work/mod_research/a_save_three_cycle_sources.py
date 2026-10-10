"""Bounded native three-save successor sources, emitted without changing predecessors.

The generated runtime retains one process, Owner, parent hook and pipe. Each new
planning Controller is used once. No production installer or ABI export is added.
"""
from pathlib import Path

def replace(text, before, after, count=1):
    if text.count(before) != count:
        raise ValueError(f'predecessor shape changed: {before[:100]!r}')
    return text.replace(before, after)

def sources(root):
    root=Path(root)
    names=('a_save_repeat_runtime.h','a_save_repeat_runtime.cpp',
           'a_save_dispatch_mailbox.h','a_save_dispatch_mailbox.cpp',
           'a_save_dispatch_ipc.h','a_save_dispatch_ipc.cpp','checkpoint_fresh_save.cpp',
           'checkpoint_fresh_save_packet.cpp','checkpoint_fresh_save_packet.py')
    out={n:(root/n).read_text(encoding='utf-8') for n in names}
    for name, pairs in {
        'a_save_dispatch_mailbox.h': [('records[2]','records[3]'),('artifacts_[2]','artifacts_[3]')],
        'a_save_dispatch_mailbox.cpp': [('report_.count==2','report_.count==3')],
        'a_save_dispatch_ipc.h': [('records_[2]','records_[3]')],
        'a_save_dispatch_ipc.cpp': [('count_>=2','count_>=3')],
        'checkpoint_fresh_save_packet.cpp': [('r.completed_requests<=2','r.completed_requests<=3')],
        'checkpoint_fresh_save_packet.py': [("r['completed_requests'] <= 2","r['completed_requests'] <= 3")],
        'checkpoint_fresh_save.cpp': [('history[2]','history[3]'),('files[2]','files[3]'),
                                     ('fileEvidence[2]','fileEvidence[3]'),('completed[2]','completed[3]'),('p_->count>=2','p_->count>=3')],
        'a_save_repeat_runtime.h': [('Period periods_[2]','Period periods_[3]'),
                                 ('planning_input_interlock::Controller controller_;','planning_input_interlock::Controller controllers_[3];'),
                                 ('planning_input_interlock::Controller secondController_;','')]
    }.items():
        for before,after in pairs:out[name]=replace(out[name],before,after)
    s=out['a_save_repeat_runtime.cpp']
    start=s.index('bool Runtime::RequestNext(');end=s.index('void Runtime::RepeatSnapshot(',start)
    s=s[:start]+'''bool Runtime::RequestNext(const Next&n)noexcept {
 AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {
  const auto index=InterlockedCompareExchange(&activePeriod_,0,0);
  if(index<0||index>=2||!r_.sourcesArmed||repeat_.requested||InterlockedCompareExchange(&stopped_,0,0)||r_.error!=Error::None||
     (repeat_.state!=RepeatState::Idle&&repeat_.state!=RepeatState::ReadySecond))__leave;
  const auto&p=periods_[index];
  if(p.binding.period==UINT64_MAX||n.previousGeneration!=std::uint64_t(index+1)||n.generation!=std::uint64_t(index+2)||
     n.period!=p.binding.period+1||n.epoch<=p.binding.epoch||!nonzero(n.previousSha256,32)||!nonzero(n.inputDigest,32))__leave;
  bool reused=false;for(LONG i=0;i<=index;++i)if(!memcmp(n.inputDigest,periods_[i].binding.room_input_digest.data(),32))reused=true;
  if(reused)__leave;
  auto y=p.year;auto m=p.month;auto d=p.day;
  if(d==21){d=1;if(m==12){m=1;if(y==65535)__leave;++y;}else ++m;}else d=static_cast<unsigned char>(d+10);
  if(n.year!=y||n.month!=m||n.day!=d)__leave;
  repeat_.request=n;repeat_.requested=1;repeat_.state=RepeatState::Queued;
  repeat_.previousArtifactMatched=false;repeat_.nativeDateMatched=false;
  periods_[index+1]={this,p.binding,n.year,n.month,n.day};
  periods_[index+1].binding.period=n.period;periods_[index+1].binding.epoch=n.epoch;
  memcpy(periods_[index+1].binding.room_input_digest.data(),n.inputDigest,32);ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
'''+s[end:]
    s=replace(s,'&controller_,&mailbox_','&controllers_[0],&mailbox_')
    s=replace(s,'checkpoint_fresh_save::Artifact*previous=nullptr;',
              'checkpoint_fresh_save::Artifact*previous=nullptr;const auto index=InterlockedCompareExchange(&activePeriod_,0,0);')
    s=replace(s,'r_.mailbox.count!=1||r_.mailbox.records[0].state!=a_save_dispatch_mailbox::State::Delivered||r_.mailbox.records[0].message.request.generation!=1',
              'index<0||index>=2||r_.mailbox.count!=unsigned(index+1)||r_.mailbox.records[index].state!=a_save_dispatch_mailbox::State::Delivered||r_.mailbox.records[index].message.request.generation!=std::uint64_t(index+1)')
    s=replace(s,'owner_->CopyArtifact(1,*previous)','owner_->CopyArtifact(std::uint64_t(index+1),*previous)')
    s=replace(s,'controller_.Snapshot(observed)','controllers_[index].Snapshot(observed)')
    s=replace(s,'identity(periods_[0])||!controller_.BeginObservation','identity(periods_[index])||!controllers_[index].BeginObservation')
    s=replace(s,'identity(periods_[1])){if(!identity(periods_[0]))','identity(periods_[index+1])){if(!identity(periods_[index]))')
    s=replace(s,'next.binding=periods_[1].binding;next.sample=planningSample;next.context=&periods_[1];',
              'next.binding=periods_[index+1].binding;next.sample=planningSample;next.context=&periods_[index+1];')
    s=replace(s,'pc.binding=periods_[1].binding','pc.binding=periods_[index+1].binding')
    s=replace(s,'secondController_.Initialize(pc)','controllers_[index+1].Initialize(pc)')
    s=replace(s,'host_.BindPeriod(secondController_)','host_.BindPeriod(controllers_[index+1])')
    s=replace(s,'InterlockedExchange(&activePeriod_,1);repeat_.activeGeneration=2;',
              'InterlockedExchange(&activePeriod_,index+1);repeat_.activeGeneration=std::uint64_t(index+2);repeat_.requested=0;')
    s=replace(s,'const bool observed=controller_.EndObservation(repeatRevision_);',
              'const auto index=InterlockedCompareExchange(&activePeriod_,0,0);const bool observed=controllers_[index].EndObservation(repeatRevision_);')
    s=replace(s,'Retire(*owner_,*gate_,controller_,periods_[0].binding,retired_)',
              'Retire(*owner_,*gate_,controllers_[index],periods_[index].binding,retired_)')
    s=replace(s,'repeat_.retiredCount=1','++repeat_.retiredCount')
    s=replace(s,'controller_.EndObservation(repeatRevision_);repeatFail',
              'controllers_[InterlockedCompareExchange(&activePeriod_,0,0)].EndObservation(repeatRevision_);repeatFail')
    out['a_save_repeat_runtime.cpp']=s
    return out
