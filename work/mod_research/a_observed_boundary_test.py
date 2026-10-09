"""Owned fake RAM plus typed Runtime reports; archive reads are offline only."""
from dataclasses import asdict,FrozenInstanceError
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import a_observed_boundary as observed
import a_save_runtime_contract as wire
import b_warm_world as world
from b_warm_world_test import Reader,configuration

OUTPUT=None
INPUTS={}


class PlanningReader(Reader):
    def require_type(self,address,name):
        if (name,address) in self.states:return
        return super().require_type(address,name)


class Fixture:
    def __init__(self):
        self.reader=PlanningReader('A');self.birth=1001;self.calls=0;self.mutate_runtime=None
        r=self.reader;m=r.memory;b=m.base;self.nonce=b'\x55'*32
        self.cache=0x620000000;self.stack=0x620002000;self.toolbar=0x620004000
        self.panel=0x620006000;self.keyboard=0x620008000;self.report=0x62000A000
        def raw(address,size):m.put(address,bytes(size))
        raw(self.cache,0x3f4);raw(self.toolbar,0x8c);raw(self.panel,0x1f8);raw(self.keyboard,0x258)
        for _,a in r.states:raw(a,0x668)
        self.write(r.states[4][1]+0x478,self.toolbar,'<Q');self.write(r.states[2][1]+0x480,self.panel,'<Q')
        self.write(r.states[4][1]+0x470,2);self.write(self.toolbar+0x88,-1,'<i');self.write(self.cache+0x3ec,-1,'<i')
        m.put(b+0x2025318,struct.pack('<Q',self.cache));m.put(b+0x1FCA0A0,struct.pack('<Q',self.keyboard))
        head=bytearray(0x50);struct.pack_into('<3Q',head,0x10,5,16,self.stack);m.put(b+0x19E7310,head)
        m.put(self.stack,struct.pack('<5Q',*[a for _,a in r.states]))
        m.put(b+0x1FC98B0,struct.pack('<2Q',self.report,0));tree=bytearray(0x20)
        struct.pack_into('<3Q',tree,0,self.report,self.report,self.report);tree[0x19]=1;m.put(self.report,tree)
        m.put(r.world+0x165A,struct.pack('<H',43));m.put(b+0x18EB8B0,struct.pack('<I',123))
        self.plans=wire.envelope(wire.Plans,'Plans',self.nonce)
        self.plans.pid,self.plans.birth,self.plans.base,self.plans.module=r.pid,self.birth,b,0x700000000
        for index,(slot,original) in enumerate(observed.SLOTS):
            p=self.plans.slots[index];p.address=b+slot;p.original=b+original;p.hook=self.plans.module+0x1000+index*0x100
            m.put(p.address,struct.pack('<Q',p.hook))
        for index,rva in enumerate(observed.INLINE):
            p=self.plans.inlines[index];p.address=b+rva;p.size=5;p.relay=self.plans.module+0x5000
            p.before[:]=b'\xe8\x01\x02\x03\x04\0\0';p.after[:]=b'\xe8\x11\x12\x13\x14\0\0'
            m.put(p.address,bytes(p.after)[:p.size])
        for index,p in enumerate(self.plans.counters):p.startedAddress=self.plans.module+0x8000+index*16;p.activeAddress=p.startedAddress+8
        self.runtime=wire.envelope(wire.Snapshot,'Snapshot',self.nonce)
        for k in ('prepared','ownerArmed','sourcesArmed','ready','hostInitialized','hostCacheValid'):setattr(self.runtime,k,1)
        self.runtime.hostThread=77;self.runtime.hostCacheAddress=self.plans.module+0x9000
        self.node=dict(year=203,month=8,day=11,phase='PLANNING_BOUNDARY')
        self.provider=observed.AObservedBoundary(r,pid=r.pid,birth=self.birth,base=b,root=r.root,world_address=r.world,
            cache=self.cache,force=12,ruler=666,nonce=self.nonce,plans=self.plans,read_birth=lambda:self.birth,
            runtime_snapshot=self.snapshot,no_new_commands=True)

    def write(self,address,value,fmt='<I'):
        m=self.reader.memory;data=struct.pack(fmt,value)
        for at,raw in list(m.spans.items()):
            if at<=address and address+len(data)<=at+len(raw):
                value=bytearray(raw);value[address-at:address-at+len(data)]=data;m.put(at,value);return
        m.put(address,data)

    def snapshot(self):
        self.calls+=1;s=wire.Snapshot.from_buffer_copy(bytes(self.runtime))
        s.parentBefore=s.parentAfter=s.parentFinally=self.calls*10;s.hostCacheSequence=self.calls*20
        for i,(c,p) in enumerate(zip(s.counters,self.plans.counters)):
            c.startedAddress=p.startedAddress;c.activeAddress=p.activeAddress;c.started=self.calls*(i+1)
        if self.mutate_runtime:self.mutate_runtime(s)
        return s

    def complete_and_rebuild(self):
        s=self.runtime;s.saveStatus=5;s.saveGeneration=s.mailboxCount=1;s.mailboxStates[0]=5
        s.binds=s.queues=s.workerJoined=s.fileVerified=1;s.phaseMask=31;s.originalReturned=27
        m=self.reader.memory;states=self.reader.states[:]
        for i in (3,4):
            name,old=states[i];new=old+0x900000;m.put(new,m.spans[old]);m.put(old,bytes(len(m.spans[old])));states[i]=(name,new)
        self.reader.states=states;m.put(self.stack,struct.pack('<5Q',*[a for _,a in states]))
        self.write(self.reader.world+0x36,8,'<B');self.write(self.reader.world+0x37,21,'<B')
        self.node={**self.node,'day':21}


class Cases(unittest.TestCase):
    def test_owned_hooks_and_real_typed_reports_observed_not_fenced(self):
        f=Fixture();p,_=configuration();ob=f.provider.observe(f.node,p)
        self.assertEqual(ob.profile_sha256,hashlib.sha256(bytes(p)).hexdigest())
        self.assertEqual(ob.day,11);self.assertEqual(p.before.day,1)
        self.assertEqual(ob.node,f.node);self.assertFalse(any(ob.coverage.values()))
        with self.assertRaises(FrozenInstanceError):ob.sequence=4
        self.assertGreater(f.calls,1)
        self.assertNotEqual(f.plans.slots[0].hook,f.plans.slots[0].original)
        (OUTPUT/'observation.json').write_text(json.dumps(asdict(ob),indent=2)+'\n')

    def test_complete_two_tables_match_B_other_view(self):
        f=Fixture();p,scope=configuration()
        a=f.provider.sample(scope=scope,epoch='3'*32,period=1,profile=p,receipt_key='4'*64)
        b=world.sample(Reader('B',0x1000000000),scope=scope,epoch='3'*32,period=1,profile=p,side='B',receipt_key='5'*64,read_birth=lambda:1201)
        self.assertEqual(world.compare(a,b)['result'],'PARTIAL_MATCH')
        ob=f.provider.world_observation(f.node,'a'*32)
        self.assertEqual(ob.world_sha256,a['partial_sha256'])
        self.assertFalse(a['full_world_verified'] or a['atomic_world_snapshot'])
        (OUTPUT/'partial-comparison.json').write_text(json.dumps(world.compare(a,b),indent=2)+'\n')

    def test_new_user_after_completed_save_is_resampled(self):
        f=Fixture();f.provider.observe(f.node);old=f.reader.states[-1][1]
        f.complete_and_rebuild();ob=f.provider.observe(f.node)
        self.assertEqual(ob.day,21);self.assertNotEqual(f.reader.states[-1][1],old)
        self.assertEqual(f.provider.records[-1]['evidence']['planning']['states'][-1],f.reader.states[-1][1])

    def test_report_queue_pending_command_active_task_and_source_drift_refused(self):
        for mode in ('report','menu','task','hook','inline','mode','queue'):
            with self.subTest(mode=mode):
                f=Fixture();b=f.reader.memory.base
                if mode=='report':f.write(b+0x1FC98B8,1,'<Q')
                if mode=='menu':f.write(f.toolbar+0x88,3,'<i')
                if mode=='task':f.write(f.reader.states[4][1]+0x50,0x20000,'<Q')
                if mode=='hook':f.write(f.plans.slots[0].address,f.plans.slots[0].original,'<Q')
                if mode=='inline':f.reader.memory.put(f.plans.inlines[0].address,b'\x90'*5)
                if mode=='mode':f.write(f.cache+8,1)
                if mode=='queue':f.write(b+0x19E7310+0x30,1,'<Q')
                with self.assertRaises(ValueError):f.provider.observe(f.node)
                self.assertEqual(f.provider.sequence,0)

    def test_busy_foreign_or_failed_runtime_never_observed(self):
        for mode in ('busy','nonce','stopped','ready','active','lease','beforeafter'):
            with self.subTest(mode=mode):
                f=Fixture()
                def change(s):
                    if mode=='busy':s.header.result=10
                    if mode=='nonce':s.nonce[0]^=1
                    if mode=='stopped':s.stopped=1
                    if mode=='ready':s.ready=0
                    if mode=='active':s.counters[1].active=1
                    if mode=='lease':s.hostLease=1
                    if mode=='beforeafter' and f.calls==2:s.ownerError=11
                f.mutate_runtime=change
                with self.assertRaises(ValueError):f.provider.observe(f.node)
                self.assertEqual(f.provider.sequence,0)

    def test_same_name_address_race_and_table_drift_refused(self):
        f=Fixture();f.reader.swap_state=True
        with self.assertRaises(ValueError):f.provider.observe(f.node)
        f=Fixture();address=f.reader.objects['objects'][0];width=len(f.reader.memory.spans[address])
        f.reader.memory.mutate=(address,width,world.TABLES[0][-1][0][0])
        with self.assertRaises(ValueError):f.provider.world_observation(f.node,'a'*32)
        self.assertEqual(f.provider.sequence,0)

    def test_actual_archived_initial_snapshot_accepts_stopped_and_busy_reject(self):
        archive=PRIVATE/'a_native_turn_start_runs/20261009-233736-417328'
        planfile=next(archive.glob('*Plans-response.bin'))
        plan=wire.Plans.from_buffer_copy(planfile.read_bytes());INPUTS[str(planfile)]=hashlib.sha256(planfile.read_bytes()).hexdigest()
        for number,accept in (('016',True),('008',False),('172',False)):
            f=Fixture();sf=archive/(number+'-Snapshot-response.bin');raw=sf.read_bytes();INPUTS[str(sf)]=hashlib.sha256(raw).hexdigest()
            f.reader.pid=plan.pid;f.reader.memory.base=plan.base
            p=observed.AObservedBoundary(f.reader,pid=plan.pid,birth=plan.birth,base=plan.base,root=f.reader.root,
                world_address=f.reader.world,cache=f.cache,force=12,ruler=666,nonce=bytes(plan.nonce),plans=plan,
                read_birth=lambda:plan.birth,runtime_snapshot=lambda:wire.Snapshot.from_buffer_copy(raw),no_new_commands=True)
            if accept:self.assertEqual(p._runtime().hostState,0)
            else:
                with self.assertRaises(ValueError):p._runtime()


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    OUTPUT=PRIVATE/'a_observed_boundary_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    before=pins();stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins()
    stable=all(sources.get(k)==v for k,v in before.items())
    report=dict(result='PASS' if r.wasSuccessful() and r.testsRun==7 and stable else 'FAIL',tests=r.testsRun,
        sources=sources,private_inputs=INPUTS,inputs_unchanged=stable,game_access=False,native_execution=False,
        fake_ram=True,fake_runtime=True,archive_snapshot_decode_only=True,
        failures=[(str(t),detail) for t,detail in r.failures+r.errors])
    report['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(0 if report['result']=='PASS' else 1)
