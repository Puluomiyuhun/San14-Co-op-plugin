"""Offline cache-mode consumer/ctor audit. No process, Steam or save access."""
from datetime import datetime
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'python_deps'),str(ROOT)]
import capstone
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *
BASE=0x7ff749440000;MEM=0x300000000;STOP=MEM+0xff00
IMAGE=(ROOT/'game-runtime-image.bin').read_bytes()
assert hashlib.sha256(IMAGE).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
q=lambda v:struct.pack('<Q',v)
d=lambda v:struct.pack('<I',v&0xffffffff)
def readq(u,p):return struct.unpack('<Q',u.mem_read(p,8))[0]
def read32(u,p):return struct.unpack('<I',u.mem_read(p,4))[0]
def new(mode,pending=-1,owned=False):
    u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(BASE,(len(IMAGE)+4095)&~4095);u.mem_write(BASE,IMAGE)
    u.mem_map(MEM,0x40000)
    cache,head,node=MEM+0x1000,MEM+0x2000,MEM+0x3000
    u.mem_write(BASE+0x2025318,q(cache));u.mem_write(cache+8,d(mode));u.mem_write(cache+0x3EC,d(pending))
    u.mem_write(cache+0x10,q(head));u.mem_write(head,q(head)+q(head))
    if owned:
        u.mem_write(cache+0x18,q(1));u.mem_write(head,q(node)+q(node));u.mem_write(node,q(head)+q(head))
        u.mem_write(node+0x138,b'mppush01.s14\0'.ljust(16,b'\0')+q(12)+q(15))
        u.mem_write(cache+0x20+63*8,q(node+16))
    return u,cache,head,node
def run(u,start,args=(),stop=STOP,free=None):
    sp=MEM+0x3fef8;u.mem_write(sp,q(STOP));u.reg_write(UC_X86_REG_RSP,sp)
    for reg,arg in zip((UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9),args):u.reg_write(reg,arg)
    visits=[]
    def hook(uc,address,size,data):
        if address==stop:uc.emu_stop();return
        if address==BASE+0x3A58B0 and free is not None:
            free.append(uc.reg_read(UC_X86_REG_RCX));sp=uc.reg_read(UC_X86_REG_RSP)
            uc.reg_write(UC_X86_REG_RAX,0);uc.reg_write(UC_X86_REG_RIP,readq(uc,sp));uc.reg_write(UC_X86_REG_RSP,sp+8);return
        assert BASE<=address<BASE+len(IMAGE),hex(address)
        visits.append(address-BASE)
    token=u.hook_add(UC_HOOK_CODE,hook);u.emu_start(BASE+start,stop,count=10000);u.hook_del(token)
    assert u.reg_read(UC_X86_REG_RIP)==stop
    return visits
def main():
    cases=[]
    for mode,pending,wanted in [(0,63,1),(1,63,0),(0,-1,0),(1,-1,0)]:
        u,cache,head,node=new(mode,pending);game=MEM+0x5000
        u.reg_write(UC_X86_REG_R12,1)
        visits=run(u,0x3F8177,(game,),stop=BASE+0x3F8194)
        assert read32(u,game+0x474)==wanted
        assert read32(u,cache+8)==mode and read32(u,cache+0x3EC)==pending&0xffffffff
        cases.append({'case':'actual_game_pending_gate','mode':mode,'pending':pending,'reload_flag':wanted,'instructions':len(visits),'result':'PASS'})
    for mode in (0,1):
        u,cache,head,node=new(mode,owned=True)
        visits=run(u,0x836710,(cache,63))
        assert u.reg_read(UC_X86_REG_RAX)==node+16 and read32(u,cache+8)==mode
        cases.append({'case':'actual_slot_getter_ignores_mode','mode':mode,'slot':63,'result':'PASS','instructions':len(visits)})
    u,cache,head,node=new(1,pending=63,owned=True);request=MEM+0x4000;state=MEM+0x5000
    u.mem_write(request,d(0)+d(0));freed=[]
    visits=run(u,0x426320,(state,request),free=freed)
    assert freed==[node] and read32(u,cache+8)==0 and read32(u,cache+0x3F0)==0
    assert read32(u,cache+0x3EC)==0xffffffff and readq(u,cache+0x18)==0
    assert readq(u,head)==head and readq(u,head+8)==head
    assert bytes(u.mem_read(cache+0x20,960))==bytes(960)
    assert visits.index(0x42638B)<visits.index(0x426399)
    cases.append({'case':'actual_saveload_ctor_clears_metadata_before_mode0','result':'PASS','freed_nodes':len(freed),
        'metadata_survives':False,'pending_after':-1,'stub_scope':'Only allocator free 3A58B0 is stubbed; actual 426320,835DD0,836DF0,837E80 and inline SSO cleanup execute.'})
    decoder=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
    anchors=[]
    for at in (0x3F817E,0x3F8182,0x3F8184,0x3F818D,0x42638B,0x426399,0x4263A6,0x4AA272,0x4AA277,0x4AA589,0x4CEAE7,0x4CEAF7,0x4CEB0B):
        ins=next(decoder.disasm(IMAGE[at:at+15],at));anchors.append({'rva':hex(at),'bytes':ins.bytes.hex(),'instruction':ins.mnemonic+' '+ins.op_str})
    report={'schema':'san14.private-checkpoint-metadata-mode-audit.v1','created':datetime.now().astimezone().isoformat(),
        'result':'PASS_OFFLINE_ONLY','game_access':False,'cases':cases,'anchors':anchors,
        'conclusions':[
            'Cache mode is not the archive stream read/write mode. Explicit save worker evidence cannot waive the reload consumer mode gate.',
            'Native node copy/link/table getter and Title pending-to-filename copy do not themselves require mode0 in the audited paths.',
            'The existing CGameState pending-slot entry has a real mode0 requirement. In mode1, pending63 remains unconsumed by this entry and does not set Game+474.',
            'Normal CSaveLoadState ctor426320 clears owned metadata and all table entries before assigning mode from its input. Register-before-native-mode-change loses the target.',
            'Old PCM core mode0 guard is an early integration readiness restriction, not a metadata parser or node-copy ABI requirement. It must remain until a separately reviewed mode0 lifecycle/alternate entry is established.',
            'For the existing pending route: establish mode0 by a proven native lifecycle first, then reverify file identity and register the exact target, then submit with mode still0. No direct cache-mode edit is proposed.'
        ],
        'necessary_conditions':['Stable supported planning/main-thread boundary and no pending state/save/load work.',
            'Valid owned list/table and physically absent reserved slot; target filename and full bytes bound before submission.',
            'Native request requires mode0,pending=-1 before commit; exact target metadata must survive until Title copies its filename.',
            'Secondary+3F0 is a UI/category field in audited consumers; keep0 under current contract rather than infer arbitrary values safe.',
            'The old core is fixed to mpckpt01.s14 and obsolete per-file journal/name/profile. It is not directly usable for the newly passed mppush01.s14.'],
        'limits':['No complete native mode-switch UI lifecycle was executed. No native load or metadata registration ran in SAN14.',
            'The ctor VM frees a synthetic owned SSO node; allocator deallocation is stubbed. Other UI/category consumers are not exhaustively proved.',
            'Header validation and point-in-time raw-file identity still do not prove a future load reads the same full bytes.'],
        'live_execution_eligible':False,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (ROOT/'private_checkpoint_metadata_mode_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':report['result'],'cases':len(cases),'game_access':False}))
if __name__=='__main__':main()
