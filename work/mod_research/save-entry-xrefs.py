from pathlib import Path
from bisect import bisect_right
import sys,struct,json
P=Path(__file__).resolve().parent
args=sys.argv[1:];sys.argv=sys.argv[:1];sys.path.insert(0,str(P))
import disasm_chained as d
targets={int(x,0) for x in args}; adjusted={t-s for t in targets for s in (0,1,4)}; roots={}
for align in range(4):
 end=0x1200000; data=d.image[align:end-(end-align)%4]
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
print(json.dumps(rows,indent=2))
(P/'save-entry-xrefs.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
