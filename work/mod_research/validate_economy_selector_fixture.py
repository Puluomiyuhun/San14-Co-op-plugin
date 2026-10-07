"""Run independent local A/B fixtures and compare copied native arithmetic."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
save=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    folder=ROOT/'economy-selector-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    binary=ROOT/'economy_selector_fixture.exe'
    def run(viewer):
        path=folder/f'viewer-{viewer}.json'
        proc=subprocess.run([str(binary),str(viewer),str(path)],capture_output=True,text=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
        assert proc.returncode==0,(viewer,proc.returncode,proc.stderr,proc.stdout)
        row=load(path)
        assert row['viewer']==viewer and row['result']=='PASS' and row['cases']==4896
        assert row['guard_cases']==36 and row['native_local_predicate_cases']==51
        assert row['hook_calls']==2*row['cases'] and not row['game_access'] and not row['full_city_calculation']
        return row
    with ThreadPoolExecutor(max_workers=2) as executor:a,b=list(executor.map(run,[12,2]))
    assert a['pid']!=b['pid']
    native_mismatches=[];shared_matches=0;ai_unchanged=0
    for x,y in zip(a['rows'],b['rows'],strict=True):
        assert len(x)==len(y)==6 and x[:4]==y[:4]
        assert x[5]==y[5],('adapted values differ',x,y)
        shared_matches+=1
        if x[4]!=y[4]:
            assert x[2] in (2,12);native_mismatches.append({'input':x[:4],'native_a':x[4],'native_b':y[4],'adapted_both':x[5]})
        if x[2] not in (2,12):
            assert x[4]==y[4]==x[5]==y[5];ai_unchanged+=1
    assert shared_matches==4896 and native_mismatches and ai_unchanged==4704
    artifacts=folder/'artifacts';artifacts.mkdir()
    paths=[binary,ROOT/'economy_selector_fixture.cpp',ROOT/'economy_selector_fixture_code.h',
           ROOT/'make_economy_selector_fixture.py',ROOT/'economy-selector-native-source.json',
           ROOT/'build_economy_selector_fixture.cmd',ROOT/'validate_economy_selector_fixture.py',
           ROOT.parents[1]/'outputs/san14-link/human_economy_policy.h']
    for path in paths:shutil.copy2(path,artifacts/path.name)
    report={'schema':'san14.economy-selector-tests.v1','created':datetime.now().astimezone().isoformat(),
            'result':'PASS','directory':str(folder),'binary_sha256':sha(binary),
            'paired_separate_processes':[{'viewer':r['viewer'],'pid':r['pid']} for r in (a,b)],
            'native_selector_cases_per_viewer':4896,'native_viewer_dependent_pairs':len(native_mismatches),
            'adapted_equal_pairs':shared_matches,'nonhuman_pairs_unchanged':ai_unchanged,
            'guard_and_unclassified_caller_checks':a['guard_cases']+b['guard_cases'],
            'original_local_predicate_checks':a['native_local_predicate_cases']+b['native_local_predicate_cases'],
            'examples':native_mismatches[:4],'native_sources':load(ROOT/'economy-selector-native-source.json'),
            'sources_sha256':{p.name:sha(p) for p in paths},'game_access':False,
            'live_adapter_installed':False,'full_city_delta_replay_verified':False,'two_real_game_clients_verified':False,
            'scope':'Two independent fixture processes execute copied percentage-selection tails with explicit settings/region lookup stubs. Real upstream income/expense calculation, city writes and network integration are not included.'}
    save(folder/'result.json',report);save(ROOT/'economy-selector-test-results.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('native_sources','sources_sha256','scope','examples')},ensure_ascii=False))

if __name__=='__main__':main()
