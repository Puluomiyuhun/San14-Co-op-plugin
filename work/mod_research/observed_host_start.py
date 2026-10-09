"""Explicit A network/native startup. Default/help never accesses the game.

--check validates files/builds only. --execute --no-new-commands captures the
explicit PID, opens this room, then uses the approved observed native entry.
This is the two-snapshot diagnostic, not a full co-op gameplay launcher.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT.parent/'mod_research/python_deps'),str(ROOT/'outputs/san14-link')]
import a_observed_start as native
from observed_room_service import HostService, need
from human_rules_activation_room import rules, GAME_SHA
from authoritative_sync import digest
from b_warm_adapter_key import load_key


NATIVE_PATHS=('build_run','repeat_abi_run','publisher_build','launcher_test_run','entry_test_run')


def read_config(path):
    config=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    validate_config(config)
    return config


def validate_config(c):
    need(type(c) is dict and set(c)=={'schema','manifest','rules','network','native','adapter_key_path'} and
         c['schema']=='san14.a-observed-host.v1','Exact A startup configuration required')
    from a_observed_room import ObservedRoom
    room=ObservedRoom(c['manifest'])
    need(room.manifest['profile']['game_sha256']==GAME_SHA and c['rules']==rules(
        c['rules'].get('native_income_key5'),c['rules'].get('native_world_option8')) and
        room.manifest['profile']['rules_sha256']==digest(c['rules']),'Pinned game/rules compatibility differs')
    need({f:room.catalog.get(f,{}).get('main_district_id') for f in (12,2)}=={12:11,2:2},
         'This diagnostic supports source Zhang Lu and guest Liu Bei only')
    n=c['network'];need(type(n) is dict and set(n)=={'listen_host','advertise_host','control_port',
        'download_port','directory'},'Exact local listener configuration required')
    need(all(type(n[k]) is str and n[k] for k in ('listen_host','advertise_host','directory')) and
         n['advertise_host'] not in ('0.0.0.0','::'),'Explicit listener/advertised host required')
    need(all(type(n[k]) is int and 1<=n[k]<65536 for k in ('control_port','download_port')) and
         n['control_port']!=n['download_port'],'Two fixed ports required')
    d=Path(n['directory']);need(d.is_absolute() and not d.exists() and not d.resolve().is_relative_to(ROOT),
        'New private room directory outside checkout required')
    a=c['native'];need(type(a) is dict and set(a)=={'pid','wait_seconds',*NATIVE_PATHS},
        'Exact explicit native build/PID configuration required')
    need(type(a['pid']) is int and 0<a['pid']<2**32 and type(a['wait_seconds']) is int and
         1<=a['wait_seconds']<=1800,'Explicit PID and bounded wait required')
    need(all(type(a[k]) is str and Path(a[k]).is_absolute() for k in NATIVE_PATHS) and
         type(c['adapter_key_path']) is str and Path(c['adapter_key_path']).is_absolute(),
         'Explicit absolute build/key paths required')
    return c


def check(c):
    validate_config(c)
    args=SimpleNamespace(**{**c['native'],**{k:Path(c['native'][k]) for k in NATIVE_PATHS}})
    native.verify_entry_tests(args.entry_test_run)
    native.verify_launcher_tests(args.launcher_test_run)
    build,abi,publisher=native.verify_native_build(args)
    for name in ('a_save_local_runtime.dll','checkpoint_planning_hold.dll'):
        native.verified_artifact(args.build_run,name,build['production']['binaries'][name])
    native.verified_artifact(args.publisher_build,'publisher.exe',publisher['binaries']['publisher.exe'])
    key=load_key(c['adapter_key_path'])
    return args,key


def run(c, *, no_new_commands):
    need(no_new_commands is True,'Explicit --no-new-commands required')
    args,key=check(c)
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
        a_human_ai_rules_installed=False,automatic_retry=False)
    folder=Path(c['network']['directory'])
    try:
        service=HostService(c['manifest'],node,**c['network'])
        invitation_path=folder/'invitation.json'
        with invitation_path.open('x',encoding='utf-8',newline='\n') as out:
            json.dump(service.invitation,out,ensure_ascii=False,indent=2);out.write('\n')
        print(json.dumps(dict(event='room-listening',invitation_file=str(invitation_path),
            credentials_printed=False,game_mutation_started=False),ensure_ascii=False),flush=True)
        coordinator=service.wait_bound(args.wait_seconds)
        entry=native.RoomEntry(service.room,coordinator,key,no_new_commands=True)
        def event(kind,info):
            if kind=='await-room-turn':service.ready_for_turn()
            # Only the native entry emits running-await-human. Do not invent
            # an advance notification from a network phase or timeout.
        result['native_attempted']=True
        code=native.execute(args,capture_path,captured,entry=entry,on_event=event)
        result['native_entry_exit']=code;result['room_entry']=entry.status()
        service.mark_host_finished()
        if len(coordinator.applied_receipts)==2:
            result['guest_cleanup_report']=service.wait_guest_finished(args.wait_seconds)
            result['guest_disconnect']=service.wait_guest_disconnected(args.wait_seconds)
        guest=result.get('guest_cleanup_report',{})
        result['result']='PASS_TWO_SNAPSHOT_NETWORK_ENTRY' if code==0 and guest.get('native_cleanup_verified') is True else 'INCOMPLETE_RETAIN_EVIDENCE'
    except BaseException as exc:
        result['error']=type(exc).__name__+': '+str(exc)
        if entry is not None:result['room_entry']=entry.status()
    finally:
        if service is not None:result['network_cleanup']=service.close()
        if result.get('network_cleanup',{}).get('network_closed') is not True:
            result['result']='INCOMPLETE_RETAIN_EVIDENCE'
        if folder.is_dir():
            with (folder/'host-result.json').open('x',encoding='utf-8',newline='\n') as out:
                json.dump(result,out,ensure_ascii=False,indent=2);out.write('\n')
    print(json.dumps(dict(result=result['result'],path=str(folder/'host-result.json'),
        native_attempted=result['native_attempted']),ensure_ascii=False))
    return 0 if result['result']=='PASS_TWO_SNAPSHOT_NETWORK_ENTRY' else 1


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
