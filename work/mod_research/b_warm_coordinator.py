"""Controlled two-load diagnostic coordinator. Default: help, no process access.

The first CC03 file must already be staged. The second replaces that exact file
only after real retirement and native handover. No room Ready, no automatic
game advance, no retry of a failed process lifetime.
"""
import argparse
import ctypes as C
from contextlib import ExitStack
from datetime import datetime
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import sys
import time
import b_warm_profile_contract as bank_wire
import b_warm_coordinator_contract as hand_wire
from b_warm_profile_capture import capture_planning, profile_from_dict, wrap_owner_config, integer
from b_warm_start import P, PRIVATE, require, sha, save_new, approved_build, refuse_prior_attempt, Calls, completion, EXPORTS
import b_warm_staging as files

HAND_EXPORTS=('DescribeBWarmCoordinator','PrepareBWarmCoordinator','AuthorizeBWarmCoordinator','ObserveBWarmCoordinator')


def approved_component(path, digest, family):
    path=Path(path).resolve(strict=True)
    require(sha(path)==digest,'Component result identity differs')
    result=json.loads(path.read_text(encoding='utf-8'))
    require(result.get('family')==family and result.get('result')=='PASS' and result.get('inputs_unchanged') is True,
            'Matching successful component required')
    for field in ('sources','generated','binaries'):
        require(type(result.get(field)) is dict and result[field],'Missing component identity closure')
        for name,h in result[field].items():require(sha(name)==h,'Component source/output drift: '+name)
    for name,h in result.get('private',{}).items():require(sha(name)==h,'Component private input drift')
    if family=='san14.b-warm-factory-pair.v1':
        require(result.get('full_factory_pair_passed') is True,'Two complete native factories required')
    return result


def dates(d):return d.year,d.month,d.day


def validate_pair(profiles):
    require(len(profiles)==2,'Exactly two diagnostic loads')
    a,b=profiles
    for p in profiles:bank_wire.validate_profile(p)
    require(dates(b.before)==dates(a.loaded) and b.currentForce==a.target.force,'Second current world must be first loaded world')
    require(bytes(a.target)==bytes(b.target) and bytes(a.source)==bytes(b.source),'Keep A/B factions across the two diagnostic loads')
    y,m,d=dates(a.loaded)
    nxt=(y,m,d+10) if d<21 else (y,m+1,1) if m<12 else (y+1,1,1)
    require(dates(b.loaded)==nxt,'Second file must be exactly the following period')
    require(bytes(a.file.sha256)!=bytes(b.file.sha256),'Two distinct checkpoint files required')


def run_two(port, profiles, target, second_source, folder, *, on_complete=None):
    """Connect actual staging to a process-local native port; never accept a JSON permit.

    Production port is Resident below. Tests use an explicitly identified port
    substitute while still performing actual Windows file replacement/backups.
    """
    validate_pair(profiles)
    target,second_source=files.clean_path(target),files.clean_path(second_source)
    require(target.name==files.NAME,'Exact CC03 destination required')
    source_identity,_=files.read_file(second_source)
    require((source_identity['size'],source_identity['sha256'])==(profiles[1].file.size,bytes(profiles[1].file.sha256).hex()),'Second received file differs')
    completed=[]
    for index,p in enumerate(profiles):
        bank=port.open_bank(index)
        if index:
            # Completion JSON is audit material, never the handover authority.
            port.authorize_second(bank,p)
            proposed=files.plan(second_source,target.parent,bytes(p.file.sha256).hex(),p.file.size)
            require(proposed['previous_identity']==completed[0]['file_identity'],'First staged file changed after its retired load')
            evidence=folder/'first-retired.json'
            save_new(evidence,completed[0]['completion'])
            auth=folder/'second-file-authorization.json'
            save_new(auth,dict(schema='san14.local-file-overwrite-authorization.v1',nonce=secrets.token_hex(16),
                plan_sha256=files.digest(files.canonical(proposed)),expires_unix=int(time.time())+120,
                retirement_reference=str(evidence),retirement_sha256=sha(evidence)))
            records=folder/'staging';records.mkdir()
            outcome=files.apply(proposed,auth,sha(auth),records)
            save_new(folder/'staging-result.json',outcome)
            require(outcome['result']=='STAGED','Second staging incomplete; no automatic restore or retry')
        # Lease spans native execution through deep retirement and final checks.
        with ExitStack() as held:
            files.pin_parents(held,target)
            handle=held.enter_context(files.Handle(target))
            identity,raw=handle.snapshot()
            require((identity['size'],identity['sha256'])==(p.file.size,bytes(p.file.sha256).hex()),'Staged input differs')
            try:
                result=port.load(bank,p,raw)
                require(handle.snapshot()[0]==identity,'Staged file changed during load')
            except BaseException:
                # Keep file lease while attempting only known-completed Stop.
                port.abort()
                raise
            completed.append(dict(file_identity=identity,completion=result))
        if on_complete is not None:on_complete(index,result)
    port.finish()
    return dict(result='PASS_TWO_WARM_DIAGNOSTIC_LOADS',completed=completed,room_ready=False,
                full_world_verified=False,input_exclusion_proven=False,screen_cover_verified=False)


class Resident:
    """One writable process handle and one native handover owner for both banks."""
    def __init__(self,reader,folder,bank_dll,bank_sha,helper_dll,helper_sha,steam_paths,expected_ruler,timeout):
        from b_warm_start_support import open_process_api
        from checkpoint_live_prefetch_start import invoke
        self.reader,self.folder,self.bank_dll,self.bank_sha=reader,folder,bank_dll,bank_sha
        self.steam,self.ruler,self.timeout=steam_paths,expected_ruler,timeout
        self.api=open_process_api(reader);self.calls=Calls(self.api,invoke)
        self.helper_dll,self.helper_sha=helper_dll,helper_sha
        self.helper=None;self.nonce=secrets.token_bytes(32);self.serial=0
        self.banks=[];self.current=None;self.prepared=False;self.before=None;self.first_hooks=None

    def _module(self,source,digest,destination,exports):
        import pefile
        from checkpoint_complete_live_capture import module_approval,readable
        shutil.copyfile(source,destination);require(sha(destination)==digest,'Copied DLL differs')
        self.calls.call(self.api.load_library_address(),str(destination).encode('utf-16le')+b'\0\0')
        matches=[a for a,p in self.api.modules() if str(p).casefold()==str(destination).casefold()]
        require(len(matches)==1,'Loaded module identity differs');base=matches[0]
        module_approval(self.reader,base,destination,digest)
        pe=pefile.PE(str(destination))
        try:
            found={s.name.decode('ascii'):s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
            require(all(n in found for n in exports),'Missing required export')
            for name in exports:
                address=base+found[name]
                require(0<found[name] and found[name]+32<=pe.OPTIONAL_HEADER.SizeOfImage,'Export outside image')
                readable(self.reader,address,32,allocation=base,execute=True)
                require(self.reader.memory.read(address,32)==pe.get_data(found[name],32),'Loaded export differs')
            return dict(module=base,path=destination,addresses={n:base+found[n] for n in exports})
        finally:pe.close()

    def hand(self,kind,**values):
        from a_save_runtime_control import remote_call,RemoteCallUnknown
        command=hand_wire.envelope(kind,self.nonce)
        for key,value in values.items():
            if key in ('slots','originals'):getattr(command,key)[:]=value
            else:setattr(command,key,value)
        self.serial+=1
        name={hand_wire.Prepare:'Prepare',hand_wire.Authorize:'Authorize',hand_wire.Observe:'Observe'}[kind]+'BWarmCoordinator'
        try:
            code,raw=remote_call(self.api,self.helper['addresses'][name],bytes(command),self.folder,f'hand-{self.serial:03d}')
        except RemoteCallUnknown:
            self.calls.uncertain=True;raise
        answer=hand_wire.decode(kind,raw,self.nonce)
        require(code==0 and answer.header.result==0,'Native handover rejected; no replay')
        return answer

    def open_bank(self,index):
        require(index==len(self.banks) and index<2,'Ordered independent banks required')
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
        if self.banks:require(bank['module']!=self.banks[0]['module'],'Loader reused first module')
        self.banks.append(bank);return bank

    def authorize_second(self,bank,profile):
        require(len(self.banks)==2 and self.prepared,'First bank must have completed')
        fresh=capture_planning(self.reader,profile,self.ruler)
        require(all(fresh[k]==self.before[k] for k in ('pid','birth','base')),'Attachment changed')
        self.hand(hand_wire.Authorize,second=bank['module'])
        state=self.hand(hand_wire.Observe)
        require(state.stage==2 and state.firstCompleted==1 and state.second==bank['module'],'Native second ownership differs')

    def load(self,bank,profile,raw_file):
        from b_warm_start_support import build_config,storage_bindings,live_hook_evidence
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
                      slots=[r['slot'] for r in hooks],originals=[r['original'] for r in hooks])
            self.prepared=True
        local=bank['folder']/files.NAME;files.save_new(local,raw_file)
        owner=build_config(planning,storage,folder=bank['folder'],target=local,attempt=secrets.randbits(64) or 1,
                           epoch=secrets.randbits(64) or 1,attachment_hex=secrets.token_hex(32),owner_binding_hex=secrets.token_hex(32))
        config=wrap_owner_config(owner,profile,planning)
        save_new(bank['folder']/'bindings.json',dict(planning=planning,storage=storage,description=description))
        (bank['folder']/'config.bin').write_bytes(bytes(config))
        try:
            code,_=self.calls.call(bank['addresses']['InstallBWarmProfileOwner'],bytes(config));bank['install_completed']=True
        except BaseException as exc:
            bank['install_completed']=bool(getattr(exc,'completed',False));raise
        require(code==0,'Bank install rejected')
        trace=[]
        def record(samples,row):
            for name,raw in samples.items():(bank['folder']/f'{len(trace):04d}-{name}.bin').write_bytes(raw)
            trace.append(row)
        try:
            accepted=completion(self.calls,bank['addresses'],profile=profile,planning=planning,storage=storage,
                description=description,config=config,deadline=time.monotonic()+self.timeout,record=record)
        finally:save_new(bank['folder']/'trace.json',trace)
        live_hook_evidence(self.reader,planning,storage,baseline=hooks)
        snap=self.reader.snapshot()
        require(self.reader.snapshot()==snap and process_birth(self.reader)==planning['birth'],'Post-load context changed')
        require(tuple(snap['date'][k] for k in ('year','month','day'))==dates(profile.loaded) and
                (snap['player']['force_id'],snap['player']['ruler_id'])==(profile.target.force,profile.target.ruler),'Post-load identity/date differs')
        state=self.hand(hand_wire.Observe)
        require((state.firstCompleted if bank['index']==0 else state.secondCompleted)==1,'Native completion absent')
        self.ruler=profile.target.ruler
        answer=dict(accepted=accepted,attempt=owner.attempt,pid=planning['pid'],birth=planning['birth'],
                    profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(),snapshot=snap,slots_restored=True)
        save_new(bank['folder']/'completion.json',answer)
        return answer

    def abort(self):
        bank=self.current
        if bank and bank['install_completed'] and not self.calls.uncertain:
            try:
                code,_=self.calls.call(bank['addresses']['StopCheckpointCompleteLiveOwner'])
                save_new(bank['folder']/'stop.json',dict(control_completed=code==0,native_drained=False,staging_reuse_authorized=False))
            except BaseException as exc:
                save_new(bank['folder']/'stop-error.json',dict(error=repr(exc),native_drained=False))

    def finish(self):
        state=self.hand(hand_wire.Observe)
        require(state.stage==3 and state.secondCompleted==1,'Second native completion missing')

    def close(self):self.api.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--pid',type=int)
    parser.add_argument('--plan',type=Path)
    for name in ('helper','pair'):
        parser.add_argument('--'+name+'-build',type=Path);parser.add_argument('--'+name+'-sha256')
    parser.add_argument('--timeout',type=int,default=180)
    args=parser.parse_args(argv)
    if not args.execute:parser.print_help();return 0
    integer(args.pid,1,0xffffffff);integer(args.timeout,30,1800)
    require(args.plan,'Explicit local two-checkpoint plan required')
    plan=json.loads(args.plan.read_text(encoding='utf-8-sig'))
    require(set(plan)=={'profiles','target','second_source','expected_ruler','steam_paths'},'Plan fields differ')
    profiles=[profile_from_dict(p) for p in plan['profiles']];validate_pair(profiles)
    integer(plan['expected_ruler'],1,5999)
    helper=approved_component(args.helper_build,args.helper_sha256,'san14.b-warm-coordinator.v1')
    pair=approved_component(args.pair_build,args.pair_sha256,'san14.b-warm-factory-pair.v1')
    bank_dll=Path(pair['production_dll']['path']);bank_sha=pair['production_dll']['sha256']
    require(bank_dll.resolve().is_relative_to(args.pair_build.resolve().parent) and
            pair['binaries'].get(str(bank_dll))==bank_sha and sha(bank_dll)==bank_sha,'Pair production DLL closure differs')
    for name,digest in helper['sources'].items():
        if Path(name).suffix in ('.cpp','.h'):
            require(pair['sources'].get(name)==digest,'Pair used a different native handover source: '+name)
    helper_dll=Path(helper['production_dll']['path']);helper_sha=helper['production_dll']['sha256']
    require(helper_dll.resolve().is_relative_to(args.helper_build.resolve().parent) and
            helper['binaries'].get(str(helper_dll))==helper_sha and sha(helper_dll)==helper_sha,'Coordinator DLL closure differs')
    sys.path[:0]=[str(PRIVATE/'python_deps'),str(P.parents[1]/'outputs/san14-link')]
    from game_reader import GameReader
    from a_save_local_binding import source_hashes
    import b_warm_start_support,run_autonomous_pilot,checkpoint_live_prefetch_start,a_save_runtime_control,b_warm_start_acceptance
    reader=GameReader(pid=args.pid);port=None
    folder=PRIVATE/'b_warm_coordinator_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    result=dict(result='INCOMPLETE_RETAIN_EVIDENCE',room_ready=False,native_drained=False,staging_reuse_authorized=False)
    try:
        before=capture_planning(reader,profiles[0],plan['expected_ruler']);refuse_prior_attempt(reader.pid,before['birth'])
        pins=source_hashes()
        claims=PRIVATE/'b_warm_start_claims';claims.mkdir(exist_ok=True)
        save_new(claims/f'{reader.pid}-{before["birth"]}.json',dict(pid=reader.pid,birth=before['birth'],run=str(folder),
                    kind='two-bank-coordinator',automatic_retry_allowed=False))
        save_new(folder/'plan.json',plan)
        port=Resident(reader,folder,bank_dll,bank_sha,helper_dll,helper_sha,plan['steam_paths'],plan['expected_ruler'],args.timeout)
        result=run_two(port,profiles,plan['target'],plan['second_source'],folder)
        require(all(sha(P.parents[1]/n)==h for n,h in pins.items()),'Coordinator source changed during operation')
        result['sources']=pins
    except BaseException as exc:
        result.update(result='INCOMPLETE_RETAIN_EVIDENCE',error=repr(exc),room_ready=False,native_drained=False,staging_reuse_authorized=False)
    finally:
        if port:
            result['control_uncertain']=port.calls.uncertain
            port.close()
        reader.close();save_new(folder/'result.json',result)
    print(json.dumps(dict(result=result['result'],path=str(folder/'result.json'))))
    return 0 if result['result']=='PASS_TWO_WARM_DIAGNOSTIC_LOADS' else 1


if __name__=='__main__':raise SystemExit(main())
