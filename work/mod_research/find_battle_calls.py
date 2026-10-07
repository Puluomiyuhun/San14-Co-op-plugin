"""Locate candidate direct branches into unit runtime code, offline only.
Candidates are checked by later disassembly; byte scanning alone isn't a CFG.
"""
from pathlib import Path
from bisect import bisect_right
import re,struct,json,sys
args=sys.argv[1:];sys.argv=sys.argv[:1]
import disasm_chained as d
targets={int(a,0) for a in args}
out=[]
for hit in re.finditer(rb'[\xe8\xe9]',d.image[0x1000:0x123BACF]):
    a=hit.start()+0x1000
    target=a+5+struct.unpack_from('<i',d.image,a+1)[0]
    if targets:
        if target not in targets:continue
    elif not (0x1ADE00<=target<0x1C0000 and not 0x1ADE00<=a<0x1C0000):continue
    idx=bisect_right(d.starts,a)-1
    if idx<0 or a>=d.entries[idx][1]:continue
    primary=d.primary(d.entries[idx])[0]
    out.append({'at':a,'target':target,'function':primary})
suffix='-'.join(f'{v:x}' for v in sorted(targets)) if targets else 'external-unit-runtime'
(d.ROOT/f'calls-{suffix}.json').write_text(json.dumps(out,indent=2))
from collections import defaultdict
grouped=defaultdict(list)
for r in out:grouped[r['target']].append(r)
for target,rows in sorted(grouped.items()):
    print(hex(target),'count',len(rows),'from',','.join(f"{r['function']:x}@{r['at']:x}" for r in rows[:30]))
