"""Two immutable profile chains and exact hash/date refusal, owned processes only."""
from pathlib import Path
from datetime import datetime
import subprocess,sys,os,json,hashlib
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=PRIVATE/'b_warm_profile_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    s=(P/'b_warm_retire_test.py').read_text().replace('P=Path(__file__).resolve().parent','P=Path('+repr(str(P))+')',1)
    s=s.replace("run=PRIVATE/'b_warm_retire_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)",'run=Path('+repr(str(run/'composition'))+');run.mkdir(parents=True)')
    s=s.replace('import hashlib,json,re,shutil,subprocess','import hashlib,json,re,shutil,subprocess,os,sys\nsys.path.insert(0,'+repr(str(P))+')\nimport b_warm_profile_fixture')
    s=s.replace("CASES=('success-new','report-state','user-exception','stop-during-load','restore-conflict')","CASES=('profile-one','profile-two','wrong-hash','wrong-date')")
    s=s.replace("    try:\n        archive=", "    for n in ('b_warm_profile_test.py','b_warm_profile_fixture.py','b_warm_profile_fixture.inc'):pin(P/n)\n    try:\n        archive=",1)
    s=s.replace("        for kind in ('build','fixture_build'):","        b_warm_profile_fixture.transform(run,P)\n        for kind in ('build','fixture_build'):",1)
    before="            for name in set(re.findall"
    insert="""            replacements={'b_warm_retire_owner.cpp':'b_warm_profile_owner.cpp','checkpoint_cc_load_observer.cpp':'b_warm_profile_bytes.cpp','checkpoint_cc_load_lifecycle.cpp':'b_warm_profile_lifecycle.cpp','checkpoint_title_identity_adapter.cpp':'b_warm_profile_identity.cpp','checkpoint_forward_planning_observer_v2.cpp':'b_warm_profile_planning.cpp','checkpoint_live_runtime_guards_v2.cpp':'b_warm_profile_guards.cpp','checkpoint_load_request_commit.cpp':'b_warm_profile_request.cpp'}
            for old,new in replacements.items():cmd=cmd.replace(old,new)
            cmd=cmd.replace('for %%F in (checkpoint_load_worker_bridge.cpp','for %%F in (b_warm_profile.cpp checkpoint_dynamic_file_profile.cpp checkpoint_load_worker_bridge.cpp',1)
"""
    s=s.replace(before,insert+before,1)
    s=s.replace('for case in CASES:','for variant,case in enumerate(CASES):')
    s=s.replace("shutil.copyfile(archive,local)","shutil.copyfile(archive,local)\n            if variant:local.write_bytes(local.read_bytes()+bytes(range(32)))\n            input_sha=sha(local);env=os.environ.copy();env['B_WARM_PROFILE_VARIANT']=str(variant);scenario='wrong-profile-hash' if variant==2 else 'success-new'")
    s=s.replace("fixture.exe'),case,str(local)","fixture.exe'),scenario,str(local)")
    s=s.replace('capture_output=True,timeout=35)','capture_output=True,timeout=35,env=env)')
    s=s.replace("'archive_unchanged':sha(local)==sha(archive)","'archive_unchanged':sha(local)==input_sha,'input_sha256':input_sha")
    script=run/'driver.py';script.write_text(s)
    env=os.environ.copy();env['PYTHONUTF8']='1';result={'result':'FAIL','game_process_access':False,'steam_save_access':False}
    try:
        r=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,errors='replace',env=env,timeout=240);(run/'driver.log').write_text(r.stdout+r.stderr)
        result['execution']=json.loads((run/'composition/result.json').read_text());assert r.returncode==0 and result['execution']['result']=='PASS';result['result']='PASS'
    except Exception as e:result['error']=repr(e)
    result['generated_script_sha256']=sha(script);(run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(run/'result.json')}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
