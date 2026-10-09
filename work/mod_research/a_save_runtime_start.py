"""One controlled A fresh-save experiment. Default is read-only capture.

Requires explicit current PID and separately verified export/publisher builds.
Never retries a remote call, a save, a partial write or an uncertain publisher.
No timeline advancement, game load, force conversion or multiplayer claim.
"""
import argparse
import ctypes as C
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import struct
import subprocess
import sys
import time
from types import MappingProxyType

P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
sys.path[:0]=[str(P),str(PRIVATE/'python_deps'),str(P.parents[1]/'outputs/san14-link')]
from a_save_runtime_control import (require,sha,save_new,backup_saves,inventory,
    compare_saves,remote_call,RemoteCallUnknown)
import a_save_runtime_contract as wire


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def capture(pid):
    r=subprocess.run([sys.executable,str(P/'a_save_local_binding.py'),'--capture','--pid',str(pid)],
                     capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
    rows=[json.loads(s) for s in r.stdout.splitlines() if s.startswith('{')]
    require(r.returncode==0 and len(rows)==1 and rows[0]['result']=='PASS_READ_ONLY',
            'Read-only capture failed: '+r.stdout+r.stderr)
    path=Path(rows[0]['path']);value=read(path)
    require(value['pid']==pid and value['sources_unchanged'],'Capture attachment/source mismatch')
    for n,h in value['sources'].items():require(sha(P.parents[1]/n)==h,'Capture source changed: '+n)
    return path,value


def verify_sources(result):
    require(result.get('result')=='PASS' and isinstance(result.get('sources'),dict) and result['sources'],
            'Successful build with pinned sources required')
    for n,h in result['sources'].items():
        require(Path(n).name==n and Path(n).suffix in ('.h','.cpp','.asm','.inc','.py'),'Unexpected source path')
        require(sha(P/n)==h,'Build source changed: '+n)


def verified_artifact(folder, name, digest):
    found=list(Path(folder).rglob(name))
    found=[p for p in found if p.is_file() and sha(p)==digest]
    require(len(found)==1,'Expected exactly one pinned artifact: '+name)
    return found[0]


def publish(exe, operation, prep, module, dll, plans_file, snapshot_file, run, label):
    command=[str(exe),operation,str(prep.pid),str(prep.birth),str(prep.base),str(module),
             str(dll),sha(dll),str(plans_file),str(snapshot_file)]
    save_new(run/(label+'-intent.json'),dict(command=command,publisher_sha256=sha(exe),automatic_retry=False))
    with (run/(label+'-stdout.log')).open('xb') as out,(run/(label+'-stderr.log')).open('xb') as err:
        child=subprocess.Popen(command,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        save_new(run/(label+'-process.json'),dict(pid=child.pid))
        try:code=child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            save_new(run/(label+'-pending.json'),dict(pid=child.pid,may_own_debug_event=True,must_not_terminate=True))
            raise RemoteCallUnknown('Publisher unresolved; preserve controller and target state',dict(controller_pid=child.pid))
    rows=[json.loads(s) for s in (run/(label+'-stdout.log')).read_text(encoding='utf-8').splitlines() if s.startswith('{')]
    require(len(rows)==1,'Publisher result is missing or ambiguous')
    result=rows[0];save_new(run/(label+'-result.json'),dict(exit=code,report=result))
    require(not result.get('uncertain') and (not result.get('attached') or result.get('detached')),
            'Publisher has not proved clean detach')
    expected='INSTALLED' if operation=='install' else 'RESTORED' if operation=='restore' else 'PASS_READ_ONLY'
    if code==3 and result['status']=='REJECTED_HELD_NO_WRITES' and not result.get('written_mask'):
        return result  # Fresh observation may try another no-write window.
    require(code==0 and result['status']==expected,'Publication did not complete: '+result['status'])
    return result


def execute(args, capture_path, captured):
    # Build field formats are versioned by the concrete builders, not supplied
    # by peers. Required identities are checked again immediately before load.
    build=read(args.build_run/'result.json');publisher=read(args.publisher_build/'result.json')
    verify_sources(build['production']);verify_sources(publisher)
    require(build.get('result')=='PASS' and build.get('abi_executed') is True,'Export ABI execution not verified')
    for n,h in build['own_sources'].items():require(sha(P/n)==h,'Export ABI source changed: '+n)
    binaries=build['production']['binaries'];pubbins=publisher['binaries']
    dll_source=verified_artifact(args.build_run,'a_save_local_runtime.dll',binaries['a_save_local_runtime.dll'])
    publisher_exe=verified_artifact(args.publisher_build,'publisher.exe',pubbins['publisher.exe'])
    dependency=verified_artifact(args.build_run,'checkpoint_planning_hold.dll',binaries['checkpoint_planning_hold.dll'])
    schema_path=args.build_run/'schema.json'
    require(schema_path.is_file() and sha(schema_path)==build['generated']['schema.json'],'Missing exact bootstrap ABI schema')
    validate_schema(read(schema_path))
    from checkpoint_complete_live_capture import SOURCE,SOURCE_SHA
    require(sha(SOURCE)==SOURCE_SHA,'Original slot34 changed')
    run=PRIVATE/'a_save_runtime_live_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    save_new(run/'capture.json',captured)
    save_new(run/'build-inputs.json',dict(exports=str(args.build_run),exports_sha256=sha(args.build_run/'result.json'),
        publisher=str(args.publisher_build),publisher_sha256=sha(args.publisher_build/'result.json'),capture=str(capture_path)))
    before=backup_saves(SOURCE.parent,run/'original-saves')
    intent_directory=run/'native-intents';intent_directory.mkdir()
    prep=wire.prepare_from_capture(captured,SOURCE.parent,intent_directory)
    nonce=bytes(prep.nonce);filename='mp'+secrets.token_hex(4)+'.s14'
    require(not (SOURCE.parent/filename).exists(),'New filename collided')
    claim_dir=PRIVATE/'a_save_runtime_live_claims';claim_dir.mkdir(exist_ok=True)
    # A process has at most one retained bootstrap attempt, even if rejected.
    claim=claim_dir/f'{prep.pid}-{prep.birth}.json'
    require(not claim.exists(),'This process already has a retained A Runtime attempt; inspect it, do not replay')
    dll=run/dll_source.name;shutil.copyfile(dll_source,dll)
    dep=run/dependency.name;shutil.copyfile(dependency,dep)
    require(sha(dll)==sha(dll_source) and sha(dep)==sha(dependency),'Copied module identity differs')
    import pefile
    pe=pefile.PE(str(dll))
    try:exports={s.name.decode('ascii'):s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
    finally:pe.close()
    require(all('ASaveRuntime'+op in exports for op in wire.OPS),'Missing typed exports')
    from game_reader import GameReader
    from run_autonomous_pilot import ProcessAPI
    from checkpoint_push_start import process_birth
    reader=GameReader(pid=prep.pid);api=None;channel=None;module=0;serial=0;plans_file=None
    result=dict(result='INCOMPLETE',real_fresh_save=False,game_load=False,game_advance=False,
                two_game_ready=False,production_permit=False,cleanup_verified=False,automatic_retry=False)
    uncertain=False;prepared=False
    def call(op, value=None, *, allow_reject=False):
        nonlocal serial
        typ={'Prepare':wire.Prepare,'Plans':wire.Plans,'Snapshot':wire.Snapshot,'StartServer':wire.StartServer,'ServerStatus':wire.ServerStatus}.get(op,wire.Command)
        value=value if value is not None else wire.envelope(typ,op,nonce)
        serial+=1;label=f'{serial:03d}-{op}'
        code,raw=remote_call(api,module+exports['ASaveRuntime'+op],bytes(value),run,label)
        answer=wire.decode(typ,op,nonce,raw)
        save_new(run/(label+'-decoded.json'),wire.values(answer))
        if not allow_reject:require(code==0 and answer.header.result==0,f'{op} rejected: code={code}, result={answer.header.result}')
        return answer,run/(label+'-response.bin')
    def snapshot(deadline):
        while True:
            snap,path=call('Snapshot',allow_reject=True)
            if snap.header.result==0:return snap,path
            require(snap.header.result==10 and time.monotonic()<deadline,'Cannot obtain a stable Runtime snapshot')
            time.sleep(.05)
    def window(operation):
        deadline=time.monotonic()+10
        for attempt in range(20):
            snap,path=snapshot(deadline)
            if operation=='restore' and not snap.restoreReady:
                require(time.monotonic()<deadline,'Native drain not proved; retain sources')
                time.sleep(.1);continue
            outcome=publish(publisher_exe,operation,prep,module,dll,plans_file,path,run,f'{operation}-{attempt:02d}')
            if outcome['status'] in ('INSTALLED','RESTORED'):return
            require(time.monotonic()<deadline,'No quiet publication window; zero-write rejections retained')
        raise RuntimeError('Publication window unavailable; inspect retained source state')
    try:
        require((reader.pid,process_birth(reader),reader.memory.base)==(prep.pid,prep.birth,prep.base),'Attachment changed')
        # Capture immediately before any target mutation, after potentially slow
        # build hashing and backups. It is still a sample, not an input lock.
        _,fresh=capture(prep.pid)
        require(fresh['planning']==captured['planning'] and fresh['storage']==captured['storage'],'World/storage changed while preparing')
        save_new(claim,dict(pid=prep.pid,birth=prep.birth,run=str(run),nonce=nonce.hex(),filename=filename,dll_sha256=sha(dll),automatic_retry=False))
        api=ProcessAPI(reader)
        # Resolve/import DLL by full path while no debug event is held.
        existing=[(b,p) for b,p in api.modules() if p.name.casefold()==dep.name.casefold()]
        require(len(existing)<=1 and all(sha(p)==sha(dep) for _,p in existing),
                'An incompatible planning dependency is already loaded')
        remote_call(api,api.load_library_address(),str(dep).encode('utf-16le')+b'\0\0',run,'load-dependency')
        loaded_dependency=[(b,p) for b,p in api.modules() if p.name.casefold()==dep.name.casefold()]
        require(len(loaded_dependency)==1 and sha(loaded_dependency[0][1])==sha(dep),
                'Actual loaded planning dependency differs from approved build')
        save_new(run/'dependency-module.json',dict(base=loaded_dependency[0][0],path=str(loaded_dependency[0][1]),sha256=sha(dep)))
        remote_call(api,api.load_library_address(),str(dll).encode('utf-16le')+b'\0\0',run,'load-runtime')
        matches=[b for b,p in api.modules() if p.resolve()==dll.resolve()]
        require(len(matches)==1,'Runtime module load unresolved')
        module=matches[0];result['module_retained']=True
        call('Prepare',prep);prepared=True
        plans,plans_file=call('Plans')
        require((plans.pid,plans.birth,plans.base,plans.module)==(prep.pid,prep.birth,prep.base,module),'Plans belong to another attachment')
        call('ArmOwner')
        window('install')
        result['sources_published']=True
        call('ArmPublishedSources')
        deadline=time.monotonic()+10
        while True:
            snap,_=snapshot(deadline)
            require(not snap.error and not snap.ownerError and not snap.parentError and not snap.saveError,'Runtime failed before request')
            if snap.ready:break
            require(time.monotonic()<deadline,'Natural parent did not initialize in time')
            time.sleep(.1)
        from a_save_ipc_client import Endpoint,ASaveClient
        from checkpoint_fresh_save_binding import SaveReservation
        secret=secrets.token_bytes(32);pipe='\\\\.\\pipe\\san14-a-save-'+secrets.token_hex(16)
        start=wire.envelope(wire.StartServer,'StartServer',nonce);start.clientPid=os.getpid();start.idleTimeoutMs=30000
        wire.put_bytes(start.secret,secret);wire.put_wide(start.pipeName,pipe)
        call('StartServer',start)
        faults=[];channel=ASaveClient(Endpoint(pipe,prep.pid,prep.birth,secret),on_fault=faults.append,timeout=10)
        request=dict(generation=1,room_epoch=prep.nativeRoomEpoch,period=1,cut=0,room_id=bytes(prep.roomId),
            year=prep.year,ruler=prep.ruler,month=prep.month,day=prep.day,force=prep.force,reserved=0,filename=filename)
        binding=hashlib.sha256(bytes(prep)+filename.encode('ascii')).hexdigest()
        save_new(run/'save-submit-intent.json',dict(filename=filename,binding_sha256=binding,exactly_once=True))
        channel.submit(SaveReservation(1,binding,MappingProxyType(request)))
        artifact=channel.wait_artifact(1,timeout=30)
        with (run/filename).open('xb') as out:out.write(artifact.data)
        require(sha(SOURCE.parent/filename)==artifact.sha256==sha(run/filename),'Native disk and exported bytes differ')
        save_new(run/'artifact.json',dict(filename=filename,sha256=artifact.sha256,size=len(artifact.data),report=dict(artifact.report)))
        result.update(real_fresh_save=True,filename=filename,save_sha256=artifact.sha256,save_bytes=len(artifact.data))
        channel.stop();channel.close();channel=None
    except RemoteCallUnknown as exc:
        uncertain=True;result.update(error=repr(exc),uncertain=exc.record)
    except Exception as exc:result['error']=repr(exc)
    finally:
        if channel:channel.close()
        if api and module and prepared and not uncertain:
            try:
                call('Stop')
                deadline=time.monotonic()+10
                while True:
                    service,_=call('ServerStatus')
                    if not service.started or service.threadExited:break
                    require(time.monotonic()<deadline,'IPC thread has not exited; retain sources')
                    time.sleep(.1)
                require(plans_file is not None,'Missing published-source plan')
                window('restore')
                result['sources_restored']=True
                # No unload: retained objects, thunks and storage leases live
                # until normal game-process exit.
                from a_save_observation_status import preflight
                after=preflight(prep.pid);save_new(run/'post-preflight.json',after)
                require(after['result']=='PASS_READ_ONLY','Post-restore map/source check failed')
                result['cleanup_verified']=True
            except Exception as exc:result['cleanup_error']=repr(exc)
        if api:api.close()
        reader.close()
        try:
            after=inventory(SOURCE.parent)
            result['save_comparison']=compare_saves(before,after,filename,result.get('save_sha256'))
            save_new(run/'save-files-after.json',after)
        except Exception as exc:result['inventory_error']=repr(exc)
        good=result.get('save_comparison',{})
        if result['real_fresh_save'] and result['cleanup_verified'] and good.get('originals_unchanged') and good.get('only_expected_new_file') and good.get('new_hash_matches') and not result.get('error'):
            result['result']='PASS_REAL_SINGLE_FRESH_SAVE'
        else:result['result']='INCOMPLETE_RETAIN_EVIDENCE'
        save_new(run/'result.json',result)
    print(json.dumps(dict(result=result['result'],path=str(run/'result.json'),real_fresh_save=result['real_fresh_save'],cleanup_verified=result['cleanup_verified']),ensure_ascii=False))
    return 0 if result['result']=='PASS_REAL_SINGLE_FRESH_SAVE' else 1


def validate_schema(schema):
    # The native schema executable supplies sizes and direct field offsets.
    for name,kind in wire.TYPES.items():
        row=schema['structures'][name]
        require(row['size']==C.sizeof(kind),'Native ABI size differs: '+name)
        for field,typ in kind._fields_:
            native=row['fields'][field]
            require(native['offset']==getattr(kind,field).offset and native['size']==C.sizeof(typ),
                    'Native ABI field differs: '+name+'.'+field)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True);parser.add_argument('--execute',action='store_true')
    parser.add_argument('--build-run',type=Path);parser.add_argument('--publisher-build',type=Path)
    args=parser.parse_args()
    if args.pid<=0:parser.error('positive explicit PID required')
    if args.execute and (not args.build_run or not args.publisher_build):parser.error('--execute requires both tested builds')
    path,value=capture(args.pid)
    if not args.execute:print(json.dumps(dict(result='PASS_READ_ONLY',capture=str(path),native_requests=0)));return 0
    return execute(args,path,value)


if __name__=='__main__':raise SystemExit(main())
