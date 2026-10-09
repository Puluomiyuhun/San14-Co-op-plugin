// Owned environment faults; production sampler/Controller/Claim predicates remain linked.
static std::wstring traceCase;
static bool traceFault=false;
static unsigned traceSamples=0;
static void traceChangeSlot(){void*p=reinterpret_cast<void*>(b+0x12CC4D0);DWORD old=0,ignored=0;
 need(VirtualProtect(p,sizeof(uintptr_t),PAGE_READWRITE,&old)!=FALSE,"owned slot write protection");
 put<uintptr_t>(b+0x12CC4D0,0);need(VirtualProtect(p,sizeof(uintptr_t),old,&ignored)!=FALSE,"owned slot protection restored");
}
static bool traceSample(void*p,uintptr_t u,unsigned actor,ar::Source&out){
 if(traceFault){++traceSamples;if(traceCase==L"sample")return false;}
 if(!RewardData::sample(p,u,actor,out))return false;
 if(traceFault&&traceCase==L"identity")++out.reward.world;
 if(traceFault&&traceCase==L"bind")out.admission.pending.user.size=0;
 if(traceFault&&traceCase==L"inspect")put<uintptr_t>(b+0x19E7310+0x48,b+0x200000);
 return true;
}
static int traceFinish(const a_save_parent_adapter::Report&p){
 const auto&r=ASaveInitializeFirstFailure;
 const LONG expected=traceCase==L"sample"?42:traceCase==L"identity"?43:traceCase==L"bind"?45:traceCase==L"inspect"?46:17;
 printf("TRACE stage=%ld expected=%ld parent=%u samples=%u\n",r.stage,expected,unsigned(p.error),traceSamples);fflush(stdout);
 need(!p.hostInitialized&&p.error==a_save_parent_adapter::Error::Initialize,"actual Parent refuses failed Controller init");
 planning_input_interlock::Report c{};interlock.Snapshot(c);
 need(!c.initialized&&c.error==planning_input_interlock::Error::Config,"original Config failure retained");
 need(r.size==sizeof(r)&&r.version==1&&r.stage==expected&&r.thread==GetCurrentThreadId()&&r.controller==uintptr_t(&interlock)&&r.owner==uintptr_t(session)&&r.base==b&&r.root==root&&r.world==world,"first failure exact stage and initialization identity");
 need(traceSamples==(traceCase==L"slot"?0u:1u),"failure short-circuit samples exactly once or not reached");
 auto saved=r;a_save_initialize_trace::Check(false,99);a_save_initialize_trace::Begin(&interlock,session,b,root,world);a_save_initialize_trace::Check(false,98);a_save_initialize_trace::End();
 need(!memcmp(&saved,&r,sizeof r),"first record immutable both outside and later scope");
 FILE*f=nullptr;need(!fopen_s(&f,"trace.bin","wb")&&f,"trace record output");need(fwrite(&r,1,sizeof r,f)==sizeof r&&!fclose(f),"persist trace");
 printf("{\"passed\":true,\"stage\":%ld,\"samples\":%u,\"a\":%llu,\"b\":%llu,\"c\":%llu}\n",r.stage,traceSamples,r.a,r.b,r.c);return 0;
}
