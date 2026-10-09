"""Actual warm six-bridge composition: complete, retire, restore, retained calls."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,shutil,subprocess
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
CASES=('success-new','report-state','user-exception','stop-during-load','restore-conflict')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=PRIVATE/'b_warm_retire_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result={'result':'FAIL','game_process_access':False,'steam_save_access':False};sources={}
    def pin(path):
        path=path.resolve()
        if str(path) in sources:return
        sources[str(path)]=sha(path)
        if path.suffix in ('.cpp','.h','.inc'):
            for name in re.findall(r'#include "([^"]+)"',path.read_text()):
                f=path.parent/name
                if not f.exists():f=P/name
                if f.exists():pin(f)
    for n in ('b_warm_retire_session.h','b_warm_retire_session.cpp','b_warm_retire_admission.cpp','b_warm_retire_owner.cpp','b_warm_retire_test.py','b_warm_retire_fixture.inc'):pin(P/n)
    try:
        archive=PRIVATE/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
        assert sha(archive)=='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
        result['private_archive_sha256']=sha(archive)
        body=(P/'checkpoint_complete_live_owner_v2_chain_body.inc').read_text();pin(P/'checkpoint_complete_live_owner_v2_chain_body.inc')
        body='static bool warmLate=false;static unsigned warmLateBodies[6]{};\n'+body
        for i,stem in enumerate(('User','Menu','Game','Update','Worker','Read')):
            pattern=r'(extern "C" (?:void|std::uint64_t) GuestSession'+stem+r'Body\([^\n]*\)\s*\{)'
            body,count=re.subn(pattern,r'\1'+('if(warmLate){++warmLateBodies['+str(i)+'];return'+(' 77' if stem=='Read' else '')+';}'),body,count=1);assert count==1,stem
        body=body.replace('check(pr::Initialize(planning,planningConfig),"observer bound to actual Session before hook installation");','check(pr::Initialize(planning,planningConfig),"observer bound to actual Session before hook installation");check(b_warm_retire::Bind(session,planning),"immutable retirement binding");')
        body=body.replace('++planningBodies;check(','++planningBodies;if(scenario==L"restore-conflict"){DWORD old=0;check(VirtualProtect(GuestSessionSlots,4096,PAGE_READWRITE,&old)!=0,"owned conflict write");GuestSessionSlots[1]=reinterpret_cast<void*>(0x12345678);check(VirtualProtect(GuestSessionSlots,4096,old,&old)!=0,"owned conflict protection");}check(',1)
        (run/'chain_body.inc').write_text(body)
        auth=(P/'checkpoint_complete_live_owner_v2_chain_authorized.inc').read_text();pin(P/'checkpoint_complete_live_owner_v2_chain_authorized.inc')
        auth=auth.replace('"checkpoint_complete_live_owner_v2_chain_body.inc"','"chain_body.inc"')
        auth=auth.replace('extern "C" void GuestSessionMenuBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){','extern "C" void GuestSessionMenuBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){if(warmLate){++warmLateBodies[1];return;}',1)
        (run/'chain_authorized.inc').write_text(auth)
        fixture=(P/'checkpoint_complete_live_owner_v2_fixture.cpp').read_text();pin(P/'checkpoint_complete_live_owner_v2_fixture.cpp')
        fixture=fixture.replace('"checkpoint_complete_live_owner_v2.cpp"','"b_warm_retire_owner.cpp"').replace('"checkpoint_complete_live_owner_v2_chain_authorized.inc"','"chain_authorized.inc"')
        begin=fixture.index('    if(s.casPublished){',fixture.index('const int result=CompleteOwnerChainMain'));end=fixture.index('    check(writeReport',begin)
        fixture=fixture[:begin]+(P/'b_warm_retire_fixture.inc').read_text()+fixture[end:];(run/'fixture.cpp').write_text(fixture)
        for kind in ('build','fixture_build'):
            path=P/('checkpoint_complete_live_owner_v2_'+kind+'.cmd');pin(path);cmd=path.read_text()
            cmd=cmd.replace('checkpoint_forward_native_session.cpp','b_warm_retire_session.cpp').replace('checkpoint_authorized_forward_admission_controller.cpp','b_warm_retire_admission.cpp').replace('checkpoint_complete_live_owner_v2.cpp','b_warm_retire_owner.cpp')
            for name in set(re.findall(r'\b[\w]+\.(?:cpp|asm)\b',cmd)):
                source=P/name
                if name=='checkpoint_complete_live_owner_v2_fixture.cpp':source=run/'fixture.cpp'
                else:pin(source)
                cmd=cmd.replace(name,'"'+str(source)+'"')
            cmd=cmd.replace('/nologo /std:c++17','/nologo /I"'+str(P)+'" /std:c++17')
            (run/(kind+'.cmd')).write_text(cmd)
            proc=subprocess.run(['cmd','/c',str(run/(kind+'.cmd'))],cwd=run,capture_output=True,timeout=180);(run/(kind+'.log')).write_bytes(proc.stdout+proc.stderr);assert proc.returncode==0,kind
        rows=[]
        for case in CASES:
            d=run/case;d.mkdir();local=d/'svdexccSC03.s14';shutil.copyfile(archive,local)
            proc=subprocess.run([str(run/'checkpoint_complete_live_owner_v2_fixture.exe'),case,str(local),str(d/'request.intent'),str(d/'identity.intent'),str(d/'report.bin')],capture_output=True,timeout=35)
            (d/'run.log').write_bytes(proc.stdout+proc.stderr);rows.append({'case':case,'exit':proc.returncode,'passed':proc.returncode==0,'archive_unchanged':sha(local)==sha(archive)})
        result['cases']=rows;assert all(x['passed'] and x['archive_unchanged'] for x in rows)
        assert all(sha(Path(n))==h for n,h in sources.items());result['result']='PASS'
    except Exception as e:result['error']=repr(e)
    result['source_sha256']=sources;result['source_unchanged']=all(sha(Path(n))==h for n,h in sources.items())
    result['binary_sha256']={str(p):sha(p) for p in run.iterdir() if p.suffix in ('.obj','.exe','.dll')}
    result['generated_sha256']={str(p):sha(p) for p in run.iterdir() if p.suffix in ('.cpp','.inc','.cmd')}
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(run/'result.json'),'error':result.get('error')}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
