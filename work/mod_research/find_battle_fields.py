"""Offline candidate displacement search, validated by linear fragment decoding."""
import sys, struct, json
from bisect import bisect_right
args=sys.argv[1:]
sys.argv=sys.argv[:1]
import disasm_chained as d
offsets={int(a,0) for a in args} or {0x580,0x590,0x594,0x730}
hits={}
for offset in offsets:
    pattern=struct.pack('<I',offset)
    p=0
    while True:
        p=d.image.find(pattern,p,0x510000)
        if p<0:break
        k=bisect_right(d.starts,p)-1
        if k>=0 and p<d.entries[k][1]:
            hits[d.entries[k]]=True
        p+=1
records=[]
for fragment in sorted(hits):
    a,z,_=fragment
    for ins in d.decoder.disasm(d.image[a:z],a):
        if any(o.type==d.capstone.x86.X86_OP_MEM and o.mem.disp in offsets for o in ins.operands):
            root=d.primary(fragment)
            records.append({'at':hex(ins.address),'root':hex(root[0]),'instruction':ins.mnemonic+' '+ins.op_str})
print(json.dumps(records,indent=2))
(d.ROOT/('fields-'+ '-'.join(f'{n:x}' for n in sorted(offsets))+'.json')).write_text(json.dumps(records,indent=2))
