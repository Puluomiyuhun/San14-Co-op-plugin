"""Build/run only our own native fixture. Never discovers or opens SAN14."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess

ROOT=Path(__file__).resolve().parent
FILES=['checkpoint_load_worker_bridge.h','checkpoint_load_worker_bridge.cpp',
       'checkpoint_load_worker_bridge.asm','checkpoint_load_worker_bridge_fixture.cpp',
       'checkpoint_load_worker_bridge_fixture.asm','checkpoint_load_worker_bridge_build.cmd',
       'checkpoint_load_worker_bridge_test.py']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=ROOT/'checkpoint_load_worker_bridge_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True,exist_ok=False)
    baseline=json.loads((ROOT/'checkpoint_load_mode_cpp_review_20261006-220631-527695.json').read_text())['source_sha256']
    frozen={p:sha(ROOT/p) for p in ('checkpoint_push_bridge.h','checkpoint_push_bridge.cpp','checkpoint_push_bridge.asm')}
    assert all(frozen[p]==baseline[p] for p in frozen),'frozen bridge has changed since earlier reviewed snapshot'
    sources={p:sha(ROOT/p) for p in FILES}
    build=subprocess.run(['cmd','/c',str(ROOT/'checkpoint_load_worker_bridge_build.cmd')],cwd=ROOT,capture_output=True,timeout=60)
    (out/'build.stdout').write_bytes(build.stdout);(out/'build.stderr').write_bytes(build.stderr)
    result={'schema':'san14.checkpoint-load-worker-bridge-ownprocess.v1',
        'source_sha256':sources,'frozen_source_sha256':frozen,'frozen_sources_unchanged':True,
        'build_exit_code':build.returncode,'build_flags':'MSVC x64 /W4 /WX /EHa /std:c++17 /O2 /MT; MASM normal PE unwind',
        'game_access':False,'real_game_hooks_installed':False,'actual_OS_thread_fixture':True}
    if build.returncode:
        result['result']='BUILD_FAIL'
    else:
        exe=ROOT/'checkpoint_load_worker_bridge_fixture.exe'
        run=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,timeout=20)
        (out/'fixture.stdout').write_bytes(run.stdout);(out/'fixture.stderr').write_bytes(run.stderr)
        final=run.stdout.decode('utf-8').strip().splitlines()[-1]
        report=json.loads(final)
        result.update(fixture=report,fixture_exit_code=run.returncode,
            binary_sha256={p:sha(ROOT/p) for p in ['checkpoint_load_worker_bridge_fixture.exe',
                'checkpoint_load_worker_bridge.obj','checkpoint_load_worker_bridge_core.obj','checkpoint_load_worker_bridge_fixture_asm.obj']})
        result['result']='PASS' if run.returncode==0 and report['result']=='PASS' and report['failures']==0 and report['checks']>=473 else 'FAIL'
    result['limitations']=[
        'Own EXE tests; no native game worker, Steam DLL, actual VT hook installation, file loading or map change.',
        'TLS ownership is per-thread only. Transaction matching and exclusive target ownership must be supplied by the future adapter.',
        'Native and AFTER exceptions preserve original exception and run FINALLY; original is not called if BEFORE throws.',
        'The two cleanup_faults are deliberately injected SEH cases and must never be accepted by a real successful receipt.',
        'Cleanup observer is required not to throw. Intentional SEH violations are tested as contained; a C++ cleanup observer violation is not separately tested.',
        'Stats are individually sampled; zero active is not an unload proof. This module stays pinned.',
        'Only four INTEGER register arguments and RAX/XMM0 results are supported; no stack/floating arguments, variadic calls or aggregate-return convention.',
        'No exception swallowing around BEFORE, original or AFTER; no fail-closed native load behavior is provided.']
    result['sources_unchanged_during_build_and_run']=sources=={p:sha(ROOT/p) for p in FILES}
    result['frozen_sources_unchanged']=frozen=={p:sha(ROOT/p) for p in frozen}
    if not result['sources_unchanged_during_build_and_run'] or not result['frozen_sources_unchanged']:result['result']='SOURCE_DRIFT'
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':result['result'],'path':str(out/'result.json'),'fixture':result.get('fixture'),'game_access':False}))
    raise SystemExit(0 if result['result']=='PASS' else 1)


if __name__=='__main__':main()
