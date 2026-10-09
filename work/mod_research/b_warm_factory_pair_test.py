"""Same-host two actual warm factory installations; only native business is substituted."""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,subprocess,sys
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
FACTORY=PRIVATE/'b_warm_factory_runs/20261009-172050-464741'
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
    run=PRIVATE/'b_warm_factory_pair_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result={'family':'san14.b-warm-factory-pair.v1','result':'FAIL','game_process_access':False,'steam_save_access':False}
    try:
        assert sha(FACTORY/'result.json')=='d08889ffb8cdbf517c141e8b3b2a8e05d38374008cd7833a041713fb48720499'
        f=json.loads((FACTORY/'result.json').read_text())
        for section in ('sources','private','generated'):
            for n,h in f[section].items():assert sha(Path(n))==h,(section,n)
        s=(P/'b_warm_two_bank_test.py').read_text()
        s=replace(s,"P=Path(__file__).resolve().parent",'P=Path('+repr(str(P))+')')
        s=replace(s,"run=PRIVATE/'b_warm_two_bank_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)",'run=Path('+repr(str(run/'composition'))+');run.mkdir(parents=True)')
        s=replace(s,"for q in P.glob('b_warm_two_bank_*'):","for q in list(P.glob('b_warm_two_bank_*'))+list(P.glob('b_warm_factory_pair_*'))+[P/'b_warm_factory_fixture.inc',P/'b_warm_factory_owner.cpp',P/'b_warm_coordinator_native.h',P/'b_warm_coordinator_native.cpp']:")
        point="        body=(PRIOR/'chain_body.inc').read_text();auth=(PRIOR/'chain_authorized.inc').read_text();fixture=(PRIOR/'fixture.cpp').read_text()"
        extra="""
        FACTORY=Path(FACTORY_PATH)
        for name in ('result.json','fixture.cpp','factory_callers.asm'):
            result['private_pins'][str(FACTORY/name)]=sha(FACTORY/name)
        fixture=(FACTORY/'fixture.cpp').read_text().replace('"b_warm_factory_owner.cpp"','"b_warm_factory_pair_owner.cpp"')
        fixture=change(fixture,'extern "C" {std::uint64_t BindingFixtureGeneration=1;void BindingFixtureContextInit();}','extern "C" {__declspec(dllimport) std::uint64_t BindingFixtureGeneration;__declspec(dllimport) void BindingFixtureContextInit();}')
        line=next(line for line in fixture.splitlines(True) if 'constexpr uintptr_t slots[]=' in line)
        fixture=change(fixture,line,'')
        fixture=change(fixture,'static void factoryNeed(', (P/'b_warm_factory_pair_fixture.inc').read_text()+'\\nstatic void factoryNeed(')
        fixture=change(fixture,'factoryConfig(c,argv);scenario=L"success-new";','factoryConfig(c,argv);pairConfig(c);scenario=L"success-new";')
        fixture=change(fixture,'GuestSessionSlots=reinterpret_cast<void**>(alloc(4096));for(unsigned i=0;i<6;++i)GuestSessionSlots[i]=reinterpret_cast<void*>(i<5?base+rv[i]:c.storageVtable+8);','for(unsigned i=0;i<6;++i)factoryNeed(GuestSessionSlots[i]==reinterpret_cast<void*>(i<5?base+rv[i]:c.storageVtable+8),"same exact host owned slot addresses");')
        fixture=change(fixture,'factoryNeed(!InstallCheckpointCompleteLiveOwner(&c),"Install configure reserve Arm");','factoryNeed(!InstallCheckpointCompleteLiveOwner(&c),"Install configure reserve Arm");HostBankArmed();')
""".replace('FACTORY_PATH',repr(str(FACTORY)))
        s=replace(s,point,point+extra)
        s=s.replace("data=['GuestSessionSlots'","data=['HostStorageVtable','HostStorage','BindingFixtureGeneration','GuestSessionSlots'")
        s=s.replace("+['HwbpFixtureSite','HostBankArmed']","+['HwbpFixtureSite','HostBankArmed','BindingFixtureContextInit','HostExists','HostFileSize']")
        s=replace(s,"asm=['checkpoint_load_worker_bridge.asm','checkpoint_load_dispatch_bridge.asm','checkpoint_authorized_forward_admission_bridge.asm','checkpoint_live_storage_binding_fixture.asm']","asm=['checkpoint_load_worker_bridge.asm','checkpoint_load_dispatch_bridge.asm','checkpoint_authorized_forward_admission_bridge.asm']")
        s=replace(s,"('checkpoint_guest_native_session_fixture.asm','checkpoint_native_input_hwbp_fixture.asm')","(str(FACTORY/'factory_callers.asm'),'checkpoint_native_input_hwbp_fixture.asm','checkpoint_live_storage_binding_fixture.asm')")
        s=s.replace('b_warm_two_bank_fixture.cpp','b_warm_factory_pair_host.cpp')
        s=s.replace('"{P/"b_warm_two_bank_owner.cpp"}" host0.obj host1.obj','"{P/"b_warm_two_bank_owner.cpp"}" "{P/"b_warm_coordinator_native.cpp"}" host0.obj host1.obj host2.obj')
        s=replace(s,"pcmd=(PRIOR/'build.cmd').read_text().replace('b_warm_profile_guards.cpp','b_warm_two_bank_guards.cpp')","pcmd=(PRIOR/'build.cmd').read_text().replace('b_warm_profile_guards.cpp','b_warm_two_bank_guards.cpp').replace('b_warm_profile_owner.cpp','b_warm_factory_pair_owner.cpp')")
        marker="        result['inputs_unchanged']=all(sha(Path(n))==h"
        negative="""
        failroot=run/'first_failed';failroot.mkdir()
        for i in (1,2):
            (failroot/f'bank{i}').mkdir();shutil.copyfile(run/f'bank{i}'/'svdexccSC03.s14',failroot/f'bank{i}'/'svdexccSC03.s14')
        negative_env=env.copy();negative_env['B_WARM_PAIR_FIRST_FAIL']='1'
        r=subprocess.run([str(run/'host.exe'),str(run/'bank1.dll'),str(run/'bank2.dll'),str(failroot)],cwd=run,capture_output=True,timeout=50,env=negative_env)
        (run/'first_failed.log').write_bytes(r.stdout+r.stderr);result['negative_exit']=r.returncode
        assert r.returncode==0 and b'FIRST_FAILED_NO_HANDOVER actual_guard_drift=1 second_install=0' in r.stdout
"""
        s=replace(s,marker,negative+marker)
        driver=run/'driver.py';driver.write_text(s)
        env=os.environ.copy();env['PYTHONUTF8']='1'
        r=subprocess.run([sys.executable,str(driver)],capture_output=True,env=env,timeout=300);(run/'driver.log').write_bytes(r.stdout+r.stderr)
        result['execution']=json.loads((run/'composition/result.json').read_text());assert r.returncode==0 and result['execution']['result']=='PASS';result['result']='PASS'
        result['same_process_two_complete_factories']=True
        e=result['execution'];result['sources']=e['source_pins'];result['private']=e['private_pins'];result['generated']=e['generated'];result['binaries']=e['binaries']
        for field in ('sources','private','generated','binaries'):
            assert result[field] and all(sha(Path(n))==h for n,h in result[field].items()),field
        result['generated'][str(driver)]=sha(driver)
        result['inputs_unchanged']=e['inputs_unchanged'];result['full_factory_pair_passed']=True
        dll=run/'composition/production/checkpoint_complete_live_owner_v2.dll';assert dll.is_file()
        result['production_dll']={'path':str(dll),'sha256':sha(dll)}
        result['cases']={'same_process_two_actual_factories':True,'first_source_failure_no_handover':e['negative_exit']==0}
        result['native_business_double']=True;result['production_compile_only']=True
    except Exception as e:result['error']=repr(e)
    if (run/'driver.py').exists():result['driver_sha256']=sha(run/'driver.py')
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(run/'result.json')}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
