"""Bounded archived updater execution. No process discovery or current game IO."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import struct
import sys
import a_save_early_audit as old

P = Path(__file__).resolve().parent
EXTRA = {
    'inactive': (0x16BEF0, 0x16BFE7, 'eff1758d96631c5bb80c33b50705def39fdfa157cde02150d6b1c61efd19be4f'),
    'object_reset': (0x337200, 0x337279, 'f767a3a45d62e7ff8b3e5c20f96999579ab0fcc9c8fde752111bdd72f5184f0d'),
    'topcheck': (0x509640, 0x509675, '63b7bf401981a4cd0ff3976f75fdcc761e8ea8ee3df6b697ab5da8e1dd0e4116'),
    'manager_singleton': (0xF690, 0xF711, 'c04dff10f16d1bf930f6b4ecf5e7bec60911e83f11d81613042f5372adfe44fe'),
}


def check(ok, why):
    if not ok:
        raise AssertionError(why)


def execute(raw, name):
    import capstone as cs
    import unicorn as uc
    from unicorn import x86_const as x
    base, arena, stack, teb = 0x140000000, 0x50000000, 0x60010008, 0x70000000
    updater, root, node, scene, descriptor, unit = base + 0x1A38840, arena, arena+0x1000, arena+0x2000, arena+0x3000, arena+0x4000
    m = uc.Uc(uc.UC_ARCH_X86, uc.UC_MODE_64)
    m.mem_map(base, 0x2400000); m.mem_write(base, raw[:0x2400000])
    m.mem_map(arena, 0x100000); m.mem_map(stack-0x10008, 0x20000); m.mem_map(teb, 0x10000)
    def put(p, v, n=8): m.mem_write(p, int(v).to_bytes(n, 'little', signed=v<0))
    def get(p, n=8): return int.from_bytes(m.mem_read(p, n), 'little')
    put(stack, base+0x2200000)
    put(base+0x1FCA1E0, root); put(root+0x60, 0)
    put(updater+0xA0, node); put(node, descriptor); put(node+0x28, scene); put(node+0x30, 0)
    put(scene+0x28, node); put(scene+0x1C, 1, 4); put(scene+0x70, 0x12, 4)
    put(descriptor, 44, 2); put(descriptor+4, 0x1B, 4)
    put(root+0x7DF60+44*8, unit); put(unit+0x148, scene)
    put(teb+0x58, teb+0x1000); put(teb+0x1000, teb+0x2000); put(teb+0x2010, 0x7FFFFFFF, 4)
    put(base+0x203ABC0, 0, 4); put(base+0x1A38A10, 0, 4)
    m.reg_write(x.UC_X86_REG_GS_BASE, teb)
    mode = 4 if name in ('inactive-reset','inactive-busy') else 2
    put(updater+0x1C4, int(name=='active-invalid') or int(mode==4), 4)
    if name=='inactive-busy': put(scene+0x10, arena+0x5000)
    if name=='singleton-cold': put(base+0x1A38A10, 0, 4); put(teb+0x2010, 0x80000000, 4)
    start = 0x15FA20 if name.startswith('singleton') else 0x16C5F0
    m.reg_write(x.UC_X86_REG_RCX, updater); m.reg_write(x.UC_X86_REG_RSP, stack)
    d = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_64)
    native = {a for a, _, _ in (*old.RANGES.values(), *EXTRA.values())}
    entered, models, writes = [], [], []
    def step(machine, address, size, unused):
        rva=address-base
        if rva in native: entered.append(hex(rva))
        i=next(d.disasm(bytes(machine.mem_read(address,size)),address))
        if i.mnemonic!='call': return
        target=int(i.op_str,16)-base if i.op_str.startswith('0x') else None
        if target in native: return
        rcx=m.reg_read(x.UC_X86_REG_RCX); value=0
        if target==0xF720: value=arena+0x6000
        elif target==0xD140: value=mode
        elif target in (0xEF8530,0xEF8554): pass  # Explicit lock API double.
        elif target==0x161E20: pass  # Explicit eligibility false branch.
        elif target==0x337BB0: pass  # Unresolved lifecycle callee; never called pure.
        elif target==0x160E20:
            m.mem_write(rcx, struct.pack('<ffff',10.0,0.0,0.0,1.0))
        elif target==0xF1E8A8: m.reg_write(x.UC_X86_REG_XMM0,int.from_bytes(struct.pack('<f',10.0),'little'))
        elif target==0x2F2BB0: value=1
        elif target==0x1B09E0: pass  # Unresolved scene update, not claimed read-only.
        elif target==0xEF9C3C: put(base+0x1A38A10,0xFFFFFFFF,4)
        elif target in (0x159CB0,0xEF9A4C,0xEF9BDC): pass  # Constructor/runtime lifetime unknown.
        else: raise AssertionError(f'unmodeled {target!r} at {rva:x}')
        models.append(dict(site=hex(rva), target=hex(target) if target else 'indirect'))
        m.reg_write(x.UC_X86_REG_RAX,value); m.reg_write(x.UC_X86_REG_RIP,address+size)
    def write(machine, access, address, size, value, unused):
        if stack-0x10008<=address<stack+0xFFF8: return
        category='scene-object' if scene<=address<scene+0x1000 else 'updater-node' if node<=address<node+0x1000 else 'updater' if updater<=address<updater+0x200 else 'other'
        origin=scene if category=='scene-object' else node if category=='updater-node' else updater if category=='updater' else base
        writes.append(dict(pc=hex(m.reg_read(x.UC_X86_REG_RIP)-base),owner=category,offset=hex(address-origin),size=size,value=value))
    m.hook_add(uc.UC_HOOK_CODE,step); m.hook_add(uc.UC_HOOK_MEM_WRITE,write)
    m.emu_start(base+start,base+0x2200000,count=30000)
    check(m.reg_read(x.UC_X86_REG_RIP)==base+0x2200000,'archived function did not return')
    check(m.reg_read(x.UC_X86_REG_RSP)==stack+8,'original updater stack not restored')
    if name=='inactive-reset': check(get(scene+0x1C,4)==0xFFFFFFFF and get(scene+0x78)==1 and get(updater+0x1C4,4)==0,'actual object reset/mode clear missing')
    elif name=='inactive-busy': check(get(scene+0x70,4)==0x10 and get(updater+0x1C4,4)==0,'actual flags and mode writes missing')
    elif name=='active-invalid': check(get(scene+0x70,4)==0x10 and not get(node+0x28),'actual invalid-object unlink missing')
    elif name=='inactive-create': check(get(updater+0x1C4,4)==1 and '0x163c80' in entered,'actual updater active flag missing')
    elif name=='singleton-warm': check(not writes and not models and m.reg_read(x.UC_X86_REG_RAX)==updater,'warm singleton should be read-only fast path')
    elif name=='singleton-cold': check(any(row['target']=='0x159cb0' for row in models),'cold singleton constructor not reached')
    return dict(case=name,result='PASS',actual_functions=entered,actual_nonstack_writes=writes,modeled_calls=models,complete_world_exclusion=False)


def cut(raw):
    import unicorn as uc
    from unicorn import x86_const as x
    b,u,s=0x140000000,0x50000000,0x60001008
    m=uc.Uc(uc.UC_ARCH_X86,uc.UC_MODE_64);m.mem_map(b+0x3F9000,0x2000);m.mem_map(u,0x1000);m.mem_map(s-0x1008,0x3000)
    m.mem_write(b+0x3F9B00,raw[0x3F9B00:0x3FA0B4]);m.mem_write(s,(b+0x3FA0B4).to_bytes(8,'little'))
    regs=(x.UC_X86_REG_RBX,x.UC_X86_REG_RBP,x.UC_X86_REG_RSI,x.UC_X86_REG_R14,x.UC_X86_REG_R15)
    for n,v in zip(regs,(11,22,33,44,55)):m.reg_write(n,v)
    m.reg_write(x.UC_X86_REG_RCX,u);m.reg_write(x.UC_X86_REG_RSP,s)
    calls=[]
    def step(machine,a,n,_):
        if a==b+0x3F9B09: calls.append('509640 eligibility double');machine.reg_write(x.UC_X86_REG_RAX,1);machine.reg_write(x.UC_X86_REG_RIP,a+5)
        elif a==b+0x3F9B16: machine.reg_write(x.UC_X86_REG_RIP,b+0x3FA0AE)
    m.hook_add(uc.UC_HOOK_CODE,step);m.emu_start(b+0x3F9B00,b+0x3FA0B4,count=100)
    check([m.reg_read(n) for n in regs]==[11,22,33,44,55] and m.reg_read(x.UC_X86_REG_RSP)==s+8,'upstream cut must use short original epilogue')
    return dict(case='upstream-cut-original-prolog-short-epilogue',result='PASS',decision_is_model=True,modeled_calls=calls,native_bridge=False)


def main():
    private=Path(os.environ['SAN14_PRIVATE_FIXTURE_ROOT']).resolve();sys.path.insert(0,str(private/'python_deps'))
    run=P/'a_save_upstream_audit_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    sources={q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in (Path(__file__).resolve(),P/'a_save_early_audit.py')}
    result=dict(schema='san14.a-save-upstream-audit.v1',result='FAIL',game_access=False,cases=[],production_permit=False,sources=sources)
    try:
        raw=(private/'game-runtime-image.bin').read_bytes();check(hashlib.sha256(raw).hexdigest()==old.ARCHIVE_SHA,'archive identity')
        result['archive_sha256']=old.ARCHIVE_SHA;result['ranges']=[]
        for name,(a,z,h) in {**old.RANGES,**EXTRA}.items():
            check(hashlib.sha256(raw[a:z]).hexdigest()==h,'range differs '+name);result['ranges'].append(dict(name=name,start=hex(a),end=hex(z),sha256=h))
        for name in ('singleton-warm','singleton-cold','inactive-create','active-invalid','inactive-reset','inactive-busy'):
            result['cases'].append(execute(raw,name));print(name,'PASS',flush=True)
        result['cases'].append(cut(raw));check(all(hashlib.sha256((P/n).read_bytes()).hexdigest()==h for n,h in sources.items()),'source changed during audit');result['sources_unchanged']=True;result['result']='PASS'
    except Exception as exc:result['error']=repr(exc);raise
    finally:
        (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(run/'result.json')


if __name__=='__main__':main()
