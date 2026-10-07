"""Offline exact-byte checks for planning-hold ABI and remaining native entry scope."""
from pathlib import Path
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
IMAGE_SHA='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'


def audit():
    image=(ROOT/'game-runtime-image.bin').read_bytes();assert hashlib.sha256(image).hexdigest()==IMAGE_SHA
    cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
    expected={0x50B782:('call','qword ptr [rax + 0x28]'),0x50B785:('mov','rbx, qword ptr [rsp + 0x30]'),
              0x7149D4:('call','0x1d1940'),0x7149D9:('mov','rcx, qword ptr [rbx + 0x548]'),
              0x1D1968:('mov','r14d, edx'),0x1D196B:('mov','rbx, rcx'),0x1D1DAF:('mov','rax, rbx'),
              0x1D6DA0:('mov','qword ptr [rsp + 8], rcx'),
              0x3F9DAF:('mov','rax, qword ptr [rsi + 0x478]'),0x3FA09A:('call','0x3fc270'),
              0x3F85F2:('call','qword ptr [r8 + 0x18]'),0x3F8606:('call','0x3fa820')}
    instructions=[]
    for address,wanted in expected.items():
        row=next(cs.disasm(image[address:address+16],address));assert(row.mnemonic,row.op_str)==wanted
        instructions.append(dict(rva=hex(address),bytes=row.bytes.hex(),instruction=f'{row.mnemonic} {row.op_str}'))
    user_return=list(cs.disasm(image[0x50B785:0x50B79A],0x50B785))
    assert [i.mnemonic for i in user_return]==['mov','mov','mov','add','pop','ret']
    assert all('rax' not in i.op_str and 'xmm' not in i.op_str for i in user_return)
    return dict(result='PASS',game_access=False,image_sha256=IMAGE_SHA,instructions=instructions,
        user_update=dict(rva='0x3F9B00',slot='0x12CC4D0',audited_caller='0x50B782',result_consumed_by_this_caller=False,
            outer_cleanup=['0x834D9B callable return','0x834DB4 done publication already happened','0x50B607 state detached'],
            body_side_effects=['0x3F9B09 state active test','0x3F9B16/1E global updater','0x3F9BB0 selection cleanup','0x3F9DDF widget virtual call','0x3FA01D advance and User phase transition'],
            production_skip_enabled=False),
        parent_game=dict(rva='0x3F8140',slot='0x12CC9E0',skip_supported=False,
            reasons=['Handles Game+474 load transition and +488 task progression.','Calls UI/global update at 3F85F2 and 3F8606 independently of User body.']),
        remaining_readonly_observation=dict(target='Bind exact native command callers to formal User/Game/UI task intervals before selecting a production skip boundary.',
            entry_points=['0x3F9B00 User Update','0x3F9DAF menu fetch','0x3FA09A menu handler call','0x3F85F2 Game global update callback','0x3F8606 Game UI update','0x1D1940 sortie body','0x1D6DA0 reward body'],
            unknowns=['Do any UI/Game/posted-message paths submit commands while formal User is held?','Which native pool thread owns each User call; may it change between frames?','Which pre-command boundary can reject without charging resources or discarding selected UI data?','How are physical input release and other command families covered?']),
        submit_gate_limit='Sortie caller 7149D9 ignores RAX; entry rejection alone cannot prove full UI transaction cancellation.',
        replay_limit='Envelope snapshot is not deep semantic ownership. Remote tickets refuse without explicit trusted capture provider; no real-game provider supplied.')


if __name__=='__main__':
    result=audit();(ROOT/'checkpoint_planning_hold_entry_audit.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(dict(result=result['result'],anchors=len(result['instructions']),game_access=False)))
