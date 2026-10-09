"""Explicit A protected network/native successor. Default/help is inert.

--check validates files/builds only. --execute --no-new-commands captures the
explicit PID, opens this room, then uses the approved observed native entry.
Installs both save and human-AI protection owners. Still two snapshots and
no new commands; reward/input modules are not silently enabled.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT.parent/'mod_research/python_deps'),str(ROOT/'outputs/san14-link')]
import a_protected_start as native
import observed_host_start as predecessor
from b_warm_rules_factory import RulesBuild
from observed_room_service import HostService, need


NATIVE_PATHS=('build_run','repeat_abi_run','publisher_build','launcher_test_run','entry_test_run')


def read_config(path):
    config=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    validate_config(config)
    return config


def validate_config(c):
    need(type(c) is dict and set(c)=={'schema','manifest','rules','network','native','adapter_key_path','rules_build','network_entry_test_run'} and
         c['schema']=='san14.a-protected-host.v1','Exact protected A startup configuration required')
    base={k:v for k,v in c.items() if k not in ('rules_build','network_entry_test_run')}
    base['schema']='san14.a-observed-host.v1'
    predecessor.validate_config(base)
    need(type(c['network_entry_test_run']) is str and Path(c['network_entry_test_run']).is_absolute(),
         'Absolute protected network entry test result directory required')
    build=c['rules_build']
    need(type(build) is dict and set(build)=={'stage','publisher'} and
         all(type(v) is str and Path(v).is_absolute() for v in build.values()),
         'Explicit absolute approved AI rules build paths required')
    return c


def verify_network_tests(folder):
    result=json.loads((Path(folder)/'result.json').read_text(encoding='utf-8'))
    need(result.get('schema')=='san14.protected-host-tests.v1' and result.get('result')=='PASS' and
         result.get('sources_unchanged') is True and result.get('actual_TLS') is True and
         result.get('game_access') is False,'Passing protected network entry tests required')
    pins=result['sources']
    need(str(Path(__file__).resolve()) in pins,'Protected CLI not covered by test sources')
    for name,expected in pins.items():
        need(hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected,'Tested source changed: '+name)


def check(c):
    validate_config(c)
    verify_network_tests(c['network_entry_test_run'])
    base={k:v for k,v in c.items() if k not in ('rules_build','network_entry_test_run')}
    base['schema']='san14.a-observed-host.v1'
    args,key=predecessor.check(base)
    native.verify_entry_tests(args.entry_test_run)
    build=RulesBuild(Path(c['rules_build']['stage']),Path(c['rules_build']['publisher']))
    build.check()
    return args,key,build


def run(c, *, no_new_commands):
    need(no_new_commands is True,'Explicit --no-new-commands required')
    args,key,rules_build=check(c)
    capture_path,captured=native.capture(args.pid)
    from checkpoint_complete_live_capture import SOURCE,SOURCE_SHA
    need(hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA==c['manifest']['profile']['checkpoint_sha256'],
         'Room starting checkpoint differs from approved actual slot34')
    snapshot=captured['planning']['context']['snapshot']
    node={k:snapshot['date'][k] for k in ('year','month','day')};node['phase']='PLANNING_BOUNDARY'
    need(node==dict(year=203,month=8,day=11,phase='PLANNING_BOUNDARY') and
         snapshot['player']['force_id']==12 and snapshot['player']['ruler_id']==666,
         'Only confirmed slot34 Zhang Lu planning start supported')
    service=None;entry=None;result=dict(result='INCOMPLETE',native_attempted=False,
        two_real_clients_proven=False,target_file_restoration_claimed=False,
        a_human_ai_rules_installed=False,a_human_ai_rules_restored=False,automatic_retry=False,
        reward_flow_enabled=False,complete_input_fence_proven=False)
    folder=Path(c['network']['directory'])
    try:
        service=HostService(c['manifest'],node,**c['network'])
        invitation_path=folder/'invitation.json'
        with invitation_path.open('x',encoding='utf-8',newline='\n') as out:
            json.dump(service.invitation,out,ensure_ascii=False,indent=2);out.write('\n')
        print(json.dumps(dict(event='room-listening',invitation_file=str(invitation_path),
            credentials_printed=False,game_mutation_started=False),ensure_ascii=False),flush=True)
        coordinator=service.wait_bound(args.wait_seconds)
        entry=native.ProtectedRoomEntry(service.room,coordinator,key,no_new_commands=True)
        def event(kind,info):
            if kind=='await-room-turn':service.ready_for_turn()
            # Only the native entry emits running-await-human. Do not invent
            # an advance notification from a network phase or timeout.
        result['native_attempted']=True
        code=native.execute(args,capture_path,captured,entry=entry,on_event=event,
            rules_build=rules_build,settings=c['rules'])
        result['native_entry_exit']=code;result['room_entry']=entry.status()
        # The native entry owns verification; a configured rule set alone is
        # never evidence that installation or cleanup succeeded.
        protection=result['room_entry'].get('protection',{})
        result['a_human_ai_rules_installed']=protection.get('installed_once') is True
        result['a_human_ai_rules_restored']=protection.get('restore_verified') is True
        service.mark_host_finished()
        if len(coordinator.applied_receipts)==2:
            result['guest_cleanup_report']=service.wait_guest_finished(args.wait_seconds)
            result['guest_disconnect']=service.wait_guest_disconnected(args.wait_seconds)
        guest=result.get('guest_cleanup_report',{})
        result['result']='PASS_PROTECTED_TWO_SNAPSHOT_NETWORK_ENTRY' if code==0 and result['a_human_ai_rules_installed'] and result['a_human_ai_rules_restored'] and protection.get('retained_or_unknown') is False and guest.get('native_cleanup_verified') is True else 'INCOMPLETE_RETAIN_EVIDENCE'
    except BaseException as exc:
        result['error']=type(exc).__name__+': '+str(exc)
        if entry is not None:
            result['room_entry']=entry.status()
            protection=result['room_entry'].get('protection',{})
            result['a_human_ai_rules_installed']=protection.get('installed_once') is True
            result['a_human_ai_rules_restored']=protection.get('restore_verified') is True
    finally:
        if service is not None:result['network_cleanup']=service.close()
        if result.get('network_cleanup',{}).get('network_closed') is not True:
            result['result']='INCOMPLETE_RETAIN_EVIDENCE'
        if folder.is_dir():
            with (folder/'host-result.json').open('x',encoding='utf-8',newline='\n') as out:
                json.dump(result,out,ensure_ascii=False,indent=2);out.write('\n')
    print(json.dumps(dict(result=result['result'],path=str(folder/'host-result.json'),
        native_attempted=result['native_attempted']),ensure_ascii=False))
    return 0 if result['result']=='PASS_PROTECTED_TWO_SNAPSHOT_NETWORK_ENTRY' else 1


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group();mode.add_argument('--check',action='store_true');mode.add_argument('--execute',action='store_true')
    p.add_argument('--config',type=Path);p.add_argument('--no-new-commands',action='store_true')
    args=p.parse_args(argv)
    if not args.check and not args.execute:p.print_help();return 0
    if args.config is None:p.error('--config required')
    if args.execute and not args.no_new_commands:p.error('--execute requires --no-new-commands')
    c=read_config(args.config)
    if args.check:
        check(c);print(json.dumps(dict(result='PASS_FILES_ONLY',game_access=False,network_opened=False)));return 0
    return run(c,no_new_commands=args.no_new_commands)


if __name__=='__main__':raise SystemExit(main())
