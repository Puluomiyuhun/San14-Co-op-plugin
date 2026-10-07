"""Execute real User callbacks inside the isolated queue/apply harness.

Peripheral UI/services are explicit stubs, never live objects. This narrows the
old all-lifecycle-stub gap; it does NOT authorize a native export or assert that
UI callees have no business side effects.
"""
from pathlib import Path
from datetime import datetime
import hashlib, json, struct
from save_return_shadow_base import Harness, ROOT, BASE, MEM, STOP
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import *


class UserHarness(Harness):
    def __init__(self, selected=False, selection_valid=False, panel_visible=True, context_pointer_present=False):
        super().__init__()
        self.ui_calls=[]; self.writes=[]
        self.control=MEM+0x54000; self.cursor=MEM+0x55000
        self.coordinator=MEM+0x56000; self.panel=MEM+0x57000
        self.toolbar=MEM+0x58000; self.popup=MEM+0x59000
        self.effects=MEM+0x5a000; self.selection=MEM+0x5b000
        self.config=MEM+0x5c000; self.scene=MEM+0x5d000
        self.command_source=MEM+0x5e000
        self.user_vt=self.readq(self.user)
        for offset,rva in ((0x18,0x3F5530),(0x20,0x3F5920),(0x58,0x3F7710),(0x60,0x3F7A70)):
            self.putq(self.user_vt+offset,BASE+rva)
        self.putq(self.user+0x478,self.toolbar)
        self.putq(self.states[2]+0x480,self.panel)
        for i,obj in enumerate((self.panel,self.toolbar,self.popup,self.selection)):
            vt=MEM+0x60000+i*0x1000;self.putq(obj,vt)
            for offset in (0x18,0x38,0x40,0xC0,0x130,0x138,0x140):
                self.stub(vt,offset,lambda offset=offset:self.ui_vcall(offset),'ui_boundary')
        self.putq(self.toolbar+0x98,self.popup)
        self.put32(self.toolbar+0x88,0xffffffff)
        self.put32(self.panel+0x40,3 if panel_visible else 0)
        self.putq(self.user+0x4a8,self.selection if selected else 0)
        self.selection_valid=selection_valid
        self.put32(self.cursor+0x13c,1)
        self.put32(self.control+0x28,0)
        self.put32(self.coordinator,1)
        self.put32(self.config+0xc,3)
        self.putq(BASE+0x201EC70,MEM+0x5f000 if context_pointer_present else 0)
        self.put32(MEM+0x5f000,0)  # nonnull context with inactive flag is also ordinary
        returns={0x161170:self.control,0xF720:self.coordinator,0x173F0:self.cursor,
                 0x3ECFD0:self.effects,0x17A480:self.command_source,0x145A90:self.config,
                 0x194A90:self.scene,0xF570:self.scene,0x1C1A70:0,0x2F5F70:0}
        for rva,value in returns.items():self.stubs[BASE+rva]=lambda value=value:self.ret(value)
        self.stubs[BASE+0x509460]=lambda:self.ret(self.states[2])
        self.stubs[BASE+0x7842E0]=lambda:self.ret(1) # UI registry contains toolbar
        self.stubs[BASE+0x16BFF0]=lambda:self.ret(0) # no competing modal/UI group
        for rva in (0x7ADAC0,0x1A8540,0x78CA80,
                    0x788190,0x3FDBB0,0x7A32D0,0x337BB0):
            self.stubs[BASE+rva]=lambda rva=rva:self.ui_service(rva)
        self.u.hook_add(UC_HOOK_MEM_WRITE,self.record_write)

    def record_write(self,u,access,address,size,value,data):
        if not MEM+0xEE000<=address<MEM+0xF1000:
            self.writes.append({'rva':hex(self.reg(UC_X86_REG_RIP)-BASE),
                                'address':hex(address),'size':size,'value':hex(value&((1<<(size*8))-1))})

    def ui_vcall(self,offset):
        self.ui_calls.append({'kind':'virtual','offset':hex(offset),'this':hex(self.reg(UC_X86_REG_RCX)),
                              'arg':hex(self.reg(UC_X86_REG_RDX))})
        result=int(self.selection_valid) if self.reg(UC_X86_REG_RCX)==self.selection and offset==0x18 else 1
        self.ret(result)

    def ui_service(self,rva):
        self.ui_calls.append({'kind':'service','rva':hex(rva),'this':hex(self.reg(UC_X86_REG_RCX)),
                              'arg':hex(self.reg(UC_X86_REG_RDX))})
        self.ret(1)

    def snapshot(self):
        return {'stack':self.stack_names(),
                'user_phase':struct.unpack('<I',self.u.mem_read(self.user+0x470,4))[0],
                'pending_menu':struct.unpack('<i',self.u.mem_read(self.toolbar+0x88,4))[0],
                'advance_game':struct.unpack('<I',self.u.mem_read(self.states[2]+0x47c,4))[0],
                'advance_panel':struct.unpack('<I',self.u.mem_read(self.panel+0x1b0,4))[0],
                'control_pause':struct.unpack('<I',self.u.mem_read(self.control+0x28,4))[0],
                'cursor_enabled':struct.unpack('<I',self.u.mem_read(self.cursor+0x13c,4))[0],
                'coordinator_flags':struct.unpack('<H',self.u.mem_read(self.coordinator,2))[0],
                'selected':[hex(self.readq(self.user+x)) for x in (0x4a8,0x4b0,0x4b8)],
                'callback_2b0':hex(self.readq(self.coordinator+0x2b0+0x38)),
                'callback_330':hex(self.readq(self.coordinator+0x330+0x38))}


def main():
    cases=[]
    matrix=[(selected,valid,visible,present)
            for selected,valid,visible in ((False,False,True),(False,False,False),(True,False,True),(True,True,True))
            for present in (False,True)]
    for selected,valid,visible,present in matrix:
        h=UserHarness(selected,valid,visible,present);before=h.snapshot()
        assert h.queue(0x2DF990)==0
        h.apply();paused=h.snapshot()
        assert paused['stack']==['Root','Motor','Game','Strategy','User','Save']
        assert paused['user_phase']==2 and paused['control_pause']==1 and paused['cursor_enabled']==0
        h.complete();after=h.snapshot()
        assert after['stack']==before['stack'] and after['user_phase']==2
        assert after['control_pause']==0 and after['cursor_enabled']==1
        assert paused['coordinator_flags']==0 and after['coordinator_flags']==1
        assert after['pending_menu']==-1 and after['advance_game']==after['advance_panel']==0
        assert 'User' not in h.frees
        assert (after['selected'][0]=='0x0')==(not selected or valid)
        visited=set(h.visits)
        assert {0x3F5920,0x3F5530,0x3F7710,0x3F7A70,0x2F2BB0,0xC020,0x3DF8B0,0x3DF670,
                0x8F50,0xD390,0x13E90,0x12EE0}<=visited
        if selected and valid:assert 0x3E8EF0 in visited
        cases.append({'result':'PASS','selected':selected,'selection_valid':valid,'panel_visible':visible,
                      'special_context_pointer_present':present,'special_context_flag':0,
                      'before':before,'paused':paused,'after':after,'instructions':len(h.visits),
                      'writes':h.writes,'peripheral_calls':h.ui_calls,
                      'image_writes':[w for w in h.writes if BASE<=int(w['address'],0)<BASE+0x2200000]})
    path=ROOT/('save_return_user_shadow_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    result={'result':'PASS','cases':cases,'game_access':False,'native_export_ready':False,
            'executed':['actual queue/apply/save cleanup/pop','User pause/resume/enter/exit',
                        'selection validity and selection clearing','UI callback container copying and clearing'],
            'limits':['World serialization and worker are not executed; worker result is synthetic.',
                      'Selected peripheral UI/services and singleton lookup are stubs; no claim of full side-effect coverage.',
                      'Ordinary mode only: special context pointer absent or flag=0; active special context is unproved.',
                      'Coordinator uses fixture flags=1 and empty timer/event lists; other real configurations remain unproved.',
                      'Valid selection clearing is an observed local UI effect, not world preservation proof.']}
    with path.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps({'result':'PASS','cases':len(cases),'evidence':str(path),'native_export_ready':False}))


if __name__=='__main__':main()
