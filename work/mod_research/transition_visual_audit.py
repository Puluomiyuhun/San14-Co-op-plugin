from pathlib import Path
from bisect import bisect_right
import sys,struct,json
P=Path(__file__).resolve().parent
args=sys.argv[1:];sys.argv=sys.argv[:1];sys.path.insert(0,str(P))
import disasm_chained as d
base=struct.unpack_from('<Q',d.image,0x12cd408)[0]-0x3f69f0
rows={}
for name in ['CLoadState','CTitleState','CGameState','CMotorGameState','CUserStrategyState','CStrategyState']:
 pos=d.image.find(('.?AV'+name+'@@\0').encode());td=pos-16;cols=[];x=0
 while True:
  x=d.image.find(struct.pack('<I',td),x)
  if x<0:break
  start=x-12
  if start>=0 and struct.unpack_from('<I',d.image,start)[0]==1 and struct.unpack_from('<I',d.image,start+20)[0]==start:cols.append(start)
  x+=1
 rows[name]=[]
 for col in cols:
  needle=struct.pack('<Q',base+col);x=0
  while True:
   x=d.image.find(needle,x)
   if x<0:break
   vt=x+8; methods={hex(i*8):hex(struct.unpack_from('<Q',d.image,vt+8*i)[0]-base) for i in range(14)}
   rows[name].append({'vtable':hex(vt),'methods':methods});x+=1
print(json.dumps(rows,indent=2));(P/'transition_visual_rtti.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
for text in args:
 at=int(text,0);entry=d.entries[bisect_right(d.starts,at)-1]
 if not entry[0]<=at<entry[1]:
  ins=[]
  for i in d.decoder.disasm(d.image[at:at+512],at):
   ins.append(i)
   if i.mnemonic in ('ret','jmp'):break
  chunks=[ins];root=at
 else:
  en=d.primary(entry);chunks=[list(d.decoder.disasm(d.image[a:z],a)) for a,z,_ in sorted(set(d.groups[en]+[en]))];root=en[0]
 lines=[]
 for chunk in chunks:
  for i in chunk:
   refs=[hex(i.address+i.size+o.mem.disp) for o in i.operands if o.type==d.capstone.x86.X86_OP_MEM and o.mem.base==d.capstone.x86.X86_REG_RIP]
   lines.append(f'{i.address:#x}: {i.mnemonic} {i.op_str}'+(' ; '+','.join(refs) if refs else ''))
 (P/f'transition_visual_{root:x}.txt').write_text('\n'.join(lines),encoding='utf8')
