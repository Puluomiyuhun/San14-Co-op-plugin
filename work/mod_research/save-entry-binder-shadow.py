"""Execute the native request binder in a private emulator; never opens SAN14."""
from pathlib import Path
import sys,struct,json,hashlib
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P/'python_deps'),str(P)]
import disasm_chained as d
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *
BASE=0x7ff749440000; STACK=0x300000000; OBJ=STACK+0x1000; STOP=STACK+0x8000
assert hashlib.sha256(d.image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
def q(x):return struct.pack('<Q',x)
def sso(s):
 b=s.encode('ascii');assert len(b)<=15
 return b.ljust(16,b'\0')+q(len(b))+q(15)
def run(slot,name,caption='',stale_name='',stale_caption=''):
 u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(BASE,(len(d.image)+4095)&~4095);u.mem_write(BASE,d.image);u.mem_map(STACK,0x20000)
 u.mem_write(OBJ,struct.pack('<i',slot)+bytes(4)+sso(name)+sso(caption))
 u.mem_write(BASE+0x201ed18,sso(stale_name));u.mem_write(BASE+0x201ed38,sso(stale_caption))
 sp=STACK+0x1fef8;u.mem_write(sp,q(STOP));u.reg_write(UC_X86_REG_RSP,sp);u.reg_write(UC_X86_REG_RCX,OBJ)
 visits=[]
 def code(uc,a,n,x):
  if a==STOP:uc.emu_stop();return
  if not BASE<=a<BASE+len(d.image):raise AssertionError(f'Unknown external {a:#x}')
  if len(visits)<10000:visits.append(a-BASE)
 u.hook_add(UC_HOOK_CODE,code)
 u.emu_start(BASE+0x2fc750,STOP,count=50000)
 assert u.reg_read(UC_X86_REG_RIP)==STOP, 'Instruction cap reached'
 def read_sso(at):
  raw=bytes(u.mem_read(at,32));length,cap=struct.unpack_from('<QQ',raw,16);assert cap==15 and length<=15
  return raw[:length].decode('ascii')
 assert struct.unpack('<i',u.mem_read(BASE+0x201ed10,4))[0]==slot
 assert read_sso(BASE+0x201ed18)==name and read_sso(BASE+0x201ed38)==caption
 assert read_sso(OBJ+8)=='' and read_sso(OBJ+0x28)==''
 return {'slot':slot,'filename':name,'caption':caption,'instruction_count':len(visits),'distinct_instructions':len(set(visits)),'external_stubs':0,'source_strings_consumed':True,'global_strings_copied':True}
rows=[]
for values in [(49,'svdexSC49.s14'),(0,'svdexSC00.s14'),(34,'svdexSC34.s14','test'),(49,'svdexSC49.s14','','old.s14','old title')]:
 rows.append(run(*values))
result={'schema':'san14.save-entry-binder-shadow.v1','result':'PASS','cases':rows,'game_memory_writes':0,'game_calls':0,'game_files_changed':False,'scope':'Copied native request binder plus actual short-string helpers executed in Unicorn. No native save, state-queue insertion, UI state, storage, or game worker was run.'}
(P/'save-entry-binder-shadow.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(result))
