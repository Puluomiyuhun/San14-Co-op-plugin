"""One retained A Runtime, same Room reward queue, and explicit checkpoint cut.

Only the first post-bootstrap planning period is mounted. This component opens
no process, installs no extra User hook, and never interprets a network ack as
native completion or native input exclusion.
"""
from copy import deepcopy
import ctypes as C
import hashlib
import json
from pathlib import Path
import threading
import time

import a_runtime_reward_port as reward_port
from a_runtime_reward_port import base,require,save_new,RemoteCallUnknown,SharedCallState
from reward_observed_context import ContextSampler,CheckedPort,reward
from reward_observed_flow import ObservedRewardFlow,GuestConsumer
from a_observed_room import ObservedRoom
from a_room_bootstrap_protocol import BootstrapCoordinator
from observed_room_service import HostService
from b_warm_profile_contract import Profile,Date,Identity,validate_profile


def approved_planning_runtime(args,baseline):
    """Explicit new build proof; retain predecessor publisher/ABI checks."""
    folder=Path(args.reward_build_run).resolve(strict=True);record=folder/'result.json'
    require(hashlib.sha256(record.read_bytes()).hexdigest()==args.reward_build_sha256,'Planning Runtime build record differs')
    data=json.loads(record.read_text());require(data['result']=='PASS' and data['game_access'] is False and data['steam_access'] is False,
                                             'Passing owned planning Runtime build required')
    for field in ('sources','private_inputs','artifacts'):
        require(data.get(field),'Complete planning Runtime provenance required')
        for name,expected in data[field].items():
            path=(reward_port.HERE/name) if field=='sources' else ((folder/name) if field=='artifacts' else Path(name))
            require(hashlib.sha256(path.read_bytes()).hexdigest()==expected,'Planning build input/artifact changed: '+name)
    require({r['case'] for r in data['cases']}=={'bootstrap','planning-stop','normal'} and
            all(r['output'][-1]['passed'] is True for r in data['cases']),'Actual bootstrap/reward/regression evidence required')
    dll=Path(data['production_dll']).resolve(strict=True)
    require(dll==folder/'production/a_save_local_runtime.dll' and
            [value for name,value in data['artifacts'].items() if (folder/name).resolve()==dll]==[hashlib.sha256(dll.read_bytes()).hexdigest()],
            'Single proven production planning Runtime required')
    build=deepcopy(baseline)
    for name in ('a_save_local_runtime.dll','checkpoint_planning_hold.dll'):
        path=dll.parent/name;build['production']['binaries'][name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return build,data


class Open(base.Packed):
    _fields_=[('header',base.Header),('nonce',base.U8*32),('context',reward_port.Context),
              ('generation',base.U64),('artifactSha256',base.U8*32)]
class PlanningSnapshot(base.Packed):
    _fields_=Open._fields_+[(n,base.U32) for n in ('state','error','hostThread','opened','receiptMatched','stopped')]
assert C.sizeof(Open)==192 and C.sizeof(PlanningSnapshot)==216


class MountTransport(reward_port.RemoteTransport):
    def _perform(self,name,payload):
        if name not in ('ASaveRuntimeOpenPlanning','ASaveRuntimePlanningSnapshot'):
            return super()._perform(name,payload)
        import pefile
        with self.lock:
            try:
                self._identity();pe=pefile.PE(str(self.dll))
                try:
                    matches=[x for x in pe.DIRECTORY_ENTRY_EXPORT.symbols if x.name==name.encode('ascii')]
                    require(len(matches)==1 and not matches[0].forwarder,'Unique planning code export required')
                    address=self.module+matches[0].address;expected=pe.get_data(matches[0].address,32)
                finally:pe.close()
                reward_port.readable(self.api.reader,address,32,allocation=self.module,execute=True)
                require(len(expected)==32 and self.api.reader.memory.read(address,32)==expected,'Planning export differs')
                self.calls+=1
                value=reward_port.remote_call(self.api,address,payload,self.records,f'{self.calls:04d}-{name}')
                self._identity();return value
            except BaseException as exc:self.failed=repr(exc);raise


class MappedRewardPort(reward_port.RuntimeRewardPort):
    """Separate immutable Room attachment and native binding, verified locally.

    All requests/replies retain the original native Context. The journal binds
    the Room attachment. Neither is overwritten to manufacture numeric equality.
    """
    def __init__(self,sampler,transport,*,mount,records):
        require(type(mount) is RuntimeMount and mount.sampler is sampler and mount.transport is transport,
                'Only this bound Runtime mount may map attachments')
        c=reward_port.context_from_prepare(mount.prep)
        require((sampler.pid,sampler.birth)==(c.pid,c.birth) and
                sampler.attachment_id==mount.attachment and bytes(mount.prep)==mount.prepared_bytes,
                'Room/native attachment map changed')
        self.sampler,self.transport=sampler,transport;self.nonce=bytes(mount.prep.nonce);self.context=c
        self.records=Path(records).resolve(strict=True);require(self.records.is_dir(),'Private reward call records required')
        self.binding=(sampler.pid,sampler.birth,sampler.epoch,sampler.attachment_id)
        self.wait,self.poll=10,.02;self.clock,self.sleep,self.ticks=time.monotonic,time.sleep,reward_port.ticks
        self.lock=threading.RLock();self.failed=None;self.configured=False;self.config_attempted=False
        self.db=None;self.attempted=set();self.calls=0;self.receipts=[]


class MountedEndpoint:
    def __init__(self,mount,previous):self.mount,self.previous=mount,previous
    def authenticate(self,*args):return self.previous.authenticate(*args)
    def handle(self,player,connection,request):
        if isinstance(request,dict) and str(request.get('action','')).startswith('reward_'):
            return self.mount.gate.handle(player,connection,request)
        return self.previous.handle(player,connection,request)
    def disconnect(self,player,connection):
        m=self.mount
        with m.room.lock:
            current_b=(player=='B' and m.room.players.get('B',{}).get('connection')==connection)
        try:
            if m.gate is not None and m.phase=='ACTIVE':return m.gate.disconnect(player,connection)
            return self.previous.disconnect(player,connection)
        finally:
            if current_b:m.service.guest_disconnected.set()


class RuntimeMount:
    def __init__(self,service,*,reward_key,guest_cut_key,records,wait_seconds=10):
        require(type(service) is HostService and type(service.room) is ObservedRoom,
                'Actual retained HostService required')
        require(all(type(k) is bytes and len(k)==32 and any(k) for k in (reward_key,guest_cut_key)),
                'Separately provisioned local reward/cut keys required')
        require(0<wait_seconds<=30,'Bounded native planning wait required')
        self.service=service;self.room=service.room;self.c=service.coordinator
        require(type(self.c) is BootstrapCoordinator,'Bound actual bootstrap coordinator required')
        self.reward_key,self.cut_key=reward_key,guest_cut_key
        self.records=Path(records).resolve();self.records.mkdir(parents=True,exist_ok=False)
        self.wait=wait_seconds;self.phase='NEW';self.failure=None;self.gate=self.flow=self.native=self.entry=None
        self.transport=self.sampler=None;self.planning_request=None;self.serial=0

    def bind_native(self,entry,api,module,dll,prep,plans,call_state,read_birth):
        require(self.phase=='NEW' and type(call_state) is SharedCallState,'Fresh mount/shared control required')
        require(entry.room is self.room and entry.coordinator is self.c and entry.provider.reader is api.reader and
                bytes(entry.prep)==bytes(prep) and plans.module==module and bytes(plans.nonce)==bytes(prep.nonce),
                'Mount must use the same prepared entry, reader, module and nonce')
        self.phase='BINDING';self.entry,self.api,self.module=entry,api,module
        self.prep=base.Prepare.from_buffer_copy(bytes(prep));self.prepared_bytes=bytes(prep);self.state=call_state
        self.attachment=self.c.attachments['A'];self.local_epoch=format(prep.epoch,'032x')
        self.players={}
        try:
            with self.room.lock,self.c.lock:
                self.room._bound(self.c)
                for value in self.c.scope['bindings'].values():
                    force=value['force_id'];address=api.reader.pointer(prep.root+0xDCA0+force*8)
                    api.reader.require_type(address,'CForceData')
                    ruler=int.from_bytes(api.reader.memory.read(address+0x10,2),'little')
                    require(0<ruler<6000,'Current native ruler required')
                    self.players[force]=dict(ruler=ruler,district=value['main_district_id'])
            native_dir=self.records/'native';native_dir.mkdir()
            self.transport=MountTransport(api,module=module,dll=dll,dll_sha256=reward_port.hashlib.sha256(Path(dll).read_bytes()).hexdigest(),
                pid=prep.pid,birth=prep.birth,records=native_dir,call_state=call_state)
            self.sampler=ContextSampler(api.reader,pid=prep.pid,birth=prep.birth,epoch=self.local_epoch,
                attachment_id=self.attachment,current_binding=self._local_binding,node=dict(year=prep.year,month=prep.month,day=prep.day),
                viewer=prep.force,players=self.players,read_birth=read_birth)
            call_dir=self.records/'typed';call_dir.mkdir()
            self.native=MappedRewardPort(self.sampler,self.transport,mount=self,records=call_dir)
            self.port=CheckedPort(self.sampler,self.native)
            self.native.configure();self.phase='CONFIGURED'
        except BaseException as exc:self.hold(exc);raise

    def _local_binding(self):
        require(self.failure is None and self.c.attachments['A']==self.attachment and
                self.entry.provider.reader is self.api.reader and bytes(self.prep)==self.prepared_bytes,
                'Retained native/Room mapping changed')
        return self.local_epoch,self.attachment

    def _planning_call(self,kind,operation):
        q=kind.from_buffer_copy(bytes(self.planning_request)+bytes(C.sizeof(kind)-C.sizeof(Open)))
        q.header=base.Header(base.MAGIC,base.VERSION,C.sizeof(kind),operation,0)
        self.serial+=1;label=f'planning-{self.serial:04d}'
        save_new(self.records/(label+'-request.json'),base.values(q))
        code,raw=self.transport.call('ASaveRuntime'+('OpenPlanning' if operation==14 else 'PlanningSnapshot'),bytes(q))
        require(len(raw)==C.sizeof(kind),'Planning response size differs');r=kind.from_buffer_copy(raw)
        require(code==0 and r.header.result==0 and bytes(r.header)[:16]==bytes(q.header)[:16] and raw[20:192]==bytes(q)[20:192],
                'Planning response context/generation/artifact differs')
        save_new(self.records/(label+'-reply.json'),base.values(r));return r

    def planning_quiet(self):
        """Extra finite evidence for the successor observer; never edit Snapshot."""
        require(self.planning_request is not None and self.phase in ('ACTIVE','CUT_READY','RETIRED'),
                'No authenticated native planning receipt')
        p=self._planning_call(PlanningSnapshot,15)
        require(p.state==2 and p.opened==p.receiptMatched==1 and p.hostThread and not(p.error or p.stopped),
                'Native planning is not open and quiet')
        q=self.native._request(reward_port.Snapshot,'Snapshot')
        code,raw=self.transport.call('ASaveRuntimeRewardSnapshot',bytes(q))
        require(code==0 and len(raw)==C.sizeof(q),'Reward quiet snapshot unavailable')
        s=reward_port.Snapshot.from_buffer_copy(raw)
        require(bytes(s.header)==bytes(q.header) and raw[20:152]==bytes(q)[20:152],
                'Reward quiet snapshot belongs to another native binding')
        require(s.state in (1,4) and s.submitted==s.completed and not any((s.error,s.queued,s.active,s.uncertain,s.stopped,s.ownerError,s.replayError)),
                'Reward lane is not quiescent')
        return p

    def open(self,artifact,package,prep):
        try:
            require(self.phase=='CONFIGURED' and bytes(prep)==self.prepared_bytes,'Planning open is once-only')
            with self.room.lock,self.c.lock:
                self.room._bound(self.c);receipt=self.c.applied_receipts.get(package.checkpoint_id)
                remote=self.room._remote
                row=remote['rows'].get(package.checkpoint_id) if remote is not None else None
                require(self.c.bootstrap_completed and self.c.period==2 and self.c.phase=='PLANNING' and
                    len(self.c.applied_receipts)==1 and receipt is not None and receipt['checkpoint_id']==package.checkpoint_id and
                    row is not None and row.get('observed_complete') is not None and row['reply'].get('ok') is True and
                    row['context']['manifest']==package.manifest and
                    artifact.sha256==hashlib.sha256(artifact.data).hexdigest() and package.manifest['node']==self.c.node,
                    'Actual first artifact and formal bootstrap completion required')
                from b_warm_remote_completion import profile_from
                p=profile_from(row['profile'])
            # Same-day bootstrap must preserve the five native state objects.
            # Do not repin a reconstructed User to manufacture continuity.
            self.sampler.capture()
            q=Open();q.nonce[:]=prep.nonce;q.context=reward_port.context_from_prepare(prep);q.generation=1;q.artifactSha256[:]=bytes.fromhex(artifact.sha256)
            self.planning_request=q;self.phase='OPENING';self._planning_call(Open,14);deadline=time.monotonic()+self.wait
            while True:
                s=self._planning_call(PlanningSnapshot,15)
                require(not(s.error or s.stopped) and s.state in (1,2),'Native planning open failed')
                if s.state==2:
                    require(s.opened==s.receiptMatched==1 and s.hostThread,'Native planning receipt incomplete');break
                require(time.monotonic()<deadline,'Native planning did not open; do not resubmit');time.sleep(.02)
            self.phase='ACTIVE'
            self.flow=ObservedRewardFlow(self.records/'queue',self.room,self.port,self.c.attachments['B'],
                deepcopy(self.c.node),guest_report_key=self.reward_key)
            self.native.attach_journal(self.flow.host.journal)
            # Concrete shared-cut imports are intentionally local: loading the
            # inert startup module must never create a Room or native owner.
            from reward_checkpoint_shared_cut import SharedCutGate
            from reward_checkpoint_observer import CutObserver
            a,b=(self.c.scope['bindings'][side]['force_id'] for side in ('A','B'))
            require((p.source.force,p.source.ruler,p.source.district)==(a,self.players[a]['ruler'],self.players[a]['district']) and
                    (p.target.force,p.target.ruler,p.target.district)==(b,self.players[b]['ruler'],self.players[b]['district']) and
                    (p.loaded.year,p.loaded.month,p.loaded.day)==(prep.year,prep.month,prep.day),
                    'Completed bootstrap profile does not bind the current reward actors/date')
            self.profile=p;self.observer=CutObserver(self.flow.host,p)
            self.gate=SharedCutGate(self.room,self.c,self.flow,self.observer,guest_cut_key=self.cut_key)
            server=self.service.servers[0][0];self.previous_endpoint=server.room
            server.room=MountedEndpoint(self,self.previous_endpoint)
            save_new(self.records/'mounted.json',dict(native_context=base.values(q.context),room_period=self.c.period,
                room_epoch=self.c.epoch,attachment=self.attachment,independent_owner_installed=False,input_exclusion_proven=False))
        except BaseException as exc:self.hold(exc);raise

    def poll(self):
        if self.phase=='RETIRED':return
        require(self.phase=='ACTIVE','Reward mount is not active')
        try:
            if self.gate.state=='ACTIVE':
                with self.gate.lock,self.flow.lock:
                    if self.flow.last_guest is None:return
                    self.gate.pump_one();self.gate.prepare_cut()
            if self.gate.state=='COLLECTING':self.gate.close_drained()
            if self.gate.state=='RETIRED_SHARED_CUT':
                self.phase='RETIRED'
                # A explicitly ended its command period before the cut was
                # issued. Existing service still performs the actual Ready.
                self.service.ready_for_turn()
        except BaseException as exc:self.hold(exc);raise

    def validate_seal(self,seal):return self.gate.assert_sealed(seal)
    def observe_sealed(self,node):
        self.entry.protection.verify()
        return self.gate.observe_sealed(node)
    def hold(self,reason):
        self.failure=self.failure or repr(reason);self.phase='HELD'
        if self.gate is not None:self.gate._hold(reason)
        elif self.native is not None:self.native._fail(reason if isinstance(reason,BaseException) else RuntimeError(str(reason)))
        if self.entry is not None:self.entry.hold('REWARD_MOUNT_FAILED')
    def status(self):
        return dict(phase=self.phase,failure=self.failure,room_period=self.c.period,
            native_period=self.prep.period if hasattr(self,'prep') else None,native_unknown=self.state.unknown if hasattr(self,'state') else None,
            input_exclusion_proven=False,native_gameplay_enabled=False)


class GuestCutConsumer:
    """Thin retained B pump; native B executor must already be bound locally.

    Explicit finish_input is separate from polling. Loss of any response is
    terminal, including a possibly accepted signed cut; no replay is attempted.
    """
    def __init__(self,consumer,profile,*,cut_key,checkpoint_epoch):
        from reward_checkpoint_observer import CutObserver,key_check
        require(type(consumer) is GuestConsumer,'Existing retained B reward consumer required')
        key_check(cut_key);require(reward_port.journal.hex_id(checkpoint_epoch,32),'Current checkpoint epoch required')
        self.consumer=consumer;self.observer=CutObserver(consumer.replica,profile);self.key=cut_key;self.epoch=checkpoint_epoch
        self.prepared=False;self.attest_attempted=False;self.ready_attempted=False;self.failed=None
    def _request(self,value):
        require(self.failed is None,'Guest cut owner is terminal')
        try:
            r=self.consumer.control.request(value);require(r.get('ok') is True,'Reward/cut endpoint rejected request');return r
        except BaseException as exc:self.failed=repr(exc);self.consumer._fail(exc);raise
    def finish_input(self):
        require(not self.prepared,'Input-finished notification is once-only');self.prepared=True
        return self._request(dict(action='reward_cut_prepare',epoch=self.epoch))
    def poll(self):
        try:
            status=self._request(dict(action='reward_cut_status'))
            if status['state']=='ACTIVE':return self.consumer.consume_one()
            if status['state']=='COLLECTING' and not self.attest_attempted:
                require(self.prepared,'Cannot attest before explicitly ending input')
                self.attest_attempted=True
                return self._request(self.observer.attest(status['challenge'],self.key))
            require(status['state'] in ('COLLECTING','RETIRED_SHARED_CUT'),'Reward cut held or retired incorrectly')
            return status
        except BaseException as exc:
            if self.failed is None:self.failed=repr(exc);self.consumer._fail(exc)
            raise
    def ready_after_cut(self):
        require(not self.ready_attempted,'B Ready after cut is once-only');self.ready_attempted=True
        status=self._request(dict(action='reward_cut_status'))
        require(self.prepared and status['state']=='RETIRED_SHARED_CUT' and status['receipt']['checkpoint_cut_installed'],
                'Actual paired checkpoint cut required before B Ready')
        return self._request(dict(action='period_ready',epoch=self.epoch,ready=True))
