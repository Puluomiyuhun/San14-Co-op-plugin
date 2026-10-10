// Owned native bodies and memory layout; actual Runtime, Owner, source,
// Controller, parent, Save driver and retirement paths are compiled unchanged.
static void rewardJump(uintptr_t address,uintptr_t target){unsigned char code[12]={0x48,0xb8};memcpy(code+2,&target,8);code[10]=0xff;code[11]=0xe0;DWORD old=0,unused=0;need(VirtualProtect(reinterpret_cast<void*>(address),12,PAGE_EXECUTE_READWRITE,&old),"owned reward stub memory");memcpy(reinterpret_cast<void*>(address),code,12);need(VirtualProtect(reinterpret_cast<void*>(address),12,PAGE_EXECUTE_READ,&unused)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(address),12),"owned reward stub publish");}
static int runtimeThreeCase(a_save_local_runtime::Runtime&runtime,RewardData&data,const std::wstring&which){
 using namespace a_save_local_runtime;
 put<uintptr_t>(b+0x1FCA0A0,RewardData::addr(data.raw.data()));
 rewardJump(b+0x22600,uintptr_t(&RewardData::ctor));rewardJump(b+0x171B0,uintptr_t(&RewardData::append));rewardJump(b+0x83E0,uintptr_t(&RewardData::dtor));rewardJump(b+0x1D4270,uintptr_t(&RewardData::predicate));rewardJump(b+0x1D6DA0,uintptr_t(&RewardData::reward));rewardJump(b+0x1D1940,uintptr_t(&RewardData::sortie));rewardJump(b+0x3A2920,uintptr_t(&RewardData::mouse));
 RewardConfig c{};c.binding=data.binding;for(unsigned i=0;i<2;++i)c.actors[i]={data.forceIds[i],data.rulerIds[i],data.districtIds[i]};need(runtime.ConfigureReward(c),"configure once before bootstrap");
 auto&box=runtime.FixtureMailbox();auto&host=runtime.FixtureHost();unsigned char bindingHash[32]={1};unsigned sequence=0,windows=0;
 PlanningRequest prior{};auto priorBinding=data.binding;auto priorCommand=data.command(2,1);Next priorNext{};
 for(unsigned generation=1;generation<=3;++generation){
  bindingHash[0]=static_cast<unsigned char>(generation);
  ip::Config transport{};need(runtime.ConfigureTransport(transport),"actual save permit ready");auto save=request(generation);save.cut=sequence;save.year=get<unsigned short>(world+0x34);save.month=get<unsigned char>(world+0x36);save.day=get<unsigned char>(world+0x37);
  need(transport.permit(transport.permitContext,save,bindingHash)&&box.Enqueue(save,bindingHash),"current receipt cut saves through actual transport permit");
  ownedParentWork=[&]{need(scopedGame()==0&&scopedUser()==0,"real observation Game/User");};parentDispatch();dh::Report h{};host.Snapshot(h);need(h.state==dh::State::Submitted,"actual Controller checkpoint submit");
  ownedParentWork=[&]{need(scopedDispatch(0,user)==0,"actual save bind");queuedGame();pendingUser();completeOwnedSave();};parentDispatch();ownedParentWork={};host.Snapshot(h);need(h.state==dh::State::Complete&&h.copies==generation&&h.releases==generation&&!h.lease,"save copied and released");
  fs::Artifact artifact{};need(box.Copy(generation,artifact)&&artifact.report.status==fs::Status::Complete&&artifact.report.file_bytes_verified&&artifact.request.cut==sequence,"actual Delivered file and cumulative reward cut");
  PlanningRequest opening{};opening.binding=data.binding;opening.generation=generation;memcpy(opening.artifactSha256,artifact.sha256,32);
  if(generation==3){need(!runtime.OpenPlanning(opening),"bounded two planning windows refuse third");break;}
  auto command=data.command(2,sequence+1);need(!runtime.SubmitReward(data.binding,sequence+1,command),"delivered save does not auto-open planning");
  auto wrong=opening;wrong.artifactSha256[0]^=1;need(!runtime.OpenPlanning(wrong),"foreign saved SHA rejected");wrong=opening;++wrong.binding.period;need(!runtime.OpenPlanning(wrong),"foreign native period rejected");
  if(generation==2){need(!runtime.OpenPlanning(prior),"retired first receipt cannot reopen");need(!runtime.RequestNext(priorNext),"old next request cannot recur");}
  need(runtime.OpenPlanning(opening)&&!runtime.OpenPlanning(opening),"single queued current planning request");PlanningReport p{};runtime.PlanningSnapshot(p);need(p.state==PlanningState::Queued&&!p.opened,"request awaits parent boundary");
  if(which==L"second-stop"&&generation==2){runtime.Stop();parentDispatch();runtime.PlanningSnapshot(p);need(p.state==PlanningState::Failed&&!p.opened&&p.stopped&&data.bodies==2,"second queued window Stop fails closed");break;}
  ownedParentWork=[&]{need(scopedGame()==0&&scopedUser()==0,"opened planning preserves bounded fence");};parentDispatch();runtime.PlanningSnapshot(p);need(p.state==PlanningState::Opened&&p.opened&&p.receiptMatched,"current delivered receipt opens at actual parent");++windows;
  if(generation==2){auto stale=command;stale.day=11;need(!runtime.SubmitReward(data.binding,sequence+1,stale),"old date reward rejected in second window");need(!runtime.SubmitReward(priorBinding,sequence+1,command),"old binding reward rejected");need(!runtime.SubmitReward(data.binding,sequence,command),"old reward sequence rejected");need(!runtime.SubmitReward(priorBinding,1,priorCommand),"old complete request rejected");}
  for(unsigned actor:{2u,12u}){
   command=data.command(actor,sequence+1);need(runtime.SubmitReward(data.binding,sequence+1,command),"current actor reward admitted");
   Next busy{};need(!runtime.RequestNext(busy)&&!runtime.OpenPlanning(opening),"queued reward cannot retire or reopen");
   ownedParentWork=[&]{scopedGame();scopedUser();};parentDispatch();RewardReport reward{};runtime.RewardSnapshot(reward);++sequence;
   need(reward.state==RewardState::Complete&&reward.readyResealed&&reward.owner.completed==sequence&&data.bodies==sequence&&data.ctors==sequence&&data.dtors==sequence,"actual reward body cleanup and reseal in current window");
  }
  need(!runtime.OpenPlanning(opening),"unretired current window cannot reopen");
  Next next{};next.previousGeneration=generation;memcpy(next.previousSha256,artifact.sha256,32);next.generation=generation+1;next.period=data.binding.period+1;next.epoch=data.binding.epoch+1;next.inputDigest[0]=static_cast<unsigned char>(0x70+generation);next.year=203;next.month=static_cast<unsigned char>(generation==1?8:9);next.day=static_cast<unsigned char>(generation==1?21:1);
  auto staleNext=next;staleNext.day=save.day;need(!runtime.RequestNext(staleNext),"stale next date refuses before retiring window");runtime.PlanningSnapshot(p);need(p.opened,"bad request preserves existing window");
  need(runtime.RequestNext(next)&&!runtime.RequestNext(next),"one current transition accepted");runtime.PlanningSnapshot(p);need(p.state==PlanningState::Retired&&!p.opened,"transition closes reward admission");need(!runtime.SubmitReward(data.binding,sequence+1,data.command(2,sequence+1))&&!runtime.OpenPlanning(opening),"retired receipt cannot reopen before completed transition");
  ownedParentWork=[&]{need(scopedGame()==0&&scopedUser()==0,"post reward retirement observation");};parentDispatch();RepeatReport repeat{};runtime.RepeatSnapshot(repeat);need(repeat.state==RepeatState::RetiredWaitingDate&&repeat.retiredCount==generation&&a_native_turn::Running(),"real period retirement");
  const auto manager=b+0x19E7310,stack=get<uintptr_t>(manager+0x20);oldTurnUser=user;
  ownedParentWork=[&]{put<unsigned>(user+0x470,5);scopedUser();scopedGame();put<std::uint64_t>(manager+0x10,3);put<unsigned char>(world+0x36,next.month);put<unsigned char>(world+0x37,next.day);++turnSteps;};parentDispatch();
  need(!runtime.OpenPlanning(opening),"date change without rebuilt planning is insufficient");
  ownedParentWork=[&]{const auto oldStrategy=get<uintptr_t>(stack+24),newStrategy=b+0x442000+generation*0x10000,newUser=b+0x440000+generation*0x10000;memcpy(reinterpret_cast<void*>(newStrategy),reinterpret_cast<void*>(oldStrategy),0x1000);memcpy(reinterpret_cast<void*>(newUser),reinterpret_cast<void*>(user),0x1000);memset(reinterpret_cast<void*>(oldStrategy),0,0x1000);memset(reinterpret_cast<void*>(user),0,0x1000);user=newUser;put<unsigned>(user+0x470,2);put<uintptr_t>(stack+24,newStrategy);put<uintptr_t>(stack+32,user);put<std::uint64_t>(manager+0x10,5);};parentDispatch();
  ownedParentWork={};parentDispatch();runtime.RepeatSnapshot(repeat);need(repeat.state==RepeatState::ReadySecond&&repeat.activeGeneration==generation+1&&!repeat.requested&&!repeat.drainPending&&!a_native_turn::Running()&&user!=oldTurnUser,"rebuilt current User rebinds and leaves no automatic window");
  prior=opening;priorBinding=data.binding;priorCommand=command;priorNext=next;data.binding.period=next.period;data.binding.epoch=next.epoch;memcpy(data.binding.room_input_digest.data(),next.inputDigest,32);
 }
 if(which==L"normal"){need(windows==2&&sequence==4&&data.bodies==4,"two windows and both actors complete");need(get<unsigned char>(RewardData::addr(data.persons[1].data())+0x120)==88&&get<unsigned char>(RewardData::addr(data.persons[4].data())+0x120)==78,"both loyalties reflect two real reward bodies");}
 runtime.Stop();need(!failed,"all inherited native business assertions");
 printf("{\"passed\":true,\"case\":\"%ls\",\"planning_windows\":%u,\"reward_bodies\":%u,\"reward_sequence\":%u,\"actual_runtime\":true,\"actual_parent\":true,\"actual_save_driver\":true,\"native_business_double\":true,\"game_access\":false}\n",which.c_str(),windows,data.bodies,sequence);return 0;
}
