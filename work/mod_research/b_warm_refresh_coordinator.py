"""Two-bank native publication/load successor; never physically stages CC03."""
import ctypes as C
from contextlib import ExitStack
import hashlib
from pathlib import Path
import secrets
import time

import b_warm_staging as files
import b_warm_profile_contract as bank_wire
import b_warm_coordinator_contract as hand_wire
from b_warm_coordinator import Resident as PreviousResident, HAND_EXPORTS, validate_pair, dates
from b_warm_profile_capture import capture_planning, wrap_owner_config
from b_warm_start import require, save_new, completion
from b_warm_refresh_start_support import identity, storage_bindings, make_config, validate_completed

REFRESH_EXPORTS=('DescribeBWarmRefreshOwner','InstallBWarmRefreshOwner','GetBWarmRefreshReport')


def record_observation(calls,bank,samples,row,trace):
    """Keep original reports and one read-only refresh snapshot on every sample.

    A failed/unknown snapshot is never retried here. The original native failure
    remains the primary exception when present and no control call is uncertain.
    """
    import b_warm_refresh_contract as wire
    number=len(trace);diagnostic={}
    for name,raw in samples.items():(bank['folder']/f'{number:04d}-{name}.bin').write_bytes(raw)
    if calls.uncertain:
        diagnostic=dict(error='Control already uncertain; refresh query skipped',control_uncertain=True)
    else:
        try:
            name='GetBWarmRefreshReport'
            code,raw=calls.call(bank['addresses'][name],output_size=C.sizeof(wire.Report))
            if raw is not None:(bank['folder']/f'{number:04d}-{name}.bin').write_bytes(raw)
            require(code==0 and raw is not None,'Refresh diagnostic export rejected')
            r=wire.decode(wire.Report,raw)
            diagnostic={key:getattr(r,key) for key in ('state','error','captured','executeCalls','writeAttempts',
                'writeReturned','intentCreated','intentDurable','matched','leaseHeld','leaseReleased','releaseCalls',
                'previousSize','newSize','osError','exceptionCode','previousReads','newReads','attempt','epoch','generation')}
            diagnostic.update(stage=bytes(r.stage).decode('ascii',errors='replace'),
                firstFailure=bytes(r.firstFailure).decode('ascii',errors='replace'),
                previousSha256=bytes(r.previousSha256).hex(),newSha256=bytes(r.newSha256).hex())
        except BaseException as exc:
            diagnostic=dict(snapshot_error=repr(exc),control_uncertain=calls.uncertain)
    trace.append({**row,'refresh_diagnostic':diagnostic})
    if calls.uncertain:raise RuntimeError('Refresh observation control uncertain; original reports retained')
    if diagnostic.get('snapshot_error') and not any(row.get(k,0) for k in ('OwnerError','SessionError','ControllerError',
            'QueueError','BytesError','LifecycleError','IdentityError','PlanningError','HardwareError','StorageError','GuardError')):
        raise RuntimeError('Refresh observation unavailable; original reports retained')


def run_two(port,profiles,target,sources,initial_target,folder,*,on_complete=None):
    """Back up exact old bytes; only the authenticated native bank may write target.

    No target file handle is retained across port.load. Private source and path
    leases persist until the local load call returns (success or known failure).
    Native owner is responsible for its target lease until complete retirement.
    """
    validate_pair(profiles);identity(initial_target)
    target=files.clean_path(target);require(target.name==files.NAME,'CC03 target required')
    require(len(sources)==2,'Two private sources required');sources=[files.clean_path(p) for p in sources]
    completed=[];expected=initial_target
    for index,(profile,source) in enumerate(zip(profiles,sources)):
        old,old_raw=files.read_file(target);require(old==expected,'Old target changed before next bank')
        bank=port.open_bank(index)
        if index:port.authorize_second(bank,profile)
        backup=folder/f'bank-{index+1}-old-target.s14';files.save_new(backup,old_raw)
        backup_id,backup_raw=files.read_file(backup)
        require(backup_raw==old_raw,'Old target backup differs')
        save_new(folder/f'bank-{index+1}-old-target.json',dict(target=str(target),identity=old,
            backup=str(backup),backup_identity=backup_id,native_write_pending=True))
        # Parent directory leases forbid path replacement, not writing target.
        # The new source is independent from both target and backup.
        with ExitStack() as held:
            files.pin_parents(held,target);files.pin_parents(held,source)
            handle=held.enter_context(files.Handle(source));source_id,raw=handle.snapshot()
            require(source_id['file_id'][:3]!=old['file_id'][:3],'Source aliases target')
            require((source_id['size'],source_id['sha256'])==(profile.file.size,bytes(profile.file.sha256).hex()),'New source differs')
            require(files.read_file(target)[0]==old,'Old target changed before native publication')
            try:
                result=port.load(bank,profile,raw,target=target,previous=old,backup=backup)
                require(handle.snapshot()[0]==source_id,'Private input changed during load')
                fresh,fresh_raw=files.read_file(target)
                require((fresh['size'],fresh['sha256'])==(profile.file.size,bytes(profile.file.sha256).hex()) and fresh_raw==raw,'Native published target differs')
            except BaseException:
                port.abort();raise
        completed.append(dict(file_identity=fresh,completion=result,previous_identity=old,backup=str(backup)))
        expected=fresh
        if on_complete is not None:on_complete(index,result)
    port.finish()
    return dict(result='PASS_TWO_WARM_REFRESH_LOADS',completed=completed,room_ready=False,
        full_world_verified=False,input_exclusion_proven=False,scheduler_fence_proven=False,
        target_written_by_python=False,screen_cover_verified=False)


class Resident(PreviousResident):
    def _module(self,source,digest,destination,exports):
        if Path(source)==Path(self.bank_dll):exports=tuple(dict.fromkeys((*exports,*REFRESH_EXPORTS)))
        return super()._module(source,digest,destination,exports)

    def load(self,bank,profile,raw_file,*,target,previous,backup):
        import b_warm_refresh_contract as refresh_wire
        from b_warm_start_support import build_config,live_hook_evidence
        from checkpoint_complete_live_capture import process_birth
        self.current=bank
        planning=capture_planning(self.reader,profile,self.ruler)
        if self.before is None:self.before=planning
        require(all(planning[k]==self.before[k] for k in ('pid','birth','base')),'Attachment changed')
        description=bank['description']
        storage=storage_bindings(self.reader,self.api.modules(),steam_paths=self.steam,owner_module=bank['module'],
            owner_path=bank['path'],owner_sha=self.bank_sha,read_bridge=description['readBridge'])
        hooks=live_hook_evidence(self.reader,planning,storage,baseline=self.first_hooks)
        if self.first_hooks is None:self.first_hooks=hooks
        if not self.prepared:
            self.helper=self._module(self.helper_dll,self.helper_sha,self.folder/'coordinator.dll',HAND_EXPORTS)
            code,raw=self.calls.call(self.helper['addresses']['DescribeBWarmCoordinator'],output_size=C.sizeof(hand_wire.Description))
            require(code==0,'Coordinator description failed');hand_wire.decode(hand_wire.Description,raw)
            self.hand(hand_wire.Prepare,pid=planning['pid'],birth=planning['birth'],first=bank['module'],
                slots=[r['slot'] for r in hooks],originals=[r['original'] for r in hooks]);self.prepared=True
        local=bank['folder']/files.NAME;files.save_new(local,raw_file)
        source_id,_=files.read_file(local)
        require(files.read_file(target)[0]==previous,'Target changed before install')
        owner=build_config(planning,storage,folder=bank['folder'],target=local,attempt=secrets.randbits(64) or 1,
            epoch=secrets.randbits(64) or 1,attachment_hex=secrets.token_hex(32),owner_binding_hex=secrets.token_hex(32))
        warm=wrap_owner_config(owner,profile,planning)
        config=make_config(warm,write=storage['write'],previous=previous,source_identity=source_id,
            target_path=target,backup_path=backup,refresh_intent=bank['folder']/'refresh.intent')
        code,raw=self.calls.call(bank['addresses']['DescribeBWarmRefreshOwner'],output_size=C.sizeof(refresh_wire.Description))
        require(code==0,'Refresh description rejected');described=refresh_wire.decode(refresh_wire.Description,raw)
        require(bank_wire.old.decode_description(bytes(described.warm.bank))==description,'Refresh/warm description identity differs')
        save_new(bank['folder']/'bindings.json',dict(planning=planning,storage=storage,description=description,previous=previous))
        (bank['folder']/'config.bin').write_bytes(bytes(config))
        try:
            code,_=self.calls.call(bank['addresses']['InstallBWarmRefreshOwner'],bytes(config));bank['install_completed']=True
        except BaseException as exc:
            bank['install_completed']=bool(getattr(exc,'completed',False));raise
        require(code==0,'Refresh bank install rejected')
        trace=[]
        def record(samples,row):
            record_observation(self.calls,bank,samples,row,trace)
        try:
            accepted=completion(self.calls,bank['addresses'],profile=profile,planning=planning,storage=storage,
                description=description,config=warm,deadline=time.monotonic()+self.timeout,record=record)
        finally:save_new(bank['folder']/'trace.json',trace)
        bank['warm_load_retired']=True
        # All original warm completion predicates remain necessary. New refresh
        # evidence must independently bind this exact config and a released lease.
        refresh_rows=[]
        for number in range(2):
            code,raw=self.calls.call(bank['addresses']['GetBWarmRefreshReport'],output_size=C.sizeof(refresh_wire.Report))
            require(code==0 and raw is not None,'Refresh report rejected')
            (bank['folder']/f'refresh-final-{number}.bin').write_bytes(raw)
            refresh_rows.append(validate_completed(raw,config))
        require(refresh_rows[0]==refresh_rows[1],'Refresh completion observations differ')
        bank['refresh_load_retired']=True
        live_hook_evidence(self.reader,planning,storage,baseline=hooks)
        snap=self.reader.snapshot()
        require(self.reader.snapshot()==snap and process_birth(self.reader)==planning['birth'],'Post-load context changed')
        require(tuple(snap['date'][k] for k in ('year','month','day'))==dates(profile.loaded) and
            (snap['player']['force_id'],snap['player']['ruler_id'])==(profile.target.force,profile.target.ruler),'Post-load date/player differs')
        target_id,target_raw=files.read_file(target)
        require((target_id['size'],target_id['sha256'])==(profile.file.size,bytes(profile.file.sha256).hex()) and target_raw==raw_file,'Published target bytes differ')
        state=self.hand(hand_wire.Observe)
        require((state.firstCompleted if bank['index']==0 else state.secondCompleted)==1,'Native helper completion absent')
        self.ruler=profile.target.ruler
        answer=dict(accepted=accepted,refresh=refresh_rows[0],attempt=owner.attempt,pid=planning['pid'],birth=planning['birth'],
            profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(),snapshot=snap,slots_restored=True,target_lease_released=True)
        save_new(bank['folder']/'completion.json',answer);return answer

    def abort(self):
        if self.current and self.current.get('warm_load_retired'):return
        super().abort()
