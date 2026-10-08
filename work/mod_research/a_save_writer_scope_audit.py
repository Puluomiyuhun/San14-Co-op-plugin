"""Bounded archived native writer/scheduler audit; never opens a game process.

All native ranges come from the pinned historical image. OS thread services,
path search, UI services and allocation are named doubles, never permissions.
"""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import struct
import sys

P = Path(__file__).resolve().parent
IMAGE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
BASE, ARENA, STACK, TEB, STOP = 0x140000000, 0x50000000, 0x60010008, 0x70000000, 0x142200000
RANGES = {
    'manager_singleton': (0xF690, 0xF711), 'manager_ctor': (0x509060, 0x509089),
    'top': (0x509640, 0x509675), 'user': (0x3F9B00, 0x3FA0B4),
    'game': (0x3F8140, 0x3F871B), 'scheduler': (0x509FE0, 0x50B690),
    'save': (0x4AA650, 0x4AA6D2), 'save_start': (0x4DA320, 0x4DA38A),
    'save_join': (0x4F7050, 0x4F70A4), 'unit_start': (0x16CB30, 0x16CBF0),
    'unit_worker': (0x16C1A0, 0x16C2B8), 'unit_path': (0x2CD3E0, 0x2CD5C4),
    'unit_serialize_prefix': (0x212F00, 0x2133DC), 'archive_write': (0x3A93E0, 0x3A95C8),
    'effects_update': (0x16C2E0, 0x16C577),
    'save_worker': (0x508CA0,0x508D28), 'save_prepare': (0x2EE740,0x2EE8E4),
    'save_open': (0x2F7A10,0x2F7B50), 'save_serialization_prefix': (0x2F7B50,0x2F7C70),
    'army_dispatch': (0x2E80EC,0x2E810B), 'army_wrapper_prefix': (0x2E1680,0x2E1698),
    'army_loop': (0x2E0DB0,0x2E0E78),
}


def need(ok, why):
    if not ok:
        raise AssertionError(why)


class VM:
    def __init__(self, raw):
        import capstone as cs
        import unicorn as uc
        from unicorn import x86_const as x
        self.x, self.uc, self.d = x, uc, cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_64)
        self.m = uc.Uc(uc.UC_ARCH_X86, uc.UC_MODE_64)
        self.m.mem_map(BASE, 0x2400000); self.m.mem_write(BASE, raw[:0x2400000])
        for a, n in ((ARENA, 0x200000), (STACK-0x10008, 0x20000), (TEB, 0x10000)):
            self.m.mem_map(a, n)
        self.manager, self.vector = BASE+0x19E7310, ARENA+0x1000
        self.states = [ARENA+0x10000+i*0x1000 for i in range(6)]
        self.root, self.world, self.unit = ARENA+0x40000, ARENA+0xD0000, ARENA+0xE0000
        self.cache, self.pool, self.control = ARENA+0x110000, ARENA+0x112000, ARENA+0x113000
        self.unit_manager, self.effects = BASE+0x1A24CF0, BASE+0x1A38A20
        self.table, self.node = ARENA+0x120000, ARENA+0x130000
        self.put(BASE+0x1FCA1E0, self.root); self.put(self.root+0x85130, self.world)
        self.put(self.root+0x7DF60+44*8, self.unit); self.put(self.unit, BASE+0x123E288)
        self.put(self.manager+0x10, 6); self.put(self.manager+0x20, self.vector); self.put(self.manager+0x30, 0)
        for i, s in enumerate(self.states):
            self.put(self.vector+i*8, s); self.put(s+0x50, 0)
        self.put(TEB+0x58, TEB+0x1000); self.put(TEB+0x1000, TEB+0x2000)
        self.put(TEB+0x2010, 0x7fffffff, 4); self.put(BASE+0x203ABC0, 0, 4); self.put(BASE+0x19E7360, 0, 4)
        self.m.reg_write(x.UC_X86_REG_GS_BASE, TEB)
        self.models, self.visits, self.writes = [], [], []
        self.handlers, self.stops, self.pre = {}, set(), {}
        self.allow = set(RANGES)
        self.m.hook_add(uc.UC_HOOK_CODE, self.step)
        self.m.hook_add(uc.UC_HOOK_MEM_WRITE, self.write)

    def put(self, p, v, n=8): self.m.mem_write(p, int(v).to_bytes(n, 'little', signed=v<0))
    def get(self, p, n=8): return int.from_bytes(self.m.mem_read(p, n), 'little')
    def reg(self, name): return self.m.reg_read(getattr(self.x, 'UC_X86_REG_'+name))
    def set(self, name, value): self.m.reg_write(getattr(self.x, 'UC_X86_REG_'+name), value)
    def ret(self, value=0):
        sp=self.reg('RSP'); self.set('RAX',value); self.set('RIP',self.get(sp)); self.set('RSP',sp+8)
    def model(self, rva, label, fn=None, value=0):
        self.handlers[BASE+rva] = (label, fn or (lambda: self.ret(value)))
    def write(self, machine, access, address, size, value, unused):
        if STACK-0x10008 <= address < STACK+0xFFF8: return
        category, origin = ('unit',self.unit) if self.unit<=address<self.unit+0x1000 else ('other', BASE)
        self.writes.append(dict(pc=hex(self.reg('RIP')-BASE),category=category,offset=hex(address-origin),size=size,value=value))
    def step(self, machine, address, size, unused):
        if address==STOP or address in self.stops: machine.emu_stop(); return
        if address in self.pre: self.pre[address]()
        if address in self.handlers:
            label, fn = self.handlers[address]
            self.models.append(dict(label=label,at=hex(address-BASE),caller=hex(self.get(self.reg('RSP'))-BASE)))
            fn(); return
        rva=address-BASE
        need(any(RANGES[n][0]<=rva<RANGES[n][1] for n in self.allow),f'unbounded execution {rva:#x}')
        self.visits.append(rva)
    def run(self, rva, args=(), setup=None, stop=None):
        self.put(STACK,STOP); self.set('RSP',STACK)
        for r,v in zip(('RCX','RDX','R8','R9'),args): self.set(r,v)
        self.stops={BASE+stop} if stop is not None else set()
        if setup: setup()
        self.m.emu_start(BASE+rva, STOP+1,count=100000)
        need(self.reg('RIP') in self.stops or self.reg('RIP')==STOP,'bounded native sequence did not finish')
    def row(self, name, **kw):
        return dict(case=name,result='PASS',native_instruction_count=len(self.visits),modeled_calls=self.models,actual_nonstack_writes=self.writes,**kw)


def top_cases(raw):
    rows=[]
    for count,name in ((5,'user-planning-warm'),(6,'user-covered-by-save-warm'),(0,'empty-manager-warm')):
        v=VM(raw);v.put(v.manager+0x10,count);v.run(0x509640,(v.states[4],))
        need(v.reg('RAX')==int(count==5) and not v.writes and not v.models,'warm top check must only read')
        rows.append(v.row(name,top=bool(v.reg('RAX')),warm_tls_epoch_proved_in_fixture=True))
    v=VM(raw);v.run(0x3F9B00,(v.states[4],))
    need(0xF690 in v.visits and 0x3F9B16 not in v.visits and not v.writes,'actual User must return before upstream cut under Save')
    rows.append(v.row('full-user-not-top-early-return',upstream_cut_reached=False))
    v=VM(raw);v.put(TEB+0x2010,0x80000000,4)
    v.model(0xEF9C3C,'CRT initialized epoch synchronization',lambda:v.ret())
    v.run(0x509640,(v.states[5],));need(v.reg('RAX')==1 and not v.writes,'existing manager stale TLS must not reconstruct')
    rows.append(v.row('existing-manager-stale-tls',constructor_called=False))
    v=VM(raw);v.put(TEB+0x2010,0x80000000,4)
    def cold_header():v.put(BASE+0x19E7360,-1,4);v.ret()
    v.model(0xEF9C3C,'CRT uninitialized header',cold_header);v.model(0xEF9A4C,'CRT register destructor');v.model(0xEF9BDC,'CRT initialization footer')
    v.run(0x509640,(v.states[4],))
    need(0x509060 in v.visits and v.get(v.manager+0x10)==0,'cold ctor must remain classified as mutating lifecycle')
    rows.append(v.row('cold-manager-constructor-negative',not_a_valid_existing_save_start=True))
    return rows


def scheduler_case(raw):
    v=VM(raw);starts=[]
    # Actual fresh pool selection, native callable construction sites, vector
    # walk / wait / cleanup execute. Callable storage and OS tasks are doubles.
    worker=v.pool+8;v.put(worker+0x10,v.control);v.put(worker+0x78,0,4)
    vt=BASE+0x12F2440
    def clone():
        dest=v.reg('RDX');v.m.mem_write(dest,bytes(v.m.mem_read(v.reg('RCX'),0x40)));v.ret(dest)
    def transfer():
        v.m.mem_write(v.reg('RDX'),bytes(v.m.mem_read(v.reg('RCX'),0x40)));v.ret()
    v.put(vt,BASE+0x2210400);v.put(vt+0x20,BASE+0x2210500)
    v.handlers[BASE+0x2210400]=('callable clone storage double',clone)
    v.handlers[BASE+0x2210500]=('callable destruction storage double',lambda:v.ret())
    v.model(0x160F0,'callable transfer storage double',transfer)
    for at in (0x834460,):v.model(at,'completed Root task double',value=1)
    for at in (0x834EF0,):v.model(at,'Root wait double')
    def start():starts.append(v.get(v.manager+0x48));v.ret()
    v.model(0x834B60,'Root start double',start);v.model(0x145B20,'pool service double',value=v.pool)
    # Imported lock calls target fixed private addresses; the call operands stay native.
    for slot in (0x123C328,0x123C0D8):
        target=BASE+0x2210000+slot%0x1000;v.put(BASE+slot,target);v.handlers[target]=('Root lock service double',lambda:v.ret())
    def setup():
        v.set('R15',v.manager);v.set('RBP',STACK+0x300);v.put(STACK+0x300-0x78,0);v.put(STACK+0x38,0)
    v.run(0x50B441,setup=setup,stop=0x50B669)
    need(starts==v.states,'native Save stack must schedule all six states in original order')
    need(v.get(v.pool+0x208,4)==0 and all(v.get(s+0x50)==0 for s in v.states),'native completed task pool cleanup')
    return v.row('native-stack-walk-with-save',states_scheduled=['Root','Motor','Game','Strategy','User','Save'],actual_os_scheduling=False,save_is_not_scheduler_exclusion=True)


def save_case(raw):
    v=VM(raw);state=v.states[5];started=[];joined=[];done=[False]
    v.model(0x8351F0,'clock double',value=123)
    def construct():started.append(dict(worker=hex(v.reg('RDX')-BASE),object=hex(v.reg('RCX')-state)));v.ret()
    v.model(0x833CB0,'Save worker constructor double',construct)
    v.model(0x834B60,'Save thread start double');v.model(0x834460,'Save done observation double',lambda:v.ret(int(done[0])))
    v.model(0x834BC0,'Save join double',lambda:(joined.append(True),v.ret())[1])
    sleep=BASE+0x2210100;v.put(BASE+0x123C0E0,sleep);v.handlers[sleep]=('Sleep double',lambda:v.ret())
    v.put(state+0x470,0,4);phases=[]
    for expected in (1,2,2):v.run(0x4AA650,(state,));phases.append(v.get(state+0x470,4));need(phases[-1]==expected,'native Save start/pending transition')
    done[0]=True
    for expected in (3,4):v.run(0x4AA650,(state,));phases.append(v.get(state+0x470,4));need(phases[-1]==expected,'native Save completion transition')
    need(started==[dict(worker='0x508ca0',object='0x478')] and len(joined)==1,'native Save separate thread/join ordering')
    return v.row('native-save-pending-and-join',phases=phases,native_storage_executed=False)


def path_case(raw, search_ok, through_worker=False):
    v=VM(raw);unit=v.unit;out=ARENA+0x150000
    v.put(unit+0x2A,100,2);v.put(unit+0x48,101,2);v.put(unit+0x1F8,105,2)
    for rva,val,label in ((0x2F2BB0,1,'unit-valid predicate double'),(0x210D40,0,'unit-reservation predicate double'),(0x286950,110,'destination lookup double')):v.model(rva,label,value=val)
    for rva in (0x21980,0x7B60,0x2018F0,0x1FED80,0xEF9F20):v.model(rva,'path-local constructor/destructor/cookie double')
    def search():
        target=v.reg('RCX');v.put(target,out);v.put(target+8,5,4)
        for i,value in enumerate((100,102,104,106,108)):v.put(out+i*4,value,4)
        v.ret(int(search_ok))
    v.model(0x1760E0,'path-search result double',search)
    if through_worker:
        v.put(v.unit_manager+8,ARENA+0x153000);v.put(ARENA+0x153000,3,4)
        v.put(BASE+0x201D3A8,ARENA+0x153800);v.put(BASE+0x201D3B0,v.table);v.put(BASE+0x201D3E0,4,4)
        v.put(BASE+0x201D370,0,4);v.put(v.table+3*8,v.node);v.put(v.node,unit);v.put(v.node+8,0)
        v.put(unit+0x10,1,1);v.model(0x16C50,'finished native working-list clear double')
        v.run(0x16C1A0,(v.unit_manager,))
        need(0x16C238 in v.visits and 0x2CD3E0 in v.visits,'native worker must call the unit writer')
    else:v.run(0x2CD3E0,(unit,1,1,0))
    need(v.get(unit+0x48,2)==(102 if search_ok else 101) and v.get(unit+0x1F8,2)==(108 if search_ok else 0xBD10),'native unit stores differ from path model writes')
    need(any(w['category']=='unit' and w['offset']=='0x1f8' for w in v.writes),'native unit write missing')
    # Run actual serializer branch and buffer writer for +48. Only memcpy is a
    # byte-copy service double; no complete archive/storage is synthesized.
    archive,buffer=ARENA+0x151000,ARENA+0x152000
    v.put(archive+0x20,0,4);v.put(archive+0x30,buffer);v.put(archive+0x38,buffer+64)
    def copy():v.m.mem_write(v.reg('RCX'),bytes(v.m.mem_read(v.reg('RDX'),v.reg('R8'))));v.ret()
    v.model(0xF1AF70,'memcpy service double',copy)
    def setup():v.set('RSI',unit);v.set('RBX',archive)
    v.run(0x2133BD,setup=setup,stop=0x2133DC)
    need(v.get(buffer,2)==v.get(unit+0x48,2) and v.get(archive+0x30)==buffer+2,'actual authoritative field crosses save serializer')
    return v.row(('unit-worker-' if through_worker else '')+'unit-path-and-native-save-field-'+str(int(search_ok)),army48=v.get(unit+0x48,2),army1f8=v.get(unit+0x1F8,2),serialized48=v.get(buffer,2),full_serializer_executed=False)


def game_case(raw):
    v=VM(raw);game=v.states[2];starts=[]
    v.put(BASE+0x2025318,v.cache);v.put(v.cache+8,1,4)
    dummy=ARENA+0x157000;ui=ARENA+0x158000;uvt=ARENA+0x159000
    v.put(BASE+0x201D4C8,dummy);v.put(dummy+0x98,0)
    v.put(ui,uvt);v.put(uvt+0x18,BASE+0x2210300)
    v.handlers[BASE+0x2210300]=('covered global UI service double',lambda:v.ret())
    for at,val,label in ((0x1C1A70,0,'special UI absent'),(0xB11E0,v.unit_manager,'unit-list singleton lookup'),
        (0x194A90,ui,'UI singleton lookup'),(0x173F0,dummy,'cursor lookup'),(0x5086A0,dummy,'save/menu service lookup'),
        (0x15FAA0,v.effects,'CTacticsEffectManager lookup'),(0x509460,0,'named state absent'),
        (0x3ECFD0,dummy,'scene effect lookup'),(0x3ECEB0,dummy,'scene effect lookup')):
        v.model(at,label+' double',value=val)
    for at in (0x3AD580,0x8271A0,0x4E8C90,0x1786B0,0x178FE0,0x177E60):v.model(at,'unresolved peripheral Game callee double')
    v.model(0x3FA820,'covered Game panel service double')
    v.put(v.effects+0x38,0)
    v.put(v.unit_manager+0x90,0,4);v.put(v.unit_manager+0x18,ARENA+0x154000);v.put(ARENA+0x154000,3,4)
    v.put(BASE+0x201D3C8,v.table);v.put(v.table+3*8,1)
    v.model(0x16BB70,'pending-to-working queue copy double')
    def construct():need(v.reg('RDX')==BASE+0x16C2C0,'native Game starts the army worker');v.ret()
    v.model(0x833CB0,'unit worker constructor double',construct)
    v.model(0x834B60,'unit worker start double',lambda:(starts.append(v.reg('RCX')),v.ret())[1])
    # This is a fixture pending Save phase. It does not fabricate native worker
    # completion or claim real concurrency; the archived Game body sees Save top.
    v.put(v.states[5]+0x470,2,4);v.run(0x3F8140,(game,0,0,0))
    need(0x3F8544 in v.visits and 0x16CB30 in v.visits and starts==[v.unit_manager+0x20], 'Game below Save still starts native army writer worker')
    need(v.get(v.states[5]+0x470,4)==2 and v.get(v.unit_manager+0x90,4)==1,'native worker active publication with Save pending')
    return v.row('full-native-game-under-pending-save-starts-army-worker',native_game_entry=True,native_top_predicate=True,native_worker_lifecycle=True,actual_os_thread_started=False)


def unit_lifecycle(raw, mode):
    v=VM(raw);m=v.unit_manager;events=[]
    v.put(m+0x90,int(mode!='start'),4);v.put(m+0x18,ARENA+0x154000);v.put(ARENA+0x154000,3,4)
    v.put(BASE+0x201D3C8,v.table);v.put(v.table+3*8,int(mode=='start'))
    v.model(0x834460,'unit worker done double',lambda:(events.append('done'),v.ret(int(mode=='joined')))[1])
    v.model(0x834BC0,'unit worker join double',lambda:(events.append('join'),v.ret())[1])
    v.model(0x16BB70,'pending-to-working queue copy double',lambda:(events.append('queue-copy'),v.ret())[1])
    def construct():events.append('construct');need(v.reg('RDX')==BASE+0x16C2C0,'actual unit worker target');v.ret()
    v.model(0x833CB0,'unit worker constructor double',construct)
    v.model(0x834B60,'unit worker start double',lambda:(events.append('start'),v.ret())[1])
    v.run(0x16CB30,(m,))
    expected={'start':['queue-copy','construct','start'],'pending':['done'],'joined':['done','join']}[mode]
    need(events==expected and v.get(m+0x90,4)==int(mode!='joined'),'native unit worker lifecycle')
    return v.row('native-unit-worker-'+mode,events=events,save_top_preserved=v.get(v.vector+40)==v.states[5],active=v.get(m+0x90,4))


def provenance(raw):
    old=0x7ff749440000
    def rtti(vt):
        col=int.from_bytes(raw[vt-8:vt],'little')-old
        td=int.from_bytes(raw[col+12:col+16],'little')
        return raw[td+16:td+180].split(b'\0')[0].decode('ascii')
    types={hex(p):rtti(p) for p in (0x123E200,0x123E288,0x128F960)}
    need('CArmyUnitData' in types['0x123e200'] and 'CArmyUnitData' in types['0x123e288'] and 'CTacticsEffectManager' in types['0x128f960'],'archived object type provenance')
    # Targeted direct-call candidates only. Never claims indirect caller closure.
    callers={}
    text=raw[0x1000:0x1230000]
    for target in (0x16CB30,0x16C1A0,0x2CD3E0):
        hits=[];cursor=0
        while True:
            i=text.find(b'\xe8',cursor)
            if i<0 or i+5>len(text):break
            cursor=i+1;site=i+0x1000
            if site+5+int.from_bytes(text[i+1:i+5],'little',signed=True)==target:hits.append(hex(site))
        callers[hex(target)]=hits
    return dict(case='object-provenance-and-direct-call-candidates',result='PASS',rtti=types,direct_call_byte_candidates=callers,indirect_call_closure=False,
        classifications={'16c2e0':'CTacticsEffectManager node countdown; no business-field proof in this bounded audit; do not add global gate based only on these writes',
        '16cb30':'ptr_list<CArmyUnitData> background worker start/poll/join',
        '2cd3e0':'actual army+48 and +1f8 writes; +48 is passed by native CArmyUnitData serializer into actual archive-buffer writer'})


def lock_review(raw):
    import capstone as cs
    d=cs.Cs(cs.CS_ARCH_X86,cs.CS_MODE_64)
    anchors={0x508CE4:'call 0x2ee740',0x2EE866:'call 0x2f7a10',
        0x2EE86D:'lea rdx, [rsi + 0x85170]',0x2EE879:'call 0x3a50d0',
        0x2EE89C:'call 0x3a5680',0x2F7B38:'call 0x2f7b50',0x2F7C28:'call 0x2e7d30',
        0x2E80EC:'mov r9, qword ptr [rip + 0x1ce20ed]',0x2E80F9:'add r9, 0x7df60',
        0x2E8106:'call 0x2e1680',0x2E1693:'call 0x2e0db0',
        0x2E0E20:'mov rcx, qword ptr [rdi]',0x2E0E29:'call qword ptr [rax + 0x28]'}
    checked=[]
    for address,want in anchors.items():
        i=next(d.disasm(raw[address:address+15],address));text=i.mnemonic+' '+i.op_str
        need(text==want,'native save/lock anchor mismatch '+hex(address));checked.append(dict(at=hex(address),instruction=text))
    return dict(case='bounded-save-lock-and-live-army-source-review',result='PASS',anchors=checked,
        established=['The root+85170 lock in 2EE740 is acquired after 2F7A10 has returned; this particular lock section clears the root error string, so it does not enclose the observed serialization call.',
            '2E80EC reads the global root and passes root+7DF60; the normal write loop 2E0E20 dereferences each live army pointer and calls its virtual+28 method.',
            'No new lock claim or drain was implemented by this audit.'],
        unresolved=['Other save preparation, serialization descendants, native queue producers and lifecycle may provide existing coordination; it is not exhaustively disproved.',
            'Shared field access plus asynchronous start/join establishes the need to verify native coordination, not actual overlapping writes or corrupted native saves.',
            'Prefer proving and reusing native save serialization or queue-drain ownership before adding a new gate.'])


def main():
    private=Path(os.environ['SAN14_PRIVATE_FIXTURE_ROOT']).resolve();sys.path.insert(0,str(private/'python_deps'))
    run=P/'a_save_writer_scope_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    source=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result=dict(schema='san14.a-save-writer-scope.v1',result='FAIL',game_access=False,production_permit=False,full_writer_exclusion=False,cases=[],source_sha256=source)
    try:
        raw=(private/'game-runtime-image.bin').read_bytes();need(hashlib.sha256(raw).hexdigest()==IMAGE_SHA,'fixed private archive identity')
        result['archive_sha256']=IMAGE_SHA
        result['native_ranges']={k:dict(begin=hex(a),end=hex(z),sha256=hashlib.sha256(raw[a:z]).hexdigest()) for k,(a,z) in RANGES.items()}
        result['cases']+=top_cases(raw)
        result['cases'].append(scheduler_case(raw))
        result['cases'].append(save_case(raw))
        for ok in (True,False):result['cases'].append(path_case(raw,ok))
        result['cases'].append(path_case(raw,True,True))
        for mode in ('start','pending','joined'):result['cases'].append(unit_lifecycle(raw,mode))
        result['cases'].append(game_case(raw))
        result['cases'].append(provenance(raw))
        result['cases'].append(lock_review(raw))
        need(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==source,'source changed while running')
        need(hashlib.sha256((private/'game-runtime-image.bin').read_bytes()).hexdigest()==IMAGE_SHA,'private archive changed while running')
        result['source_unchanged']=True;result['archive_unchanged']=True;result['result']='PASS'
    except Exception as exc:result['error']=repr(exc);raise
    finally:
        (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(result=result['result'],cases=len(result['cases']),path=str(run/'result.json'))))


if __name__=='__main__':main()
