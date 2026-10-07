from pathlib import Path
from bisect import bisect_right
import sys,json,struct
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));import disasm_chained as d
out=[];roots={}
for sig in (b'\xba\x00\x01\x00\x00',b'\xba\x14\x00\x00\x00',b'\xba\x10\x00\x00\x00'):
 p=0
 while True:
  p=d.image.find(sig,p,0x123c000)
  if p<0:break
  n=bisect_right(d.starts,p)-1
  if n>=0 and d.entries[n][0]<=p<d.entries[n][1]:
   root=d.primary(d.entries[n]);roots[root[0]]=root
  p+=1
for root in roots.values():
 ins=[i for a,z,_ in sorted(set(d.groups[root]+[root])) for i in d.decoder.disasm(d.image[a:z],a)]
 for k,i in enumerate(ins):
  if i.mnemonic=='mov' and i.op_str in ('edx, 0x100','edx, 0x14','edx, 0x10'):
   span=ins[max(0,k-6):k+8]
   if any(j.mnemonic=='call' and '+ 0x48]' in j.op_str for j in span):
    out.append({'root':hex(root[0]),'instructions':[f'{j.address:#x}: {j.mnemonic} {j.op_str}'for j in span]})
(P/'transition_input_gate_audit_poll_candidates.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
