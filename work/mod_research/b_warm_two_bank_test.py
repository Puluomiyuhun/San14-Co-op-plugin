"""Two retained banks share one host slot page; native business remains an explicit double."""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,re,shutil,subprocess,sys
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
PRIOR=PRIVATE/'b_warm_profile_runs/20261009-154811-322893/composition'
VC=Path(r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def change(s,a,b,count=1):
    assert s.count(a)==count,(a,s.count(a),count)
    return s.replace(a,b)
def main():
    run=PRIVATE/'b_warm_two_bank_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result={'result':'FAIL','game_process_access':False,'steam_save_access':False,'source_pins':{},'private_pins':{}}
    try:
        previous=json.loads((PRIOR/'result.json').read_text());assert previous['result']=='PASS'
        assert sha(PRIOR.parent/'result.json')=='1fead4fef554b0d58caf09bf28c30d11c9e5e94b38ccca7f7b39e9f6a63f31a5'
        result['private_pins'][str(PRIOR.parent/'result.json')]=sha(PRIOR.parent/'result.json')
        result['private_pins'][str(PRIOR/'result.json')]=sha(PRIOR/'result.json')
        # Include the previous complete transitive source closure, and the exact
        # private generated code consumed here. No old test or live script runs.
        for key in ('source_sha256',):
            old=previous.get(key,{})
            if isinstance(old,dict):
                for n,h in old.items():
                    q=Path(n);q=q if q.is_absolute() else P/n
                    assert q.exists() and sha(q)==h;result['source_pins'][str(q)]=h
        q=P/'checkpoint_native_input_prefetch_archived.inc';result['source_pins'][str(q)]=sha(q)
        for q in P.glob('b_warm_two_bank_*'):
            if q.suffix in ('.h','.cpp','.py','.inc'):result['source_pins'][str(q)]=sha(q)
        for n in ('fixture.cpp','chain_body.inc','chain_authorized.inc','fixture_build.cmd','build.cmd'):
            q=PRIOR/n;result['private_pins'][str(q)]=sha(q)
        body=(PRIOR/'chain_body.inc').read_text();auth=(PRIOR/'chain_authorized.inc').read_text();fixture=(PRIOR/'fixture.cpp').read_text()
        body=change(body,'void** GuestSessionSlots=nullptr;','__declspec(dllimport) void** GuestSessionSlots;')
        body=change(body,'std::uint64_t GuestSessionParent=0,GuestSessionReadRax=0,GuestSessionWorkerRax=0;','__declspec(dllimport) std::uint64_t GuestSessionParent,GuestSessionReadRax,GuestSessionWorkerRax;')
        body=change(body,'unsigned char GuestSessionReadXmm[16]{},GuestSessionWorkerXmm[16]{};','__declspec(dllimport) unsigned char GuestSessionReadXmm[16],GuestSessionWorkerXmm[16];')
        body=re.sub(r'unsigned char GuestSessionPattern\[32\]=\{[^}]+\};','__declspec(dllimport) unsigned char GuestSessionPattern[32];',body)
        body=change(body,'uintptr_t HwbpFixtureUser=0;','__declspec(dllimport) uintptr_t HwbpFixtureUser;')
        body=change(body,'HardwareFixtureSnapshot HwbpFixtureBefore{},HwbpFixtureAfter{};','__declspec(dllimport) HardwareFixtureSnapshot HwbpFixtureBefore,HwbpFixtureAfter;')
        body=change(body,'alignas(16) unsigned char HwbpFixtureSeed[256]{};','__declspec(dllimport) unsigned char HwbpFixtureSeed[256];')
        body=change(body,'std::int32_t HwbpFixtureFetched=-999;','__declspec(dllimport) std::int32_t HwbpFixtureFetched;')
        body=re.sub(r'(?<!\w)(std::uint64_t|void) (GuestSession\w+(?:Invoke|Original|Return))\(',r'__declspec(dllimport) \1 \2(',body)
        body=change(body,'void HwbpFixtureSite();extern unsigned char HwbpFixtureBeforeCall;','__declspec(dllimport) void HwbpFixtureSite();__declspec(dllimport) unsigned char HwbpFixtureBeforeCall;\n__declspec(dllimport) void HostBankArmed();')
        body=change(body,'GuestSessionSlots=reinterpret_cast<void**>(alloc(0x1000));for(unsigned i=0;i<6;++i){GuestSessionSlots[i]=originals[i];c.hooks[i]={GuestSessionSlots+i,originals[i],bridges[i]};}','for(unsigned i=0;i<6;++i){check(GuestSessionSlots[i]==originals[i],"host original before arm");c.hooks[i]={GuestSessionSlots+i,originals[i],bridges[i]};}')
        body=change(body,'check(session.ArmHooks(),"all six hook slots armed");','check(session.ArmHooks(),"all six hook slots armed");HostBankArmed();')
        # Only native-business definitions are renamed/exported; immutable bridge
        # and Session targets stay local to each DLL.
        for n in ('User','Game','Update','Worker','Read'):
            body=re.sub(r'extern "C" (void|std::uint64_t) GuestSession'+n+r'Body',r'extern "C" __declspec(dllexport) \1 Bank'+n+'Body',body)
        auth=change(auth,'extern "C" void GuestSessionMenuBody','extern "C" __declspec(dllexport) void BankMenuBody')
        auth=change(auth,' put<uintptr_t>(self+0x470,originalList);',' put<DWORD>(base+0x19E7510+0x13C,0);put<DWORD>(base+0x1A38EC8+0x28,1); // Explicit native menu UI transition on shared base.\n put<uintptr_t>(self+0x470,originalList);')
        fixture=fixture.replace('static bool configureProfile(', 'extern \"C\" bool BankPlanningGraphRegression(uintptr_t,uintptr_t,uintptr_t);\nstatic bool configureProfile(',1)
        fixture=change(fixture,'        DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(world)', '        check(BankPlanningGraphRegression(base,layout.config.states[0],layout.config.states[1]),\"actual production planningGraph target force predicate\");\n        DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(world)')
        fixture=change(fixture,'int wmain(int argc,wchar_t**argv)','extern "C" __declspec(dllexport) int RunBank(int argc,wchar_t**argv)')
        layout=(P/'checkpoint_load_input_boundary_fixture_layout.h').read_text()
        layout=change(layout,'if(image)VirtualFree(image,0,MEM_RELEASE);','')
        layout=change(layout,'image=VirtualAlloc(nullptr,0x2200000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);','image=SharedGameBase;')
        layout=layout.replace('namespace checkpoint_load_input_boundary_fixture {','extern "C" __declspec(dllimport) void* SharedGameBase;\nnamespace checkpoint_load_input_boundary_fixture {',1)
        for n,s in [('fixture.cpp',fixture),('chain_body.inc',body),('chain_authorized.inc',auth),('checkpoint_load_input_boundary_fixture_layout.h',layout)]: (run/n).write_text(s)
        guard_header=(P/'checkpoint_live_runtime_guards_v2.h').read_text().replace('private:','public:').replace('bool planningGraph()const;','bool planningGraph()const;bool planningGraphLegacy()const;')
        (run/'guard_test_access.h').write_text(guard_header)
        guard=(P/'b_warm_two_bank_guards.cpp').read_text().replace('#include "checkpoint_live_runtime_guards_v2.h"','#include "guard_test_access.h"')
        legacy=(P/'b_warm_profile_guards.cpp').read_text();start=legacy.index('bool Context::planningGraph()const{');end=legacy.index('bool Context::body(',start)
        guard+='\nnamespace checkpoint_live_runtime_guards_v2 {\n'+legacy[start:end].replace('Context::planningGraph()','Context::planningGraphLegacy()')+'}\n'+(P/'b_warm_two_bank_guard_fixture.inc').read_text()
        (run/'guard_test.cpp').write_text(guard)
        # Compile host stable native callers and original functions first.
        data=['GuestSessionSlots','SharedGameBase','GuestSessionParent','GuestSessionReadRax','GuestSessionWorkerRax','GuestSessionReadXmm','GuestSessionWorkerXmm','GuestSessionPattern','HwbpFixtureUser','HwbpFixtureBefore','HwbpFixtureAfter','HwbpFixtureSeed','HwbpFixtureFetched','HwbpFixtureBeforeCall']
        names=[f'GuestSession{n}{kind}' for n in ('User','Menu','Game','Update','Worker','Read') for kind in ('Invoke','Original','Return')]+['HwbpFixtureSite','HostBankArmed']
        (run/'host.def').write_text('EXPORTS\n'+'\n'.join(names+[n+' DATA' for n in data])+'\n')
        common=f'/nologo /I"{run}" /I"{P}" /std:c++17 /EHa /W4 /WX /O2 /MT'
        cmd=(PRIOR/'fixture_build.cmd').read_text();flags=re.search(r'set flags=(.+)',cmd).group(1)
        cpp=re.findall(r'"([^"]+\.cpp)"',cmd);cpp=[Path(q) for q in cpp if not q.endswith('fixture.cpp')]
        cpp=[run/'guard_test.cpp' if q.name=='b_warm_profile_guards.cpp' else q for q in cpp]
        asm=['checkpoint_load_worker_bridge.asm','checkpoint_load_dispatch_bridge.asm','checkpoint_authorized_forward_admission_bridge.asm','checkpoint_live_storage_binding_fixture.asm']
        lines=['@echo off',f'call "{VC}" >nul','if errorlevel 1 exit /b 1',f'cd /d "{run}"']
        for i,n in enumerate(('checkpoint_guest_native_session_fixture.asm','checkpoint_native_input_hwbp_fixture.asm')):
            lines += [f'ml64 /nologo /I"{P}" /c /Fo host{i}.obj "{P/n}"','if errorlevel 1 exit /b 1']
        lines += [f'cl {common} /Fe:host.exe "{P/"b_warm_two_bank_fixture.cpp"}" "{P/"b_warm_two_bank_owner.cpp"}" host0.obj host1.obj /link /DEF:host.def /IMPLIB:host.lib /INCREMENTAL:NO','if errorlevel 1 exit /b 1']
        objects=[]
        for i,q in enumerate(cpp):

            if q.parent==P:result['source_pins'][str(q)]=sha(q)
            o=f'bank{i}.obj';objects.append(o);lines += [f'cl {common} {flags} /c /Fo:{o} "{q}"','if errorlevel 1 exit /b 1']
        for i,n in enumerate(asm):
            q=P/n;result['source_pins'][str(q)]=sha(q);o=f'bankasm{i}.obj';objects.append(o);lines += [f'ml64 /nologo /I"{P}" /c /Fo {o} "{q}"','if errorlevel 1 exit /b 1']
        lines += [f'cl {common} {flags} /LD /Fe:bank.dll /Fo:bankfixture.obj "{run/"fixture.cpp"}" '+ ' '.join(objects)+' host.lib /link /INCREMENTAL:NO','if errorlevel 1 exit /b 1']
        (run/'build.cmd').write_text('\n'.join(lines)+'\n')
        env=os.environ.copy();env['PYTHONUTF8']='1';r=subprocess.run(['cmd','/d','/c',str(run/'build.cmd')],cwd=run,capture_output=True,timeout=180,env=env);(run/'build.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,('build',r.returncode)
        production=run/'production';production.mkdir()
        pcmd=(PRIOR/'build.cmd').read_text().replace('b_warm_profile_guards.cpp','b_warm_two_bank_guards.cpp')
        (production/'build.cmd').write_text(pcmd)
        rr=subprocess.run(['cmd','/d','/c',str(production/'build.cmd')],cwd=production,capture_output=True,timeout=180,env=env);(production/'build.log').write_bytes(rr.stdout+rr.stderr);assert rr.returncode==0,('production build',rr.returncode)
        result['production_compile_only']=True
        archive=PRIVATE/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14';assert sha(archive)=='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c';result['private_pins'][str(archive)]=sha(archive)
        for i in (1,2):
            shutil.copyfile(run/'bank.dll',run/f'bank{i}.dll');(run/f'bank{i}').mkdir();(run/f'bank{i}'/'svdexccSC03.s14').write_bytes(archive.read_bytes()+(bytes(range(32)) if i==2 else b''))
        shutil.copyfile(run/'bank.dll',run/'stopped.dll')
        r=subprocess.run([str(run/'host.exe'),str(run/'bank1.dll'),str(run/'bank2.dll'),str(run)],cwd=run,capture_output=True,timeout=50,env=env);(run/'execution.log').write_bytes(r.stdout+r.stderr);result['exit']=r.returncode;assert r.returncode==0,('execution',r.returncode);assert b'"completed_banks":2' in r.stdout
        result['inputs_unchanged']=all(sha(Path(n))==h for field in ('source_pins','private_pins') for n,h in result[field].items());assert result['inputs_unchanged'];result['result']='PASS'
    except Exception as e:result['error']=repr(e)
    result['generated']={str(q):sha(q) for q in run.rglob('*') if q.is_file() and q.suffix in ('.cpp','.h','.inc','.def','.cmd')}
    result['binaries']={str(q):sha(q) for q in run.rglob('*') if q.is_file() and q.suffix in ('.dll','.exe','.obj','.lib')}
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(run/'result.json')}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
