"""Explicit B observed pilot entry: two checkpoints, retained owners, rules cleanup.

Default help does nothing. --check is read-only; --execute requires a supplied
PID and the human no-new-command condition. Observations are not an input fence.
Native modules remain resident. Never restore CC03 physically in a live process.
"""
from copy import deepcopy
from dataclasses import asdict
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import sys
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT.parent/'mod_research/python_deps'),str(ROOT/'outputs/san14-link')]
from authoritative_sync import canonical,digest,validate_scope,validate_node,next_node
from b_remote_session import Session,verify_sources,approved_builds
from b_remote_session_boundary import DiagnosticBoundary,need
from b_observed_completion import GuestCompletion
from b_warm_profile_contract import Profile,Date,Identity,validate_profile
from human_rules_world_lifecycle import NextWorldRequest
from b_warm_rules_factory import RulesBuild
from b_warm_adapter_key import load_key,public
from b_warm_received_apply import write_once
from b_warm_bootstrap_protocol import receive_bootstrap_staged
from b_warm_room import receive_staged
from b_warm_refresh_start_support import identity
from b_warm_pair_preflight import dll_identity,STEAM_HASHES
from b_warm_pair_diagnostic import require_original_rules,require_no_debugger
from checkpoint_complete_live_capture import process_birth
from human_rules_activation_room import rules
from game_reader import GameReader
from observed_room_service import validate_invitation,join_guest,request_ok
import b_warm_staging as files
# Resident loads these lazily during native work; expose their source identity
# before the startup approval manifest is checked, without executing an API.
import b_warm_start_support
import a_save_runtime_control
import run_autonomous_pilot
import b_warm_refresh_contract

SCHEMA='san14.b-observed-start.v1'
EXTRA_SOURCES=('b_observed_start.py','b_observed_completion.py','observed_completion_contract.py',
               'observed_room_service.py','b_warm_bootstrap_protocol.py','b_warm_room.py',
               'b_warm_start_support.py','a_save_runtime_control.py','run_autonomous_pilot.py','b_warm_refresh_contract.py')
LOCAL_KEYS=set(('pid birth target initial_target initial_node source_player target_player records adapter_key_path '
               'pair_build helper_build rules_build steam_paths source_manifest rules wait_seconds native_timeout').split())


def sha(raw):return hashlib.sha256(raw).hexdigest()


def validate_config(value):
    need(type(value) is dict and set(value)=={'schema','network','local'} and value['schema']==SCHEMA,
         'Exact B startup configuration required')
    c=deepcopy(value);validate_invitation(c['network']);v=c['local']
    need(type(v) is dict and set(v)==LOCAL_KEYS,'Exact local configuration fields required')
    need(type(v['pid']) is int and 0<v['pid']<2**32 and type(v['birth']) is int and 0<v['birth']<2**64,
         'Explicit process incarnation required')
    validate_node(v['initial_node'])
    need(type(v['wait_seconds']) is int and 1<=v['wait_seconds']<=1800 and
         type(v['native_timeout']) is int and 30<=v['native_timeout']<=1800,'Bounded timeouts required')
    for key in ('source_player','target_player'):
        p=v[key];need(type(p) is dict and set(p)=={'force','ruler','district'} and
                     all(type(x) is int for x in p.values()),'Exact native player identity required')
    need(v['target_player']['force']==c['network']['force_id'],'Invitation selects another force')
    for key in ('pair_build','helper_build','source_manifest'):
        p=v[key];need(type(p) is dict and set(p)=={'path','sha256'} and type(p['sha256']) is str and
                     len(p['sha256'])==64 and all(x in '0123456789abcdef' for x in p['sha256']),
                     'Explicit approved path and SHA required')
        files.clean_path(p['path'])
    need(type(v['rules_build']) is dict and set(v['rules_build'])=={'stage','publisher'},'Exact rules build required')
    for key in ('target','records','adapter_key_path'):files.clean_path(v[key])
    need(Path(v['target']).name==files.NAME and Path(v['records'])!=Path(v['target']).parent,
         'Independent records and exact CC03 target required')
    need(v['rules']==rules(v['rules'].get('native_income_key5'),v['rules'].get('native_world_option8')),
         'Supported immutable rules required')
    identity(v['initial_target']);make_profile(v,v['initial_target'],v['initial_node'],v['initial_node'],1)
    return c


def make_profile(local,part,before,loaded,generation):
    p=Profile();p.file.name=files.NAME.encode();p.file.slot=63;p.file.size=part['size']
    p.file.sha256[:]=bytes.fromhex(part['sha256'])
    p.before=Date(*(before[k] for k in ('year','month','day')))
    p.loaded=Date(*(loaded[k] for k in ('year','month','day')))
    for key,name in (('source_player','source'),('target_player','target')):
        v=local[key];setattr(p,name,Identity(v['ruler'],v['force'],v['district']))
    p.currentForce=p.source.force if generation==1 else p.target.force
    return validate_profile(p)


def preflight(config):
    """Local reads only: no network join, claims, DLL loads or native calls."""
    config=validate_config(config);v=config['local']
    need(not Path(v['records']).exists(),'Fresh records path required; no previous run reuse')
    spec=v['source_manifest'];raw=Path(spec['path']).read_bytes()
    need(sha(raw)==spec['sha256'],'Source manifest hash differs')
    manifest=json.loads(raw);need(manifest.get('result')=='PASS' and manifest.get('inputs_unchanged') is True,
                                  'Approved successful source manifest required')
    pins=manifest['sources'];verify_sources(pins)
    for name in EXTRA_SOURCES:need(str(HERE/name) in pins,'Startup source missing: '+name)
    pair,helper=approved_builds(v['pair_build']['path'],v['pair_build']['sha256'],
                               v['helper_build']['path'],v['helper_build']['sha256'])
    build=RulesBuild(Path(v['rules_build']['stage']),Path(v['rules_build']['publisher']));build.check()
    need(type(v['steam_paths']) is dict and set(v['steam_paths'])==set(STEAM_HASHES),'Exact storage modules required')
    for name,h in STEAM_HASHES.items():
        need(Path(v['steam_paths'][name]).name==name and dll_identity(v['steam_paths'][name])['sha256']==h,
             'Storage module identity differs')
    key=load_key(v['adapter_key_path']);current,raw=files.read_file(Path(v['target']))
    need(current==v['initial_target'],'Initial CC03 identity differs')
    reader=GameReader(pid=v['pid'])
    try:
        need(process_birth(reader)==v['birth'],'Process incarnation differs')
        probe=make_profile(v,current,v['initial_node'],v['initial_node'],1)
        boundary=DiagnosticBoundary(reader,probe,pid=v['pid'],birth=v['birth'],no_new_commands=True)
        observation=asdict(boundary.observe())
        original=require_original_rules(reader,pid=v['pid'],birth=v['birth']);require_no_debugger(reader)
        need(process_birth(reader)==v['birth'] and files.read_file(Path(v['target']))[0]==current,'Preflight identity changed')
    finally:reader.close()
    return dict(result='READ_ONLY_CHECKED',sources=pins,adapter_key=public(key),observation=observation,
                original_rules=original,target=current,native_calls=0,network_joined=False,claim_created=False)


class Runner:
    """One retained owner. Any failure is terminal; this object is never reused."""
    def __init__(self,config,link):
        self.config=validate_config(config);self.local=self.config['local'];self.link=link
        self.reader=None;self.session=None;self.guest=None;self.received=[];self.phase='NEW'
        self.cleanup=dict(native_cleanup_verified=False,retained_native_state=False,formal_completions=0,
            sources_restored=False,local_handles_closed=False,
            native_modules_unloaded=False,target_file_restored=False,
            requires_game_exit_before_original_file_restore=True)
        self.records=Path(self.local['records']);self.notify_attempted=False

    def _record(self,name,value):write_once(self.records/name,value)

    def _context(self,generation,scope=None):
        end=time.monotonic()+self.local['wait_seconds']
        while True:
            left=end-time.monotonic();need(left>0,'Checkpoint wait timed out; no reconnect')
            c=self.link.wait_context(max(1,min(1800,int(left)+1)))
            need(c['phase'] not in ('HELD','CLOSED','DISCONNECTED'),'Authority is held')
            if scope is not None:need(canonical(c['scope'])==canonical(scope),'Authority scope changed')
            need(c['period']<=generation,'Authority skipped expected checkpoint')
            if c['period']==generation and c['phase']=='RECONCILING' and c['manifest'] is not None:
                need(c['checkpoint_id'] and c['manifest']['period']==generation,'Offered period differs')
                return c
            time.sleep(.1)

    def _open(self,context,profile,pins):
        v=self.local;self.reader=GameReader(pid=v['pid'])
        need(process_birth(self.reader)==v['birth'],'Process incarnation changed before install')
        self.initial_checkpoint=digest(dict(scope=context['scope'],pid=v['pid'],birth=v['birth'],
                                            node=v['initial_node'],target=v['initial_target']))
        initial=NextWorldRequest(1,self.initial_checkpoint,secrets.token_bytes(16),
                                 *(v['initial_node'][k] for k in ('year','month','day')))
        directory=self.records/'session';directory.mkdir()
        try:
            self.session=Session.open(reader=self.reader,control=self.link.control,scope=context['scope'],
                settings=v['rules'],profile=profile,initial_request=initial,target=v['target'],
                initial_target=v['initial_target'],records=directory,adapter_key_path=v['adapter_key_path'],
                pair_build=v['pair_build']['path'],pair_sha256=v['pair_build']['sha256'],
                helper_build=v['helper_build']['path'],helper_sha256=v['helper_build']['sha256'],
                rules_build=RulesBuild(Path(v['rules_build']['stage']),Path(v['rules_build']['publisher'])),
                steam_paths=v['steam_paths'],source_pins=pins,no_new_commands=True,timeout=v['native_timeout'])
        except BaseException as exc:
            self.session=getattr(exc,'retained_session',self.session);raise
        self.guest=GuestCompletion(self.session)

    def finish_native(self):
        s=self.session;g=self.guest
        need(s is not None and g is not None and len(g.history)==2 and
             g.phase=='TWO_COMPLETIONS_RETAINED' and s.phase=='TWO_LOADS_RETAINED',
             'Normal cleanup only after two known formal completions')
        need(s.read_birth()==self.local['birth'] and s.reader.pid==self.local['pid'],'Cleanup process changed')
        s.boundary.observe();s.warm.finish()
        port=s.lifecycle.current;need(not port.retired,'Current rules port already retired')
        restoration=port.restore();port.retired=True
        s.boundary.observe();original=require_original_rules(s.reader,pid=self.local['pid'],birth=self.local['birth'])
        require_no_debugger(s.reader)
        final=files.read_file(Path(self.local['target']))[0];p=s.boundary.profile
        need((final['size'],final['sha256'])==(p.file.size,bytes(p.file.sha256).hex()),'Final target differs')
        self.cleanup.update(sources_restored=True,formal_completions=2,
                            rules_restoration=restoration,original_rules=original,final_target=final)
        s.warm.close();self.reader.close();self.reader=None
        self.cleanup.update(native_cleanup_verified=True,local_handles_closed=True,retained_native_state=False)
        self._record('native-cleanup.json',self.cleanup)
        self.phase='NATIVE_CLEAN'

    def _terminal(self,exc):
        self.phase='TERMINAL';s=self.session
        if s is not None and not self.cleanup['native_cleanup_verified']:
            s.phase='TERMINAL';s.boundary.hold(type(exc).__name__)
        self.cleanup['retained_native_state']=s is not None and not self.cleanup['native_cleanup_verified']
        self.cleanup['formal_completions']=len(self.guest.history) if self.guest else 0
        if s is None and self.reader is not None:
            try:self.reader.close();self.reader=None;self.cleanup['local_handles_closed']=True
            except BaseException as secondary:self.reader_close_error=type(secondary).__name__
        exc.retained_runner=self
        try:self._record('failed.json',dict(error_type=type(exc).__name__,phase=self.phase,cleanup=self.cleanup))
        except BaseException as secondary:self.record_error=type(secondary).__name__;exc.record_error=self.record_error

    def _notify(self):
        need(not self.notify_attempted,'Finish notification is not replayable');self.notify_attempted=True
        body=dict(action='pilot_guest_finished',**{k:self.cleanup[k] for k in
                  ('formal_completions','native_cleanup_verified','retained_native_state')})
        self._record('finish-notification-intent.json',body)
        reply=request_ok(self.link.control,body);need(reply.get('recorded') is True,'Finish was not recorded')
        self._record('finish-notification-reply.json',reply)

    def _wait_host_finished(self):
        # Read-only false replies may be sampled again. A lost reply is terminal;
        # no completion packet, native operation, or finish notification repeats.
        end=time.monotonic()+self.local['wait_seconds'];polls=0
        self._record('host-finish-wait.json',dict(timeout_seconds=self.local['wait_seconds'],
                                                control_connection_retained=True))
        while True:
            need(time.monotonic()<end,'Host finish acknowledgement timed out; no reconnect')
            reply=request_ok(self.link.control,dict(action='pilot_host_finished'));polls+=1
            need(type(reply.get('host_finished')) is bool,'Malformed host finish acknowledgement')
            if reply['host_finished']:
                self._record('host-finished.json',dict(reply=reply,polls=polls));return
            time.sleep(min(.1,max(0,end-time.monotonic())))

    def run(self):
        need(self.phase=='NEW','Runner cannot be replayed');self.phase='CHECKING'
        primary=None
        try:
            checked=preflight(self.config);self.records.mkdir(parents=True,exist_ok=False)
            self._record('preflight.json',checked)
            old,raw=files.read_file(Path(self.local['target']));need(old==self.local['initial_target'],'Target drift before backup')
            files.save_new(self.records/'original-CC03.bin',raw);self._record('original-target.json',old)
            scope=None;before=self.local['initial_node']
            for generation in (1,2):
                c=self._context(generation,scope);validate_scope(c['scope']);scope=c['scope'];m=c['manifest']
                need(canonical(scope['profile'])==canonical(self.config['network']['profile']),
                     'Authenticated compatibility profile differs from invitation')
                for side,key in (('A','source_player'),('B','target_player')):
                    v=self.local[key];need(scope['bindings'][side]==dict(force_id=v['force'],main_district_id=v['district']),
                                           'Authenticated seat differs from local native identity')
                need(scope['profile']['rules_sha256']==digest(self.local['rules']),'Room rules differ')
                wanted=before if generation==1 else next_node(before)
                need(m['node']==wanted,'Expected same-day bootstrap then exactly one turn')
                p=make_profile(self.local,m['parts']['world.s14'],before,m['node'],generation)
                receive=receive_bootstrap_staged if generation==1 else receive_staged
                received=receive(self.link.control,self.link.connect_download,checkpoint_id=c['checkpoint_id'],
                    scope=scope,epoch=c['epoch'],period=c['period'],cut=m['cut'],attachments=c['attachments'],
                    directory=self.records/f'received-{generation}')
                self.received.append(received)
                if generation==1:self._open(c,p,checked['sources'])
                q=NextWorldRequest(generation+1,c['checkpoint_id'],secrets.token_bytes(16),
                                   *(m['node'][k] for k in ('year','month','day')))
                self.phase='APPLYING';reply=self.guest.apply(received,q,p)
                self._record(f'formal-{generation}.json',reply);before=m['node']
                if generation==1:
                    # No command or seal is issued. A must independently become ready.
                    request_ok(self.link.control,dict(action='period_ready',epoch=self.guest.epoch,ready=True))
            self.finish_native()
        except BaseException as exc:
            primary=exc;self._terminal(exc)
        finally:
            if self.records.exists():
                try:
                    self._notify()
                    if primary is None:self._wait_host_finished()
                except BaseException as exc:
                    if primary is None:primary=exc;self._terminal(exc)
                    else:self.notification_error=type(exc).__name__
            try:self.link.close()
            except BaseException as exc:
                if primary is None:primary=exc;self._terminal(exc)
                else:self.network_close_error=type(exc).__name__
        if primary is not None:raise primary
        self.phase='COMPLETE'
        result=dict(result='PASS_B_OBSERVED_TWO_CHECKPOINTS_RULES_RESTORED',cleanup=self.cleanup,
            native_gameplay_enabled=False,full_world_verified=False,input_exclusion_proven=False,
            scheduler_fence_proven=False,human_no_new_commands=True,network_closed=True)
        self._record('result.json',result);return result


def run(config,link):return Runner(config,link).run()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path)
    actions=p.add_mutually_exclusive_group();actions.add_argument('--check',action='store_true');actions.add_argument('--execute',action='store_true')
    p.add_argument('--no-new-commands',action='store_true');a=p.parse_args(argv)
    if not (a.check or a.execute):p.print_help();return 0
    need(a.config is not None and a.no_new_commands,'Explicit config and no-new-command condition required')
    config=validate_config(json.loads(a.config.read_text(encoding='utf-8')))
    checked=preflight(config)
    if a.check:print(json.dumps({k:v for k,v in checked.items() if k!='sources'},indent=2));return 0
    link=join_guest(config['network']);result=run(config,link)
    print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
