"""Own PE + owned memory only; no SAN14/Steam/process discovery/installer."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

P=Path(__file__).resolve().parent
CASES=('success','owned-read-hook','unowned-read-hook','foreign-read-hook',
       'generation-global','generation-token','storage-change','vtable-change',
       'owner-invalidation','owner-mutates-generation','owner-fault','invalidated',
       'token-noaccess','allowed-new-thread','bad-file-sha','bad-module-base',
       'bad-module-owner','bad-module-path','bad-header','bad-attachment',
       'bad-version','bad-fastpath','bad-method-code','cross-page-code')
SOURCES=tuple('checkpoint_live_storage_binding'+suffix for suffix in
    ('.h','.cpp','_fixture.cpp','_fixture.asm','_build.cmd','_test.py'))+('native_storage_read_core.h','native_storage_read_core.cpp')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    folder=P/'checkpoint_live_storage_binding_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    sources={name:sha(P/name) for name in SOURCES}
    built=subprocess.run(['cmd','/c',str(P/'checkpoint_live_storage_binding_build.cmd')],cwd=P,capture_output=True)
    (folder/'build.log').write_bytes(built.stdout+built.stderr)
    if built.returncode:
        print(built.stdout.decode(errors='replace'));raise SystemExit(built.returncode)
    exe=P/'checkpoint_live_storage_binding_fixture.exe';digest=sha(exe);rows=[]
    for case in CASES:
        proc=subprocess.run([str(exe),case,digest],cwd=P,capture_output=True,timeout=15)
        (folder/(case+'.stdout.txt')).write_bytes(proc.stdout);(folder/(case+'.stderr.txt')).write_bytes(proc.stderr)
        lines=[x for x in proc.stdout.decode(errors='replace').splitlines() if x.startswith('{')]
        row=json.loads(lines[-1]) if lines else {'case':case,'passed':False}
        row.update(exit_code=proc.returncode);row['passed']=bool(row['passed'] and not proc.returncode);rows.append(row)
    stable=sources=={name:sha(P/name) for name in SOURCES}
    result={'schema':'san14.live-storage-binding-fixtures.v1','result':'PASS' if stable and all(x['passed'] for x in rows) else 'FAIL',
            'cases':rows,'source_sha256':sources,'source_unchanged_during_build_and_run':stable,
            'fixture_binary_sha256':digest,'production_object_sha256':sha(P/'checkpoint_live_storage_binding_production.obj'),
            'fixture_core_sha256':sha(P/'checkpoint_live_storage_binding_fixture_core.obj'),
            'game_access':False,'steam_access':False,'native_steam_calls':0,'installer':False,
            'scope':'Real own PE modules, VirtualQuery/GetModuleHandleEx(PIN), approved file hash, mapped PE-header hash, 32-byte endpoint code, archived fastpath shape with own RIP-relative counter; synthetic heap game layout. No ContextInit call; only fixture explicitly calls its own original read stub.'}
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'result':result['result'],'cases':len(rows),'failed':[x['case'] for x in rows if not x['passed']],'path':str(folder/'result.json')}))
    raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
