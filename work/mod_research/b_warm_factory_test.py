"""Actual warm Owner factory/configure with real attachment guards; owned process only."""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,re,shutil,subprocess,sys
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
PRIOR=PRIVATE/'b_warm_profile_runs/20261009-154811-322893/composition'
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def main():
    run=PRIVATE/'b_warm_factory_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result={'family':'san14.b-warm-factory.v1','factory_complete_passed':False,'result':'FAIL','game_process_access':False,'steam_save_access':False,'sources':{},'private':{}}
    try:
        assert sha(PRIOR.parent/'result.json')=='1fead4fef554b0d58caf09bf28c30d11c9e5e94b38ccca7f7b39e9f6a63f31a5'
        old=json.loads((PRIOR/'result.json').read_text())
        for n,h in old['source_sha256'].items():
            q=Path(n);q=q if q.is_absolute() else P/n;assert sha(q)==h;result['sources'][str(q)]=h
        for q in list(P.glob('b_warm_factory_*'))+[P/'b_warm_two_bank_guards.cpp',P/'checkpoint_native_input_prefetch_archived.inc']:
            if q.suffix in ('.py','.cpp','.h','.inc'):result['sources'][str(q)]=sha(q)
        for n in ('fixture.cpp','chain_body.inc','chain_authorized.inc','fixture_build.cmd','build.cmd','result.json'):
            result['private'][str(PRIOR/n)]=sha(PRIOR/n)
        for n in ('chain_body.inc','chain_authorized.inc'):shutil.copyfile(PRIOR/n,run/n)
        # No old full-chain main is called. Only its native business and memory
        # constructor helpers are reused; the new runner calls actual Install.
        fixture=(PRIOR/'fixture.cpp').read_text().replace('"b_warm_profile_owner.cpp"','"b_warm_factory_owner.cpp"').replace('int wmain(int argc,wchar_t**argv)','int PriorProfileMain(int argc,wchar_t**argv)')
        fixture+='\n'+(P/'b_warm_factory_fixture.inc').read_text();(run/'fixture.cpp').write_text(fixture)
        asm=(P/'checkpoint_guest_native_session_fixture.asm').read_text()
        asm,n=re.subn(r'call qword ptr \[rax(?P<offset>\+[0-9A-Fa-f]+h)?\]',lambda m:'mov rax,qword ptr [rax'+(m['offset'] or '')+']\n call qword ptr [rax]',asm);assert n==6
        (run/'factory_callers.asm').write_text(asm)
        for kind in ('fixture_build','build'):
            cmd=(PRIOR/(kind+'.cmd')).read_text().replace(str(PRIOR/'fixture.cpp'),str(run/'fixture.cpp')).replace('b_warm_profile_owner.cpp','b_warm_factory_owner.cpp').replace('b_warm_profile_guards.cpp','b_warm_two_bank_guards.cpp')
            if kind=='fixture_build':cmd=cmd.replace(str(P/'checkpoint_guest_native_session_fixture.asm'),str(run/'factory_callers.asm'))
            (run/(kind+'.cmd')).write_text(cmd)
            r=subprocess.run(['cmd','/d','/c',str(run/(kind+'.cmd'))],cwd=run,capture_output=True,timeout=180);(run/(kind+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,(kind,r.returncode)
        archive=PRIVATE/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14';assert sha(archive)=='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c';result['private'][str(archive)]=sha(archive)
        result['cases']=[]
        for case,variant in [('factory-one',0),('factory-target9',1),('guard-drift',0)]:
            folder=run/case;folder.mkdir();local=folder/'svdexccSC03.s14';local.write_bytes(archive.read_bytes()+(bytes(range(32)) if variant else b''))
            env=os.environ.copy();env['B_WARM_PROFILE_VARIANT']=str(variant)
            r=subprocess.run([str(run/'checkpoint_complete_live_owner_v2_fixture.exe'),case,str(local),str(folder/'request.intent'),str(folder/'identity.intent'),str(folder/'owner.report')],cwd=run,capture_output=True,timeout=45,env=env);(folder/'execution.log').write_bytes(r.stdout+r.stderr)
            result['cases'].append({'case':case,'exit':r.returncode,'input_sha256':sha(local),'report_sha256':sha(folder/'owner.report') if (folder/'owner.report').exists() else None});assert r.returncode==0,('execution',case,r.returncode)
            assert (b'"actual_guard_refused":true' if case=='guard-drift' else b'"actual_factory_install":true') in r.stdout
        result['factory_complete_passed']=True
        dll=run/'checkpoint_complete_live_owner_v2.dll';result['production_dll']={'path':str(dll),'sha256':sha(dll)}
        result['inputs_unchanged']=all(sha(Path(n))==h for k in ('sources','private') for n,h in result[k].items());assert result['inputs_unchanged'];result['result']='PASS'
    except Exception as e:result['error']=repr(e)
    result['generated']={str(q):sha(q) for q in run.iterdir() if q.suffix in ('.cpp','.inc','.asm','.cmd')}
    result['binaries']={str(q):sha(q) for q in run.iterdir() if q.suffix in ('.obj','.exe','.dll','.lib','.exp')}
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(run/'result.json')}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
