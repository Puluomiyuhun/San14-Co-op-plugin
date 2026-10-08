"""Read-only archive audit plus execution of the original User action tail.

The interception decision and external callees are modeled here. The separate
PE fixture exercises the real source patches/bridge/unwind and A save owner.
No game image, archive bytes or extracted function is written to this repo.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import struct
import sys

ARCHIVE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
RANGES = ((0x3F8140, 0x5DB, '6689167731d268ca838b2490569022f8412b40f75869f9933aaf0e8af004b69f'),
          (0x1AC3C0, 0x63, '8d941d86ab42f55bbf1878f46d1e05aca7dd298474030c8cc0fd7d534b8670d6'),
          (0x3FA820, 32, 'bc615e704555f37b2e7ba11edc350cf8e633027d21d0f90c84bf7bf1c86d62ff'),
          (0x3F9B00, 0x5B4, '20dac87aef24debe8d58eac2036fca2b79149da970b7d1a90fb45cfb2b3eab94'))
UNHANDLED = ((0x3F9B16, 'e8055fd6ff', 'User earlier updater -> 15FA20'),
             (0x3F9B1E, 'e8cd2ad7ff', 'User earlier updater -> 16C5F0'),
             (0x3F9BB0, 'e80b83eaff', 'User pre-cut selection cleanup -> 2A1EC0'),
             (0x3F9C75, 'e8361d0000', 'User pre-cut selected-object update -> 3FB9B0'),
             (0x3F9CDF, 'e8cc1c0000', 'second pre-cut selected-object update -> 3FB9B0'),
             (0x3F9D45, 'e8661c0000', 'third pre-cut selected-object update -> 3FB9B0'),
             (0x3F9D7F, 'e86cf1feff', 'User earlier selection handler -> 3E8EF0'),
             (0x51234A, 'e891e8ffff', 'window dispatch -> 510BE0'),
             (0x510C1C, 'e8af2de9ff', 'mouse message preprocessing -> 3A39D0'),
             (0xF4C948, 'ff5050', 'keyboard device buffered polling'),
             (0xF4B458, 'ff5048', 'mouse device state polling'),
             (0xF4AB13, 'ff5048', 'controller device polling'),
             (0xF4AAB9, 'ff5008', 'alternate controller polling'),
             (0x509BEA, 'e8e199e9ff', 'Root keyboard/controller cache translation'),
             (0x509BFA, 'e81196e9ff', 'Root mouse cache translation'))


def require(ok, why):
    if not ok:
        raise ValueError(why)


def tail(raw, held, advance):
    import capstone as cs
    import unicorn as uc
    from unicorn import x86_const as x
    base, user, game, panel, toolbar, widget, vtable, stack = (0x140000000, 0x50000000,
        0x50002000, 0x50004000, 0x50006000, 0x50008000, 0x5000A000, 0x60001000)
    engine = uc.Uc(uc.UC_ARCH_X86, uc.UC_MODE_64)
    engine.mem_map(base, 0x2400000)
    engine.mem_map(user, 0x10000)
    engine.mem_map(stack-0x1000, 0x3000)
    engine.mem_write(base+0x3F9DAF, raw[0x3F9DAF:0x3FA0B4])
    def put(at, value, size):
        engine.mem_write(at, int(value).to_bytes(size, 'little', signed=value < 0))
    def get(at, size):
        return int.from_bytes(engine.mem_read(at, size), 'little')
    put(user+0x478, toolbar, 8); put(user+0x618, widget, 8); put(user+0x470, 2, 4)
    put(widget, vtable, 8); put(vtable+0x28, base+0x100, 8)
    put(game+0x480, panel, 8); put(game+0x47C, int(advance), 4)
    put(panel+0x1B0, int(advance), 4); put(toolbar+0x88, -1 if advance else 10, 4)
    # Reconstruct the stack at the tail of the original User prolog. Its real
    # archived epilogue must restore these exact callee-saved values.
    for off, value in ((0x40,0x44),(0x48,base+0x3FA0B4),(0x50,0x11),(0x58,0x22),(0x38,0x33)):
        put(stack+off, value, 8)
    engine.reg_write(x.UC_X86_REG_RSP, stack); engine.reg_write(x.UC_X86_REG_RSI, user)
    engine.reg_write(x.UC_X86_REG_RBP, 0)
    decoder = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_64)
    calls, writes = [], []
    watched={user+0x470:'phase',game+0x47C:'advance',panel+0x1B0:'panel',toolbar+0x88:'menu'}
    def code(machine, address, size, _):
        rva=address-base
        if rva==0x3F9DAF and held:
            machine.reg_write(x.UC_X86_REG_RIP,base+0x3FA09F); return
        row=next(decoder.disasm(bytes(machine.mem_read(address,size)),address))
        if row.mnemonic=='call':
            target=int(row.op_str,16)-base if row.op_str.startswith('0x') else None
            calls.append(target)
            result=game if target==0x509460 else 0
            machine.reg_write(x.UC_X86_REG_RAX,result)
            machine.reg_write(x.UC_X86_REG_RIP,address+size)
    def write(_, access, at, size, value, context):
        if at in watched: writes.append(dict(field=watched[at],size=size,value=value))
    engine.hook_add(uc.UC_HOOK_CODE,code); engine.hook_add(uc.UC_HOOK_MEM_WRITE,write)
    engine.emu_start(base+0x3F9DAF,base+0x3FA0B4,count=5000)
    require(engine.reg_read(x.UC_X86_REG_RIP)==base+0x3FA0B4,'Tail did not return')
    require([engine.reg_read(reg) for reg in (x.UC_X86_REG_RBX,x.UC_X86_REG_RBP,x.UC_X86_REG_R14,x.UC_X86_REG_RSI)]==[0x11,0x22,0x33,0x44], 'Original epilogue did not restore nonvolatile registers')
    after=dict(phase=get(user+0x470,4),advance=get(game+0x47C,4),panel=get(panel+0x1B0,4),menu=get(toolbar+0x88,4))
    if held:
        require(not calls and not writes and after==dict(phase=2,advance=int(advance),panel=int(advance),menu=0xFFFFFFFF if advance else 10),'Held cut changed input or phase')
    elif advance:
        require(after==dict(phase=5,advance=0,panel=0,menu=0xFFFFFFFF) and 0x2E84A0 in calls,'Original tail did not expose advance side effects')
    else:
        require(after['menu']==0xFFFFFFFF and 0x3FC270 in calls,'Original tail did not consume menu command')
    return dict(held=held,advance_requested=advance,after=after,actual_archived_writes=writes,
                modeled_external_call_targets=[hex(n) if n is not None else 'widget virtual' for n in calls])


def main():
    value=os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT','')
    require(value,'Set SAN14_PRIVATE_FIXTURE_ROOT; no archive read')
    private=Path(value).resolve();sys.path.insert(0,str(private/'python_deps'))
    raw=(private/'game-runtime-image.bin').read_bytes()
    require(hashlib.sha256(raw).hexdigest()==ARCHIVE_SHA,'Private archive identity differs')
    for at,size,want in RANGES: require(hashlib.sha256(raw[at:at+size]).hexdigest()==want,f'Source hash differs: {at:x}')
    for at,hexbytes,_ in UNHANDLED:
        expected=bytes.fromhex(hexbytes);require(raw[at:at+len(expected)]==expected,f'Uncovered anchor differs: {at:x}')
    require(raw[0x3F9DAF:0x3F9DB6]==bytes.fromhex('488b8678040000'),'Early User source differs')
    require(raw[0x3F8606:0x3F860B]==bytes.fromhex('e815220000'),'Direct panel source differs')
    rows=[tail(raw,held,advance) for held in (False,True) for advance in (False,True)]
    result=dict(schema='san14.a-save-action-gate-sources.v1',result='PASS',game_access=False,
        archive_sha256=ARCHIVE_SHA,original_tail_execution=rows,
        external_calls_modeled=True,branch_decision_modeled=True,actual_bridge_test='a_save_action_gate_test.py',
        sources=[dict(rva=hex(a),size=n,sha256=h) for a,n,h in RANGES],
        covered=['Game/global UI owner and actual panel call 3F8606',
                 'claimed save-lane User tail before 3F9DBF menu read / 3F9DC6 menu clear',
                 'User advance latches 3F9F9D/3F9FA6; writes 3FA01D/3FA03C and phase 3FA05F/3FA072',
                 'User downstream 3F9EFA Modifier22 and 3FA09A command dispatch ONLY through this held tail'],
        unhandled=[dict(rva=hex(a),description=m) for a,_,m in UNHANDLED],
        limits=['Raw User early body remains active; ordinary unclaimed User must use separate User hold between saves',
                'Other callers of panel/menu/input leaves; posted messages, physical releases/focus, all thread writes',
                'Production source publisher/thread drain and real SAN14 validation not installed',
                'CET hardware shadow-stack processes are explicitly refused'],
        full_input_hold=False,save_authorized=False,room_ready=False)
    out=Path(__file__).resolve().parent/'a_save_action_gate_sources_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result='PASS',cases=len(rows),path=str(out/'result.json'))))


if __name__=='__main__': main()
