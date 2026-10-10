"""Pinned offline selection-state evidence. No game access or hook permission.

Static call/source checks identify a separate CDataSelectState<Data>, not its
runtime lifetime, cancellation mapping, or a safe general modal whitelist.
"""
import argparse,hashlib,json,struct,sys
from datetime import datetime
from pathlib import Path
from reward_menu_handoff_gate_audit import ARCHIVE_SHA256
HERE=Path(__file__).resolve().parent
RANGES=((0x67A930,0x67A9C1),(0x68F760,0x68FBE3),(0x21ED10,0x21EDF8),
        (0x21EFB0,0x21F12D),(0x50B690,0x50B6FF))
EXPECTED={
 0x67A980:('mov','edx, dword ptr [rcx + 0x170]'),
 0x67A986:('sub','edx, 1'),0x67A989:('je','0x67a9ae'),
 0x67A9B6:('jmp','0x68f760'),
 0x68F7AA:('xor','r14d, r14d'),
 0x68F9AB:('lea','rdi, [rsi + 0x480]'),
 0x68F9B2:('mov','qword ptr [rbp - 0x20], rdi'),
 0x68F9FB:('call','0x21ed10'),0x68FA00:('test','eax, eax'),
 0x68FA02:('je','0x68fa99'),0x68FA94:('call','0x408b00'),
 0x68FAA3:('call','0x69b660'),0x68FAAF:('call','0x6cb5f0'),
 0x68FABB:('mov','dword ptr [rax + 0x170], r14d'),
 0x21ED54:('call','0x509450'),0x21EDB7:('call','0x21efb0'),
 0x21EDBF:('call','0x50b690'),0x21EDC4:('mov','ebx, dword ptr [rbx + 0x58]'),
 0x21F001:('mov','edx, 0x870'),0x21F028:('call','0x22c450'),
 0x21F04F:('call','0x509ec0'),0x21F08F:('call','0x509e10'),
 0x21F0F1:('movups','xmmword ptr [rax], xmm0'),
 0x21F0F4:('inc','qword ptr [rdi + 0x30]'),
 0x50B696:('cmp','qword ptr [rcx + 0x50], 0'),
 0x50B6AD:('call','0x50c710'),0x50B6CF:('call','0x834820')}

def inspect(archive_root):
 root=Path(archive_root).resolve(strict=True);image=root/'game-runtime-image.bin';pdata=root/'runtime-pdata.bin'
 raw=image.read_bytes();pd=pdata.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=ARCHIVE_SHA256:raise ValueError('Pinned private archive required')
 sys.path.insert(0,str(root/'python_deps'));import capstone
 decoder=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);decoder.detail=True
 functions={(a,z) for a,z,_ in struct.iter_unpack('<III',pd)}
 checks=[];instructions={}
 def check(name,ok):
  checks.append(dict(name=name,passed=bool(ok)))
  if not ok:raise ValueError('Selection source differs: '+name)
 for a,z in RANGES:
  check('function_'+hex(a),(a,z) in functions)
  ins=list(decoder.disasm(raw[a:z],a));check('complete_decode_'+hex(a),bool(ins) and ins[-1].address+ins[-1].size==z)
  instructions.update({i.address:i for i in ins})
 for address,(mnemonic,operands) in EXPECTED.items():
  i=instructions.get(address);check('instruction_'+hex(address),i is not None and (i.mnemonic,i.op_str)==(mnemonic,operands))
 i=instructions[0x21EDB0];operand=i.operands[1]
 check('selection_name_RIP_source',i.mnemonic=='lea' and operand.type==capstone.x86.X86_OP_MEM and operand.mem.base==capstone.x86.X86_REG_RIP)
 name_rva=i.address+i.size+operand.mem.disp;name=raw[name_rva:raw.index(b'\0',name_rva)]
 check('separate_selection_state_name',name==b'CDataSelectState<Data>')
 return dict(schema='san14.reward-menu-selection-static.v1',result='PASS',checks=checks,
  sources={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),HERE/'reward_menu_handoff_gate_audit.py')},
  private_inputs={str(image):hashlib.sha256(raw).hexdigest(),str(pdata):hashlib.sha256(pd).hexdigest()},
  sections=[dict(rva=a,size=z-a,sha256=hashlib.sha256(raw[a:z]).hexdigest())for a,z in RANGES],
  selection_name=dict(rva=name_rva,value=name.decode()),
  conclusions=dict(event_one_is_selection=True,separate_state_creator=True,selection_result_read_after_wait=True,
   original_reward_selection_pointer_offset=0x480,original_layout_event_reset_offset=0x170),
  unresolved=['selection activation and return lifetime','cancel input mapping','task suspension/resumption ownership','permitted UI callback scope'],
  native_execution=False,game_access=False,production_permit=False)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive-root',type=Path,required=True);a=parser.parse_args()
 run=HERE.parents[2]/'mod_research/reward_menu_selection_audit_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 try:result=inspect(a.archive_root)
 except Exception as exc:result=dict(result='FAIL',error=repr(exc),game_access=False,production_permit=False)
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(run);print(result['result']);return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
