"""Owned byte layout; production GameReader/capture_context read every field.

Only RTTI service and birth/attachment are explicit environment doubles. The
business callback writes the owned layout and is NOT the game's reward routine.
"""
import struct
import types
from copy import deepcopy

from reward_observed_context import GameReader,reward,ContextSampler,CheckedPort


class Memory:
    def __init__(self):self.base=0x140000000;self.spans=[]
    def reserve(self,a,n):self.spans.append((a,bytearray(n)))
    def block(self,a,n):
        for b,data in self.spans:
            if b<=a and a+n<=b+len(data):return data,a-b
        raise ValueError('Unmapped owned address '+hex(a))
    def read(self,a,n):data,i=self.block(a,n);return bytes(data[i:i+n])
    def put(self,a,raw):data,i=self.block(a,len(raw));data[i:i+len(raw)]=raw
    def pack(self,a,f,*v):self.put(a,struct.pack(f,*v))


class World:
    def __init__(self,viewer):
        self.memory=m=Memory();b=m.base;self.root=0x200000000;self.world=0x210000000
        m.reserve(b,0x2240000);m.reserve(self.root,0x86000);m.reserve(self.world,0x2000)
        self.types={self.root:'CSan14Data',self.world:'CWorldData'};self.alloc=0x220000000
        self.reader=r=GameReader.__new__(GameReader);r.memory=m;r.pid=12000+viewer;r.sha256=reward.SUPPORTED_SHA256
        def require_type(_,a,n):
            if self.types.get(a)!=n:raise ValueError('Owned RTTI service mismatch')
        r.require_type=types.MethodType(require_type,r)
        self.epoch='e'*32;self.attachment=('a' if viewer==12 else 'b')*32;self.birth=70000+viewer;self.viewer=viewer
        m.pack(b+0x1FCA1E0,'<Q',self.root);m.pack(self.root+0x85130,'<Q',self.world)
        m.pack(self.world+0x34,'<HBB4B',203,8,11,0,0,viewer,0)
        self.states=[]
        for i,name in enumerate(reward.PLANNING_STACK):
            a=self.obj(name,0x800);m.put(a+0x70,name.encode()+b'\0');self.states.append(a)
        array=self.obj('array',40);m.pack(array,'<5Q',*self.states)
        m.pack(b+0x19E7310+0x10,'<Q',5);m.pack(b+0x19E7310+0x20,'<Q',array)
        m.pack(self.states[-1]+0x470,'<I',2);m.pack(b+0x18ECF30,'<I',1)
        self.districts={}
        for i in range(52):
            d=self.obj('CDistrictData',0x80);self.districts[i]=d;m.pack(self.root+0xDE40+i*8,'<Q',d)
        for district,force,ruler in ((11,12,666),(2,2,952)):
            m.pack(self.districts[district]+0x10,'<BBH4B',force,1,ruler,10,0,0,0)
            f=self.obj('CForceData',0x80);m.pack(f+0x10,'<H',ruler);m.pack(self.root+0xDCA0+force*8,'<Q',f)
        dummy=self.obj('CPersonData',0x200);m.pack(self.root+0x737C0,'<Q',dummy)
        army=self.obj('CArmyUnitData',0x200);m.pack(self.root+0x7DF60,'<Q',army)
        self.people={}
        for identity,district,city,rank,loyalty in ((666,11,19,1,100),(97,11,19,4,80),(952,2,13,1,100),(101,2,13,4,70)):
            a=self.obj('CPersonData',0x200);self.people[identity]=a;m.pack(a,'<Q',b+0x129DD00)
            m.pack(a+0x10,'<H',identity);m.put(a+0x12,('P'+str(identity)).encode('utf-16le'))
            m.pack(a+0x118,'<B',district);m.pack(a+0x11A,'<HHB',city,city,rank);m.pack(a+0x120,'<B',loyalty)
            m.pack(self.root+0x148+identity*8,'<Q',a)
        m.pack(b+0x129DD00+0x18,'<Q',b+0x2119F0)
        self.cities={}
        for city,district,gold in ((19,11,83308),(13,2,20804)):
            a=self.obj('CCityData',0x200);self.cities[city]=a;m.pack(a,'<Q',b+0x129FD10)
            m.pack(a+0x10,'<H',city);m.put(a+0x12,('C'+str(city)).encode('utf-16le'))
            m.pack(a+0x30,'<B',district);m.pack(a+0x34,'<III',gold,50000,10000);m.pack(a+0x4E,'<H',city)
            m.pack(self.root+0xDAA8+city*8,'<Q',a)
        m.pack(b+0x129FD10+0x80,'<Q',b+0x209A00);m.pack(b+0x129FD10+0x90,'<Q',b+0x20C2E0)
        heads=self.obj('heads',64);tails=self.obj('tails',64);counts=self.obj('counts',64)
        pool=b+0x201D3A0;m.pack(pool+8,'<Q',1);m.pack(pool+0x10,'<QQ',heads,tails)
        m.pack(pool+0x28,'<Q',counts);m.pack(pool+0x40,'<I',0x14000)
        for slot,(a,vt,values) in enumerate(((self.root+0xF8,0x123F448,list(self.people.values())),
                                            (self.root+0xC8,0x123F3F8,[self.districts[11],self.districts[2]]),
                                            (self.root+0x78,0x123F3B8,list(self.cities.values())))):
            handle=self.obj('handle',8);m.pack(handle,'<I',slot);m.pack(a,'<QQ',b+vt,handle)
            nodes=[self.obj('node',24) for _ in values]
            for i,(node,value) in enumerate(zip(nodes,values)):
                m.pack(node,'<QQQ',value,nodes[i+1] if i+1<len(nodes) else 0,nodes[i-1] if i else 0)
            m.pack(heads+slot*8,'<Q',nodes[0]);m.pack(tails+slot*8,'<Q',nodes[-1]);m.pack(counts+slot*8,'<Q',len(nodes))
        manager=self.obj('task-manager',0x40);m.pack(self.root+0x85128,'<Q',manager)
        m.pack(manager+0x10,'<QQ',b+0x129BB28,0)
        self.calls=0;self.failure=None

    def obj(self,name,size):
        a=self.alloc;self.alloc+=(size+0xff)&~0xff;self.memory.reserve(a,size);self.types[a]=name;return a
    def binding(self):return self.epoch,self.attachment
    def identity(self):return self.reader.pid,self.birth,self.epoch,self.attachment
    def port(self):
        s=ContextSampler(self.reader,pid=self.reader.pid,birth=self.birth,epoch=self.epoch,attachment_id=self.attachment,
            current_binding=self.binding,node=dict(year=203,month=8,day=11),viewer=self.viewer,
            players={12:dict(ruler=666,district=11),2:dict(ruler=952,district=2)},read_birth=lambda:self.birth)
        return CheckedPort(s,self)
    def execute(self,command):
        self.calls+=1;m=self.memory;city=self.cities[command['funding_city_id']]
        district=m.read(city+0x30,1)[0];dp=self.districts[district]
        gold=struct.unpack('<I',m.read(city+0x34,4))[0]
        m.pack(city+0x34,'<I',gold-100*len(command['officer_ids'])+(1 if self.failure=='wrong-cost' else 0))
        m.pack(dp+0x14,'<B',m.read(dp+0x14,1)[0]-1)
        for identity in command['officer_ids']:
            p=self.people[identity];m.pack(p+0x120,'<B',min(100,m.read(p+0x120,1)[0]+4))
            m.pack(p+0x196,'<H',struct.unpack('<H',m.read(p+0x196,2))[0]|2)
        if self.failure=='unselected':m.pack(self.people[666]+0x120,'<B',99)
        if self.failure=='after-write':raise OSError('Owned native result lost after writes')
        return dict(native_returned=True,args_released=True,owned_slot_cleared=True,uncertain=False,error=0)
