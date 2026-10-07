"""Same-player load34 pilot. Default is read-only precheck; --dry attaches without data writes.

--execute needs a successful dry run of this exact binary and an unused durable
once path. Never retries automatically and never builds native slot metadata.
"""
import argparse,ctypes as C,hashlib,json,struct,subprocess,sys
from ctypes import wintypes as W
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent.parent/'outputs/san14-link'))
from game_reader import GameReader
from startup_identity_reader import capture_startup_context
CHECKPOINT=Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14')
CHECKPOINT_SHA='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
JOURNAL=ROOT/'auto_reload_live_once.json'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def precheck(reader):
    m=reader.memory;context=capture_startup_context(reader);snapshot=context['snapshot'];reasons=[]
    def need(ok,message):
        if not ok:reasons.append(message)
    k=m.k;k.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)];k.CheckRemoteDebuggerPresent.restype=W.BOOL
    debugger=W.BOOL();need(k.CheckRemoteDebuggerPresent(m.handle,C.byref(debugger)) and not debugger.value,'debugger_present_or_query_failed')
    need(reader.sha256=='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025','unsupported_game_build')
    need(snapshot['player']['force_id']==12 and snapshot['player']['ruler_id']==666,'not_Zhang_Lu')
    need(snapshot['date']=={'year':203,'month':8,'day':11,'period':'中旬'},'not_checkpoint34_date')
    need(snapshot['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'],'not_idle_planning')
    need(context['state_sample'] is not None and context['state_sample']['phase_raw']==2 and context['world_mode']==1,'wrong_user_phase_or_world_mode')
    need(sha(CHECKPOINT)==CHECKPOINT_SHA and CHECKPOINT.stat().st_size==274920,'checkpoint34_changed')
    image=(ROOT/'game-runtime-image.bin').read_bytes();profile=load(ROOT/'auto_reload_profile.json')
    for g in profile['ranges']:need(m.read(m.base+g['start'],g['end']-g['start'])==image[g['start']:g['end']],'native_code_changed_at_'+hex(g['start']))
    u64=lambda at:struct.unpack('<Q',m.read(at,8))[0]
    i32=lambda at:struct.unpack('<i',m.read(at,4))[0]
    manager=u64(m.base+0x2025318);mode=i32(manager+8);pending=i32(manager+0x3EC)
    need(mode==0,'manager_not_read_mode');need(pending==-1,'pending_reload_request')
    cache=u64(manager+0x20+34*8);filename=None
    need(cache>=0x10000,'slot34_metadata_missing')
    if cache>=0x10000:
        string=cache+0x128;length=u64(string+16);capacity=u64(string+24)
        need(length<=512 and length<=capacity<=32768,'invalid_slot_filename_string')
        if length<=512 and length<=capacity<=32768:
            pointer=u64(string) if capacity>=16 else string
            raw=m.read(pointer,length+1)
            filename=raw[:-1].decode('ascii',errors='replace')
            need(raw==b'svdexSC34.s14\0','slot34_metadata_filename_mismatch')
    queue=u64(m.base+0x19E7310+0x30);need(queue==0,'pending_state_transition')
    states=reader.state_objects()
    if len(states)==5:
        game=states[2][1];need(i32(game+0x474)==0 and i32(game+0x478)==0,'native_transition_already_started')
    need(context==capture_startup_context(reader),'context_changed_during_precheck')
    return {'result':'PASS' if not reasons else 'BLOCKED_PRECONDITIONS','reasons':reasons,'pid':reader.pid,'base':hex(m.base),'context':context,'manager':hex(manager),'mode':mode,'pending_slot':pending,'slot34_metadata':hex(cache),'filename':filename,'pending_state_commands':queue,'checkpoint_sha256':CHECKPOINT_SHA,'game_writes':0,'debugger_attached_by_precheck':False,'scope':'Targeted preconditions only; not a full-world or unsaved-command equivalence proof.'}
def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group();g.add_argument('--precheck',action='store_true');g.add_argument('--dry',action='store_true');g.add_argument('--execute',action='store_true');p.add_argument('--seconds',type=int,default=60);args=p.parse_args()
    assert 2<=args.seconds<=900
    reader=GameReader()
    try:before=precheck(reader)
    finally:reader.close()
    save(ROOT/'auto_reload_preflight.json',before)
    if not(args.dry or args.execute) or before['result']!='PASS':print(json.dumps(before,ensure_ascii=False,indent=2));return
    binary=ROOT/'observe_auto_reload.exe';binary_sha=sha(binary);tests=load(ROOT/'auto_reload_test_results.json')
    assert tests['result']=='PASS' and len(tests['cases'])==18 and tests['binary_sha256']==binary_sha,'Run native fixture tests for exact binary first'
    assert tests['cleanup']['result']=='PASS' and tests['cleanup']['cases']==6,'Run real-thread cleanup fixtures first'
    if args.execute:
        assert not JOURNAL.exists(),'Existing once intent forbids another attempt, including after failure'
        dry=load(ROOT/'auto_reload_dry_result.json')
        assert dry['result']=='PASS' and dry['binary_sha256']==binary_sha and dry['before']['pid']==before['pid'] and dry['before']['base']==before['base'],'Need dry guards for exact binary and attachment'
    folder=ROOT/'auto_reload_traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    log=folder/'trace.jsonl';save(folder/'before.json',before)
    with (folder/'stdout.log').open('wb') as out,(folder/'stderr.log').open('wb') as err:
        proc=subprocess.Popen([str(binary),str(before['pid']),before['base'],'0x3f8177',str(args.seconds),str(log),'execute' if args.execute else 'dry',str(JOURNAL),str(CHECKPOINT)],stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    try:proc.wait(timeout=args.seconds+15)
    except BaseException:
        Path(str(log)+'.stop').write_text('stop');proc.wait(timeout=15);raise
    rows=[json.loads(s) for s in log.read_text(encoding='utf-8').splitlines()]
    expected='same_player_reload_observed' if args.execute else 'dry_request_guards_passed'
    passed=proc.returncode==0 and any(r.get('event')==expected for r in rows) and rows[-1]=={'event':'detached','captured':True,'registers_restored':True}
    result={'result':'PASS' if passed else 'NOT_COMPLETED_NO_AUTO_RETRY','execute':args.execute,'binary_sha256':binary_sha,'directory':str(folder),'before':before,'exit_code':proc.returncode,'trace':rows,'once_journal':str(JOURNAL),'full_world_sync_proven':False}
    save(folder/'result.json',result)
    if args.dry and passed:save(ROOT/'auto_reload_dry_result.json',result)
    if args.execute:save(ROOT/'auto_reload_live_result.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
