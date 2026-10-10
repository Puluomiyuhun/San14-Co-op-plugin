"""Build and run only owned processes; no game discovery, installer or real saves."""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,subprocess,sys
from a_save_three_cycle_sources import sources,replace
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    run=PRIVATE/'a_save_three_cycle_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    overlay=run/'src';overlay.mkdir()
    # Snapshot source dependencies only. Runtime outputs and old binaries are not copied.
    originals={}
    for p in P.iterdir():
        if p.is_file() and p.suffix in ('.py','.cpp','.h','.inc','.asm','.def'):
            originals[p.name]=sha(p);(overlay/p.name).write_bytes(p.read_bytes())
    generated=sources(P)
    for n,s in generated.items():(overlay/n).write_text(s,encoding='utf-8')
    old=(P/'a_save_repeat_test.py').read_text(encoding='utf-8')
    script=replace(old,"P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'",
                   'P=Path('+repr(str(overlay))+');PRIVATE=Path('+repr(str(PRIVATE))+')')
    script=replace(script,"run=PRIVATE/'a_save_repeat_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)",
                   'run=Path('+repr(str(run/'native'))+');run.mkdir(parents=True)')
    script=replace(script,'from a_save_repeat_fixture import transform','from a_save_three_cycle_fixture import transform')
    script=replace(script,"CASES=('normal','stop-gap','missing-after')","CASES=('normal','stop-gap','missing-after','stop-third','missing-third')")
    script=replace(script,"s=s.replace('for gen in (1,):','for gen in (1,2):').replace('len(decoded)==1','len(decoded)==2')",
                   "s=s.replace('for gen in (1,):','for gen in (1,2,3):').replace('len(decoded)==1','len(decoded)==3').replace('(11 if gen==1 else 21)','(11 if gen==1 else 21 if gen==2 else 1)')")
    # The generated predecessor driver derives PRIVATE from P; keep private inputs pinned.
    script=script.replace("s=s.replace('from checkpoint_fresh_save_packet import'", "s=s.replace(\"PRIVATE=P.parents[2]/'mod_research'\",'PRIVATE=Path('+repr(str(PRIVATE))+')')\n    s=s.replace('from checkpoint_fresh_save_packet import'")
    launcher=run/'run_native.py';launcher.write_text(script,encoding='utf-8')
    env=os.environ.copy();env['PYTHONPATH']=str(overlay);env['PYTHONUTF8']='1';env['PYTHONDONTWRITEBYTECODE']='1'
    result=dict(result='FAIL',game_access=False,native_fixture_only=True,production_permit=False,capacity=3)
    try:
        proc=subprocess.run([sys.executable,'-B','-X','utf8',str(launcher)],env=env,capture_output=True,text=True,errors='replace',timeout=260)
        (run/'driver.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
        child=json.loads((run/'native'/'result.json').read_text());result['execution']=child
        assert proc.returncode==0 and child['result']=='PASS','owned native run failed'
        assert all(sha(P/n)==v for n,v in originals.items()),'predecessor source changed during run'
        result['result']='PASS'
    except Exception as e:result['error']=repr(e)
    result['sources']=originals
    result['generated_sources']={n:sha(overlay/n) for n in generated}
    result['artifacts']={str(p.relative_to(run)):sha(p) for p in run.rglob('*') if p.is_file() and p!=run/'result.json'}
    path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=result['result'],path=str(path))));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
