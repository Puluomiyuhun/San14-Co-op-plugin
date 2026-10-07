from pathlib import Path
import sys,json
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P));import disasm_chained as d
out=[]
for root,chunks in d.groups.items():
 if not 0xaf0000<=root[0]<0xb10000:continue
 ins=[i for a,z,_ in sorted(set(chunks+[root])) for i in d.decoder.disasm(d.image[a:z],a)]
 for k,i in enumerate(ins):
  if i.mnemonic=='call' and any(x in i.op_str for x in ('+ 0x48]','+ 0x50]','+ 0xc8]')):
   out.append({'root':hex(root[0]),'instructions':[f'{j.address:#x}: {j.mnemonic} {j.op_str}'for j in ins[max(0,k-8):k+5]]})
(P/'transition_input_gate_audit_di_candidates.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
