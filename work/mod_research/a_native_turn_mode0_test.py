"""Mode-zero native-turn successor, owned processes and production ABI only.

Uses hash-fixed prior generated input; it does not execute old generators or
access the installed game. Original native turn business/world are doubles.
"""
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import hashlib,json,os,shutil,subprocess,sys
from a_save_initialize_trace_generate import once
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
FIX=PRIVATE/'a_native_turn_runs/20261009-155031-692039/case'
PROD=PRIVATE/'a_native_turn_runtime_runs/20261009-155107-507427/abi/production'
PUBLISHER=PRIVATE/'a_save_repeat_publish_runs/20261009-142815-825524'
LAUNCHER_TEST=PRIVATE/'a_native_turn_start_test_runs/20261009-172106-322176'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def command(args,cwd,log,timeout=120):
    env=os.environ.copy();env['PYTHONUTF8']='1'
    child=subprocess.run(args,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,env=env)
    log.write_text(child.stdout+child.stderr,encoding='utf-8')
    assert child.returncode==0,str(log)
    return child

def owner_source():
    return '// Explicit native-turn successor: retain Running/Refresh; trace only Initialize scope.\n#include "a_save_initialize_trace.h"\nnamespace it=a_save_initialize_trace;\n'+once((P/'a_native_turn_owner.cpp').read_text(), '#include "planning_checkpoint_save_lifecycle.inc"','#include "a_save_initialize_trace_lifecycle.inc"')

def fixture_source(old):
    s='#include "a_save_initialize_trace.h"\n'+old
    at=s.index('static unsigned turnSteps=0;')
    s=s[:at]+(P/'a_native_turn_mode0_fixture.inc').read_text()+s[at:]
    s=once(s,' cfg.room_epoch=7;',' put<unsigned>(b+0x290000+8,0);cfg.room_epoch=7;')
    s=once(s,'if(!turnSteps&&!a_native_turn::Running())','if(!modeFault&&!turnSteps&&!a_native_turn::Running())')
    old='parentDispatch();parent.Snapshot(beforeParent);need(beforeParent.hostInitialized'
    new='modeFault=caseName==L"mode1"||caseName==L"mode2";if(modeFault)put<unsigned>(b+0x290000+8,caseName==L"mode1"?1u:2u);parentDispatch();parent.Snapshot(beforeParent);if(modeFault)return modeRefused(beforeParent);need(!ASaveInitializeFirstFailure.stage,"normal first Initialize clean");need(beforeParent.hostInitialized'
    s=once(s,old,new)
    s=once(s,' if(repeatCase==L"normal")need(turnSteps>=5', ' if(repeatCase==L"normal")need(!ASaveInitializeFirstFailure.stage&&get<unsigned>(b+0x290000+8)==0,"second initialization remains mode zero and no trace");\n if(repeatCase==L"normal")need(turnSteps>=5')
    return s

def main():
    run=PRIVATE/'a_native_turn_mode0_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result=dict(result='FAIL',game_access=False,steam_save_access=False,runtime_game_execution=False)
    sources={};private={};rows=[]
    try:
        import a_native_turn_start as launcher
        for module in tuple(sys.modules.values()):
            file=getattr(module,'__file__',None)
            if not file:continue
            f=Path(file).resolve()
            if f.suffix!='.py':continue
            if f.parent==P:sources[f.name]=sha(f)
            elif f.is_relative_to(P.parents[1]):private[str(f)]=sha(f)
        launcher.verify_launcher_tests(LAUNCHER_TEST)
        private[str(LAUNCHER_TEST/'result.json')]=sha(LAUNCHER_TEST/'result.json')
        for n,h in read(LAUNCHER_TEST/'result.json')['sources'].items():assert sha(P/n)==h;sources[n]=h
        for home,digest in ((FIX,'69d7f0148c1daeb6a24d2acb463ea6bf7fad37a777a275b068ee195e43e9e6c1'),(PROD,'8da44d6b8133d6f92c2ae618348165fb1de4edba41793158149f4ae9bb136ca4')):
            assert sha(home/'result.json')==digest;private[str(home/'result.json')]=digest
            old=read(home/'result.json');assert old['result']=='PASS';sources.update(old['sources'])
            for n,h in old['generated'].items():assert sha(home/'build'/n)==h;private[str(home/'build'/n)]=h
            for n,h in old['private_inputs'].items():assert sha(PRIVATE/n)==h;private[str(PRIVATE/n)]=h
            for n in ('checkpoint_planning_hold.dll','planning.lib'):
                h=old['binaries'][n];assert sha(home/'build'/n)==h;private[str(home/'build'/n)]=h
        assert (P/'a_native_turn_mode0_owner.cpp').read_text()==owner_source()
        names=('a_native_turn_mode0_test.py','a_native_turn_mode0_owner.cpp','a_native_turn_mode0_fixture.inc',
            'a_save_planning_mode_input.cpp','a_save_initialize_trace_controller.cpp','a_save_initialize_trace_lifecycle.inc',
            'a_save_initialize_trace.h','a_save_initialize_trace.cpp','a_save_initialize_trace_generate.py',
            'a_native_turn_runtime_build.py','a_native_turn_start.py','a_save_runtime_exports_test.cpp',
            'a_save_runtime_exports.h','a_save_runtime_contract.py','a_save_repeat_exports_test.py',
            'a_save_repeat_exports_test.cpp','a_save_repeat_exports.h','a_save_repeat_exports.cpp',
            'a_save_repeat_contract.py','a_save_repeat_runtime.h')
        sources.update({n:sha(P/n)for n in names})
        abi_old=PROD.parent;abi_info=read(abi_old/'result.json')
        assert sha(abi_old/'result.json')=='bac04cd8fc501134a7e0393d83e17b1515911ec6590196d17259d7b2b0fb00ad'
        private[str(abi_old/'result.json')]=sha(abi_old/'result.json')
        for n in ('schema.cpp','abi_build.cmd'):
            assert sha(abi_old/n)==abi_info['generated'][n];private[str(abi_old/n)]=sha(abi_old/n)
        assert all(sha(P/n)==h for n,h in sources.items())
        bundle=run/'bundle';abi=bundle/'abi';prod=abi/'production/build'
        for label,home,folder in (('production',PROD/'build',prod),('owned',FIX/'build',run/'owned')):
            folder.mkdir(parents=True)
            for p in home.glob('*.inc'):shutil.copy2(p,folder/p.name)
            for n in ('checkpoint_planning_hold.dll','planning.lib'):shutil.copy2(home/n,folder/n)
            cmd=(home/'build.cmd').read_text().replace(str(home),str(folder))
            cmd=cmd.replace('a_save_scoped_input.cpp','a_save_planning_mode_input.cpp').replace('planning_checkpoint_save_interlock.cpp','a_save_initialize_trace_controller.cpp').replace('a_native_turn_owner.cpp','a_native_turn_mode0_owner.cpp')
            cl=next(x for x in cmd.splitlines()if x.startswith('cl ')and '/Fo:interlock.obj' in x)
            trace=cl.replace('a_save_initialize_trace_controller.cpp','a_save_initialize_trace.cpp').replace('/Fo:interlock.obj','/Fo:initialize_trace.obj')
            cmd=once(cmd,cl,trace+'\nif errorlevel 1 exit /b 1\n'+cl).replace(' interlock.obj',' initialize_trace.obj interlock.obj')
            if label=='owned':(folder/'scoped_fixture.cpp').write_text(fixture_source((home/'scoped_fixture.cpp').read_text()),encoding='utf-8')
            (folder/'build.cmd').write_text(cmd,encoding='utf-8')
            command(['cmd','/c',str(folder/'build.cmd')],folder,folder/'compile.log',180)
        exe=run/'owned/fixture.exe'
        for case in ('normal','stop-running','mode1','mode2'):
            folder=run/case;folder.mkdir()
            child=command([str(exe),case,str(folder),sha(exe)],folder,folder/'run.log',30)
            records=[json.loads(s)for s in child.stdout.splitlines()if s.startswith('{')]
            assert len(records)==1 and records[0]['passed'];rows.append({**records[0],'case':case})
        from checkpoint_fresh_save_packet import decode_packet
        decoded=[]
        for gen in (1,2):
            d=decode_packet((run/f'normal/normal-{gen}.packet').read_bytes())
            assert d.request['generation']==gen and d.request['day']==(11 if gen==1 else 21)
            decoded.append({'generation':gen,'sha256':d.sha256,'bytes':len(d.data),'file_bytes_verified':bool(d.report['file_bytes_verified'])})
        shutil.copy2(abi_old/'schema.cpp',abi/'schema.cpp')
        cmd=(abi_old/'abi_build.cmd').read_text().replace(str(abi_old),str(abi))
        (abi/'abi_build.cmd').write_text(cmd,encoding='utf-8')
        command(['cmd','/c',str(abi/'abi_build.cmd')],abi,abi/'compile.log',90)
        schema=command([str(abi/'schema.exe')],abi,abi/'schema.log',10);write(abi/'schema.json',json.loads(schema.stdout))
        command([str(abi/'abi.exe'),str(prod/'a_save_local_runtime.dll')],prod,abi/'abi.log',30)
        child=command([sys.executable,str(P/'a_save_repeat_exports_test.py'),'--dll',str(prod/'a_save_local_runtime.dll')],P,run/'repeat-abi-driver.log',120)
        outputs=[json.loads(s)for s in child.stdout.splitlines()if s.startswith('{')];assert len(outputs)==1
        repeat_path=Path(outputs[0]['path']);additive=read(repeat_path);assert additive['result']=='PASS'
        private[str(repeat_path)]=sha(repeat_path)
        for n,h in additive['sources'].items():assert sha(P/n)==h;sources[n]=h
        for n,h in additive['generated'].items():assert sha(repeat_path.parent/n)==h;private[str(repeat_path.parent/n)]=h
        pub=read(PUBLISHER/'result.json');assert sha(PUBLISHER/'result.json')=='ff5136c9ed8a7fb304fec26d1d913d304f43627b7adfad8d1af90cf2bcdde941'
        private[str(PUBLISHER/'result.json')]=sha(PUBLISHER/'result.json')
        for n,h in pub['sources'].items():assert sha(P/n)==h;sources[n]=h
        for n,h in pub['binaries'].items():assert sha(PUBLISHER/n)==h;private[str(PUBLISHER/n)]=h
        production=dict(result='PASS',sources=sources,binaries={n:sha(prod/n)for n in ('a_save_local_runtime.dll','checkpoint_planning_hold.dll')},
            actual_tu_replacements={'a_native_turn_owner.cpp':'a_native_turn_mode0_owner.cpp','planning_checkpoint_save_interlock.cpp':'a_save_initialize_trace_controller.cpp','a_save_scoped_input.cpp':'a_save_planning_mode_input.cpp'},
            original_owner_is_generation_input=True)
        execution=dict(result='PASS',production=production,abi_executed=True,game_access=False,runtime_game_execution=False,
            own_sources={n:sources[n]for n in ('a_save_runtime_exports_test.cpp','a_native_turn_mode0_test.py','a_native_turn_mode0_owner.cpp')},generated={'schema.json':sha(abi/'schema.json')})
        write(abi/'result.json',execution)
        package=dict(result='PASS',family='san14.a-native-turn-mode0.v1',sources=sources,execution=execution,trace_data_size=144,trace_stage_offset=140)
        write(bundle/'result.json',package)
        import a_native_turn_start as launcher
        checked=launcher.verify_native_build(SimpleNamespace(build_run=bundle,repeat_abi_run=repeat_path.parent,publisher_build=PUBLISHER))
        for n,h in checked[0]['production']['binaries'].items():assert launcher.verified_artifact(bundle,n,h)==prod/n
        result.update(result='PASS',launcher_test_run=str(LAUNCHER_TEST),compatible_build_run=str(bundle),repeat_abi_run=str(repeat_path.parent),publisher_build=str(PUBLISHER),production_dll=str(prod/'a_save_local_runtime.dll'),actual_launcher_validation=True,decoded=decoded)
    except Exception as e:result['error']=repr(e)
    same=bool(sources)and all(sha(P/n)==h for n,h in sources.items())and all(sha(Path(n))==h for n,h in private.items())
    if not same:result['result']='FAIL'
    result.update(cases=rows,sources=sources,private=private,inputs_unchanged=same,
        generated={str(p.relative_to(run)):sha(p)for p in run.rglob('*')if p.is_file()and p.suffix in ('.cpp','.cmd','.inc')},
        binaries={str(p.relative_to(run)):sha(p)for p in run.rglob('*')if p.is_file()and p.suffix in ('.dll','.obj','.lib','.exe')},
        artifacts={str(p.relative_to(run)):sha(p)for p in run.rglob('*')if p.is_file()and p.suffix in ('.log','.json','.packet','.bin','.txt')},
        native_business_world_and_storage_doubles=True,actual_two_period_runtime=True)
    write(run/'result.json',result);print(json.dumps({'result':result['result'],'path':str(run/'result.json')}));return 0 if result['result']=='PASS'else 1
if __name__=='__main__':raise SystemExit(main())
