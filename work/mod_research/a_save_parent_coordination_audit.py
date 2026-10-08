"""Bounded offline parent/scheduler investigation for normal native Save.

This module accepts only a fixed historical byte image. It never discovers a
process, attaches, installs, saves, or grants a permit. Native calls run inside
Unicorn; OS task dispatch and selected UI/container services are named doubles.
"""
import ast
import hashlib
import struct
from pathlib import Path
from types import SimpleNamespace

import a_save_writer_scope_audit as prior

P = Path(__file__).resolve().parent
BASE, ARENA, STACK = prior.BASE, prior.ARENA, prior.STACK
need = prior.need
EXTRA = {'army_queue_transfer': (0x16BB70, 0x16BC9B),
         'army_queue_producer': (0x8D3D0, 0x8D442)}


def menu_source(raw):
    """Run existing menu control flow, excluding both historical runners.

    Load only the two class ASTs. Inject the already verified fixed image; do
    not import disasm_chained or its old implicit archive lookup/CLI runner.
    All original lifecycle/UI/container doubles stay explicitly in scope.
    """
    import unicorn
    from unicorn import x86_const
    ns = {k: getattr(unicorn, k) for k in ('Uc', 'UC_ARCH_X86', 'UC_MODE_64', 'UC_HOOK_CODE')}
    ns.update({k: getattr(x86_const, k) for k in dir(x86_const) if k.startswith('UC_')})
    ns.update(BASE=0x7FF749440000, MEM=0x300000000, STOP=0x3000F0000,
              d=SimpleNamespace(image=raw), struct=struct, q=lambda n: struct.pack('<Q', n))
    for filename, classname in (('private_checkpoint_save_apply_regression.py', 'Harness'),
                                ('save_return_menu_regression.py', 'MenuHarness')):
        tree = ast.parse((P/filename).read_text(encoding='utf-8'), filename)
        nodes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == classname]
        need(len(nodes) == 1, 'one pinned class definition required')
        exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, 'exec'), ns)
    h = ns['MenuHarness']()
    stacks = [h.stack_names(), h.open_config(), h.open_selection(), h.confirm_empty()]
    expected = ['Root', 'Motor', 'Game', 'Strategy', 'User', 'CConfigDlgState', 'Save']
    need(stacks[-1] == expected, 'normal menu must retain Config parent')
    need(not any(c['state'] == 'Game' and c['method'] == 'pause' for c in h.callbacks),
         'normal menu path did not pause the lower Game state via its pause callback')
    return dict(case='actual-manual-menu-parent-stack', result='PASS', stacks=stacks,
        native_instruction_count=len(h.visits), callbacks=h.callbacks,
        user_pause_callback_invoked=any(c['state']=='User' and c['method']=='pause' for c in h.callbacks),
        lifecycle_callbacks_are_doubles=True, save_constructor_is_double=True,
        game_pause_not_invoked_in_this_queue_path=True, full_parent_coordination_proved=False)


class FrameVM(prior.VM):
    """Archived scheduler plus archived Game/User/Save bodies in one VM.

    The scheduler's OS dispatch service calls a selected archived state Update
    synchronously on this fixture's CPU, using a private call continuation.
    This is deliberately NOT an OS worker-pool/concurrency implementation.
    Army and Save OS start/done/join are distinct object-address keyed doubles.
    """
    def __init__(self, raw, state_names, registry_lock=False):
        super().__init__(raw)
        self.names = state_names
        self.states = [ARENA+0x10000+i*0x1000 for i in range(len(state_names))]
        self.game, self.user, self.save = self.states[2], self.states[4], self.states[-1]
        self.put(self.manager+0x10, len(self.states))
        for i, state in enumerate(self.states):
            self.put(self.vector+i*8, state); self.put(state+0x50, 0)
        self.put(self.save+0x470, 0, 4)
        self.frame = 0; self.log = []; self.done = {'army': False, 'save': False}
        self.started = {'army': 0, 'save': 0}; self.contexts = []; self.targets = {}
        self.pending_index, self.working_index = ARENA+0x154000, ARENA+0x154100
        self.heads, self.counts = ARENA+0x15A000, ARENA+0x15B000
        self.working_node = ARENA+0x15C000
        self.put(self.pending_index, 3, 4); self.put(self.working_index, 4, 4)
        self.put(self.unit_manager+0x18, self.pending_index)
        self.put(self.unit_manager+8, self.working_index)
        self.put(self.unit_manager+0x90,0,4)
        self.put(BASE+0x201D3A8, ARENA+0x15D000)
        self.put(BASE+0x201D3B0, self.heads); self.put(BASE+0x201D3C8, self.counts)
        self.put(BASE+0x201D3E0, 8, 4); self.put(BASE+0x201D370, int(registry_lock), 4)
        self.setup_scheduler(); self.setup_game(); self.setup_threads(); self.setup_queues()

    def step(self, machine, address, size, unused):
        if address not in self.handlers and address not in self.stops and address != prior.STOP:
            rva = address-BASE
            if any(a <= rva < z for a,z in EXTRA.values()):
                self.visits.append(rva); return
        super().step(machine, address, size, unused)

    def note(self, event, **fields):
        self.log.append(dict(seq=len(self.log)+1, frame=self.frame, event=event, **fields))

    def pending(self, count=1):
        self.put(self.heads+3*8, self.node if count else 0)
        self.put(self.counts+3*8, count)
        self.put(self.node, self.unit); self.put(self.node+8, 0)

    def setup_queues(self):
        def clear_by_index(index):
            need(index in (3,4), 'known fixture army list only')
            self.put(self.heads+index*8, 0); self.put(self.counts+index*8, 0)
        def clear_working():
            need(self.reg('RCX') == self.unit_manager, 'transfer clears working manager list')
            clear_by_index(4); self.note('working_clear_service'); self.ret()
        def clear_registry():
            need(self.reg('RCX') == BASE+0x201D3A0, 'registry owner')
            index = self.reg('RDX'); clear_by_index(index)
            self.note('registry_clear_service', index=index); self.ret()
        def append():
            need(self.reg('RCX') == BASE+0x201D3A0, 'registry append owner')
            index = self.reg('RDX'); need(index in (3,4), 'append index')
            node = self.node if index == 3 else self.working_node
            need(self.get(self.counts+index*8) == 0, 'one-element bounded list backend')
            self.put(self.heads+index*8, node); self.put(self.counts+index*8, 1)
            self.put(node+8, 0); self.note('registry_append_service', index=index); self.ret(node)
        self.model(0x1FEAC0, 'working-list clear container double', clear_working)
        self.model(0x16C50, 'pending-list clear registry double', clear_registry)
        self.model(0x172D0, 'one-node registry allocation double', append)

    def setup_scheduler(self):
        self.worker = self.pool+8
        self.put(self.worker+0x10, self.control); self.put(self.worker+0x78, 0, 4)
        vt = BASE+0x12F2440
        def clone():
            dest=self.reg('RDX'); self.m.mem_write(dest, bytes(self.m.mem_read(self.reg('RCX'),0x40))); self.ret(dest)
        def transfer():
            self.m.mem_write(self.reg('RDX'), bytes(self.m.mem_read(self.reg('RCX'),0x40))); self.ret()
        self.put(vt,BASE+0x2210400); self.put(vt+0x20,BASE+0x2210500)
        self.handlers[BASE+0x2210400]=('callable clone double',clone)
        self.handlers[BASE+0x2210500]=('callable destruction double',lambda:self.ret())
        self.model(0x160F0,'callable transfer storage double',transfer)
        self.model(0x145B20,'initialized Root pool lookup double',value=self.pool)
        self.model(0x834EF0,'Root wait service double',lambda:(self.note('root_wait'),self.ret())[1])
        for slot,label in ((0x123C328,'enter'),(0x123C0D8,'leave')):
            target=BASE+0x2210000+slot%0x1000; self.put(BASE+slot,target)
            def lock(label=label):
                self.note('lock_'+label, object=hex(self.reg('RCX'))); self.ret()
            self.handlers[target]=(label+' critical-section service double',lock)
        self.handlers[BASE+0x2210700]=('state Update dispatch continuation double',self.update_return)

    def setup_game(self):
        self.put(BASE+0x2025318,self.cache); self.put(self.cache+8,1,4); self.put(self.cache+0x3F0,1,4)
        dummy,ui,uvt=ARENA+0x157000,ARENA+0x158000,ARENA+0x159000
        self.put(BASE+0x201D4C8,dummy); self.put(dummy+0x98,0)
        self.put(ui,uvt); self.put(uvt+0x18,BASE+0x2210300)
        self.handlers[BASE+0x2210300]=('covered global UI service double',lambda:self.ret())
        for at,val,label in ((0x1C1A70,0,'special UI absent'),(0xB11E0,self.unit_manager,'army singleton'),
                (0x194A90,ui,'UI singleton'),(0x173F0,dummy,'cursor'),(0x5086A0,dummy,'save/menu service'),
                (0x15FAA0,self.effects,'effects singleton'),(0x509460,0,'named state absent'),
                (0x3ECFD0,dummy,'scene effect'),(0x3ECEB0,dummy,'scene effect')):
            self.model(at,label+' lookup double',value=val)
        for at in (0x3AD580,0x8271A0,0x4E8C90,0x1786B0,0x178FE0,0x177E60):
            self.model(at,'unresolved peripheral Game callee double')
        self.model(0x3FA820,'covered Game panel service double')
        self.model(0x8351F0,'clock service double',value=123)
        self.put(self.effects+0x38,0)
        sleep=BASE+0x2210100; self.put(BASE+0x123C0E0,sleep)
        self.handlers[sleep]=('Save polling Sleep service double',lambda:self.ret())

    def kind(self, obj):
        return {self.worker+8:'root', self.unit_manager+0x20:'army', self.save+0x478:'save'}.get(obj)

    def setup_threads(self):
        def construct():
            obj=self.reg('RCX'); kind=self.kind(obj); need(kind in ('army','save'),'distinct native thread object')
            target=self.reg('RDX')-BASE
            need(target=={'army':0x16C2C0,'save':0x508CA0}[kind],'native worker source')
            self.targets[obj]=target; self.note(kind+'_construct', object=hex(obj), target=hex(target)); self.ret()
        def start():
            obj=self.reg('RCX'); kind=self.kind(obj); need(kind is not None,'unrecognized OS start')
            if kind == 'root':
                state=self.get(self.manager+0x48); name=self.names[self.states.index(state)]
                self.note('update_dispatch', state=name)
                target={'Game':0x3F8140,'User':0x3F9B00,'Save':0x4AA650}.get(name)
                if target is None: self.note('other_update_double',state=name); self.ret(); return
                # A synthetic OS dispatch body makes a correctly aligned call
                # to actual archived Update; it does not execute a worker loop.
                sp=self.reg('RSP'); self.contexts.append((sp,name))
                need((sp-0x28)%16==8,'archived Update fixture entry stack alignment')
                self.put(sp-0x28, BASE+0x2210700); self.set('RSP',sp-0x28)
                self.set('RCX',state); self.set('RDX',0); self.set('R8',0); self.set('R9',0)
                self.set('RIP',BASE+target); return
            need(obj in self.targets,'constructed object required')
            self.started[kind]+=1; self.done[kind]=False
            self.note(kind+'_start',object=hex(obj),army_active=self.get(self.unit_manager+0x90,4),
                      pending=self.get(self.counts+3*8),working=self.get(self.counts+4*8))
            self.ret()
        def done():
            kind=self.kind(self.reg('RCX')); need(kind is not None,'unrecognized done object')
            value=1 if kind=='root' else int(self.done[kind])
            self.note(kind+'_done_query',value=value); self.ret(value)
        def join():
            kind=self.kind(self.reg('RCX')); need(kind in ('army','save') and self.done[kind],'only supplied completed join')
            self.note(kind+'_join_service'); self.ret()
        self.model(0x833CB0,'OS constructor service double',construct)
        self.model(0x834B60,'OS dispatch/start service double',start)
        self.model(0x834460,'OS done service double',done)
        self.model(0x834BC0,'OS join service double',join)

    def update_return(self):
        sp,name=self.contexts.pop(); need(self.reg('RSP') == sp-0x20,'balanced archived Update return')
        self.note('update_return',state=name,army_active=self.get(self.unit_manager+0x90,4),
                  save_phase=self.get(self.save+0x470,4))
        self.set('RSP',sp); self.ret()

    def tick(self):
        self.frame+=1
        def setup():
            self.set('R15',self.manager); self.set('RBP',STACK+0x300)
            self.put(STACK+0x300-0x78,0); self.put(STACK+0x38,0)
        self.run(0x50B441,setup=setup,stop=0x50B669)
        need(not self.contexts and self.get(self.pool+0x208,4)==0,'no unfinished Root dispatch in fixture')
        dispatch=[r['state'] for r in self.log if r['frame']==self.frame and r['event']=='update_dispatch']
        need(dispatch==self.names,'all seven states execute in archived bottom-to-top order')


def frames_case(raw, names, mode, locked=False):
    v=FrameVM(raw,names,locked)
    if mode != 'empty': v.pending()
    v.tick(); need(v.get(v.save+0x470,4)==1,'first Save frame only advances to phase1')
    if mode in ('join-then-restart','join-without-producer'):
        v.done['army']=True
        # Keep Save at phase0 for this extra fixture frame. This explicitly
        # models a prior completed drain, not a natural Save-state transition.
        v.put(v.save+0x470,0,4); v.tick()
        need(v.get(v.unit_manager+0x90,4)==0,'actual join branch clears active')
        if mode=='join-then-restart':
            v.run(0x8D3D0,(v.unit_manager,v.unit))
            need(v.get(v.node)==v.unit and v.get(v.counts+3*8)==1,'actual producer enqueues after prior join')
    v.tick()
    need(v.get(v.save+0x470,4)==2 and v.started['save']==1,'actual Save starts regardless of modeled army completion')
    active=v.get(v.unit_manager+0x90,4)
    need(active==int(mode in ('held-army','join-then-restart')),'expected actual army active publication')
    rows=[r for r in v.log if r['event']=='save_start']; need(len(rows)==1,'single Save start')
    if mode=='held-army':
        need(any(r['event']=='army_done_query' and r['value']==0 for r in v.log),'native army pending branch exercised')
        need(not any(r['event']=='army_join_service' for r in v.log),'no forged join of held worker')
        game_return=[r for r in v.log if r['event']=='update_return' and r['state']=='Game' and r['frame']==2]
        need(len(game_return)==1 and game_return[0]['seq']<rows[0]['seq'] and game_return[0]['army_active']==1,
             'actual Game Update returns with army active before separate Save start')
    if mode=='join-then-restart': need(v.started['army']==2,'second actual start after real producer branch')
    if mode!='empty':
        need({0x16BB70,0x16BC01,0x16BC74}<=set(v.visits),'actual queue copy/store/clear-call must execute')
        need(v.get(v.working_node)==v.unit and v.get(v.counts+3*8)==0,'native transfer stores same army pointer and clears pending')
    return v.row('normal-parent-frames-'+mode+'-lock'+str(int(locked)),timeline=v.log,
        actual_native_queue_transfer=mode!='empty',save_start_army_active=rows[0]['army_active'],
        worker_start_counts=v.started,fixture_phase_reset=mode.startswith('join-'),
        modeled_os_dispatch=True,actual_os_threads=False,world_serializer_executed=False,
        native_coordination_absence_proved=False,production_permit=False)


def static_case(raw):
    import capstone
    d=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
    anchors={0x50B59C:'call 0x834b60',0x50B5A5:'call 0x834ef0',
      0x50B5AE:'call 0x834460',0x50B5F5:'test eax, eax',0x50B603:'mov qword ptr [rcx + 0x50], rbx',
      0x50B638:'movsxd rax, r14d',0x50B63B:'cmp qword ptr [r15 + 0x30], rax',
      0x50B63F:'jne 0x50b669',0x50B646:'add rdx, 8',
      0x4AA6B7:'mov dword ptr [rbx + 0x470], 1',0x4AA6C1:'call 0x8351f0',
      0x4AA6B2:'jmp 0x4da320',0x4DA33E:'lea rdx, [rip + 0x2e95b]',
      0x4DA366:'call 0x834b60',0x4DA37A:'mov dword ptr [rdi + 0x470], 2',
      0x16CB51:'je 0x16cbe5',0x16CB5B:'call 0x834bc0',0x16CB60:'mov dword ptr [rdi + 0x90], 0',
      0x16CB9A:'call 0x16bb70',0x16CBD6:'call 0x834b60',0x16CBDB:'mov dword ptr [rdi + 0x90], 1',
      0x16BB7E:'call 0x1feac0',0x16BC01:'mov qword ptr [rax], rdi',0x16BC74:'call 0x16c50',
      0x508CE4:'call 0x2ee740',0x2EE866:'call 0x2f7a10'}
    checked=[]
    for at,want in anchors.items():
        i=next(d.disasm(raw[at:at+16],at)); text=i.mnemonic+' '+i.op_str
        need(text==want,'source anchor mismatch '+hex(at))
        checked.append(dict(rva=hex(at),instruction=text,sha256=hashlib.sha256(raw[at:at+i.size]).hexdigest()))
    return dict(case='parent-scheduler-and-thread-identity-anchors',result='PASS',anchors=checked,
        note='Root waits for each state task, or yields; separate army thread lifetime does not equal Game.Update lifetime. No transitive lock absence claim.')


def queue_barrier_case(raw,names):
    v=FrameVM(raw,names); v.put(v.save+0x470,1,4)
    def publish():
        v.note('fixture_pending_state_transition'); v.put(v.manager+0x30,1); v.ret()
    v.model(0x3FA820,'explicit synthetic pending-transition producer',publish)
    def setup():
        v.set('R15',v.manager); v.set('RBP',STACK+0x300)
        v.put(STACK+0x300-0x78,0); v.put(STACK+0x38,0)
    v.frame=1; v.run(0x50B441,setup=setup,stop=0x50B669)
    dispatch=[r['state'] for r in v.log if r['event']=='update_dispatch']
    need(dispatch==names[:3] and v.started['save']==0 and v.get(v.save+0x470,4)==1,
         'native pending-transition comparison must stop before Save')
    return v.row('native-state-transition-barrier-positive-control',timeline=v.log,
        native_queue_comparison_executed=True,pending_transition_producer_is_double=True,
        save_skipped_this_frame=True,production_permit=False)


def observation_spec(raw):
    """A precise next diagnostic pack, not an observer or runtime instruction.

    Root's existing four-point Save-read/army-body pack remains the first test.
    This second pack can distinguish paired join from two independent starts;
    read fields before instructions, retain debugger identity/loss guarantees.
    """
    events=(
      ('army_join_call',0x16CB5B,'manager=RDI; RCX=manager+20h; RSP is pre-call; active=[manager+90h]'),
      ('army_join_return',0x16CB60,'same thread/RSP/RDI; active is still pre-clear, zero publication is next instruction'),
      ('army_start_call',0x16CBD6,'manager=RDI; RCX=manager+20h; active still zero until 16CBDB; capture pending/working list count with read errors'),
      ('save_start_call',0x4DA366,'save=RDI; RCX=save+478h; phase=[save+470h] should be1; army manager fixed base+1A24CF0; snapshot active/pending/working'),
    )
    return dict(schema='san14.a-save-parent-coordination.observation.v1',
        profile=[dict(event=n,rva=a,bytes16=raw[a:a+16].hex(),fields=f) for n,a,f in events],
        requirements=[
          'Existing Save-scope/army-body observation is first; do not replace it with start-only evidence.',
          'Use one new fully bound process/run with all existing/new threads observed and contiguous event sequence.',
          'Pair join call/return by tid, RSP and manager; return observation precedes native active clear.',
          'A start-call observation is only an attempted dispatch, not worker entry or completed start.',
          'For source queue reads validate registry pointer, list index bounds and every dereference; snapshot failure is explicit incomplete evidence.',
          'Pending index is u32[[manager+18h]], working index is u32[[manager+8h]]; counts are qword[[base+201D3C8h]+index*8], bounded by u32[base+201D3E0h]. These are observations, not locks.',
          'A prior paired join can be followed by another start; do not convert zero active or a paired join to a retained lease.',
          'Separate four-breakpoint runs cannot establish a single causal ordering across runs.',
          'No records prove absent external producers, unknown UI descendants or global writer exclusion.'
        ],observer_implemented=False,production_permit=False,game_access=False)
