from pathlib import Path
from bisect import bisect_right
import sys,json
P=Path(__file__).resolve().parent
args=sys.argv[1:];sys.argv=sys.argv[:1];sys.path.insert(0,str(P))
import disasm_chained as d
for x in args:
 at=int(x,0);entry=d.entries[bisect_right(d.starts,at)-1];assert entry[0]<=at<entry[1]
 root=d.primary(entry); rows=[]
 for a,z,_ in sorted(set(d.groups[root]+[root])):
  rows.append(f'Fragment {a:#x}..{z:#x}')
  for i in d.decoder.disasm(d.image[a:z],a):
   extra=[]
   for o in i.operands:
    if o.type==d.capstone.x86.X86_OP_MEM and o.mem.base==d.capstone.x86.X86_REG_RIP:extra.append(hex(i.address+i.size+o.mem.disp))
   rows.append(f'{i.address:#x}: {i.mnemonic} {i.op_str}'+(' ; '+','.join(extra) if extra else ''))
 (P/f'save-entry-{root[0]:x}.txt').write_text('\n'.join(rows),encoding='utf8')
 print(hex(root[0]),len(rows))
