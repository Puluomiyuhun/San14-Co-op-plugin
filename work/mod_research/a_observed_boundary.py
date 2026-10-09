"""A-side repeated observations with installed owned hooks; never a fence.

No discovery, process opening, game writes, native control, or implicit retries.
The retained launcher supplies approved typed Plans and read-only Snapshot calls.
"""
from dataclasses import dataclass
import ctypes as C
import hashlib
import struct
import threading

import a_save_runtime_contract as wire
from authoritative_sync import canonical, digest, validate_node, hexid
from checkpoint_fresh_save_binding import LocalWorldObservation
from b_warm_profile_contract import Profile, validate_profile
import b_warm_world as world

SLOTS=((0x12CC4D0,0x3F9B00),(0x12DC620,0x4AA650),(0x12CC9E0,0x3F8140),(0x1297D10,0x1AC3C0))
INLINE=(0x3F8606,0x3F9B16,0x13DC09)


def need(ok,message):
    if not ok:raise ValueError(message)


class NotReady(ValueError):
    """Snapshot was explicitly busy, not an accepted boundary or unknown call."""


@dataclass(frozen=True)
class Observation:
    sequence:int
    pid:int
    birth:int
    year:int
    month:int
    day:int
    force:int
    ruler:int
    profile_sha256:str|None
    sample_sha256:str
    human_no_new_commands:bool=True
    input_exclusion_proven:bool=False
    scheduler_fence_proven:bool=False
    atomic_snapshot:bool=False
    full_world_verified:bool=False
    ready_authorized:bool=False

    @property
    def node(self):
        return dict(year=self.year,month=self.month,day=self.day,phase='PLANNING_BOUNDARY')

    @property
    def coverage(self):
        return dict(input_exclusion_proven=False,scheduler_fence_proven=False,
                    atomic_snapshot=False,full_world_verified=False,ready_authorized=False)


class AObservedBoundary:
    def __init__(self,reader,*,pid,birth,base,root,world_address,cache,force,ruler,
                 nonce,plans,read_birth,runtime_snapshot,no_new_commands):
        need(no_new_commands is True,'Explicit human no-new-command condition required')
        for value,limit in ((pid,2**32),(birth,2**64),(base,2**47),(root,2**47),
                            (world_address,2**47),(cache,2**47),(force,52),(ruler,6000)):
            need(type(value) is int and 0<value<limit,'Invalid pinned identity')
        need(type(nonce) is bytes and len(nonce)==32 and any(nonce),'Exact runtime nonce required')
        need(type(plans) is wire.Plans,'Typed approved runtime Plans required')
        self.plans=wire.decode(wire.Plans,'Plans',nonce,bytes(plans))
        need(not self.plans.header.result and (self.plans.pid,self.plans.birth,self.plans.base)==(pid,birth,base)
             and self.plans.module,'Plans belongs to another installed runtime')
        for p,(slot,original) in zip(self.plans.slots,SLOTS):
            need((p.address,p.original)==(base+slot,base+original) and
                 p.hook>=0x10000 and p.hook!=p.original,'Wrong owned slot plan')
        for p,rva in zip(self.plans.inlines,INLINE):
            need(p.address==base+rva and p.size==5 and bytes(p.after)[0]==0xE8 and
                 bytes(p.after)[:5]!=bytes(p.before)[:5],'Wrong owned inline plan')
        need(callable(read_birth) and callable(runtime_snapshot),'Retained read-only callbacks required')
        self.reader,self.pid,self.birth=reader,pid,birth
        self.base,self.root,self.world,self.cache=base,root,world_address,cache
        self.force,self.ruler,self.nonce=force,ruler,nonce
        self.read_birth,self.runtime_snapshot=read_birth,runtime_snapshot
        self._reader=reader;self._lock=threading.RLock();self.sequence=0;self.records=[];self._last_runtime=None

    def _identity(self):
        need(self.reader is self._reader and self.reader.pid==self.pid and self.read_birth()==self.birth and
             self.reader.memory.base==self.base and self.reader.sha256==world.objects.GAME_SHA256,
             'Pinned process/image changed')

    def _runtime(self):
        self._identity()
        value=self.runtime_snapshot()
        need(type(value) is wire.Snapshot,'Exact typed Runtime Snapshot required')
        s=wire.decode(wire.Snapshot,'Snapshot',self.nonce,bytes(value))
        if s.header.result==10:raise NotReady('Runtime Snapshot is explicitly NotReady')
        need(s.header.result==0,'Runtime Snapshot failed')
        need(all(getattr(s,k)==1 for k in ('prepared','ownerArmed','sourcesArmed','ready','hostInitialized','hostCacheValid')),
             'Runtime has not reached its controlled planning state')
        need(all(getattr(s,k)==0 for k in ('error','stopped','ownerError','ownerStopped','saveLane','saveError',
            'saveActive','ownerActive','gateActive','parentActive','parentError','mailboxStopped','hostLease','hostFrame',
            'productionPermit','allWritersProven','restoreReady')),'Runtime failed, active, stopped or claims unsupported authority')
        need(s.hostThread and s.hostCacheAddress and s.hostCacheSequence%2==0 and s.hostState in (0,3),
             'Host cache is not an idle/completed observation')
        need(s.parentBefore==s.parentAfter==s.parentFinally and s.parentBefore>0,'Parent callback pair is incomplete')
        need(s.mailboxCount<=2 and list(s.mailboxStates)==[5]*s.mailboxCount+[0]*(2-s.mailboxCount),
             'Pending or unknown mailbox request')
        if s.saveStatus==0:
            need(s.saveGeneration==0 and not any(getattr(s,k) for k in
                ('binds','queues','phaseMask','workerJoined','originalReturned','fileVerified')) and s.mailboxCount==0,
                'Idle report contains a prior/pending save')
        else:
            need(s.saveStatus==5 and s.saveGeneration in (1,2) and s.mailboxCount==s.saveGeneration and
                 s.binds==s.queues==s.workerJoined==s.fileVerified==1 and s.phaseMask==31 and s.originalReturned>0,
                 'Prior Save lacks real Complete/Copy/drain evidence')
        for actual,plan in zip(s.counters,self.plans.counters):
            need((actual.startedAddress,actual.activeAddress)==(plan.startedAddress,plan.activeAddress) and
                 actual.startedAddress and actual.activeAddress and actual.active==0,'Foreign or active bridge counters')
        return s

    def _progress(self,a,b):
        need(a.hostThread==b.hostThread and a.hostCacheAddress==b.hostCacheAddress,'Runtime host identity changed')
        need(b.hostCacheSequence>=a.hostCacheSequence and b.parentBefore>=a.parentBefore and
             all(y.started>=x.started for x,y in zip(a.counters,b.counters)),'Runtime history went backwards')

    def _planning(self,node,reads):
        self._identity();m=self.reader.memory;b=self.base
        expected=(node['year'],node['month'],node['day'],self.force,self.ruler)
        context=world.context(self.reader,reads,self.read_birth,expected)
        need((context['root'],context['world'])==(self.root,self.world),'Root/world changed')
        q=lambda p:struct.unpack('<Q',reads.read(p,8))[0]
        u=lambda p:struct.unpack('<I',reads.read(p,4))[0]
        signed=lambda p:struct.unpack('<i',reads.read(p,4))[0]
        need(q(b+0x2025318)==self.cache,'Planning cache changed')
        states=[a for _,a in context['states']]
        for name,address in context['states']:self.reader.require_type(address,name)
        head=reads.read(b+0x19E7310,0x50)
        count,capacity,stack=struct.unpack_from('<3Q',head,0x10)
        queued,qcapacity,queue=struct.unpack_from('<3Q',head,0x30)
        current=struct.unpack_from('<Q',head,0x48)[0]
        need(count==5 and 5<=capacity<=4096 and queued==0 and 0<=qcapacity<=4096 and
             bool(queue)==bool(qcapacity),'Nonempty or inconsistent planning vectors')
        need(list(struct.unpack('<5Q',reads.read(stack,40)))==states,'State stack pointers changed')
        tasks=[q(a+0x50) for a in states]
        need(current==0 and not any(tasks),'Native scheduler task still active')
        toolbar=q(states[4]+0x478);panel=q(states[2]+0x480);keyboard=q(b+0x1FCA0A0)
        need(all(0x10000<=p<2**47 for p in (toolbar,panel,keyboard)),'Invalid planning input pointers')
        pending=dict(user_phase=u(states[4]+0x470),command=signed(toolbar+0x88),
            game_transition=u(states[2]+0x474),load_queued=u(states[2]+0x478),advance=u(states[2]+0x47c),
            panel_advance=u(panel+0x1b0),user_transition=u(states[4]+0x660),mode=u(self.cache+8),
            cache_selection=signed(self.cache+0x3ec),cache_pending=u(self.cache+0x3f0),
            selections=[u(a+0x68) for a in states],targets=[q(states[4]+o) for o in (0x4a8,0x4b0,0x4b8)])
        need(pending['user_phase']==2 and pending['command']==pending['cache_selection']==-1 and pending['mode']==0,
             'Wrong planning phase/cache/menu')
        need(not any(pending[k] for k in ('game_transition','load_queued','advance','panel_advance',
            'user_transition','cache_pending')) and not any(pending['selections']+pending['targets']),
            'Pending command, report, transition or selection')
        report_head=reads.pointer(b+0x1FC98B0);report_count=q(b+0x1FC98B8)
        links=[q(report_head+i*8) for i in range(3)];nil=reads.read(report_head+0x19,1)[0]
        need(report_count==0 and links==[report_head]*3 and nil==1,'Pending report tree')
        report_cursor=struct.unpack('<H',reads.read(self.world+0x165A,2))[0]
        for p in self.plans.slots:need(q(p.address)==p.hook,'Owned native slot no longer installed')
        for p in self.plans.inlines:need(reads.read(p.address,p.size)==bytes(p.after)[:p.size],
                                      'Owned inline source changed')
        # No B-sampler original-slot condition: these exact approved A hooks
        # remain installed throughout this observation.
        return dict(context=context,cache=self.cache,manager=head.hex(),stack=stack,states=states,tasks=tasks,
            toolbar=toolbar,panel=panel,keyboard=keyboard,pending=pending,report_head=report_head,
            report_links=links,report_nil=nil,report_cursor=report_cursor,rng=u(b+0x18EB8B0))

    def _capture(self,node,profile,payload):
        validate_node(node);node=dict(node)
        profile_bytes=bytes(profile) if type(profile) is Profile else None
        if profile is not None:
            need(type(profile) is Profile,'Typed native profile required');validate_profile(profile)
            need((profile.source.force,profile.source.ruler)==(self.force,self.ruler),'Profile source changes A identity')
        before=self._runtime();reads=world.Reads(self.reader.memory.read)
        first=self._planning(node,reads)
        tables=world.payload_pass(self.reader,reads,self.root) if payload else None
        second=self._planning(node,reads)
        again=world.payload_pass(self.reader,reads,self.root) if payload else None
        need(first==second and tables==again,'Complete planning/table samples differ')
        after=self._runtime();self._progress(before,after)
        need((before.saveGeneration,before.saveStatus,before.mailboxCount)==
             (after.saveGeneration,after.saveStatus,after.mailboxCount),'Save changed during observation')
        if self._last_runtime is not None:self._progress(self._last_runtime,before)
        need(profile is None or bytes(profile)==profile_bytes,
             "Profile changed while observing")
        self._last_runtime=after;self.sequence+=1
        evidence=dict(planning=first,runtime_before=wire.values(before),runtime_after=wire.values(after),
                      table_hashes={k:hashlib.sha256(v).hexdigest() for k,v in tables.items()} if tables else None)
        ob=Observation(self.sequence,self.pid,self.birth,node['year'],node['month'],node['day'],self.force,self.ruler,
            hashlib.sha256(bytes(profile)).hexdigest() if profile is not None else None,digest(evidence))
        self.records.append(dict(observation=ob,evidence=evidence))
        return ob,first,tables

    def observe(self,node,profile=None):
        with self._lock:return self._capture(node,profile,False)[0]

    def world_observation(self,node,attachment):
        need(hexid(attachment,32),'Exact A attachment required')
        with self._lock:
            ob,_,payload=self._capture(node,None,True)
            return LocalWorldObservation(attachment,ob.year,ob.month,ob.day,self.force,self.ruler,
                world.CONTRACT,digest(world.shared(node,payload)),True)

    def sample(self,*,scope,epoch,period,profile,receipt_key):
        # Existing world.sample validates every scope/profile/receipt/byte field;
        # bracket its full read with our planning + Runtime observations.
        with self._lock:
            node=world.node(profile);before=self.observe(node,profile)
            value=world.sample(self.reader,scope=scope,epoch=epoch,period=period,profile=profile,side='A',
                               receipt_key=receipt_key,read_birth=self.read_birth)
            after=self.observe(node,profile)
            a=self.records[-2]['evidence']['planning'];b=self.records[-1]['evidence']['planning']
            need(a==b and value['local_context']==a['context'] and
                 before.profile_sha256==after.profile_sha256==value['binding']['profile_sha256'],
                 'Planning/profile changed around complete world sample')
            world.validate_sample(value)
            return value
