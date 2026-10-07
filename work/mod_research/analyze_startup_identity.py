"""Validate a finished load trace without inferring that identity switching works."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from run_second_force_reward import BattleObserver, capture, CHECKPOINT
from startup_identity_reader import capture_startup_context
import hashlib
import ctypes as C
from ctypes import wintypes as W

ROOT=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
save=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def validate_trace(rows):
    if not rows or rows[-1] != {'event':'detached','captured':True,'registers_restored':True}:
        raise ValueError('Trace has not finished with captured events and restored debug registers')
    if any(r['event'] in ('error','error_cleanup','process_exit') for r in rows):
        raise ValueError('Observer did not finish normally')
    events=[r for r in rows if 'seq' in r]
    if [r['seq'] for r in events] != list(range(1,len(events)+1)):
        raise ValueError('Observation sequence has gaps')
    names=('deserialize_return','load_worker_result','strategy_initialize','user_strategy_initialize','first_user_update')
    points={}
    for name in names:
        found=[r for r in events if r['event']==name]
        if len(found)!=1:
            raise ValueError(f'Expected exactly one {name}, found {len(found)}')
        points[name]=found[0]
    if [points[n]['seq'] for n in names] != sorted(points[n]['seq'] for n in names):
        raise ValueError('Unexpected startup ordering')
    if points['load_worker_result']['ebx']!=1 or not points['first_user_update']['complete_path_seen']:
        raise ValueError('Successful native load path not established')
    if events[-1]['event']!='first_user_update':
        raise ValueError('Unexpected observations after the stopping boundary')
    for name,row in points.items():
        if row.get('date') != [203,8,11] or 'world_context' not in row:
            raise ValueError(f'Missing/wrong checkpoint context at {name}')
        if row['world_context']['force']!=12:
            raise ValueError('This observation expected the unchanged Zhang Lu checkpoint')
    first=points['first_user_update'].get('state_context',{})
    if not first.get('field_478_raw') or not first.get('field_618_raw'):
        raise ValueError('Expected constructed user-state objects absent')
    return {'ordered_points':points,'identity_initializer_events':[r for r in events if r['event']=='native_identity_initializer'],
            'native_gameplay_enabled':False,'safe_identity_insertion_point_proven':False,
            'scope':'Observed ordering for one unchanged-player load. Absence of the known initializer entry does not exclude other/bulk identity writes.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path)
    args=parser.parse_args()
    folder=args.directory or Path(load(ROOT/'startup-identity-active.json')['directory'])
    meta=load(folder/'metadata.json')
    rows=[json.loads(line) for line in (folder/'trace.jsonl').read_text(encoding='utf-8').splitlines()]
    analysis=validate_trace(rows)
    reader=BattleObserver()
    try:
        current=capture(reader)
        context=capture_startup_context(reader)
        if current!=capture(reader) or context!=capture_startup_context(reader):
            raise RuntimeError('Game sample still changing; finish returning to the map first')
        k=reader.memory.k
        k.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)]
        k.CheckRemoteDebuggerPresent.restype=W.BOOL
        attached=W.BOOL()
        assert k.CheckRemoteDebuggerPresent(reader.memory.handle,C.byref(attached)) and not attached.value
        assert reader.pointer(reader.memory.base+0x12CC4A8+0x28)==reader.memory.base+0x3F9B00
        before=load(folder/'before.json')
        changes=[key for key,value in before['records'].items() if current['records'].get(key)!=value]
        save(folder/'after.json',current)
        save(folder/'context-after.json',context)
        result={'schema':'san14.startup-identity-observation.v1','created':datetime.now().astimezone().isoformat(),
                'result':'LOAD_ORDER_OBSERVED_NO_IDENTITY_CHANGE','directory':str(folder),'analysis':analysis,
                'record_comparison':{'changed_keys':changes,'sampled_keys':len(before['records']),
                    'note':'Raw army display pointers may be reconstructed by load; changed raw records are not silently normalized.'},
                'known_rng_before':before['global_rng'],'known_rng_after':current['global_rng'],
                'debugger_attached':False,'original_user_update_unchanged':True,
                'checkpoint34_unchanged':hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest()==
                    'afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95',
                'game_native_identity_calls_by_adapter':0,'game_data_writes_by_adapter':0,
                'b_faction_menu_verified':False,'current_context':context,
                'observer_sha256':meta['observer_sha256']}
        assert result['checkpoint34_unchanged']
        save(folder/'analysis.json',result)
        save(ROOT/'startup-identity-live-result.json',result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('analysis','current_context')},ensure_ascii=True,indent=2))
    finally:
        reader.close()


if __name__=='__main__':
    main()
