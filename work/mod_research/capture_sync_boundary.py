"""Read-only candidate boundary probe. A quiet sample is NOT a proven barrier."""
import argparse,json,struct,time
from pathlib import Path
from lockstep_baseline import BattleObserver,sample
from finalize_lockstep_capture import diagnostics
ROOT=Path(__file__).resolve().parent
PLANNING=['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']

def person_line_queue(r):
    m=r.memory;base=m.base;manager=base+0x1A38EC8
    r.require_type(manager,'CPersonLineManager')
    def u64(a):return struct.unpack('<Q',m.read(a,8))[0]
    def u32(a):return struct.unpack('<I',m.read(a,4))[0]
    raw=m.read(manager,0x30);handle=struct.unpack_from('<Q',raw,0x10)[0]
    registry_guard=u64(base+0x201D3A8);table=u64(base+0x201D3B0);capacity=u32(base+0x201D3E0)
    assert handle and registry_guard and table and 0<capacity<=0x20000,'Uninitialized/unknown registry'
    index=u32(handle);assert index<capacity,'Invalid person-line registry index'
    head=u64(table+index*8);node=head;seen=set();items=[]
    while node:
        assert node not in seen and len(seen)<4096,'Queue cycle or bound exceeded'
        seen.add(node);item=u64(node);next_node=u64(node+8);v=m.read(item,0x30)
        items.append({'node':hex(node),'item':hex(item),'kind_0':struct.unpack_from('<I',v)[0],
            'field_4':struct.unpack_from('<I',v,4)[0],'person_candidate_8':struct.unpack_from('<I',v,8)[0],
            'field_c':struct.unpack_from('<I',v,12)[0],'field_10':struct.unpack_from('<I',v,16)[0],
            'delay_counter_1c':v[0x1c],'age_counter_20':struct.unpack_from('<i',v,0x20)[0],
            'display_object_present':bool(struct.unpack_from('<Q',v,0x28)[0]),'raw_hex':v.hex()})
        node=next_node
    assert raw==m.read(manager,0x30) and head==u64(table+index*8),'Queue changed during traversal'
    return {'index':index,'head':hex(head),'items':items,'count':len(items),
        'manager_block_28':struct.unpack_from('<I',raw,0x28)[0],
        'scope':'Known CPersonLineManager list only. Serial reads, no atomic barrier or exhaustive queue inventory.'}

def capture(r):
    b=sample(r);q=person_line_queue(r);d=diagnostics(r)
    assert b==sample(r),'Gameplay changed while reading candidate boundary'
    conditions={'planning_stack':b['focused']['state_stack']==PLANNING,
        'known_person_line_queue_empty':q['count']==0,'known_person_line_block_clear':q['manager_block_28']==0,
        'known_battle_worker_clear':d['battle_manager_1a24cf0']['worker_90']==0,
        'known_battle_pending_clear':d['battle_manager_1a24cf0']['pending_94']==0,
        'known_effect_pending_clear':d['effects_1a38a20']['pending_98']==0,
        'known_effect_list_empty':d['effects_1a38a20']['count_38']==0}
    return {'conditions':conditions,'candidate_idle':all(conditions.values()),'person_line_queue':q,
        'diagnostics':d,'random_inputs':b['random_inputs'],'state_stack':b['focused']['state_stack'],
        'date':b['focused']['critical_state']['date'],'sampled_records':len(b['records'])}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name');a=p.parse_args();assert a.name.replace('-','').isalnum()
    dest=ROOT/'lockstep-traces'/(a.name+'.json');assert not dest.exists()
    r=BattleObserver()
    try:
        start=sample(r);observations=[capture(r) for _ in range(3)];end=sample(r)
        result={'observations':observations,'stable_samples':all(x==observations[0] for x in observations),
            'gameplay_sample_unchanged':start==end,'certified_sync_barrier':False,
            'scope':'Three immediate read-only samples of known fields. Empty now does not prevent future enqueue or prove no worker is executing; do not normalize RNG based on this alone.'}
        dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'path':str(dest),'stable_samples':result['stable_samples'],
            'candidate_idle':observations[-1]['candidate_idle'],'certified_sync_barrier':False,
            'known_person_line_queue_count':observations[-1]['person_line_queue']['count'],'random_inputs':end['random_inputs']},ensure_ascii=True))
    finally:r.close()
