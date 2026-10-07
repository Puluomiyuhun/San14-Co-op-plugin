from pathlib import Path
import json,re,struct,sys,argparse

b=Path('work/mod_research/game-runtime-image.bin').read_bytes()
base=int(json.loads(Path('work/mod_research/runtime-203-08-zhanglu.json').read_text())['image_base'],16)
parser=argparse.ArgumentParser()
parser.add_argument('names',nargs='*')
parser.add_argument('--output',default='work/mod_research/command-types.json')
args=parser.parse_args()
names=args.names or ['CStrategyUnitMakeState','CStrategyUnitTargetState','CStrategyPreparedArmyState','CDepartureNode','CDepartureTroopsCreateNode']
out={}
for name in names:
    td=b.find(('.?AV'+name+'@@\0').encode())-16
    tables=[]
    if td<0:continue
    for hit in re.finditer(re.escape(struct.pack('<I',td)),b):
        col=hit.start()-12
        if col<0 or struct.unpack_from('<I',b,col)[0]!=1 or struct.unpack_from('<I',b,col+20)[0]!=col:continue
        for v in re.finditer(re.escape(struct.pack('<Q',base+col)),b):tables.append(v.start()+8)
    out[name]={'type_descriptor':td,'tables':tables,'xrefs':[], 'methods':[]}
    for v in tables:
        methods=[]
        for n in range(96):
            addr=struct.unpack_from('<Q',b,v+n*8)[0]-base
            if not 0x1000<=addr<0x123bacf:break
            methods.append(addr)
        out[name]['methods'].append(methods)
targets={v:name for name,r in out.items() for v in r['tables']}
for hit in re.finditer(rb'[\x48-\x4f][\x8d\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]',b[:19118286]):
    i=hit.start();dest=i+7+struct.unpack_from('<i',b,i+3)[0]
    if dest in targets:out[targets[dest]]['xrefs'].append(i)
Path(args.output).write_text(json.dumps(out,indent=2))
for name,r in out.items():
    print(name,'vtable',[hex(x) for x in r['tables']],'refs',[hex(x) for x in r['xrefs']])
    for methods in r['methods']:print('methods', [hex(x) for x in methods])
