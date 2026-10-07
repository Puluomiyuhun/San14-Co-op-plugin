"""Only archived image decoding/emulation; never looks up or opens a process."""
import pathlib,hashlib,json,struct,sys
p=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(p/'python_deps'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RIP,UC_X86_REG_RSP,UC_X86_REG_RCX,UC_X86_REG_RAX
raw=(p/'game-runtime-image.bin').read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
cs=Cs(CS_ARCH_X86,CS_MODE_64)
anchors=[(0x3f85e4,23),(0x3f8603,8),(0x19e9f0,27),(0x194b04,13),(0x1ac3c0,99),(0x3fa850,29),(0x3faa82,17)]
rows=[]
for rva,size in anchors:
 code=raw[rva:rva+size];rows.append({'rva':hex(rva),'size':size,'bytes':code.hex(),'instructions':[f'{i.address:x}: {i.mnemonic} {i.op_str}' for i in cs.disasm(code,rva)]})
assert struct.unpack_from('<Q',raw,0x1297cf8+0x18)[0]-0x7ff749440000==0x1ac3c0
base=0x140000000;stack=0x200000000;objects=0x300000000;stop=0x400000000
runs=[]
for request in [0,4]:
 u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(base,(len(raw)+4095)&~4095);u.mem_write(base,raw);u.mem_map(stack,0x20000);u.mem_map(objects,0x2000);u.mem_map(stop,0x1000)
 rsp=stack+0x10008;u.mem_write(rsp,struct.pack('<Q',stop));u.mem_write(objects+0x480,struct.pack('<Q',objects+0x1000));u.mem_write(objects+0x1000+0x1b0,struct.pack('<I',request));u.reg_write(UC_X86_REG_RSP,rsp);u.reg_write(UC_X86_REG_RCX,objects)
 record={'request':request,'business_calls':[],'returned':False,'stub_calls':[]}
 def hook(uc,address,size,_):
  if address==stop:record['returned']=True;uc.emu_stop();return
  rva=address-base
  if rva in (0xef9f20,0xf690):
   record['stub_calls'].append(hex(rva));sp=uc.reg_read(UC_X86_REG_RSP);ret=struct.unpack('<Q',uc.mem_read(sp,8))[0];uc.reg_write(UC_X86_REG_RSP,sp+8);uc.reg_write(UC_X86_REG_RAX,objects+0x1800);uc.reg_write(UC_X86_REG_RIP,ret);return
  if rva==0x3e05c0:record['business_calls'].append(hex(rva));uc.emu_stop();return
  if not 0x3fa820<=rva<=0x3faab3:raise RuntimeError(f'unapproved execution {address:x}')
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(base+0x3fa820,stop+1,count=500);record['panel_after']=struct.unpack('<I',u.mem_read(objects+0x1000+0x1b0,4))[0];runs.append(record)
assert runs[0]['returned'] and not runs[0]['business_calls'] and runs[1]['business_calls']==['0x3e05c0']
out={'result':'PASS','archive_sha256':digest,'anchors':rows,'global_ui':{'singleton_rva':'0x1fc8410','vtable_rva':'0x1297cf8','slot':'0x18','target':'0x1ac3c0','nested_ui_calls':['0x1ac3fb','0x1ac40d'],'nested_dynamic_targets_not_yet_bound':True},'panel_real_bytes_emulation':runs,'emulation_limit':'Only security-cookie helper and singleton getter stubbed. Request4 stops on exact native dialog-business call; does not execute a real dialog. Gate suppression itself is separately exercised with real owned-process bridge/ASM callers.','ready_claim':'Insufficient to establish all posted-message/UI consumers. Full room Ready remains denied.','game_access':False}
(p/'checkpoint_ready_input_evidence.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'result':'PASS','real_machine_code_panel_cases':2,'anchors':len(rows)}))
