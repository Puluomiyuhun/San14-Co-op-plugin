"""B external-console successor: explicit two-load reward pilot, no native menus.

Default help is inert. --check reads configuration/build/source/key files only;
it never checks a live PID, HWND, Steam module or save. --execute requires the
human no-game-input condition and runs the existing input/reward Runner with
its full fresh preflight. No retries, automatic Ready, reconnect or unload.

First load precedes input installation. After load2 the input WndProc remains
held: the test ends with a required normal game exit, not resumed gameplay.
Config schema: san14.b-simple-remote-guest.v1. Fields: startup (the exact
b-observed-start configuration), reward_build/input_build ({run,sha256}),
window ({handle,thread,timeout_ms}), report_key_path and cut_key_path.
After reward-planning-open, enter one JSON object per line, for example:
  {"action":"reward","request_id":"11111111111111111111111111111111","district_id":2,"officer_ids":[101]}
  {"action":"ready","request_id":"22222222222222222222222222222222"}
Use fresh request IDs and officers belonging to B's configured main district.
"""
from copy import deepcopy
import argparse,hashlib,json,secrets,sys,threading
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT.parent/'mod_research/python_deps'),str(ROOT/'outputs/san14-link')]
import b_observed_start as startup
import b_input_reward_runner as native
import b_reward_native_port as reward_native
import player_input_lease_bootstrap_port as inputs
from b_remote_session import verify_sources,approved_builds
from b_warm_rules_factory import RulesBuild
from b_warm_adapter_key import load_key,public
from observed_room_service import join_guest
from reward_room_flow import envelope
from reward_observed_context import need
from authority_reward import eligible_ids

SCHEMA='san14.b-simple-remote-guest.v1'
FIELDS={'schema','startup','reward_build','input_build','window','report_key_path','cut_key_path'}
DEFERRED=('fresh PID/birth and game executable','HWND/thread and original WndProc',
    'Steam module identity and storage interfaces','current CC03 bytes and five-state planning snapshot',
    'first real load retirement and native completion','network reachability and A reward-discovery binding',
    'input bootstrap and Ready ACK','reward execution/replay and bridge restoration before second load',
    'second real load and retained input owner cleanup')

def _sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def _path(value):
    need(type(value) is str and Path(value).is_absolute(),'Explicit absolute local file path required')
    return startup.files.clean_path(value)
def _build(value):
    need(type(value) is dict and set(value)=={'run','sha256'} and type(value['sha256']) is str and
         len(value['sha256'])==64 and all(c in '0123456789abcdef' for c in value['sha256']),
         'Explicit immutable native build result required')
    _path(value['run']);return value

def validate_config(value):
    need(type(value) is dict and set(value)==FIELDS and value['schema']==SCHEMA,'Exact B simple guest configuration required')
    c=deepcopy(value);startup.validate_config(c['startup']);_build(c['reward_build']);_build(c['input_build'])
    storage=c['startup']['local']['steam_paths']
    need(type(storage) is dict and set(storage)==set(startup.STEAM_HASHES),'Exact storage module paths required')
    for name,path in storage.items():
        _path(path);need(Path(path).name==name,'Storage module basename differs')
    for name in ('report_key_path','cut_key_path'):_path(c[name])
    w=c['window'];need(type(w) is dict and set(w)=={'handle','thread','timeout_ms'} and
        type(w['handle']) is int and 0<w['handle']<2**64 and type(w['thread']) is int and 0<w['thread']<2**32 and
        type(w['timeout_ms']) is int and 50<=w['timeout_ms']<=5000,'Explicit local window identity and bounded timeout required')
    return c

def read_config(path):return validate_config(json.loads(Path(path).read_text(encoding='utf-8-sig')))

def check(value):
    """Approve actual file closures only. Never call startup.preflight here."""
    c=validate_config(value);v=c['startup']['local'];spec=v['source_manifest']
    need(not Path(v['records']).exists(),'Fresh native record directory required')
    raw=Path(spec['path']).read_bytes();need(hashlib.sha256(raw).hexdigest()==spec['sha256'],'Source manifest changed')
    manifest=json.loads(raw);need(manifest.get('result')=='PASS' and manifest.get('inputs_unchanged') is True,
        'Successful unchanged startup source manifest required')
    pins=manifest['sources'];verify_sources(pins)
    for name in startup.EXTRA_SOURCES+native.predecessor.REWARD_SOURCES+native.SOURCES+('b_simple_remote_guest.py','simple_remote_console.py'):
        p=(HERE/name).resolve();need(pins.get(str(p))==_sha(p),'B startup source missing or changed: '+name)
    for name in ('reward_room_flow.py','execution_journal.py'):
        p=(ROOT/'outputs/san14-link'/name).resolve();need(pins.get(str(p))==_sha(p),'B journal source missing or changed: '+name)
    pair,helper=approved_builds(v['pair_build']['path'],v['pair_build']['sha256'],v['helper_build']['path'],v['helper_build']['sha256'])
    RulesBuild(Path(v['rules_build']['stage']),Path(v['rules_build']['publisher'])).check()
    reward=reward_native.approved_build(reward_native.NativeBuild(Path(c['reward_build']['run']),c['reward_build']['sha256']))
    input_dll,input_sha=inputs.approved(inputs.Build(Path(c['input_build']['run']),c['input_build']['sha256']))
    keys={name:public(load_key(path)) for name,path in (
        ('adapter',v['adapter_key_path']),('report',c['report_key_path']),('cut',c['cut_key_path']))}
    need(len({item['fingerprint'] for item in keys.values()})==3,'Adapter, report and cut keys must differ')
    return dict(result='PASS_FILES_ONLY',schema=SCHEMA,runner='b_input_reward_runner.Runner',
        source_count=len(pins),source_manifest_sha256=spec['sha256'],
        native_builds=dict(pair=pair['family'],helper=helper['family'],reward_sha256=reward['sha256'],input_sha256=input_sha),
        key_fingerprints={k:x['fingerprint'] for k,x in keys.items()},live_checks_deferred=list(DEFERRED),
        game_access=False,steam_access=False,save_access=False,process_access=False,network_opened=False,
        native_calls=0,install_permission=False,two_real_clients_verified=False,
        first_load_precedes_input_install=True,input_window_restored_at_end=False,
        retained_input_owner_at_end=True,external_commands_only=True)

class Runner(native.Runner):
    """Drain the local operator before every inherited native terminal path."""
    def __init__(self,*args,operator,**kw):
        self.operator=operator
        super().__init__(*args,**kw)

    def _reward_sources(self,pins):
        super()._reward_sources(pins)
        for name in ('b_simple_remote_guest.py','simple_remote_console.py'):
            p=(HERE/name).resolve();need(pins.get(str(p))==_sha(p),'B console source drift: '+name)

    def _terminal(self,exc):
        # Ordinary run exceptions have unwound reward_lock before reaching here.
        # finish_input may call us on the Console thread already holding both
        # reentrant locks in Console -> reward order; closing is reentrant there.
        self.operator.close()
        with self.reward_lock:super()._terminal(exc)

class Operator:
    """Trusted local input only; callbacks retain the exact Runner/room owner."""
    def __init__(self,stream,emit):
        self.stream=stream;self.emit=emit;self.runner=None;self.console=None;self.active=False

    def event(self,name,runner):
        need(self.runner in (None,runner),'Foreign B Runner callback')
        self.runner=runner
        self.emit(dict(event=name,seat='B',native_menu_permission=False))
        if name=='reward-planning-restored':self.close()
        if name=='reward-planning-open':
            need(self.console is None and runner.input_phase=='PLANNING','Exactly one acknowledged input window required')
            from simple_remote_console import Console
            self.active=True;self.console=Console(on_reward=self.reward,on_ready=self.ready,on_failure=self.failure,emit=self.emit)
            with runner.reward_lock,runner.reward.lock:
                r=self._current().reward;r._binding();actor=r.replica.scope['bindings']['B']
                context=r.replica.port.context(actor['force_id']);candidates=eligible_ids(context,actor['main_district_id'])
            self.emit(dict(event='external-reward-planning-open',force_id=actor['force_id'],
                district_id=actor['main_district_id'],observed_candidate_ids=candidates,
                eligibility_rechecked_at_execution=True,
                reward_example=(dict(action='reward',request_id=secrets.token_hex(16),
                    district_id=actor['main_district_id'],officer_ids=candidates[:1]) if candidates else None),
                ready_example=dict(action='ready',request_id=secrets.token_hex(16)),automatic_ready=False,
                native_menu_supported=False,input_exclusion_proven=False))
            self.console.start(self.stream)

    def _current(self):
        r=self.runner
        need(self.active and r is not None and r.phase=='REWARD_PLANNING' and r.reward is not None and
             r.reward.phase=='ACTIVE' and not r.finish_requested.is_set(),'B external input window is closed')
        return r

    def reward(self,request_id,district_id,officer_ids):
        runner=self.runner;need(runner is not None,'B planning has not opened')
        with runner.reward_lock:
            r=self._current().reward
            with r.lock:
                r._binding();need(not r.cut.prepared,'B shared cut already prepared')
                scope=r.replica.scope;actor=scope['bindings']['B']
                need(district_id==actor['main_district_id'] and type(officer_ids) is list and
                     1<=len(officer_ids)<=16 and all(type(i) is int and 1<=i<6000 for i in officer_ids) and
                     len(set(officer_ids))==len(officer_ids),'Exact B district and unique bounded officers required')
                # Real retained reader validates date/identity before queueing;
                # ACK remains a queue outcome, never local native completion.
                r.replica.port.context(actor['force_id'])
                reply=r.cut._request(envelope(scope,'reward_submit',request_id=request_id,
                    district_id=district_id,officer_ids=officer_ids))
                need(reply.get('ok') is True and reply.get('player')=='B' and reply.get('request_id')==request_id and
                     type(reply.get('ordinal')) is int and reply['ordinal']>0 and
                     reply.get('status') in ('QUEUED','DISPATCHING','AWAITING_B','PAIRED','REJECTED'),
                     'Foreign reward queue acknowledgement')
                return dict(authority_ack=reply,queue_ack_only=True,native_execution_verified=False)

    def ready(self,request_id):
        runner=self.runner;need(runner is not None,'B planning has not opened')
        with runner.reward_lock:
            self._current();runner.finish_input()
            return dict(request_id=request_id,input_ready_acknowledged=True,
                ready_sent_to_room=False,waiting_for_shared_cut_and_native_restore=True)

    def failure(self,exc):
        runner=self.runner
        if runner is not None:
            with runner.reward_lock:
                if self.active:self.active=False;runner._terminal(exc)

    def close(self):
        # Console callbacks take Console.lock -> reward_lock. Drain that outer
        # lock first, outside reward_lock, before native second-load/cleanup.
        if self.console is not None:self.console.close()
        runner=self.runner
        if runner is None:self.active=False
        else:
            with runner.reward_lock:self.active=False

def run(value,*,no_game_input,stream=None,emit=None):
    need(no_game_input is True,'Explicit --no-game-input required; use external commands only')
    c=validate_config(value);checked=check(c)
    output_lock=threading.Lock()
    def output(row):
        if emit is not None:return emit(row)
        with output_lock:print(json.dumps(row,ensure_ascii=False),flush=True)
    output(dict(event='files-checked',result=checked['result'],live_checks_still_required=True))
    operator=Operator(sys.stdin if stream is None else stream,output);link=None;started=False
    try:
        link=join_guest(c['startup']['network'])
        runner=Runner(c['startup'],link,operator=operator,
            native_build=reward_native.NativeBuild(Path(c['reward_build']['run']),c['reward_build']['sha256']),
            input_build=inputs.Build(Path(c['input_build']['run']),c['input_build']['sha256']),
            window=c['window']['handle'],window_thread=c['window']['thread'],input_timeout_ms=c['window']['timeout_ms'],
            report_key_path=c['report_key_path'],cut_key_path=c['cut_key_path'],on_event=operator.event)
        operator.runner=runner;started=True;result=runner.run()
        need(result.get('result')=='PASS_B_REWARD_TWO_CHECKPOINTS_RESTORED' and
             result['cleanup'].get('formal_completions')==2 and result['cleanup'].get('native_cleanup_verified') is True and
             result['cleanup'].get('input_owner_retained') is True and result['cleanup'].get('input_window_restored') is False,
             'B diagnostic lifecycle/retained input outcome incomplete')
        output(dict(event='b-remote-test-complete',two_checkpoints=True,input_owner_retained=True,
            input_window_restored=False,requires_game_exit=True,two_real_clients_verified=False))
        return result
    finally:
        operator.close()
        if link is not None and not started:link.close()

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('--config',type=Path)
    modes=p.add_mutually_exclusive_group();modes.add_argument('--check',action='store_true');modes.add_argument('--execute',action='store_true')
    p.add_argument('--no-game-input',action='store_true');a=p.parse_args(argv)
    if not(a.check or a.execute):p.print_help();return 0
    if a.config is None:p.error('--config required')
    if a.execute and not a.no_game_input:p.error('--execute requires --no-game-input')
    try:
        c=read_config(a.config)
        if a.check:print(json.dumps(check(c),ensure_ascii=False,indent=2));return 0
        run(c,no_game_input=True);return 0
    except Exception as exc:
        # Config/invitation contains credentials. Do not print arbitrary exception
        # text that could contain packets; retained native records keep details.
        print(json.dumps(dict(result='FAILED_RETAIN_EVIDENCE',error_type=type(exc).__name__,
            retry_allowed=False,game_cleanup_claimed=False,credentials_disclosed=False)),flush=True);return 1

if __name__=='__main__':raise SystemExit(main())
