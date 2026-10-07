"""Read-only capture plus x64 emulation. No native game calls or game writes.

All CPU stores, allocator activity and identity changes occur in Unicorn's
private memory. Unknown external execution and missing replay pages fail.
This is a research harness, not an injectable multiplayer adapter.
"""
from pathlib import Path
import sys, json, struct, hashlib, time, zipfile, collections, argparse
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'python_deps'),str(HERE.parents[1]/'outputs'/'san14-link')]
import unicorn as un
from unicorn.x86_const import *
import pefile
from game_reader import GameReader
from economy_reader import PLANNING

PAGE=4096
STACK=0x600000000000
STACK_SIZE=0x200000
HEAP=STACK+0x10000000
HEAP_SIZE=0x1000000
STOP=STACK+0x20000000
SCRATCH=STACK+0x30000000
REG_ARGS=[UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9]
LOCK_IMPORTS=('EnterCriticalSection','LeaveCriticalSection','AcquireSRWLockExclusive','ReleaseSRWLockExclusive')
POOL_CODE=((0x17040,0x171a5),(0x172d0,0x173ea),(0x16c50,0x16d0b),(0x16d10,0x16e1a))

class Capture:
    def __init__(self,reader=None,path=None):
        self.reader=reader;self.pages={};self.used={}
        if path:
            with zipfile.ZipFile(path) as z:
                self.meta=json.loads(z.read('metadata.json'))
                for name in z.namelist():
                    if name.startswith('pages/'):
                        self.pages[int(name[6:],16)]=z.read(name)
        else:
            m=reader.memory
            before=reader.snapshot()
            if before['state_stack']!=PLANNING:raise RuntimeError('Requires idle planning map')
            self.meta={'schema':'san14.economy-shadow-capture.v1','base':m.base,'image_size':m.image_size,
                       'snapshot':before,'exe_sha256':reader.sha256,'imports':{},'sections':m.sections}
            pe=pefile.PE(str(m.path))
            for desc in pe.DIRECTORY_ENTRY_IMPORT:
                for item in desc.imports:
                    addr=m.base+item.address-pe.OPTIONAL_HEADER.ImageBase
                    dest=struct.unpack('<Q',self.read(addr,8))[0]
                    name=(item.name.decode() if item.name else '#'+str(item.ordinal))
                    self.meta['imports'][str(dest)]=desc.dll.decode()+'!'+name
            self.meta['pool_captures']=[]
            for rva in (0x201d3a0,0x19e1bf0):self.prefetch_pool(rva)
    def prefetch_pool(self,rva):
        """Take two identical complete pool copies, before any emulation.

        Captured node allocator state is immutable in the shadow even though
        the real UI continues borrowing/freeing nodes after this read.
        """
        m=self.reader.memory;addr=self.meta['base']+rva
        def read_many(a,n):
            return b''.join(m.read(p,min(0x300000,a+n-p)) for p in range(a,a+n,0x300000))
        for attempt in range(30):
            header=m.read(addr,0x128)
            q=lambda o:struct.unpack_from('<Q',header,o)[0]
            cap=struct.unpack_from('<I',header,0x40)[0];nodes=q(0x38)
            if not 0<cap<=0x14000 or not 0<nodes<=0x40000:raise RuntimeError('Unsupported pool layout')
            ranges=[(q(8),nodes*24),(q(0x10),cap*8),(q(0x18),cap*8),(q(0x28),cap*8),(q(0x50),cap*24)]
            spans=[(a&-PAGE,((a+n+PAGE-1)&-PAGE)-(a&-PAGE)) for a,n in ranges]
            first=[read_many(a,n) for a,n in spans]
            second=[read_many(a,n) for a,n in spans]
            after=m.read(addr,0x128)
            # Only the pool payload must be identical; surrounding allocation
            # headers on shared pages are not part of this atomicity check.
            same=header==after and all(x[a-p:a-p+n]==y[a-p:a-p+n] for (a,n),(p,_),x,y in zip(ranges,spans,first,second))
            if same:break
        else:raise RuntimeError('Could not capture a stable complete pool')
        for (p,n),data in zip(spans,second):
            for o in range(0,n,PAGE):self.pages[p+o]=data[o:o+PAGE]
        p=addr&-PAGE;page=bytearray(self.page(p));page[addr-p:addr-p+len(header)]=header;self.pages[p]=bytes(page)
        self.meta['pool_captures'].append({'rva':hex(rva),'capacity':cap,'nodes':nodes,'attempts':attempt+1,
             'two_equal_copies':True,'ranges':ranges,'header_sha256':hashlib.sha256(header).hexdigest()})
    def page(self,p):
        if p not in self.pages:
            if self.reader is None:raise RuntimeError(f'Missing replay page {p:#x}')
            try:self.pages[p]=self.reader.memory.read(p,PAGE)
            except OSError as e:raise RuntimeError(f'Unreadable source page {p:#x}: {e}') from e
        return self.pages[p]
    def mark(self,a,n,dirty=None,kind=1):
        while n:
            p=a&-PAGE;o=a-p;s=min(n,PAGE-o)
            if p in self.pages:
                mask=self.used.setdefault(p,bytearray(PAGE))
                if (dirty is None or p not in dirty) and kind==1:mask[o:o+s]=b'\1'*s
                else:
                    d=dirty.get(p) if dirty else None
                    for i in range(o,o+s):
                        if d is None or not d[i]:mask[i]|=kind
            a+=s;n-=s
    def read(self,a,n):
        data=bytearray();start=a;length=n
        while n:
            p=a&-PAGE;o=a-p;s=min(n,PAGE-o)
            data+=self.page(p)[o:o+s];a+=s;n-=s
        self.mark(start,length)
        return bytes(data)
    def q(self,a):return struct.unpack('<Q',self.read(a,8))[0]
    def verify(self):
        if not self.reader:return {'result':'OFFLINE_REPLAY','pages':len(self.pages)}
        changed=[];pool_changed=[]
        pool_ranges=[]
        for pool in self.meta.get('pool_captures',[]):
            pool_ranges+=pool['ranges']+[(self.meta['base']+int(pool['rva'],16),0x128)]
        for p,mask in self.used.items():
            current=self.reader.memory.read(p,PAGE);old=self.pages[p]
            for i in range(PAGE):
                if not mask[i] or current[i]==old[i]:continue
                a=p+i
                if mask[i]==2 and any(start<=a<start+n for start,n in pool_ranges):pool_changed.append(hex(a))
                else:changed.append(hex(a))
        after=self.reader.snapshot()
        result={'result':'STABLE_READ_DEPENDENCIES' if not changed and after==self.meta['snapshot'] else 'CHANGED',
                'changed_bytes':len(changed),'first_changed':changed[:32],
                'allocator_only_changed_bytes':len(pool_changed),'allocator_only_changed_addresses':pool_changed,
                'allocator_classification':'Read before shadow write only by audited pool allocator instruction ranges; no economic caller reads these initial bytes',
                'pages':len(self.pages),'dependency_bytes':sum(sum(bool(v) for v in m) for m in self.used.values()),
                'snapshot_after':after,'atomic_snapshot':False}
        self.meta['verification']=result
        if result['result']=='CHANGED':raise RuntimeError('Source changed: '+json.dumps(result,ensure_ascii=False))
        return result
    def save(self,path):
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('metadata.json',json.dumps(self.meta,ensure_ascii=False,indent=2))
            for p,data in sorted(self.pages.items()):z.writestr(f'pages/{p:x}',data)
            for p,data in sorted(self.used.items()):z.writestr(f'reads/{p:x}',data)

class Shadow:
    def __init__(self,source,adapt=False):
        self.source=source;self.base=source.meta['base'];self.adapt=adapt
        self.uc=un.Uc(un.UC_ARCH_X86,un.UC_MODE_64)
        self.mapped=set();self.dirty={};self.allocs={};self.cursor=HEAP;self.events=collections.Counter()
        self.instructions=0;self.blocks=0;self.last=collections.deque(maxlen=24);self.error=None;self.seen_blocks=set();self.current_read_kind=1
        self.entry_counts=collections.Counter();self.executed=set();self.settings=collections.Counter();self.components=[]
        self.uc.mem_map(STACK,STACK_SIZE);self.uc.mem_map(HEAP,HEAP_SIZE)
        self.uc.mem_map(STOP,PAGE);self.uc.mem_map(SCRATCH,0x10000)
        self.uc.mem_write(STOP,b'\xcc')
        # Put a terminating instruction at each allowed external trampoline.
        # Otherwise Unicorn's decoder can fetch beyond a zero-filled page
        # before the code hook has a chance to intercept the import entry.
        for addr,name in source.meta['imports'].items():
            if name.split('!')[-1] in LOCK_IMPORTS+('GetCurrentThreadId',):
                a=int(addr);p=a&-PAGE
                if p not in self.mapped:self.uc.mem_map(p,PAGE);self.mapped.add(p)
                self.uc.mem_write(a,b'\xc3')
        self.uc.reg_write(UC_X86_REG_MXCSR,0x1f80)
        self.uc.hook_add(un.UC_HOOK_MEM_UNMAPPED,self._unmapped)
        self.uc.hook_add(un.UC_HOOK_MEM_READ|un.UC_HOOK_MEM_WRITE,self._memory)
        self.uc.hook_add(un.UC_HOOK_BLOCK,self._block)
        entries=(0x28df03,0x28db37,0x28de2e,0x28debc,0x28da67,0x28daf0,0xef9eb0,0x176160,0x176185,0x39c260,0x3a5820,0x3a58b0,0x2110b0,0x20d3f0,0x284a20,0x28db70,0x28d750,0x39c7d0)
        for rva in entries:self.uc.hook_add(un.UC_HOOK_CODE,self._code,begin=self.base+rva,end=self.base+rva)
        for addr,name in source.meta['imports'].items():
            if name.split('!')[-1] in LOCK_IMPORTS+('GetCurrentThreadId',):
                self.uc.hook_add(un.UC_HOOK_CODE,self._code,begin=int(addr),end=int(addr))
        self.root=source.q(self.base+0x1fca1e0);self.world=source.q(self.root+0x85130)
    def _virtual(self,a):return STACK<=a<STACK+STACK_SIZE or HEAP<=a<HEAP+HEAP_SIZE or STOP<=a<STOP+PAGE or SCRATCH<=a<SCRATCH+0x10000
    def ensure(self,a,n):
        for p in range(a&-PAGE,((a+n-1)&-PAGE)+PAGE,PAGE):
            if not self._virtual(p) and p not in self.mapped:
                data=self.source.page(p);self.uc.mem_map(p,PAGE);self.uc.mem_write(p,data);self.mapped.add(p)
    def read(self,a,n):
        self.ensure(a,n);self.source.mark(a,n,self.dirty)
        return bytes(self.uc.mem_read(a,n))
    def q(self,a):return struct.unpack('<Q',self.read(a,8))[0]
    def write(self,a,data):
        self.ensure(a,len(data));self._mark_dirty(a,len(data));self.uc.mem_write(a,data)
    def _mark_dirty(self,a,n):
        while n:
            p=a&-PAGE;o=a-p;s=min(n,PAGE-o)
            if p in self.mapped:self.dirty.setdefault(p,bytearray(PAGE))[o:o+s]=b'\1'*s
            a+=s;n-=s
    def _fail(self,message):
        self.error=message;self.uc.emu_stop()
    def _unmapped(self,uc,access,a,n,value,unused):
        try:
            if access==un.UC_MEM_FETCH_UNMAPPED and not self.base<=a<self.base+self.source.meta['image_size']:
                name=self.source.meta['imports'].get(str(a))
                if name and name.split('!')[-1] in LOCK_IMPORTS+('GetCurrentThreadId',):
                    p=a&-PAGE
                    if p not in self.mapped:uc.mem_map(p,PAGE);self.mapped.add(p)
                    return True
                raise RuntimeError(f'Unknown external execution {a:#x} {name}')
            self.ensure(a,n)
            if access==un.UC_MEM_WRITE_UNMAPPED:self._mark_dirty(a,n)
            if access==un.UC_MEM_READ_UNMAPPED:self.source.mark(a,n,self.dirty,self._read_kind())
            return True
        except Exception as e:self._fail(str(e));return False
    def _memory(self,uc,access,a,n,value,unused):
        if access==un.UC_MEM_WRITE:self._mark_dirty(a,n)
        else:self.source.mark(a,n,self.dirty,self._read_kind())
    def _read_kind(self):
        return self.current_read_kind
    def ret(self,value=None):
        sp=self.uc.reg_read(UC_X86_REG_RSP);target=self.q(sp)
        if value is not None:self.uc.reg_write(UC_X86_REG_RAX,value&0xffffffffffffffff)
        self.uc.reg_write(UC_X86_REG_RSP,sp+8);self.uc.reg_write(UC_X86_REG_RIP,target)
    def _block(self,uc,a,n,unused):
        self.blocks+=1;self.last.append(a-self.base)
        rva=a-self.base
        self.current_read_kind=2 if any(lo<=rva and rva+n<=hi for lo,hi in POOL_CODE) else 1
        if not self.base<=a<self.base+self.source.meta['image_size']:
            name=self.source.meta['imports'].get(str(a),'UNKNOWN')
            if name.split('!')[-1] not in LOCK_IMPORTS+('GetCurrentThreadId',):self._fail(f'Unknown block {a:#x} {name}')
            return
        if (a,n) not in self.seen_blocks:
            self.source.mark(a,n,self.dirty);self.seen_blocks.add((a,n))
    def _code(self,uc,a,n,unused):
        self.instructions+=1;self.last.append(a-self.base)
        try:
            if a==STOP:uc.emu_stop();return
            rva=a-self.base
            if not 0<=rva<self.source.meta['image_size']:
                name=self.source.meta['imports'].get(str(a),'UNKNOWN')
                if name.split('!')[-1] in LOCK_IMPORTS:
                    self.events['single_thread_lock:'+name]+=1;self.ret();return
                if name.split('!')[-1]=='GetCurrentThreadId':
                    self.events['synthetic_thread_id']+=1;self.ret(0x70000001);return
                raise RuntimeError(f'Unknown external {a:#x} {name}')
            self.source.mark(a,n,self.dirty);self.executed.add(rva)
            if rva in (0x28de2e,0x28debc,0x28da67,0x28daf0):
                self.settings[f'{rva:x}:{uc.reg_read(UC_X86_REG_EAX)}']+=1
            if rva in (0x28df03,0x28db37):
                area=uc.reg_read(UC_X86_REG_R14);first=self.q(self.root+0x6c860)
                identity=(area-first)//0x98
                if not 0<=identity<501 or self.q(self.root+0x6c860+identity*8)!=area:raise RuntimeError('Area result identity mismatch')
                value=struct.unpack('<i',struct.pack('<I',uc.reg_read(UC_X86_REG_EAX)))[0]
                self.components.append({'area_id':identity,'city_id':self.read(area+0x35,1)[0],
                                        'component':0 if rva==0x28df03 else 1,'result':value})
            if rva==0xef9eb0:
                if uc.reg_read(UC_X86_REG_RSP)-uc.reg_read(UC_X86_REG_RAX)<STACK:raise RuntimeError('Shadow stack overflow')
                self.events['precommitted_stack_probe']+=1;self.ret();return
            if rva in (0x176160,0x176185):
                if self.read(a,2)!=b'\xf3\xaa':raise RuntimeError('REP STOSB anchor mismatch')
                count=uc.reg_read(UC_X86_REG_RCX);dest=uc.reg_read(UC_X86_REG_RDI)
                if count>0x200000 or uc.reg_read(UC_X86_REG_EFLAGS)&0x400:raise RuntimeError('Unexpected REP state')
                if count:self.write(dest,bytes([uc.reg_read(UC_X86_REG_RAX)&255])*count)
                uc.reg_write(UC_X86_REG_RDI,dest+count);uc.reg_write(UC_X86_REG_RCX,0)
                uc.reg_write(UC_X86_REG_RIP,a+2);self.events['accelerated_rep_stosb']+=1;return
            if rva==0x39c260:
                # This accessor's hot path returns the already constructed
                # settings singleton. Do not emulate TLS static initialization.
                guard=struct.unpack('<i',self.read(self.base+0x1fd0c5c,4))[0]
                if guard in (0,-1):raise RuntimeError('Settings singleton not initialized')
                self.events['initialized_settings_singleton']+=1
                self.ret(self.base+0x18eb600);return
            # Only audited allocation wrappers are substituted; all economic
            # arithmetic, trait/rank queries and table traversal remain native.
            if rva==0x3a5820:
                size=uc.reg_read(UC_X86_REG_RCX)
                if not 0<size<=0x100000:raise RuntimeError('Unexpected allocation size')
                p=self.cursor;self.cursor+=(size+15)&-16
                if self.cursor>HEAP+HEAP_SIZE:raise RuntimeError('Shadow heap exhausted')
                self.allocs[p]=size;uc.mem_write(p,b'\xcd'*size)
                self.events['private_alloc']+=1;self.ret(p);return
            if rva==0x3a58b0:
                p=uc.reg_read(UC_X86_REG_RCX)
                if p and p not in self.allocs:raise RuntimeError(f'Free of non-shadow allocation {p:#x}')
                if p:del self.allocs[p]
                self.events['private_free']+=1;self.ret();return
            if rva in (0x2110b0,0x20d3f0,0x284a20,0x28db70,0x28d750,0x39c7d0):
                self.entry_counts[hex(rva)]+=1
            if rva==0x2110b0 and self.adapt:
                caller=self.q(uc.reg_read(UC_X86_REG_RSP))-self.base
                if caller in (0x28de76,0x28daaa):
                    force=uc.reg_read(UC_X86_REG_RCX)
                    # Use actual force table membership, not an inferred stride.
                    matches=[i for i in range(1,52) if self.q(self.root+0xdca0+i*8)==force]
                    if len(matches)!=1:raise RuntimeError('Unknown economic subject force')
                    self.events['adapted_human_selector']+=1;self.ret(int(matches[0] in (12,2)));return
        except Exception as e:self._fail(str(e))
    def call(self,rva,*args):
        self.error=None;sp=STACK+STACK_SIZE-0x108
        self.uc.mem_write(sp,b'\0'*0x100);self.uc.mem_write(sp,struct.pack('<Q',STOP))
        self.uc.reg_write(UC_X86_REG_RSP,sp)
        for reg,value in zip(REG_ARGS,list(args[:4])+[0]*4):self.uc.reg_write(reg,value)
        for i,v in enumerate(args[4:]):self.uc.mem_write(sp+0x28+8*i,struct.pack('<Q',v))
        try:self.uc.emu_start(self.base+rva,STOP,timeout=120_000_000,count=40_000_000)
        except un.UcError as e:raise RuntimeError(self.error or str(e)) from e
        if self.error:raise RuntimeError(self.error)
        if self.uc.reg_read(UC_X86_REG_RIP)!=STOP:raise RuntimeError('Emulation budget exhausted')
        return self.uc.reg_read(UC_X86_REG_RAX)
    def identity(self,force):
        fp=self.q(self.root+0xdca0+force*8);ruler=struct.unpack('<H',self.read(fp+0x10,2))[0]
        person=self.q(self.root+0x148+ruler*8)
        self.call(0x2fc850,person)
        actual=self.read(self.world+0x3a,1)[0]
        if actual!=force:raise RuntimeError('Shadow native identity initialization failed')
    def city(self,city_id):
        p=self.q(self.root+0xdaa8+city_id*8);values={}
        for mode in (1,0):
            for kind,rva in [('cost',0x20d3b0),('income',0x20b290)]:
                self.uc.mem_write(SCRATCH,b'\0'*0x1000)
                self.call(rva,p,mode,SCRATCH,0)
                values[f'{kind}_{mode}']=list(struct.unpack('<2i',self.read(SCRATCH,8)))
        values['derived']=[2*(values['income_0'][i]-values['cost_0'][i])+values['income_1'][i]-values['cost_1'][i] for i in (0,1)]
        values['stored']=list(struct.unpack('<2i',self.read(p+0xa0,8)))
        return values

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--replay',type=Path);ap.add_argument('--capture',type=Path)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--cities',default='13')
    ap.add_argument('--viewers',default='12');ap.add_argument('--adapt',action='store_true');args=ap.parse_args()
    reader=None;source=None;report={'schema':'san14.economy-shadow-result.v1','result':'INCOMPLETE',
        'game_writes':False,'native_game_calls':False,'emulator':'unicorn '+un.__version__,'adapted':args.adapt,'runs':[]}
    try:
        if not args.replay:reader=GameReader()
        source=Capture(reader,args.replay)
        for viewer in map(int,args.viewers.split(',')):
            shadow=Shadow(source,args.adapt);row={'viewer':viewer,'cities':{}};report['runs'].append(row)
            try:
                shadow.identity(viewer)
                for city in map(int,args.cities.split(',')):
                    row['cities'][str(city)]=shadow.city(city)
                    print(json.dumps({'viewer':viewer,'city':city,'value':row['cities'][str(city)],'blocks':shadow.blocks}),flush=True)
            finally:
                row.update(hooked_entries=shadow.instructions,blocks=shadow.blocks,events=dict(shadow.events),entry_counts=dict(shadow.entry_counts),
                           settings_query_results=dict(shadow.settings),area_component_results=shadow.components,
                           last_rvas=[hex(x) for x in shadow.last],live_shadow_allocations=len(shadow.allocs))
        report['source_verification']=source.verify();report['result']='COMPLETED_SHADOW_EXECUTION'
    except Exception as e:
        report['error']=repr(e)
        if source and reader:
            try:report['source_verification']=source.verify()
            except Exception as ve:report['verification_error']=repr(ve)
    finally:
        if source and args.capture:source.save(args.capture)
        if reader:reader.close()
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'result':report['result'],'error':report.get('error'),'output':str(args.output)},ensure_ascii=False))
    return 0 if report['result']=='COMPLETED_SHADOW_EXECUTION' else 1

if __name__=='__main__':sys.exit(main())
