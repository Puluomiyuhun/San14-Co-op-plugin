"""Read-only refresh preflight and exact FileWrite binding; no process at import."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct

import b_warm_staging as files
from b_warm_coordinator import approved_component, validate_pair
from b_warm_profile_capture import profile_from_dict, integer
from b_warm_pair_preflight import dll_identity, STEAM_HASHES
from b_warm_start import require, sha

FAMILY = 'san14.b-warm-refresh-pair.v1'


def identity(value):
    require(type(value) is dict and set(value)=={'size','sha256','file_id'},'Exact target identity required')
    integer(value['size'],1,files.MAX_BYTES)
    require(type(value['sha256']) is str and len(value['sha256'])==64 and
            all(c in '0123456789abcdef' for c in value['sha256']),'Target SHA256 required')
    require(type(value['file_id']) is list and len(value['file_id'])==7,'Target file identity required')
    for n in value['file_id']:integer(n,0,0xffffffff)
    require(value['file_id'][1] or value['file_id'][2],'Target file index missing')
    require((value['file_id'][3]<<32)|value['file_id'][4]==value['size'],'Target identity size differs')
    return value


def preflight(plan_path, *, helper_build, helper_sha256, pair_build, pair_sha256):
    path=files.clean_path(plan_path);plan_id,raw=files.read_file(path)
    require(len(raw)<=256*1024,'Plan too large');plan=json.loads(raw.decode('utf-8-sig'))
    require(type(plan) is dict and set(plan)=={'profiles','target','sources','initial_target','expected_ruler','steam_paths'},'Exact native-refresh plan required')
    require(type(plan['profiles']) is list and len(plan['profiles'])==2,'Two profiles required')
    profiles=[profile_from_dict(p) for p in plan['profiles']];validate_pair(profiles)
    integer(plan['expected_ruler'],1,5999);identity(plan['initial_target'])
    target=files.clean_path(plan['target']);require(target.name==files.NAME,'Exact CC03 target required')
    require(type(plan['sources']) is list and len(plan['sources'])==2,'Two independent source paths required')
    sources=[files.clean_path(p) for p in plan['sources']]
    old,_=files.read_file(target);require(old==plan['initial_target'],'Initial old target differs')
    inputs=[]
    for p,profile in zip(sources,profiles):
        row,_=files.read_file(p)
        require((row['size'],row['sha256'])==(profile.file.size,bytes(profile.file.sha256).hex()),'Received source differs')
        require(row['file_id'][:3]!=old['file_id'][:3],'Source aliases native target')
        inputs.append(row)
    require(inputs[0]['file_id'][:3]!=inputs[1]['file_id'][:3],'Source paths alias each other')
    steam=plan['steam_paths'];require(type(steam) is dict and set(steam)==set(STEAM_HASHES),'Exact Steam paths required')
    steam_rows={}
    for name,digest in STEAM_HASHES.items():
        p=files.clean_path(steam[name]);require(p.name==name,'Steam filename differs')
        row=dll_identity(p);require(row['sha256']==digest,'Unapproved Steam file: '+name);steam_rows[name]=row
    helper_path=Path(helper_build).resolve(strict=True);pair_path=Path(pair_build).resolve(strict=True)
    helper=approved_component(helper_path,helper_sha256,'san14.b-warm-coordinator.v1')
    pair=approved_component(pair_path,pair_sha256,FAMILY)
    require(pair.get('refresh_factory_pair_passed') is True,'Two complete refresh factories required')
    for name,h in helper['sources'].items():
        if Path(name).suffix in ('.h','.cpp'):require(pair['sources'].get(name)==h,'Helper/native pair source differs: '+name)
    components={}
    for name,p,result,h in (('helper',helper_path,helper,helper_sha256),('pair',pair_path,pair,pair_sha256)):
        dll=Path(result['production_dll']['path']).resolve(strict=True);digest=result['production_dll']['sha256']
        require(dll.is_relative_to(p.parent) and result['binaries'].get(str(dll))==digest and sha(dll)==digest,'Production DLL closure differs')
        components[name]=dict(result_path=str(p),result_sha256=h,production_dll=dict(path=str(dll),sha256=digest))
    require(files.read_file(path)[0]==plan_id and files.read_file(target)[0]==old and
            all(files.read_file(p)[0]==row for p,row in zip(sources,inputs)),'Files changed during preflight')
    normalized={**plan,'target':str(target),'sources':[str(p) for p in sources],
                'steam_paths':{n:r['path'] for n,r in steam_rows.items()}}
    return dict(result='PASS_LOCAL_REFRESH_PREFLIGHT',normalized_plan=normalized,plan_sha256=plan_id['sha256'],
        files=dict(initial=old,sources=inputs),steam_files=steam_rows,**components,
        game_access=False,claims_created=False,files_staged=False,native_load_permitted=False)


def storage_bindings(reader,module_list,**kwargs):
    """Extend the unchanged read bindings with v014 FileWrite slot0 PE/RX pins."""
    import pefile
    from b_warm_start_support import storage_bindings as read_bindings
    from checkpoint_complete_live_capture import readable
    result=read_bindings(reader,module_list,**kwargs)
    m=reader.memory;vtable=result['storageVtable'];module=result['storageModules'][result['vtableModuleIndex']]
    address=struct.unpack('<Q',m.read(vtable,8))[0]
    require(module['base']<=address and address+32<=module['base']+module['sizeOfImage'],'FileWrite outside vtable module')
    readable(reader,address,32,allocation=module['base'],execute=True)
    raw=m.read(address,32);pe=pefile.PE(module['path'],fast_load=True)
    try:require(raw==pe.get_data(address-module['base'],32),'Loaded FileWrite differs from pinned PE')
    finally:pe.close()
    again=read_bindings(reader,module_list,**kwargs)
    require(again==result and m.read(vtable,8)==struct.pack('<Q',address) and m.read(address,32)==raw,'Storage/FileWrite binding changed')
    return {**result,'write':dict(address=address,moduleIndex=result['vtableModuleIndex'],first32=raw.hex())}


def make_config(warm,*,write,previous,source_identity,target_path,backup_path,refresh_intent):
    """Build the new immutable wrapper; native Capture/guards still authorize it."""
    import b_warm_refresh_contract as wire
    identity(previous);identity(source_identity)
    require(source_identity['file_id'][:3]!=previous['file_id'][:3],'Private source aliases target')
    require((source_identity['size'],source_identity['sha256'])==
            (warm.profile.file.size,bytes(warm.profile.file.sha256).hex()),'Private copy/profile differs')
    result=wire.Config();result.warm=warm
    result.write.address=integer(write['address'],0x10000,0x7fffffffffff-32)
    result.write.moduleIndex=integer(write['moduleIndex'],0,2)
    require(result.write.moduleIndex==warm.owner.vtableModuleIndex,'FileWrite module differs')
    raw=bytes.fromhex(write['first32']);require(len(raw)==32 and any(raw),'FileWrite source bytes missing');result.write.first32[:]=raw
    result.previousSize=previous['size'];result.previousSha256[:]=bytes.fromhex(previous['sha256'])
    for key,record in (('sourceIdentity',source_identity),('previousTargetIdentity',previous)):
        v=record['file_id'];getattr(result,key).volume=v[0];getattr(result,key).indexHigh=v[1];getattr(result,key).indexLow=v[2]
        getattr(result,key).lastWriteLow=v[6];getattr(result,key).lastWriteHigh=v[5]
    paths=[str(files.clean_path(Path(warm.owner.localPath))),str(files.clean_path(target_path)),
           str(files.clean_path(backup_path)),str(files.clean_path(refresh_intent)),
           warm.owner.installIntent,warm.owner.requestIntent,warm.owner.identityIntent]
    require(len({p.casefold() for p in paths})==7 and all(len(p)<512 for p in paths),'Refresh paths alias or exceed ABI')
    require(Path(paths[0]).name==Path(paths[1]).name==files.NAME,'Refresh source/target name differs')
    require(not Path(paths[3]).exists(),'Refresh intent already exists')
    result.targetPath=paths[1];result.backupPath=paths[2];result.refreshIntent=paths[3]
    return result


def validate_completed(raw,config):
    import b_warm_refresh_contract as wire
    r=wire.decode(wire.Report,raw)
    expected=dict(state=4,error=0,captured=1,executeCalls=1,writeAttempts=1,writeReturned=1,
        intentCreated=1,intentDurable=1,matched=1,leaseHeld=0,leaseReleased=1,releaseCalls=1,
        previousReads=2,newReads=2,osError=0,exceptionCode=0)
    require(all(getattr(r,k)==v for k,v in expected.items()),'Refresh write/readback/lease completion differs')
    require((r.attempt,r.epoch,r.generation)==(config.warm.owner.attempt,config.warm.owner.epoch,config.warm.owner.generation),
            'Refresh attempt/generation differs')
    require((r.previousSize,bytes(r.previousSha256))==(config.previousSize,bytes(config.previousSha256)) and
            (r.newSize,bytes(r.newSha256))==(config.warm.profile.file.size,bytes(config.warm.profile.file.sha256)),
            'Refresh old/new file identity differs')
    require(bytes(r.stage)==b'released_after_native_retirement' and not bytes(r.firstFailure),'Refresh did not retire cleanly')
    return dict(**expected,attempt=r.attempt,epoch=r.epoch,generation=r.generation,
        previous_size=r.previousSize,previous_sha256=bytes(r.previousSha256).hex(),
        new_size=r.newSize,new_sha256=bytes(r.newSha256).hex(),stage=bytes(r.stage).decode('ascii'))
