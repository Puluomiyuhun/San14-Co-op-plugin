"""Read retained message resources after the capture; never execute a message."""
import json
from pathlib import Path
import struct
from lockstep_baseline import sample,BattleObserver

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'lockstep-traces/load-rng-run-e'
trace=[json.loads(s) for s in (RUN/'trace.jsonl').read_text(encoding='utf-8').splitlines()]
stacks=json.loads((RUN/'unwound-stacks.json').read_text(encoding='utf-8'))
r=BattleObserver()
try:
    before=sample(r); m=r.memory
    manager=m.base+0x18cbf00
    r.require_type(manager,'CMessageManager')
    def rawptr(addr):return struct.unpack('<Q',m.read(addr,8))[0]
    def typename(addr):
        try:
            vt=rawptr(addr)
            if not m.base<=vt<m.base+m.image_size:return None
            col=rawptr(vt-8)
            if not m.base<=col<m.base+m.image_size-24:return None
            sig,_,_,td,_,self_rva=struct.unpack('<6I',m.read(col,24))
            if sig!=1 or col-m.base!=self_rva or td>=m.image_size-160:return None
            return m.read(m.base+td+16,128).split(b'\0')[0].decode('ascii')
        except (OSError,RuntimeError,UnicodeError):return None
    def text16(data):
        # Plain decoding is diagnostic: compiled message streams contain controls.
        s=data[:len(data)//2*2].decode('utf-16le',errors='replace')
        return ''.join(c if c.isprintable() else f'<{ord(c):02x}>' for c in s)
    out={'scope':'Resources and object RTTI read AFTER observer detached; not a historical snapshot of mutable object contents.',
         'resource_window_warning':'The +0x58 buffer can be refilled while keeping its address. The recorded +0x1274 cursor is not established as a linear offset in the current buffer. These diagnostic windows and retained output MUST NOT identify the text executed at the breakpoint.',
         'manager_rva':hex(manager-m.base),'script_windows':[], 'frames':[]}
    seen=set()
    for row in trace:
        if row.get('rbx_type')!='.?AVCMessageManager@@':continue
        d=row['rbx_diagnostic']; key=(d['field_58'],d['field_1274'])
        if key in seen:continue
        seen.add(key)
        pointer,offset=key
        assert pointer==rawptr(manager+0x58), 'Message buffer address changed since trace'
        start=max(0,offset-112)
        blob=m.read(pointer+start,384)
        (RUN/f'message-window-{offset}.bin').write_bytes(blob)
        out['script_windows'].append({'offset':offset,'start':start,'mode_observed':d['field_1270'],
            'hex':blob.hex(),'utf16_even_diagnostic':text16(blob),'utf16_odd_diagnostic':text16(blob[1:])})
    buf=rawptr(manager+0x1280)
    if 0x10000<=buf<0x7fffffffffff:
        output=m.read(buf,2048)
        out['retained_output_utf16']=output.decode('utf-16le',errors='replace').split('\0')[0]
    for row in stacks:
        selected=[]
        for f in row['unwind']['frames']:
            if f['pc_rva'] not in ('0x2d40a2','0x1ab6f9','0x1acb26','0x50b785','0x5e54e5','0x5e54f6','0x5de3ed','0x5dd7c8'):continue
            entry={'pc_rva':f['pc_rva'],'registers':f['nonvolatile'],'current_pointed_object_types':{}}
            for reg,s in f['nonvolatile'].items():
                addr=int(s,16)
                if addr<0x10000:continue
                typ=typename(addr)
                if typ:entry['current_pointed_object_types'][reg]=typ
            if f['pc_rva']=='0x2d40a2':
                # 2D4040 prolog retains normalized input message ID in EBX.
                entry['observed_message_id']=int(f['nonvolatile']['rbx'],16)&0xffffffff
            selected.append(entry)
        out['frames'].append({'seq':row['seq'],'selected':selected})
    assert before==sample(r), 'Game data changed during read-only inspection'
    out['game_sample_unchanged']=True
    (RUN/'message-resources.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in out.items() if k!='script_windows'},ensure_ascii=True,indent=2))
finally:r.close()
