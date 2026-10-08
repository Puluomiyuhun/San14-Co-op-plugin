"""Bounded offline reward-menu source audit and archived-Update execution.

Only accepts an explicit private archive folder. Never finds/opens a process.
The 145-byte archived UI Update runs in Unicorn with explicit callee doubles;
the player wrapper/common handler do NOT run. No whole-function dump is saved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ARCHIVE_SHA256 = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
GAME_SHA256 = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'

# Small source anchors. Observing them grants no suppression/execution permit.
ANCHORS = (
    ('ui_wrapper_call', 0x67A993, 'e8b8b6faff', 'RCX=reward state; RBX=same state; [RCX+478]->layout, [layout+170]=2; RSP is before CALL'),
    ('ui_wrapper_return', 0x67A998, '85c0', 'same RSP as ui_wrapper_call; EAX is UI wrapper result, not common reward result'),
    ('wrapper_common_call', 0x626275, 'e8260bbbff', 'RCX=stack RewardArgs; R13=reward state; [RCX+10]=funding foothold; authoritative reward writes are in callee'),
    ('other_menu_branch', 0x67A9B6, 'e9a54d0100', 'RCX=reward state; tail call with Update frame removed; event code 1, cancellation NOT established'),
)


def run(archive_root):
    archive_root = Path(archive_root).resolve()
    image_path = archive_root / 'game-runtime-image.bin'
    image = image_path.read_bytes()
    before = hashlib.sha256(image).hexdigest()
    if before != ARCHIVE_SHA256:
        raise ValueError('Unsupported offline archive')
    sys.path.insert(0, str(archive_root / 'python_deps'))
    import capstone
    import unicorn as u
    from unicorn import x86_const as x
    dis = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    checks = []
    def check(name, value):
        checks.append(dict(name=name, passed=bool(value)))
    anchor_rows = []
    for name, rva, small, fields in ANCHORS:
        check(name + '_bytes', image[rva:rva + len(small)//2].hex() == small)
        anchor_rows.append(dict(event=name, rva=rva, bytes=small, capture=fields))
    instructions = {i.address:(i.mnemonic, i.op_str) for i in dis.disasm(image[0x626050:0x6264B2], 0x626050)}
    check('common_return_not_tested', [instructions[a] for a in (0x62627A,0x62627F,0x626284)] ==
          [('mov','rcx, qword ptr [rsp + 0x40]'), ('call','0x2f2bb0'), ('test','eax, eax')])
    common = {i.address:(i.mnemonic, i.op_str) for i in dis.disasm(image[0x1D6DA0:0x1D7059], 0x1D6DA0)}
    check('common_loyalty_write',common[0x1D6F91]==('mov','byte ptr [rsi + 0x120], al'))
    check('common_status_write',common[0x1D6F8A]==('mov','word ptr [rsi + 0x196], cx'))
    check('common_money_delta',common[0x1D6FD4]==('imul','edx, dword ptr [rax + rcx*8], -0x64') and
          common[0x1D6FDC]==('call','0x15bd40'))
    check('common_action_points_write',common[0x1D7001]==('mov','byte ptr [r15 + 0x14], r14b'))
    def scenario(event, wrapper_result, gate_result=0, repeats=1):
        em = u.Uc(u.UC_ARCH_X86,u.UC_MODE_64)
        em.mem_map(0x1000, 0x800000)
        em.mem_write(0x67A930, image[0x67A930:0x67A9C1])
        stack, state, layout, stop = 0x680000, 0x690000, 0x691000, 0x1000
        em.mem_write(state+0x478, struct.pack('<Q',layout))
        em.mem_write(layout+0x170, struct.pack('<I',event))
        em.mem_write(layout+0x1B0, struct.pack('<Q',0x692000))
        calls=[]
        stubs = {0x626050:('wrapper',wrapper_result), 0x3A29E0:('input_gate',gate_result),
                 0x76ECB0:('input_ui_action',0), 0x3A2700:('input_reset',0),
                 0x68F760:('other_menu',0), 0xF690:('state_manager',0x693000),
                 0x10A60:('state_request',0)}
        def hook(engine, address, size, unused):
            if address == stop:
                engine.emu_stop()
            elif address in stubs:
                label,result=stubs[address]
                calls.append(dict(callee=label, rcx=engine.reg_read(x.UC_X86_REG_RCX)))
                rsp=engine.reg_read(x.UC_X86_REG_RSP)
                ret=struct.unpack('<Q',engine.mem_read(rsp,8))[0]
                engine.reg_write(x.UC_X86_REG_RAX,result)
                engine.reg_write(x.UC_X86_REG_RSP,rsp+8)
                engine.reg_write(x.UC_X86_REG_RIP,ret)
        em.hook_add(u.UC_HOOK_CODE,hook)
        for unused in range(repeats):
            em.mem_write(stack,struct.pack('<Q',stop))
            em.reg_write(x.UC_X86_REG_RSP,stack)
            em.reg_write(x.UC_X86_REG_RCX,state)
            em.reg_write(x.UC_X86_REG_RBX,0x12345678)
            em.emu_start(0x67A930,0,count=1000)
            if em.reg_read(x.UC_X86_REG_RIP)!=stop or em.reg_read(x.UC_X86_REG_RSP)!=stack+8:
                raise AssertionError('Unbalanced/unfinished archived Update')
            if em.reg_read(x.UC_X86_REG_RBX)!=0x12345678:
                raise AssertionError('Update did not preserve RBX')
        return [c['callee'] for c in calls], struct.unpack('<I',em.mem_read(layout+0x170,4))[0]
    traces = []
    for name,event,ret,gate,repeats,expected in [
        ('idle',0,1,0,1,['input_gate']),
        ('input_gate_path',0,1,1,1,['input_gate','input_ui_action','input_reset']),
        ('other_event_one',1,1,0,1,['other_menu']),
        ('confirm_nonzero',2,1,0,1,['wrapper','state_manager','state_request']),
        ('confirm_zero_repeats',2,0,0,2,['wrapper','wrapper']),
        ('unknown_event',3,1,0,1,[])]:
        calls,after = scenario(event,ret,gate,repeats)
        check(name, calls==expected and after==event)
        traces.append(dict(case=name, event=event, wrapper_result_double=ret,
                           calls=calls, event_after=after, balanced_return=True))
    after = hashlib.sha256(image_path.read_bytes()).hexdigest()
    check('private_image_unchanged', after==before)
    return dict(schema='san14.reward-menu-source-audit.v1', passed=all(c['passed'] for c in checks),
                archive_sha256=before, archive_end_sha256=after, game_sha256=GAME_SHA256,
                checks=checks, anchors=anchor_rows, update_double_traces=traces,
                native_interception=False, native_execution=False,
                cancellation_mapping='unresolved; event 1 is not proven cancellation',
                evidence='Actual archived UI Update only; all external callees are service doubles')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=run(args.archive_root)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=result['passed'], checks=len(result['checks']), output=str(args.output))))
    raise SystemExit(0 if result['passed'] else 1)
