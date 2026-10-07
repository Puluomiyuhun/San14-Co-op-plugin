"""Isolated private-process fixtures only; never opens SAN14 or Steam saves."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
CASES=('dry','queue','slot34','slot49','wrong-filename','wrong-date','wrong-phase','wrong-owner','wrong-ruler',
       'busy-queue','busy-request','existing-local','late-local','remote-exists','remote-unavailable',
       'storage-phase-drift','intent-exists','cancel','original-drift','binder-mismatch','queue-failure','binder-exception',
       'native-failure','globals-not-cleared','wrong-save-object','request-replaced','bad-save-phase','save-stall',
       'slot0','slot50','slot119','bad-magic','reserved-nonzero','cache-pending-load','world-mode',
       'heap-name-dry','heap-name-queue','heap-both-queue','heap-null','heap-unterminated','heap-bad-cap','heap-bind-mismatch',
       'empty-vector-dry','empty-vector-queue','heap-empty-vector-queue','null-vector-with-capacity','zero-capacity-with-pointer','oversized-vector','bad-allocator-type','bad-allocator-method')
CASES+=('cache-mode-one','selected-object','advance-pending','toolbar-pending','control-paused','cursor-disabled','secondary-active',
        'type2-queue','return-phase-drift','return-object-changed','return-rng-drift','return-advance','return-pending-menu','return-queue-pending',
        'cache-broken-list','cache-hidden-entry')
CASES+=('late-hook-after-stop','stop-during-original','stop-during-binder')
CASES+=('cache-menu-table','cache-not-cleared')
def fingerprint():
    files=('pilot.cpp','pilot.h','profile.h','profile.json','fixture.cpp','build.cmd','test.py','start.py','contract.py',
           'bridge.h','bridge.cpp','bridge.asm','save_callbacks.inc','user_callbacks.inc')
    return {name:hashlib.sha256((ROOT/('checkpoint_push_'+name)).read_bytes()).hexdigest() for name in files}
def main():
    folder=ROOT/'checkpoint_push_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True,exist_ok=False)
    rows=[]
    for case in CASES:
        run=folder/case;run.mkdir()
        p=subprocess.run([str(ROOT/'checkpoint_push_fixture.exe'),str(ROOT/'checkpoint_push_fixture.dll'),case,str(run)],capture_output=True,text=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
        (run/'stdout.txt').write_text(p.stdout);(run/'stderr.txt').write_text(p.stderr)
        row=json.loads(p.stdout);assert p.returncode==0 and row['passed'],(case,row,p.stderr)
        assert row['report_size']==384 and row['config_size']==2096,row
        rows.append(row)
    from checkpoint_push_contract import selftest
    contract_tests=selftest()
    result={'schema':'san14.checkpoint-push-fixtures.v2','result':'PASS','cases':rows,'case_count':len(rows),
            'source_fingerprints':fingerprint(),'contract_tests':contract_tests,
            'dll_sha256':hashlib.sha256((ROOT/'checkpoint_push_pilot.dll').read_bytes()).hexdigest(),
            'fixture_dll_sha256':hashlib.sha256((ROOT/'checkpoint_push_fixture.dll').read_bytes()).hexdigest(),
            'scope':'Own process, stub binder/queue/storage/save state lifecycle; real serializer, native worker and Steam backend are not run.',
            'game_access':False,'native_saved':False}
    with (folder/'result.json').open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'result':'PASS','cases':len(rows),'contract_tests':contract_tests,'evidence':str(folder/'result.json'),'game_access':False}))
if __name__=='__main__':main()
