"""Execute bounded archived User early paths; all external models are named.

Only SAN14_PRIVATE_FIXTURE_ROOT is read. No process, Steam, UI or game file IO.
The private machine code stays in memory and is never emitted into the repo.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import struct
import sys

ARCHIVE_SHA='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
RANGES={
 'user':(0x3F9B00,0x3FA0B4,'20dac87aef24debe8d58eac2036fca2b79149da970b7d1a90fb45cfb2b3eab94'),
 'singleton':(0x15FA20,0x15FA9B,'538a3c2fe54eb6ba44fa35f2cfd707f0872e3cd333a8c7bd6a8c6f0029d84bec'),
 'updater':(0x16C5F0,0x16C63C,'4688dac5892266d89ff063fa9278fa552f204ce2b68020176856c1726366823e'),
 'render_empty_a':(0x163C80,0x163FFE,'d99cfc5d472f2f02022a132335c2e5cf87892a3d4aafa7eeeabcad8657006e2c'),
 'render_empty_b':(0x16C6D0,0x16CB2D,'f84fdcaef73879f055ff01f205b9875773ec1e9f86a5bff9d226e5a58a0aaf7e'),
 'report_flush':(0x2A1EC0,0x2A24F2,'bb19d25ed47c8532f8fbef139e7387ea139b378ee95f808a0ed01883d8289d2e'),
 'report_clear':(0x240310,0x2403D2,'c63a674323db7ed66cc922fedb5546245a14708b116f880cc921c3fa077875c0'),
 'selection_clear':(0x3E8EF0,0x3E8F98,'112c4a49b29cde5ff587df6e87d7b7ecf6ba262ac3eb2145b62836f733fbf029'),
 'selection_set':(0x3FB9B0,0x3FBAFA,'714277513aef74674244b50f10ff146d7941b15a1fd051b9d87d775190f932dd'),
 'picked_tile':(0x179FD0,0x179FF4,'4295c9481aa6691f0365b35ae474ef2588a2a4c2b06efb18985e7944b9510adf'),
 # Complete function verified separately from the fixed archive, including the
 # actual root-owned report writes and world+165A cursor store.
 'report_insert':(0x835800,0x835D27,'f8b338ea68e060276954fc5118cd99860ea01cf806455f0c5b3a28c6c1252cd8'),
}


def require(ok,why):
    if not ok:raise ValueError(why)


def execute(raw,name):
    import capstone as cs
    import unicorn as uc
    from unicorn import x86_const as x
    base,root,stack,teb=0x140000000,0x50000000,0x60010008,0x70000000
    world,record,unit,force,head,node,data,user=(root+i for i in (0x86000,0x90000,0x95000,0x98000,0x9B000,0x9C000,0x9D000,0xF0000))
    machine=uc.Uc(uc.UC_ARCH_X86,uc.UC_MODE_64)
    machine.mem_map(base,0x2400000);machine.mem_map(root,0x100000);machine.mem_map(stack-0x10008,0x20000);machine.mem_map(teb,0x10000)
    for a,z,_ in RANGES.values():machine.mem_write(base+a,raw[a:z])
    def put(at,value,n=8):machine.mem_write(at,int(value).to_bytes(n,'little',signed=value<0))
    def get(at,n=8):return int.from_bytes(machine.mem_read(at,n),'little')
    def reg(n):return machine.reg_read(n)
    enabled=name in ('report-empty','report-one','report-other-owner')
    populated=name in ('report-one','report-other-owner','flag-zero-queued')
    put(base+0x18EB8B8,root+0xA1000);put(base+0x1FCA1E0,root);put(root+0x85130,world);put(world+0x165A,0,2);put(world+0x450,203*36+23,4)
    put(root+0x795B8+8,record);put(root+0xDE40+12*8,force)
    put(user+0x470,2,4);put(user+0x660,int(enabled),4)
    put(base+0x1FC98B0,head);put(base+0x1FC98B8,int(populated))
    for off in (0,8,16):put(head+off,node if populated else head)
    put(head+0x19,1,1)
    for off in (0,8,16):put(node+off,head)
    put(node+0x20,unit);put(node+0x28,data);put(node+0x30,data+20);put(node+0x38,data+20)
    put(unit+0x118,13 if name=='report-other-owner' else 12,1);put(unit+0x10,44,2);put(unit+0x11A,4,2)
    # One empty-text diagnostic event; native integer record mutation still runs.
    put(data+4,7,1);put(data+5,3,1);put(data+12,0,4);put(data+16,1,4)
    put(teb+0x58,teb+0x1000);put(teb+0x1000,teb+0x2000);put(teb+0x2010,0x7FFFFFFF,4)
    put(base+0x203ABC0,0,4);machine.reg_write(x.UC_X86_REG_GS_BASE,teb)
    # Already constructed drawing updater, empty +90 list. Both branches below
    # are actual archived functions and therefore make no scene-object calls.
    put(base+0x1A38A10,0,4);put(base+0x1A38840+0xA0,0)
    put(base+0x1A38840+0x1C4,int(name=='updater-active-empty'),4)
    locale_table=base+0x2201000;put(base+0x18CBF00,locale_table);put(locale_table+8,base+0x2201100)
    put(base+0x1A38F30,root+0xB0000);put(root+0xDF4B0,1 if name=='selection-pick' else -1,4)
    put(root+0xDFE0+8,root+0xA0000);put(root+0x7DF60+44*8,unit)
    if name=='selection-clear':put(user+0x4A8,unit)
    before=dict(flag=get(user+0x660,4),queue_count=get(base+0x1FC98B8),
                report_owner_matches=get(root+0xDE40+get(unit+0x118,1)*8)==force)
    if name=='report-other-owner':
        require(before==dict(flag=1,queue_count=1,report_owner_matches=False),
                'Different-owner fixture must start flagged, populated, and owner-mismatched')
    machine.reg_write(x.UC_X86_REG_RCX,user);machine.reg_write(x.UC_X86_REG_RSP,stack)
    decoder=cs.Cs(cs.CS_ARCH_X86,cs.CS_MODE_64)
    callsites=[];external=[];writes=[];started=[];errors=[]
    known={a for a,_,_ in RANGES.values()}
    def model(at,row,target):
        callsites.append(dict(site=hex(at-base),target=hex(target) if target is not None else 'indirect'))
        if target in known:return
        external.append(dict(site=hex(at-base),target=hex(target) if target is not None else 'indirect'))
        rcx,rdx=reg(x.UC_X86_REG_RCX),reg(x.UC_X86_REG_RDX)
        value=0
        if target==0x509640:value=1
        elif target==0xD140:value=2 if name=='selection-pick' else 3
        elif target==0x2F21A0:value=force
        elif target==0x2F07A0:value=unit
        elif target in (0x20B000,):value=unit
        elif target==0x2F2BB0:value=int(bool(rcx))
        elif target==0x22CE30:machine.mem_write(rcx,bytes(machine.mem_read(rdx,24)))
        elif target==0xF1BB40:machine.mem_write(rcx,bytes([rdx&255])*reg(x.UC_X86_REG_R8));value=rcx
        elif target==0x160BD0:put(rcx,0x1B,4);put(rdx,44,4)
        elif target==0xEF9EB0:value=reg(x.UC_X86_REG_RAX) # __chkstk, preserve size
        elif target==0x3EC960:pass # selection UI rebuild is an explicit unresolved callee
        elif target in (0xF720,0xF690,0x3A29E0,0x2D54E0,0x2D7D50,0x2D6C10,0x2D7DC0,0x2D7EE0,
                        0x188970,0x3B3960,0x1D5170,0x20B730,0x3A58B0,0x2D07B0,0xEF9F20,
                        0x1FE6D0,0x21D9A0,0x21D9C0,0x9C4F60,0x1FEB40,0x20A810,0x5086A0,
                        0x337BB0,None):pass
        else:raise ValueError(f'UNMODELED external {target!r} at {at-base:x}')
        machine.reg_write(x.UC_X86_REG_RAX,value);machine.reg_write(x.UC_X86_REG_RIP,at+row.size)
    def code(m,address,size,_):
        rva=address-base
        if rva==0x3F9DAF:m.emu_stop();return
        if rva in known:started.append(hex(rva))
        row=next(decoder.disasm(bytes(m.mem_read(address,size)),address))
        if row.mnemonic=='call':
            target=int(row.op_str,16)-base if row.op_str.startswith('0x') else None
            model(address,row,target)
    def write(m,access,at,n,value,_):
        if stack-0x10008<=at<stack+0xFFF8:return
        owner=('world' if world<=at<world+0x2000 else 'report-record' if record<=at<record+0x2000 else
               'user' if user<=at<user+0x1000 else 'queue-node' if head<=at<node+0x1000 else 'other')
        origin=world if owner=='world' else record if owner=='report-record' else user if owner=='user' else base if at>=base else root
        writes.append(dict(pc=hex(reg(x.UC_X86_REG_RIP)-base),owner=owner,offset=hex(at-origin),size=n,value=value))
    machine.hook_add(uc.UC_HOOK_CODE,code);machine.hook_add(uc.UC_HOOK_MEM_WRITE,write)
    try:machine.emu_start(base+0x3F9B00,base+0x3FA0B4,count=30000)
    except Exception as exc:raise RuntimeError(f'{name}: pc={reg(x.UC_X86_REG_RIP)-base:x} rax={reg(x.UC_X86_REG_RAX):x} rbx={reg(x.UC_X86_REG_RBX):x} rcx={reg(x.UC_X86_REG_RCX):x} rdx={reg(x.UC_X86_REG_RDX):x}: {exc}') from exc
    require(reg(x.UC_X86_REG_RIP)==base+0x3F9DAF,'User did not reach existing tail gate')
    state=dict(flag=get(user+0x660,4),world_report_cursor=get(world+0x165A,2),queue_count=get(base+0x1FC98B8),selection=get(user+0x4A8))
    if name=='report-one':require(state==dict(flag=0,world_report_cursor=1,queue_count=0,selection=0),'Real native report insertion/cursor/queue path not observed')
    elif name=='report-other-owner':
        require(state['world_report_cursor']==0 and state['queue_count']==0 and state['flag']==0,'Different-owner record filtering or global queue clear differed')
        require('0x2a1ec0' in started and '0x240310' in started and '0x835800' not in started,
                'Different-owner fixture must execute native report flush/clear and skip report insert')
        require(not any(w['owner'] in ('world','report-record') for w in writes) and bool(writes),
                'Different-owner filtering must clear queue/User without world/record writes')
    elif name=='report-empty':require(state['flag']==0 and state['world_report_cursor']==0,'Empty report flush differs')
    elif name=='flag-zero-queued':require(state['flag']==0 and state['queue_count']==1 and state['world_report_cursor']==0,'Zero flag should skip pending queue')
    elif name=='selection-pick':require(state['selection']==unit and any(w['owner']=='user' and w['offset']=='0x4a8' for w in writes),'Native early selection assignment absent')
    elif name=='selection-clear':require(state['selection']==0 and any(w['owner']=='user' and w['offset']=='0x610' for w in writes),'Native selection cleanup absent')
    else:require(not writes,'Empty updater/idle path unexpectedly wrote non-stack memory')
    return dict(case=name,result='PASS',before=before,after=state,actual_nonstack_writes=writes,actual_functions_started=started,
                observed_calls=callsites,modeled_external_calls=external)


def main():
    value=os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT','');require(value,'Set SAN14_PRIVATE_FIXTURE_ROOT')
    private=Path(value).resolve();sys.path.insert(0,str(private/'python_deps'))
    run=Path(__file__).resolve().parent/'a_save_early_audit_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    output=dict(schema='san14.a-save-early-audit.v1',result='FAIL',game_access=False,cases=[])
    try:
        raw=(private/'game-runtime-image.bin').read_bytes();require(hashlib.sha256(raw).hexdigest()==ARCHIVE_SHA,'Archive identity differs')
        output['archive_sha256']=ARCHIVE_SHA
        output['source_ranges']=[]
        for name,(a,z,wanted) in RANGES.items():
            observed=hashlib.sha256(raw[a:z]).hexdigest();require(wanted is None or observed==wanted,f'Range differs {name}')
            output['source_ranges'].append(dict(name=name,begin=hex(a),end=hex(z),sha256=observed))
        for case in ('idle','updater-active-empty','report-empty','report-one','report-other-owner','flag-zero-queued','selection-pick','selection-clear'):
            row=execute(raw,case);output['cases'].append(row);print(case,row['result'],flush=True)
        output['result']='PASS'
    except Exception as exc:
        output['error']=repr(exc)
        raise
    finally:
        (run/'result.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(result=output['result'],path=str(run/'result.json'))))


if __name__=='__main__':main()
