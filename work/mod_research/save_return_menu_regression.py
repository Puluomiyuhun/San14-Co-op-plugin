"""Offline native menu/save control flow and real queue apply regression.

No process opening, game DLL loading, or live interfaces. Copied instructions
execute only in Unicorn; lifecycle/UI/storage dependencies are synthetic.
"""
from pathlib import Path
from datetime import datetime
import ast,json,struct,hashlib
P=Path(__file__).resolve().parent
# Load only definitions from the existing reviewed harness. Its historical
# top-level test runner is deliberately excluded and never writes old evidence.
source=P/'private_checkpoint_save_apply_regression.py'
tree=ast.parse(source.read_text(encoding='utf8'),str(source));nodes=[]
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='rows' for t in node.targets):break
    nodes.append(node)
ns={'__file__':str(source),'__name__':'save_return_menu_harness'}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
Harness=ns['Harness'];BASE=ns['BASE'];MEM=ns['MEM'];STOP=ns['STOP'];d=ns['d']
for k,v in ns.items():
    if k.startswith('UC_'):globals()[k]=v

class MenuHarness(Harness):
    def __init__(self):
        super().__init__()
        self.config=MEM+0x19000;self.selection=MEM+0x1A000
        self.toolbar=MEM+0x60000;self.config_dialog=MEM+0x62000;self.slot_dialog=MEM+0x64000
        self.cache=MEM+0x66000;self.header=MEM+0x68000;self.filename=MEM+0x69000
        self.names.update({self.config:'CConfigDlgState',self.selection:'CSaveLoadState'})
        self.putq(self.user+0x480,self.toolbar);self.put32(self.toolbar+0x1B0,6)
        self.putq(BASE+0x2025318,self.cache);self.put32(self.cache+0x3EC,0xFFFFFFFF)
        allocfn=self.readq(self.allocvt+0x40);self.stubs[allocfn]=self.allocate_state
        self.stubs[BASE+0x1C1A70]=lambda:self.ret(MEM+0x6A000)
        self.stubs[BASE+0x1C0CD0]=lambda:self.ret(0)
        self.stubs[BASE+0x3A29E0]=lambda:self.ret(0)
        self.stubs[BASE+0x3A2BF0]=lambda:self.ret(0)
        self.stubs[BASE+0x3A2700]=lambda:self.ret(0)
        self.stubs[BASE+0x836710]=lambda:self.ret(0)
        self.stubs[BASE+0x2F1650]=lambda:self.ret(self.filename)
        self.u.mem_write(self.filename,b'svdexSC49.s14\0')
        # Body+caption fixture, no real windows or handlers.
        self.putq(self.config+0x470,self.config_dialog)
        self.footprints=[]
    def allocate_state(self):
        size=self.reg(UC_X86_REG_RDX)
        self.ret({0x490:self.config,0x4C0:self.selection,0x4F0:self.save}[size])
    def read32(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
    def set_callback_vtable(self,state):
        # Actual constructors/name/callback transfer run first. Replace only
        # lifecycle callbacks to isolate this task from the root's UI study.
        vt=MEM+0x70000+(state-self.config)
        self.putq(state,vt)
        for offset,label in ((0,'destroy'),(8,'initialize'),(0x10,'finalize'),(0x18,'resume'),(0x20,'pause'),(0x58,'enter_event'),(0x60,'exit_event')):
            self.stub(vt,offset,lambda label=label:self.callback(label),label)
        self.put32(state+0x6C,3)
        self.putq(state+0x60,MEM+0x50000)
    def pending_kind(self):
        assert self.readq(self.manager+0x30)==1
        return self.read32(self.readq(self.manager+0x40))
    def open_config(self):
        self.run(0x3FA820,args=(self.user,))
        assert self.pending_kind()==0
        assert self.read32(self.user+0x470)==2 and self.read32(self.toolbar+0x1B0)==0
        assert self.readq(self.config+0x48)==self.config+0x10
        assert self.readq(self.config+0x10)==BASE+0x12CE580
        assert self.readq(self.config+0x18)==self.user
        self.set_callback_vtable(self.config)
        return self.apply()
    def open_selection(self):
        self.putq(self.config+0x470,self.config_dialog);self.put32(self.config_dialog+0x168,1)
        self.run(0x79F8C0,args=(self.config,))
        assert self.pending_kind()==0
        assert self.read32(self.config+0x488)==1
        assert self.read32(self.config_dialog+0x168)==0
        assert self.read32(self.cache+8)==1 and self.read32(self.cache+0x3F0)==1
        assert self.readq(self.selection+0x48)==0 # Empty return callback.
        self.set_callback_vtable(self.selection)
        self.putq(self.selection+0x470,self.slot_dialog);self.put32(self.slot_dialog+0x170,49)
        self.u.mem_write(self.selection+0x480,b'fixture\0')
        return self.apply()
    def confirm_empty(self):
        self.run(0x4AA200,args=(self.selection,))
        assert self.pending_kind()==2
        assert self.read32(BASE+0x201ED10)==49
        assert bytes(self.u.mem_read(BASE+0x201ED18,13))==b'svdexSC49.s14'
        assert bytes(self.u.mem_read(BASE+0x201ED38,7))==b'fixture'
        assert self.read32(self.cache+0x3EC)==0xFFFFFFFF
        self.set_callback_vtable(self.save)
        return self.apply()
    def existing_slot(self,accept):
        name=b'svdexSC48.s14'
        self.u.mem_write(self.header+0x128,name.ljust(16,b'\0')+struct.pack('<QQ',len(name),15))
        self.stubs[BASE+0x836710]=lambda:self.ret(self.header)
        self.stubs[BASE+0x835D30]=lambda:self.ret(1)
        self.stubs[BASE+0x3A6C20]=lambda:self.ret(MEM+0x6B000)
        self.stubs[BASE+0x1C0CF0]=lambda:self.ret(MEM+0x6B100)
        self.stubs[BASE+0x2D54E0]=lambda:self.ret(0)
        textvt=MEM+0x6C000;self.putq(BASE+0x18CBF00,textvt)
        self.stub(textvt,8,lambda:self.ret(MEM+0x6B200),'localized_text')
        for address in (0x187C10,0x188970,0x1F65D0):self.stubs[BASE+address]=lambda:self.ret(1)
        self.stubs[BASE+0x2A1DB0]=lambda:self.ret(1 if accept else 0)
        self.run(0x4AA200,args=(self.selection,))
        if accept:
            assert self.pending_kind()==2
            assert bytes(self.u.mem_read(BASE+0x201ED18,len(name)))==name
            assert self.read32(BASE+0x201ED10)==49
            self.set_callback_vtable(self.save)
            return self.apply()
        assert self.readq(self.manager+0x30)==0
        assert self.read32(self.slot_dialog+0x170)==0xFFFFFFFF
        return self.stack_names()
    def close_config(self):
        # Actual Config update cancel branch queues a pop. The UI input query
        # alone is synthetic; all queue/event/apply stack mutations are native.
        self.stubs[BASE+0x3A2BF0]=lambda:self.ret(1)
        self.run(0x79F8C0,args=(self.config,));assert self.pending_kind()==1
        # Execute exact result/callback tail independently; no expensive UI
        # destruction is inferred harmless. Config callback invoke is real ret.
        self.run(0x79E627,BASE+0x79E655,setup=lambda sp:(self.u.reg_write(UC_X86_REG_RBX,self.config),self.u.reg_write(UC_X86_REG_RSI,0)))
        assert self.read32(self.config+8)==0xB
        return self.apply()

rows=[]
h=MenuHarness();sequence=[h.stack_names(),h.open_config(),h.open_selection(),h.confirm_empty(),h.complete(),h.close_config()]
expected=[['Root','Motor','Game','Strategy','User'],
          ['Root','Motor','Game','Strategy','User','CConfigDlgState'],
          ['Root','Motor','Game','Strategy','User','CConfigDlgState','CSaveLoadState'],
          ['Root','Motor','Game','Strategy','User','CConfigDlgState','Save'],
          ['Root','Motor','Game','Strategy','User','CConfigDlgState'],
          ['Root','Motor','Game','Strategy','User']]
assert sequence==expected,sequence
assert not any(x['state']=='User' and x['method'] in ('destroy','finalize') for x in h.callbacks)
assert any(x['state']=='CSaveLoadState' and x['method']=='destroy' for x in h.callbacks)
assert h.read32(h.user+0x470)==2
rows.append({'name':'normal_manual_menu_empty_slot','result':'PASS','stack_sequence':sequence,
             'queue_kinds':[0,0,2,1,1],'user_phase2_under_stub_lifecycle':True,
             'native_fields':{'toolbar_1b0':0,'config_save_started_488':1,'config_return_code_8':11,
                              'cache_mode_8':1,'cache_secondary_3f0':1,'pending_load_3ec':-1},
             'callbacks':h.callbacks,'instruction_count':len(h.visits)})

# Verify selection Update refuses to submit when it is not the exact top.
h=MenuHarness();h.open_config();h.open_selection();h.putq(h.stack+6*8,h.config)
h.run(0x4AA200,args=(h.selection,));assert h.readq(h.manager+0x30)==0
rows.append({'name':'selection_not_top_no_queue','result':'PASS','native_exact_top_check':True})

for accept in (True,False):
    h=MenuHarness();h.open_config();h.open_selection();after=h.existing_slot(accept)
    assert after[-1]==('Save' if accept else 'CSaveLoadState')
    assert h.read32(h.cache+0x3EC)==0xFFFFFFFF
    rows.append({'name':'existing_slot_confirm_'+('accept' if accept else 'decline'),'result':'PASS',
                 'after':after,'game_file_overwritten':False,'confirmation_response_stub':accept,
                 'source_name_from_cached_header_not_slot_formatter':accept,
                 'decline_resets_dialog_selected_slot':not accept,
                 'pending_load_unchanged':True,'instruction_count':len(h.visits)})

stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f');path=P/f'save_return_menu_regression_{stamp}.json'
report={'schema':'san14.save-return-menu-regression.v1','result':'PASS','cases':rows,
        'captured_image_sha256':hashlib.sha256(d.image).hexdigest(),
        'game_access':False,'native_export_success':False,'live_execution_allowed':False,
        'native_executed':['3FA820 toolbar branch6 and action reset','3E0170 Config push queue',
                           '792650 Config constructor','403530 callback clone and empty invoke58E520',
                           '79F8C0 save menu branch and explicit cancel branch','411980 SaveLoad push queue',
                           '426320 SaveLoad constructor','4AA200 empty/existing-slot requests, decline and exact-top check',
                           '426930 request copy','2FC750 binder and actual short-string helpers',
                           '412520 Save replacement queue','509FE0 event and apply fragments',
                           '465C10 successful completion and10A60 pop','79E627..79E655 Config return-code/callback tail'],
        'synthetic_dependencies':['state/heap allocation','Save constructor','all state lifecycle/UI callbacks during apply',
                                  'cache invalidation and slot lookup','world exists/ruler lookup','empty-slot filename formatter',
                                  'UI input polling, localized text and confirmation answer','temporary list/vector backend','worker success status'],
        'limits':['UI state initialization and destruction are not executed; selected widgets are synthetic',
                  'Saving serializer/storage/worker do not run','User real lifecycle is not covered',
                  'Only menu control-flow and request/stack semantics are tested; no complete checkpoint equivalence claim',
                  'No new live entry and no changes to retired pilots']}
with path.open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
print(json.dumps({'result':'PASS','cases':len(rows),'evidence':str(path),'game_access':False}))
