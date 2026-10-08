#undef session
// Only the owned fixture's observer raises. All reports come from real observers.
#include "b_reload_lifecycle_fault_guard.h"
namespace lfg=b_reload_lifecycle_fault_guard;
static lfg::Gate* lifecycleAdvance=nullptr;
static tp::Config lifecycleFaultConfig{};
static unsigned lifecycleFaultRaised=0;
static bool lifecycleFaultTarget(){return (providerCase==L"lf-first-observer"&&!generationIndex)||(providerCase==L"lf-second-observer"&&generationIndex==1);}
static void lifecycleFaultAfterGeneration();
struct LifecycleFaultProvider {hw::Provider inner{};hw::Observe observe=nullptr;void*context=nullptr;};
static hw::PendingReport lifecycleFaultObserve(void*p,const hw::Binding&b,std::uint64_t c,const void*u)noexcept{
 auto&w=*static_cast<LifecycleFaultProvider*>(p);
 if(lifecycleFaultTarget()){++lifecycleFaultRaised;RaiseException(0xE014CF21,0,0,nullptr);}
 return w.observe(w.context,b,c,u);
}
static bool lifecycleFaultBegin(void*p,hw::Observe observe,void*context,const hw::Binding&b,std::uint64_t c,const void*u)noexcept{
 auto&w=*static_cast<LifecycleFaultProvider*>(p);w.observe=observe;w.context=context;return w.inner.begin(w.inner.context,lifecycleFaultObserve,&w,b,c,u);
}
static void lifecycleFaultFinish(void*p)noexcept{auto&w=*static_cast<LifecycleFaultProvider*>(p);w.inner.finish(w.inner.context);}
static bool lifecycleFaultSnapshot(void*p,hw::HardwareReceipt&r)noexcept{auto&w=*static_cast<LifecycleFaultProvider*>(p);return w.inner.snapshot(w.inner.context,r);}
static hw::Provider lifecycleFaultProvider(hw::Context&c){auto*w=new LifecycleFaultProvider;w->inner=hw::MakeProvider(c);return {w,lifecycleFaultBegin,lifecycleFaultFinish,lifecycleFaultSnapshot};}
static void lifecycleFaultVerify(){ad::Report a{};check(admissionBundle->controller.Snapshot(a),"fault input report available");ns::Report n{};currentSession->Snapshot(n);
 check(lifecycleFaultRaised==1&&a.blocked&&a.error!=ad::Error::None,"actual observer SEH blocks authorized input controller");
 check(a.prefetch.error==hw::Error::Observer&&a.prefetch.exception_code==0xE014CF21&&a.prefetch.entered&&a.prefetch.captured==1&&a.prefetch.finished&&a.prefetch.restored&&!a.prefetch.restore_uncertain,"actual child VEH catches SEH and restores borrowed hardware registers");
 check(!a.active&&!a.route_active&&a.route_started==a.route_finished&&!a.menu_bound&&!a.commit_succeeded&&!a.queue_returned&&!n.menuBound&&!n.casPublished,"fault cannot publish queue or loading request and actual callbacks drained");
 check(!provider.CloseCompletedWindow(generationIndex+2),"failed actual generation cannot close as completed");
}
