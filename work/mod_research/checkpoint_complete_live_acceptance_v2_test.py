"""Focused V2 regressions, synthetic success only; never rewrites a live report."""
import copy,datetime,hashlib,json
from pathlib import Path
from checkpoint_complete_live_acceptance_test import synthetic,report_bytes,sync_pods
from checkpoint_complete_live_owner_contract import decode_report
from checkpoint_complete_live_acceptance import validate_report as v1
from checkpoint_complete_live_acceptance_v2 import validate_report as v2
P=Path(__file__).resolve().parent

def main():
    data,kw,_=synthetic();rows=[]
    for mode in ('distinct_addresses','new_game_reuses_load','new_user_reuses_title'):
        r=copy.deepcopy(data)
        if mode=='new_game_reuses_load':
            for key in ('planningBeforeSample','planningAfterSample'):r[key]['states'][2]=r['lifecycle']['load']
        if mode=='new_user_reuses_title':
            r['planningUser']=r['identity']['title'];r['PlanningUserReused']=int(r['planningUser']==kw['planning']['states'][4])
            for key in ('planningBeforeSample','planningAfterSample'):r[key]['states'][4]=r['planningUser']
        sync_pods(r);decoded=decode_report(report_bytes(r));accepted=v2(decoded,**kw)
        assert accepted['result']=='PASS_NATIVE_LOAD_IDENTITY_PLANNING' and not accepted['ready_authorized']
        if mode!='distinct_addresses':
            try:v1(decoded,**kw)
            except ValueError as exc:assert 'historical loading' in str(exc)
            else:raise AssertionError('V1 reproducer did not reject reused address')
        rows.append(dict(case=mode,passed=True,synthetic_only=True))
    for field in ('PlanningError','GuardError','BytesError','ReadyAuthorized'):
        r=copy.deepcopy(data);r[field]=1
        try:v2(decode_report(report_bytes(r)),**kw)
        except ValueError:pass
        else:raise AssertionError('V2 accepted bad proof '+field)
        rows.append(dict(case='reject_'+field,passed=True))
    run=P/'checkpoint_complete_live_runs/20261007-154025-966862'
    actual=json.loads((run/'trace.json').read_text('utf8'))[-1]
    claim=json.loads((run/'result.json').read_text('utf8'));b=json.loads((run/'bindings.json').read_text('utf8'))
    actual_kw=dict(base=claim['base'],attempt=claim['attempt'],epoch=claim['epoch'],generation=claim['generation'],
        attachment_hex=claim['attachment'],description=json.loads((run/'description.json').read_text('utf8')),
        planning=b['planning'],storage=b['storage'])
    try:v2(actual,**actual_kw)
    except ValueError as exc:assert 'PlanningError' in str(exc)
    else:raise AssertionError('V2 must not relabel the failed actual observation as success')
    rows.append(dict(case='real_incomplete_attempt_remains_rejected',passed=True,actual_report_mutated=False))
    folder=P/'checkpoint_complete_live_acceptance_v2_runs'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    result=dict(passed=True,cases=rows,game_access=False,actual_attempt_still_incomplete=True,
        source_sha256={name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in
            ('checkpoint_complete_live_acceptance_v2.py','checkpoint_complete_live_acceptance_v2_test.py')})
    (folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(dict(passed=True,cases=len(rows),path=str(folder/'result.json'))))

if __name__=='__main__':main()
