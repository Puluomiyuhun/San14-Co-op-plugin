"""Owned-process parent-source successor; never opens a game process.

Runs the archived whole 509FE0 scheduler. Its pool/root-worker business remains
explicit fixture code; no synthetic parent fresh/create/complete Capture.
"""
from pathlib import Path
import importlib.util
import inspect

P = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('parent_previous', P / 'b_reload_title520_test.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
once = previous.once


def fixture_sources():
    cpp, asm, machine, ports = previous.fixture_sources()
    cpp = '#include "b_reload_parent_source.h"\n#include "b_reload_parent_profile.h"\n' + cpp
    cpp = once(cpp, 'int wmain(int argc,wchar_t**argv){', r'''
static LONG WINAPI parentUnhandled(EXCEPTION_POINTERS*e){printf("UNHANDLED code=%lx rip=%llx rva=%llx access=%llx rsp=%llx\n",e->ExceptionRecord->ExceptionCode,e->ContextRecord->Rip,e->ContextRecord->Rip-base,e->ExceptionRecord->ExceptionInformation[1],e->ContextRecord->Rsp);fflush(stdout);return EXCEPTION_EXECUTE_HANDLER;}
int wmain(int argc,wchar_t**argv){setvbuf(stdout,nullptr,_IONBF,0);SetUnhandledExceptionFilter(parentUnhandled);
''')
    start = cpp.index('        check(VirtualProtect(reinterpret_cast<void*>(sharedImage),0x12DA000')
    end = cpp.index('layout.config.base=sharedImage;', start)
    cpp = cpp[:start] + r'''
        for(uintptr_t page=0;page<0x2200000;page+=4096){
            if(page==0||page==0x13D000||page==0x509000||page==0x50A000||page==0x50B000||page==0x12DA000||page==0x12DB000)continue;
            check(VirtualProtect(reinterpret_cast<void*>(sharedImage+page),4096,PAGE_READWRITE,&prior),"owned reset excludes ALL retained source pages");
            memcpy(reinterpret_cast<void*>(sharedImage+page),reinterpret_cast<void*>(layout.config.base+page),4096);
        }
        ''' + cpp[end:]
    ports = once(ports, 'static StatePort* lateTask=nullptr;', '#include "b_reload_parent_fixture.inc"\nstatic StatePort* lateTask=nullptr;')
    start = ports.index('static DWORD WINAPI parentPort(')
    end = ports.index('static StatePort* prepareState(', start)
    ports = ports[:start] + ports[end:]
    ports = once(ports, 't->worker=alloc(4096);', 't->worker=alloc(4096)+8;')
    ports = once(ports, 'CreateThread(nullptr,0,parentPort,t,0,nullptr)', 'CreateThread(nullptr,0,actualParentPort,t,0,nullptr)')
    # Fixture queue mutation is business setup: it makes this parent stop after
    # the root callback, including when that callback changed the formal stack.
    ports = once(ports, 't.abnormal=true;SetEvent(t.done);', 't.abnormal=true;put<DWORD>(t.worker+0x78,1);put<std::uint64_t>(base+0x19E7310+0x30,1);SetEvent(t.done);')
    ports = once(ports, 'c.rip=t.image+0x834DB4;observe(c);SetEvent(t.done);', 'c.rip=t.image+0x834DB4;observe(c);put<std::uint64_t>(base+0x19E7310+0x30,1);SetEvent(t.done);')
    cpp = once(cpp, '    prepareNativeMachine();', '    prepareNativeMachine();\n    prepareParentMachine();')
    cpp = once(cpp, 'for(const auto&a:CheckpointLiveSessionAnchors)memcpy(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size);', 'for(const auto&a:CheckpointLiveSessionAnchors){const auto page=a.rva&~uintptr_t(4095);if(generationIndex&&(page==0x13D000||page==0x509000||page==0x50A000||page==0x50B000)){check(!memcmp(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size),"retained source page anchor unchanged");continue;}memcpy(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size);}')
    admission = (P / 'checkpoint_task_completion_fixture_admission.inc').read_text(encoding='utf-8-sig')
    admission = once(admission, 'for(const auto& anchor:CheckpointNativeQueueAnchors)memcpy(reinterpret_cast<void*>(base+anchor.rva),anchor.bytes,anchor.size);', 'for(const auto& anchor:CheckpointNativeQueueAnchors){const auto page=anchor.rva&~uintptr_t(4095);if(generationIndex&&(page==0x13D000||page==0x509000||page==0x50A000||page==0x50B000)){check(!memcmp(reinterpret_cast<void*>(base+anchor.rva),anchor.bytes,anchor.size),"retained queue anchor unchanged");continue;}memcpy(reinterpret_cast<void*>(base+anchor.rva),anchor.bytes,anchor.size);}')
    cpp = once(cpp, '#include "checkpoint_task_completion_fixture_admission.inc"', admission)
    # Old Finalize adapter requires manager.current=Load; the real scheduler
    # proves current is zero. Keep the old explicit Finalize fixture boundary,
    # do not count it as a newly solved queue-phase integration.
    cpp = once(cpp, '    __try {using Finalize=void(*)(uintptr_t);', '    put<uintptr_t>(base+0x19E7310+0x48,load); // Existing Finalize fixture boundary, NOT native parent queue.\n    __try {using Finalize=void(*)(uintptr_t);')
    anchor = '    rt::Report report{};report=physicalReport().route;'
    cpp = once(cpp, anchor, r'''
    b_reload_parent_source::Report parentReport{};parentSource.Snapshot(parentReport);
    check(parentReport.error==b_reload_parent_source::Error::None&&parentReport.armed&&!parentReport.active&&!parentReport.uncertain&&parentReport.scopes==parentReport.finally&&parentReport.scopes==parentReport.restored,"all real scheduler parent sources restore and drain");
    check(parentReport.scopes==parentReport.phaseStarted&&parentQueueChecks==parentReport.scopes&&parentReport.accepted[0]==parentReport.scopes&&parentReport.accepted[1]==parentReport.scopes&&parentReport.accepted[3]==parentReport.scopes,"one actual fresh/creation/completion per root callback in both generations");
    check(parentReport.yieldedSkipped>0&&!memcmp(parentReport.originalDr,parentReport.restoredDr,sizeof parentReport.originalDr),"real yielded skip is not completion and all debug registers restore");
    CheckpointLoadWorkerBridgeStats parentStats{};check(BReloadParentBridgeSnapshot(0,&parentStats)&&parentStats.started==parentReport.scopes&&parentStats.finally_calls==parentReport.scopes&&!parentStats.cleanup_faults&&!parentStats.active,"real outer PE bridge native return and FINALLY paired");
    printf("{\"parent_scopes\":%u,\"parent_fresh\":%u,\"parent_create\":%u,\"parent_complete\":%u,\"yield_skip\":%u,\"queue_phase\":%u,\"restored\":%u,\"parent_error\":%u}\n",parentReport.scopes,parentReport.accepted[0],parentReport.accepted[1],parentReport.accepted[3],parentReport.yieldedSkipped,parentQueueChecks,parentReport.restored,unsigned(parentReport.error));
    if(providerCase==L"parent-queue-exception"||providerCase==L"parent-worker-exception")parentExceptionProbe(providerCase==L"parent-queue-exception"?1:2);
''' + anchor)
    # Preserve published source pages on the second synthetic world rebuild.
    machine = once(machine, '){unsigned char j[]={0x48,0xB8,', '){if(generationIndex&&target.first==0x509640)continue;unsigned char j[]={0x48,0xB8,')
    machine = once(machine, 'static BOOL nativeSetEventDouble(HANDLE h){', 'static BOOL nativeSetEventDouble(HANDLE h){parentBeforeWake(h);')
    machine = machine.replace('RtlAddFunctionTable(', 'parentAddFunctions(')
    if '0x50B4B3' in ports or '0x50B598' in ports or '0x50B632' in ports:
        raise RuntimeError('Manual parent source still present')
    return cpp, asm, machine, ports


def main():
    # Reuse the existing private-input verifier/build, retaining every run.
    source = inspect.getsource(previous.main)
    source = source.replace('b_reload_title520_runs', 'b_reload_parent_runs')
    source = source.replace("name in ('b_reload_title590_profile.h', 'b_reload_title520_profile.h')", "name in ('b_reload_title590_profile.h', 'b_reload_title520_profile.h', 'b_reload_parent_profile.h')")
    source = source.replace("'b_reload_title520_bridge']", "'b_reload_title520_bridge', 'b_reload_parent_bridge']")
    source = source.replace("'b_reload_title520_test.py',", "'b_reload_parent_test.py', 'b_reload_parent_fixture.inc', 'b_reload_title520_test.py',")
    source = source.replace("'b_reload_finalize_source'), CASES=", "'b_reload_finalize_source', 'b_reload_parent_bridge', 'b_reload_parent_source'), CASES=")
    source = source.replace("CASES=('success', 'reuse-full-addresses', 'late-old-root', 'completion-wait', 'title520-exception', 'title520-wrong-wait', 'finalize-native-exception', 'title590-exception', 'title590-wrong-wait', 'finalize-stop-before-publish', 'finalize-slot-drift', 'finalize-code-drift')", "CASES=('success', 'reuse-full-addresses', 'completion-wait', 'parent-stop-before-arm', 'parent-code-drift', 'parent-patch-drift', 'parent-queue-exception', 'parent-worker-exception')")
    source = source.replace("'StartBytes': (0x4BEE50, 0x4BEED7)}", "'StartBytes': (0x4BEE50, 0x4BEED7)}")
    anchor = "(run / 'b_reload_title520_profile.h').write_text(profile+'}\\\\n')"
    insert = """
    parent_spans={'SchedulerBytes':(0x509FE0,0x50B690),'OuterCall':(0x13DC09,0x13DC0E),'PhaseCall':(0x50B41B,0x50B420),'WaitBytes':(0x834EF0,0x834EFE)}
    parent_profile='#pragma once\\\\nnamespace b_reload_parent_profile {\\\\n'
    for name,(start,end) in parent_spans.items():
        parent_profile+='inline constexpr unsigned char '+name+'[]={'+','.join(hex(v) for v in image[start:end])+'};\\\\n'
    (run / 'b_reload_parent_profile.h').write_text(parent_profile+'}\\\\n')
"""
    source = once(source, anchor, anchor + insert)
    source = source.replace("    env = previous.__dict__.copy()", "    source=source.replace('/DB_RELOAD_TITLE_SOURCE_FIXTURE', '/DB_RELOAD_TITLE_SOURCE_FIXTURE /DB_RELOAD_PARENT_FIXTURE')\n    env = previous.__dict__.copy()")
    source = source.replace("schema='san14.b-reload-title520-finalize-owned.v1'", "schema='san14.b-reload-parent-owned.v1'")
    source = source.replace('actual_finalize_context=True, owned_finalize_slot_published=True', 'actual_finalize_context=True, owned_finalize_slot_published=True, actual_parent_scheduler_context=True, root_worker_sources_are_doubles=True, finalize_queue_integration=False')
    source = source.replace('Constructor, payloads and scheduler parent sources remain owned doubles; no game installation.', 'Full archived parent scheduler supplies fresh/create/complete CONTEXT. Constructor, root worker entry/return and business remain owned doubles. Finalize still uses its explicit old fixture boundary; no game installation.')
    env = previous.__dict__.copy()
    env.update(fixture_sources=fixture_sources)
    exec(compile(source, __file__, 'exec'), env)
    env['main']()


if __name__ == '__main__':
    main()
