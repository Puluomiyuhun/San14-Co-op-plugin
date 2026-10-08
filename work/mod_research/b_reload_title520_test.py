"""Owned-process successor: actual Load Finalize -> Title520, with Title590.

No game access. Native initializer/start/thread runner execute on CPU; thread
construction, game payloads and scheduler parent sources remain explicit doubles.
"""
from pathlib import Path
import importlib.util

P = Path(__file__).resolve().parent


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, P / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


previous = load_module('title590_predecessor', 'b_reload_title590_test.py')
once = previous.once


def fixture_sources():
    cpp, asm, machine, ports = previous.fixture_sources()
    cpp = '#include "b_reload_finalize_source.h"\n#include "b_reload_title520_profile.h"\nstatic b_reload_finalize_source::Owner finalizeSource;\nstatic b_reload_title520_router::Router title520Router;\nstatic b_reload_title520_publish::Publisher* title520Publisher=nullptr;\nstatic b_reload_finalize_ports::Adapter* finalizePorts=nullptr;\n' + cpp
    cpp = cpp.replace('sharedImage+0x12DB000),0x2200000-0x12DB000', 'sharedImage+0x12DC000),0x2200000-0x12DC000')
    cpp = cpp.replace('sharedImage+0x12DB000),reinterpret_cast<void*>(layout.config.base+0x12DB000),0x2200000-0x12DB000', 'sharedImage+0x12DC000),reinterpret_cast<void*>(layout.config.base+0x12DC000),0x2200000-0x12DC000')
    anchor = 'check(title590Router.Initialize(base),"one retained automatic Title590 runner bridge");'
    cpp = once(cpp, anchor, anchor + '\ncheck(title520Router.Initialize(base),"Title520 uses independent retained worker bridge bank");')
    anchor = 'check(title590Router.Register(provider,generationIndex+2),"immutable Title590 router generation");'
    cpp = once(cpp, anchor, anchor + r'''
    check(title520Router.Register(provider,generationIndex+2),"immutable Title520 registration");
    title520Publisher=new b_reload_title520_publish::Publisher;
    check(title520Publisher->Initialize({base,generationIndex+2,&provider,&title520Router,true}),"Title520 fixed publication before construction");
    finalizePorts=new b_reload_finalize_ports::Adapter;
    check(finalizePorts->Initialize({base,generationIndex+2,&provider,title520Publisher,1000}),"Finalize actual scope configured");
    if(!generationIndex) {
        check(finalizeSource.Initialize({base,finalizePorts}),"retained native Load Finalize source configured");
        const auto slot=base+0x12DBD68+0x10;
        if(providerCase==L"finalize-stop-before-publish")finalizeSource.Stop();
        if(providerCase==L"finalize-code-drift") {DWORD old=0;VirtualProtect(reinterpret_cast<void*>(base+0x497110),8,PAGE_READWRITE,&old);*reinterpret_cast<BYTE*>(base+0x497110)^=1;VirtualProtect(reinterpret_cast<void*>(base+0x497110),8,PAGE_EXECUTE_READ,&old);}
        if(providerCase==L"finalize-slot-drift") {DWORD old=0;VirtualProtect(reinterpret_cast<void*>(slot),8,PAGE_READWRITE,&old);put<uintptr_t>(slot,base+0x497111);VirtualProtect(reinterpret_cast<void*>(slot),8,PAGE_READONLY,&old);}
        const bool refusal=providerCase==L"finalize-stop-before-publish"||providerCase==L"finalize-code-drift"||providerCase==L"finalize-slot-drift";
        check(finalizeSource.Publish()!=refusal,"Finalize source admits only supported original state");
        if(refusal){b_reload_finalize_source::Report refused{};check(finalizeSource.Snapshot(refused)&&!refused.published&&!refused.hooks.entries[0].dirty,"refusal leaves source untouched");printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"finalize_refused\":true}\n",providerCase.c_str(),failures?"false":"true",failures);fflush(stdout);ExitProcess(failures?1:0);}
    }
    check(finalizeSource.Verify(),"same retained Finalize source verified each generation");
''')
    anchor = '    prepareNativeMachine();'
    cpp = once(cpp, anchor, anchor + r'''
    if(!generationIndex)put<uintptr_t>(base+0x12DBD68+0x10,base+0x497110);
    {DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(base+0x12DB000),4096,PAGE_READONLY,&old),"Load Finalize vtable source RO");}
    auto panel=alloc(4096);auto panelVtable=alloc(4096);put<uintptr_t>(panel,panelVtable);put<uintptr_t>(panelVtable+0xC0,uintptr_t(&nativeNullDouble));put<uintptr_t>(title+0x4B8,panel);
''')
    cpp = once(cpp, 'static DWORD WINAPI titleStartOnOtherParent(void*){startEmbedded(1);return 0;}', r'''
static DWORD WINAPI titleStartOnOtherParent(void*){
    __try {using Finalize=void(*)(uintptr_t);reinterpret_cast<Finalize>(at<uintptr_t>(at<uintptr_t>(load)+0x10))(load);}
    __except(GetExceptionCode()==0xE014CC94?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return 1;}
    return 0;
}''')
    start = '    auto starter=CreateThread(nullptr,0,titleStartOnOtherParent,nullptr,0,nullptr);check(starter&&WaitForSingleObject(starter,10000)==WAIT_OBJECT_0,"Title520 start parent differs from native join parent");CloseHandle(starter);check(WaitForSingleObject(embeddedPorts[1]->handle,10000)==WAIT_OBJECT_0,"Title520 finished before second start");'
    cpp = once(cpp, start, '    check(WaitForSingleObject(embeddedPorts[1]->handle,10000)==WAIT_OBJECT_0,"automatically started Title520 finishes before Title Update");')
    cpp = once(cpp, '    callbackPort();', r'''
    auto starter=CreateThread(nullptr,0,titleStartOnOtherParent,nullptr,0,nullptr);check(starter&&WaitForSingleObject(starter,10000)==WAIT_OBJECT_0,"native Finalize invoked on separate parent thread");CloseHandle(starter);
    if(embeddedPorts[1])check(WaitForSingleObject(embeddedPorts[1]->handle,10000)==WAIT_OBJECT_0,"native Title520 worker completed before checks");
    b_reload_finalize_ports::Report finalReport{};b_reload_title520_publish::Report start520{};b_reload_title520_router::Report worker520{};
    check(finalizePorts->Snapshot(finalReport)&&title520Publisher->Snapshot(start520)&&title520Router.Snapshot(generationIndex+2,worker520),"Finalize and worker520 reports");
    check(finalReport.scopeCount==1&&finalReport.completedScopes==1&&!finalReport.active&&finalReport.callback==1,"one native Finalize scope captures real callback");
    const auto&fq=finalReport.scopes[0];check(fq.armed&&fq.finally&&fq.restored&&!fq.uncertain&&!memcmp(fq.originalDr,fq.restoredDr,sizeof fq.originalDr),"Finalize scope restores all debug registers");
    check(finalReport.samples[0].rip==base+0x4CC690&&finalReport.samples[0].gpr[1]==title&&finalReport.samples[0].gpr[2]==load,"native closure thunk supplies actual callback identity");
    if(scenario==L"finalize-native-exception")check(fq.abnormal&&!fq.after&&!finalReport.start520&&!start520.captured&&!worker520.selected,"native Finalize exception forwards and cannot invent worker start");
    else {
        check(finalReport.start520==1&&start520.captured&&start520.samples[0].rip==base+0x834B60&&start520.samples[0].rcx==title+0x520,"native initializer actual Start CONTEXT");
        if(scenario==L"title520-wrong-wait")check(start520.error==checkpoint_task_native_start::Error::WaitStack&&!start520.published&&!worker520.selected&&start520.workerResumed,"wrong520 wait rejects publication and resumes native thread");
        else {check(start520.published&&start520.waitStackVerified&&start520.workerResumed&&worker520.selected&&worker520.armed&&worker520.finally&&worker520.ports.role==1,"automatic520 role with real wait verification");check(worker520.ports.captured==(scenario==L"title520-exception"?2u:4u)&&worker520.ports.finished&&worker520.ports.restored&&!worker520.ports.uncertain,"actual520 sources and hardware restoration");}
    }
    printf("{\"title520_generation\":%u,\"finalize_callback\":%u,\"start\":%u,\"published\":%u,\"automatic_worker\":%u,\"captured\":%u,\"worker_finally\":%u,\"finalize_restored\":%u,\"error\":%u}\n",generationIndex+2,finalReport.callback,finalReport.start520,start520.published,worker520.selected,worker520.ports.captured,worker520.finally,fq.restored,unsigned(start520.error));
    if(scenario==L"finalize-native-exception"||scenario==L"title520-wrong-wait"||scenario==L"title520-exception") {
        if(scenario==L"title520-exception")check(worker520.abnormal&&!worker520.after&&worker520.ports.providerScopeAbandoned,"520 exception abandons exact incomplete task");
        check(!provider.CloseCompletedWindow(generationIndex+2),"Finalize/520 failure cannot close generation");
        if(embeddedPorts[1])joinEmbedded(1);return finishReport(r,true);
    }
''')
    cpp = once(cpp, '    if(self==auxCallable)', '    if(self==titleCallable&&scenario==L"title520-exception")RaiseException(0xE014CC93,0,0,nullptr);\n    if(self==auxCallable)')
    cpp = once(cpp, 'const unsigned expectedTitleCalls=providerCase==L"completion-wait"?5:', 'const unsigned expectedTitleCalls=providerCase==L"title520-exception"||providerCase==L"title520-wrong-wait"||providerCase==L"finalize-native-exception"?2:providerCase==L"completion-wait"?5:')
    anchor = '    rt::Report report{};report=physicalReport().route;'
    cpp = once(cpp, anchor, r'''
    check(finalizeSource.Verify(),"Finalize source retained after both generations");finalizeSource.Stop();check(finalizeSource.Verify(),"published Finalize source stays resident after Stop");
    b_reload_finalize_source::Report finalSourceReport{};check(finalizeSource.Snapshot(finalSourceReport)&&finalSourceReport.published&&finalSourceReport.verified&&finalSourceReport.modulePinned&&finalSourceReport.hooks.count==1&&!finalSourceReport.hooks.entries[0].dirty&&finalSourceReport.hooks.entries[0].lastProtection==PAGE_READONLY,"one Finalize CAS with restored RO protection");
    CheckpointLoadWorkerBridgeStats fs{};check(BReloadTitle520BridgeSnapshot(1,&fs)&&fs.started==2&&fs.finally_calls==2&&!fs.active&&!fs.cleanup_faults,"two real Finalize calls exactly paired");
    check(b_reload_title520_router::Router::Entry()!=b_reload_title590_router::Router::Entry(),"roles have separate pinned bridge banks");
    b_reload_title520_router::Statistics s520{};b_reload_title590_router::Statistics s590{};title520Router.SnapshotStatistics(s520);title590Router.SnapshotStatistics(s590);
    const unsigned want520=providerCase==L"title520-wrong-wait"||providerCase==L"finalize-native-exception"?1:2;
    const unsigned want590=providerCase==L"title520-wrong-wait"||providerCase==L"title520-exception"||providerCase==L"finalize-native-exception"||providerCase==L"title590-wrong-wait"?1:2;
    check(s520.before==want520&&s520.bridge.started==want520&&s520.bridge.finally_calls==want520&&!s520.bridge.active&&!s520.bridge.cleanup_faults&&!s520.unknownForwarded&&!s520.refused,"520 bank contains only its exact immutable role/generations");
    check(s590.before==want590&&s590.bridge.started==want590&&s590.bridge.finally_calls==want590&&!s590.bridge.active&&!s590.bridge.cleanup_faults&&!s590.unknownForwarded&&!s590.refused,"590 bank remains independent and correctly paired");
''' + anchor)
    # The old manual +520 setup and synthetic callback path no longer execute.
    ports = once(ports, 'static void callbackPort(){uintptr_t sp[]={base+0x497134};auto c=capture(base,0x4CC690);c.rcx=title;c.rdx=load;c.rsp=uintptr_t(sp);observe(c);}', '// Finalize callback is exclusively supplied by actual hardware CONTEXT.')
    ports = ports[:ports.index('static void nativeTitleRunner(EmbeddedPort&);')] + ports[ports.index('static void joinEmbedded(unsigned role);'):]
    begin = ports.index('static EmbeddedPort* startEmbedded(unsigned role){')
    ports = ports[:begin] + ports[ports.index('static void joinEmbedded(unsigned role){', begin):]
    begin = machine.index('static void nativeTitleRunner(EmbeddedPort&t){')
    machine = machine[:begin] + machine[machine.index('static void nativeCtorDouble(', begin):]
    machine = once(machine, 'if(t.role==1)return syntheticEmbeddedEntry(p);', '')
    machine = once(machine, 'nativeUnboundExecuting=t.role==2;', 'nativeUnboundExecuting=t.role!=0;')
    machine = once(machine, 'if(t.role==2)return t.abnormal?1:0;', 'if(t.role)return t.abnormal?1:0;')
    machine = once(machine, 'const unsigned role=control==title+0x590?2:0;', 'const unsigned role=control==title+0x520?1:control==title+0x590?2:0;')
    machine = once(machine, 'control==(role?title+0x590:load+0x478)&&payload==base+(role?0x466600:0x508B40)', 'control==(role?title+(role==1?0x520:0x590):load+0x478)&&payload==base+(role==1?0x4DA390:role==2?0x466600:0x508B40)')
    machine = once(machine, 't->callable=role?auxCallable:loadCallable;', 't->callable=role==1?titleCallable:role==2?auxCallable:loadCallable;')
    machine = once(machine, 'if(!role)CloseHandle(t.ready);', 'CloseHandle(t.ready);') if 'if(!role)CloseHandle(t.ready);' in machine else machine
    ports = once(ports, 'if(!role)CloseHandle(t.ready);', 'CloseHandle(t.ready);')
    machine = once(machine, '(scenario==L"title590-wrong-wait"&&t.role==2)', '(scenario==L"title590-wrong-wait"&&t.role==2)||(scenario==L"title520-wrong-wait"&&t.role==1)')
    machine = machine.replace('GetExceptionCode()==0xE014CC92?', 'GetExceptionCode()==0xE014CC92||GetExceptionCode()==0xE014CC93?')
    machine = once(machine, 'static void prepareNativeMachine(){', r'''
static void finalizePrepareDouble(){if(scenario==L"finalize-native-exception")RaiseException(0xE014CC94,0,0,nullptr);}
static void prepareNativeMachine(){
    memcpy(reinterpret_cast<void*>(base+0x497110),b_reload_title520_profile::FinalizeBytes,sizeof b_reload_title520_profile::FinalizeBytes);
    memcpy(reinterpret_cast<void*>(base+0x4FAC30),b_reload_title520_profile::ThunkBytes,sizeof b_reload_title520_profile::ThunkBytes);
    memcpy(reinterpret_cast<void*>(base+0x4CC690),b_reload_title520_profile::CallbackBytes,sizeof b_reload_title520_profile::CallbackBytes);
    memcpy(reinterpret_cast<void*>(base+0x4BEE50),b_reload_title520_profile::StartBytes,sizeof b_reload_title520_profile::StartBytes);
    {const uintptr_t target=uintptr_t(&finalizePrepareDouble);unsigned char j[]={0x48,0xB8,0,0,0,0,0,0,0,0,0xFF,0xE0};memcpy(j+2,&target,8);memcpy(reinterpret_cast<void*>(base+0x4BDD90),j,sizeof j);}
    const unsigned char finalUw[]={1,4,1,0,4,0x42,0,0},callbackUw[]={1,6,2,0,6,0x52,2,0x30},initUw[]={1,10,4,0,10,0x72,6,0x70,5,0x34,10,0};
    memcpy(reinterpret_cast<void*>(base+0x940),finalUw,sizeof finalUw);memcpy(reinterpret_cast<void*>(base+0x960),callbackUw,sizeof callbackUw);memcpy(reinterpret_cast<void*>(base+0x980),initUw,sizeof initUw);
    auto*finalTable=new RUNTIME_FUNCTION[3]{{0x497110,0x49713F,0x940},{0x4BEE50,0x4BEED7,0x980},{0x4CC690,0x4CC7C5,0x960}};check(RtlAddFunctionTable(finalTable,3,base),"archived Finalize/520 chain runtime unwind");
    DWORD fp=0;for(uintptr_t page:{0x497000u,0x4FA000u,0x4CC000u,0x4BD000u})check(VirtualProtect(reinterpret_cast<void*>(base+page),4096,PAGE_EXECUTE_READ,&fp),"Finalize native chain pages RX");
''')
    cpp = cpp.replace('b_reload_title590_fixture_ports.inc', 'b_reload_title520_fixture_ports.inc')
    ports = ports.replace('b_reload_title590_machine.inc', 'b_reload_title520_machine.inc')
    if 'wp::Begin' in machine or 'startEmbedded(' in machine + ports or 'callbackPort(' in cpp + ports:
        raise RuntimeError('Manual Title activation/callback path unexpectedly remains')
    return cpp, asm, machine, ports


def main():
    # Reuse the reviewed runner while creating a separate successor build/log.
    source = (P / 'b_reload_title590_test.py').read_text(encoding='utf-8')
    source = source[source.index('def main():'):source.index("if __name__ == '__main__':")]
    source = source.replace('b_reload_title590_runs', 'b_reload_title520_runs')
    source = source.replace("name == 'b_reload_title590_profile.h'", "name in ('b_reload_title590_profile.h', 'b_reload_title520_profile.h')")
    source = source.replace("'b_reload_title_bridge']", "'b_reload_title_bridge', 'b_reload_title520_bridge']")
    source = source.replace("todo += ['b_reload_title590_test.py'", "todo += ['b_reload_title520_test.py', 'b_reload_title590_test.py'")
    source = source.replace('b_reload_title590_machine.inc', 'b_reload_title520_machine.inc').replace('b_reload_title590_fixture_ports.inc', 'b_reload_title520_fixture_ports.inc')
    anchor = '    cpp, asm, machine, ports = fixture_sources()'
    source = once(source, anchor, '''    image = image_file.read_bytes()
    spans = {'FinalizeBytes': (0x497110, 0x49713F), 'ThunkBytes': (0x4FAC30, 0x4FAC3C), 'CallbackBytes': (0x4CC690, 0x4CC7C5), 'StartBytes': (0x4BEE50, 0x4BEED7)}
    profile = '#pragma once\\nnamespace b_reload_title520_profile {\\n'
    for name, (start, end) in spans.items():
        profile += 'inline constexpr unsigned char '+name+'[]={' + ','.join(hex(v) for v in image[start:end]) + '};\\n'
    (run / 'b_reload_title520_profile.h').write_text(profile+'}\\n')
''' + anchor)
    source = source.replace("schema='san14.b-reload-title590-owned.v1'", "schema='san14.b-reload-title520-finalize-owned.v1'")
    source = source.replace('title520_fixture_manual_begin=True, parent_sources_installed=False, load_finalize_source_installed=False', 'title520_fixture_manual_begin=False, title520_automatic_worker_begin=True, parent_sources_installed=False, load_finalize_source_installed=False, actual_finalize_context=True, owned_finalize_slot_published=True')
    source = source.replace("scope='Archived Title.Update/4BEEE0/834B60/83A930/834D10 execute on CPU with actual native CONTEXT delivery; Title590 runner is automatically published and observes its role. Thread construction, engine/Steam payloads, parent and Title520 sources remain explicit owned doubles.'", "scope='Archived 497110/4FAC30/4CC690/4BEE50 and Title590 chain execute on CPU with actual native CONTEXT. Both Title roles automatically activate in independent banks. Constructor, payloads and scheduler parent sources remain owned doubles; no game installation.'")
    env = previous.__dict__.copy()
    env.update(fixture_sources=fixture_sources, NEW_UNITS=previous.NEW_UNITS + ('b_reload_title520_bridge', 'b_reload_title520_router', 'b_reload_title520_publish', 'b_reload_finalize_ports', 'b_reload_finalize_source'), CASES=('success', 'reuse-full-addresses', 'late-old-root', 'completion-wait', 'title520-exception', 'title520-wrong-wait', 'finalize-native-exception', 'title590-exception', 'title590-wrong-wait', 'finalize-stop-before-publish', 'finalize-slot-drift', 'finalize-code-drift'))
    exec(compile(source, __file__, 'exec'), env)
    env['main']()


if __name__ == '__main__':
    main()
