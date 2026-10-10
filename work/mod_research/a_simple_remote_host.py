"""A external-command pilot: actual protected Runtime entry plus retained reward mount.

Default/--help and --config-fields are inert. --check reads approved LOCAL files
only, never discovers a PID or opens a game, Steam save, socket or native owner.
--execute --no-native-commands is explicit: operate only this console during the
planning window; advance the game only at running-await-human. Native menus are
not connected. Finite observations do not constitute an input/scheduler fence.

Config schema san14.a-simple-remote-host.v1 retains protected-host manifest,
rules, network, native, adapter_key_path, rules_build, network_entry_test_run.
native adds reward_build_run and reward_build_sha256. Two further absolute
private key paths: reward_report_key_path and guest_cut_key_path; B must hold
the same respective keys. The existing adapter key is separate. Explicit pid
is the CURRENT locally confirmed process, never copied from another computer.
All build paths refer to approved local results; no memory addresses are input.
"""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import sys
import threading
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT.parent/'mod_research/python_deps'),str(ROOT/'outputs/san14-link')]
import a_reward_runtime_entry as native
import observed_host_start as predecessor
from a_reward_runtime_mount import RuntimeMount,approved_planning_runtime
from b_warm_rules_factory import RulesBuild
from b_warm_adapter_key import load_key,public
from b_warm_received_apply import write_once
from observed_room_service import HostService,need
from simple_remote_console import Console
from reward_room_flow import envelope
import execution_journal as journal

SCHEMA='san14.a-simple-remote-host.v1'
NATIVE_PATHS=predecessor.NATIVE_PATHS
EXTRA={'rules_build','network_entry_test_run','reward_report_key_path','guest_cut_key_path'}
_OUTPUT_LOCK=threading.RLock()


def base_config(c):
    result={k:deepcopy(v) for k,v in c.items() if k not in EXTRA}
    result['schema']='san14.a-observed-host.v1'
    result['native']={k:v for k,v in result['native'].items() if k not in ('reward_build_run','reward_build_sha256')}
    return result


def validate_config(c):
    need(type(c) is dict and set(c)=={'schema','manifest','rules','network','native','adapter_key_path',*EXTRA}
         and c['schema']==SCHEMA,'Exact simple reward host configuration required')
    need(type(c['native']) is dict and set(c['native'])=={'pid','wait_seconds',*NATIVE_PATHS,
         'reward_build_run','reward_build_sha256'},'Explicit original and reward Runtime builds required')
    predecessor.validate_config(base_config(c))
    for key in ('network_entry_test_run','reward_report_key_path','guest_cut_key_path'):
        need(type(c[key]) is str and Path(c[key]).is_absolute(),'Absolute local path required: '+key)
    need(type(c['native']['reward_build_run']) is str and Path(c['native']['reward_build_run']).is_absolute()
         and journal.hex_id(c['native']['reward_build_sha256']),'Exact reward build path/result SHA required')
    r=c['rules_build']
    need(type(r) is dict and set(r)=={'stage','publisher'} and
         all(type(v) is str and Path(v).is_absolute() for v in r.values()),'Explicit rules build required')
    return c


def read_config(path):
    return validate_config(json.loads(Path(path).read_text(encoding='utf-8-sig')))


def verify_network_tests(folder):
    result=json.loads((Path(folder)/'result.json').read_text(encoding='utf-8'))
    need(result.get('schema')=='san14.simple-remote-host-tests.v1' and result.get('result')=='PASS'
         and result.get('sources_unchanged') is True and result.get('actual_TLS') is True
         and result.get('mounted_entry_executed') is True and result.get('full_cli_actual_entry') is True
         and result.get('game_access') is False,
         'Passing actual mounted-entry/TLS launcher tests required')
    pins=result['sources']
    need(str(Path(__file__).resolve()) in pins,'This CLI absent from tested sources')
    for path,expected in pins.items():
        need(hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected,'Tested source changed: '+path)


def check(c):
    validate_config(c);verify_network_tests(c['network_entry_test_run'])
    # Reuse actual checks, not the old check wrapper: it also demands a test
    # record naming the retired a_observed_start entry, which is not executed.
    args=SimpleNamespace(**{**c['native'],**{k:Path(c['native'][k]) for k in NATIVE_PATHS}})
    native.verify_entry_tests(args.entry_test_run)
    native.verify_launcher_tests(args.launcher_test_run)
    args.reward_build_run=Path(c['native']['reward_build_run'])
    args.reward_build_sha256=c['native']['reward_build_sha256']
    baseline,_,publisher=native.verify_native_build(args)
    for name in ('a_save_local_runtime.dll','checkpoint_planning_hold.dll'):
        native.verified_artifact(args.build_run,name,baseline['production']['binaries'][name])
    native.verified_artifact(args.publisher_build,'publisher.exe',publisher['binaries']['publisher.exe'])
    _,reward_build=approved_planning_runtime(args,baseline)
    # Validate the actual selected successor, not only the predecessor DLL.
    import pefile
    pe=pefile.PE(reward_build['production_dll'])
    try:
        names=[s.name for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if not s.forwarder]
        for name in ('ASaveRuntimeRewardConfigure','ASaveRuntimeRewardSubmit','ASaveRuntimeRewardSnapshot',
                     'ASaveRuntimeOpenPlanning','ASaveRuntimePlanningSnapshot'):
            need(names.count(name.encode())==1,'Required real reward export missing: '+name)
    finally:pe.close()
    build=RulesBuild(Path(c['rules_build']['stage']),Path(c['rules_build']['publisher']));build.check()
    adapter=load_key(c['adapter_key_path'])
    reward=load_key(c['reward_report_key_path']);cut=load_key(c['guest_cut_key_path'])
    need(len({adapter,reward,cut})==3,'Adapter, reward report and cut keys must be separate')
    return args,adapter,build,reward,cut


def serialize_control(control):
    """Preserve actual RoomConnection identity; serialize every request on it."""
    need(not hasattr(control,'_simple_remote_request_lock'),'Connection already has a command owner')
    lock=threading.RLock();original=control.request
    def request(packet):
        with lock:return original(packet)
    control.request=request;control._simple_remote_request_lock=lock
    return lock


class Operator:
    """Trusted local external proposal adapter. ACK is queue acceptance only."""
    def __init__(self,mount,*,emit):
        need(type(mount) is RuntimeMount,'Exact retained Runtime mount required')
        self.mount=mount;self.emit=emit;self.console=None;self.closed=False
        self.lock=threading.RLock();self.failure=None;self.rows={}
        self.control=mount.service.control
        need(hasattr(self.control,'_simple_remote_request_lock'),'Shared control serialization required')

    def start(self,stream):
        with self.lock:
            m=self.mount
            need(not self.closed and self.console is None and m.phase=='ACTIVE','Planning console opens once after native OpenPlanning')
            self.graph=(m.service,m.room,m.c,m.flow,m.gate,m.port,m.native,m.entry)
            self.scope=deepcopy(m.flow.scope);self.binding=deepcopy(m.gate.binding)
            self.attachment=m.attachment;self.connection=m.room.players['A']['connection']
            self.records=m.records/'external-proposals';self.records.mkdir(exist_ok=False)
            context=self._current()
            self.console=Console(on_reward=self.reward,on_ready=self.ready,on_failure=self.hold,emit=self.emit)
            candidates=[p['id'] for p in context['persons'] if p['force_id']==12 and p['district_id']==11
                        and p['loyalty']<100 and not(p['flags']&2)]
            self.emit(dict(event='external-reward-planning-open',force_id=12,district_id=11,
                observed_candidate_ids=candidates,eligibility_rechecked_at_execution=True,
                reward_example=dict(action='reward',request_id=secrets.token_hex(16),district_id=11,
                                    officer_ids=candidates[:1]),
                ready_example=dict(action='ready',request_id=secrets.token_hex(16)),
                automatic_ready=False,native_menu_supported=False,input_exclusion_proven=False))
            self.console.start(stream)

    def _current(self):
        m=self.mount
        # This order matches mount polling; release ALL server-side locks before TLS.
        with m.gate.lock,m.room.lock,m.c.lock:
            need(not self.closed and self.failure is None and self.graph==
                 (m.service,m.room,m.c,m.flow,m.gate,m.port,m.native,m.entry)
                 and m.service.control is self.control and m.room.players['A']['connection']==self.connection
                 and self.control.player_id=='A' and m.phase=='ACTIVE' and not m.failure
                 and 'A' not in m.gate.finished,'Current active A planning owner required')
            m.gate._current()
            need(m.gate.binding==self.binding and m.flow.scope==self.scope and
                 bytes(m.prep)==m.prepared_bytes and m.attachment==self.attachment==m.c.attachments['A']==m.port.attachment_id,
                 'Room/native attachment or planning scope changed')
            need(m.native.identity()==m.port.binding,'Native owner identity changed')
            return m.port.context(self.scope['bindings']['A']['force_id'])

    def _request(self,identity,packet):
        need(journal.hex_id(identity,32) and identity not in self.rows,'Request already attempted; no resend')
        write_once(self.records/(identity+'-intent.json'),dict(packet=packet,request_id=identity,attachment=self.attachment))
        self.rows[identity]=dict(state='INTENT',packet=deepcopy(packet))
        reply=self.control.request(packet)
        need(type(reply) is dict and reply.get('ok') is True and reply.get('native_gameplay_enabled') is False,
             'Reward endpoint rejected command or returned invalid authority flags')
        return reply

    def reward(self,identity,district,officers):
        with self.lock:
            try:
                self._current()
                need(type(district) is int and district==self.scope['bindings']['A']['main_district_id'],
                     'Only the bound A main district may submit')
                packet=envelope(self.scope,'reward_submit',request_id=identity,district_id=district,officer_ids=officers)
                reply=self._request(identity,packet)
                need(reply.get('player')=='A' and reply.get('request_id')==identity and type(reply.get('ordinal')) is int
                     and reply['ordinal']>0 and reply.get('status') in ('QUEUED','DISPATCHING','AWAITING_B','PAIRED','REJECTED')
                     and type(reply.get('duplicate')) is bool,'Queue receipt does not match this request')
                return self._ack(identity,reply)
            except BaseException as exc:self.hold(exc);raise

    def ready(self,identity):
        with self.lock:
            try:
                self._current()
                reply=self._request(identity,dict(action='reward_cut_prepare',epoch=self.binding['checkpoint_epoch']))
                finished=reply.get('finished')
                need(type(finished) is list and len(set(finished))==len(finished)
                     and 'A' in finished and set(finished)<={'A','B'},'Input-finished response differs')
                return self._ack(identity,reply)
            except BaseException as exc:self.hold(exc);raise

    def _ack(self,identity,reply):
        write_once(self.records/(identity+'-ack.json'),reply)
        self.rows[identity].update(state='ACKNOWLEDGED',reply=deepcopy(reply))
        return dict(authority_ack=reply,native_execution_verified=False,native_menu_close_authorized=False)

    def hold(self,exc):
        with self.lock:
            self.failure=self.failure or repr(exc)
            m=self.mount
            with m.gate.lock,m.room.lock,m.c.lock:m.hold(exc)

    def close(self):
        # Console callback holds Console.lock then Operator.lock: same order on close.
        # Never acquire gate/room locks while waiting for a pending callback.
        if self.console is not None:self.console.close()
        with self.lock:self.closed=True

    def status(self):
        return dict(started=self.console is not None,closed=self.closed,failure=self.failure,
                    ready_sent=self.console.ready if self.console else False,
                    request_states={k:v['state'] for k,v in self.rows.items()})


def connect_operator(entry,mount,*,stream,emit):
    """Explicit instance hooks preserve exact-type native owner checks."""
    need(type(entry) is native.RoomEntry and entry.mount is mount and mount.entry is None,
         'Fresh exact mounted entry required')
    operator=Operator(mount,emit=emit);original_open=mount.open;original_close=entry.close_observation
    def opened(*args,**kwargs):
        result=original_open(*args,**kwargs)
        operator.start(stream)
        return result
    def closed():
        operator.close()
        return original_close()
    mount.open=opened;entry.close_observation=closed
    return operator


def emit(value):
    with _OUTPUT_LOCK:print(json.dumps(value,ensure_ascii=False),flush=True)


def run(c,*,no_native_commands,stream=None):
    need(no_native_commands is True,'Explicit --no-native-commands required')
    args,key,rules_build,reward_key,cut_key=check(c)
    capture_path,captured=native.capture(args.pid)
    from checkpoint_complete_live_capture import SOURCE,SOURCE_SHA
    need(hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA==c['manifest']['profile']['checkpoint_sha256'],
         'Actual slot34 source differs from approved starting file')
    snapshot=captured['planning']['context']['snapshot']
    node={k:snapshot['date'][k] for k in ('year','month','day')};node['phase']='PLANNING_BOUNDARY'
    need(node==dict(year=203,month=8,day=11,phase='PLANNING_BOUNDARY') and
         snapshot['player']['force_id']==12 and snapshot['player']['ruler_id']==666,
         'Only confirmed slot34 Zhang Lu planning start supported')
    service=entry=mount=operator=None;folder=Path(c['network']['directory'])
    result=dict(result='INCOMPLETE_RETAIN_EVIDENCE',native_attempted=False,automatic_retry=False,
                native_menu_supported=False,input_exclusion_proven=False,two_real_clients_proven=False)
    try:
        service=HostService(c['manifest'],node,**c['network'])
        serialize_control(service.control)
        write_once(folder/'invitation.json',service.invitation)
        emit(dict(event='room-listening',invitation_file=str(folder/'invitation.json'),credentials_printed=False))
        coordinator=service.wait_bound(args.wait_seconds)
        mount=RuntimeMount(service,reward_key=reward_key,guest_cut_key=cut_key,records=folder/'reward',wait_seconds=10)
        entry=native.RoomEntry(service.room,coordinator,key,mount=mount,no_new_commands=True)
        operator=connect_operator(entry,mount,stream=sys.stdin if stream is None else stream,emit=emit)
        def event(kind,info):
            if kind=='running-await-human':
                operator.close()
                emit(dict(event=kind,instruction='现在仅执行一次正常旬推进，处理游戏报告后回到规划界面；不要下达其他命令。'))
        result['native_attempted']=True
        code=native.execute(args,capture_path,captured,entry=entry,on_event=event,rules_build=rules_build,
                            settings=c['rules'],reward_flow=mount,input_fence=False)
        result['native_entry_exit']=code;result['room_entry']=entry.status();result['reward_mount']=mount.status()
        result['operator']=operator.status()
        service.mark_host_finished()
        if len(coordinator.applied_receipts)==2:
            result['guest_cleanup_report']=service.wait_guest_finished(args.wait_seconds)
            result['guest_disconnect']=service.wait_guest_disconnected(args.wait_seconds)
        protection=result['room_entry'].get('protection',{})
        if (code==0 and protection.get('installed_once') is True and protection.get('restore_verified') is True and
                protection.get('retained_or_unknown') is False and mount.phase=='RETIRED' and not mount.failure and
                operator.failure is None and operator.console is not None and operator.console.ready and
                result.get('guest_cleanup_report',{}).get('native_cleanup_verified') is True):
            result['result']='PASS_EXTERNAL_REWARD_TWO_SNAPSHOT_ENTRY'
    except BaseException as exc:
        result['error']=type(exc).__name__+': '+str(exc)
    finally:
        if operator is not None:operator.close();result['operator']=operator.status()
        if entry is not None:result['room_entry']=entry.status()
        if mount is not None:result['reward_mount']=mount.status()
        if service is not None:result['network_cleanup']=service.close()
        if result.get('network_cleanup',{}).get('network_closed') is not True:result['result']='INCOMPLETE_RETAIN_EVIDENCE'
        if folder.is_dir():write_once(folder/'host-result.json',result)
    emit(dict(result=result['result'],path=str(folder/'host-result.json'),native_attempted=result['native_attempted']))
    return 0 if result['result']=='PASS_EXTERNAL_REWARD_TWO_SNAPSHOT_ENTRY' else 1


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group();mode.add_argument('--check',action='store_true');mode.add_argument('--execute',action='store_true')
    mode.add_argument('--config-fields',action='store_true')
    p.add_argument('--config',type=Path);p.add_argument('--no-native-commands',action='store_true')
    a=p.parse_args(argv)
    if a.config_fields:
        emit(dict(schema=SCHEMA,top_level=['manifest','rules','network','native','adapter_key_path',*sorted(EXTRA)],
            native=['pid','wait_seconds',*NATIVE_PATHS,'reward_build_run','reward_build_sha256'],
            rules_build=['stage','publisher'],network=['listen_host','advertise_host','control_port','download_port','directory'],
            inherited_schema='san14.a-protected-host.v1',pid_discovery=False,
            key_pairing={'reward_report_key_path':'B report_key_path','guest_cut_key_path':'B cut_key_path'},
            native_menu_supported=False));return 0
    if not a.check and not a.execute:p.print_help();return 0
    if a.config is None:p.error('--config required')
    if a.execute and not a.no_native_commands:p.error('--execute requires --no-native-commands')
    c=read_config(a.config)
    if a.check:
        _,adapter,_,report,cut=check(c)
        emit(dict(result='PASS_FILES_ONLY',game_access=False,network_opened=False,execute_authorized=False,
                  key_fingerprints=dict(adapter=public(adapter),reward_report=public(report),guest_cut=public(cut))));return 0
    return run(c,no_native_commands=a.no_native_commands)


if __name__=='__main__':raise SystemExit(main())
