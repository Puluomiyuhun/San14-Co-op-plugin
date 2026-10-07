import ctypes as C
from ctypes import wintypes as W
import json, struct, sys, re, time
from pathlib import Path
sys.path.insert(0, str(Path('outputs/san14-link').resolve()))
from readonly_probe import Memory

class MBI(C.Structure):
    _fields_=[('BaseAddress',C.c_void_p),('AllocationBase',C.c_void_p),
              ('AllocationProtect',W.DWORD),('PartitionId',W.WORD),
              ('RegionSize',C.c_size_t),('State',W.DWORD),('Protect',W.DWORD),('Type',W.DWORD)]

m=Memory(int(sys.argv[1]));start=time.monotonic()
m.k.VirtualQueryEx.argtypes=[W.HANDLE,C.c_void_p,C.POINTER(MBI),C.c_size_t]
m.k.VirtualQueryEx.restype=C.c_size_t
vt=json.loads(Path('work/mod_research/vtables.json').read_text())
patterns={struct.pack('<Q',m.base+r):name for name,rs in vt.items() for r in rs}
regex=re.compile(b'|'.join(re.escape(x) for x in patterns))
found={name:[] for name in vt};address=0;scanned=0;regions=0
try:
    while address<0x7fffffffffff:
        info=MBI()
        if not m.k.VirtualQueryEx(m.handle,address,C.byref(info),C.sizeof(info)):break
        location=info.BaseAddress or 0;size=info.RegionSize;address=location+size
        if not size:break
        if info.State!=0x1000 or info.Type!=0x20000 or info.Protect&0x101:continue
        if info.Protect&0xff not in (0x04,0x08,0x40,0x80):continue
        regions+=1
        for off in range(0,size,1024*1024):
            n=min(1024*1024,size-off)
            try: data=m.read(location+off,n)
            except OSError:continue
            scanned+=len(data)
            for hit in regex.finditer(data):
                a=location+off+hit.start()
                if a%8==0:
                    name=patterns[hit.group()]
                    if len(found[name])<30000:found[name].append(a)
            if scanned>2*1024**3 or time.monotonic()-start>40:break
        if scanned>2*1024**3 or time.monotonic()-start>40:break
finally:m.close()
Path('work/mod_research/objects.json').write_text(json.dumps(found,indent=2))
print('Scanned',scanned,'bytes in',regions,'regions;',round(time.monotonic()-start,2),'seconds')
for name,items in found.items(): print(name,len(items),[hex(x) for x in items[:12]])
