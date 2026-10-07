"""Separate process DLL/vtable callback tests; does not access SAN14."""
from datetime import datetime
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
folder=ROOT/'auto_cache_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
cases=('execute','dry','wrong_mode','wrong_pending','cache_nonempty','list_nonempty','wrong_date','wrong_phase','wrong_code','pending_state_command','wrong_metadata','existing_journal','repeat_install','cancel','state_changed_after_install','scanner_exception','world_mutation','missing_slot34','reentrant_update','bad_magic')
rows=[]
for case in cases:
    journal=folder/(case+'.once.json');report=folder/(case+'.report.bin')
    proc=subprocess.run([str(ROOT/'auto_cache_fixture.exe'),str(ROOT/'auto_cache_fixture.dll'),case,str(journal),str(report)],capture_output=True,text=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    (folder/(case+'.stdout')).write_text(proc.stdout,encoding='utf-8');(folder/(case+'.stderr')).write_text(proc.stderr,encoding='utf-8')
    assert proc.returncode==0,(case,proc.returncode,proc.stdout,proc.stderr)
    row=json.loads(proc.stdout);assert row['result']=='PASS' and row['game_process_access'] is False
    assert report.stat().st_size==144,(case,report.stat().st_size)
    if row['intent_created']:assert journal.exists() and json.loads(journal.read_text())['status']=='intent_uncertain_no_auto_retry'
    elif case=='existing_journal':assert journal.read_bytes()==b'prior'
    else:assert not journal.exists(),case
    row['case']=case;rows.append(row);print(json.dumps({'case':case,'result':'PASS'}),flush=True)
result={'result':'PASS','created':datetime.now().astimezone().isoformat(),'directory':str(folder),'dll_sha256':hashlib.sha256((ROOT/'auto_cache_pilot.dll').read_bytes()).hexdigest(),'fixture_dll_sha256':hashlib.sha256((ROOT/'auto_cache_fixture.dll').read_bytes()).hexdigest(),'cases':rows,'retained_native_hint_fields_accepted':{'3e8':56,'3f8':114},'scope':'Actual DLL installation, atomic vtable hook/restoration, native update callback and copied three-byte parameter helper in isolated processes. Scanner callback is synthetic, so this does not prove native file parsing or current-game scan safety. World guard compares only CWorld[0..0x2200) and one RNG value, not full world.'}
(ROOT/'auto_cache_test_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','cases':len(rows),'game_access':False}))
