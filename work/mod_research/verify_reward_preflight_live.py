"""Read-only current-state positive/negative reward command preflight evidence."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT.parents[1]/'outputs'/'san14-link'
sys.path.insert(0,str(OUTPUT))
from battle_observer import BattleObserver
from reward_preflight import capture_context,eligible_ids,make_command,validate_reward,PreflightError
from pilot_evidence import check_checkpoint,check_restored,load_json

def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

reader=BattleObserver()
try:
    run=ROOT/'reward-preflight-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    baseline=reader.capture();check_restored(load_json(ROOT/'before-native-submit.json'),baseline)
    context=capture_context(reader);force=context['current_player_force_id'];district=context['main_district_id']
    command=make_command(context,district,eligible_ids(context,district))
    preview=validate_reward(command,context,force)
    save(run/'context.json',context);save(run/'preview.json',preview)
    negatives=[]
    for name,field,value,expected in [
        ('duplicate_officer','officer_ids',[97,97],'duplicate_officer'),
        ('declared_other_force','force_id',2,'authorization'),
        ('wrong_funding_city','funding_city_id',18,'funding_city'),
        ('deployed_officer','officer_ids',[166],'officer_ineligible'),
        ('empty_selection','officer_ids',[],'officer_ids'),
        ('boolean_officer','officer_ids',[True],'officer_ids'),
    ]:
        candidate=deepcopy(command);candidate[field]=value
        try:validate_reward(candidate,context,force)
        except PreflightError as error:
            assert error.code==expected
            negatives.append({'case':name,'result':'CORRECTLY_REJECTED','code':error.code})
        else:raise RuntimeError(f'Unexpectedly accepted {name}')
    local_command=make_command(context,9,eligible_ids(context,9))
    local_preview=validate_reward(local_command,context,force)
    after_context=capture_context(reader);after=reader.capture()
    assert context==after_context
    comparison=check_restored(baseline,after)
    check_checkpoint(Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14'))
    fixtures=load_json(ROOT/'reward-preflight-fixtures.json');assert fixtures['result']=='PASS' and fixtures['tests_run']==30
    report={'result':'PASS','stage':'READ_ONLY_REWARD_COMMAND_PREFLIGHT','directory':str(run),
            'offline_fixture_tests':30,'read_only_positive_cases':2,'read_only_rejection_cases':negatives,
            'main_district_preview':preview,'other_own_district_preview':local_preview,
            'context_stable':True,'focused_state_comparison':comparison,'checkpoint34_unchanged':True,
            'native_functions_called':False,'new_dll_loaded':False,'game_orders_executed':0,
            'domestic_network_execution_enabled':False,'two_client_multiplayer':False,
            'scope':'Read-only preflight on current snapshot; native execution, recovery and two-player permission context unverified'}
    save(run/'result.json',report);save(OUTPUT/'赏赐命令预检验证.json',report)
    save(OUTPUT/'最近一次赏赐预检.json',preview)
    save(run/'after.json',after)
    print(json.dumps({'result':'PASS','offline_tests':30,'live_readonly_positive_cases':2,
                      'live_readonly_negative_cases':len(negatives),
                      'main_district_costs':preview['expected_costs'],
                      'other_district_costs':local_preview['expected_costs'],
                      'game_orders_executed':0,'state_unchanged':True},ensure_ascii=True,indent=2))
finally:reader.close()
