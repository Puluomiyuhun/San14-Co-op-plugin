"""Freeze the completed one-shot evidence and the user's ruler observation."""
from datetime import datetime
import json
import shutil
from pathlib import Path
from start_startup_switch import ROOT,load,save,sha
from analyze_startup_switch import validate_trace

def main():
    meta=load(ROOT/'startup-switch-active.json');folder=Path(meta['directory'])
    result=load(ROOT/'startup-switch-live-result.json');assert result['directory']==str(folder)
    rows=[json.loads(line) for line in (folder/'trace.jsonl').read_text(encoding='utf-8').splitlines()]
    validate_trace(rows)
    assert sha(ROOT/'startup_identity_switch.exe')==meta['binary_sha256']
    journal=load(ROOT/'startup-switch-live-once.json')
    assert journal=={'stage':'INTENT','pid':meta['pid'],'source_force':12,'target_force':2,'automatic_retry_allowed':False}
    observation={'schema':'san14.startup-ui-observation.v1','created':datetime.now().astimezone().isoformat(),
                 'directory':str(folder),'source':'user_message','user_text':'牛逼！进入后是刘备了',
                 'displayed_ruler_confirmed':'刘备','city_menu_permissions_verified':False,
                 'reward_selection_verified':False,'events_verified':False,
                 'scope':'Only the displayed ruler has been confirmed by the user; the separate menu check is pending.'}
    dest=folder/'user-ruler-observation.json'
    if dest.exists():
        old=load(dest);assert old['user_text']==observation['user_text'] and old['directory']==str(folder)
    else:save(dest,observation)
    files=['startup_identity_switch.exe','startup_identity_switch.cpp','startup_identity_switch.inc',
           'startup_switch_profile.h','startup-switch-profile.json','startup-load-boundary-baseline.json',
           'startup-switch-fixture-tests.json','startup-switch-lifecycle-tests.json','startup-switch-analysis-tests.json',
           'startup-switch-idle-check.json','load-boundary-baseline-tests.json','analyze_startup_switch.py',
           'prepare_load_boundary_baseline.py','audit_city_identity_effects.py','city-identity-effects-audit.json']
    artifacts=folder/'artifacts';artifacts.mkdir(exist_ok=True)
    for name in files:
        source=ROOT/name;target=artifacts/name
        if target.exists():assert sha(target)==sha(source),f'Existing artifact differs: {name}'
        else:shutil.copy2(source,target)
    save(folder/'artifact-manifest.json',{n:sha(artifacts/n) for n in files})
    print(json.dumps({'result':'REAL_HANDOFF_EVIDENCE_PRESERVED','native_force':2,'user_displayed_ruler':'刘备',
                      'archived_artifacts':len(files),'menus_pending':True,'city_differences_pending':True},ensure_ascii=False))

if __name__=='__main__':main()
