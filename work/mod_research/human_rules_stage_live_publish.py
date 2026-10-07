"""Bound installation/restoration pilot; retains any unresolved debugger owner."""
from datetime import datetime
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P=Path(__file__).resolve().parent
sys.path[:0]=[str(P),str(P/'python_deps'),str(P.parents[1]/'outputs/san14-link')]
RUN=P/'human_rules_stage_live_runs/20261007-222556-471691'
EXE=P/'human_rules_bound_publish_runs/20261007-222930-902937/inputs/publisher-production.exe'
EXE_SHA='b4247b9d804fd08a9b88c9eefab7a0f35310ec97b1a9ca8b0b5fe7398b618095'
CLOSEOUT_SHA='28b6aa86969cd11ef71509397d60d753b4b6de445174de580382e87267e5de6a'


def read(path):return json.loads(path.read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    import os
    with path.open('x',encoding='utf8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['install','restore'])
    parser.add_argument('--native-cycle',action='store_true',
                        help='Separate completed-pilot successor for user-driven native forwarding')
    args=parser.parse_args()
    assert sha(EXE)==EXE_SHA and sha(RUN/'preparation-closeout.json')==CLOSEOUT_SHA
    prepared=read(RUN/'result.json');d=prepared['descriptor']
    records=RUN
    if args.native_cycle:
        # This is a distinct, journaled successor after proven restoration,
        # never reuse/delete a prior action or reinterpret an uncertain attempt.
        previous=read(RUN/'restore-closeout.json')
        assert previous['result']=='PASS_REAL_GAME_RESTORED' and previous['debugger_present'] is False
        assert previous['source_patches_present'] is False and previous['known_data_equal'] is True
        records=RUN/'native-forwarding'
        records.mkdir(exist_ok=True)
    from human_rules_stage_live_start import read_descriptor,DLL_SHA,report,same_known_data
    from checkpoint_push_start import process_birth
    from checkpoint_complete_live_capture import known_snapshot
    from run_autonomous_pilot import ProcessAPI
    from battle_observer import BattleObserver
    assert sha(Path(prepared['dll']))==DLL_SHA
    intent=records/(args.operation+'-intent.json')
    assert not intent.exists(),'Action already claimed; inspect outcome, never repeat uncertain publication'
    reader=BattleObserver();api=None
    try:
        assert (reader.pid,process_birth(reader),reader.memory.base)==(d['pid'],d['birth'],d['base'])
        api=ProcessAPI(reader)
        assert read_descriptor(reader,d['address'])==d
        slot=reader.pointer(reader.memory.base+0x12cc4d0)
        before=known_snapshot(reader,expected_user_hook=slot)
        save(records/(args.operation+'-before.json'),before)
        desired_patched=args.operation=='restore'
        for site in d['sites']:
            expected=bytes.fromhex(site['expected'])
            if desired_patched:
                expected=bytes.fromhex(site['replacement'])+expected[site['patch_size']:]
            assert reader.memory.read(site['address'],site['profile_size'])==expected
        command=[str(EXE),args.operation,str(d['pid']),str(d['birth']),str(d['base']),
                 str(d['address']),prepared['dll'],d['nonce']]
        save(intent,dict(command=command,publisher_sha256=EXE_SHA,created=datetime.now().astimezone().isoformat(),
                         automatic_retry_allowed=False,terminate_controller_allowed=False))
        stdout=records/(args.operation+'-publisher.stdout.txt');stderr=records/(args.operation+'-publisher.stderr.txt')
        with stdout.open('xb') as out,stderr.open('xb') as err:
            child=subprocess.Popen(command,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
            save(records/(args.operation+'-controller.json'),dict(pid=child.pid,command=command))
            try:code=child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                # Popen.wait does not terminate on timeout. Preserve the actual
                # debugger process and its event ownership, and stop here.
                pending=dict(result='CONTROLLER_STILL_RUNNING_REQUIRES_INSPECTION',controller_pid=child.pid,
                             stdout=str(stdout),stderr=str(stderr),target_must_not_be_resumed_blindly=True)
                save(records/(args.operation+'-pending.json'),pending)
                print(json.dumps(pending));return 2
        output=stdout.read_text(encoding='utf8');lines=output.strip().splitlines()
        outcome=json.loads(lines[-1]) if lines else {}
        save(records/(args.operation+'-publisher.json'),dict(exit=code,report=outcome,stdout=output))
        expected_status='INSTALLED_PASSTHROUGH' if args.operation=='install' else 'RESTORED'
        assert code==0 and outcome['status']==expected_status and outcome['detached'] and not outcome['uncertain'],outcome
        # Independent post-detach attachment also refuses a remaining debugger.
        api.close();api=ProcessAPI(reader)
        assert read_descriptor(reader,d['address'])==d
        counters=report(api,prepared['exports']['HumanRulesStageReadReport'])
        for site in d['sites']:
            expected=bytes.fromhex(site['expected'])
            if args.operation=='install':
                expected=bytes.fromhex(site['replacement'])+expected[site['patch_size']:]
            assert reader.memory.read(site['address'],site['profile_size'])==expected
        after=known_snapshot(reader,expected_user_hook=slot)
        save(records/(args.operation+'-after.json'),after)
        result=dict(result='PASS_REAL_GAME_'+expected_status,publisher=outcome,counters=counters,
                    known_data_equal=same_known_data(before,after),debugger_present=False,
                    source_patches_present=args.operation=='install',policy_enabled=False,
                    game_orders=0,full_world_verified=False,two_player_ready=False)
        save(records/(args.operation+'-closeout.json'),result)
        print(json.dumps(result));return 0
    finally:
        if api:api.close()
        reader.close()


if __name__=='__main__':raise SystemExit(main())
