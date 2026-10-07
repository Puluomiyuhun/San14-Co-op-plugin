"""Relocate verified native leaf RNG helpers into a private test image."""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
b=(ROOT/'game-runtime-image.bin').read_bytes();md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
segments=[('get',0x3aa390,0x3aa397,0),('set',0x3aa3e0,0x3aa3e7,0x40),
 ('unbounded',0x3aa3a0,0x3aa3e0,0x80),('percentage',0x3aa3f0,0x3aa458,0x100),('range',0x3aa7c0,0x3aa818,0x200),
 ('derived_percentage_read_only',0x3aa460,0x3aa4d7,0x300)]
buf=bytearray(4096);fixups=[];manifest=[]
for name,start,end,dest in segments:
    code=b[start:end];instructions=list(md.disasm(code,start));assert sum(i.size for i in instructions)==len(code)
    assert instructions[-1].mnemonic=='ret'
    buf[dest:dest+len(code)]=code
    for ins in instructions:
        assert ins.mnemonic!='call'
        if ins.mnemonic.startswith('j'):assert start<=ins.operands[0].imm<end
        for op in ins.operands:
            if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
                target=ins.address+ins.size+op.mem.disp
                assert (target,op.size) in ((0x18eb8b0,4),(0x1fca1e0,8))
                local_target=4096 if target==0x18eb8b0 else 4112
                offset=dest+ins.address-start
                struct.pack_into('<i',buf,offset+ins.disp_offset,local_target-(offset+ins.size))
                fixups.append({'rva':hex(ins.address),'source_target_rva':hex(target),'target_fixture_offset':hex(local_target)})
    manifest.append({'name':name,'start_rva':hex(start),'end_rva':hex(end),'fixture_offset':hex(dest),'sha256':hashlib.sha256(code).hexdigest()})
assert len(fixups)==10
(ROOT/'native_rng_fixture_code.h').write_text('static const unsigned char nativeRngCode[] = {'+','.join(hex(x) for x in buf)+'};\n',encoding='ascii')
trace=ROOT/'lockstep-traces/camera-near-rng-k2/trace.jsonl'
observed=[r for r in (json.loads(x) for x in trace.read_text(encoding='utf-8').splitlines()) if r['event']=='rng_write']
assert len(observed)==144
header='struct ObservedStateWrite { uint32_t before,after; bool sameValue; };\nstatic const ObservedStateWrite observedWrites[] = {\n'
header+='\n'.join('{'+str(r['previous_observed'])+'u,'+str(r['observed_after'])+'u,'+('true' if r['previous_observed']==r['observed_after'] else 'false')+'},' for r in observed)
header+='\n};\n'
(ROOT/'observed_rng_states_fixture.h').write_text(header,encoding='ascii')
(ROOT/'native-rng-fixture-source.json').write_text(json.dumps({'segments':manifest,'fixups':fixups,
 'observed_trace_sha256':hashlib.sha256(trace.read_bytes()).hexdigest(),'observed_state_writes':len(observed),
 'observed_replay_scope':'Replay the real write-state sequence using native unbounded update and same-value setter. Does not reconstruct uncaptured percentage threshold or historical return values.',
 'scope':'Exact native leaf function instructions except their RIP-relative state references redirected to private test storage. No process handles, live-game calls or writes.'},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'segments':len(segments),'relocations':len(fixups)}))
