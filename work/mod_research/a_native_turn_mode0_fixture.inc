// Owned negative environments; no production field or predicate is modified.
static bool modeFault=false;
static int modeRefused(const a_save_parent_adapter::Report&p){
 const auto&r=ASaveInitializeFirstFailure;
 need(!p.hostInitialized&&p.error==a_save_parent_adapter::Error::Initialize,"actual Runtime Parent refuses mode");
 need(r.size==sizeof r&&r.version==1&&r.stage==46&&r.thread==GetCurrentThreadId()&&r.controller&&r.owner==uintptr_t(session)&&r.base==b&&r.root==root&&r.world==world,"actual Controller initialization trace identity");
 need(r.input.error==0&&r.input.decision==unsigned(checkpoint_native_input_pending::Decision::StateTransition)&&r.input.stackCount==5&&r.input.queueCount==0&&r.input.userPhase==2,"only strict unsupported planning mode rejects");
 ss::Report owner{};session->Snapshot(owner);need(!owner.save.binds&&!owner.save.queues&&!owner.save.completed_requests,"rejected initialization never saves");
 FILE*f=nullptr;need(!fopen_s(&f,"trace.bin","wb")&&f,"owned trace output");need(fwrite(&r,1,sizeof r,f)==sizeof r&&!fclose(f),"trace output complete");
 printf("{\"passed\":true,\"stage\":46,\"decision\":%u,\"planning_mode\":%u,\"saves\":0}\n",r.input.decision,get<unsigned>(b+0x290000+8));return 0;
}
