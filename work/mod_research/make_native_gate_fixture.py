"""Extract a bounded native branch function for execution ONLY in its own fixture.

Every external call is replaced by a counted local stub. No game process handle,
attachment, injection, or original external function is used by the fixture.
"""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
image=(ROOT/'game-runtime-image.bin').read_bytes()
begin,end=0x16c640,0x16c6ca
code=image[begin:end]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
targets={0x15faa0:0,0x15fa20:1,0x1622f0:2,0x15be80:3,0x162180:4}
calls=[]
decoded=list(md.disasm(code,begin))
assert sum(i.size for i in decoded)==len(code)
for ins in decoded:
    assert not any(o.type==capstone.x86.X86_OP_MEM and o.mem.base==capstone.x86.X86_REG_RIP for o in ins.operands), 'Unhandled RIP-relative data'
    if ins.mnemonic=='call':
        assert ins.bytes[0]==0xe8 and ins.size==5
        target=ins.address+5+struct.unpack('<i',ins.bytes[1:])[0]
        assert target in targets
        calls.append((ins.address-begin,targets[target]))
    elif ins.mnemonic.startswith('j'):
        assert ins.operands[0].type==capstone.x86.X86_OP_IMM
        assert begin<=ins.operands[0].imm<end, 'External branch not stubbed'
header='// Generated from the verified offline runtime image. Fixture process only.\n'
header+='static const unsigned char originalCode[] = {'+','.join(hex(x) for x in code)+'};\n'
header+='struct CallPatch { unsigned offset; unsigned target; };\n'
header+='static const CallPatch callPatches[] = {'+','.join('{'+str(a)+','+str(t)+'}' for a,t in calls)+'};\n'
(ROOT/'native_gate_fixture_code.h').write_text(header,encoding='utf-8')
metadata={'source_rva':hex(begin),'length':len(code),'source_code_sha256':hashlib.sha256(code).hexdigest(),
          'external_calls':[{'offset':hex(a),'stub_index':t} for a,t in calls],
          'stub_targets':{hex(k):v for k,v in targets.items()},
          'scope':'Only gate control flow is native; pair generation, damage processing, effects accessor and presentation are local stubs.'}
(ROOT/'native-gate-fixture-source.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
print(json.dumps(metadata))
