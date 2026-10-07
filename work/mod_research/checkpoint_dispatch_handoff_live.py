"""Read-only, bounded idle-User hardware trace. Default is offline preparation.

--record is the only path which opens the game. No gameplay input, game routine,
file save/load, vtable write or instruction patch is issued. A Windows debugger
temporarily stops threads at selected execution instructions and restores DRs.
"""
from pathlib import Path
from datetime import datetime
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import struct
import subprocess
import sys
import copy
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import checkpoint_dispatch_handoff_probe as offline
EXE_SHA = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
ANCHORS = tuple(offline.TAPS) + (0x50B782, 0x834B7B)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def birth(handle):
    k=C.WinDLL('kernel32', use_last_error=True)
    k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4
    k.GetProcessTimes.restype=W.BOOL
    times=(W.FILETIME*4)()
    if not k.GetProcessTimes(handle,*[C.byref(times[n]) for n in range(4)]):
        raise OSError(C.get_last_error(), 'GetProcessTimes')
    return (times[0].dwHighDateTime<<32)|times[0].dwLowDateTime


def analyze_live(rows,recorder_exit=None):
    terminal=[r for r in rows if r.get('event') in ('detached','error_cleanup','process_exit')]
    base=dict(live_authority=False, scheduler_fence=False, task_chain_observed=False)
    if any(r.get('event')=='error' for r in rows): return dict(base,classification='REJECTED',blockers=['recorder_error'])
    if recorder_exit!=0:
        return dict(base,classification='INCOMPLETE',blockers=['recorder_exit_zero_required'])
    if not terminal or terminal[-1].get('event')!='detached' or not terminal[-1].get('registers_restored') or not terminal[-1].get('owned_queue_drained'):
        return dict(base,classification='INCOMPLETE',blockers=['no_verified_detach'])
    verified=[r for r in rows if r.get('event')=='restore_verified']
    if not verified or not verified[-1].get('all_six_debug_registers') or not verified[-1].get('owned_queue_drained'):
        return dict(base,classification='INCOMPLETE',blockers=['no_six_DR_readback'])
    samples=[r for r in rows if 'seq' in r]
    if any(type(r['seq']) is not int for r in samples) or [r['seq'] for r in samples]!=list(range(1,len(samples)+1)):
        return dict(base,classification='REJECTED',blockers=['native_sequence_gap_duplicate_or_reorder'])
    fresh=[r for r in samples if r['event']=='new_pool_selection']
    dispatch=[r for r in samples if r['event']=='user_update_dispatch']
    if len(fresh)!=1 or len(dispatch)!=1:
        return dict(base,classification='INCOMPLETE',blockers=['fresh_admission_and_actual_User_dispatch_required'])
    body=dispatch[0]
    selected=[r for r in samples if r['event'] in offline.CHAIN]
    if len(selected)!=8 or not fresh[0]['seq']<selected[0]['seq']<body['seq']<selected[2]['seq']:
        return dict(base,classification='INCOMPLETE',blockers=['native_chain_or_body_order'])
    if body.get('rva')!='0x50b782' or any(body.get(k)!=selected[1].get(k) for k in ('worker','state','callable','native_thread','thread')):
        return dict(base,classification='REJECTED',blockers=['User_body_dispatch_binding'])
    if any(r.get('callable_entry')!=r.get('module_base',0)+0x50B730 for r in selected):
        return dict(base,classification='REJECTED',blockers=['callable_entry_build_binding'])
    # 50B598 precedes 834B60. A reused pool worker can still have done=1;
    # 834B7B clears it before signalling activation. Preserve raw evidence;
    # only adapt this pre-start field to the older VM analyzer's zero-initialized
    # pool fixture. All seven later task samples retain their original values.
    initial_done=selected[0].get('done')
    if initial_done not in (0,1): return dict(base,classification='REJECTED',blockers=['invalid_prestart_done'])
    adapted=copy.deepcopy([r for r in samples if r['event']!='user_update_dispatch'])
    next(r for r in adapted if r['event']=='state_attached')['done']=0
    result=offline.analyze(adapted)
    result['raw_prestart_done']=initial_done
    result['adaptation']='Only pre-start done at 50B598; subsequent worker-entry done must be zero.'
    return result


def snapshot(reader):
    m=reader.memory; q=lambda p:struct.unpack('<Q',m.read(p,8))[0]
    u=lambda p:struct.unpack('<I',m.read(p,4))[0]
    states=reader.state_objects()
    if [x[0] for x in states]!=['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']:
        raise RuntimeError('Not idle five-state formal User')
    user=states[-1][1]; stack=q(m.base+0x19E7310+0x20)
    if q(m.base+0x19E7310+0x30) or u(user+0x470)!=2 or u(user+0x68):
        raise RuntimeError('User phase/pending transition is not supported')
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    if hashlib.sha256(image).hexdigest()!=offline.IMAGE_SHA: raise RuntimeError('Archived build changed')
    for rva in ANCHORS:
        if m.read(m.base+rva,32)!=image[rva:rva+32]: raise RuntimeError(f'Code changed at {rva:x}')
    root=q(m.base+0x1FCA1E0);world=q(root+0x85130)
    # Existing resident V2 forwards are permitted. We only snapshot their values.
    slots=(0x12CC4D0,0x12DB4E8,0x12CC9E0,0x12DBD90,0x138E8D0)
    return dict(pid=reader.pid,birth=birth(m.handle),base=m.base,exe_sha256=reader.sha256,
                user=user,stack=stack,states=states,world=world,
                date_player_hex=m.read(world+0x34,8).hex(),world_mode=u(world+0x40),
                five_known_vtable_slots={hex(rva):q(m.base+rva) for rva in slots})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record',action='store_true')
    parser.add_argument('--pid',type=int)
    parser.add_argument('--seconds',type=int,default=8)
    parser.add_argument('--analyze',type=Path)
    args=parser.parse_args()
    if args.analyze:
        result_file=args.analyze.parent/'result.json'
        recorded_exit=json.loads(result_file.read_text()).get('recorder_exit') if result_file.is_file() else None
        print(json.dumps(analyze_live([json.loads(x) for x in args.analyze.read_text().splitlines() if x],recorded_exit),indent=2));return
    if not args.record:
        print(json.dumps(dict(mode='offline_prepare',game_access=False,production_admission=False,
            native_taps=offline.decode_profile(),extra_actual_User_call_tap='0x50B782',
            title_mode='not_enabled; owned Title+520/+590 pairing belongs to a later recorder mode',
            exe_sha256=EXE_SHA,recorder_sha256=sha(ROOT/'checkpoint_dispatch_handoff_live.exe')),indent=2));return
    if not 1<=args.seconds<=30: raise ValueError('seconds must be 1..30')
    sys.path.insert(0,str(ROOT.parent.parent/'outputs/san14-link'))
    from game_reader import GameReader
    reader=GameReader(args.pid)
    try:
        before=snapshot(reader)
        if before['exe_sha256']!=EXE_SHA: raise RuntimeError('Unsupported executable')
        folder=ROOT/'checkpoint_dispatch_handoff_live_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        folder.mkdir(parents=True)
        trace=folder/'trace.jsonl';binary=ROOT/'checkpoint_dispatch_handoff_live.exe'
        meta=dict(mode='idle_user',before=before,recorder_sha256=sha(binary),
                  seconds=args.seconds,game_writes=0,live_authority=False,
                  title_mode_enabled=False,native_sequence='debug-event processing before ContinueDebugEvent',
                  limitations=['Debug stops perturb timing.','One observed state task is not a scheduler fence.'])
        (folder/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
        command=[str(binary),str(reader.pid),hex(before['base']),'0x50b4b3',str(args.seconds),str(trace),
                 str(before['birth']),hex(before['user']),hex(before['stack'])]
        with (folder/'stdout.log').open('wb') as out,(folder/'stderr.log').open('wb') as err:
            proc=subprocess.Popen(command,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
            try: code=proc.wait(timeout=args.seconds+15)
            except subprocess.TimeoutExpired:
                Path(str(trace)+'.stop').write_text('stop',encoding='ascii')
                # Never terminate a debugger process as an automatic workaround.
                raise RuntimeError(f'Recorder did not exit; stop requested, PID {proc.pid}, trace {trace}')
        after=snapshot(reader)
        rows=[json.loads(x) for x in trace.read_text().splitlines() if x]
        result=dict(recorder_exit=code,analysis=analyze_live(rows,code),before_after_equal=before==after,
                    after=after,trace=str(trace),game_writes=0,live_authority=False)
        if before!=after: result['analysis']=dict(classification='REJECTED',task_chain_observed=False,
            live_authority=False,scheduler_fence=False,blockers=['bound_sample_changed'])
        (folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8')
        print(json.dumps(dict(folder=str(folder),**result),indent=2))
    finally: reader.close()


if __name__=='__main__': main()
