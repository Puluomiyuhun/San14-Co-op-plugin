"""Real DebugActiveProcess tests against a dedicated synthetic process, never SAN14."""
from datetime import datetime
import hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
folder=ROOT/'auto_reload_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
folder.mkdir(parents=True)
checkpoint=ROOT.parent/'mod_test/replay-checkpoint-34/svdexSC34.s14'
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
def rows(path):
    try:return [json.loads(s) for s in path.read_text().splitlines() if s]
    except (OSError,json.JSONDecodeError):return []
def wait(predicate,seconds=10):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        value=predicate()
        if value:return value
        time.sleep(.01)
    raise AssertionError('wait timed out')
cases=('execute','dry','wrong_mode','wrong_pending','missing_cache','wrong_filename','wrong_date','wrong_code','pending_transition','readonly_request','existing_journal','repeat_request','timeout','cancel','stall_after_request','deserialize_id_map_unavailable','worker_id_map_unavailable','deserialize_wrong_date')
results=[]
for case in cases:
    out=folder/case;out.mkdir();ready=out/'ready.json';go=out/'go';log=out/'trace.jsonl';journal=out/'once.json'
    if case=='existing_journal':journal.write_text('preserve me\n')
    if case=='repeat_request':journal=folder/'execute'/'once.json'
    journal_before=journal.read_bytes() if journal.exists() else None
    fixture=subprocess.Popen([str(ROOT/'auto_reload_fixture.exe'),str(ready),str(go),case],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    observer=None
    try:
        info=wait(lambda: rows(ready));info=info[0]
        command=[str(ROOT/'observe_auto_reload.exe'),str(info['pid']),hex(info['base']),'0x3f8177','1' if case in ('timeout','stall_after_request') else '15',str(log),'dry' if case=='dry' else 'execute',str(journal),str(checkpoint)]
        observer=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        wait(lambda:any(r.get('event')=='armed' for r in rows(log)) or observer.poll() is not None)
        if case=='cancel':Path(str(log)+'.stop').write_text('stop')
        elif case!='timeout':go.write_text('go')
        stdout,stderr=observer.communicate(timeout=20)
        trace=rows(log)
        if case in ('timeout','cancel'):go.write_text('go')
        fstdout,fstderr=fixture.communicate(timeout=10)
        assert fixture.returncode==0,(case,fixture.returncode,fstdout,fstderr,trace)
        actual=json.loads(fstdout)
        assert not actual['debugger_attached'] and actual['game_process_access'] is False,(case,actual)
        success=case in ('execute','dry','deserialize_id_map_unavailable');timeout=case in ('timeout','cancel','stall_after_request')
        expected=0 if success else 4 if timeout else 1
        assert observer.returncode==expected,(case,observer.returncode,stderr,trace)
        events=[r['event'] for r in trace]
        if success or timeout:
            assert trace[-1]=={'event':'detached','captured':success,'registers_restored':True},(case,trace)
        elif case!='wrong_code':assert trace[-1]=={'event':'error_cleanup','registers_restored':True,'detached':True},(case,trace)
        if case in ('execute','stall_after_request','deserialize_id_map_unavailable','worker_id_map_unavailable','deserialize_wrong_date'):
            assert actual['request']==34 and actual['consumed'] and actual['changed_request_bytes']==4,(case,actual)
            assert journal.exists() and json.loads(journal.read_text())['outcome']=='unknown_no_auto_retry'
        else:
            assert actual['changed_request_bytes']==0,(case,actual)
            assert (journal.read_bytes() if journal.exists() else None)==journal_before,(case,'journal changed')
        if case in ('execute','deserialize_id_map_unavailable'):assert events.count('reload_request_written')==1 and events.count('same_player_reload_observed')==1
        if case=='deserialize_id_map_unavailable':
            assert actual['semantic_maps_unavailable_at_deserialize'] and actual['semantic_maps_restored_before_worker']
            assert 'deserialize_return' in events and 'load_worker_result' in events
        if case=='worker_id_map_unavailable':
            error=next(r for r in trace if r['event']=='error')
            assert error['point_epoch']==4 and error['last_observation_rva']==0x508BC2,(case,trace)
            assert 'deserialize_return' in events and 'load_worker_result' not in events and 'same_player_reload_observed' not in events
        if case=='deserialize_wrong_date':
            error=next(r for r in trace if r['event']=='error')
            assert error['point_epoch']==3 and error['last_observation_rva']==0x2EE64C and error['message']=='not_checkpoint34_date',(case,trace)
        if case=='dry':assert events.count('dry_request_guards_passed')==1 and 'reload_request_written' not in events
        result={'case':case,'result':'PASS','observer_exit':observer.returncode,'events':events,'fixture':actual,'stderr':stderr.decode(errors='replace')}
        results.append(result);print(json.dumps({'case':case,'result':'PASS'}),flush=True)
    finally:
        if observer and observer.poll() is None:
            Path(str(log)+'.stop').write_text('stop');observer.wait(timeout=15)
        if fixture.poll() is None:go.write_text('go');fixture.wait(timeout=10)
cleanup_binary=ROOT/'auto_reload_cleanup_fixture.exe'
cleanup_run=subprocess.run([str(cleanup_binary)],capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
cleanup=json.loads(cleanup_run.stdout)
assert cleanup['result']=='PASS' and cleanup['cases']==6 and cleanup['real_windows_threads'] and not cleanup['game_process_access']
cleanup['binary_sha256']=hashlib.sha256(cleanup_binary.read_bytes()).hexdigest()
(folder/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n',encoding='utf-8')
result={'result':'PASS','created':datetime.now().astimezone().isoformat(),'directory':str(folder),'binary_sha256':hashlib.sha256((ROOT/'observe_auto_reload.exe').read_bytes()).hexdigest(),'cases':results,'cleanup':cleanup,
 'scope':'Real Windows debugger lifecycle/hardware breakpoints against a separate native process. Copied request consumer branch executes. Later native load stages are synthetic scaffolding; no full native game load and no SAN14 process access.'}
(ROOT/'auto_reload_test_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','cases':len(results),'game_access':False}))
