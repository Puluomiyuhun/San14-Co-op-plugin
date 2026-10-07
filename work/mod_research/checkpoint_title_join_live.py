"""Manual-load read-only observer. Default is offline; only --record opens SAN14.

Does not initiate loading. Waits for the user to perform one normal named load.
Debug register cleanup may retain the debugger indefinitely if OS restoration is
uncertain; never terminate this recorder to implement a hard timeout.
"""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
import time
import checkpoint_dispatch_handoff_live as prior
ROOT=Path(__file__).resolve().parent
EXE_SHA=prior.EXE_SHA
sha=prior.sha
birth=prior.birth
ANCHORS=(0x4DA240,0x834B60,0x834D98,0x834D9B,0x834DB4,0x508B40,0x4DA390,0x466600,
         0x4F7079,0x4CC690,0x4AAF64,0x4AAF89,0x4DA2E3,0x4DA2EF,0x4BEEB1,0x4BEEBD,
         0x4BEEFE,0x4BEF1A,0x4BEF26,0x4AAF5F,0x4AAF84,0x497110,0x4FAC30,0x834BC0,0x4FABC0)
EVENTS=('worker_start','runner_invocation','actual_payload_entry','runner_return','runner_done_store','worker_join_return')
PAYLOADS=(0x508B40,0x4DA390,0x466600)
STARTS=(0x4DA2F4,0x4BEEC2,0x4BEF2B)
JOINS=(0x4F7079,0x4AAF64,0x4AAF89)


def analyze_live(rows,recorder_exit=None,module_base=None,expected_name=None):
    result=dict(live_authority=False,scheduler_fence=False,task_chain_observed=False,
                source_file_bytes_attested=False)
    def reject(why):return dict(result,classification='INCOMPLETE_OR_REJECTED',blockers=[why])
    if recorder_exit!=0:return reject('recorder_exit_zero_required')
    if any(r.get('event')=='error' for r in rows):return reject('recorder_error')
    terminal=[r for r in rows if r.get('event') in ('detached','error_cleanup','process_exit')]
    if not terminal or terminal[-1].get('event')!='detached' or terminal[-1].get('registers_restored') is not True or terminal[-1].get('owned_queue_drained') is not True:return reject('no_verified_detach')
    verified=[r for r in rows if r.get('event')=='restore_verified']
    if not verified or verified[-1].get('all_six_debug_registers') is not True or verified[-1].get('owned_queue_drained') is not True:return reject('no_six_DR_readback_and_drain')
    if type(module_base) is not int or module_base<=0 or not isinstance(expected_name,str):return reject('independent_base_and_source_name_required')
    samples=[r for r in rows if 'seq' in r]
    if len(samples)!=20 or any(type(r['seq']) is not int for r in samples) or [r['seq'] for r in samples]!=list(range(1,21)):return reject('exact_twenty_native_samples_required')
    try:
        first=samples[0]
        if first['event']!='load_bound' or first['rva']!='0x4da240' or first['role']!=-1:raise ValueError('Load entry')
        if any(type(first[k]) is not int or first[k]<=0 for k in ('load','title','load_closure','thread')):raise ValueError('Object identity')
        if type(first['source_slot']) is not int or not 0<=first['source_slot']<120 or first['source_name']!=expected_name:raise ValueError('Source identity')
        for r in samples:
            if any(r[k]!=first[k] for k in ('load','title','load_closure','source_slot','source_name')) or r.get('lost_events')!=0:raise ValueError('Chain identity/loss')
        callbacks=[r for r in samples if r['event']=='load_finalize_title_callback']
        if len(callbacks)!=1:raise ValueError('Unique finalizer callback')
        cb=callbacks[0]
        if cb['rva']!='0x4cc690' or cb['role']!=-1 or cb['native_return']!=module_base+0x497134 or cb['native_result']!=1:raise ValueError('Finalizer origin')
        groups=[]
        for role in range(3):
            group=[r for r in samples if r['role']==role]
            if [r['event'] for r in group]!=list(EVENTS):raise ValueError('Paired worker chain')
            start,invoke,payload,returned,done,join=group
            control=first['load']+0x478 if role==0 else first['title']+(0x520 if role==1 else 0x590)
            if any(start[k]<=0 for k in ('callable','handle','callable_method','worker_thread','thread')):raise ValueError('Worker identity')
            if start['worker_thread']==start['thread'] or start['start_seq']!=start['seq'] or start['done'] not in (0,1):raise ValueError('Worker start identity')
            for r in group:
                if r['control']!=control or r['payload_rva']!=hex(PAYLOADS[role]) or any(r[k]!=start[k] for k in ('callable','handle','callable_method','worker_thread','start_seq')):raise ValueError('Worker immutable receipt')
            if [r['rva'] for r in group]!=[hex(x) for x in (0x834B60,0x834D98,PAYLOADS[role],0x834D9B,0x834DB4,JOINS[role])]:raise ValueError('Instruction identity')
            if start['native_return']!=module_base+STARTS[role]:raise ValueError('Worker creator caller')
            if any(r['thread']!=start['worker_thread'] for r in group[1:5]):raise ValueError('Actual payload thread')
            if any(r['done']!=0 for r in group[1:4]) or done['done']!=1 or join['done']!=1:raise ValueError('Completion publication')
            if join['cleanup_fields']!=[0,0,0]:raise ValueError('Join resource cleanup')
            if role==0 and (returned['native_result']!=1 or join['native_result']!=1):raise ValueError('Current native load result')
            groups.append(group)
        if not first['seq']<groups[0][0]['seq']<groups[0][-1]['seq']<cb['seq']<groups[1][0]['seq']:raise ValueError('Load to Title origin order')
        if not groups[1][4]['seq']<groups[2][0]['seq']<groups[1][-1]['seq']<groups[2][-1]['seq']:raise ValueError('Title starts and joins order')
        # Title590 may finish before Title520 join. No artificial serial order.
        for a in range(3):
            for b in range(a+1,3):
                if groups[a][0]['worker_thread']==groups[b][0]['worker_thread'] and groups[b][0]['seq']<groups[a][-1]['seq']:raise ValueError('Concurrent worker thread alias')
    except (KeyError,TypeError,ValueError) as exc:return reject(str(exc))
    return dict(result,classification='CURRENT_LOAD_AND_BOTH_TITLE_JOINS_OBSERVED',task_chain_observed=True,
                load=first['load'],title=first['title'],source_name=first['source_name'],source_slot=first['source_slot'],
                title590_done_before_title520_join=groups[2][4]['seq']<groups[1][-1]['seq'],
                blockers=['No scheduler fence or authority granted.','File contents/hash are not attested by this observer.'])


def snapshot(reader,require_idle):
    m=reader.memory;q=lambda p:struct.unpack('<Q',m.read(p,8))[0]
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    if hashlib.sha256(image).hexdigest()!=prior.offline.IMAGE_SHA:raise RuntimeError('Archived build changed')
    for rva in ANCHORS:
        if m.read(m.base+rva,32)!=image[rva:rva+32]:raise RuntimeError(f'Code changed at {rva:x}')
    states=reader.state_objects();stack=q(m.base+0x19E7310+0x20)
    user=states[-1][1] if states and states[-1][0]=='CUserStrategyState' else 0
    if require_idle:
        if [s[0] for s in states]!=['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']:raise RuntimeError('Not five-state idle User')
        if q(m.base+0x19E7310+0x30) or struct.unpack('<I',m.read(user+0x470,4))[0]!=2 or struct.unpack('<I',m.read(user+0x68,4))[0]:raise RuntimeError('User phase/pending transition unsupported')
    slots=(0x12CC4D0,0x12DB4E8,0x12CC9E0,0x12DBD90,0x138E8D0)
    return dict(pid=reader.pid,birth=birth(m.handle),base=m.base,exe_sha256=reader.sha256,
                user=user,stack=stack,states=states,five_known_vtable_slots={hex(x):q(m.base+x) for x in slots})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--record',action='store_true');p.add_argument('--pid',type=int)
    p.add_argument('--seconds',type=int,default=600);p.add_argument('--expected-name',default='svdexSC34.s14')
    p.add_argument('--analyze',type=Path);args=p.parse_args()
    if args.analyze:
        meta=json.loads((args.analyze.parent/'metadata.json').read_text());r=json.loads((args.analyze.parent/'result.json').read_text())
        print(json.dumps(analyze_live([json.loads(x) for x in args.analyze.read_text().splitlines() if x],r['recorder_exit'],meta['before']['base'],meta['expected_name']),indent=2));return
    if not args.record:
        print(json.dumps(dict(mode='offline_prepare',game_access=False,production_admission=False,exe_sha256=EXE_SHA,
                             recorder_sha256=sha(ROOT/'checkpoint_title_join_live.exe'),taps=[hex(x) for x in ANCHORS],
                             payloads=[hex(x) for x in PAYLOADS],wait_seconds=600),indent=2));return
    if not 1<=args.seconds<=600 or not re.fullmatch(r'[A-Za-z0-9_.]{1,62}',args.expected_name):raise ValueError('Invalid timeout or source basename')
    sys.path.insert(0,str(ROOT.parent.parent/'outputs/san14-link'))
    from game_reader import GameReader
    reader=GameReader(args.pid)
    try:
        before=snapshot(reader,True)
        if before['exe_sha256']!=EXE_SHA:raise RuntimeError('Unsupported executable')
        folder=ROOT/'checkpoint_title_join_live_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
        trace=folder/'trace.jsonl';binary=ROOT/'checkpoint_title_join_live.exe'
        meta=dict(mode='manual_normal_load',before=before,expected_name=args.expected_name,seconds=args.seconds,
                  recorder_sha256=sha(binary),game_writes=0,live_authority=False,
                  native_sequence='debug-event processing before ContinueDebugEvent',
                  limitations=['Debug stops perturb timing.','No source bytes/hash attestation.','No scheduler fence.','Uncertain OS cleanup may retain debugger indefinitely.'])
        (folder/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
        cmd=[str(binary),str(reader.pid),hex(before['base']),'0x4da240',str(args.seconds),str(trace),str(before['birth']),hex(before['user']),hex(before['stack']),args.expected_name]
        with (folder/'stdout.log').open('wb') as out,(folder/'stderr.log').open('wb') as err:
            proc=subprocess.Popen(cmd,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
            print(json.dumps(dict(event='recorder_started_not_yet_armed',observer_pid=proc.pid,folder=str(folder))),flush=True)
            armed=False;deadline=time.monotonic()+args.seconds+20
            while proc.poll() is None:
                if not armed and trace.exists() and '"event":"armed"' in trace.read_text():
                    armed=True;print(json.dumps(dict(event='armed',folder=str(folder),expected_name=args.expected_name)),flush=True)
                if time.monotonic()>deadline:
                    Path(str(trace)+'.stop').write_text('stop',encoding='ascii')
                    raise RuntimeError(f'Cleanup still pending; do not kill observer PID {proc.pid}; trace {trace}')
                time.sleep(.1)
            code=proc.returncode
        rows=[json.loads(x) for x in trace.read_text().splitlines() if x]
        analysis=analyze_live(rows,code,before['base'],args.expected_name)
        after=None;after_error=None
        try:after=snapshot(reader,False)
        except Exception as exc:after_error=str(exc)
        bound_keys=('pid','birth','base','exe_sha256','five_known_vtable_slots')
        stable=after is not None and all(after[k]==before[k] for k in bound_keys)
        if not stable:analysis.update(classification='INCOMPLETE_OR_REJECTED',task_chain_observed=False,blockers=['post_process_code_or_resident_hook_binding_not_verified'])
        result=dict(recorder_exit=code,analysis=analysis,binding_stable=stable,after=after,after_error=after_error,trace=str(trace),game_writes=0,live_authority=False)
        (folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8')
        print(json.dumps(dict(folder=str(folder),**result),indent=2),flush=True)
    finally:reader.close()


if __name__=='__main__':main()
