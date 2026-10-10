"""Bounded three-load retained refresh resident using the distinct chain helper.

No CLI, process discovery, automatic Ready, retry, or module unload. The caller
must supply approved bank and chain-helper builds and retained local ownership.
"""
import ctypes as C
from contextlib import ExitStack
import hashlib,secrets,time
from pathlib import Path
import b_warm_staging as files
import b_warm_profile_contract as bank_wire
import b_warm_chain_coordinator_contract as hand_wire
from b_warm_stable_refresh_coordinator import Resident as FrozenResident
from b_warm_stable_refresh_coordinator import record_observation, capture_planning
from b_warm_coordinator import dates
from b_warm_profile_capture import wrap_owner_config
from b_warm_start import require,save_new,completion,EXPORTS
from b_warm_refresh_start_support import identity,storage_bindings,make_config,validate_completed
HAND_EXPORTS=tuple(n+'BWarmChainCoordinator' for n in ('Describe','Prepare','Authorize','Observe'))

def validate_three(profiles):
    require(type(profiles) in (list,tuple) and len(profiles)==3,'Exactly three bounded checkpoints required')
    for p in profiles:bank_wire.validate_profile(p)
    first=profiles[0]
    require(dates(first.before)==dates(first.loaded) and first.currentForce==first.source.force,'Same-day A-view bootstrap required')
    for before,after in zip(profiles,profiles[1:]):
        y,m,d=dates(before.loaded)
        nxt=(y,m,d+10) if d<21 else (y,m+1,1) if m<12 else (y+1,1,1)
        require(dates(after.before)==dates(before.loaded) and dates(after.loaded)==nxt and after.currentForce==before.target.force,
                'Exactly successive B-view periods required')
        require(bytes(after.source)==bytes(first.source) and bytes(after.target)==bytes(first.target),'Human factions changed')
    require(len({bytes(p.file.sha256) for p in profiles})==3,'Checkpoint files must be distinct')

def run_three(port,profiles,target,sources,initial_target,folder,*,on_complete=None):
    """Back up exact old bytes; only the authenticated native bank may write target.

    No target file handle is retained across port.load. Private source and path
    leases persist until the local load call returns (success or known failure).
    Native owner is responsible for its target lease until complete retirement.
    """
    validate_three(profiles);identity(initial_target)
    target=files.clean_path(target);require(target.name==files.NAME,'CC03 target required')
    require(len(sources)==3,'Three private sources required');sources=[files.clean_path(p) for p in sources]
    completed=[];expected=initial_target
    for index,(profile,source) in enumerate(zip(profiles,sources)):
        old,old_raw=files.read_file(target);require(old==expected,'Old target changed before next bank')
        bank=port.open_bank(index)
        if index:port.authorize_next(bank,profile)
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
    return dict(result='PASS_THREE_WARM_REFRESH_LOADS',completed=completed,room_ready=False,
        full_world_verified=False,input_exclusion_proven=False,scheduler_fence_proven=False,
        target_written_by_python=False,screen_cover_verified=False)


class Resident(FrozenResident):
    """Three new bank modules, two independent native transition certificates."""
    def hand(self,kind,**values):
        from a_save_runtime_control import remote_call
        require(not self.calls.uncertain,'Unknown previous native result; no further calls')
        command=hand_wire.envelope(kind,self.nonce)
        for key,value in values.items():
            if key in ('slots','originals'):getattr(command,key)[:]=value
            else:setattr(command,key,value)
        self.serial+=1
        name={hand_wire.Prepare:'Prepare',hand_wire.Authorize:'Authorize',hand_wire.Observe:'Observe'}[kind]+'BWarmChainCoordinator'
        try:code,raw=remote_call(self.api,self.helper['addresses'][name],bytes(command),self.folder,f'chain-{self.serial:03d}')
        # The transport's final evidence write may mask an unknown-call error.
        # No exception from that transport permits another native call.
        except BaseException:self.calls.uncertain=True;raise
        answer=hand_wire.decode(kind,raw,self.nonce)
        require(code==0 and answer.header.result==0,'Native chain helper refused')
        return answer
    def open_bank(self,index):
        require(type(index) is int and index==len(self.banks) and index<3 and not self.calls.uncertain and not getattr(self,'_chain_failed',False),'Ordered independent banks required')
        if index:require(self.banks[-1].get('warm_load_retired') and self.banks[-1].get('refresh_load_retired') and self.banks[-1].get('load_accepted'),'Previous load not fully accepted')
        directory=self.folder/f'bank-{index+1}';directory.mkdir()
        bank=self._module(self.bank_dll,self.bank_sha,directory/'bank.dll',EXPORTS)
        bank.update(index=index,folder=directory,install_completed=False)
        code,raw=self.calls.call(bank['addresses']['DescribeBWarmProfileOwner'],output_size=C.sizeof(bank_wire.Description))
        require(code==0,'Bank description rejected');d=bank_wire.decode(bank_wire.Description,raw)
        bank['description']=bank_wire.old.decode_description(bytes(d.bank))
        # A valid export table alone is insufficient: bind all actual bridge code.
        import pefile
        from checkpoint_complete_live_capture import readable
        desc=bank['description'];bridges=desc['dispatchBridge']+[desc['workerBridge'],desc['readBridge'],desc['authorizedForward']]
        require(len(set(bridges))==7,'Bank bridges alias')
        pe=pefile.PE(str(bank['path']),fast_load=True)
        try:
            for address in bridges:
                offset=address-bank['module']
                require(0<offset and offset+32<=pe.OPTIONAL_HEADER.SizeOfImage,'Bridge outside bank')
                readable(self.reader,address,32,allocation=bank['module'],execute=True)
                require(self.reader.memory.read(address,32)==pe.get_data(offset,32),'Loaded bridge differs')
        finally:pe.close()
        require(bank['description']['module']==bank['module'],'Wrong bank module')
        require(all(bank['module']!=previous['module'] for previous in self.banks),'Loader reused a prior module')
        self.banks.append(bank);return bank

    def authorize_next(self,bank,profile):
        require(len(self.banks) in (2,3) and self.prepared and bank is self.banks[-1] and
                not bank.get('authorization_attempted') and not self.calls.uncertain and not getattr(self,'_chain_failed',False),'Ordered once-only successor authorization required')
        previous=self.banks[-2]
        require(previous.get('warm_load_retired') and previous.get('refresh_load_retired') and previous.get('load_accepted'),'Prior load not fully accepted')
        fresh=capture_planning(self.reader,profile,self.ruler,expected_birth=self.before['birth'],expected_pid=self.reader.pid)
        require(all(fresh[k]==self.before[k] for k in ('pid','birth','base')),'Attachment changed')
        bank['authorization_attempted']=True
        self.hand(hand_wire.Authorize,next=bank['module'],generation=len(self.banks))
        state=self.hand(hand_wire.Observe)
        require(state.currentGeneration==len(self.banks) and list(state.banks)[:len(self.banks)]==[b['module'] for b in self.banks] and
                all(state.completed[i]==1 for i in range(len(self.banks)-1)) and state.certificateCount==len(self.banks)-1,
                'Native successor module or predecessor completion differs')
        certificate=state.certificates[len(self.banks)-2]
        require(certificate.generation==len(self.banks) and certificate.previous==previous['module'] and certificate.next==bank['module'] and
                certificate.pid==self.before['pid'] and certificate.birth==self.before['birth'] and bytes(certificate.nonce)==self.nonce,
                'Native transition certificate binding differs')
        bank['authorized']=True

    # Existing refresh RulesBridge calls this name for every non-bootstrap bank.
    def authorize_second(self,bank,profile):return self.authorize_next(bank,profile)
    def load(self,bank,profile,raw_file,*,target,previous,backup):
        require(not getattr(self,'_chain_failed',False),'Failed chain is terminal')
        try:return self._load_once(bank,profile,raw_file,target=target,previous=previous,backup=backup)
        except BaseException:self._chain_failed=True;raise

    def _load_once(self,bank,profile,raw_file,*,target,previous,backup):
        import b_warm_refresh_contract as refresh_wire
        from b_warm_start_support import build_config,live_hook_evidence
        from checkpoint_complete_live_capture import process_birth
        require(bank is self.banks[-1] and not bank.get('load_attempted') and not self.calls.uncertain and
                (bank['index']==0 or bank.get('authorized')),'Fresh authorized bank required')
        bank['load_attempted']=True
        self.current=bank
        sampling={}
        try:
            planning=capture_planning(self.reader,profile,self.ruler,
                expected_birth=self.before['birth'] if self.before else process_birth(self.reader),
                expected_pid=self.reader.pid,evidence=sampling)
        finally:save_new(bank['folder']/'planning-sampling.json',sampling)
        if self.before is None:self.before=planning
        require(all(planning[k]==self.before[k] for k in ('pid','birth','base')),'Attachment changed')
        description=bank['description']
        storage=storage_bindings(self.reader,self.api.modules(),steam_paths=self.steam,owner_module=bank['module'],
            owner_path=bank['path'],owner_sha=self.bank_sha,read_bridge=description['readBridge'])
        hooks=live_hook_evidence(self.reader,planning,storage,baseline=self.first_hooks)
        if self.first_hooks is None:self.first_hooks=hooks
        if not self.prepared:
            self.helper=self._module(self.helper_dll,self.helper_sha,self.folder/'chain-coordinator.dll',HAND_EXPORTS)
            code,raw=self.calls.call(self.helper['addresses']['DescribeBWarmChainCoordinator'],output_size=C.sizeof(hand_wire.Description))
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
        require(state.currentGeneration==bank['index']+1 and state.banks[bank['index']]==bank['module'] and
                all(state.completed[i]==1 for i in range(bank['index']+1)),'Native chain completion absent')
        self.ruler=profile.target.ruler
        answer=dict(accepted=accepted,refresh=refresh_rows[0],attempt=owner.attempt,pid=planning['pid'],birth=planning['birth'],
            profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(),snapshot=snap,slots_restored=True,target_lease_released=True)
        save_new(bank['folder']/'completion.json',answer)
        bank['load_accepted']=True
        return answer

    def finish(self):
        require(not getattr(self,'_chain_failed',False) and not self.calls.uncertain and len(self.banks)==3 and all(b.get('warm_load_retired') and b.get('refresh_load_retired') and b.get('load_accepted') for b in self.banks),
                'Three independently retired refresh banks required')
        state=self.hand(hand_wire.Observe)
        require(state.currentGeneration==3 and list(state.banks)==[b['module'] for b in self.banks] and
                list(state.completed)==[1,1,1] and state.certificateCount==2,'Final native three-bank completion missing')
