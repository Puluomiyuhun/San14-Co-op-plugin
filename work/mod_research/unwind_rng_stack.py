"""Offline, bounded Win64 unwind of recorded RNG stacks. Never accesses the game.

Uses the game's .pdata/.xdata per Microsoft x64 exception-handling documentation.
Only version 1 ordinary frames are supported; stop instead of guessing outside
captured memory or for machine frames. Return sites are checked against actual
decoded call instructions. This is not a general-purpose Windows unwinder.
"""
from bisect import bisect_right
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'python_deps'))
import capstone

REGS = ['rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi'] + [f'r{i}' for i in range(8,16)]


class Unwinder:
    def __init__(self, image, pdata, base):
        self.image, self.base = image, base
        self.functions = [struct.unpack_from('<III',pdata,i) for i in range(0,len(pdata)-11,12)]
        self.functions = sorted(e for e in self.functions if 0 < e[0] < e[1] <= len(image))
        self.starts = [e[0] for e in self.functions]
        self.md = capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
        self.call_cache = {}

    def function(self, rva):
        i = bisect_right(self.starts,rva)-1
        return self.functions[i] if i >= 0 and rva < self.functions[i][1] else None

    def call_before(self, rva):
        if rva in self.call_cache:
            return self.call_cache[rva]
        entry = self.function(rva-1)
        answer = None
        if entry:
            # Decode from a known function/fragment boundary, not arbitrary bytes.
            for ins in self.md.disasm(self.image[entry[0]:rva],entry[0]):
                if ins.address+ins.size == rva and ins.mnemonic == 'call':
                    answer = {'rva':hex(ins.address),'instruction':ins.mnemonic+' '+ins.op_str}
        self.call_cache[rva] = answer
        return answer

    def unwind_one(self, regs, stack_read):
        regs = dict(regs)
        rva = regs['rip']-self.base
        entry = self.function(rva)
        if entry is None:
            # RNG routines have been independently disassembled as stackless leaves.
            if not (0x3aa390 <= rva < 0x3aa450 or 0x3aa7c0 <= rva < 0x3aa830):
                raise ValueError('Unverified leaf at '+hex(rva))
        seen = set()
        first = True
        while entry:
            begin,end,info = entry
            if info in seen:
                raise ValueError('Cyclic unwind chain')
            seen.add(info)
            version_flags,prolog,count,frame = struct.unpack_from('<BBBB',self.image,info)
            if version_flags & 7 != 1:
                raise ValueError('Unsupported unwind version')
            flags = version_flags >> 3
            framereg, frameoff = frame & 15, (frame >> 4)*16
            # SAVE offsets use the fixed-frame base, before any PUSH unwind.
            fixed = regs[REGS[framereg]]-frameoff if framereg else regs['rsp']
            code_index = 0
            while code_index < count:
                codepos, packed = struct.unpack_from('<BB',self.image,info+4+2*code_index)
                op, arg = packed & 15, packed >> 4
                extra = {0:0,1:(1 if arg==0 else 2),2:0,3:0,4:1,5:2,8:1,9:2}.get(op)
                if extra is None or (op==1 and arg>1):
                    raise ValueError('Unsupported unwind opcode '+str(op))
                if code_index+extra >= count:
                    raise ValueError('Truncated unwind codes')
                value = 0
                if extra:
                    value = int.from_bytes(self.image[info+6+2*code_index:info+6+2*(code_index+extra)],'little')
                active = not first or rva-begin >= codepos
                if active:
                    if op == 0:
                        regs[REGS[arg]]=stack_read(regs['rsp']); regs['rsp']+=8
                    elif op == 1:
                        regs['rsp'] += value*(8 if arg==0 else 1)
                    elif op == 2:
                        regs['rsp'] += arg*8+8
                    elif op == 3:
                        regs['rsp'] = regs[REGS[framereg]]-frameoff
                    elif op in (4,5):
                        regs[REGS[arg]] = stack_read(fixed+value*(8 if op==4 else 1))
                    # XMM restoration does not affect integer frame recovery.
                code_index += extra+1
            entry = struct.unpack_from('<III',self.image,info+4+2*((count+1)&~1)) if flags & 4 else None
            first = False
        slot = regs['rsp']
        regs['rip'] = stack_read(slot)
        regs['rsp'] += 8
        return regs,slot

    def walk(self, row):
        regs = dict(row['registers'])
        start = regs['rsp']; raw = bytes.fromhex(row['stack_hex'])
        def read(address):
            off = address-start
            if off < 0 or off+8 > len(raw):
                raise ValueError('Beyond captured stack at '+hex(off))
            return struct.unpack_from('<Q',raw,off)[0]
        frames=[]; stopped='Frame limit'
        for depth in range(48):
            rva=regs['rip']-self.base
            if not 0 <= rva < len(self.image):
                stopped='Outside game module'; break
            entry=self.function(rva)
            call=self.call_before(rva) if depth else None
            frames.append({'pc_rva':hex(rva),'function_fragment':hex(entry[0]) if entry else None,
                           'rsp_offset':hex(regs['rsp']-start),'preceding_call':call,
                           'nonvolatile':{k:hex(v) for k,v in regs.items() if k not in ('rip','rsp')}})
            if depth and not call:
                stopped='Return site not verified as a decoded call'; break
            try:
                nextregs,slot=self.unwind_one(regs,read)
            except (ValueError,KeyError,struct.error) as error:
                stopped=str(error); break
            frames[-1]['return_slot_offset']=hex(slot-start)
            if nextregs['rsp']<=regs['rsp']:
                stopped='Non-increasing stack pointer'; break
            regs=nextregs
        return {'frames':frames,'stopped':stopped,
                'scope':'Version 1 ordinary frames only, call-site checked; bounded by 4096-byte capture. No general epilog simulation.'}


def main():
    folder=ROOT/'lockstep-traces'/sys.argv[1]
    metadata=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    base=int(metadata['base'],16)
    u=Unwinder((ROOT/'game-runtime-image.bin').read_bytes(),(ROOT/'runtime-pdata.bin').read_bytes(),base)
    rows=[json.loads(s) for s in (folder/'trace.jsonl').read_text(encoding='utf-8').splitlines()]
    out=[{'seq':r['seq'],'event':r['event'],'before':r['before'],'after':r['after'],
          'date':r.get('date'),'states':r['states'],'rbx_type':r.get('rbx_type'),
          'unwind':u.walk(r)} for r in rows if r['event'] in ('rng_set','rng_update')]
    (folder/'unwound-stacks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([{'seq':r['seq'],'event':r['event'],'before':r['before'],'after':r['after'],
                      'states':r['states'],'rbx_type':r['rbx_type'],
                      'frames':[f['pc_rva'] for f in r['unwind']['frames']],
                      'stopped':r['unwind']['stopped']} for r in out],ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
