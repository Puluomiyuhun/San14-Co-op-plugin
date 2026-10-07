"""Compile/run six-entry ABI probes in our own EXE; never opens the game."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
P=Path(__file__).resolve().parent
FILES=('checkpoint_persistent_bridge.h','checkpoint_persistent_bridge.cpp','checkpoint_persistent_bridge.asm',
    'checkpoint_persistent_bridge_fixture.cpp','checkpoint_persistent_bridge_fixture.asm',
    'checkpoint_persistent_bridge_build.cmd','checkpoint_persistent_bridge_test.py')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    out=P/'checkpoint_persistent_bridge_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    frozen=json.loads((P/'checkpoint_complete_live_owner_v2_handoff.json').read_text('utf8'))['source_sha256']
    assert all(sha(P/name)==expected for name,expected in frozen.items()),'Frozen single-load sources changed'
    hashes={name:sha(P/name) for name in FILES}
    build=subprocess.run(['cmd','/c',str(P/'checkpoint_persistent_bridge_build.cmd')],cwd=P,capture_output=True,timeout=45)
    (out/'build.stdout').write_bytes(build.stdout);(out/'build.stderr').write_bytes(build.stderr)
    result=dict(schema='san14.persistent-six-bridge-tests.v1',passed=False,game_access=False,source_sha256=hashes,
        build_exit=build.returncode,native_scheduler_fence=False,multiplayer_ready=False,
        old_session_compatible_without_adaptation=False)
    if not build.returncode:
        run=subprocess.run([str(P/'checkpoint_persistent_bridge_fixture.exe')],cwd=P,capture_output=True,timeout=20)
        (out/'run.stdout').write_bytes(run.stdout);(out/'run.stderr').write_bytes(run.stderr)
        result['run_exit']=run.returncode
        if run.stdout:
            fixture=json.loads(run.stdout.decode('utf8').strip().splitlines()[-1]);result['fixture']=fixture
            result['passed']=run.returncode==0 and fixture['result']=='PASS' and fixture['failures']==0 and fixture['physical_slots']==6 and fixture['scenarios']==29
        result['binary_sha256']={name:sha(P/name) for name in ('checkpoint_persistent_bridge_core.obj',
            'checkpoint_persistent_bridge.obj','checkpoint_persistent_bridge_fixture.exe')}
    result['frozen_sources_unchanged']=all(sha(P/name)==expected for name,expected in frozen.items())
    result['sources_unchanged']=all(sha(P/name)==expected for name,expected in hashes.items())
    result['passed']=result['passed'] and result['sources_unchanged'] and result['frozen_sources_unchanged']
    result['limitations']=[
        'Only own-process native functions. No game hooks, file loads, world replacement or room transition.',
        'The two cleanup faults are intentional tests; a real successful receipt must contain zero faults.',
        'Frame.slot is physical 0..5. Old worker observers use logical 0/1 and old TLS symbols; integration requires explicit adaptation.',
        'Four integer register arguments only, normal Win64 RAX/XMM0 result. No float/stack/variadic/aggregate-return signature.',
        'Modules/configs/callback contexts stay resident; all six callbacks having FINALLY does not prove scheduler quiescence.']
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(dict(passed=result['passed'],path=str(out/'result.json'),scenarios=29)))
    if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
