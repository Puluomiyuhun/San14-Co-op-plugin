"""Three-save native reward-planning successor. Owned fixture seam, no installer.
Frozen reward runtime plus bounded three-cycle retirement/source allocation.
"""
from pathlib import Path
from a_save_three_cycle_sources import sources as cycle_sources, replace

def reward_planning(s):
    s=replace(s,'#include "a_runtime_reward_planning_runtime.h"','#include "a_runtime_reward_three_runtime.h"')
    s=replace(s,'if(reward_.configured&&!rewardSource(1))','if(reward_.configured&&!rewardSource(unsigned(index+1)))')
    s=replace(s,'InterlockedCompareExchange(&activePeriod_,0,0)?secondController_:controller_',
        'controllers_[InterlockedCompareExchange(&activePeriod_,0,0)]',2)
    s=replace(s,'planning_input_interlock::Report c{};controller_.Snapshot(c);',
        'planning_input_interlock::Report c{};controllers_[InterlockedCompareExchange(&activePeriod_,0,0)].Snapshot(c);')
    s=replace(s,'if(index<0||index>=2||!r_.sourcesArmed||repeat_.requested||',
        'if(index<0||index>=2||!reward_.configured||!planning_.opened||planning_.state!=PlanningState::Opened||reward_.state==RewardState::Queued||reward_.state==RewardState::Executing||reward_.state==RewardState::Failed||!r_.sourcesArmed||repeat_.requested||')
    s=replace(s,'repeat_.request=n;repeat_.requested=1;repeat_.state=RepeatState::Queued;',
        'planning_.opened=false;planning_.state=PlanningState::Retired;repeat_.request=n;repeat_.requested=1;repeat_.state=RepeatState::Queued;')
    # Commands require the explicitly opened window of this exact receipt.
    s=replace(s,'if(!reward_.configured||(reward_.state!=RewardState::Idle',
        'if(!planning_.opened||planning_.state!=PlanningState::Opened||!reward_.configured||(reward_.state!=RewardState::Idle')
    s=replace(s,'(mail.count!=unsigned(index)&&!(index==0&&planning_.opened&&planning_.state==PlanningState::Opened&&mail.count==1))',
        '(mail.count!=unsigned(index+1)||planning_.request.generation!=std::uint64_t(index+1))')
    a=s.index('bool Runtime::planningReceipt(');b=s.index('bool Runtime::OpenPlanning(',a)
    receipt=s[a:b]
    receipt=replace(receipt,' if(!owner_||q.generation!=1||!rewardBinding(q.binding,periods_[0].binding)||!identity(periods_[0]))return false;',
        ' const auto index=InterlockedCompareExchange(&activePeriod_,0,0);\n if(index<0||index>=2)return false;const auto&p=periods_[index];\n if(!owner_||q.generation!=std::uint64_t(index+1)||!rewardBinding(q.binding,p.binding)||!identity(p))return false;')
    receipt=replace(receipt,'m.count!=1||m.records[0].state!=a_save_dispatch_mailbox::State::Delivered',
        'm.count!=unsigned(index+1)||m.records[index].state!=a_save_dispatch_mailbox::State::Delivered')
    receipt=replace(receipt,'m.records[0].message.request','m.records[index].message.request')
    receipt=replace(receipt,'r.generation!=1','r.generation!=q.generation')
    receipt=replace(receipt,'r.year!=c_.year||r.month!=c_.month||r.day!=c_.day','r.year!=p.year||r.month!=p.month||r.day!=p.day')
    receipt=replace(receipt,'CopyArtifact(1,*a)','CopyArtifact(q.generation,*a)')
    receipt=replace(receipt,'s.generation==1','s.generation==q.generation')
    s=s[:a]+receipt+s[b:]
    s=replace(s,'if(planning_.state!=PlanningState::Closed||!reward_.configured',
        'const auto index=InterlockedCompareExchange(&activePeriod_,0,0);\n  if(index<0||index>=2||planning_.opened||((index==0&&planning_.state!=PlanningState::Closed)||(index>0&&(planning_.state!=PlanningState::Retired||planning_.request.generation!=std::uint64_t(index))))||!reward_.configured')
    s=replace(s,'||InterlockedCompareExchange(&activePeriod_,0,0)||repeat_.requested||',
        '||repeat_.requested||repeat_.retiredCount!=std::uint64_t(index)||(repeat_.state!=RepeatState::Idle&&repeat_.state!=RepeatState::ReadySecond)||')
    s=replace(s,'planning_.request=q;planning_.state=PlanningState::Queued;',
        'planning_={};planning_.request=q;planning_.state=PlanningState::Queued;')
    return s


def sources(root):
    root=Path(root)
    out=cycle_sources(root)
    # Reuse the already checked three-controller RequestNext and common capacity
    # changes. The runtime below preserves native-turn retirement/return behavior.
    three=out['a_save_repeat_runtime.cpp']
    request=three[three.index('bool Runtime::RequestNext('):three.index('void Runtime::RepeatSnapshot(')]
    request=replace(request,'repeat_.previousArtifactMatched=false;repeat_.nativeDateMatched=false;',
        'repeat_.previousArtifactMatched=false;repeat_.nativeDateMatched=false;returnedSource_=false;runningFrames_=0;')
    h=(root/'a_runtime_reward_planning_runtime.h').read_text(encoding='utf-8')
    for a,b in (
        ('planning_input_interlock::Controller controller_;','planning_input_interlock::Controller controllers_[3];'),
        ('planning_input_interlock::Controller secondController_;',''),
        ('Period periods_[2]','Period periods_[3]'),
        ('a_save_local_binding::Sampler sampler_,nextSampler_;','a_save_local_binding::Sampler samplers_[3];'),
        ('a_save_local_binding::Config sources_[2]','a_save_local_binding::Config sources_[3]')):
        h=replace(h,a,b)
    h=replace(h,'rewardSources_[2]','rewardSources_[3]')
    out['a_runtime_reward_three_runtime.h']=h
    s=(root/'a_runtime_reward_planning_runtime.cpp').read_text(encoding='utf-8')
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
    s=reward_planning(s)
    out['a_runtime_reward_three_runtime.cpp']=s
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
    s=(root/'a_native_turn_mode0_owner.cpp').read_text(encoding='utf-8')
    for a,b in (
        ('a_save_early_guard::Guard guard,nextGuard;', 'a_save_early_guard::Guard guard,nextGuards[2];'),
        ('bool nextGuardUsed=false;', 'unsigned nextGuardCount=0;'),
        ('!call.input||rp::state.nextGuardUsed', '!call.input||rp::state.nextGuardCount>=2||call.serial!=rp::state.nextGuardCount+1'),
        ('rp::state.nextGuardUsed=true;', 'auto&nextGuard=rp::state.nextGuards[rp::state.nextGuardCount++];'),
        ('rp::state.nextGuard.Initialize(guard)||rp::state.nextGuard.Observe(l.input)', 'nextGuard.Initialize(guard)||nextGuard.Observe(l.input)'),
        ('rp::state.currentGuard=&rp::state.nextGuard;', 'rp::state.currentGuard=&nextGuard;')):
        s=replace(s,a,b)
    out['a_native_turn_mode0_owner.cpp']=s
    # Legacy capacity sources above provide the transform contract, but this
    # seam deliberately emits no reward ABI, native export or deployable DLL.
    del out['a_save_repeat_runtime.h'],out['a_save_repeat_runtime.cpp']
    return out
