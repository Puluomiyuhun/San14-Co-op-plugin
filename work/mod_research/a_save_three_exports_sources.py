"""Bounded three-save production overlay; predecessors remain byte-for-byte intact.

Includes the current native-turn path (normal business forwarding, rebuilt
planning objects and guards), not just the older repeat runtime experiment.
"""
from pathlib import Path
from a_save_three_cycle_sources import sources as cycle_sources, replace


def sources(root):
    root=Path(root)
    out=cycle_sources(root)
    # Reuse the already checked three-controller RequestNext and common capacity
    # changes. The runtime below preserves native-turn retirement/return behavior.
    three=out['a_save_repeat_runtime.cpp']
    request=three[three.index('bool Runtime::RequestNext('):three.index('void Runtime::RepeatSnapshot(')]
    request=replace(request,'repeat_.previousArtifactMatched=false;repeat_.nativeDateMatched=false;',
        'repeat_.previousArtifactMatched=false;repeat_.nativeDateMatched=false;returnedSource_=false;runningFrames_=0;')
    h=(root/'a_native_turn_runtime.h').read_text(encoding='utf-8')
    for a,b in (
        ('planning_input_interlock::Controller controller_;','planning_input_interlock::Controller controllers_[3];'),
        ('planning_input_interlock::Controller secondController_;',''),
        ('Period periods_[2]','Period periods_[3]'),
        ('a_save_local_binding::Sampler sampler_,nextSampler_;','a_save_local_binding::Sampler samplers_[3];'),
        ('a_save_local_binding::Config sources_[2]','a_save_local_binding::Config sources_[3]')):
        h=replace(h,a,b)
    out['a_native_turn_runtime.h']=h
    s=(root/'a_native_turn_runtime.cpp').read_text(encoding='utf-8')
    start=s.index('bool Runtime::RequestNext(');end=s.index('void Runtime::RepeatSnapshot(',start)
    s=s[:start]+request+s[end:]
    pairs=(
        ('return InterlockedCompareExchange(&s.sourceIndex_,0,0)?s.nextSampler_.Capture(out):s.sampler_.Capture(out);',
         'const auto index=InterlockedCompareExchange(&s.sourceIndex_,0,0);return index>=0&&index<3&&s.samplers_[index].Capture(out);'),
        ('sampler_.Initialize(c.source)','samplers_[0].Initialize(c.source)'),
        ('sampler_.Capture(pending)','samplers_[0].Capture(pending)'),
        ('&controller_,&mailbox_','&controllers_[0],&mailbox_'),
        ('checkpoint_fresh_save::Artifact*previous=nullptr;',
         'checkpoint_fresh_save::Artifact*previous=nullptr;const auto index=InterlockedCompareExchange(&activePeriod_,0,0);'),
        ('r_.mailbox.count!=1||r_.mailbox.records[0].state!=a_save_dispatch_mailbox::State::Delivered||r_.mailbox.records[0].message.request.generation!=1',
         'index<0||index>=2||r_.mailbox.count!=unsigned(index+1)||r_.mailbox.records[index].state!=a_save_dispatch_mailbox::State::Delivered||r_.mailbox.records[index].message.request.generation!=std::uint64_t(index+1)'),
        ('owner_->CopyArtifact(1,*previous)','owner_->CopyArtifact(std::uint64_t(index+1),*previous)'),
        ('controller_.Snapshot(observed)','controllers_[index].Snapshot(observed)'),
        ('identity(periods_[0])||!controller_.BeginObservation','identity(periods_[index])||!controllers_[index].BeginObservation'),
        ('(unsigned(c_.year)*12+c_.month)*32+c_.day,nextDate=(unsigned(periods_[1].year)*12+periods_[1].month)*32+periods_[1].day',
         '(unsigned(periods_[index].year)*12+periods_[index].month)*32+periods_[index].day,nextDate=(unsigned(periods_[index+1].year)*12+periods_[index+1].month)*32+periods_[index+1].day'),
        ('identity(periods_[1])','identity(periods_[index+1])'),
        ('next.binding=periods_[1].binding;next.sample=planningSample;next.context=&periods_[1];',
         'next.binding=periods_[index+1].binding;next.sample=planningSample;next.context=&periods_[index+1];'),
        ('pc.binding=periods_[1].binding','pc.binding=periods_[index+1].binding'),
        ('secondController_.Initialize(pc)','controllers_[index+1].Initialize(pc)'),
        ('host_.BindPeriod(secondController_)','host_.BindPeriod(controllers_[index+1])'),
        ('InterlockedExchange(&activePeriod_,1);repeat_.activeGeneration=2;',
         'InterlockedExchange(&activePeriod_,index+1);repeat_.activeGeneration=std::uint64_t(index+2);repeat_.requested=0;'),
        ('const bool observed=controller_.EndObservation(repeatRevision_);',
         'const auto index=InterlockedCompareExchange(&activePeriod_,0,0);const bool observed=controllers_[index].EndObservation(repeatRevision_);'),
        ('Retire(*owner_,*gate_,controller_,periods_[0].binding,retired_)',
         'Retire(*owner_,*gate_,controllers_[index],periods_[index].binding,retired_)'),
        ('repeat_.retiredCount=1','++repeat_.retiredCount'),
        ('controller_.EndObservation(repeatRevision_);repeatFail',
         'controllers_[InterlockedCompareExchange(&activePeriod_,0,0)].EndObservation(repeatRevision_);repeatFail'),
        ('if(returnedSource_)return true;',
         'if(returnedSource_)return true;const auto next=InterlockedCompareExchange(&activePeriod_,0,0)+1;if(next<1||next>=3)return repeatFail(RepeatError::Rebind);'),
        ('sources_[1]=candidate;if(!nextSampler_.Initialize(candidate))',
         'sources_[next]=candidate;if(!samplers_[next].Initialize(candidate))'),
        ('InterlockedExchange(&sourceIndex_,1);','InterlockedExchange(&sourceIndex_,next);'))
    for a,b in pairs:s=replace(s,a,b)
    out['a_native_turn_runtime.cpp']=s
    s=(root/'a_native_turn_owner.cpp').read_text(encoding='utf-8')
    for a,b in (
        ('a_save_early_guard::Guard guard,nextGuard;', 'a_save_early_guard::Guard guard,nextGuards[2];'),
        ('bool nextGuardUsed=false;', 'unsigned nextGuardCount=0;'),
        ('!call.input||rp::state.nextGuardUsed', '!call.input||rp::state.nextGuardCount>=2||call.serial!=rp::state.nextGuardCount+1'),
        ('rp::state.nextGuardUsed=true;', 'auto&nextGuard=rp::state.nextGuards[rp::state.nextGuardCount++];'),
        ('rp::state.nextGuard.Initialize(guard)||rp::state.nextGuard.Observe(l.input)', 'nextGuard.Initialize(guard)||nextGuard.Observe(l.input)'),
        ('rp::state.currentGuard=&rp::state.nextGuard;', 'rp::state.currentGuard=&nextGuard;')):
        s=replace(s,a,b)
    out['a_native_turn_owner.cpp']=s
    h=(root/'a_save_runtime_exports.h').read_text(encoding='utf-8')
    h=replace(h,'Magic=0x31585241','Magic=0x33585241')
    out['a_save_runtime_exports.h']=replace(h,'mailboxStates[2]','mailboxStates[3]')
    s=(root/'a_native_turn_exports.cpp').read_text(encoding='utf-8')
    s=replace(s,'for(unsigned i=0;i<2;++i)v.mailboxStates[i]=unsigned(x.mailbox.records[i].state);',
        'for(unsigned i=0;i<3;++i)v.mailboxStates[i]=unsigned(x.mailbox.records[i].state);')
    # Test host access is absent in the production build and cannot be exported
    # or called by a production launcher.
    s+='''\n#ifdef A_SAVE_THREE_EXPORTS_FIXTURE
extern "C" void ASaveThreeFixtureBind(a_save_local_runtime::Runtime*r,uintptr_t base)noexcept {
 runtime=r;prepared.base=base;memset(prepared.nonce,0x37,32);
}
#endif
'''
    out['a_native_turn_exports.cpp']=s
    s=(root/'a_save_runtime_exports_test.cpp').read_text(encoding='utf-8')
    at=' w::Prepare p{};header(p,w::Op::Prepare);'
    s=replace(s,at,''' w::Snapshot oldSnapshot{};header(oldSnapshot,w::Op::Snapshot);oldSnapshot.header.magic=0x31585241;
 need(fn[4](&oldSnapshot)==unsigned(w::Result::BadEnvelope),"old magic explicitly rejected");
 header(oldSnapshot,w::Op::Snapshot);oldSnapshot.header.size-=4;
 need(fn[4](&oldSnapshot)==unsigned(w::Result::BadEnvelope),"old two-slot Snapshot size rejected");
 w::Prepare p{};header(p,w::Op::Prepare);''')
    out['a_save_runtime_exports_test.cpp']=s
    return out
