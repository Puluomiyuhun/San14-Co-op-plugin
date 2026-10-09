"""Offline compiler layouts and bounded disassembly of the exact retained DLL.

Never opens a target process or invokes any target export.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,sys,re
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
sys.path.insert(0,str(PRIVATE/'python_deps'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    import pefile,capstone
    run=PRIVATE/'a_save_runtime_layout_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    build=PRIVATE/'a_save_runtime_exports_runs'/'20261009-123451-722629'/'production'/'build';dll=build/'a_save_local_runtime.dll'
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags=f'/nologo /std:c++17 /EHa /O2 /MT /I"{PRIVATE}" /I"{P}"'
    helper=run/'runtime.cpp';helper.write_text('#include "a_save_local_runtime.h"\nstatic_assert(sizeof(a_save_local_runtime::Runtime)>0);\n')
    jobs=[('runtime',helper,'Runtime'),('owner',P/'planning_checkpoint_save_owner.cpp','Impl'),('driver',P/'checkpoint_fresh_save.cpp','Impl'),
      ('state',P/'planning_checkpoint_save_owner.cpp','State'),('inputgate',P/'a_save_scoped_gate.cpp','Impl'),('inputgate-report',P/'a_save_scoped_gate.cpp','Report'),
      ('storagegate',P/'checkpoint_serialized_storage_gate.cpp','Gate'),('storage-report',P/'checkpoint_serialized_storage_gate.cpp','Report'),('file-evidence',P/'checkpoint_fresh_save.cpp','Evidence')]
    commands=[f'cl {flags} /d1reportSingleClassLayout{kind} /c "{source}" /Fo:layout_{name}.obj > {name}.txt 2>&1\nif errorlevel 1 exit /b 1' for name,source,kind in jobs]
    commands+=[f'link /nologo /DLL /OUT:a_save_local_runtime.dll /MAP:runtime.map /WHOLEARCHIVE:"{build/"a_save_held_ipc.lib"}" "{build/"production_reward.obj"}" "{build/"planning.lib"}" bcrypt.lib advapi32.lib > map-link.txt 2>&1']
    cmd=run/'layouts.cmd';cmd.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(commands)+'\n')
    proc=subprocess.run(['cmd','/c',str(cmd)],cwd=run,capture_output=True,text=True,errors='replace',timeout=90)
    pe=pefile.PE(str(dll));image=pe.get_memory_mapped_image();md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
    exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name};out={}
    for name in ('ASaveRuntimeSnapshot','ASaveRuntimePrepare'):
        pending=[exports[name]];seen=set();rows=[]
        while pending and len(seen)<6:
            rva=pending.pop(0)
            if rva in seen:continue
            seen.add(rva);instructions=[]
            for n,i in enumerate(md.disasm(image[rva:rva+2048],rva)):
                if n>=180:break
                row={'rva':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
                for op in i.operands:
                    if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:row['rip_target']=hex(i.address+i.size+op.mem.disp)
                if i.mnemonic in ('call','jmp') and i.operands and i.operands[0].type==capstone.x86.X86_OP_IMM:
                    target=i.operands[0].imm
                    if 0x1000<=target<len(image):pending.append(target)
                instructions.append(row)
                if i.mnemonic in ('ret','int3') or i.mnemonic=='jmp':break
            rows.append({'entry':hex(rva),'instructions':instructions})
        out[name]=rows
    mapped=pefile.PE(str(run/'a_save_local_runtime.dll'));sections=[]
    for a,b in zip(pe.sections,mapped.sections):sections.append(dict(name=a.Name.rstrip(b'\0').decode(),rva=a.VirtualAddress,same_rva=a.VirtualAddress==b.VirtualAddress,same_bytes=a.get_data()==b.get_data()))
    verified=all(row['same_rva'] and row['same_bytes'] for row in sections if row['name']!='.rdata')
    # Map-only re-link changes the export/debug timestamp in rdata. No addresses
    # are consumed unless code, data, unwind and relocation sections all match.
    symbols={}
    for line in (run/'runtime.map').read_text().splitlines():
        if '?runtime@?' in line or ('?state@?' in line and '@a_save_report_owner@@' in line):
            name='runtime_pointer_rva' if '?runtime@?' in line else 'report_state_rva'
            address=re.search(r'\s([0-9A-Fa-f]{16})\s',line)
            if address:symbols[name]=int(address.group(1),16)-pe.OPTIONAL_HEADER.ImageBase
    assert proc.returncode==0 and verified and len(symbols)==2,'Layout/map evidence incomplete'
    pe.close();mapped.close();(run/'disassembly.json').write_text(json.dumps(out,indent=2)+'\n')
    result={'result':'PASS_OFFLINE_LAYOUT','compiler_exit':proc.returncode,'game_access':False,'dll':str(dll),'dll_sha256':sha(dll),'map_identity':sections,'symbols':symbols,'sources':{n:sha(P/n) for n in ('a_save_runtime_exports_layout.py','a_save_local_runtime.h','planning_checkpoint_save_owner.cpp','checkpoint_fresh_save.cpp','a_save_scoped_gate.cpp','checkpoint_serialized_storage_gate.cpp','native_storage_read_core.h')},'files':{p.name:sha(p) for p in run.iterdir() if p.is_file()}}
    f=run/'result.json';f.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'path':str(f),'compiler_exit':proc.returncode}));return proc.returncode
if __name__=='__main__':raise SystemExit(main())
