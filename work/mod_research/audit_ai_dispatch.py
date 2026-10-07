"""Offline validate the four known direct references to the per-force AI gate."""
import hashlib
import json
from pathlib import Path
from bisect import bisect_right
import disasm_chained as d
ROOT=Path(__file__).resolve().parent
out=ROOT/'ai-dispatch-handoff'
out.mkdir(exist_ok=False)
calls=json.loads((ROOT/'calls-b44d0.json').read_text())
assert len(calls)==4
records=[]
for row in calls:
    address=row['at'];entry=d.entries[bisect_right(d.starts,address)-1];main=d.primary(entry)
    fragments=sorted(set(d.groups[main]+[main]));instructions=[];lines=[]
    for a,z,_ in fragments:
        part=list(d.decoder.disasm(d.image[a:z],a));instructions+=part
        lines.append(f'Fragment {a:#x}..{z:#x}')
        lines.extend(f'{i.address:#x}: {i.mnemonic} {i.op_str}' for i in part)
    call=next(i for i in instructions if i.address==address)
    assert call.mnemonic=='call' and call.operands[0].type==d.capstone.x86.X86_OP_IMM and call.operands[0].imm==0xB44D0
    record={'function_rva':hex(main[0]),'gate_call_rva':hex(address),
            'direct_calls':[{'at':hex(i.address),'target':hex(i.operands[0].imm)} for i in instructions if i.mnemonic=='call' and i.operands[0].type==d.capstone.x86.X86_OP_IMM],
            'indirect_calls':[{'at':hex(i.address),'operand':i.op_str} for i in instructions if i.mnemonic=='call' and i.operands[0].type!=d.capstone.x86.X86_OP_IMM],
            'blocks':[{'start':hex(a),'end':hex(z),'sha256':hashlib.sha256(d.image[a:z]).hexdigest()} for a,z,_ in fragments]}
    records.append(record)
    (out/f'{main[0]:x}.txt').write_text('\n'.join(lines),encoding='utf-8')
result={'scope':'Validated direct call sites only; indirect/dynamic references and complete decision coverage not proven',
        'gate_rva':'0xb44d0','manager_pointer_rva':'0x1a1f6c0','map_offset':'0x60',
        'map_key':'process-local CForceData pointer; network must carry force id instead',
        'missing_entry_returns':1,'known_direct_callers':records,'game_access':False,'ai_policy_patched':False}
(out/'index.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'validated_direct_callers':[x['function_rva'] for x in records],'game_access':False,'indirect_calls':[x['indirect_calls'] for x in records]}))
