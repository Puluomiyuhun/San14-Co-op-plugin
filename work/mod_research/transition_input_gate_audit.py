"""Offline input-path inspection; only reads archived bytes and the on-disk exe."""
from pathlib import Path
from bisect import bisect_right
import json, struct, sys, re
P=Path(__file__).resolve().parent
args=sys.argv[1:];sys.argv=sys.argv[:1];sys.path.insert(0,str(P))
import disasm_chained as d
import pefile
EXE=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Romance_of_the_Three_Kingdoms_14\SAN14PK_SC.exe')
PREFIX='transition_input_gate_audit'

def save(name,value):
    (P/f'{PREFIX}_{name}.json').write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps(value,indent=2,ensure_ascii=False))

def root_at(at):
    n=bisect_right(d.starts,at)-1
    if n<0 or not d.entries[n][0]<=at<d.entries[n][1]:return None
    return d.primary(d.entries[n])

def instructions(root):
    return [i for a,z,_ in sorted(set(d.groups[root]+[root])) for i in d.decoder.disasm(d.image[a:z],a)]

if args[0]=='imports':
    pe=pefile.PE(str(EXE)); names=[]
    for lib in pe.DIRECTORY_ENTRY_IMPORT:
        rows=[{'rva':hex(x.address-pe.OPTIONAL_HEADER.ImageBase),'name':x.name.decode() if x.name else f'ordinal:{x.ordinal}'} for x in lib.imports]
        rows=[x for x in rows if any(q in x['name'].lower() for q in ('input','key','message','cursor','capture','focus','active','window','joystick','joy','loadlibrary','getprocaddress'))]
        if rows:names.append({'dll':lib.dll.decode(),'entries':rows})
    save('imports',names)
elif args[0]=='disasm':
    for s in args[1:]:
        at=int(s,0);root=root_at(at)
        if root:ins=instructions(root);at=root[0]
        else:
            ins=[]
            for i in d.decoder.disasm(d.image[at:at+1024],at):
                ins.append(i)
                if i.mnemonic in ('ret','jmp'):break
        rows=[]
        for i in ins:
            refs=[hex(i.address+i.size+o.mem.disp) for o in i.operands if o.type==d.capstone.x86.X86_OP_MEM and o.mem.base==d.capstone.x86.X86_REG_RIP]
            rows.append(f'{i.address:#x}: {i.mnemonic} {i.op_str}'+(' ; '+','.join(refs) if refs else ''))
        path=P/f'{PREFIX}_{at:x}.txt';path.write_text('\n'.join(rows),encoding='utf8');print(path.name,len(rows))
elif args[0]=='xrefs':
    targets={int(x,0) for x in args[1:]};adjusted={t-s for t in targets for s in (0,1,4)};roots={}
    for align in range(4):
        end=0x123c000;raw=d.image[align:end-(end-align)%4]
        for idx,(v,) in enumerate(struct.iter_unpack('<i',raw)):
            pos=align+idx*4
            if pos+4+v in adjusted:
                root=root_at(pos)
                if root:roots[root[0]]=root
    rows=[]
    for root in roots.values():
        for i in instructions(root):
            for o in i.operands:
                target=None
                if o.type==d.capstone.x86.X86_OP_MEM and o.mem.base==d.capstone.x86.X86_REG_RIP:target=i.address+i.size+o.mem.disp
                elif o.type==d.capstone.x86.X86_OP_IMM and i.mnemonic in ('call','jmp'):target=o.imm
                if target in targets:rows.append({'function':hex(root[0]),'at':hex(i.address),'instruction':i.mnemonic+' '+i.op_str,'target':hex(target),'bytes':i.bytes.hex()})
    # Imported leaf thunks often have no unwind record; inspect exactly their 6-byte opcode.
    for marker in (b'\xff\x25',b'\xff\x15'):
        pos=0
        while True:
            pos=d.image.find(marker,pos,0x123c000)
            if pos<0:break
            target=pos+6+struct.unpack_from('<i',d.image,pos+2)[0]
            if target in targets and not root_at(pos):rows.append({'function':None,'at':hex(pos),'target':hex(target),'bytes':d.image[pos:pos+6].hex(),'leaf_thunk':True})
            pos+=1
    save('xrefs',rows)
elif args[0]=='strings':
    rows=[]
    for s in args[1:]:
        for encoding in ('ascii','utf-16le'):
            raw=s.encode(encoding);pos=0
            while True:
                pos=d.image.find(raw,pos)
                if pos<0:break
                rows.append({'text':s,'encoding':encoding,'rva':hex(pos)});pos+=1
    save('strings',rows)
elif args[0]=='region':
    at=int(args[1],0);size=int(args[2],0)
    rows=[f'{i.address:#x}: {i.mnemonic} {i.op_str}' for i in d.decoder.disasm(d.image[at:at+size],at)]
    (P/f'{PREFIX}_region_{at:x}.txt').write_text('\n'.join(rows),encoding='utf8');print('\n'.join(rows))
elif args[0]=='rtti':
    base=struct.unpack_from('<Q',d.image,0x12cd408)[0]-0x3f69f0;rows=[]
    for m in re.finditer(rb'\.\?AV[^\x00]{1,150}\x00',d.image):
        if not any(x in m.group().lower() for x in (b'input',b'keyboard',b'mouse',b'joystick')):continue
        td=m.start()-16;cols=[];x=0
        while True:
            x=d.image.find(struct.pack('<I',td),x)
            if x<0:break
            col=x-12
            if col>=0 and struct.unpack_from('<I',d.image,col)[0]==1 and struct.unpack_from('<I',d.image,col+20)[0]==col:
                vptr=0
                while True:
                    vptr=d.image.find(struct.pack('<Q',base+col),vptr)
                    if vptr<0:break
                    vt=vptr+8;methods=[]
                    for k in range(18):
                        target=struct.unpack_from('<Q',d.image,vt+k*8)[0]-base
                        if not 0x1000<=target<0x123c000:break
                        methods.append(hex(target))
                    cols.append({'vtable':hex(vt),'methods':methods,'limit':'initial consecutive code pointers; not a complete vtable size proof'});vptr+=1
            x+=1
        rows.append({'name':m.group()[:-1].decode(),'type_rva':hex(td),'vtables':cols})
    save('rtti',rows)
else:raise ValueError(args[0])
