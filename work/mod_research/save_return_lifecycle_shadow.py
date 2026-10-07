"""Offline native save-return/control-side-effect cases; never opens the game."""
from pathlib import Path
import ast,hashlib,json,struct,types
ROOT=Path(__file__).resolve().parent
# Reuse only helper definitions; do not run or overwrite earlier shadow reports.
source=ROOT/'private_checkpoint_load_shadow.py';tree=ast.parse(source.read_text())
body=[]
for item in tree.body:
    if isinstance(item,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cases' for t in item.targets):break
    body.append(item)
ns={'__file__':str(source),'__name__':'save_return_helpers'}
exec(compile(ast.Module(body=body,type_ignores=[]),str(source),'exec'),ns)
n=types.SimpleNamespace(**ns)
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
BASE=n.BASE;MEM=n.MEM
q=n.q
def w(u,p,value):u.mem_write(p,struct.pack('<I',value&0xffffffff))
def read32(u,p):return struct.unpack('<I',u.mem_read(p,4))[0]
def fresh():
    u=n.new();u.mem_map(MEM+0x40000,0x1C0000)
    root=MEM+0x50000;world=MEM+0xE0000
    u.mem_write(BASE+0x1FCA1E0,q(root));u.mem_write(root+0x85130,q(world));u.mem_write(root+0x85198,q(7))
    u.mem_write(world,bytes((i*13+7)&255 for i in range(0x2200)));w(u,BASE+0x18EB8B0,0x12345678)
    return u,root,world
def unchanged(u,world,before):
    assert bytes(u.mem_read(world,0x2200))==before and read32(u,BASE+0x18EB8B0)==0x12345678
def command_manager(u,capacity=64):
    m=MEM+0x1000;allocator=MEM+0x2000;vt=MEM+0x2100;queue=MEM+0x3000
    u.mem_write(m,q(allocator));u.mem_write(m+0x28,q(allocator));u.mem_write(m+0x30,q(0)+q(capacity)+q(queue if capacity else 0))
    u.mem_write(allocator,q(vt));u.mem_write(vt+0x48,q(BASE+0x1479B0));u.mem_write(vt+0x28,q(MEM+0x18000))
    return m,allocator,vt,queue
def queue_case(capacity):
    u,root,world=fresh();before=bytes(u.mem_read(world,0x2200));m,allocator,vt,queue=command_manager(u,capacity)
    state=MEM+0x4000;callback=MEM+0x7000;alloc_state=MEM+0x18100;allocations=[]
    u.mem_write(vt+0x40,q(alloc_state));u.mem_write(callback,bytes(0x40))
    def state_alloc(uc):
        assert uc.reg_read(UC_X86_REG_RDX)==0x4F0 and uc.reg_read(UC_X86_REG_R8)==16
        allocations.append('state0x4f0');n.ret(uc,state)
    def queue_alloc(uc):assert uc.reg_read(UC_X86_REG_RDX)==1024;allocations.append('queue1024');n.ret(uc,queue)
    result=n.execute(u,0x2DF990,(m,BASE+0x12AA8E0,0,callback),{alloc_state:state_alloc,MEM+0x18000:queue_alloc})
    assert n.u64(u,m+0x30)==1 and read32(u,queue)==0 and n.u64(u,queue+8)==state
    assert n.u64(u,state)==BASE+0x12DC5F8 and n.cstring(u,state+0x70)=='CSaveState'
    assert read32(u,state+0x470)==0 and n.u64(u,state+0x4E8)==0 and n.u64(u,callback+0x38)==0
    assert all(r in result['visited'] for r in (0x4263C0,0x8333D0,0x509EC0,0x509E10,0x3C6300,0x3D3400))
    unchanged(u,world,before)
    return {'case':'type0_queue_with_native_ctor_and_empty_callback','capacity':capacity,'result':'PASS','queued_type':0,'state_name':'CSaveState',
      'native_instructions':result['instructions'],'stubbed_boundaries':allocations,'world_rng_unchanged_in_case':True,
      'limit':'Queues only. Does not apply the scheduler command or execute UserStrategy pause/resume.'}
def finish_case(success,nonempty_error=False,capacity=64):
    u,root,world=fresh();before=bytes(u.mem_read(world,0x2200));m,allocator,vt,queue=command_manager(u,capacity)
    cache=MEM+0x8000;head=MEM+0x8800;u.mem_write(cache+0x10,q(head));u.mem_write(head,q(head)+q(head));w(u,cache+0x3EC,77)
    w(u,cache+0x3E8,56);w(u,cache+0x3F8,114);u.mem_write(BASE+0x2025318,q(cache))
    u.mem_write(BASE+0x201ED18,n.sso('mpckpt01.s14'));u.mem_write(BASE+0x201ED38,n.sso('fixture'))
    w(u,BASE+0x201ED10,0xffffffff);w(u,BASE+0x201EC2C,success)
    calls=[]
    def stub(label,value=0):
        def call(uc):calls.append(label);n.ret(uc,value)
        return call
    stubs={BASE+0xF690:stub('manager_getter',m),BASE+0x2EFF70:stub('error_text_getter',MEM+0xC000),BASE+0x187C10:stub('error_ui_context'),
           BASE+0x9C4F60:stub('error_text_length',4 if nonempty_error else 0),BASE+0x1D5170:stub('error_dialog'),MEM+0x18000:stub('queue_allocator',queue)}
    result=n.execute(u,0x465C10,(MEM+0x4000,),stubs)
    assert read32(u,queue)==1 and n.u64(u,queue+8)==0 and n.u64(u,m+0x30)==1
    assert n.text_at(u,BASE+0x201ED18)=='' and n.text_at(u,BASE+0x201ED38)=='' and n.i32(u,BASE+0x201ED10)==-1
    assert n.i32(u,cache+0x3EC)==-1 and read32(u,cache+0x3E8)==56 and read32(u,cache+0x3F8)==114
    assert ('error_dialog' in calls)==(not success and nonempty_error)
    assert read32(u,BASE+0x201EC2C)==success
    unchanged(u,world,before)
    return {'case':'native_save_completion','main_result':success,'error_text_nonempty':nonempty_error,'queue_capacity':capacity,'result':'PASS',
      'queued_type':1,'cache_invalidated':True,'pending_reset':True,'request_strings_cleared':True,'result_flag_preserved':True,
      'retained_cache_indices':[56,114],'stubbed_calls':calls,'native_instructions':result['instructions'],'world_rng_unchanged_in_case':True,
      'limit':'Native type1 queue append and native empty-cache clear run. Actual scheduler pop/underlying resume and error UI side effects are outside this case.'}
def phase_case(phase,top=True,done=True):
    u,root,world=fresh();before=bytes(u.mem_read(world,0x2200));m,allocator,vt,queue=command_manager(u)
    state=MEM+0x4000;stack=MEM+0x7000;u.mem_write(m+0x10,q(1));u.mem_write(m+0x20,q(stack));u.mem_write(stack,q(state if top else state+0x1000))
    w(u,state+0x470,phase);w(u,BASE+0x201EC2C,1);calls=[]
    def stub(label,value=0):
        def call(uc):calls.append(label);n.ret(uc,value)
        return call
    stubs={BASE+0xF690:stub('manager_getter',m),BASE+0x8351F0:stub('clock',12345),BASE+0x833CB0:stub('thread_construct'),BASE+0x834B60:stub('thread_start'),
           BASE+0x834460:stub('thread_done',int(done)),BASE+0x834BC0:stub('thread_join'),MEM+0x18200:stub('Sleep8')}
    u.mem_write(BASE+0x123C0E0,q(MEM+0x18200))
    result=n.execute(u,0x4AA650,(state,0x1234,0x5678,0x9abc),stubs)
    expected={0:1,1:2,2:3 if done else 2,3:4,9:9}[phase] if top else phase
    assert read32(u,state+0x470)==expected
    if top and phase==1:assert read32(u,BASE+0x201EC2C)==0 and calls[-2:]==['thread_construct','thread_start']
    else:assert read32(u,BASE+0x201EC2C)==1
    unchanged(u,world,before)
    return {'case':'native_save_update_phase','before_phase':phase,'top':top,'worker_done':done,'after_phase':expected,'result':'PASS',
      'raw_rax_at_return':hex(u.reg_read(UC_X86_REG_RAX)),'stubbed_calls':calls,'world_rng_unchanged_in_case':True,
      'limit':'Real Update/top-check/phase helpers; native OS/thread construction, timing/poll/join are explicit stubs.'}
def reset_case(nodes):
    u,root,world=fresh();before=bytes(u.mem_read(world,0x2200));freed=[]
    for i,(ptr,count) in enumerate(((0x1FCA330,0x1FCA338),(0x1FCA340,0x1FCA348))):
        head=MEM+0x9000+i*0x200;node=head+0x100;u.mem_write(BASE+ptr,q(head));u.mem_write(head,q(node if nodes else head)*3);u.mem_write(head+0x19,b'\x01')
        if nodes:u.mem_write(node,q(head)*3);u.mem_write(node+0x19,b'\0')
        u.mem_write(BASE+count,q(int(nodes)))
    def free(uc):freed.append(uc.reg_read(UC_X86_REG_RCX));n.ret(uc,0)
    result=n.execute(u,0x2F4B20,stubs={BASE+0x3A58B0:free})
    assert bytes(u.mem_read(BASE+0x1FCA320,2))==b'\x01\0'
    for ptr,count in ((0x1FCA330,0x1FCA338),(0x1FCA340,0x1FCA348)):
        head=n.u64(u,BASE+ptr);assert bytes(u.mem_read(head,24))==q(head)*3 and n.u64(u,BASE+count)==0
    assert len(freed)==2*nodes;unchanged(u,world,before)
    return {'case':'native_serialization_work_tables_reset','nonempty':bool(nodes),'result':'PASS','freed_nodes':len(freed),'global_flag':'1fca320 word=1',
      'zeroed_counts':['1fca338','1fca348'],'stubbed_boundaries':['heap free'] if nodes else [],'world_rng_unchanged_in_case':True}
def rng_case(intervene=False):
    u,root,world=fresh();stream=MEM+0xA000;writes=[];captured=[]
    w(u,stream+0x20,0);u.reg_write(UC_X86_REG_RBX,stream)
    def stream_write(uc):
        captured.append(read32(uc,uc.reg_read(UC_X86_REG_RDX)))
        if intervene:w(uc,BASE+0x18EB8B0,0xCAFEBABE)
        n.ret(uc,stream)
    def watch(uc,access,address,size,value,data):
        if address==BASE+0x18EB8B0:writes.append(value&0xffffffff)
    h=u.hook_add(UC_HOOK_MEM_WRITE,watch)
    result=n.execute(u,0x2F9A24,stubs={BASE+0x3A93E0:stream_write,BASE+0x2F9A72:lambda uc:n.ret(uc)})
    u.hook_del(h);assert captured==[0x12345678] and read32(u,BASE+0x18EB8B0)==0x12345678
    assert writes==[0x12345678] # API mem_write by the stub is not a native instruction event.
    return {'case':'native_world_serializer_rng_roundtrip','simulated_intervening_write':intervene,'result':'PASS','captured_rng':'0x12345678',
      'native_rng_store_values':[hex(x) for x in writes],'final_rng':'0x12345678','limit':'Only the native RNG serialization fragment. The intervening write is a synthetic race demonstration, not evidence a real race occurred.'}
def sidecar_case(which,opened=True,serialized=True):
    u,root,world=fresh();before=bytes(u.mem_read(world,0x2200));system=MEM+0x9000;object_=MEM+0xA000;opens=[];calls=[]
    u.mem_write(BASE+0x2025F50,q(system));u.mem_write(system+0x108,q(1))
    context=MEM+0xB000;interface=MEM+0xB100;vtable=MEM+0xB200;identity=MEM+0xB300
    u.mem_write(BASE+0x123CB28,q(MEM+0x18300));u.mem_write(context,q(interface));u.mem_write(interface,q(vtable));u.mem_write(vtable+0x10,q(MEM+0x18400));w(u,identity,391007908)
    def stub(label,value=0):
        def call(uc):calls.append(label);n.ret(uc,value)
        return call
    def ctor(uc):n.ret(uc,uc.reg_read(UC_X86_REG_RCX))
    def open_stream(uc):
        name=n.text_at(uc,uc.reg_read(UC_X86_REG_RDX));sp=uc.reg_read(UC_X86_REG_RSP)
        opens.append({'filename':name,'mode':uc.reg_read(UC_X86_REG_R8),'arg5':read32(uc,sp+0x28)})
        n.ret(uc,int(opened))
    stubs={BASE+0x3A5120:ctor,BASE+0x3A4FC0:ctor,BASE+0x3A90C0:open_stream,
      BASE+0x3A0870:stub('config_serialize',int(serialized)),BASE+0x39E060:stub('profile_serialize',int(serialized)),
      BASE+0x3A83D0:stub('stream_transform',1),BASE+0x3A6340:stub('stream_close',1),BASE+0x3A55D0:stub('stream_destroy'),BASE+0x3A56A0:stub('aux_destroy'),
      BASE+0x836760:stub('error_log_manager',object_),BASE+0x838100:stub('error_log'),MEM+0x18300:stub('steam_context',context),MEM+0x18400:stub('steam_user_id',identity)}
    result=n.execute(u,0x3A0690 if which=='config' else 0x39D500,(object_,),stubs)
    expected='configS_SC.s14' if which=='config' else 'prdataN.s14'
    assert len(opens)==1 and opens[0]['filename']==expected and opens[0]['mode']==0
    assert bool(u.reg_read(UC_X86_REG_RAX))==(opened and serialized)
    unchanged(u,world,before)
    return {'case':'native_sidecar_control_flow','which':which,'open_success':opened,'serializer_success':serialized,'result':'PASS','open_requests':opens,
      'stubbed_calls':calls,'native_instructions':result['instructions'],'world_rng_unchanged_in_case':True,
      'limit':'Runs native sidecar function/SSO/control flow; stream allocation/I/O/serializer and Steam context are explicit stubs. No sidecar file written.'}
cases=[]
for capacity in (0,64):cases.append(queue_case(capacity))
for args in ((1,False,64),(0,False,64),(0,True,64),(1,False,0)):cases.append(finish_case(*args))
for phase in (0,1,2,3,9):cases.append(phase_case(phase))
cases.extend((phase_case(2,done=False),phase_case(0,top=False)))
cases.extend((reset_case(0),reset_case(1),rng_case(),rng_case(True)))
for which in ('config','profile'):
    for opened,serialized in ((True,True),(False,True),(True,False)):cases.append(sidecar_case(which,opened,serialized))
report={'schema':'san14.save-return-lifecycle-shadow.v1','result':'PASS','cases':cases,'game_access':False,'save_files_written':False,
 'scope':'Copied native queue/constructor/empty callback, save update phases, completion+pop append+cache clear, serialization table reset, RNG fragment and sidecar control. Every external stub boundary is listed. No complete scheduler apply, world serialization, real storage or native thread execution.',
 'retired_entry_reenabled':False}
(ROOT/'save_return_lifecycle_shadow.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','cases':len(cases),'game_access':False,'save_files_written':False,'retired_entry_reenabled':False}))
