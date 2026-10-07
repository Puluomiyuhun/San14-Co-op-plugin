"""Compare complete emulated formulas with saved live handoff observations."""
import json, hashlib, zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
load=lambda name:json.loads((HERE/name).read_text(encoding='utf-8'))
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()

def runs(name):
    p=load(name)
    assert p['result']=='COMPLETED_SHADOW_EXECUTION',(name,p.get('error'))
    assert p['game_writes'] is False and p['native_game_calls'] is False
    assert len(p['runs'])==2 and {r['viewer'] for r in p['runs']}=={12,2}
    for r in p['runs']:
        assert r['live_shadow_allocations']==0
        assert r['events']['private_alloc']==r['events']['private_free']
    return p,{r['viewer']:r for r in p['runs']}

native,n=runs('economy-shadow-nine-cities.json')
adapt,a=runs('economy-shadow-adapted.json')
control,c=runs('economy-shadow-rounding-controls.json')
control_adapt,ca=runs('economy-shadow-adapted-controls.json')
guards=load('economy-shadow-guard-tests.json');assert guards['result']=='PASS' and guards['tests']==12
assert native['source_verification']['result']=='STABLE_READ_DEPENDENCIES'
assert native['source_verification']['changed_bytes']==0
changes=load('city-identity-effects-audit.json')['city_changes']
fields=('cost_1','income_1','cost_0','income_0','derived')
rows=[]
for city in changes:
    key=str(city['city_id']);owner=city['owner_force_id']
    expected={12:[city['field_a0'][0],city['field_a4'][0]],2:[city['field_a0'][1],city['field_a4'][1]]}
    for viewer in (12,2):
        assert n[viewer]['cities'][key]['derived']==expected[viewer]
        for f in ('cost_1','cost_0','income_0'):
            assert n[viewer]['cities'][key][f]==n[12]['cities'][key][f]
        for f in fields:
            assert a[viewer]['cities'][key][f]==n[owner]['cities'][key][f]
    rows.append({'city_id':city['city_id'],'name':city['city_name'],'owner_force':owner,
                 'observed_original_A':expected[12],'observed_original_B':expected[2],
                 'adapted_A_and_B':a[12]['cities'][key]['derived'],
                 'native_complete_formula_matches_both_live_samples':True,'adapted_pair_equal':True})
# The full area results must agree in native order, not only city totals.
assert a[12]['area_component_results']==a[2]['area_component_results']
assert len(a[12]['area_component_results'])==160
for viewer in (12,2):
    assert a[viewer]['events']['adapted_human_selector']==160
    assert all(k.endswith(':1') for k in a[viewer]['settings_query_results'])
    for key,value in a[viewer]['cities'].items():
        sums=[sum(r['result'] for r in a[viewer]['area_component_results'] if r['city_id']==int(key) and r['component']==component) for component in (0,1)]
        assert sums==value['income_1']
    for f in fields:
        assert c[viewer]['cities']['12'][f]==c[12]['cities']['12'][f]==ca[viewer]['cities']['12'][f]
    assert c[viewer]['cities']['12']['derived']==c[viewer]['cities']['12']['stored']
lujiang=[]
for component in (0,1):
    source=[r for r in c[12]['area_component_results'] if r['city_id']==13 and r['component']==component]
    target=[r for r in c[2]['area_component_results'] if r['city_id']==13 and r['component']==component]
    assert [r['area_id'] for r in source]==[r['area_id'] for r in target]
    assert all(y['result']==x['result']*150//100 for x,y in zip(source,target))
    total1=sum(r['result'] for r in source);total2=sum(r['result'] for r in target)
    assert total1==c[12]['cities']['13']['income_1'][component]
    assert total2==c[2]['cities']['13']['income_1'][component]
    lujiang.append({'component':component,'AI_region_values':[r['result'] for r in source],
                   'human_region_values':[r['result'] for r in target],
                   'AI_sum':total1,'human_sum_after_per_region_truncation':total2,
                   'incorrect_aggregate_multiply':total1*150//100})
with zipfile.ZipFile(HERE/'economy-shadow-nine-cities.zip') as z:metadata=json.loads(z.read('metadata.json'))
assert all(pool['two_equal_copies'] for pool in metadata['pool_captures'])
files=['economy-shadow-nine-cities.zip','economy-shadow-nine-cities.json','economy-shadow-adapted.json',
       'economy-shadow-rounding-controls.json','economy-shadow-adapted-controls.json','economy-shadow-guard-tests.json']
result={'schema':'san14.economy-shadow-verification.v1','result':'PASS_EXACT_CITY_DELTAS_AND_SHARED_HUMAN_PREVIEW',
        'exact_observed_delta_fields':18,'native_observed_city_values_matched':36,
        'shared_human_city_pairs_equal':9,'shared_human_area_component_pairs_equal':160,
        'other_force_full_city_control':{'city_id':12,'force_id':11,'four_variants_equal':True,'derived':[-1002,-2633]},
        'current_settings_key_5':1,'settings_ui_label_verified':False,
        'current_native_percentages':{'human':150,'AI':100},'cities':rows,'rounding_example_lujiang':lujiang,
        'source_verification':native['source_verification'],'pool_captures':metadata['pool_captures'],
        'guard_tests':guards,'source_sha256':{name:sha(HERE/name) for name in files},
        'executed_entry_rvas':['0x2fc850','0x20d3b0','0x20b290'],
        'economic_query_substitutions':[],
        'runtime_substitutions':['Single-thread critical-section/SRW lock operations',
            'Synthetic thread ID used by private lock bookkeeping','Private heap allocation/free wrappers',
            'Already initialized settings singleton accessor (TLS guard bypass after checking its initialized flag)',
            'Precommitted emulated stack probe','Two REP STOSB fills implemented equivalently in private memory'],
        'candidate_rule_change':'Only native 2110B0 calls returning to 28DE76 or 28DAAA use room human set {12,2}',
        'live_game_code_or_data_written':False,'real_game_functions_invoked':False,
        'turn_settlement_verified':False,'all_economic_paths_verified':False,'all_51_cities_verified':False,
        'live_patch_installed':False,'two_real_clients_verified':False,'full_world_lockstep_verified':False,
        'scope':'One saved world and current setting. Complete preview income/cost entry points and their native economic dependencies were emulated; OS/allocation plumbing was modeled. No real settlement or full startup routine was executed.'}
(HERE/'economy-shadow-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ('result','exact_observed_delta_fields','shared_human_city_pairs_equal','shared_human_area_component_pairs_equal')},ensure_ascii=False))
