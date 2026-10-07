"""Read-only Steam module/cached-interface inventory; never calls Steam or pins remote modules."""
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime, timezone
import hashlib, json, struct, sys
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P),str(P/'python_deps'),str(P.parents[1]/'outputs/san14-link')]
from battle_observer import BattleObserver
from checkpoint_push_start import process_birth, MemoryPage, file_sample

class ModuleInfo(C.Structure):
    _fields_=[('base',C.c_void_p),('size',W.DWORD),('entry',C.c_void_p)]

def main():
    reader=BattleObserver()
    try:
        m=reader.memory; birth=process_birth(reader); base=m.base
        q=lambda address:struct.unpack('<Q',m.read(address,8))[0]
        token=m.read(base+0x18D08B8,24)
        storage=struct.unpack_from('<Q',token,16)[0];vt=q(storage)
        addresses={'context_init':q(base+0x123CB28),'vtable':vt,
            'exists':q(vt+0x68),'size':q(vt+0x78),'read':q(vt+8)}
        code=m.read(addresses['context_init'],0x70)
        assert code[:16]==bytes.fromhex('40 53 48 83 ec 20 48 8b 51 08 48 8b d9 48 8b 05')
        counter=addresses['context_init']+20+struct.unpack_from('<i',code,16)[0]
        addresses['generation_counter']=counter
        assert q(counter)==struct.unpack_from('<Q',token,8)[0]
        ps=C.WinDLL('psapi',use_last_error=True)
        ps.EnumProcessModulesEx.argtypes=[W.HANDLE,C.POINTER(C.c_void_p),W.DWORD,C.POINTER(W.DWORD),W.DWORD]
        ps.EnumProcessModulesEx.restype=W.BOOL
        ps.GetModuleInformation.argtypes=[W.HANDLE,C.c_void_p,C.POINTER(ModuleInfo),W.DWORD]
        ps.GetModuleInformation.restype=W.BOOL
        ps.GetModuleFileNameExW.argtypes=[W.HANDLE,C.c_void_p,W.LPWSTR,W.DWORD]
        ps.GetModuleFileNameExW.restype=W.DWORD
        m.k.VirtualQueryEx.argtypes=[W.HANDLE,C.c_void_p,C.POINTER(MemoryPage),C.c_size_t]
        m.k.VirtualQueryEx.restype=C.c_size_t
        handles=(C.c_void_p*4096)();needed=W.DWORD()
        assert ps.EnumProcessModulesEx(m.handle,handles,C.sizeof(handles),C.byref(needed),3)
        assert needed.value<=C.sizeof(handles) and needed.value%C.sizeof(C.c_void_p)==0
        modules=[];owners={}
        allowed={str(Path(r'C:\Program Files (x86)\Steam\steamclient64.dll')).casefold(),
            str(Path(r'C:\Program Files (x86)\Steam\steamapps\common\Romance_of_the_Three_Kingdoms_14\steam_api64.dll')).casefold()}
        for handle in list(handles)[:needed.value//C.sizeof(C.c_void_p)]:
            info=ModuleInfo();assert ps.GetModuleInformation(m.handle,handle,C.byref(info),C.sizeof(info))
            labels=[label for label,address in addresses.items() if info.base<=address<info.base+info.size]
            if not labels:continue
            path=C.create_unicode_buffer(32768);n=ps.GetModuleFileNameExW(m.handle,handle,path,len(path))
            assert 0<n<len(path) and path.value.casefold() in allowed
            disk=file_sample(Path(path.value));header=m.read(info.base,0x1000)
            assert header[:2]==b'MZ'
            nt=struct.unpack_from('<I',header,0x3c)[0]
            assert nt+0x100<len(header) and header[nt:nt+4]==b'PE\0\0'
            assert struct.unpack_from('<H',header,nt+4)[0]==0x8664
            assert struct.unpack_from('<H',header,nt+24)[0]==0x20b
            assert struct.unpack_from('<I',header,nt+24+56)[0]==info.size
            row={'path':path.value,'base':info.base,'size_of_image':info.size,
                'pe_timestamp':struct.unpack_from('<I',header,nt+8)[0],
                'disk':disk,'loaded_header_bytes':len(header),
                'loaded_header_sha256':hashlib.sha256(header).hexdigest()}
            modules.append(row)
            for label in labels:
                address=addresses[label];page=MemoryPage()
                assert m.k.VirtualQueryEx(m.handle,address,C.byref(page),C.sizeof(page))==C.sizeof(page)
                assert page.Type==0x1000000 and page.State==0x1000 and page.AllocationBase==info.base
                assert not page.Protect&0x100 and page.Protect&0xff not in (0,1)
                method=label in ('context_init','exists','size','read')
                if method:assert page.Protect&0xff in (0x10,0x20,0x40,0x80)
                owners[label]={'address':address,'module_base':info.base,'rva':address-info.base,
                    'module_path':path.value,'protect':page.Protect,
                    'first_32_bytes':m.read(address,32).hex() if method else None}
        assert set(owners)==set(addresses) and len(modules)==2
        assert m.read(base+0x18D08B8,24)==token and q(storage)==vt
        assert process_birth(reader)==birth
        result={'schema':'san14.storage-module-inventory.v1','result':'PASS_READ_ONLY',
            'captured_utc':datetime.now(timezone.utc).isoformat(),
            'pid':reader.pid,'birth':birth,'base':base,'game_sha256':reader.sha256,
            'storage':storage,'vtable':vt,'cached_generation':q(counter),'modules':modules,
            'owners':owners,'game_writes':0,'native_calls':0,'modules_pinned':False,
            'full_loaded_image_verified':False,'authorize_install':False}
    finally:reader.close()
    path=P/('checkpoint_storage_module_inventory_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with path.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'result':result['result'],'modules':modules,'owners':owners}))

if __name__=='__main__':main()
