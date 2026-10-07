"""Extract native reward and identity paths for isolated paired processes.

Does not call the game. The capacity calculator's policy-effect query has one
explicit stub: it only contributes to the fourth output (not the money cap).
The untested tribal-city branch ends in a trap instead of guessing.
"""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
RANGES=[
 ('reward',0x1D6DA0,0x1D7059),('valid',0x2F2BB0,0x2F2BD4),
 ('person_valid',0x2119F0,0x211A2D),('district_valid',0x211610,0x211659),
 ('force_valid',0x211710,0x21174B),('force_id',0x20B610,0x20B63A),
 ('force_ruler',0x3A0C0,0x3A0EC),('compatibility',0x278C40,0x278CB2),
 ('keyed_random',0x3AA2C0,0x3AA389),('random_field',0x2F0FC0,0x2F0FC7),
 ('city_district',0x209A00,0x209A2A),('city_valid',0x211540,0x2115B4),
 ('object_valid',0x2119C0,0x2119F0),('money',0x20C2E0,0x20C2E4),
 ('add_money',0x15BD40,0x15BD97),('set_money',0x21D7C0,0x21D801),
 ('money_cap',0x20BDF0,0x20BE1B),('capacities',0x242140,0x24228C),
 ('city_force',0x20A5F0,0x20A628),('city_force_id',0x20A8E0,0x20A944),
 ('tribal_city',0x2108C0,0x210A1C),('context',0x1C1A70,0x1C1A78),
 ('context_mode',0x1C0CD0,0x1C0CEF),('own_ruler_district',0x211260,0x21130D),
 ('local_counter',0x2E6380,0x2E63F0),('counter_data',0x1C1AA0,0x1C1AB9),
 ('player_force',0x2F21E0,0x2F220A),('player_main',0x2F21A0,0x2F21D2),
 ('main_district',0x20C110,0x20C1E5),('district_begin',0x206EF0,0x206FB1),
 ('district_end',0x206FC0,0x20703C),('district_member',0x2F6330,0x2F6350),
 ('is_player',0x2110B0,0x211109),('combat_filter',0x43F160,0x43F216),
 ('initialize_player',0x2FC850,0x2FC8F9),('person_force_id',0x20A9F0,0x20AA41),
 ('person_force',0x20A660,0x20A6D5),('rank_apply',0x2BBBC0,0x2BBC5A),
 ('rank_valid',0x211B80,0x211BB4),('world_valid',0x665CD0,0x665CD6),
]

def main():
 image=(ROOT/'game-runtime-image.bin').read_bytes()
 md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
 offsets={a:i*0x400 for i,(_,a,_) in enumerate(RANGES)}
 external={0x3CB260:0xB000,0x208D70:0xB020,0x1C16F0:0xB040}
 patches=[];data={};meta=[];header='// Generated isolated native identity/reward code; never installed into SAN14.\n'
 for name,a,z in RANGES:
  off=offsets[a];code=image[a:z];instructions=list(md.disasm(code,a));assert sum(i.size for i in instructions)==len(code)<0x400
  bounds={i.address for i in instructions};refs=[]
  for ins in instructions:
   if ins.mnemonic=='call' or ins.mnemonic.startswith('j'):
    op=ins.operands[0]
    if op.type==capstone.x86.X86_OP_IMM:
     target=op.imm
     if a<=target<z:assert target in bounds
     else:
      assert ins.mnemonic in ('call','jmp') and ins.size==5 and target in offsets|external,(name,hex(target))
      dest=offsets.get(target,external.get(target));patches.append((off+ins.address-a+1,off+ins.address-a+5,dest))
      refs.append({'at':hex(ins.address),'target':hex(target),'external':target in external})
    else:
     assert op.type==capstone.x86.X86_OP_MEM and op.mem.disp in (8,0x18,0x60,0x80,0x90,0x98,0xB0,0xB8),(name,ins.op_str)
     refs.append({'at':hex(ins.address),'virtual_offset':hex(op.mem.disp)})
   for op in ins.operands:
    if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
     target=ins.address+ins.size+op.mem.disp
     dest=data.setdefault(target,0xC000+len(data)*0x20)
     assert ins.disp_size==4
     patches.append((off+ins.address-a+ins.disp_offset,off+ins.address-a+ins.size,dest))
  header+=f'constexpr unsigned fn_{name}=0x{off:X};\nstatic const unsigned char bytes_{name}[]={{'+','.join(map(str,code))+'};\n'
  meta.append({'name':name,'rva':hex(a),'end':hex(z),'sha256':hashlib.sha256(code).hexdigest(),'references':refs})
 header+='struct NativeBlock {const unsigned char* bytes;unsigned size,offset;};\nstatic const NativeBlock nativeBlocks[]={'
 header+=','.join('{bytes_%s,sizeof bytes_%s,fn_%s}'%(n,n,n) for n,_,_ in RANGES)+'};\n'
 header+='struct Patch {unsigned at,next,target;};\nstatic const Patch patches[]={'+','.join('{%d,%d,%d}'%p for p in patches)+'};\n'
 header+='struct DataSlot {unsigned rva,offset;unsigned char bytes[8];};\nstatic const DataSlot dataSlots[]={'
 header+=','.join('{%d,%d,{%s}}'%(r,o,','.join(map(str,image[r:r+8]))) for r,o in data.items())+'};\n'
 (ROOT/'identity_pair_fixture_code.h').write_text(header,encoding='utf-8')
 result={'blocks':meta,'data_slots':{hex(r):hex(o) for r,o in data.items()},'relocations':len(patches),
         'external_boundaries':{'0x3cb260':'policy-effect query returns controlled zero; used only in capacity output four, not gold cap',
                                '0x208d70':'unsupported tribal-city branch traps if reached',
                                '0x1c16f0':'unsupported identity initializer mode 4 traps; captured world+40 is 1'},
         'scope':'Copied native command/identity branches in isolated processes with explicit bounded external dependencies; no rendering or gameplay simulation.'}
 (ROOT/'identity-pair-native-source.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'native_blocks':len(meta),'relocations':len(patches),'data_rvas':[hex(r) for r in data]}))

if __name__=='__main__':main()
