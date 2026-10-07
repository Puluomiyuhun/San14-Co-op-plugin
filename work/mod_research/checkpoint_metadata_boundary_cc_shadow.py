"""Exact native CC formatter/category+full scans and Title filename binder.

Offline machine-code experiment only; byte source is a read-only archived
checkpoint. OS charset conversion, CRT formatting, allocation, timestamps and
storage transport are declared test doubles. No game process or file writes.
"""
from datetime import datetime
from pathlib import Path
import hashlib,json,struct
from checkpoint_metadata_boundary_pending_shadow import ScopeHarness
from checkpoint_load_mode_native_chain import BASE,MEM,ROOT,STOP
from unicorn.x86_const import *

class CCHarness(ScopeHarness):
    def __init__(self,present=True):
        super().__init__();self.cc_present=present;self.formats=[];self.opens=[];self.load_queues=[];self.small_next=MEM+0x2D0000
        del self.stubs[BASE+0x2F1650]
        self.output=MEM+0x2F1000;self.options=MEM+0x2F0000
        self.stubs[BASE+0x3A6C20]=lambda:self.ret(self.options)
        self.stubs[BASE+0x1C0CF0]=lambda:self.ret(self.output)
        self.stubs[BASE+0xC7710]=lambda:self.ret(self.options)
        self.stubs[BASE+0xF23CE8]=self.crt_format
        for rva,addr,fn in ((0x123C118,MEM+0x2F2000,self.to_wide),(0x123C148,MEM+0x2F2100,self.to_utf8)):
            self.putq(BASE+rva,addr);self.stubs[addr]=fn
    def allocate_ui(self):
        size=self.reg(UC_X86_REG_RCX)
        if size<=0x40:
            result=self.small_next;self.small_next+=0x100
            assert self.small_next<MEM+0x2F0000
            self.ret(result)
        else:super().allocate_ui()
    def run(self,start,stop=STOP,args=(),setup=None):
        sp=MEM+0xEF000;self.u.mem_write(sp-0x1000,bytes(0x2000));self.putq(sp,STOP)
        self.u.reg_write(UC_X86_REG_RSP,sp);self.u.reg_write(UC_X86_REG_RBP,sp+0x300)
        for reg,arg in zip((UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9),args):self.u.reg_write(reg,arg)
        if setup:setup(sp)
        self.stop=stop;self.u.emu_start(BASE+start,stop,count=1000000)
        assert self.reg(UC_X86_REG_RIP)==stop,'Instruction limit'
    def crt_format(self):
        dst=self.reg(UC_X86_REG_RDX);fmt=self.cstring(self.reg(UC_X86_REG_R9))
        ap=self.readq(self.reg(UC_X86_REG_RSP)+0x30)
        if '%s' in fmt:values=(self.cstring(self.readq(ap)),self.readq(ap+8)&0xffffffff)
        else:values=(self.readq(ap)&0xffffffff,)
        result=fmt%values;self.formats.append({'format':fmt,'args':list(values),'result':result})
        self.u.mem_write(dst,result.encode()+b'\0');self.ret(len(result))
    def to_wide(self):
        assert self.reg(UC_X86_REG_RCX)==65001
        text=self.cstring(self.reg(UC_X86_REG_R8));dst=self.readq(self.reg(UC_X86_REG_RSP)+0x28)
        self.u.mem_write(dst,(text+'\0').encode('utf-16le'));self.ret(len(text)+1)
    def to_utf8(self):
        assert self.reg(UC_X86_REG_RCX)==65001
        src=self.reg(UC_X86_REG_R8);words=[]
        while True:
            w=bytes(self.u.mem_read(src+2*len(words),2))
            if w==b'\0\0':break
            words.append(w)
        text=b''.join(words).decode('utf-16le');dst=self.readq(self.reg(UC_X86_REG_RSP)+0x28)
        self.u.mem_write(dst,text.encode()+b'\0');self.ret(len(text.encode())+1)
    def file_exists(self):
        name=self.cstring(self.reg(UC_X86_REG_RDX));self.scans.append(name)
        self.ret(int(self.cc_present and name=='svdexccSC03.s14'))
    def stream_open(self):
        ptr=self.reg(UC_X86_REG_RCX);name=self.read_sso(self.reg(UC_X86_REG_RDX))
        assert name=='svdexccSC03.s14' and self.cc_present
        assert self.reg(UC_X86_REG_R8)==1
        self.opens.append(name);self.put32(ptr+0x20,1);self.stream_cursor[ptr]=0;self.ret(1)
    def load_queue(self):
        name=self.cstring(self.reg(UC_X86_REG_RDX));self.load_queues.append(name);self.ret(0)

def format_case():
    h=CCHarness();rows=[]
    for slot in (0,49,50,59,60,63,109,110,119):
        for variant in (0,1):
            h.run(0x2F1650,args=(slot,0,variant));name=h.cstring(h.reg(UC_X86_REG_RAX))
            if 60<=slot<110:assert name==f'svdexccSC{slot-60:02d}.s14'
            rows.append({'slot':slot,'variant':variant,'name':name})
    assert {0x2F1650,0x2FE070,0x3A9800}<=set(h.visits)
    return {'case':'actual_native_slot_formatter','result':'PASS','rows':rows,
        'native_routines':['0x2F1650','0x2FE070','0x3A9800'],
        'stubs':['scratch-string provider3A6C20/1C0CF0','CRT option getterC7710 and vsnprintfF23CE8','Win32 UTF8/wide conversion APIs'],
        'corrected_legacy_assumption':'Slot63 is svdexccSC03.s14; svdexCC03.s14 is not the native formatter output.'}

def scan_case(present):
    h=CCHarness(present);h.u.mem_write(h.request,bytes(8))
    h.run(0x411980,args=(h.manager,BASE+0x12DD6E0,h.request,h.carrier));h.apply()
    first=list(h.scans)
    assert len(first)==50 and first[0]=='svdexSC00.s14' and first[-1]=='svdexSC49.s14'
    assert 'svdexccSC03.s14' not in first and h.readq(h.cache+0x20+63*8)==0
    # A positive pending slot needs no pre-existing table entry in Game Update.
    h.put32(h.cache+0x3EC,63);h.scans=[];start=len(h.visits)
    h.run(0x836EF0,args=(h.cache,0));second=list(h.scans)
    assert len(second)==120 and second[63]=='svdexccSC03.s14'
    assert h.read32(h.cache+0x3EC)==63
    metadata=h.readq(h.cache+0x20+63*8)
    assert bool(metadata)==present
    if present:
        assert h.read_sso(metadata+0x128)=='svdexccSC03.s14'
        assert len(h.opens)==1 and sum(x['size'] for x in h.scan_reads)==294
        assert {0x2FAAD0,0x2E0E80,0x837315}<=set(h.visits[start:])
    title=MEM+0x2A0000
    h.put32(title+0x47C,0xffffffff);h.u.mem_write(title+0x480,bytes(24)+struct.pack('<Q',15))
    h.u.mem_write(BASE+0x201ECE0,bytes(24)+struct.pack('<Q',15))
    before=len(h.visits);h.stubs[BASE+0x410810]=h.load_queue
    h.run(0x4CEAB0,args=(title,0))
    if present:
        assert h.read32(title+0x47C)==63
        assert h.read_sso(title+0x480)=='svdexccSC03.s14'
        assert h.read32(BASE+0x201ECD0)==63
        assert h.read_sso(BASE+0x201ECE0)=='svdexccSC03.s14'
        assert 0x4BF5A0 in h.visits[before:] and h.load_queues==['CLoadState']
    else:assert not h.load_queues and 0x4BF5A0 not in h.visits[before:]
    return {'case':'native_storage_visible_CC03' if present else 'native_storage_missing_CC03','result':'PASS',
        'storage_visibility_fixture':present,'SaveLoad_default_category_scan_count':len(first),
        'SaveLoad_default_category_includes_slot63':False,'Title_full_scan_count':len(second),
        'Title_full_scan_slot63_name':second[63],'Title_native_metadata_constructed':bool(metadata),
        'native_filename_binder_executed':present,'bound_slot':63 if present else None,
        'bound_filename':'svdexccSC03.s14' if present else None,'load_state_queue_stub_calls':h.load_queues,
        'native_header_bytes_consumed':sum(x['size'] for x in h.scan_reads),
        'native_storage_stream_open_names':h.opens,
        'scope':'Native formatter, category/full scanner, header parser, native node copy/registration, positive-slot lookup, SSO filename binding execute. UI/storage/allocator/CRT/charset/timestamp primitives and final CLoadState queue are stubs. No world deserialization executes.'}

def main():
    rows=[format_case(),scan_case(True),scan_case(False)]
    out=ROOT/('checkpoint_metadata_boundary_cc_shadow_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    result={'schema':'san14.checkpoint-native-cc-boundary-shadow.v1','result':'PASS','cases':rows,
        'game_access':False,'actual_file_created':False,'steam_write_or_refresh_executed':False,
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'conclusion':'An actually absent slot63 may be reserved as svdexccSC03.s14. SaveLoad category0 does not index it; Title full native scan naturally indexes and binds it if Steam FileExists/Open see the bytes. Local filesystem existence alone does not prove Steam visibility.'}
    with out.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps({'result':'PASS','cases':len(rows),'path':str(out),'game_access':False}))
if __name__=='__main__':main()
