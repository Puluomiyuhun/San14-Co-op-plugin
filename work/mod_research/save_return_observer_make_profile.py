"""Offline exact-byte profile for four single-return User callbacks."""
from pathlib import Path
import hashlib,json,sys
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));sys.argv=sys.argv[:1]
import disasm_chained as d
b=(P/'game-runtime-image.bin').read_bytes()
assert hashlib.sha256(b).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
points=[('resume',0x3F5530,0x3F578F,0x18),('pause',0x3F5920,0x3F5A2B,0x20),('enter',0x3F7710,0x3F7968,0x58),('exit',0x3F7A70,0x3F7B5C,0x60)]
s=['// Generated from pinned offline capture; no process access.','#pragma once','struct SROPoint { const char* name; unsigned entry,ret,slot,size; const unsigned char* bytes; };']
rows=[];proof=[]
for n,a,z,slot in points:
 data=b[a:z+1];assert data[-1]==0xC3
 instructions=list(d.decoder.disasm(data,a))
 assert instructions[-1].address+instructions[-1].size==z+1
 returns=[i.address for i in instructions if i.mnemonic.startswith('ret')]
 assert returns==[z],(n,returns)
 branches=[]
 for i in instructions:
  if i.mnemonic.startswith('j'):
   assert len(i.operands)==1 and i.operands[0].type==d.capstone.x86.X86_OP_IMM
   target=i.operands[0].imm;assert a<=target<=z,(n,hex(i.address),hex(target))
   branches.append({'rva':hex(i.address),'target':hex(target)})
 proof.append({'name':n,'entry':hex(a),'ret':hex(z),'size':len(data),'single_ret':True,'all_direct_branches_internal':True,'sha256':hashlib.sha256(data).hexdigest(),'branch_edges':branches})
 s.append('static const unsigned char sro_'+n+'[]={'+','.join(f'0x{x:02x}' for x in data)+'};')
 rows.append(f'{{"{n}",0x{a:x},0x{z:x},0x{slot:x},{len(data)},sro_{n}}}')
s.append('static const SROPoint sroPoints[]={'+','.join(rows)+'};')
(P/'save_return_observer_profile.h').write_text('\n'.join(s)+'\n',encoding='utf8')
(P/'save_return_observer_profile.json').write_text(json.dumps({'result':'PASS','image_sha256':hashlib.sha256(b).hexdigest(),'callbacks':proof,'scope':'Complete linear-decoded function ranges, sole RET and direct jump bounds; indirect call behavior remains external.','game_access':False},indent=2),encoding='utf8')
print(json.dumps({'result':'PASS','callbacks':4,'game_access':False}))
