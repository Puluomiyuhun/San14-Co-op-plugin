"""Own-process native fixtures with two actual byte payloads; no game API."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
FROZEN=('checkpoint_load_request_commit','checkpoint_cc_load_observer','checkpoint_cc_load_lifecycle')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder=ROOT/'checkpoint_dynamic_files_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    before={str(ROOT/(stem+ext)):sha(ROOT/(stem+ext)) for stem in FROZEN for ext in ('.cpp','.h')}
    build=subprocess.run(['cmd','/c',str(ROOT/'checkpoint_dynamic_files_build.cmd')],capture_output=True,timeout=90)
    (folder/'build.log').write_bytes(build.stdout+build.stderr)
    if build.returncode:raise RuntimeError('Native /W4 /WX build failed: '+str(folder/'build.log'))
    payloads=[]
    for size,seed in ((257,17),(65537,193)):
        path=folder/f'payload-{size}.bin'
        path.write_bytes(bytes((i*29+seed+(i>>8))%256 for i in range(size)))
        payloads.append(path)
    results=[]
    def run(exe,args,label):
        proc=subprocess.run([str(ROOT/exe),*map(str,args)],capture_output=True,timeout=20)
        output=(proc.stdout+proc.stderr).decode('utf-8','replace')
        row={'label':label,'exit':proc.returncode,'output':output,'passed':False}
        lines=[line for line in output.splitlines() if line.startswith('{')]
        if lines:
            row['native']=json.loads(lines[-1]);row['passed']=proc.returncode==0 and row['native'].get('passed') is True
        results.append(row)
    run('checkpoint_dynamic_file_profile_fixture.exe',[],'profile contract')
    request_cases=('success','wrong-profile-hash','read-corrupt','read-short','read-seh','pending-during-read',
                   'reject-before-cas','reject-after-cas','existing-intent','missing-menu','busy-user')
    byte_cases=('success','wrong-profile-hash','wrong-hash','wrong-size','wrong-name','short-read','negative-read',
                'read-seh','read-cpp','worker-seh','worker-cpp','duplicate-read','duplicate-worker','missing-read',
                'title-transparent','concurrent-unowned','stop-during-read','wrong-parent','bad-buffer')
    for payload in payloads:
        for case in request_cases:
            dest=folder/f'request-{payload.stem}-{case}';dest.mkdir()
            run('checkpoint_dynamic_load_request_commit_fixture.exe',[case,payload,dest/'svdexccSC03.s14',dest/'intent.bin'],f'request {payload.stem} {case}')
        for case in byte_cases:
            run('checkpoint_dynamic_cc_load_observer_fixture.exe',[case,payload],f'bytes {payload.stem} {case}')
    for case in ('success','success-large','profile-mismatch','bad-byte-hash','bad-byte-token','missing-byte-finally',
                 'snapshot-after-free','wait-phase2','wrong-request-slot','wrong-request-name','uncleared-slot',
                 'join-handle-left','failure-status','wrong-pop','missing-join','original-seh','original-cpp'):
        run('checkpoint_dynamic_cc_load_lifecycle_fixture.exe',[case],'lifecycle '+case)
    after={path:sha(Path(path)) for path in before}
    record={'passed':all(row['passed'] for row in results) and before==after,'cases':len(results),
            'results':results,'payloads':[{'path':str(x),'size':x.stat().st_size,'sha256':sha(x)} for x in payloads],
            'compiler':'MSVC /W4 /WX /EHa /O2 /MT C++17; production cores and fixture cores both compiled',
            'frozen_before':before,'frozen_after':after,'frozen_sources_unchanged':before==after,
            'coverage':'Request uses real boundary, native storage verifier and CAS in own-process memory; Bytes uses real assembly worker/read bridges and real SHA of two payloads; Lifecycle native calls and byte receipt are explicit doubles',
            'game_access':False,'native_world_loaded':False}
    (folder/'result.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'passed':record['passed'],'cases':record['cases'],'failures':[r for r in results if not r['passed']],'result':str(folder/'result.json')},indent=2))
    return 0 if record['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
