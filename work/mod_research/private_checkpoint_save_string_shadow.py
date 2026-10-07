"""Captured binder/cleanup instructions with retained heap strings; offline only."""
from pathlib import Path
from datetime import datetime
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parent;sys.path[:0]=[str(ROOT/'python_deps'),str(ROOT)];sys.argv=sys.argv[:1]
import disasm_chained as d
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *
BASE=0x7ff749440000;MEM=0x300000000;STOP=MEM+0x8000
assert hashlib.sha256(d.image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
q=lambda v:struct.pack('<Q',v)
def sso(text):
    value=text.encode();assert len(value)<=15
    return value.ljust(16,b'\0')+q(len(value))+q(15)
def execute(u,start,stop):
    seen=[]
    def hook(uc,address,size,data):
        if address==stop:uc.emu_stop();return
        assert BASE<=address<BASE+len(d.image),hex(address);seen.append(address-BASE)
    handle=u.hook_add(UC_HOOK_CODE,hook);u.emu_start(start,stop,count=50000);u.hook_del(handle)
    assert u.reg_read(UC_X86_REG_RIP)==stop,'Execution bound reached';return seen
def decode(u,address):
    raw=bytes(u.mem_read(address,32));length,cap=struct.unpack_from('<QQ',raw,16)
    pointer=struct.unpack_from('<Q',raw)[0] if cap>=16 else address
    return {'length':length,'capacity':cap,'pointer':pointer,'text':bytes(u.mem_read(pointer,length+1))[:-1].decode()}
rows=[]
for name_cap,caption_cap in ((31,15),(31,31),(63,31)):
    u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(BASE,(len(d.image)+4095)&~4095);u.mem_write(BASE,d.image);u.mem_map(MEM,0x20000)
    request=MEM+0x1000;u.mem_write(request,struct.pack('<iI',-1,0)+sso('mpckpt01.s14')+sso(''))
    for at,cap,heap in ((BASE+0x201ED18,name_cap,MEM+0x4000),(BASE+0x201ED38,caption_cap,MEM+0x5000)):
        u.mem_write(at,q(heap)+bytes(8)+q(0)+q(cap) if cap>=16 else sso(''))
    before=[decode(u,BASE+rva) for rva in (0x201ED18,0x201ED38)]
    sp=MEM+0x1FEF8;u.mem_write(sp,q(STOP));u.reg_write(UC_X86_REG_RSP,sp);u.reg_write(UC_X86_REG_RCX,request)
    binder=execute(u,BASE+0x2FC750,STOP)
    bound=[decode(u,BASE+rva) for rva in (0x201ED18,0x201ED38)]
    assert bound[0]['text']=='mpckpt01.s14' and bound[1]['text']==''
    assert all(a['capacity']==b['capacity'] and a['pointer']==b['pointer'] for a,b in zip(before,bound))
    assert decode(u,request+8)['text']==decode(u,request+40)['text']==''
    cleanup=execute(u,BASE+0x465C67,BASE+0x465CB3)
    after=[decode(u,BASE+rva) for rva in (0x201ED18,0x201ED38)]
    assert all(a['text']=='' and a['capacity']==b['capacity'] and a['pointer']==b['pointer'] for a,b in zip(after,before))
    assert struct.unpack('<i',u.mem_read(BASE+0x201ED10,4))[0]==-1
    rows.append({'name_capacity':name_cap,'caption_capacity':caption_cap,'binder_instructions':len(binder),'cleanup_instructions':len(cleanup),'bound':bound,'after':after,'result':'PASS','external_stubs':0})
path=ROOT/('private_checkpoint_save_string_shadow_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
report={'result':'PASS','cases':rows,'game_access':False,'native_saved':False,'scope':'Actual copied 2FC750 binder/helpers and 465C67..465CB3 request-string clearing in Unicorn; no game state/worker/Steam or allocator side effects.'}
with path.open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
print(json.dumps({'result':'PASS','cases':len(rows),'evidence':str(path),'game_access':False}))
