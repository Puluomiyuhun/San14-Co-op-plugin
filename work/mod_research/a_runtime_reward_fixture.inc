// Production Runtime and source sampler; only archived native business bodies
// are owned-function doubles at their exact configured RVAs.
static void rewardJump(uintptr_t address,uintptr_t target){unsigned char code[12]={0x48,0xb8};memcpy(code+2,&target,8);code[10]=0xff;code[11]=0xe0;DWORD old=0,unused=0;need(VirtualProtect(reinterpret_cast<void*>(address),12,PAGE_EXECUTE_READWRITE,&old),"owned reward stub memory");memcpy(reinterpret_cast<void*>(address),code,12);need(VirtualProtect(reinterpret_cast<void*>(address),12,PAGE_EXECUTE_READ,&unused)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(address),12),"owned reward stub publish");}
static int runtimeRewardCase(a_save_local_runtime::Runtime&runtime,RewardData&data,const std::wstring&which,const wchar_t*){
 using namespace a_save_local_runtime;
 put<uintptr_t>(b+0x1FCA0A0,RewardData::addr(data.raw.data()));
 rewardJump(b+0x22600,uintptr_t(&RewardData::ctor));rewardJump(b+0x171B0,uintptr_t(&RewardData::append));rewardJump(b+0x83E0,uintptr_t(&RewardData::dtor));rewardJump(b+0x1D4270,uintptr_t(&RewardData::predicate));rewardJump(b+0x1D6DA0,uintptr_t(&RewardData::reward));rewardJump(b+0x1D1940,uintptr_t(&RewardData::sortie));rewardJump(b+0x3A2920,uintptr_t(&RewardData::mouse));
 RewardConfig c{};c.binding=data.binding;for(unsigned i=0;i<2;++i)c.actors[i]={data.forceIds[i],data.rulerIds[i],data.districtIds[i]};need(runtime.ConfigureReward(c)&&!runtime.ConfigureReward(c),"one immutable production reward configuration");
 auto command=data.command(2,1);auto wrong=command;wrong.ruler=666;need(!runtime.SubmitReward(data.binding,1,wrong),"command cannot supply actor authority");auto binding=data.binding;++binding.epoch;need(!runtime.SubmitReward(binding,1,command),"foreign binding refused");need(!runtime.SubmitReward(data.binding,2,command),"future sequence refused");
 need(runtime.SubmitReward(data.binding,1,command),"typed command queued on retained Runtime");RewardReport q{};runtime.RewardSnapshot(q);need(q.state==RewardState::Queued&&!q.owner.submitted&&!q.owner.completed,"remote queue does not fake Owner submission");Report snapshot{};runtime.Snapshot(snapshot);need(!snapshot.readyForControlledRequest,"pending reward excludes new Save permit");
 if(which==L"stop-queued"){runtime.Stop();parentDispatch();runtime.RewardSnapshot(q);need(q.state==RewardState::Failed&&q.error==RewardError::Stopped&&!q.owner.submitted&&!data.bodies,"Stop before parent invokes no reward");}
 else{
  if(which==L"native-failure")mode="exception";
  ownedParentWork=[&]{scopedGame();scopedUser();};parentDispatch();runtime.RewardSnapshot(q);
  if(which==L"native-failure"){need(q.state==RewardState::Failed&&!q.readyResealed&&q.uncertain&&data.bodies==1,"native fault stays terminal without Ready receipt");need(!runtime.SubmitReward(data.binding,1,command),"fault cannot replay");}
  else{
   fprintf(stderr,"reward state %u error %u owner %u replay %u submitted %llu completed %llu finally %llu bodies %u\n",unsigned(q.state),unsigned(q.error),unsigned(q.owner.error),unsigned(q.owner.reward.error),q.owner.submitted,q.owner.completed,q.owner.finally,data.bodies);
   need(q.state==RewardState::Complete&&q.readyResealed&&q.owner.completed==1&&q.owner.reward.native_returned&&q.owner.reward.args_released&&q.owner.reward.owned_slot_cleared,"actual User reward and cleanup then Controller reseal");
   command=data.command(12,2);need(runtime.SubmitReward(data.binding,2,command),"second actor same Runtime");parentDispatch();runtime.RewardSnapshot(q);need(q.state==RewardState::Complete&&q.owner.completed==2&&data.bodies==2&&data.ctors==2&&data.dtors==2,"same physical owner completes both actors");
   need(!runtime.SubmitReward(data.binding,2,command),"completed sequence cannot replay");runtime.Snapshot(snapshot);need(snapshot.readyForControlledRequest&&snapshot.reward.completed==2,"save ready only after reseal and correct reward cut");ip::Config transport{};need(runtime.ConfigureTransport(transport),"transport keeps actual reward-cut permit");auto save=request(1);save.cut=0;unsigned char bindingHash[32]={1};need(!transport.permit(transport.permitContext,save,bindingHash),"stale cut zero rejected");save.cut=2;need(transport.permit(transport.permitContext,save,bindingHash),"actual completed reward cut accepted");runtime.Stop();
  }
 }
 printf("{\"passed\":true,\"case\":\"%ls\",\"submitted\":%llu,\"completed\":%llu,\"reward_bodies\":%u,\"actual_runtime\":true,\"actual_parent\":true,\"actual_controller\":true,\"actual_source\":true,\"actual_owner\":true,\"native_business_double\":true,\"game_access\":false}\n",which.c_str(),q.owner.submitted,q.owner.completed,data.bodies);return 0;
}
