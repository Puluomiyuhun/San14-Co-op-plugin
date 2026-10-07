from pathlib import Path
import sys,json
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P));import disasm_chained as d
out=[]
for root,chunks in d.groups.items():
 if not 0x840000 <= root[0] < 0x860000:continue
 instructions=[]
 for a,z,_ in sorted(set(chunks+[root])):instructions.extend(d.decoder.disasm(d.image[a:z],a))
 for k,i in enumerate(instructions):
  if '0x3080]' in i.op_str:
   nearby=instructions[max(0,k-2):k+12]
   if any(j.mnemonic=='call' and '+ 0x40]' in j.op_str for j in nearby):
    out.append({'root':hex(root[0]),'instructions':[f'{j.address:#x}: {j.mnemonic} {j.op_str}' for j in nearby]})
print(json.dumps(out,indent=2));(P/'transition_visual_present_candidates.json').write_text(json.dumps(out,indent=2))
