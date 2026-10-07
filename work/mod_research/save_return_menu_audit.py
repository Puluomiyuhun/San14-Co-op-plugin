"""Offline helpers for the normal save menu; never imports live readers."""
from pathlib import Path
from bisect import bisect_right
import sys,struct,json,hashlib,re
P=Path(__file__).resolve().parent
args=sys.argv[1:];sys.argv=sys.argv[:1];sys.path.insert(0,str(P))
import disasm_chained as d
BASE=0x7ff749440000
assert hashlib.sha256(d.image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
def dump(at):
 e=d.entries[bisect_right(d.starts,at)-1]
 if not e[0]<=at<e[1]:
  lines=['Leaf without unwind metadata; first linear ret only']
  for i in d.decoder.disasm(d.image[at:at+128],at):
   lines.append(f'{i.address:#x}: {i.mnemonic} {i.op_str}')
   if i.mnemonic=='ret':break
  else:raise ValueError('No bounded leaf ret')
  p=P/f'save_return_menu_disasm_{at:x}.txt';p.write_text('\n'.join(lines),encoding='utf8');print(p.name,len(lines));return
 root=d.primary(e);lines=[]
 for a,z,_ in sorted(set(d.groups[root]+[root])):
  lines.append(f'Fragment {a:#x}..{z:#x}')
  for i in d.decoder.disasm(d.image[a:z],a):
   refs=[hex(i.address+i.size+o.mem.disp) for o in i.operands if o.type==d.capstone.x86.X86_OP_MEM and o.mem.base==d.capstone.x86.X86_REG_RIP]
   lines.append(f'{i.address:#x}: {i.mnemonic} {i.op_str}'+(' ; '+','.join(refs) if refs else ''))
 p=P/f'save_return_menu_disasm_{root[0]:x}.txt';p.write_text('\n'.join(lines),encoding='utf8');print(p.name,len(lines))
def xrefs(targets):
 adjusted={t-s for t in targets for s in (0,1,4)};roots={}
 for align in range(4):
  end=0x1200000;data=d.image[align:end-(end-align)%4]
  for idx,(v,) in enumerate(struct.iter_unpack('<i',data)):
   pos=align+idx*4
   if pos+4+v in adjusted:
    e=d.entries[bisect_right(d.starts,pos)-1]
    if e[0]<=pos<e[1]:roots[d.primary(e)[0]]=d.primary(e)
 rows=[]
 for root in roots.values():
  for a,z,_ in sorted(set(d.groups[root]+[root])):
   for i in d.decoder.disasm(d.image[a:z],a):
    for o in i.operands:
     t=None
     if o.type==d.capstone.x86.X86_OP_MEM and o.mem.base==d.capstone.x86.X86_REG_RIP:t=i.address+i.size+o.mem.disp
     elif o.type==d.capstone.x86.X86_OP_IMM and i.mnemonic in ('call','jmp'):t=o.imm
     if t in targets:rows.append({'function':hex(root[0]),'at':hex(i.address),'instruction':i.mnemonic+' '+i.op_str,'target':hex(t),'bytes':i.bytes.hex()})
 return rows
def rtti():
 rows=[]
 for match in re.finditer(rb'\.\?AV[^\0]{1,150}@@\0',d.image):
  name=match.group()[:-1].decode('ascii',errors='replace')
  if not any(x in name for x in ('Save','Menu','Load')):continue
  td=match.start()-16;cols=[];x=0
  while True:
   x=d.image.find(struct.pack('<I',td),x)
   if x<0:break
   col=x-12
   if col>=0 and struct.unpack_from('<I',d.image,col)[0]==1 and struct.unpack_from('<I',d.image,col+20)[0]==col:cols.append(col)
   x+=1
  for col in cols:
   x=0
   while True:
    x=d.image.find(struct.pack('<Q',BASE+col),x)
    if x<0:break
    vt=x+8;methods={hex(i*8):hex(struct.unpack_from('<Q',d.image,vt+i*8)[0]-BASE) for i in range(16)}
    rows.append({'name':name,'type':hex(td),'col':hex(col),'vtable':hex(vt),'methods':methods});x+=1
 return rows
if args[0]=='dump':
 for a in args[1:]:dump(int(a,0))
else:
 rows=rtti() if args[0]=='rtti' else xrefs({int(a,0) for a in args[1:]})
 path=P/('save_return_menu_rtti.json' if args[0]=='rtti' else 'save_return_menu_xrefs_'+'_'.join(a.removeprefix('0x') for a in args[1:])+'.json')
 path.write_text(json.dumps(rows,indent=2),encoding='utf8');print(json.dumps(rows,indent=2))
