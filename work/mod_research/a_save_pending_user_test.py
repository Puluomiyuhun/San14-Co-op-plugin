"""Reproduce then repair only the authenticated pending-User window offline."""
from pathlib import Path
from datetime import datetime
import subprocess,sys,os,json,hashlib,difflib
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    baseline='--baseline' in sys.argv
    run=PRIVATE/'a_save_pending_user_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    old=(P/'a_save_covered_integration_test.py').read_text();s=old.replace('P=Path(__file__).resolve().parent','P=Path('+repr(str(P))+')',1)
    s=s.replace("run=PRIVATE/'a_save_covered_integration_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)",'run=Path('+repr(str(run/'composition'))+');run.mkdir(parents=True)')
    s=s.replace('a_save_covered_integration_fixture.inc','a_save_pending_user_fixture.inc')
    s=s.replace('queuedGame();completeOwnedSave();','queuedGame();pendingUser();completeOwnedSave();')
    s=s.replace("'a_save_scoped_input_test.py','a_save_covered_integration_test.py'","'a_save_scoped_input_test.py','a_save_covered_integration_test.py','a_save_pending_user_test.py'")
    if baseline:
        s=s.replace("CASES=('normal','foreign','multi','wrong-generation','cursor-drift')","CASES=('normal',)")
    else:
        s=s.replace("owner='a_save_covered_owner.cpp'","owner='a_save_pending_user_owner.cpp'")
        needle='    original=(P/'
        # Insert into the generated scoped driver before it builds fixture text.
        s=s.replace("'''"+'+s[at:]',"    s=s.replace(\"defines = '\",\"defines = '/DA_SAVE_PENDING_USER_SUCCESS \")\n'''"+'+s[at:]',1)
        s=s.replace("CASES=('normal','foreign','multi','wrong-generation','cursor-drift')","CASES=('normal','foreign','multi','wrong-generation','cursor-drift','user-foreign')")
        s=s.replace('else if(coveredCase==L"cursor-drift")need','else if(coveredCase==L"cursor-drift"||coveredCase==L"user-foreign")need')
        s=s.replace('coveredCase==L"cursor-drift"&&parentReport.error','(coveredCase==L"cursor-drift"||coveredCase==L"user-foreign")&&parentReport.error')
    script=run/'generated_integration_test.py';script.write_text(s,encoding='utf-8');(run/'generator.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True))),encoding='utf-8')
    result={'result':'FAIL','baseline':baseline,'game_access':False}
    try:
        env=os.environ.copy();env['PYTHONUTF8']='1';r=subprocess.run([sys.executable,str(script)],env=env,capture_output=True,text=True,errors='replace',timeout=240);(run/'driver.log').write_text(r.stdout+r.stderr,encoding='utf-8')
        child=json.loads((run/'composition'/'result.json').read_text());result['execution']=child
        if baseline:
            log=(run/'composition/case/normal/run.log').read_text();assert child['result']=='FAIL' and 'PENDING value=1 stopped=1 error=11 entrySuppressed=1 revoked=1' in log and child['execution']['sources_unchanged'];result['application_result']='FAIL_REPRODUCED'
        else:assert r.returncode==0 and child['result']=='PASS'
        result['result']='PASS'
    except Exception as e:result['error']=repr(e)
    result['generated_script_sha256']=sha(script);(run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(run/'result.json')}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
