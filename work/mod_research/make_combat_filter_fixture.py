"""Extract four native predicates into a local-only executable fixture.

Explicitly relocate every direct call and RIP-relative data operand. Virtual
force-id and validity dependencies are local stubs; no game process is opened.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
image=(ROOT/'game-runtime-image.bin').read_bytes()
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
blocks=[('filter',0x43f160,0x43f216,0),('is_player',0x2110b0,0x211109,0x200),
        ('player_force',0x2f21e0,0x2f220a,0x400),('relation',0x29a000,0x29a151,0x600)]
internal={a:o for _,a,_,o in blocks};stubs={0x2f2bb0:0x1000}
patches=[];data={};meta=[];header='// Generated native predicates; isolated fixture process only.\n'
for name,start,end,offset in blocks:
    code=image[start:end];instructions=list(md.disasm(code,start))
    assert sum(x.size for x in instructions)==len(code)
    record={'name':name,'source_rva':hex(start),'bytes':len(code),'sha256':hashlib.sha256(code).hexdigest(),'relocations':[]}
    for ins in instructions:
        if ins.mnemonic=='call':
            op=ins.operands[0]
            if op.type==capstone.x86.X86_OP_IMM:
                assert ins.size==5 and ins.bytes[0]==0xe8
                t=op.imm;assert t in internal or t in stubs
                dest=internal[t] if t in internal else stubs[t]
                patches.append((offset+ins.address-start+1,offset+ins.address-start+5,dest))
                record['relocations'].append({'kind':'call','rva':hex(ins.address),'target':hex(t),'local':hex(dest)})
            else:
                assert op.type==capstone.x86.X86_OP_MEM and op.mem.disp==0x60
                assert op.mem.base in (capstone.x86.X86_REG_RAX,capstone.x86.X86_REG_RDX)
                record['relocations'].append({'kind':'virtual_force_id_stub','rva':hex(ins.address)})
        elif ins.mnemonic.startswith('j'):
            assert ins.operands[0].type==capstone.x86.X86_OP_IMM and start<=ins.operands[0].imm<end
        for op in ins.operands:
            if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
                t=ins.address+ins.size+op.mem.disp;assert ins.disp_size==4
                dest=data.setdefault(t,0x2000+16*len(data))
                patches.append((offset+ins.address-start+ins.disp_offset,offset+ins.address-start+ins.size,dest))
                record['relocations'].append({'kind':'data','rva':hex(ins.address),'target':hex(t),'local':hex(dest)})
    header+='static const unsigned char code_'+name+'[]={'+','.join(str(x) for x in code)+'};\n'
    meta.append(record)
assert set(data)=={0x1fca1e0,0x201ec70}
header+='struct Patch {unsigned at,next,target;};\nstatic const Patch patches[]={'+','.join('{%d,%d,%d}'%x for x in patches)+'};\n'
header+='struct Slot {unsigned rva,offset;};\nstatic const Slot slots[]={'+','.join('{%d,%d}'%x for x in data.items())+'};\n'
trace=ROOT/'lockstep-traces/branch-run-f/trace.jsonl'
rows=[json.loads(l) for l in trace.read_text().splitlines()]
pairs=next(r['pairs'] for r in rows if r['event']=='pairs_ready')
assert len(pairs)==17
header+='static const unsigned char realPairs[17][2][24]={'+','.join('{'+','.join('{'+','.join(str(x) for x in bytes.fromhex(p[s]))+'}' for s in ('a','b'))+'}' for p in pairs)+'};\n'
before=json.loads((ROOT/'lockstep-traces/run-a/before.json').read_text(encoding='utf-8'))
flags=[bytes.fromhex(before['records'][f'force:{i}'])[2] for i in range(52)]
assert flags==[0]*52
header+='static const unsigned char originalForceFlags[52]={'+','.join(map(str,flags))+'};\n'
(ROOT/'combat_filter_fixture_code.h').write_text(header,encoding='utf-8')
report={'blocks':meta,'data_rvas':[hex(k) for k in data],'pair_trace_sha256':hashlib.sha256(trace.read_bytes()).hexdigest(),
        'dataset':'F first 17 generated pairs, NOT original A pair list; A planning force+12 flags are all zero',
        'limits':'Native predicates with stub validity/force-id methods and controlled local globals; no combat simulation or game access'}
with (ROOT/'combat-filter-fixture-source.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps({'native_blocks':4,'pairs':17,'relocations':len(patches),'data_rvas':report['data_rvas']}))
