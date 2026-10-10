"""Exercise actual exported coordinator using owned predecessor report DLLs only."""
import ctypes as C
import os,shutil
from pathlib import Path
import b_warm_chain_coordinator_contract as w
class Input(C.Structure):
    _fields_=[('slots',w.U64*6),('originals',w.U64*6),('mode',w.U32),('fault',w.U32),('seed',w.U32)]
def exercise(run):
    cases=[]
    def need(condition,name):
        if not condition:raise AssertionError(name)
        cases.append(name)
    def call(dll,name,x):
        fn=getattr(dll,name);fn.argtypes=[C.c_void_p];fn.restype=w.U32
        return fn(C.byref(x))
    dll=C.WinDLL(str(run/'coordinator.dll'));nonce=bytes([0x73])*32
    d=w.Description();need(call(dll,w.EXPORTS[0],d)==0,'actual_description');w.decode(w.Description,bytes(d))
    def command(kind,**fields):
        x=w.envelope(kind,nonce)
        for key,value in fields.items():
            if key in ('slots','originals'):getattr(x,key)[:]=value
            else:setattr(x,key,value)
        rc=call(dll,{w.Prepare:w.EXPORTS[1],w.Authorize:w.EXPORTS[2],w.Observe:w.EXPORTS[3]}[kind],x)
        return rc,w.decode(kind,bytes(x),nonce)
    need(command(w.Observe)[0]!=0,'unprepared_observe_refused')
    need(command(w.Authorize,next=1,generation=2)[0]!=0,'unprepared_authorize_refused')
    banks=[]
    for i in range(3):
        dest=run/f'bank-{i}.dll';shutil.copyfile(run/'bank.dll',dest);banks.append(C.WinDLL(str(dest)))
    k=C.WinDLL('kernel32',use_last_error=True)
    k.VirtualAlloc.argtypes=[C.c_void_p,C.c_size_t,w.U32,w.U32];k.VirtualAlloc.restype=C.c_void_p
    memory=k.VirtualAlloc(None,4096,0x3000,4);need(bool(memory),'owned_slots_allocated')
    slots=(w.U64*6).from_address(memory);original=C.cast(k.GetCurrentProcessId,C.c_void_p).value
    data=Input()
    for i in range(6):slots[i]=original;data.slots[i]=memory+i*8;data.originals[i]=original
    def setbank(index,mode=0,fault=0,seed=0):
        data.mode=mode;data.fault=fault;data.seed=seed
        need(call(banks[index],'FixtureSet',data)==0,f'set_owned_bank_{index}_{mode}_{fault}')
    for i in range(3):setbank(i)
    k.GetCurrentProcess.restype=C.c_void_p
    k.GetProcessTimes.argtypes=[C.c_void_p]+[C.POINTER(w.U64)]*4
    times=[w.U64() for _ in range(4)];need(bool(k.GetProcessTimes(k.GetCurrentProcess(),*[C.byref(t) for t in times])),'owned_process_birth')
    rc,x=command(w.Prepare,pid=os.getpid(),birth=times[0].value,first=banks[0]._handle,slots=list(data.slots),originals=list(data.originals));need(rc==0,'prepare_export')
    need(command(w.Prepare)[0]==2,'prepare_cannot_reset')
    need(command(w.Authorize,next=banks[2]._handle,generation=3)[0]!=0,'skip_generation_refused')
    need(command(w.Authorize,next=banks[1]._handle,generation=2)[0]!=0,'early_second_refused')
    setbank(0,1)
    rc,state=command(w.Observe);need(rc==0 and list(state.completed)==[1,0,0],'first_completion_real_predicates')
    bad=w.envelope(w.Authorize,bytes([1])*32);bad.next=banks[1]._handle;bad.generation=2
    need(call(dll,w.EXPORTS[2],bad)!=0,'different_nonce_refused')
    need(command(w.Authorize,next=banks[0]._handle,generation=2)[0]!=0,'first_bank_reuse_refused')
    need(command(w.Authorize,next=banks[1]._handle,generation=2)[0]==0,'second_export_authorized')
    rc,state=command(w.Observe);first=bytes(state.certificates[0]);need(rc==0 and state.currentGeneration==2 and list(state.completed)==[1,0,0],'second_not_falsely_complete')
    need(command(w.Authorize,next=banks[1]._handle,generation=2)[0]!=0,'second_authorization_replay_refused')
    for fault in range(1,5):
        setbank(1,1,fault,1);need(command(w.Authorize,next=banks[2]._handle,generation=3)[0]!=0,'third_fault_refused_'+str(fault))
    setbank(1,1,0,1);slots[0]=0
    need(command(w.Authorize,next=banks[2]._handle,generation=3)[0]!=0,'dirty_live_slot_refused');slots[0]=original
    need(command(w.Authorize,next=banks[0]._handle,generation=3)[0]!=0,'third_bank_reuse_refused')
    need(command(w.Authorize,next=banks[2]._handle,generation=3)[0]==0,'third_export_authorized')
    rc,state=command(w.Observe)
    need(rc==0 and state.currentGeneration==3 and list(state.completed)==[1,1,0],'third_not_falsely_complete')
    need(first==bytes(state.certificates[0]) and state.certificates[1].attempt==78 and state.certificates[1].fileSha256[0]==18,'exact_second_receipt_not_first')
    setbank(2,1,0,2);rc,state=command(w.Observe);need(rc==0 and list(state.completed)==[1,1,1],'third_completed_export')
    need(command(w.Authorize,next=banks[0]._handle,generation=4)[0]!=0,'fourth_outside_bound_refused')
    bad=w.Observe.from_buffer_copy(bytes(state));bad.certificates[1].birth+=1
    try:w.decode(w.Observe,bytes(bad),nonce)
    except ValueError:cases.append('decoder_cross_process_certificate_refused')
    else:raise AssertionError('decoder accepted mismatched process')
    bad=w.Observe.from_buffer_copy(bytes(state));bad.completed[0]=0
    try:w.decode(w.Observe,bytes(bad),nonce)
    except ValueError:cases.append('decoder_prior_completion_refused')
    else:raise AssertionError('decoder accepted lost prior completion')
    # Isolated one-shot preparation rejection does not poison successful coordinator.
    other=run/'rejected-coordinator.dll';shutil.copyfile(run/'coordinator.dll',other);rejected=C.WinDLL(str(other))
    bad=w.envelope(w.Prepare,nonce);bad.pid=os.getpid();bad.birth=1;bad.first=banks[0]._handle
    need(call(rejected,w.EXPORTS[1],bad)==3,'wrong_birth_refused')
    bad=w.envelope(w.Prepare,nonce);need(call(rejected,w.EXPORTS[1],bad)==2,'failed_prepare_terminal')
    return cases
