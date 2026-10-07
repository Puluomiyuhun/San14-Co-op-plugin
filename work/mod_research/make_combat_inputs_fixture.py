"""Relocate three native routines into a separate process, with explicit local dependencies."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
image=(ROOT/'game-runtime-image.bin').read_bytes()
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
blocks=[('predicate',0x210d40,0x210e85,0),('compare',0x15abc0,0x15ae6d,0x400),('sort',0x159580,0x159808,0x800)]
internal={begin:offset for _,begin,_,offset in blocks}
stubs={0x2f2bb0:0,0x20a810:1,0x15a3b0:2,0xd440:3,0x337bb0:3}
data_targets={};patches=[];report=[];header='// Native code copied ONLY to a local isolated fixture process.\n'
for name,begin,end,offset in blocks:
    code=image[begin:end];instructions=list(md.disasm(code,begin));assert sum(i.size for i in instructions)==len(code)
    row={'name':name,'rva':hex(begin),'length':len(code),'sha256':hashlib.sha256(code).hexdigest(),'patches':[]}
    for ins in instructions:
        if ins.mnemonic=='call':
            assert ins.size==5 and ins.bytes[0]==0xe8 and ins.operands[0].type==capstone.x86.X86_OP_IMM
            t=ins.operands[0].imm
            assert t in internal or t in stubs
            dest=internal[t] if t in internal else 0xc00+stubs[t]*16
            patch=(offset+ins.address-begin+1,offset+ins.address-begin+ins.size,dest)
            patches.append(patch);row['patches'].append({'kind':'call','rva':hex(ins.address),'target':hex(t),'local':hex(dest)})
        elif ins.mnemonic.startswith('j'):
            assert ins.operands[0].type==capstone.x86.X86_OP_IMM and begin<=ins.operands[0].imm<end
        for op in ins.operands:
            if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
                t=ins.address+ins.size+op.mem.disp
                assert ins.disp_size==4
                dest=data_targets.setdefault(t,0x1000+16*len(data_targets))
                patch=(offset+ins.address-begin+ins.disp_offset,offset+ins.address-begin+ins.size,dest)
                patches.append(patch);row['patches'].append({'kind':'rip_data','rva':hex(ins.address),'target':hex(t),'local':hex(dest)})
    header+='static const unsigned char code_'+name+'[]={'+','.join(hex(x) for x in code)+'};\n'
    report.append(row)
header+='struct CodePatch {unsigned at,next,target;};\nstatic const CodePatch codePatches[]={'+','.join('{%d,%d,%d}'%p for p in patches)+'};\n'
header+='struct DataSlot {unsigned rva,local;};\nstatic const DataSlot dataSlots[]={'+','.join('{%d,%d}'%p for p in data_targets.items())+'};\n'
trace=[json.loads(line) for line in (ROOT/'lockstep-traces/branch-run-f/trace.jsonl').read_text().splitlines()]
pair_rows=next(r['pairs'] for r in trace if r['event']=='pairs_ready')
assert len(pair_rows)==17 and all(int.from_bytes(bytes.fromhex(p[s])[4:8],'little') in (5,6,27) for p in pair_rows for s in ('a','b'))
header+='static const unsigned char realPairs[17][2][24]={'+','.join('{'+','.join('{'+','.join(str(x) for x in bytes.fromhex(p[s]))+'}' for s in ('a','b'))+'}' for p in pair_rows)+'};\n'
(ROOT/'combat_inputs_fixture_code.h').write_text(header,encoding='utf-8')
meta={'blocks':report,'data_slots':{hex(k):hex(v) for k,v in data_targets.items()},'stub_targets':{hex(k):v for k,v in stubs.items()},
    'dataset':'F first pairs_ready, 17 pairs; all side kinds 5/6/27. Missing pointer fields replaced with local pointers or zero.',
    'scope':'Native list membership, pair comparator, and insertion sort control flow. External validity/force helpers are local explicit stubs; destructor is counted no-op. Facility comparison fails rather than being guessed.',
    'game_access':False}
(ROOT/'combat-inputs-fixture-source.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print(json.dumps({'blocks':[r['name'] for r in report],'data_targets':[hex(k) for k in data_targets],'pairs':len(pair_rows)}))
