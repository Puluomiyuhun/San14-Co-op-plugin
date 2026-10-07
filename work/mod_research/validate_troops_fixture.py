"""Correlate read-only live data plus edge cases with copied native query code."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs' / 'san14-link'
sys.path.insert(0, str(OUT))
from battle_observer import BattleObserver
from troops_reader import capture_model, resolve_groups
from run_second_force_reward import capture as world_capture
from make_troops_fixture import BLOCKS


def empty():
    return {'armies': [{'id': i, 'flag': 0, 'leader': 0, 'group': 0} for i in range(501)],
            'persons': {i: {'slot': i, 'id': i, 'district': 0, 'rank': 0} for i in [0, 1, 2, 6000]},
            'districts': [{'id': i, 'force': 0, 'kind': 0, 'leader': 0} for i in range(52)],
            'order': [], 'excluded': [], 'relations': []}


def standard():
    m = empty()
    for identity, district, force in [(1, 11, 12), (2, 2, 2)]:
        m['persons'][identity].update(district=district, rank=2)
        m['armies'][identity].update(flag=1, leader=identity, group=1)
        m['districts'][district].update(force=force, kind=1, leader=identity)
    m['order'] = [1, 2]
    return m


def scenarios():
    cases = []
    def add(name, model, expected, group=1):
        assert resolve_groups(model)[group]['district_id'] == expected, name
        cases.append((name, model))
    add('empty', empty(), 0)
    add('first_in_list', standard(), 11)
    m=standard();m['order'].reverse();add('reversed_order', m, 2)
    m=standard();m['persons'][1]['rank']=0;add('invalid_first_no_fallback', m, 0)
    m=standard();m['armies'][1]['flag']=0;add('membership_does_not_test_army_validity', m, 11)
    m=standard();m['excluded']=[1];add('explicit_exclusion_uses_next', m, 2)
    m=standard();m['excluded']=[1,2];add('all_explicitly_excluded', m, 0)
    for group in [0, 500, 501, 65535]:
        m=standard();m['armies'][1]['group']=group;m['order']=[1]
        add(f'group_id_{group}', m, 11 if group==500 else 0, 500 if group==500 else 0)
    for leader in [0,6000,6001,65535]:
        m=standard();m['armies'][1]['leader']=leader;add(f'leader_id_{leader}', m, 0)
    for special in [5000,5001,5100,5101]:
        m=standard();m['persons'][special]={'slot':special,'id':special,'district':11,'rank':0};m['armies'][1]['leader']=special
        add(f'special_validity_{special}', m, 11 if 5001<=special<=5100 else 0)
    for force in [0,2,45,46,47,48,49,50,51,52,255]:
        m=standard();m['districts'][11]['force']=force;m['relations']=[[None,2,1]]
        add(f'relation_third_force_{force}', m, 11 if 46<=force<=51 else 2)
    for column in ['kind','leader']:
        m=standard();m['districts'][11][column]=0;m['relations']=[[None,2,1]]
        add(f'relation_third_invalid_district_{column}',m,2)
    m=standard();m['relations']=[[1,None,None]];add('relation_first_alone',m,2)
    m=standard();m['relations']=[[1,None,None]];m['armies'][1]['flag']=0;add('relation_first_invalid',m,11)
    m=standard();m['relations']=[[None,None,1]];add('relation_second_null',m,11)
    m=standard();m['relations']=[[None,0,1]];add('relation_second_sentinel',m,11)
    m=standard();m['relations']=[[None,2,1]];m['armies'][2]['flag']=0;add('relation_second_invalid',m,11)
    m=standard();m['relations']=[[None,2,1]];m['armies'][1]['flag']=0;add('relation_third_invalid',m,11)
    m=standard();m['persons'][1]['district']=255;add('raw_out_of_range_district_preserved',m,255)
    m=standard();m['relations']=[[None,2,None],[1,None,None]];add('multiple_relations',m,2)
    return cases


def write_cases(cases, path):
    lines=[str(len(cases))]
    for name,m in cases:
        lines.append(str(len(m['persons'])))
        lines.extend(f"{i} {p['id']} {p['district']} {p['rank']}" for i,p in sorted(m['persons'].items()))
        lines.extend(f"{a['flag']} {a['leader']} {a['group']}" for a in m['armies'])
        lines.extend(f"{d['force']} {d['kind']} {d['leader']}" for d in m['districts'])
        for key in ['order','excluded']:
            lines.append(' '.join(map(str,[len(m[key]),*m[key]])))
        lines.append(str(len(m['relations'])))
        lines.extend(' '.join(str(-1 if value is None else value) for value in row) for row in m['relations'])
        lines.append(' '.join(str(g['district_id']) for g in resolve_groups(m)))
    path.write_text('\n'.join(lines)+'\n',encoding='ascii')


def main():
    reader=BattleObserver()
    try:
        before=world_capture(reader)
        model=capture_model(reader)
        assert model==capture_model(reader), 'Unstable native group input'
        original=(ROOT/'game-runtime-image.bin').read_bytes()
        for _,a,z,_ in BLOCKS:
            assert reader.memory.read(reader.memory.base+a,z-a)==original[a:z], f'Native query changed at {a:#x}'
        cases=scenarios()+[('live_planning_snapshot',model)]
        case_path=ROOT/'troops-native-cases.txt';write_cases(cases,case_path)
        run=subprocess.run([str(ROOT/'troops_fixture.exe'),str(case_path)],capture_output=True,text=True,check=True)
        native=json.loads(run.stdout)
        assert native['result']=='PASS' and native['native_getter_comparisons']==501*len(cases)
        assert before==world_capture(reader), 'Observed world/RNG/pools changed during independent query fixture'
        rows=resolve_groups(model)
        result={'schema':'san14.troops-query-correlation.v1','created':datetime.now().astimezone().isoformat(),
                'result':'PASS','native_fixture':native,'scenario_names':[name for name,_ in cases],
                'live_group_slots_compared':501,'live_nonempty_groups':sum(bool(g['member_ids']) for g in rows),
                'live_armies':len(model['order']),'live_exclusion_list_length':len(model['excluded']),
                'live_relation_count':len(model['relations']),'live_nonempty_relations_correlated':False,
                'native_query_game_calls':0,'game_memory_writes':0,'game_hooks_installed':False,
                'sampled_world_records_unchanged':len(before['records']),'known_rng_and_pools_unchanged':True,
                'test_input_sha256':hashlib.sha256(case_path.read_bytes()).hexdigest(),
                'scope':'Ten copied transitive native query bodies execute in an independent process, with local pointer relocation and validated local virtual targets; no getter stubs. Live planning input and synthetic edge cases only. No in-game AI suppression, movement or two-client proof.'}
        (ROOT/'troops-live-model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (ROOT/'troops-fixture-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True,indent=2))
    finally:reader.close()


if __name__=='__main__':main()
