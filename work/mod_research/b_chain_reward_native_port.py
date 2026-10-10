"""B chain reward providers: fresh one-shot DLL owner for each of two windows.
A durable local execution INTENT precedes Submit. Only this provider restores
its one User slot; it never installs A save sources or replaces the warm owner.
"""
from copy import deepcopy
from dataclasses import dataclass
import ctypes as C
import hashlib,json,secrets,shutil,threading,time
from pathlib import Path
import a_runtime_reward_port as common
from a_runtime_reward_port import base,Context,Actor,Submit,SharedCallState,RemoteCallUnknown,require,save_new
from reward_observed_context import ContextSampler,reward
from reward_rebind_context import CheckedPort
from b_remote_chain_session import Session
from b_observed_chain_completion import GuestCompletion
from b_warm_profile_contract import Profile,validate_profile
from b_warm_start_support import storage_bindings,live_hook_evidence
import b_warm_chain_coordinator_contract as hand_wire
import execution_journal as journal

OPS=dict(Configure=1,Submit=2,Snapshot=3,Stop=4,Restore=5)
SLOTS=((0x12CC4D0,0x3F9B00),(0x12DB4E8,0x4AA200),(0x12CC9E0,0x3F8140),
       (0x12DBD90,0x4A85C0),(0x138E8D0,0x4FABC0))
class Configure(base.Packed):
    _fields_=[('header',base.Header),('nonce',base.U8*32),('context',Context)]+[(n,base.U64) for n in ('base','root','world','cache')]+[
        ('states',base.U64*5),('year',base.U16),('ruler',base.U16),('month',base.U8),('day',base.U8),('viewer',base.U8),
        ('reserved',base.U8),('actors',Actor*2),('storageVtable',base.U64),('readOriginal',base.U64)]
class Snapshot(base.Packed):
    _fields_=common.Snapshot._fields_+[(n,base.U32) for n in ('armed','admissionClosed','nativeClean','restoreVerified','slotRestored')]+[
        (n,base.U64) for n in ('bridgeStarted','bridgeActive','bridgeFinally','bridgeCleanupFaults')]
assert (C.sizeof(Configure),C.sizeof(Snapshot))==(256,400)

@dataclass(frozen=True)
class NativeBuild:
    run:Path
    result_sha256:str

def approved_build(build):
    require(type(build) is NativeBuild,'Explicit B owner build required')
    folder=Path(build.run).resolve(strict=True);record=folder/'result.json'
    require(hashlib.sha256(record.read_bytes()).hexdigest()==build.result_sha256,'B build record changed')
    data=json.loads(record.read_text());require(data.get('result')=='PASS' and data.get('game_access') is False,
                                               'Passing owned B native build required')
    for field in ('sources','private_inputs','artifacts'):
        require(data.get(field),'Complete B native provenance required')
        for name,h in data[field].items():
            f=Path(name)
            if not f.is_absolute():f=common.HERE/f if field=='sources' else folder/f
            require(f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest()==h,'B build input changed: '+name)
    dll=Path(data['production_dll']).resolve(strict=True)
    require(dll.is_relative_to(folder) and dll.name=='b_reward_owner.dll','B-specific owner DLL required')
    approved={ (Path(n) if Path(n).is_absolute() else folder/n).resolve():h for n,h in data['artifacts'].items()}
    require(approved.get(dll)==hashlib.sha256(dll.read_bytes()).hexdigest(),'Unproved B owner binary')
    dependencies=[]
    for f in dll.parent.glob('*.dll'):
        if f==dll:continue
        require(approved.get(f.resolve())==hashlib.sha256(f.read_bytes()).hexdigest(),'Unproved B dependency')
        dependencies.append(f)
    return dict(dll=dll,sha256=approved[dll],dependencies=dependencies,record_sha256=build.result_sha256)

def retained_call(*args,**kw):
    # The legacy transport may raise while writing completion evidence. Unless
    # it returned a complete response, never infer that its remote thread ended.
    try:return common.remote_call(*args,**kw)
    except RemoteCallUnknown:raise
    except BaseException as exc:
        raise RemoteCallUnknown('B chain remote call did not return verified completion',
                                dict(error=repr(exc),automatic_retry=False)) from exc

class Transport(common.RemoteTransport):
    def _perform(self,name,payload):
        import pefile
        with self.lock:
            try:
                self._identity();require(name in {'BReward'+op for op in OPS},'B reward operation required')
                pe=pefile.PE(str(self.dll))
                try:
                    matches=[s for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name==name.encode('ascii')]
                    require(len(matches)==1 and not matches[0].forwarder,'Unique B code export required')
                    rva=matches[0].address;address=self.module+rva;expected=pe.get_data(rva,32)
                finally:pe.close()
                common.readable(self.api.reader,address,32,allocation=self.module,execute=True)
                require(len(expected)==32 and self.api.reader.memory.read(address,32)==expected,'B export bytes differ')
                self.calls+=1
                result=retained_call(self.api,address,payload,self.records,f'{self.calls:04d}-{name}')
                self._identity();return result
            except BaseException as exc:self.failed=repr(exc);raise

class NativePort(common.RuntimeRewardPort):
    @classmethod
    def open(cls,*,session,guest,profile,scope,records,build):
        require(type(session) is Session and type(guest) is GuestCompletion and guest.session is session,
                'Exact retained chain owners required')
        with guest._lock,session._lock:
            return cls._open(session=session,guest=guest,profile=profile,scope=scope,records=records,build=build)

    @classmethod
    def _open(cls,*,session,guest,profile,scope,records,build):
        require(type(session) is Session and type(guest) is GuestCompletion and guest.session is session,
                'Same exact B checkpoint owners required')
        window=len(guest.history)
        require(window in (1,2) and session.phase==guest.phase=='ACTIVE' and len(session.sessions)==window and
                guest.period==window+1 and not session.lifecycle.current.retired and not session.warm.calls.uncertain,
                'First formal loaded B world required')
        claims=getattr(session,'_b_chain_reward_native',None)
        if claims is None:claims={};session._b_chain_reward_native=claims
        require(window not in claims and set(claims)==set(range(1,window)),
                'Ordered once-only reward owners; never reset a failed claim')
        if window>1:
            previous=claims[window-1]
            require(journal.canonical(scope)!=previous.scope_bytes and guest.epoch!=previous.bound[3] and
                    guest.attachments['B']!=previous.bound[4]['B'],'Fresh native reward scope/attachment required')
            previous.verify_retired_successor()
        require(type(profile) is Profile,'Typed first load profile required');validate_profile(profile);journal.validate_scope(scope)
        require(all(scope[k]==session.scope[k] for k in ('room_id','binding_epoch','profile','bindings')),
                'Reward scope differs from retained room')
        from b_chain_input_transition import observe_completed
        observe_completed(session,guest)
        current=session.boundary.profile
        require(bytes(current.file)==bytes(profile.file) and bytes(current.loaded)==bytes(profile.loaded) and
                bytes(current.source)==bytes(profile.source) and bytes(current.target)==bytes(profile.target),
                'Native reward profile differs from current loaded world')
        approved=approved_build(build);records=Path(records);records.mkdir(parents=True,exist_ok=False)
        obj=cls.__new__(cls);claims[window]=obj;obj.window=window
        obj.session,obj.guest=session,guest;obj.profile_bytes=bytes(profile);obj.scope_bytes=journal.canonical(scope)
        obj.bound=(session.reader,session.warm,session.lifecycle.current,guest.epoch,deepcopy(guest.attachments),guest.history[window-1]['checkpoint_id'])
        obj.closed=False;obj.restore_attempted=False;obj.restoration=None;obj.failed=None;obj.records=records
        obj.state=SharedCallState(threading.RLock(),obj._unknown) if window==1 else claims[window-1].state
        obj.state.require_known()
        obj.input_owner=None
        try:
            obj._bind_shared_input()
            session.boundary.observe();bank=session.warm.current
            require(bank is not None and bank['index']==window-1 and bank.get('load_accepted') and bank.get('warm_load_retired') and bank.get('refresh_load_retired'),
                    'First warm load must have fully retired before B reward')
            helper=session.warm.hand(hand_wire.Observe)
            require(helper.currentGeneration==window and helper.certificateCount==window-1 and
                    list(helper.banks)[:window]==[b['module'] for b in session.warm.banks] and
                    all(helper.completed[i]==1 for i in range(window)),'Native chain completion required')
            r=session.reader;api=session.warm.api
            require(api.reader is r and session.read_birth()==session.native_identity[1],'Retained B process differs')
            storage=storage_bindings(r,api.modules(),steam_paths=session.warm.steam)
            planning=dict(base=r.memory.base,nativeSlots=[(r.memory.base+s,r.memory.base+o) for s,o in SLOTS])
            obj.slot_baseline=live_hook_evidence(r,planning,storage,baseline=session.warm.first_hooks)
            obj.slot_planning,obj.slot_storage=planning,storage
            players={p.force:dict(ruler=p.ruler,district=p.district) for p in (profile.source,profile.target)}
            ctx=Context();ctx.pid=r.pid;ctx.birth=session.native_identity[1];ctx.period=guest.period;ctx.epoch=secrets.randbits(64) or 1
            ctx.native.attempt[:]=secrets.token_bytes(16);ctx.native.attachment[:]=bytes.fromhex(guest.attachments['B']);ctx.native.ownerGeneration=window
            ctx.inputDigest[:]=bytes.fromhex(journal.digest(dict(scope=scope,checkpoint=obj.bound[-1],profile=hashlib.sha256(bytes(profile)).hexdigest(),attachment=guest.attachments['B'])))
            obj.local_epoch=format(ctx.epoch,'032x');obj.attachment=guest.attachments['B']
            sampler=ContextSampler(r,pid=r.pid,birth=ctx.birth,epoch=obj.local_epoch,attachment_id=obj.attachment,
                current_binding=obj._local_binding,node=dict(year=profile.loaded.year,month=profile.loaded.month,day=profile.loaded.day),
                viewer=profile.target.force,players=players,read_birth=session.read_birth)
            # Keep all unknown calls on the same retained process gate. A failed
            # load/configure is never retried and its loaded module is retained.
            module_dir=records/'module';module_dir.mkdir()
            owner_name=f'b_chain_reward_owner_{window}_{bytes(ctx.native.attempt).hex()}.dll'
            for source in [*approved['dependencies'],approved['dll']]:
                path=module_dir/(owner_name if source==approved['dll'] else source.name);shutil.copyfile(source,path)
                require(hashlib.sha256(path.read_bytes()).hexdigest()==hashlib.sha256(source.read_bytes()).hexdigest(),'Copied B binary differs')
                matches=[Path(p) for _,p in api.modules() if Path(p).name.casefold()==path.name.casefold()]
                require(all(hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256(source.read_bytes()).hexdigest() for p in matches),'Conflicting resident B dependency')
                if source==approved['dll']:require(not matches,'B owner already resident; no second owner')
                obj.state.invoke(lambda path=path:retained_call(api,api.load_library_address(),str(path).encode('utf-16le')+b'\0\0',records,'load-'+path.stem))
            dll=module_dir/owner_name;found=[a for a,p in api.modules() if Path(p).resolve()==dll.resolve()]
            require(len(found)==1,'B owner module unresolved')
            native_records=records/'calls';native_records.mkdir()
            transport=Transport(api,module=found[0],dll=dll,dll_sha256=approved['sha256'],pid=ctx.pid,birth=ctx.birth,
                                records=native_records,call_state=obj.state)
            common.RuntimeRewardPort.__init__(obj,sampler,transport,nonce=secrets.token_bytes(32),context=ctx,records=records)
            q=obj._request(Configure,'Configure');q.base=r.memory.base;q.root=r.pointer(q.base+0x1FCA1E0);q.world=r.pointer(q.root+0x85130);q.cache=r.pointer(q.base+0x2025318)
            q.states[:]=[a for _,a in r.state_objects()];q.year=profile.loaded.year;q.month=profile.loaded.month;q.day=profile.loaded.day
            q.viewer=profile.target.force;q.ruler=profile.target.ruler
            for dst,(f,v) in zip(q.actors,sorted(players.items())):dst.force,dst.ruler,dst.district=f,v['ruler'],v['district']
            q.storageVtable=storage['storageVtable'];q.readOriginal=storage['read']['address'];obj.configuration=q
            obj.config_attempted=True;obj._call('Configure',q);obj.configured=True
            s=obj._call('Snapshot',obj._request(Snapshot,'Snapshot'))
            require(s.configured==s.armed==s.nativeClean==1 and s.state==1 and not any((s.error,s.queued,s.active,s.uncertain,s.stopped,s.admissionClosed)),
                    'B owner did not install into an idle reward lane')
            obj.checked_port=CheckedPort(sampler,obj)
            return obj
        except BaseException as exc:
            obj._terminal(exc);exc.retained_native_port=obj;raise

    def _bind_shared_input(self):
        from player_input_rebind_port import InputLease
        owner=getattr(self.session,'_chain_input_owner',None)
        if owner is None:
            require(self.window==1 or self.session._b_chain_reward_native[self.window-1].input_owner is None,
                    'Retained input owner disappeared between reward windows')
            return
        require(type(owner) is InputLease and type(owner.state) is SharedCallState and
                owner.transport.state is owner.state,'Exact retained shared input owner required')
        with owner.lock:
            owner.state.require_known();g=self.guest;s=self.session;b=owner.binding
            require(owner.failed is None and owner.active is None and
                    owner.local_binding==(*s.native_identity,g.epoch,g.attachments['B']) and
                    bytes(b.room).hex()==s.scope['room_id'] and b.period==g.period and b.seat==1 and
                    bytes(b.epoch).hex()==g.epoch and bytes(b.attachment).hex()==g.attachments['B'] and
                    s._chain_input_transitions[self.window]['phase']=='REBOUND_HELD',
                    'Input owner not rebound to this completed checkpoint')
            if self.window>1:require(owner.state is self.state,'Input unknown gate changed between windows')
            snapshot=owner.snapshot()
            require(snapshot.phase==2 and snapshot.held and snapshot.acknowledged and not snapshot.localReady and
                    snapshot.revision==snapshot.acknowledgedRevision and snapshot.leasesIssued==snapshot.leasesCompleted and
                    not any((snapshot.pending,snapshot.active,snapshot.leaseId,snapshot.localCommandPolicyOpen,
                             snapshot.remoteExecutionPolicyOpen)),'Reward installation requires acknowledged drained LOAD input')
            self.state=owner.state;self.input_owner=owner

    def verify_retired_successor(self):
        """Read the old immutable owner after load, without reviving its world context."""
        try:
            s=self.session;g=self.guest;r,w,_,_,_,_=self.bound
            require(self.failed is None and self.closed and self.restore_attempted and self.restoration is not None,
                    'Predecessor native bridge lacks verified retirement')
            require(s.reader is r and s.warm is w and len(g.history)==len(s.sessions)==self.window+1 and
                    s.phase==g.phase=='ACTIVE' and not w.calls.uncertain and not getattr(s.factory,'uncertain',False) and
                    s.read_birth()==s.native_identity[1], 'Retired predecessor process/chain changed')
            self.state.require_known()
            q=self._request(Snapshot,'Snapshot');self.calls+=1;label=f'{self.calls:04d}-RetiredSnapshot'
            save_new(self.records/(label+'-request.json'),base.values(q))
            code,raw=self.transport.call('BRewardSnapshot',bytes(q))
            require(type(raw) is bytes and len(raw)==C.sizeof(q),'Retired owner reply size differs')
            result=Snapshot.from_buffer_copy(raw)
            require(bytes(result.header)[:16]==bytes(q.header)[:16] and bytes(result.nonce)==self.nonce and
                    bytes(result.context)==bytes(self.context) and code==0 and result.header.result==0,
                    'Retired owner reply binding differs')
            self._require_restored(result)
            live_hook_evidence(r,self.slot_planning,self.slot_storage,baseline=self.slot_baseline)
            save_new(self.records/(label+'-reply.json'),dict(exit=code,report=base.values(result)))
            return dict(native_bridge_restored=True,native_drained=True,window=self.window,automatic_retry=False)
        except BaseException as exc:self._terminal(exc);raise

    @staticmethod
    def _require_restored(s):
        require(s.admissionClosed==s.nativeClean==s.restoreVerified==s.slotRestored==s.stopped==1 and s.armed==0 and
                s.submitted==s.completed and s.bridgeStarted==s.bridgeFinally and
                not any((s.error,s.ownerError,s.replayError,s.uncertain,s.queued,s.active,s.bridgeActive,s.bridgeCleanupFaults)),
                'B source restoration or drain is incomplete')

    def _graph(self):
        s=self.session;g=self.guest;r,w,p,epoch,attachments,checkpoint=self.bound
        require(self.failed is None and s._b_chain_reward_native.get(self.window) is self and
                g.period==self.window+1 and s.reader is r and s.warm is w and s.lifecycle.current is p and not p.retired and
                s.phase in ('ACTIVE','REWARD_PLANNING') and g.phase=='ACTIVE' and len(s.sessions)==len(g.history)==self.window and
                g.epoch==epoch and g.attachments==attachments and g.history[self.window-1]['checkpoint_id']==checkpoint and
                not w.calls.uncertain and not getattr(s.factory,'uncertain',False) and s.read_birth()==s.native_identity[1],
                'B retained world/owner/unknown state changed')
        self.state.require_known()
        if self.input_owner is not None:
            require(getattr(s,'_chain_input_owner',None) is self.input_owner and self.input_owner.state is self.state and
                    self.input_owner.transport.state is self.state,'Retained input gate changed')
    def _local_binding(self):
        self._graph();return self.local_epoch,self.attachment
    def identity(self):
        self._graph();require(not self.closed,'B reward epoch closed')
        return super().identity()
    def _unknown(self,exc):
        self.session.warm.calls.uncertain=True;self.session.factory.uncertain=True
        self.session.phase='TERMINAL';self.session.boundary.hold(repr(exc))
    def _terminal(self,exc):
        if isinstance(exc,RemoteCallUnknown):self._unknown(exc)
        if self.failed is None:self.failed=repr(exc)
        if hasattr(self,'sampler'):self.sampler.retire(self.failed)
        self.session.phase='TERMINAL';self.session.boundary.hold(self.failed)
    def _fail(self,exc):
        super()._fail(exc);self._terminal(exc)
    def _request(self,typ,op):
        q=typ();q.header=base.Header(base.MAGIC,base.VERSION,C.sizeof(typ),OPS[op],0);q.nonce[:]=self.nonce
        if hasattr(q,'context'):q.context=self.context
        return q
    def _call(self,op,q):
        self._graph();self.calls+=1;label=f'{self.calls:04d}-{op}'
        save_new(self.records/(label+'-request.json'),base.values(q))
        code,raw=self.transport.call('BReward'+op,bytes(q));require(type(raw) is bytes and len(raw)==C.sizeof(q),'B reply size differs')
        value=type(q).from_buffer_copy(raw)
        require(bytes(value.header)[:16]==bytes(q.header)[:16] and bytes(value.nonce)==self.nonce,'Foreign B reply envelope')
        if hasattr(value,'context'):require(bytes(value.context)==bytes(self.context),'Foreign B context')
        save_new(self.records/(label+'-reply.json'),dict(exit=code,report=base.values(value)))
        require(code==0 and value.header.result==0,'Native B request rejected')
        if op!='Snapshot':require(raw[20:]==bytes(q)[20:],'B request echo changed')
        self._graph();return value
    def stop_restore(self):
        try:
            self._graph();require(not self.restore_attempted,'B restoration attempted already');self.restore_attempted=True
            s=self._call('Snapshot',self._request(Snapshot,'Snapshot'))
            require(s.submitted==s.completed and s.nativeClean==1 and not any((s.error,s.queued,s.active,s.uncertain,s.bridgeActive,s.bridgeCleanupFaults)),
                    'B reward lane has not drained')
            self.closed=True
            self._call('Stop',self._request(base.Command,'Stop'))
            self._call('Restore',self._request(base.Command,'Restore'))
            self.restoration=self.verify_restored();return deepcopy(self.restoration)
        except BaseException as exc:self._terminal(exc);raise
    def verify_restored(self):
        try:
            self._graph();require(self.restore_attempted and self.closed,'B native restore was not requested')
            s=self._call('Snapshot',self._request(Snapshot,'Snapshot'))
            require(s.admissionClosed==s.nativeClean==s.restoreVerified==s.slotRestored==s.stopped==1 and s.armed==0 and
                    s.submitted==s.completed and s.bridgeStarted==s.bridgeFinally and
                    not any((s.error,s.ownerError,s.replayError,s.uncertain,s.queued,s.active,s.bridgeActive,s.bridgeCleanupFaults)),
                    'B source restoration or drain is incomplete')
            r=self.session.reader
            live_hook_evidence(r,self.slot_planning,self.slot_storage,baseline=self.slot_baseline)
            return dict(native_bridge_restored=True,native_drained=True,report=base.values(s),
                        automatic_retry=False,input_exclusion_proven=False)
        except BaseException as exc:self._terminal(exc);raise

    def execute(self,command):
        with self.sampler.lock,self.lock:
            try:
                self.identity();require(self.configured,'Configure retained Runtime before dispatch')
                intent=common.pending_intent(self.db,command,self.binding[3]);seq=intent['sequence']
                require(seq not in self.attempted,'Submit was already attempted; never replay')
                contexts,_=self.sampler.capture();force=command['force_id']
                preview=reward.validate_reward(command,contexts[force],force)
                require(len(command['officer_ids'])<=16,'Native owned reward limit is sixteen officers')
                q=self._request(Submit,'Submit');q.sequence=seq;c=q.command
                c.nonce[:]=bytes.fromhex(journal.digest(intent));c.year=command['date']['year'];c.month=command['date']['month'];c.day=command['date']['day']
                c.viewer=self.sampler.viewer;c.actor=force;c.ruler=self.sampler.players[force]['ruler'];c.city=command['funding_city_id']
                c.district=preview['expected_costs']['charged_district_id'];c.count=len(command['officer_ids'])
                c.officers[:c.count]=command['officer_ids'];c.expiresAtTick=self.ticks()+int(self.wait*1000)
                expected_hash=common.command_hash(self.context,c);deadline=self.clock()+self.wait
                self.attempted.add(seq);self._call('Submit',q)
                while True:
                    s=self._call('Snapshot',self._request(Snapshot,'Snapshot'))
                    require(s.configured==1 and s.sequence==seq and
                            not any((s.error,s.ownerError,s.replayError,s.uncertain,s.stopped,s.abnormalCalls,
                                     s.fullInputHold,s.worldFenceProven,s.nativeGameplayEnabled)),
                            'Reward report failed, foreign, or claims unsupported coverage')
                    require(s.state in (2,3,4),'Reward left admitted execution lifecycle')
                    if s.state==2:
                        require(s.submitted==seq and s.completed==seq-1,
                                'Queued request must retain the preceding completed native lane')
                    else:
                        require(s.submitted==seq and s.completed in (seq-1,seq),
                                'Native lane does not belong to this submitted sequence')
                    if s.state==4:
                        require(s.completed==seq and s.readyResealed==0 and s.nativeClean==1 and s.armed==1 and
                                s.admissionClosed==0 and s.bridgeActive==0 and s.bridgeStarted==s.bridgeFinally and s.bridgeCleanupFaults==0 and s.queued==0 and s.active==0 and s.hostThread!=0 and
                                s.replayState==3 and s.nativeReturned==s.argsReleased==s.ownedSlotCleared==1 and
                                s.ctorCalls==s.dtorCalls==s.executeCalls==1 and s.appendCalls==c.count and s.captureCalls>0 and
                                s.finallyCalls>0 and bytes(s.commandSha256)==expected_hash and any(s.semanticSha256),
                                'Native completion, cleanup, or exact command proof missing')
                        result=dict(native_returned=True,args_released=True,owned_slot_cleared=True,error=0,uncertain=False,
                                    sequence=seq,command_sha256=expected_hash.hex(),report=base.values(s),
                                    input_exclusion_proven=False,native_gameplay_enabled=False)
                        self.receipts.append(result);return result
                    require(self.clock()<deadline,'Reward completion unresolved; retain INTENT and never replay')
                    self.sleep(min(self.poll,max(0,deadline-self.clock())))
            except BaseException as exc:self._fail(exc);raise
