"""Build a diagnostic Runtime successor and execute real owned Parent composition.

No game/Steam/process discovery. Existing native business/environment fixtures
remain substitutes; Owner/Gate/Inspector/Runtime/Parent are actually linked.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,shutil,subprocess,re
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
BASE=PRIVATE/'a_runtime_reward_planning_runs/20261010-021152-669026'
BASE_SHA='45dbe45c21460e598a8f8889a381be69f21a1d5057ac0b0195fc535d9dc017ea'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    assert s.count(a)==1,a
    return s.replace(a,b,1)
def runtime_source():
    s=(P/'a_runtime_reward_planning_runtime.cpp').read_text()
    block=''' // Non-consuming finite observation; the result never changes this callback.
 AcquireSRWLockExclusive(&lock_);
 __try {
  namespace mo=a_menu_parent_observation;mo::Input v{};
  const auto index=unsigned(InterlockedCompareExchange(&activePeriod_,0,0));
  const auto source=unsigned(InterlockedCompareExchange(&sourceIndex_,0,0));
  const auto&period=periods_[index];const auto&binding=period.binding;
  v.binding.pid=c_.pid;v.binding.birth=c_.birth;v.binding.base=c_.base;v.binding.root=c_.source.root;v.binding.world=c_.source.world;v.binding.user=sources_[source].states[4];
  v.binding.generation=binding.native.owner_generation;v.binding.period=binding.period;v.binding.epoch=binding.epoch;
  memcpy(v.binding.attempt,binding.native.attempt.data(),16);memcpy(v.binding.attachment,binding.native.attachment.data(),16);memcpy(v.binding.inputDigest,binding.room_input_digest.data(),32);
  v.identity=identity(period);v.stopped=InterlockedCompareExchange(&stopped_,0,0)!=0;v.retired=a_native_turn::Running();
  v.runtimeError=unsigned(r_.error);v.planningState=unsigned(planning_.state);v.repeatState=unsigned(repeat_.state);
  v.owner=owner_;v.gate=gate_;v.sample=inputSample;v.context=this;mo::Observe(v);
 }__finally{ReleaseSRWLockExclusive(&lock_);}
'''
    return '#include "a_menu_parent_observation.h"\n'+once(s,'bool Runtime::onRepeatBefore()noexcept {\n','bool Runtime::onRepeatBefore()noexcept {\n'+block)
def run_cmd(args,cwd,log):
    r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    log.write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0,str(log)
    return r
def main():
    run=PRIVATE/'a_menu_parent_observation_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result=dict(result='FAIL',family='san14.a-menu-parent-observation.v1',game_access=False,steam_access=False,ui_permission=False)
    sources={};private={};generated={}
    try:
        assert sha(BASE/'result.json')==BASE_SHA
        prior=json.loads((BASE/'result.json').read_text());private[str(BASE/'result.json')]=BASE_SHA
        for name,h in prior['sources'].items():
            assert sha(P/name)==h,name;sources[name]=h
        names=('a_menu_parent_observation.h','a_menu_parent_observation.cpp','a_menu_parent_observation_runtime.cpp','a_menu_parent_observation_fixture.inc','a_menu_parent_observation_test.py')
        assert (P/names[2]).read_text()==runtime_source()
        for name in names:sources[name]=sha(P/name)
        def approved(f):
            key=str(f.relative_to(BASE));assert prior['artifacts'][key]==sha(f),key
            private[str(f)]=sha(f)
        for label in ('production','owned'):
            home=BASE/label;out=run/label;out.mkdir()
            for f in list(home.glob('*.inc'))+[home/'checkpoint_planning_hold.dll',home/'planning.lib']:
                approved(f);shutil.copy2(f,out/f.name)
            approved(home/'build.cmd')
            cmd=(home/'build.cmd').read_text().replace(str(home),str(out))
            cmd=cmd.replace('a_runtime_reward_planning_runtime.cpp','a_menu_parent_observation_runtime.cpp')
            cl=next(x for x in cmd.splitlines()if x.startswith('cl ')and 'a_menu_parent_observation_runtime.cpp' in x)
            added=cl.replace('a_menu_parent_observation_runtime.cpp','a_menu_parent_observation.cpp').replace('/Fo:runtime.obj','/Fo:menu_observation.obj').replace('/Fo:fixture_runtime.obj','/Fo:menu_observation.obj')
            cmd=once(cmd,cl,added+'\nif errorlevel 1 exit /b 1\n'+cl)
            cmd='\n'.join(x.replace(' runtime.obj',' menu_observation.obj runtime.obj').replace(' fixture_runtime.obj',' menu_observation.obj fixture_runtime.obj')if x.startswith(('lib ','link '))else x for x in cmd.splitlines())+'\n'
            if label=='owned':
                src=home/'scoped_fixture.cpp';approved(src);s=src.read_text()
                s='#include "a_menu_parent_observation.h"\n'+s
                marker='  need(runtime.SubmitReward(data.binding,1,command),"B actor command after bootstrap");'
                s=once(s,marker,(P/'a_menu_parent_observation_fixture.inc').read_text()+marker)
                s=once(s,'caseName==L"bootstrap"||caseName==L"planning-stop"','caseName==L"bootstrap"||caseName==L"planning-stop"||caseName==L"observe-menu"||caseName==L"observe-selection"||caseName==L"observe-sample"||caseName==L"observe-six"')
                (out/'scoped_fixture.cpp').write_text(s);generated[str((out/'scoped_fixture.cpp').relative_to(run))]=sha(out/'scoped_fixture.cpp')
            (out/'build.cmd').write_text(cmd);generated[str((out/'build.cmd').relative_to(run))]=sha(out/'build.cmd')
            run_cmd(['cmd','/c',str(out/'build.cmd')],out,out/'compile.log')
        rows=[];exe=run/'owned/fixture.exe'
        for case in ('bootstrap','planning-stop','normal','observe-menu','observe-selection','observe-sample','observe-six'):
            folder=run/case;folder.mkdir()
            output=run_cmd([str(exe),case,str(folder),sha(exe)],folder,folder/'run.log')
            records=[json.loads(line)for line in output.stdout.splitlines()if line.startswith('{')]
            assert records and records[-1]['passed'];rows.append(dict(case=case,records=records))
        assert all(sha(P/n)==h for n,h in sources.items())
        assert all(sha(Path(n))==h for n,h in private.items())
        result.update(result='PASS',cases=rows,production_dll=str(run/'production/a_save_local_runtime.dll'),production_dll_sha256=sha(run/'production/a_save_local_runtime.dll'),sources_unchanged=True,
            actual_parent_runtime_inspector=True,native_business_environment_double=True,menu_lifecycle_supported=False,
            busy_test_scope='five-state pending toolbar or selection; no opened-submenu permission',data_record_size=360,data_sequence_offset=8)
    except Exception as e:result['error']=repr(e)
    result.update(sources=sources,private=private,generated=generated,artifacts={str(f.relative_to(run)):sha(f)for f in run.rglob('*')if f.is_file()})
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(run);print(result['result']);return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
