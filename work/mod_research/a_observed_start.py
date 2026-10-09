"""Explicit A observed Room entry using the approved native-turn lifecycle.

Default CLI only describes the callable interface. No process discovery, live
execution, room creation, automatic Ready or native advancement at import/main.
execute is a reviewed successor of a_native_turn_start.execute; all native
preflight/claim/publication/unknown/Stop/drain/restore checks remain in place.
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
import sys
import time
import threading
from copy import deepcopy

P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
sys.path[:0]=[str(P),str(PRIVATE/'python_deps'),str(P.parents[1]/'outputs/san14-link')]
from a_native_turn_start import (capture,verify_launcher_tests,verify_native_build,verified_artifact,
    publish,post_turn_check,compare_two_files)
from a_save_runtime_control import (require,sha,save_new,backup_saves,inventory,
    RemoteCallUnknown)
from a_observed_start_call import remote_call
import a_save_runtime_contract as wire
import a_save_repeat_contract as repeat
import a_native_turn_start_control as turn
import a_save_failure_diagnostic as failure_diagnostic
import a_room_native_control as room_control
from a_room_bootstrap_protocol import BootstrapCoordinator
from a_observed_room import ObservedRoom,ObservedFreshSaveBinding
from a_observed_boundary import AObservedBoundary
from authoritative_sync import digest
from b_warm_remote_completion import key_check


class RoomEntry:
    """Retains the exact Room, native channel control and finite observer."""
    def __init__(self,room,coordinator,adapter_key,*,no_new_commands):
        require(type(room) is ObservedRoom and type(coordinator) is BootstrapCoordinator,
                'Exact observed Room/coordinator required')
        require(no_new_commands is True,'Human no-new-command agreement required')
        key_check(adapter_key)
        self.room,self.coordinator,self.key=room,coordinator,adapter_key
        self.control=room_control.RoomTurnControl()
        self.binding=self.prep=self.provider=None
        self.last_artifact=None;self.phase='FRESH';self.error=None;self._closing=False
        self._scope=deepcopy(coordinator.scope)
        self.check_fresh()

    def check_fresh(self):
        with self.room.lock,self.coordinator.lock:
            self.room._bound(self.coordinator)
            require(self.phase=='FRESH' and self.coordinator.phase=='PLANNING' and
                self.coordinator.period==1 and self.coordinator.scope==self._scope and
                self.coordinator.connected=={'A','B'} and self.room._remote is None,
                'Fresh connected Room without prior adapter required')

    def prepare(self,prep):
        self.check_fresh();self.phase='PREPARING'
        try:
            with self.room.lock,self.coordinator.lock:
                self.binding=ObservedFreshSaveBinding(self.room,self.coordinator,
                    native_room_id=bytes.fromhex(digest(self._scope)),native_room_epoch=prep.nativeRoomEpoch,
                    artifact_reader=self.control.copy_artifact,source_kind='LOCAL_NATIVE_PROVIDER')
                self.coordinator.begin_bootstrap()
                self.prep=room_control.prepare_from_room(prep,self.binding)
            self.phase='PREPARED'
            return wire.Prepare.from_buffer_copy(bytes(self.prep))
        except BaseException:
            self.hold('ROOM_PREPARATION_FAILED');raise

    def bind_runtime(self,prep,reader,plans,*,read_birth,runtime_snapshot):
        require(self.phase=='PREPARED' and bytes(prep)==bytes(self.prep),'Prepared native identity changed')
        try:
            self.provider=AObservedBoundary(reader,pid=prep.pid,birth=prep.birth,base=prep.base,
                root=prep.root,world_address=prep.world,cache=prep.cache,force=prep.force,ruler=prep.ruler,
                nonce=bytes(prep.nonce),plans=plans,read_birth=read_birth,runtime_snapshot=runtime_snapshot,
                no_new_commands=True)
            self.provider.observe(deepcopy(self.coordinator.node))
            self.room.enroll_observed_adapter(self.key,host_sampler=self._sample,
                host_boundary=self._boundary,host_receipt_key=self._receipt,source_kind='LOCAL_NATIVE_PROVIDER')
            self.phase='BOUND'
        except BaseException:
            self.hold('RUNTIME_OBSERVER_BIND_FAILED');raise

    def _receipt(self):
        require(self.last_artifact is not None,'No current channel artifact receipt')
        return self.last_artifact.sha256

    def _boundary(self,profile,kind):
        require(not self._closing and self.provider is not None and self.phase=='RUNNING','A adapter is not running')
        node=dict(year=profile.loaded.year,month=profile.loaded.month,day=profile.loaded.day,phase='PLANNING_BOUNDARY')
        return self.provider.observe(node,profile)

    def _sample(self,profile,key):
        require(not self._closing and self.phase=='RUNNING' and key==self._receipt(),'Foreign/closed channel artifact receipt')
        c=self.coordinator
        return self.provider.sample(scope=c.scope,epoch=c.epoch,period=c.period,profile=profile,receipt_key=key)

    def drive(self,channel,prep,filenames,call,keep,event,*,wait_seconds):
        require(self.phase=='BOUND' and bytes(prep)==bytes(self.prep),'Bound entry already used or changed')
        self.phase='RUNNING'
        def kept(generation,filename,artifact):
            keep(generation,filename,artifact)
            self.last_artifact=artifact
        try:
            result=self.control.drive(channel,prep,filenames,call,kept,event,self.binding,
                lambda node:self.provider.world_observation(node,self.binding._host_attachment),
                wait_seconds=wait_seconds)
            self.phase='TWO_COMPLETIONS_RETAINED'
            return result
        except BaseException:
            self.hold('ROOM_NATIVE_CONTROL_FAILED');raise

    def hold(self,reason):
        self.phase='HELD';self.error=self.error or reason
        with self.room.lock,self.coordinator.lock:
            if self.binding is not None:self.binding.hold(reason)
            self.room._held=reason;self.coordinator.ready.clear();self.coordinator.phase='HELD'

    def close_observation(self):
        # All enrolled handlers already hold room/coordinator before sampling.
        # Drain those local callbacks before any pipe/native/reader cleanup.
        # This is a Python callback lifetime barrier, never an engine fence.
        with self.room.lock,self.coordinator.lock:
            self._closing=True
            if self.provider is not None:
                with self.provider._lock:pass

    def status(self):
        return dict(phase=self.phase,error=self.error,formal_completions=len(self.coordinator.applied_receipts),
            input_exclusion_proven=False,scheduler_fence_proven=False,atomic_snapshot=False,
            full_world_verified=False,native_gameplay_enabled=False)


def verify_entry_tests(folder):
    value=json.loads((Path(folder)/'result.json').read_text())
    require(value.get('result')=='PASS' and value.get('game_access') is False and
        value.get('entry_integration_executed') is True and value.get('sources_unchanged') is True,
        'Passing observed entry integration tests required')
    for name,expected in value['sources'].items():require(sha(Path(name))==expected,'Entry source changed: '+name)
    require(str(Path(__file__).resolve()) in value['sources'],'Entry test does not bind this source')


def execute(args, capture_path, captured, *, entry, on_event):
    # Build field formats are versioned by the concrete builders, not supplied
    # by peers. Required identities are checked again immediately before load.
    require(type(entry) is RoomEntry and callable(on_event), "Exact retained room entry and event callback required")
    verify_entry_tests(args.entry_test_run)
    entry.check_fresh()
    verify_launcher_tests(args.launcher_test_run)
    build, abi_dir, publisher = verify_native_build(args)
    binaries=build['production']['binaries'];pubbins=publisher['binaries']
    dll_source=verified_artifact(args.build_run,'a_save_local_runtime.dll',binaries['a_save_local_runtime.dll'])
    publisher_exe=verified_artifact(args.publisher_build,'publisher.exe',pubbins['publisher.exe'])
    dependency=verified_artifact(args.build_run,'checkpoint_planning_hold.dll',binaries['checkpoint_planning_hold.dll'])
    from checkpoint_complete_live_capture import SOURCE,SOURCE_SHA
    require(sha(SOURCE)==SOURCE_SHA,'Original slot34 changed')
    run=PRIVATE/'a_observed_start_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    save_new(run/'capture.json',captured)
    save_new(run/'build-inputs.json',dict(exports=str(args.build_run),exports_sha256=sha(args.build_run/'result.json'),
        publisher=str(args.publisher_build),publisher_sha256=sha(args.publisher_build/'result.json'),capture=str(capture_path),
        launcher_sha256=sha(Path(__file__)),diagnostic_sha256=sha(P/'a_save_failure_diagnostic.py')))
    before=backup_saves(SOURCE.parent,run/'original-saves')
    intent_directory=run/'native-intents';intent_directory.mkdir()
    prep=entry.prepare(wire.prepare_from_capture(captured,SOURCE.parent,intent_directory))
    nonce=bytes(prep.nonce);filenames=['mp'+secrets.token_hex(4)+'.s14' for _ in range(2)]
    require(len(set(filenames))==2 and all(not (SOURCE.parent/n).exists() for n in filenames),'New filename collided')
    require(prep.epoch<2**64-1 and prep.period<2**64-1,'Next binding overflow')
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
    require(all('ASaveRuntime'+op in exports for op in repeat.OPS),'Missing typed exports')
    # Reject incompatible builds before any target mutation.
    failure_diagnostic.export_layout(dll,sha(dll))
    from game_reader import GameReader
    from run_autonomous_pilot import ProcessAPI
    from checkpoint_push_start import process_birth
    reader=GameReader(pid=prep.pid);api=None;channel=None;module=0;serial=0;plans_file=None
    result=dict(result='INCOMPLETE',real_fresh_save=False,artifacts=[],game_load=False,game_advance_called=False,
                two_game_ready=False,production_permit=False,cleanup_verified=False,automatic_retry=False)
    uncertain=False;prepared=False
    call_lock=threading.RLock()
    def _call(op, value=None, *, allow_reject=False):
        nonlocal serial,uncertain
        require(not uncertain, "Prior native call unresolved; no further native control")
        typ={'RequestNext':repeat.Next,'RepeatSnapshot':repeat.Snapshot,'Prepare':wire.Prepare,'Plans':wire.Plans,'Snapshot':wire.Snapshot,'StartServer':wire.StartServer,'ServerStatus':wire.ServerStatus}.get(op,wire.Command)
        codec=repeat if op in ('RequestNext','RepeatSnapshot') else wire
        value=value if value is not None else codec.envelope(typ,op,nonce)
        serial+=1;label=f'{serial:03d}-{op}'
        try:
            code,raw=remote_call(api,module+exports['ASaveRuntime'+op],bytes(value),run,label)
        except RemoteCallUnknown as exc:
            uncertain=True
            result.update(uncertain=exc.record,unknown_operation=op)
            raise
        answer=codec.decode(typ,op,nonce,raw)
        save_new(run/(label+'-decoded.json'),wire.values(answer))
        if not allow_reject:require(code==0 and answer.header.result==0,f'{op} rejected: code={code}, result={answer.header.result}')
        return answer,run/(label+'-response.bin')
    def call(op, value=None, *, allow_reject=False):
        with call_lock:return _call(op,value,allow_reject=allow_reject)
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
            if operation=='restore':
                repeated,_=call('RepeatSnapshot')
                turn.cleanup_gate(repeated)
            if operation=='restore' and snap.restoreReady!=1:
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
        save_new(claim,dict(pid=prep.pid,birth=prep.birth,run=str(run),nonce=nonce.hex(),filenames=filenames,dll_sha256=sha(dll),automatic_retry=False))
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
        entry.bind_runtime(prep,reader,plans,read_birth=lambda:process_birth(reader),
            runtime_snapshot=lambda:snapshot(time.monotonic()+2)[0])
        from a_save_ipc_client import Endpoint,ASaveClient
        from checkpoint_fresh_save_binding import SaveReservation
        secret=secrets.token_bytes(32);pipe='\\\\.\\pipe\\san14-a-save-'+secrets.token_hex(16)
        start=wire.envelope(wire.StartServer,'StartServer',nonce);start.clientPid=os.getpid();start.idleTimeoutMs=30000
        wire.put_bytes(start.secret,secret);wire.put_wide(start.pipeName,pipe)
        call('StartServer',start)
        faults=[];channel=ASaveClient(Endpoint(pipe,prep.pid,prep.birth,secret),on_fault=faults.append,timeout=10)
        def event(kind, info):
            save_new(run/(kind+'-event.json'),info)
            print(json.dumps(dict(event=kind,**info),ensure_ascii=False),flush=True)
            on_event(kind,info)
        def keep(generation, filename, artifact):
            require(artifact.report['generation']==generation,'Artifact generation differs')
            with (run/filename).open('xb') as out:
                require(out.write(artifact.data)==len(artifact.data),'Short artifact write')
                out.flush();os.fsync(out.fileno())
            require(sha(SOURCE.parent/filename)==artifact.sha256==sha(run/filename),'Native disk and exported bytes differ')
            row=dict(generation=generation,filename=filename,sha256=artifact.sha256,size=len(artifact.data),report=dict(artifact.report))
            save_new(run/f'artifact-{generation}.json',row);result['artifacts'].append(row);result['real_fresh_save']=True
        result.update(entry.drive(channel,prep,filenames,call,keep,event,wait_seconds=args.wait_seconds))
        channel.stop();channel.close();channel=None
    except RemoteCallUnknown as exc:
        entry.hold('REMOTE_CALL_UNKNOWN')
        uncertain=True;result.update(error=repr(exc),uncertain=exc.record)
    except Exception as exc:
        entry.hold('A_ENTRY_FAILED')
        result['error']=repr(exc)
    finally:
        entry.close_observation()
        # Diagnosis is read-only even after an uncertain control call. Failure
        # to observe must not mask the original error or skip normal cleanup.
        if module:
            try:
                diagnosis=failure_diagnostic.observe(prep.pid,prep.birth,reader.memory.path,
                    reader.sha256,module,dll,sha(dll))
                save_new(run/'first-failure-diagnostic.json',diagnosis)
                result['first_failure_diagnostic']=diagnosis['status']
            except Exception as exc:
                result['first_failure_diagnostic_error']=repr(exc)
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
                after=post_turn_check(reader,prep)
                save_new(run/'post-turn-readonly.json',after)
                result['cleanup_verified']=True
            except RemoteCallUnknown as exc:
                result.update(cleanup_error=repr(exc),cleanup_uncertain=exc.record)
            except Exception as exc:result['cleanup_error']=repr(exc)
        if api:api.close()
        reader.close()
        try:
            after=inventory(SOURCE.parent)
            result['save_comparison']=compare_two_files(before,after,result['artifacts'])
            save_new(run/'save-files-after.json',after)
        except Exception as exc:result['inventory_error']=repr(exc)
        good=result.get('save_comparison',{})
        result['room_entry']=entry.status()
        if result.get('formal_completions')==2 and result.get('two_native_artifacts') and result['cleanup_verified'] and good.get('originals_unchanged') and good.get('only_expected_new_files') and good.get('new_hashes_match') and not result.get('error'):
            result['result']='PASS_OBSERVED_ROOM_TWO_SAVES'
        else:result['result']='INCOMPLETE_RETAIN_EVIDENCE'
        save_new(run/'result.json',result)
    print(json.dumps(dict(result=result['result'],path=str(run/'result.json'),real_fresh_save=result['real_fresh_save'],cleanup_verified=result['cleanup_verified']),ensure_ascii=False))
    return 0 if result['result']=='PASS_OBSERVED_ROOM_TWO_SAVES' else 1



def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.epilog='Callable: RoomEntry(room, coordinator, adapter_key, no_new_commands=True), then execute(args, capture_path, captured, entry=entry, on_event=callback). Network owner supplies authenticated connected Room.'
    parser.parse_args();parser.print_help();return 0


if __name__=='__main__':raise SystemExit(main())
