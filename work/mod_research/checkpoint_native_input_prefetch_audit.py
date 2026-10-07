"""Only fixed bytes from the existing workspace archive; no live addresses."""
from pathlib import Path
import hashlib, json, sys
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'python_deps'))
import capstone
b=(P/'game-runtime-image.bin').read_bytes()
sha=hashlib.sha256(b).hexdigest()
assert sha=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
d=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);d.detail=True
a,z=0x3f9daf,0x3f9dd0
rows=[]
for i in d.disasm(b[a:z],a):
    rows.append({'rva':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str})
    for o in i.operands:
        if o.type==capstone.x86.X86_OP_MEM:assert o.mem.base!=capstone.x86.X86_REG_RIP
        if i.group(capstone.CS_GRP_JUMP):assert o.type==capstone.x86.X86_OP_IMM and a<=o.imm<=z
assert rows[0]['instruction']=='mov rax, qword ptr [rsi + 0x478]' and len(bytes.fromhex(rows[0]['bytes']))==7
assert sum(len(bytes.fromhex(i['bytes'])) for i in rows)==33
for at,expected in [(0x3f9b00,'push rsi'),(0x3f9b02,'sub rsp, 0x40'),(0x3f9dbd,'je 0x3f9dd0')]:
    i=next(d.disasm(b[at:at+16],at));assert i.mnemonic+' '+i.op_str==expected
text='; Generated from exact existing archive bytes. No installer.\n'
text+='PREFETCH_REPLAY_LOAD macro\n    db '+','.join(f'0{x:02x}h' for x in b[a:a+7])+'\nendm\n'
text+='PREFETCH_REMAINING_CONSUMER macro\n    db '+','.join(f'0{x:02x}h' for x in b[a+7:z])+'\nendm\n'
(P/'checkpoint_native_input_prefetch_archived.inc').write_text(text,encoding='utf8')
out={'schema':'checkpoint-native-input-prefetch-audit/v1','image_sha256':sha,'instructions':rows,
     'minimum_covered_range':{'start':'0x3f9daf','end_exclusive':'0x3f9db6','bytes':b[a:a+7].hex(),'length':7},
     'remaining_relative_branch':{'site':'0x3f9dbd','target':'0x3f9dd0','unchanged_if_same_7_byte_site_extent':True},
     'candidate_callsite_shape':'A 5-byte relative CALL plus 2-byte padding could cover this entire instruction. This prototype does not select a live address, verify rel32 reachability, or install such a patch.',
     'stack_derivation':'Normal Win64 entry RSP%16=8; push RSI then sub RSP,40h yields RSP%16=0 at the candidate callsite. Additional runtime ownership/order still unverified.',
     'replay_semantics':'Observe BEFORE the original seven-byte load; execute exact load while the bridge frame is still fully allocated; return RAX=toolbar and all other input registers/flags/XMM unchanged.',
     'live_hook_installed':False,'entire_native_update_executed':False,
     'limits':['No upper YMM/ZMM, opmask, AMX or x87-state preservation claim.','No live detour publication, displaced-instruction installer, CET/CFG policy validation, or all-thread patch fence.','Owned PE unwind tests do not authorize patching the native game.']}
(P/'checkpoint_native_input_prefetch_audit.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
print(json.dumps({'covered_bytes':7,'native_block_bytes':33,'relative_target':'0x3f9dd0','live_installed':False}))
