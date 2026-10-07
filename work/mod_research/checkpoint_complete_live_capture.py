"""Fresh bounded read-only bindings for the single-load owner. No native calls."""
import ctypes as C
from ctypes import wintypes as W
import hashlib,struct
from pathlib import Path
from checkpoint_push_start import MemoryPage,file_sample,process_birth

GAME_SHA='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
STEAM=Path(r'C:\Program Files (x86)\Steam')
STEAM_MODULES={
    str(STEAM/'steamapps/common/Romance_of_the_Three_Kingdoms_14/steam_api64.dll').casefold():
        'e61ac9a9ac216d56abc70aaeefedc11708ef45aa1aa48f1dd313adfd9aa99150',
    str(STEAM/'steamclient64.dll').casefold():
        '52ff7a513f8d5913a185ac8820eadb17d6e8e4144cd8fff36cc5bae6fa9d3fee'}
SOURCE=STEAM/'userdata/391007908/872410/remote/svdexSC34.s14'
TARGET=SOURCE.parent/'svdexccSC03.s14'
SOURCE_SHA='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
TARGET_SHA='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
TARGET_SIZE=274880

def require(value,message):
    if not value:raise RuntimeError(message)

def readable(reader,address,size,*,allocation=None,execute=False):
    require(type(address)is int and type(size)is int and address>=0x10000 and
        size>0 and address+size<=0x7fffffffffff,'Invalid memory range')
    k=reader.memory.k
    k.VirtualQueryEx.argtypes=[W.HANDLE,C.c_void_p,C.POINTER(MemoryPage),C.c_size_t]
    k.VirtualQueryEx.restype=C.c_size_t
    at=address;end=address+size
    while at<end:
        page=MemoryPage()
        require(k.VirtualQueryEx(reader.memory.handle,at,C.byref(page),C.sizeof(page))==C.sizeof(page),
            'Cannot query binding page')
        prot=page.Protect&255
        require(page.State==0x1000 and not page.Protect&0x100 and prot in (2,4,8,0x20,0x40,0x80),
            'Binding page is not readable')
        if allocation is not None:require(page.AllocationBase==allocation and page.Type==0x1000000,'Wrong image owner')
        if execute:require(prot in (0x20,0x80),'Function page is not approved RX image code')
        nxt=page.BaseAddress+page.RegionSize
        require(nxt>at,'Nonadvancing memory region');at=min(nxt,end)

def planning_bindings(reader):
    from startup_identity_reader import capture_startup_context
    m=reader.memory;b=m.base;q=lambda a:struct.unpack('<Q',m.read(a,8))[0]
    require(reader.sha256==GAME_SHA,'Unsupported game build')
    birth=process_birth(reader);context=capture_startup_context(reader);s=context['snapshot']
    require(s['date']==dict(year=203,month=8,day=11,period='中旬') and
        s['player']['force_id']==12 and s['player']['ruler_id']==666,'Wrong source scenario/player')
    names=['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']
    states=reader.state_objects();require([n for n,_ in states]==names,'Not idle formal planning')
    states=[a for _,a in states];manager=b+0x19e7310
    head=m.read(manager,0x50);stack_count,stack_cap,stack=struct.unpack_from('<QQQ',head,0x10)
    queue_count,queue_cap,queue=struct.unpack_from('<QQQ',head,0x30)
    require(stack_count==5 and 5<=stack_cap<=4096 and queue_count==0 and 0<=queue_cap<=4096,
        'Unexpected planning vector shape')
    require(bool(queue)==bool(queue_cap),'Invalid empty vector binding')
    readable(reader,stack,stack_cap*8)
    require(list(struct.unpack('<5Q',m.read(stack,40)))==states,'Stack pointers differ')
    if queue_cap:readable(reader,queue,queue_cap*16)
    root=q(b+0x1fca1e0);world=q(root+0x85130);cache=q(b+0x2025318)
    mode=struct.unpack('<I',m.read(cache+8,4))[0];require(mode in (0,1),'Unknown initial cache mode')
    toolbar=q(states[4]+0x478);panel=q(states[2]+0x480);keyboard=q(b+0x1fca0a0)
    require(struct.unpack('<i',m.read(toolbar+0x88,4))[0]==-1 and
        struct.unpack('<I',m.read(states[4]+0x470,4))[0]==2,'Pending menu command or wrong User phase')
    for p,n in ((states[4],0x668),(states[2],0x488),(cache,0x3f4),(toolbar,0x8c),(panel,0x1f8),(keyboard,0x258)):
        readable(reader,p,n)
    rng=struct.unpack('<I',m.read(b+0x18eb8b0,4))[0]
    slots=[]
    for srva,frva in ((0x12cc4d0,0x3f9b00),(0x12db4e8,0x4aa200),(0x12cc9e0,0x3f8140),
            (0x12dbd90,0x4a85c0),(0x138e8d0,0x4fabc0)):
        require(q(b+srva)==b+frva,'Foreign native hook present');slots.append((b+srva,b+frva))
    require(q(b+0x1fca1e0)==root and q(root+0x85130)==world and q(b+0x2025318)==cache,
        'World/cache rebuilt while capturing')
    require(m.read(manager+0x10,0x38)==head[0x10:0x48] and process_birth(reader)==birth,
        'Attachment/stack/queue changed while capturing')
    require(capture_startup_context(reader)==context,'Planning context changed while capturing')
    return dict(pid=reader.pid,birth=birth,base=b,states=states,root=root,world=world,cache=cache,
        keyboard=keyboard,toolbar=toolbar,panel=panel,stack=stack,stackCapacity=stack_cap,
        queue=queue,queueCapacity=queue_cap,rng=rng,expectedMode=mode,context=context,nativeSlots=slots,
        gameSha256=GAME_SHA,atomic_snapshot=False)

def module_approval(reader,base,path,approved_sha):
    import pefile
    data=file_sample(path);require(data['sha256']==approved_sha,'Module file differs from approved build')
    readable(reader,base,4096,allocation=base);raw=reader.memory.read(base,4096)
    require(raw[:2]==b'MZ','Bad loaded DOS header');nt=struct.unpack_from('<I',raw,0x3c)[0]
    require(0x40<=nt<=0x800 and raw[nt:nt+4]==b'PE\0\0','Bad loaded PE header')
    machine,timestamp=struct.unpack_from('<H',raw,nt+4)[0],struct.unpack_from('<I',raw,nt+8)[0]
    size=struct.unpack_from('<I',raw,nt+24+56)[0]
    require(machine==0x8664 and struct.unpack_from('<H',raw,nt+24)[0]==0x20b,'Not x64 PE')
    pe=pefile.PE(str(path),fast_load=True)
    try:require(pe.FILE_HEADER.TimeDateStamp==timestamp and pe.OPTIONAL_HEADER.SizeOfImage==size,
        'Disk and loaded PE identity differ')
    finally:pe.close()
    return dict(base=base,path=str(path),sizeOfImage=size,timestamp=timestamp,fileSize=data['size'],
        fileSha256=approved_sha,headerSha256=hashlib.sha256(raw).hexdigest())

def storage_bindings(reader,module_list,*,owner_module=None,owner_path=None,owner_sha=None,read_bridge=None):
    import pefile
    m=reader.memory;b=m.base;q=lambda a:struct.unpack('<Q',m.read(a,8))[0]
    modules=[]
    for path,approved in STEAM_MODULES.items():
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

def known_snapshot(reader,*,expected_user_hook):
    import checkpoint_live_capture as capture
    from startup_identity_reader import capture_startup_context
    objects=capture.capture(reader);context=capture_startup_context(reader)
    require(context['snapshot']['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'],
        'Cannot collect business comparison outside formal planning')
    tiles=capture.hex_fields.capture(reader,capture.hex_fields.audit());files=capture.inventory()
    require(objects==capture.capture(reader) and context==capture_startup_context(reader),'Known fields changed while capturing')
    require(reader.pointer(reader.memory.base+0x12cc4d0)==expected_user_hook,'Unexpected current User hook')
    require(files==capture.inventory(),'Save inventory changed')
    return dict(context=context,objects=objects,tiles=tiles,save_files=files,
        expected_user_hook=expected_user_hook,atomic_snapshot=False,full_world_coverage=False)
