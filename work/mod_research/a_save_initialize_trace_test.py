"""Compile exact production successor and exercise actual scoped initialization.

Only owned processes. Frozen native business/world are fixture data; original
Controller, Claim, source identity and Inspector predicates execute unchanged.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,shutil,sys
from a_save_initialize_trace_generate import instrument,once
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
FIX=PRIVATE/'a_save_abort_pending_runs/20261009-135450-754156/case'
PROD=PRIVATE/'a_save_abort_pending_runtime_runs/20261009-135510-973447/abi/production'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run_cmd(cmd,cwd,log,timeout=120):
    p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,errors='replace',timeout=timeout)
    log.write_text(p.stdout+p.stderr,encoding='utf-8');assert p.returncode==0,str(log);return p
def main():
    run=PRIVATE/'a_save_initialize_trace_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result=dict(result='FAIL',game_access=False,runtime_game_execution=False)
    sources={};private={};rows=[]
    try:
        for home,digest in ((FIX,'9eae1e157facde216af9bd41cc35eb95e8aba3db18784b3e2318709c8ac27cda'),(PROD,'ddf4c709201851df4b17da5b7563abc8e4ff00cc822a41bff78539b9b71af64f')):
            assert sha(home/'result.json')==digest;private[str(home/'result.json')]=digest
            old=json.loads((home/'result.json').read_text());assert old['result']=='PASS';sources.update(old['sources'])
            for n,h in old['generated'].items():assert sha(home/'build'/n)==h;private[str(home/'build'/n)]=h
            for n,h in old['private_inputs'].items():assert sha(PRIVATE/n)==h;private[str(PRIVATE/n)]=h
            for n in ('checkpoint_planning_hold.dll','planning.lib'):
                h=old['binaries'][n];assert sha(home/'build'/n)==h;private[str(home/'build'/n)]=h
        # This historic Python generator is not invoked; its pinned generated
        # fixture/build files above are the actual inputs. Its later source edit
        # must not be silently called unchanged or accepted for native code.
        result['unused_predecessor_generator']={'name':'a_save_abort_pending_test.py','recorded':sources.pop('a_save_abort_pending_test.py'),'current':sha(P/'a_save_abort_pending_test.py')}
        for n,text in instrument().items():assert (P/n).read_text()==text.rstrip()+'\n','successor differs from exact transform: '+n
        sources.update({n:sha(P/n) for n in ('a_save_initialize_trace_generate.py','a_save_initialize_trace_test.py','a_save_initialize_trace_fixture.inc',*instrument().keys())})
        sources['a_save_initialize_trace.cpp']=sha(P/'a_save_initialize_trace.cpp');sources['a_save_initialize_trace.h']=sha(P/'a_save_initialize_trace.h')
        for n in ('a_save_runtime_exports_test.cpp','a_save_diagnostic_start.py','a_save_runtime_exports.h','a_save_runtime_control.py','a_save_runtime_contract.py','a_save_failure_diagnostic.py'):
            sources[n]=sha(P/n)
        abi_old=PROD.parent;abi_info=json.loads((abi_old/'result.json').read_text())
        private[str(abi_old/'result.json')]=sha(abi_old/'result.json')
        assert private[str(abi_old/'result.json')]=='4b6f834e5b35a6860f9ff58bb5e1fd70d856842502b314438fdccc9604e98703'
        for n in ('schema.cpp','abi_build.cmd'):
            assert sha(abi_old/n)==abi_info['generated'][n];private[str(abi_old/n)]=sha(abi_old/n)
        assert all(sha(P/n)==h for n,h in sources.items())
        for label,oldhome in (('production',PROD/'build'),('owned',FIX/'build')):
            folder=run/label;folder.mkdir()
            for p in oldhome.glob('*.inc'):shutil.copy2(p,folder/p.name)
            for n in ('checkpoint_planning_hold.dll','planning.lib'):shutil.copy2(oldhome/n,folder/n)
            cmd=(oldhome/'build.cmd').read_text().replace(str(oldhome),str(folder))
            cmd=cmd.replace('planning_checkpoint_save_interlock.cpp','a_save_initialize_trace_controller.cpp').replace('a_save_abort_pending_owner.cpp','a_save_initialize_trace_owner.cpp')
            # Compile trace once without fixture definitions and link that same object.
            cl=next(x for x in cmd.splitlines() if x.startswith('cl ') and '/Fo:interlock.obj' in x)
            trace=cl.replace('a_save_initialize_trace_controller.cpp','a_save_initialize_trace.cpp').replace('/Fo:interlock.obj','/Fo:initialize_trace.obj')
            cmd=once(cmd,cl,trace+'\nif errorlevel 1 exit /b 1\n'+cl)
            cmd=cmd.replace(' interlock.obj',' initialize_trace.obj interlock.obj')
            if label=='owned':
                fixture=(oldhome/'scoped_fixture.cpp').read_text();fixture='#include "a_save_initialize_trace.h"\n'+fixture
                pos=fixture.index('int wmain(');fixture=fixture[:pos]+(P/'a_save_initialize_trace_fixture.inc').read_text()+fixture[pos:]
                fixture=once(fixture,'rc.sample=RewardData::sample;','rc.sample=traceSample;')
                fixture=once(fixture,'parentDispatch();parent.Snapshot(beforeParent);','traceCase=caseName;traceFault=caseName!=L"normal";if(traceCase==L"slot")traceChangeSlot();parentDispatch();parent.Snapshot(beforeParent);if(traceFault)return traceFinish(beforeParent);need(!ASaveInitializeFirstFailure.stage,"normal initialization publishes no failure");')
                (folder/'scoped_fixture.cpp').write_text(fixture,encoding='utf-8')
            if label=='production':cmd+='dumpbin /exports a_save_local_runtime.dll > exports.log\nif errorlevel 1 exit /b 1\n'
            (folder/'build.cmd').write_text(cmd,encoding='utf-8')
            run_cmd(['cmd','/c',str(folder/'build.cmd')],folder,folder/'compile.log',180)
            if label=='production':assert 'ASaveInitializeFirstFailure' in (folder/'exports.log').read_text()
        exe=run/'owned/fixture.exe'
        for case in ('normal','slot','sample','identity','bind','inspect'):
            folder=run/case;folder.mkdir()
            p=run_cmd([str(exe),case,str(folder),sha(exe)],folder,folder/'run.log',30)
            records=[json.loads(line) for line in p.stdout.splitlines() if line.startswith('{')]
            assert len(records)==1 and records[0]['passed'];rows.append({**records[0],'case':case})
        # Execute the existing typed Runtime ABI against this new production DLL.
        abi=run/'abi-test';abi.mkdir();shutil.copy2(abi_old/'schema.cpp',abi/'schema.cpp')
        cmd=(abi_old/'abi_build.cmd').read_text().replace(str(abi_old/'production/build'),str(run/'production')).replace(str(abi_old),str(abi))
        (abi/'abi_build.cmd').write_text(cmd,encoding='utf-8');run_cmd(['cmd','/c',str(abi/'abi_build.cmd')],abi,abi/'compile.log',90)
        schema=run_cmd([str(abi/'schema.exe')],abi,abi/'schema.log',10)
        (abi/'schema.json').write_text(json.dumps(json.loads(schema.stdout),indent=2)+'\n')
        run_cmd([str(abi/'abi.exe'),str(run/'production/a_save_local_runtime.dll')],run/'production',abi/'abi.log',30)
        launch=run/'launch';launch.mkdir()
        for n in ('a_save_local_runtime.dll','checkpoint_planning_hold.dll'):shutil.copy2(run/'production'/n,launch/n)
        shutil.copy2(abi/'schema.json',launch/'schema.json')
        package=dict(result='PASS',abi_executed=True,game_access=False,runtime_game_execution=False,
            production=dict(result='PASS',sources=sources,binaries={n:sha(launch/n) for n in ('a_save_local_runtime.dll','checkpoint_planning_hold.dll')}),
            own_sources={n:sources[n] for n in ('a_save_runtime_exports_test.cpp','a_save_runtime_exports.h','a_save_initialize_trace_test.py')},
            generated={'schema.json':sha(launch/'schema.json')},trace_data_size=144,trace_data_stage_offset=140)
        (launch/'result.json').write_text(json.dumps(package,indent=2)+'\n')
        import a_save_diagnostic_start as launcher
        launcher.verify_sources(package['production']);launcher.validate_schema(json.loads((launch/'schema.json').read_text()))
        for n,h in package['production']['binaries'].items():assert launcher.verified_artifact(launch,n,h)==launch/n
        result['compatible_build_run']=str(launch);result['abi_executed']=True
        result['result']='PASS'
    except Exception as e:result['error']=repr(e)
    same=bool(sources) and all(sha(P/n)==h for n,h in sources.items()) and all(sha(Path(n))==h for n,h in private.items())
    if not same:result['result']='FAIL'
    result.update(cases=rows,sources=sources,private=private,inputs_unchanged=same,
        generated={str(p.relative_to(run)):sha(p) for p in run.rglob('*') if p.is_file() and p.suffix in ('.cpp','.cmd','.inc')},
        binaries={str(p.relative_to(run)):sha(p) for p in run.rglob('*') if p.is_file() and p.suffix in ('.dll','.obj','.lib','.exe')},
        artifacts={str(p.relative_to(run)):sha(p) for p in run.rglob('*') if p.is_file() and p.suffix in ('.log','.bin','.packet','.json')},
        production_dll=str(run/'production/a_save_local_runtime.dll'),actual_controller=True,actual_claim=True,actual_inspector=True,native_world_and_business_doubles=True)
    path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=result['result'],path=str(path))));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
