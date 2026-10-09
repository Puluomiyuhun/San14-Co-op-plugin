"""Profile-aware startup support. No process discovery or access at import."""
import ctypes as C
from pathlib import Path
import secrets
import struct
from checkpoint_complete_live_capture import GAME_SHA, require, readable, module_approval
STEAM_HASHES = {
    'steam_api64.dll': 'e61ac9a9ac216d56abc70aaeefedc11708ef45aa1aa48f1dd313adfd9aa99150',
    'steamclient64.dll': '52ff7a513f8d5913a185ac8820eadb17d6e8e4144cd8fff36cc5bae6fa9d3fee',
}

def storage_bindings(reader,module_list,*,steam_paths,owner_module=None,owner_path=None,owner_sha=None,read_bridge=None):
    import pefile
    m=reader.memory;b=m.base;q=lambda a:struct.unpack('<Q',m.read(a,8))[0]
    modules=[]
    for name,approved in STEAM_HASHES.items():
        path=str(Path(steam_paths[name]).resolve(strict=True)).casefold()
        require(Path(path).name==name,"Wrong Steam module filename")
        found=[(a,p) for a,p in module_list if str(p).casefold()==path]
        require(len(found)==1,'Steam module path binding differs')
        modules.append(module_approval(reader,*found[0],approved))
    if owner_module is not None:
        require(owner_path and owner_sha and read_bridge,'Missing owner module approval')
        require([(a,str(p).casefold()) for a,p in module_list if str(p).casefold()==str(owner_path).casefold()]
            ==[(owner_module,str(owner_path).casefold())],'Copied owner DLL binding differs')
        modules.append(module_approval(reader,owner_module,owner_path,owner_sha))
    def owner(address,n=1):
        matches=[i for i,row in enumerate(modules) if row['base']<=address and
            address+n<=row['base']+row['sizeOfImage']]
        require(len(matches)==1,'Address is outside approved modules');return matches[0]
    def endpoint(address):
        i=owner(address,32);row=modules[i];readable(reader,address,32,allocation=row['base'],execute=True)
        code=m.read(address,32);pe=pefile.PE(row['path'],fast_load=True)
        try:require(code==pe.get_data(address-row['base'],32),'Loaded endpoint code differs from approved disk image')
        finally:pe.close()
        return dict(address=address,moduleIndex=i,first32=code.hex())
    token=m.read(b+0x18d08b8,24);callback,generation,storage=struct.unpack('<3Q',token)
    require(callback==b+0x2fcb90,'Unexpected context token callback')
    ci=q(b+0x123cb28);einit=endpoint(ci);code=m.read(ci,0x65)
    require(code[:16]==bytes.fromhex('40534883ec20488b5108488bd9488b05') and
        code[20:25]==bytes.fromhex('483bd07442') and
        code[0x5b:0x65]==bytes.fromhex('488d41104883c4205bc3'),'Unknown cached context fast path')
    counter=ci+20+struct.unpack_from('<i',code,16)[0];idx=owner(counter,8)
    readable(reader,counter,8,allocation=modules[idx]['base']);require(q(counter)==generation,'Cached generation differs')
    readable(reader,storage,8);vt=q(storage);vidx=owner(vt,0x80)
    readable(reader,vt,0x80,allocation=modules[vidx]['base']);vtbytes=m.read(vt,0x80)
    endpoints={key:endpoint(struct.unpack_from('<Q',vtbytes,off)[0])
        for key,off in (('exists',0x68),('fileSize',0x78),('read',8))}
    require(all(e['moduleIndex']==vidx for e in endpoints.values()),'Vtable method module differs')
    endpoints['contextInit']=einit
    if read_bridge:endpoints['ownedReadBridge']=endpoint(read_bridge)
    require(m.read(b+0x18d08b8,24)==token and q(storage)==vt and m.read(vt,0x80)==vtbytes,
        'Cached interface changed while capturing')
    return dict(storageModules=modules,storageModuleCount=len(modules),vtableModuleIndex=vidx,
        counterModuleIndex=idx,storage=storage,storageVtable=vt,storageCounter=counter,
        cachedGeneration=generation,contextCode=code.hex(),**endpoints)


def live_hook_evidence(reader,planning,storage,*,expected=None,baseline=None):
    """Fresh slot/page observations; HookSet's publication cache is insufficient."""
    from ctypes import wintypes as W
    from checkpoint_push_start import MemoryPage
    from checkpoint_complete_live_capture import readable
    rows=list(planning['nativeSlots'])+[(storage['storageVtable']+8,storage['read']['address'])]
    values=expected if expected is not None else [original for _,original in rows]
    require(len(values)==len(rows)==6,'Wrong hook set size')
    result=[];k=reader.memory.k
    k.VirtualQueryEx.argtypes=[W.HANDLE,C.c_void_p,C.POINTER(MemoryPage),C.c_size_t]
    k.VirtualQueryEx.restype=C.c_size_t
    for i,((slot,original),wanted) in enumerate(zip(rows,values)):
        allocation=planning['base'] if i<5 else storage['storageModules'][storage['vtableModuleIndex']]['base']
        readable(reader,slot,8,allocation=allocation)
        page=MemoryPage()
        require(k.VirtualQueryEx(reader.memory.handle,slot,C.byref(page),C.sizeof(page))==C.sizeof(page),'Cannot inspect hook page')
        actual=struct.unpack('<Q',reader.memory.read(slot,8))[0]
        require(actual==wanted,'Actual hook slot differs at index '+str(i))
        row=dict(slot=slot,original=original,observed=actual,protection=page.Protect,allocation=page.AllocationBase)
        if baseline is not None:
            require(all(row[key]==baseline[i][key] for key in ('slot','original','protection','allocation')),
                'Actual hook page binding/protection changed at index '+str(i))
        result.append(row)
    return result


def build_config(planning,storage,*,folder,target,attempt,epoch,attachment_hex,owner_binding_hex):
    """Data-only construction; native guards remain the installation authority."""
    from checkpoint_complete_live_owner_contract import Config
    cfg=Config()
    for name in ('pid','birth','base','root','world','cache','keyboard','toolbar','panel','stack',
            'stackCapacity','queue','queueCapacity','rng','expectedMode'):
        setattr(cfg,name,planning[name])
    require(cfg.expectedMode==0 and cfg.queue==cfg.queueCapacity==0,'Only exact observed empty queue/mode0 supported')
    cfg.states[:]=planning['states'];cfg.attempt=attempt;cfg.epoch=epoch;cfg.generation=attempt
    for name,value in (('attachment',attachment_hex),('ownerBinding',owner_binding_hex),
            ('nonce',secrets.token_hex(32)),('gameSha256',GAME_SHA)):
        raw=bytes.fromhex(value);require(len(raw)==32,'Token/digest size differs');getattr(cfg,name)[:]=raw
    for name,path in (('localPath',target),('installIntent',folder/'install.intent'),
            ('requestIntent',folder/'request.intent'),('identityIntent',folder/'identity.intent')):
        path=Path(path).resolve();require(len(str(path))<512 and path.is_absolute(),'Owner path too long/nonabsolute')
        if name!='localPath':require(not path.exists(),'Intent path already exists')
        setattr(cfg,name,str(path))
    require(Path(cfg.localPath).name=='svdexccSC03.s14','Wrong target leaf')
    require(storage['storageModuleCount']==3 and len(storage['storageModules'])==3,'Need exact three approved modules')
    for i,row in enumerate(storage['storageModules']):
        dst=cfg.storageModules[i]
        for name,value in row.items():
            if name in ('fileSha256','headerSha256'):getattr(dst,name)[:]=bytes.fromhex(value)
            else:setattr(dst,name,value)
    for name in ('storageModuleCount','vtableModuleIndex','counterModuleIndex','storage','storageVtable','storageCounter','cachedGeneration'):
        setattr(cfg,name,storage[name])
    for name in ('contextInit','exists','fileSize','read','ownedReadBridge'):
        src=storage[name];dst=getattr(cfg,name);dst.address=src['address'];dst.moduleIndex=src['moduleIndex']
        dst.first32[:]=bytes.fromhex(src['first32'])
    cfg.contextCode[:]=bytes.fromhex(storage['contextCode'])
    return cfg



def open_process_api(reader):
    """Preserve old API behavior while closing handles on constructor rejection."""
    from run_autonomous_pilot import ProcessAPI
    api = ProcessAPI.__new__(ProcessAPI)
    try:
        ProcessAPI.__init__(api, reader)
        return api
    except BaseException:
        if getattr(api, 'handle', None):
            api.close()
        raise
