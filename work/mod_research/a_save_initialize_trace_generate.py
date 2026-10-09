"""Exact bounded instrumentation; frozen inputs stay unchanged."""
from pathlib import Path
P=Path(__file__).resolve().parent
def once(s,a,b):
    if s.count(a)!=1:raise ValueError('trace anchor changed: '+a)
    return s.replace(a,b,1)
def instrument():
    s=(P/'planning_checkpoint_save_interlock.cpp').read_text()
    start=s.index('bool Controller::read(');end=s.index('bool Controller::clean(',start)
    read=s[start:end]
    read=once(read,'if(!c_.owner||!c_.gate||!c_.gate->MatchesOwner(c_.owner,c_.binding.native,c_.base,c_.root,c_.world))return false;', 'if(!it::Check(c_.owner&&c_.gate&&c_.gate->MatchesOwner(c_.owner,c_.binding.native,c_.base,c_.root,c_.world),10))return false;')
    read=once(read,'if(!planning_period_owner::CurrentController(*c_.owner,c_.binding,this,!r_.initialized))return false;', 'if(!it::Check(planning_period_owner::CurrentController(*c_.owner,c_.binding,this,!r_.initialized),11))return false;')
    read=once(read,'))return false;}\n __except(EXCEPTION_EXECUTE_HANDLER){return false;}', ')){it::Check(false,12);return false;}}\n __except(EXCEPTION_EXECUTE_HANDLER){it::Exception(13,GetExceptionCode());return false;}')
    read=once(read,'if(!ar::Snapshot(*c_.owner,x.reward))return false;', 'if(!it::Check(ar::Snapshot(*c_.owner,x.reward),14))return false;')
    read=once(read,'if(!h->initialized||h->count!=2||h->exceptionCode)return false;', 'if(!it::Check(h->initialized&&h->count==2&&!h->exceptionCode,15,h==&x.owner.hooks?0:1,h->count,h->exceptionCode))return false;')
    read=once(read,'if(!e.known||!e.published||e.error||!e.binding.slot||!e.binding.hook||*e.binding.slot!=e.binding.hook)return false;', 'if(!it::Check(e.known&&e.published&&!e.error&&e.binding.slot&&e.binding.hook,16,h==&x.owner.hooks?0:1,i,e.error))return false;const auto actual=*e.binding.slot;if(!it::Check(actual==e.binding.hook,17,reinterpret_cast<uintptr_t>(e.binding.slot),reinterpret_cast<uintptr_t>(actual),reinterpret_cast<uintptr_t>(e.binding.hook)))return false;')
    read=once(read,'__except(EXCEPTION_EXECUTE_HANDLER){return false;}return true;', '__except(EXCEPTION_EXECUTE_HANDLER){it::Exception(18,GetExceptionCode());return false;}return true;')
    s=s[:start]+read+s[end:]
    start=s.index('bool Controller::Initialize(');end=s.index('bool Controller::Request(',start)
    init=s[start:end]
    init=once(init,'bool ok=false;', 'bool ok=false;bool traceEntered=false;')
    init=once(init,' __try {if(', ' __try {it::Begin(this,c.owner,c.base,c.root,c.world);traceEntered=true;if(')
    init=once(init,'if(r_.initialized||c_.owner||!c.owner||!c.gate||!c.base||!c.root||!c.world)__leave;', 'if(!it::Check(!r_.initialized&&!c_.owner&&c.owner&&c.gate&&c.base&&c.root&&c.world,1))__leave;')
    init=once(init,'!read(r_)||!clean(r_)||!planning_period_owner::ClaimController(*c.owner,c.binding,this)', '!read(r_)||!it::Check(clean(r_),2)||!it::Check(planning_period_owner::ClaimController(*c.owner,c.binding,this),3)')
    init=once(init,'{r_.error=Error::Identity;__leave;}', '{it::Exception(4,GetExceptionCode());r_.error=Error::Identity;__leave;}')
    init=once(init,'__finally {ReleaseSRWLockExclusive', '__finally {if(traceEntered)it::End();ReleaseSRWLockExclusive')
    s=s[:start]+init+s[end:]
    s='#include "a_save_initialize_trace.h"\nnamespace it=a_save_initialize_trace;\n'+s
    life=(P/'planning_checkpoint_save_lifecycle.inc').read_text()
    start=life.index('bool fresh(');end=life.index('\n}\nbool CurrentController',start)
    fresh=life[start:end]
    fresh=once(fresh,'if(!c.sample||!readDate(now)||!c.sample(c.context,s.user,now.viewer,source))return false;', 'if(!it::Check(c.sample!=nullptr,40)||!it::Check(readDate(now),41)||!it::Check(c.sample(c.context,s.user,now.viewer,source),42,s.user,now.viewer))return false;')
    a=fresh.index(' if(!ar::binding');b=fresh.index('\n#ifndef',a)
    condition=fresh[a:b];fresh=fresh[:a]+condition.replace('return false;', '{it::Check(false,43);return false;}')+fresh[b:]
    fresh=once(fresh,'if(uintptr_t(source.admission.reward)!=s.base+0x1D6DA0)return false;', 'if(!it::Check(uintptr_t(source.admission.reward)==s.base+0x1D6DA0,44,uintptr_t(source.admission.reward),s.base+0x1D6DA0))return false;')
    fresh=once(fresh,'checkpoint_native_input_pending::Adapter a;if(a.Bind(source.admission.pending)!=checkpoint_native_input_pending::Error::None)return false;', 'checkpoint_native_input_pending::Adapter a;const auto bindError=a.Bind(source.admission.pending);if(!it::Check(bindError==checkpoint_native_input_pending::Error::None,45,unsigned(bindError)))return false;')
    fresh=once(fresh,'return r.error==checkpoint_native_input_pending::Error::None&&\n r.decision==checkpoint_native_input_pending::Decision::QuiescentObserved&&r.stack_count==5&&r.user_phase==2;', 'return it::Inspect(r.error==checkpoint_native_input_pending::Error::None&&\n r.decision==checkpoint_native_input_pending::Decision::QuiescentObserved&&r.stack_count==5&&r.user_phase==2,r);')
    fresh=once(fresh,'__except(EXCEPTION_EXECUTE_HANDLER){return false;}', '__except(EXCEPTION_EXECUTE_HANDLER){it::Exception(47,GetExceptionCode());return false;}')
    life=life[:start]+fresh+life[end:]
    start=life.index('bool ClaimController(');end=life.index('bool Retire(',start)
    claim=life[start:end]
    claim=once(claim,'if(&o!=s.owner||!s.lock||!controller)return false;', 'if(!it::Check(&o==s.owner&&s.lock&&controller,30))return false;')
    claim=once(claim,'if(!quiet()||s.periodRetired||!ar::binding(b,s.config.binding)||!readDate(now)||!fresh(s.config)||periods.controller)__leave;', 'if(!it::Check(quiet(),31)||!it::Check(!s.periodRetired,32)||!it::Check(ar::binding(b,s.config.binding),33)||!it::Check(readDate(now),34)||!fresh(s.config)||!it::Check(!periods.controller,35,reinterpret_cast<uintptr_t>(periods.controller)))__leave;')
    claim=once(claim,'if(periods.tracked&&(GetCurrentThreadId()!=periods.thread||!sameDate(now,periods.date)))__leave;', 'if(!it::Check(!(periods.tracked&&(GetCurrentThreadId()!=periods.thread||!sameDate(now,periods.date))),36,periods.thread,GetCurrentThreadId()))__leave;')
    life=life[:start]+claim+life[end:]
    owner=once((P/'a_save_abort_pending_owner.cpp').read_text(),'#include "planning_checkpoint_save_lifecycle.inc"','#include "a_save_initialize_trace_lifecycle.inc"')
    owner='#include "a_save_initialize_trace.h"\nnamespace it=a_save_initialize_trace;\n'+owner
    return {'a_save_initialize_trace_controller.cpp':s,'a_save_initialize_trace_lifecycle.inc':life,'a_save_initialize_trace_owner.cpp':owner}
if __name__=='__main__':
    for n,s in instrument().items():(P/n).write_text(s.rstrip()+'\n',encoding='utf-8')
