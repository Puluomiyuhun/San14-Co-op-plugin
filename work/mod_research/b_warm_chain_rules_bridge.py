"""Bounded three-bank rules lifecycle bridge using native refresh, never physical checkpoint staging.

Trusted local callbacks still provide the existing lifecycle guard. This bridge
does not make file locks or a returned dictionary into global input exclusion.
"""
from contextlib import ExitStack
import hashlib

import b_warm_staging as files
from b_warm_rules_bridge import WarmRulesBridge as PreviousBridge
from b_warm_profile_contract import Profile, validate_profile
from human_rules_world_lifecycle import Config, NextWorldRequest


def check_completion(value,profile,previous,module):
    """Correlate the trusted local Resident result; not a network permission API."""
    files.need(type(value) is dict and (value['pid'],value['birth'])==(module.pid,module.birth) and
        value['profile_sha256']==hashlib.sha256(bytes(profile)).hexdigest() and
        value['slots_restored'] is True and value['target_lease_released'] is True,
        'Native refresh completion process/profile/retirement differs')
    accepted=value['accepted'];refresh=value['refresh'];snapshot=value['snapshot']
    files.need(accepted['result']=='PASS_WARM_LOAD_RETIRED' and
        (accepted['source_force'],accepted['source_ruler'],accepted['target_force'],accepted['target_ruler'])==
        (profile.source.force,profile.source.ruler,profile.target.force,profile.target.ruler),
        'Native warm receipt factions differ')
    expected=dict(state=4,error=0,captured=1,executeCalls=1,writeAttempts=1,writeReturned=1,
        intentCreated=1,intentDurable=1,matched=1,leaseHeld=0,leaseReleased=1,releaseCalls=1,
        previousReads=2,newReads=2,osError=0,exceptionCode=0)
    files.need(type(refresh) is dict and all(type(refresh.get(k)) is int and refresh[k]==v for k,v in expected.items()),
        'Native refresh write/readback/lease receipt differs')
    files.need(type(value['attempt']) is int and value['attempt']>0 and
        refresh['attempt']==refresh['generation']==value['attempt'] and
        type(refresh['epoch']) is int and refresh['epoch']>0 and
        (refresh['previous_size'],refresh['previous_sha256'])==(previous['size'],previous['sha256']) and
        (refresh['new_size'],refresh['new_sha256'])==(profile.file.size,bytes(profile.file.sha256).hex()) and
        refresh['stage']=='released_after_native_retirement', 'Native refresh attempt/file identity differs')
    files.need(tuple(snapshot['date'][k] for k in ('year','month','day'))==
        (profile.loaded.year,profile.loaded.month,profile.loaded.day) and
        (snapshot['player']['force_id'],snapshot['player']['ruler_id'])==(profile.target.force,profile.target.ruler),
        'Native loaded date/player differs')


class WarmRulesBridge(PreviousBridge):
    def __init__(self,lifecycle,warm_port,*,target,records):
        super().__init__(lifecycle,warm_port,target=target,records=records)
        # This is an immutable initial physical identity, not a native-cache
        # assertion. The native owner separately reads old bytes twice.
        self.initial_target=files.read_file(self.target)[0]

    def _load_checkpoint(self,request,profile,source,index):
        folder=self.records/('generation-'+str(request.generation));folder.mkdir()
        source=files.clean_path(source)
        old,old_raw=files.read_file(self.target)
        expected=self.completed[-1]['file_identity'] if index else self.initial_target
        files.need(old==expected,'Previous retired/initial target identity changed')
        backup=folder/'previous-target.s14';files.save_new(backup,old_raw)
        backup_id,backup_raw=files.read_file(backup)
        files.need(backup_raw==old_raw,'Old target backup differs')
        files.save_new(folder/'rules-restored.json',files.canonical(dict(
            history=self.lifecycle.history,generation=request.generation,checkpoint=request.checkpoint,
            previous_identity=old,backup=str(backup),backup_identity=backup_id,
            native_publication_pending=True,permission=False)))
        with ExitStack() as held:
            files.pin_parents(held,self.target);files.pin_parents(held,source)
            handle=held.enter_context(files.Handle(source));source_id,raw=handle.snapshot()
            files.need(source_id['file_id'][:3]!=old['file_id'][:3],'Received source aliases native target')
            files.need((source_id['size'],source_id['sha256'])==
                (profile.file.size,bytes(profile.file.sha256).hex()),'Received source differs from profile')
            files.need(files.read_file(self.target)[0]==old,'Old target changed before native load')
            bank=self.warm.open_bank(index)
            if index:self.warm.authorize_next(bank,profile)
            try:
                completion=self.warm.load(bank,profile,raw,target=self.target,previous=old,backup=backup)
                check_completion(completion,profile,old,self.lifecycle.current.module)
                files.need(handle.snapshot()[0]==source_id,'Received source changed during load')
                fresh,fresh_raw=files.read_file(self.target)
                files.need((fresh['size'],fresh['sha256'])==(profile.file.size,bytes(profile.file.sha256).hex()) and
                    fresh_raw==raw,'Native published target differs')
            except BaseException:
                # Actual retained Resident suppresses Stop after real retirement
                # or uncertain control. Never release a native lease ourselves.
                self.warm.abort()
                raise
        return dict(file_identity=fresh,completion=completion,previous_identity=old,
            backup=str(backup),publication=dict(result='NATIVE_REFRESH_VERIFIED',target_written_by_bridge=False,
                source_sha256=source_id['sha256'],target_lease_released=True))

    def replace(self,request,profile,source,*,observe_loaded,prepare_rules):
        with self._lock:
            files.need(self.phase=='ACTIVE' and len(self.completed)<3,'Bridge consumed/held; no automatic retry or DLL reset')
            self.phase='REPLACING';result=None
            try:
                def load(actual_request):
                    nonlocal result
                    files.need(actual_request is request and type(request) is NextWorldRequest and type(profile) is Profile,
                        'Typed local request/profile required')
                    validate_profile(profile)
                    config=Config.from_buffer_copy(self.lifecycle.current.world.config)
                    files.need((profile.loaded.year,profile.loaded.month,profile.loaded.day)==
                        (request.year,request.month,request.day),'Requested loaded date differs')
                    files.need(profile.currentForce==config.viewer==profile.target.force and
                        set(config.force)=={profile.source.force,profile.target.force},'Warm profile changes human factions/viewer')
                    result=self._load_checkpoint(request,profile,source,len(self.completed))
                rebound=self.lifecycle.replace(request,load=load,observe_loaded=observe_loaded,prepare=prepare_rules)
                files.need(result is not None,'Missing replacement result');result['rules']=rebound
                self.completed.append(result);self.phase='ACTIVE'
                return dict(result='WARM_LOAD_AND_RULES_REBOUND',generation=request.generation,checkpoint=request.checkpoint,
                    details=result,ready=False,fence_released=False,full_world_verified=False)
            except BaseException:
                self.phase='HELD';raise
