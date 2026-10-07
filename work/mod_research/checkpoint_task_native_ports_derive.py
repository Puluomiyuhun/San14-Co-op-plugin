from pathlib import Path
p=Path('work/mod_research')
s=(p/'checkpoint_native_task_provider_fixture.cpp').read_text()
s=s.replace('#include "checkpoint_native_task_provider.h"','#include "checkpoint_native_task_provider.h"\n#include "checkpoint_task_native_ports.h"\n#include "checkpoint_task_native_ports_profile.h"')
s=s.replace('checkpoint_native_task_provider_fixture_ports.inc','checkpoint_task_native_ports_fixture_ports.inc')
s=s.replace('checkpoint_native_task_provider_fixture_planning.inc','checkpoint_task_native_ports_fixture_planning.inc').replace('checkpoint_native_task_provider_fixture_admission.inc','checkpoint_task_native_ports_fixture_admission.inc')
s=s.replace('extern "C" void GuestSessionWorkerBody(', 'extern "C" void TaskFixturePayloadBody(')
s=s.replace('++workerCalls;check(a==', '++workerCalls;if(self!=loadCallable)check(a==')
mark='static bool titleInvokeWithException()'
# Wrapper executes archived Load prologue before entering the explicit synthetic payload.
idx=s.index('static DWORD WINAPI titleStartOnOtherParent')
s=s[:idx]+'''extern "C" void GuestSessionWorkerBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    if(self==loadCallable){using Body=void(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);reinterpret_cast<Body>(base+0x508B40)(self,a,b,c);}
    else TaskFixturePayloadBody(self,a,b,c);
}
'''+s[idx:]
s=s.replace('c.bytes.fixtureWorkerCaller=uintptr_t(&GuestSessionWorkerReturn);', 'c.bytes.fixtureWorkerCaller=base+0x834D9B;')
# identity Title remains synthetic GuestSessionWorkerReturn; runtime guard allows per physical shared caller only.
# All Title/other invoke wrappers still GuestSession*; guard callbackPoint checks only owned role caller? we'll give actual Load override through fixture caller below.
s=s.replace('uintptr_t(&GuestSessionWorkerReturn),uintptr_t(&GuestSessionReadReturn)};', 'base+0x834D9B,uintptr_t(&GuestSessionReadReturn)};')
s=s.replace('    callbackPort();', '''    if(scenario==L"load-exception"){
        session.Snapshot(r);check(r.bytes.workerAbnormal&& !r.bytes.observedWorkerAndBytes&&!r.identity.casAttempts,"real native runner exception propagated through persistent worker bridge");
        check(!provider.CloseCompletedWindow(generationIndex+2),"abnormal real source cannot complete the generation");return finishReport(r,true);
    }
    callbackPort();''')
s=s.replace('    check(logical->Initialize(mapping)', '    prepareNativeMachine();\n    check(logical->Initialize(mapping)')
(p/'checkpoint_task_native_ports_fixture.cpp').write_text(s)
for suffix in ('planning.inc','admission.inc'):
 (p/('checkpoint_task_native_ports_fixture_'+suffix)).write_text((p/('checkpoint_native_task_provider_fixture_'+suffix)).read_text())
s=(p/'checkpoint_native_task_provider_fixture_ports.inc').read_text();a=s.index('static DWORD WINAPI embeddedEntry');b=s.index('static EmbeddedPort* startEmbedded',a)
old=s[a:b];old=old.replace('static DWORD WINAPI embeddedEntry', 'static DWORD WINAPI syntheticEmbeddedEntry')
s=s[:a]+old+'\n#include "checkpoint_task_native_ports_fixture_machine.inc"\n'+s[b:]
s=s.replace('auto&t=*embeddedPorts[role];check(WaitForSingleObject', 'auto&t=*embeddedPorts[role];check(WaitForSingleObject')
s=s.replace('if(!omitJoin[role]){auto c=', 'if(!t.abnormal&&!omitJoin[role]){auto c=')
(p/'checkpoint_task_native_ports_fixture_ports.inc').write_text(s)
s=(p/'checkpoint_native_task_provider_test.py').read_text();s=s.replace("'checkpoint_native_task_provider_fixture'", "'checkpoint_task_native_ports','checkpoint_task_native_ports_fixture'")
s=s.replace('checkpoint_native_task_provider_runs','checkpoint_task_native_ports_runs')
s=s.replace('checkpoint_native_task_provider_fixture_', 'checkpoint_task_native_ports_fixture_').replace('checkpoint_native_task_provider_test.py','checkpoint_task_native_ports_test.py')
s=s.replace("'checkpoint_task_native_ports_fixture_ports.inc'", "'checkpoint_task_native_ports_fixture_ports.inc','checkpoint_task_native_ports_fixture_machine.inc','checkpoint_task_native_ports_profile.h'")
s=s.replace('/DCHECKPOINT_DYNAMIC_RUNTIME_GUARDS_FIXTURE', '/DCHECKPOINT_TASK_NATIVE_PORTS_FIXTURE /DCHECKPOINT_DYNAMIC_RUNTIME_GUARDS_FIXTURE')
a=s.index('CASES=');b=s.index('\n',a);s=s[:a]+"CASES=['success','load-exception','ports-bad-profile','ports-stopped','ports-foreign-seh']"+s[b:]
s=s.replace('checkpoint_native_task_provider.cpp\')', 'checkpoint_task_native_ports.cpp\')')
(p/'checkpoint_task_native_ports_test.py').write_text(s)
