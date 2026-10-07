from pathlib import Path
p=Path('work/mod_research')
s=(p/'checkpoint_guarded_runtime_fixture.cpp').read_text(encoding='utf-8-sig')
s=s.replace('#include "checkpoint_dynamic_native_session.h"','#include "checkpoint_dynamic_native_session.h"\n#include "checkpoint_native_task_provider.h"')
# All state invocations become source-instrumented owned-native calls; extern declarations stay intact.
idx=s.index('static void invokeWorker')
s=s[:idx]+s[idx:].replace('GuestSessionUserInvoke(', 'routedUser(').replace('GuestSessionMenuInvoke(', 'routedMenu(').replace('GuestSessionGameInvoke(', 'routedGame(').replace('GuestSessionUpdateInvoke(', 'routedLoad(')
s=s.replace('extern "C" std::uint64_t GuestSessionReadBody', '#include "checkpoint_native_task_provider_fixture_ports.inc"\nextern "C" std::uint64_t GuestSessionReadBody')
s=s.replace('if(self==otherCallable){++otherBodies;return;}', 'if(self==otherCallable){++otherBodies;return;}\n    if(self==auxCallable){++auxBodies;return;}')
a=s.index('static DWORD WINAPI loadEntry');b=s.index('extern "C" void GuestSessionUpdateBody',a);s=s[:a]+s[b:]
a=s.index('    if(phase==1){');b=s.index('    else if(phase==3)',a)
s=s[:a]+'''    if(phase==1){bindLoadPort();startEmbedded(0);put<DWORD>(load+0x470,2);}
    else if(phase==2){joinEmbedded(0);++joinCalls;put<DWORD>(load+0x470,3);}
'''+s[b:]
s=s.replace('static bool titleInvokeWithException(){__try{invokeWorker(titleCallable);return false;}__except(GetExceptionCode()==0xE014CC93?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}}', '''static bool titleInvokeWithException(){
    startEmbedded(1);check(WaitForSingleObject(embeddedPorts[1]->handle,10000)==WAIT_OBJECT_0,"Title520 finished before second start");
    startEmbedded(2);put<DWORD>(title+0x470,16);joinEmbedded(1);joinEmbedded(2);return embeddedPorts[1]->abnormal;
}''')
s=s.replace('static volatile LONG loadException=0;static HANDLE loadThread=nullptr;', 'static volatile LONG loadException=0;')
s=s.replace('closure=title+0x800;cache=', 'closure=title+0x800;auxCallable=title+0x900;cache=')
s=s.replace('put<uintptr_t>(title+0x520+0x48,titleCallable);', 'put<uintptr_t>(auxCallable,base+0x138E8C0);put<uintptr_t>(auxCallable+8,base+0x466600);put<uintptr_t>(base+0x138E8D0,uintptr_t(&CheckpointPersistentBridge4));\n    put<uintptr_t>(title+0x520+0x48,titleCallable);')
s=s.replace('    if(planningContext&&self==planningContext->newUser)', '    if(self==lateOriginalSelf){++lateOriginalCalls;return;}\n    if(planningContext&&self==planningContext->newUser)')
s=s.replace('#include "checkpoint_guarded_runtime_planning.inc"', '#include "checkpoint_native_task_provider_fixture_planning.inc"')
s=s.replace('#include "checkpoint_guarded_runtime_admission.inc"', '#include "checkpoint_native_task_provider_fixture_admission.inc"')
s=s.replace('check(physicalOwner.PublishForOfflineExercise(generationIndex+1,logical->RouteGeneration()),"publish only the fully prepared generation after bootstrap");', '''tp::Config pcfg{};pcfg.base=base;pcfg.generation.callbacks=logical->RouteGeneration();pcfg.generation.attempt=layout.config.attempt;pcfg.generation.epoch=17+generationIndex;memcpy(pcfg.generation.attachment,c.request.ownerBinding,32);pcfg.file=fileProfile;pcfg.session=currentSession;pcfg.planning=planningContext->observer;
    check(provider.Register(pcfg)&&provider.OpenWindow(generationIndex+2),"retained native-source bank and observation window");
    check(physicalOwner.PublishForOfflineExercise(generationIndex+1,provider.ProxyGeneration(generationIndex+2)),"physical root always goes through native ticket provider, not current Session");''')
s=s.replace('    DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(load)', '    callbackPort();\n    DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(load)')
s=s.replace('check(workerCalls==3&&loadBodies==1', 'check(workerCalls==4&&auxBodies==1&&loadBodies==1')
s=s.replace('    observePlanningForFixture(identityPass);', '    observePlanningForFixture(identityPass);\n    check(provider.CloseCompletedWindow(generationIndex+2),"all THREE joins and real Session/planning receipts close creation window");\n    tp::Report taskReport{};provider.Snapshot(generationIndex+2,taskReport);check(taskReport.closed&&taskReport.threeJoins&&!taskReport.productionPublication&&!taskReport.schedulerFence,"three task close is not global fence");\n    printf("{\\"provider_generation\\":%llu,\\"creations\\":%llu,\\"closed\\":%u,\\"three_joins\\":%u,\\"error\\":%u}\\n",taskReport.generation,taskReport.creations,taskReport.closed,taskReport.threeJoins,unsigned(taskReport.error));')
s=s.replace('joinCalls=userBodies=menuBodies=gameBodies=planningBodies=0;', 'joinCalls=userBodies=menuBodies=gameBodies=planningBodies=auxBodies=0;')
(p/'checkpoint_native_task_provider_fixture.cpp').write_text(s,encoding='utf-8')
for old,new in [('checkpoint_guarded_runtime_planning.inc','checkpoint_native_task_provider_fixture_planning.inc'),('checkpoint_guarded_runtime_admission.inc','checkpoint_native_task_provider_fixture_admission.inc')]:
 t=(p/old).read_text(encoding='utf-8-sig').replace('GuestSessionUserInvoke(', 'routedUser(')
 (p/new).write_text(t,encoding='utf-8')
s=(p/'checkpoint_guarded_runtime_test.py').read_text(encoding='utf-8-sig')
s=s.replace("'checkpoint_guarded_runtime_fixture'", "'checkpoint_task_attribution_core','checkpoint_task_attribution_adapter','checkpoint_native_task_provider','checkpoint_native_task_provider_fixture'")
s=s.replace('checkpoint_guarded_runtime_', 'checkpoint_native_task_provider_')
s=s.replace("'checkpoint_native_task_provider_admission.inc'", "'checkpoint_native_task_provider_fixture_admission.inc','checkpoint_native_task_provider_fixture_ports.inc'").replace("'checkpoint_native_task_provider_planning.inc'", "'checkpoint_native_task_provider_fixture_planning.inc'")
a=s.index('CASES=');b=s.index('\n',a);s=s[:a]+"CASES=['success','alternate-factions','planning-reuse-load']"+s[b:]
s=s.replace("command(f'cl {FLAGS} /c /Fo\"{run / \"production.obj\"}\" checkpoint_dynamic_runtime_guards.cpp')", "command(f'cl {FLAGS} /c /Fo\"{run / \"production.obj\"}\" checkpoint_native_task_provider.cpp')")
(p/'checkpoint_native_task_provider_test.py').write_text(s,encoding='utf-8')
