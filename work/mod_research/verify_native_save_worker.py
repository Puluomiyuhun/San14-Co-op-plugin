"""Execute captured save worker/finalizer machine code in a private x64 VM.

Serialization, storage I/O, locks, destruction and other manager calls are
explicit scripted test doubles. This tests the native result/control flow,
not real storage, save content, game quiescence, or an installed adapter.
"""
from pathlib import Path
import json, struct, sys
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'python_deps'),str(HERE)]
import unicorn as u
from unicorn.x86_const import *
from audit_native_checkpoint import audit, function, d, write

BASE=0x10000000
ARENA=0x50000000
ROOT=ARENA
ARCHIVE=ARENA+0x90000
STREAM=ARENA+0x91000
BACKING=ARENA+0x92000
VTABLE=ARENA+0x93000
VIRTUAL_DELETE=ARENA+0x94000
STOP=ARENA+0x94010
STACK=ARENA+0xE0000
FLAG=BASE+0x201EC2C


def run_case(prepare=True,status=0,storage_ok=True,stream_present=True,reused=False,backing=False,old_flag=1):
    vm=u.Uc(u.UC_ARCH_X86,u.UC_MODE_64)
    vm.mem_map(BASE,(len(d.image)+4095)&-4096);vm.mem_write(BASE,d.image)
    vm.mem_map(ARENA,0x100000)
    q=lambda a,v:vm.mem_write(a,struct.pack('<Q',v))
    w=lambda a,v:vm.mem_write(a,struct.pack('<I',v&0xFFFFFFFF))
    rq=lambda a:struct.unpack('<Q',vm.mem_read(a,8))[0]
    rw=lambda a:struct.unpack('<I',vm.mem_read(a,4))[0]
    q(BASE+0x1FCA1E0,ROOT)
    q(ARCHIVE,VTABLE);q(BACKING,VTABLE)
    q(VTABLE,VIRTUAL_DELETE);q(VTABLE+0x78,VIRTUAL_DELETE)
    q(ARCHIVE+0x10,STREAM if stream_present else 0)
    q(ARCHIVE+8,BACKING if backing else 0)
    q(ROOT+0x851A0,ARCHIVE if reused else 0)
    w(ARCHIVE+0x24,status);w(ARCHIVE+0x28,0)
    w(FLAG,old_flag)
    for p in (BASE+0x201ED18,BASE+0x201ED38):q(p+0x18,0)
    q(STACK,STOP);vm.reg_write(UC_X86_REG_RSP,STACK)
    vm.reg_write(UC_X86_REG_RCX,ARENA+0x95000)
    allowed={BASE+i.address for at in (0x508CA0,0x2FCE40) for i in function(at)}
    calls=[];observations=[];instructions=0
    stubs={0x2EE740:'prepare',0x3A6A10:'storage_commit',0x3A83D0:'optional_stream_step',
        0x3A50D0:'lock_enter',0x3A5680:'lock_leave',0x2EE0B0:'report_error',
        0x3A55D0:'destroy_stream',0xEF97B4:'free_stream',
        0x39C260:'manager_one',0x3A0690:'manager_one_cleanup',
        0x39C440:'manager_two',0x39D500:'manager_two_cleanup'}
    def ret(value):
        vm.reg_write(UC_X86_REG_RAX,value&0xFFFFFFFFFFFFFFFF)
        sp=vm.reg_read(UC_X86_REG_RSP)
        vm.reg_write(UC_X86_REG_RIP,rq(sp));vm.reg_write(UC_X86_REG_RSP,sp+8)
    def hook(vm,pc,size,_):
        nonlocal instructions
        instructions+=1
        if pc==STOP:vm.emu_stop();return
        if pc==VIRTUAL_DELETE:
            calls.append('virtual_delete');ret(0);return
        rva=pc-BASE
        if rva in stubs:
            name=stubs[rva];calls.append(name)
            if name=='prepare':ret(ARCHIVE if prepare else 0)
            elif name=='storage_commit':ret(1 if storage_ok else 0)
            elif name in ('manager_one','manager_two'):ret(ARENA+0x95000)
            else:ret(0)
            return
        if pc not in allowed:raise RuntimeError(f'Unexpected emulated execution {pc:#x}')
        if rva in (0x508CE9,0x508CFD,0x508D22):
            observations.append({'pc_rva':hex(rva),'eax':vm.reg_read(UC_X86_REG_EAX),
                                 'flag':rw(FLAG),'calls_so_far':calls[:]})
    vm.hook_add(u.UC_HOOK_CODE,hook)
    vm.emu_start(BASE+0x508CA0,STOP+1,count=1000)
    assert vm.reg_read(UC_X86_REG_RIP)==STOP,'Worker did not finish'
    final_status=(status&0xFFFFFFFF) if status else (0 if storage_ok or not stream_present else 0xFFFFFED4)
    expected=int(prepare and final_status==0)
    assert rw(FLAG)==expected
    assert calls.count('storage_commit')==int(prepare and status==0 and stream_present)
    assert calls.count('destroy_stream')==int(prepare and stream_present)
    assert observations[0]['pc_rva']=='0x508ce9' and observations[0]['flag']==old_flag
    assert observations[-1]['pc_rva']=='0x508d22' and observations[-1]['flag']==expected
    if prepare:
        finalizer=next(x for x in observations if x['pc_rva']=='0x508cfd')
        assert finalizer['eax']==final_status and finalizer['flag']==old_flag
        assert rq(ARCHIVE+0x10)==0 and rq(ARCHIVE+8)==0
    else:assert all(x['pc_rva']!='0x508cfd' for x in observations)
    return {'inputs':dict(prepare=prepare,status=status,storage_ok=storage_ok,
                         stream_present=stream_present,reused=reused,backing=backing,old_flag=old_flag),
            'worker_success':bool(expected),'instructions':instructions,'calls':calls,'observations':observations}


def main():
    audit()
    cases=[{}, {'prepare':False}, {'storage_ok':False}, {'status':-323}, {'status':1},
           {'reused':True}, {'backing':True}, {'storage_ok':False,'backing':True},
           {'old_flag':0}, {'prepare':False,'old_flag':0}, {'stream_present':False},
           {'status':-300,'stream_present':False}]
    rows=[run_case(**c) for c in cases]
    result={'schema':'san14.native-save-worker-shadow.v1','result':'PASS','cases':len(rows),'rows':rows,
        'native_code':['0x508ca0 worker','0x2fce40 finalizer'],
        'game_calls':0,'game_memory_writes':0,'real_storage_tested':False,
        'full_checkpoint_roundtrip_tested':False,
        'findings':['Preparation return occurs before native storage finalization.',
            'A stale success flag remains visible until the current worker publishes its own result.',
            'Storage failure -300 propagates through the finalizer to worker failure.',
            'This worker accepts only exact zero finalizer status; positive status is not success.',
            'A fabricated null-stream archive with zero status reports success, so a flag alone cannot certify a fresh file.'],
        'limits':['Actual game entry, serialization, storage callbacks, locks, cleanup and destruction are replaced by explicit test doubles.',
            'Not a native save call, file export, actual observer test, or proof that arbitrary archive input is valid.']}
    write(HERE/'native-save-worker-shadow.json',result)
    print(json.dumps({'result':'PASS','cases':len(rows),'native_functions':2,'game_calls':0}))


if __name__=='__main__':main()
