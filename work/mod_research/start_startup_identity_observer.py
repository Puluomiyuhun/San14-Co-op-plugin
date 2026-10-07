"""Arm bounded observation of native load/identity/menu ordering. No game calls."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
from run_second_force_reward import BattleObserver, capture, CHECKPOINT
from startup_identity_reader import capture_startup_context
from test_submit_probe import wait_json

ROOT = Path(__file__).resolve().parent
load = lambda p: json.loads(p.read_text(encoding='utf-8'))
save = lambda p, v: p.write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=900)
    parser.add_argument('--idle-check', action='store_true')
    args = parser.parse_args()
    assert 2 <= args.seconds <= 900
    if args.idle_check:
        assert args.seconds <= 5
    tests = load(ROOT/'startup-identity-observer-tests.json')
    assert [r['case'] for r in tests] == ['three-hits', 'timeout', 'cancel'] and all(r['result']=='PASS' for r in tests)
    assert load(ROOT/'startup-identity-payload-validation.json')['result'] == 'PASS'
    audit = load(ROOT/'startup-identity-audit.json')
    reader = BattleObserver()
    try:
        before = capture(reader)
        context = capture_startup_context(reader)
        assert context['snapshot']['state_stack'] == ['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']
        assert context['snapshot']['player']['force_id'] == 12
        assert before == capture(reader) and context == capture_startup_context(reader), 'Current game changed'
        base = reader.memory.base
        for point in audit['observation_points']:
            assert reader.memory.read(base+int(point['rva'],16),32).hex() == point['bytes32'], point['rva']
        for row in audit['anchors']:
            expected = bytes.fromhex(row['bytes'])
            assert reader.memory.read(base+int(row['rva'],16),len(expected)) == expected
        for t in audit['types'].values():
            for offset,target in t['methods'].items():
                assert reader.pointer(base+int(t['vtable_rva'],16)+int(offset,16)) == base+int(target,16)
        assert hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest() == 'afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
        folder=ROOT/'startup-identity-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        folder.mkdir(parents=True)
        save(folder/'before.json', before)
        save(folder/'context-before.json', context)
        log=folder/'trace.jsonl'
        binary=ROOT/'observe_startup_identity.exe'
        with (folder/'stdout.log').open('wb') as out, (folder/'stderr.log').open('wb') as err:
            proc=subprocess.Popen([str(binary),str(reader.pid),hex(base),'0x2ee64c',str(args.seconds),str(log)],
                                  stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        meta={'created':datetime.now().astimezone().isoformat(),'pid':reader.pid,'base':hex(base),
              'observer_pid':proc.pid,'duration_seconds':args.seconds,'directory':str(folder),
              'idle_check':args.idle_check,'trace':str(log),'game_sha256':reader.sha256,
              'observer_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
              'method':'Four adaptive hardware execution breakpoints; observe deserialization return, post-load worker result, optional identity setter, strategy/user initialization and first user update. No game code/data writes or native calls.',
              'stop':'First user update after load, 64 records, timeout or .stop file; observer detaches and game continues. It does NOT pause the game.',
              'limits':'Debugger affects timing. Samples do not prove safe identity insertion, UI correctness or complete world equality.'}
        save(folder/'metadata.json',meta)
        try:
            wait_json(log,'armed')
            if args.idle_check:
                proc.wait(timeout=10)
                rows=[json.loads(line) for line in log.read_text().splitlines()]
                assert proc.returncode == 4 and rows[-1] == {'event':'detached','captured':False,'registers_restored':True}, rows
                assert before == capture(reader) and context == capture_startup_context(reader), 'Idle observation changed sampled game state'
                meta['idle_result']='PASS'
                save(folder/'metadata.json',meta)
                save(ROOT/'startup-identity-idle-check.json',meta)
            else:
                save(ROOT/'startup-identity-active.json',meta)
            print(json.dumps({**meta,'armed':not args.idle_check,'before_player':context['snapshot']['player'],
                              'cached_force':context['cached_player_force_id']},ensure_ascii=True))
        except BaseException:
            if proc.poll() is None:
                Path(str(log)+'.stop').write_text('stop',encoding='ascii')
                proc.wait(timeout=10)
            raise
    finally:
        reader.close()


if __name__=='__main__':
    main()
