"""Actual two-factory refresh composition; private host cache substitutes Steam only.

Consumes a hash-pinned prior generated fixture, never rewrites that predecessor.
The production DLL has no fixture macros. This does not access a game process.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,re,shutil,subprocess
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
PRIOR=PRIVATE/'b_warm_factory_pair_runs/20261009-181448-912475'
PRIOR_SHA='c13390840e1fbeaf54fde8822add15ef9c44a75967b8c57ea2da2af73247a990'
PYTHON_TEST=PRIVATE/'b_warm_refresh_python_runs/20261009-214950-848312/result.json'
PYTHON_SHA='7ae9340529c984f30458ca89a85cf2c4136f5f36ccf7d4bbbb1f0b4f5a1a995f'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def change(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)

def main():
    run=PRIVATE/'b_warm_refresh_pair_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result=dict(family='san14.b-warm-refresh-pair.v1',result='FAIL',game_process_access=False,steam_save_access=False)
    try:
        assert sha(PRIOR/'result.json')==PRIOR_SHA
        old=json.loads((PRIOR/'result.json').read_text());assert old['result']=='PASS'
        for section in ('sources','private','generated','binaries'):
            for n,h in old[section].items():assert sha(n)==h,(section,n)
        result['sources']=dict(old['sources']);result['private']={str(PRIOR/'result.json'):PRIOR_SHA,**old['private'],**old['generated']}
        assert sha(PYTHON_TEST)==PYTHON_SHA
        python_test=json.loads(PYTHON_TEST.read_text());assert python_test['result']=='PASS' and python_test['tests']==9
        for section in ('sources','artifacts'):
            for n,h in python_test[section].items():assert sha(n)==h,(section,n)
        result['sources'].update(python_test['sources']);result['private'][str(PYTHON_TEST)]=PYTHON_SHA
        for q in P.glob('b_warm_refresh_*'):
            if q.is_file() and q.suffix in ('.cpp','.h','.py','.inc'):result['sources'][str(q)]=sha(q)
        for q in P.glob('b_warm_storage_refresh_*'):
            if q.is_file() and q.suffix in ('.cpp','.h','.py','.inc'):result['sources'][str(q)]=sha(q)
        c=run/'composition';c.mkdir();prod=c/'production';prod.mkdir()
        for name in ('chain_body.inc','chain_authorized.inc','checkpoint_load_input_boundary_fixture_layout.h','guard_test_access.h','guard_test.cpp'):
            shutil.copyfile(PRIOR/'composition'/name,c/name)
        fixture=(PRIOR/'composition/fixture.cpp').read_text()
        fixture=change(fixture,(P/'b_warm_factory_pair_fixture.inc').read_text(),(P/'b_warm_refresh_pair_fixture.inc').read_text())
        needle='factoryNeed(!InstallCheckpointCompleteLiveOwner(&c),"Install configure reserve Arm");HostBankArmed();'
        fixture=change(fixture,needle,'''b_warm_refresh::Config refresh{};refresh.warm.profile=b_warm_profile::Get();refresh.warm.owner=c;
    factoryNeed(HostRefreshConfig(&refresh),"private refresh config and backup");
    factoryNeed(b_warm_refresh::Capture(refresh),"capture immutable refresh wrapper");
    '''+needle)
        needle='factoryNeed(s.casPublished&&s.request.read.matched,"Request CAS full guards storage");'
        fixture=change(fixture,needle,needle+'\n    factoryNeed(HostProbeLease(true),"target deny-write lease held during load");')
        needle='factoryNeed(retired.sealed&&retired.restored&&!retired.restoreFailed,"planning full guards seal restore");'
        fixture=change(fixture,needle,needle+'''
    b_warm_refresh::Report refreshed{};factoryNeed(!GetBWarmRefreshReport(&refreshed),"refresh report export");
    factoryNeed(refreshed.state==4&&!refreshed.error&&refreshed.writeAttempts==1&&refreshed.writeReturned==1&&refreshed.matched==1&&refreshed.previousReads==2&&refreshed.newReads==2&&refreshed.intentCreated==1&&refreshed.intentDurable==1&&!refreshed.leaseHeld&&refreshed.leaseReleased==1&&refreshed.releaseCalls==1,"native refresh and retirement receipt");
    factoryNeed(HostProbeLease(false),"target lease released only after actual retirement");
    printf("REFRESH_COMPLETE write=1 previous_reads=2 new_reads=2 lease_released=1\\n");''')
        needle='if(!ok){for(unsigned i=0;i<29;++i)'
        fixture=change(fixture,needle,'if(!ok){b_warm_refresh::Report rr{};GetBWarmRefreshReport(&rr);printf("REFRESH state=%u error=%u stage=%s first=%s os=%u\\n",rr.state,rr.error,rr.stage,rr.firstFailure,rr.osError);for(unsigned i=0;i<29;++i)')
        (c/'fixture.cpp').write_text(fixture)
        (c/'host.def').write_text((PRIOR/'composition/host.def').read_text()+'HostRefreshConfig\nHostProbeLease\n')
        def adapt(cmd):
            return cmd.replace(str(PRIOR/'composition'),str(c)).replace('b_warm_profile_request.cpp','b_warm_refresh_request.cpp').replace('b_warm_retire_session.cpp','b_warm_refresh_retire_session.cpp').replace('/W4 /WX','/W4 /WX /D_CRT_SECURE_NO_WARNINGS')
        cmd=adapt((PRIOR/'composition/build.cmd').read_text()).replace('b_warm_factory_pair_host.cpp','b_warm_refresh_pair_host.cpp')
        # Host hash/identity utilities use the same read core, never the native owner.
        cmd=cmd.replace('host0.obj host1.obj host2.obj /link',f'"{P/"native_storage_read_core.cpp"}" host0.obj host1.obj host2.obj /link')
        compileline=next(line for line in cmd.splitlines() if '/c /Fo:bank0.obj' in line)
        extra=''
        for i,name in enumerate(('b_warm_storage_refresh_core.cpp','b_warm_refresh_owner.cpp')):
            line=re.sub(r'/Fo:bank0.obj .*$',f'/Fo:refresh{i}.obj "'+str(P/name).replace('\\','/')+'"',compileline)
            extra+=line+'\nif errorlevel 1 exit /b 1\n'
        marker=next(line for line in cmd.splitlines() if '/LD /Fe:bank.dll' in line)
        cmd=change(cmd,marker,extra+marker.replace('host.lib /link','refresh0.obj refresh1.obj host.lib /link'))
        (c/'build.cmd').write_text(cmd)
        pcmd=adapt((PRIOR/'composition/production/build.cmd').read_text())
        # Preserve the production per-translation-unit compile loop.
        sourceline=next(line for line in pcmd.splitlines() if line.startswith('for %%F in (') and '.cpp' in line)
        added=' '.join('"'+str(P/n)+'"' for n in ('b_warm_storage_refresh_core.cpp','b_warm_refresh_owner.cpp'))
        pcmd=change(pcmd,sourceline,sourceline.replace(') do (',' '+added+') do ('))
        assert added in pcmd
        (prod/'build.cmd').write_text(pcmd)
        env=os.environ.copy();env['PYTHONUTF8']='1'
        for folder in (c,prod):
            rr=subprocess.run(['cmd','/d','/c',str(folder/'build.cmd')],cwd=folder,env=env,capture_output=True,timeout=180)
            (folder/'build.log').write_bytes(rr.stdout+rr.stderr);assert rr.returncode==0,('build',str(folder),rr.returncode)
        for i in (1,2):
            shutil.copyfile(c/'bank.dll',c/f'bank{i}.dll');(c/f'bank{i}').mkdir()
            (c/f'bank{i}'/'svdexccSC03.s14').write_bytes(bytes(range(256))*(3+i)+bytes([i])*i)
        shutil.copyfile(c/'bank.dll',c/'stopped.dll')
        rr=subprocess.run([str(c/'host.exe'),str(c/'bank1.dll'),str(c/'bank2.dll'),str(c)],cwd=c,env=env,capture_output=True,timeout=50)
        (c/'execution.log').write_bytes(rr.stdout+rr.stderr);assert rr.returncode==0,('execution',rr.returncode)
        assert b'"completed_banks":2' in rr.stdout and rr.stdout.count(b'REFRESH_COMPLETE write=1 previous_reads=2 new_reads=2 lease_released=1')==2
        negative=c/'first_failed';negative.mkdir()
        for i in (1,2):
            (negative/f'bank{i}').mkdir();shutil.copyfile(c/f'bank{i}'/'svdexccSC03.s14',negative/f'bank{i}'/'svdexccSC03.s14')
        e=env.copy();e['B_WARM_PAIR_FIRST_FAIL']='1'
        rr=subprocess.run([str(c/'host.exe'),str(c/'bank1.dll'),str(c/'bank2.dll'),str(negative)],cwd=c,env=e,capture_output=True,timeout=50)
        (c/'first_failed.log').write_bytes(rr.stdout+rr.stderr);assert rr.returncode==0 and b'FIRST_FAILED_NO_HANDOVER actual_guard_drift=1 second_install=0' in rr.stdout,('negative',rr.returncode)
        result['inputs_unchanged']=all(sha(n)==h for section in ('sources','private') for n,h in result[section].items());assert result['inputs_unchanged']
        result.update(result='PASS',refresh_factory_pair_passed=True,full_factory_pair_passed=True,production_compile_only=True,native_business_double=True,
            cases=dict(two_native_refresh_load_retire_generations=True,actual_target_lease_held_then_released=True,first_guard_failure_no_handover=True,late_first_callbacks_during_second=True))
        dll=prod/'checkpoint_complete_live_owner_v2.dll';result['production_dll']=dict(path=str(dll),sha256=sha(dll))
    except Exception as exc:result['error']=repr(exc)
    result['generated']={str(q):sha(q) for q in run.rglob('*') if q.is_file() and q.suffix in ('.cpp','.h','.inc','.def','.cmd')}
    result['binaries']={str(q):sha(q) for q in run.rglob('*') if q.is_file() and q.suffix in ('.dll','.exe','.obj','.lib')}
    result['artifacts']={str(q):sha(q) for q in run.rglob('*') if q.is_file() and q.suffix in ('.log','.report','.refresh','.backup','.s14','.intent','.request','.identity','.install')}
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=result['result'],path=str(run/'result.json'),error=result.get('error'))));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
