"""Dedicated three-slot A Runtime ABI. No process access or permission."""
import ctypes as C
import secrets
from pathlib import Path

U8,U16,U32,U64=C.c_uint8,C.c_uint16,C.c_uint32,C.c_uint64
MAGIC,VERSION=0x33585241,1
OPS=dict(Prepare=1,Plans=2,ArmOwner=3,ArmPublishedSources=4,Snapshot=5,Stop=6,StartServer=7,ServerStatus=8)


class Packed(C.LittleEndianStructure):
    _pack_=1


class Header(Packed):
    _fields_=[(n,U32) for n in ('magic','version','size','operation','result')]


class NativeBinding(Packed):
    _fields_=[('attempt',U8*16),('attachment',U8*16),('ownerGeneration',U64)]


class Module(Packed):
    _fields_=[('base',U64),('sizeOfImage',U32),('timestamp',U32),('path',U16*1024),('fileSize',U64),('fileSha256',U8*32),('headerSha256',U8*32)]


class Endpoint(Packed):
    _fields_=[('address',U64),('moduleIndex',U32),('first32',U8*32)]


class Storage(Packed):
    _fields_=[('pid',U32)]+[(n,U64) for n in ('birth','attempt','generation','base')]
    _fields_ += [(n,U8*32) for n in ('id','gameSha256')]+[('modules',Module*3),('moduleCount',U32)]
    _fields_ += [(n,Endpoint) for n in ('contextInit','exists','size','read')]
    _fields_ += [(n,U64) for n in ('storage','vtable','counter')]+[(n,U32) for n in ('vtableModuleIndex','counterModuleIndex')]
    _fields_ += [('cachedGeneration',U64),('contextCode',U8*0x65)]


class Prepare(Packed):
    _fields_=[('header',Header),('nonce',U8*32),('pid',U32),('birth',U64),('base',U64),('roomId',U8*32),('nativeRoomEpoch',U64),('native',NativeBinding)]
    _fields_ += [(n,U64) for n in ('root','world','cache')]+[('states',U64*5),('storage',Storage),('period',U64),('epoch',U64),('roomInputDigest',U8*32)]
    _fields_ += [('year',U16),('ruler',U16)]+[(n,U8) for n in ('month','day','force','reserved')]+[(n,U16*512) for n in ('saveDirectory','intentDirectory')]


class Inline(Packed):
    _fields_=[('address',U64),('relay',U64),('size',U32),('protection',U32),('before',U8*7),('after',U8*7)]


class Slot(Packed):
    _fields_=[('address',U64),('original',U64),('hook',U64),('protection',U32)]


class Counter(Packed):
    _fields_=[(n,U64) for n in ('startedAddress','activeAddress','started','active')]


class HostCache(Packed):
    _fields_=[('sequence',U64)]+[(n,U32) for n in ('valid','lease','frame','state')]


class Plans(Packed):
    _fields_=[('header',Header),('nonce',U8*32),('pid',U32),('birth',U64),('base',U64),('module',U64),('inlines',Inline*3),('slots',Slot*4),('counters',Counter*7)]


class Command(Packed):
    _fields_=[('header',Header),('nonce',U8*32)]


class StartServer(Packed):
    _fields_=[('header',Header),('nonce',U8*32),('clientPid',U32),('idleTimeoutMs',U32),('secret',U8*32),('pipeName',U16*180)]


class ServerStatus(Packed):
    _fields_=[('header',Header),('nonce',U8*32)]+[(n,U32) for n in ('started','threadExited','runSucceeded','opened','running','closed','stopped','osError')]+[(n,U64) for n in ('requests','submits','copies','lastSequence')]


class Snapshot(Packed):
    _fields_=[('header',Header),('nonce',U8*32)]
    _fields_ += [(n,U32) for n in ('error','prepared','ownerArmed','sourcesArmed','stopped','ready','ownerError','ownerStopped','saveLane','saveStatus','saveError','binds','queues','phaseMask','workerJoined','originalReturned','fileVerified')]
    _fields_ += [(n,U64) for n in ('saveGeneration','saveActive','ownerActive','gateActive','parentActive','parentBefore','parentAfter','parentFinally')]
    _fields_ += [(n,U32) for n in ('parentError','hostInitialized','hostThread','mailboxStopped','mailboxCount')]+[('mailboxStates',U32*3)]
    _fields_ += [(n,U32) for n in ('hostCacheValid','hostLease','hostFrame','hostState')]+[('hostCacheSequence',U64),('hostCacheAddress',U64),('counters',Counter*7)]
    _fields_ += [(n,U32) for n in ('productionPermit','allWritersProven','restoreReady')]


TYPES={c.__name__:c for c in (Header,NativeBinding,Module,Endpoint,Storage,Prepare,Inline,Slot,Counter,HostCache,Plans,Command,StartServer,ServerStatus,Snapshot)}
OPERATIONS={Prepare:('Prepare',),Plans:('Plans',),Command:('ArmOwner','ArmPublishedSources','Stop'),
            StartServer:('StartServer',),ServerStatus:('ServerStatus',),Snapshot:('Snapshot',)}


def put_bytes(array, value):
    raw=bytes.fromhex(value) if isinstance(value,str) else value
    if type(raw) is not bytes or len(raw)!=len(array):raise ValueError('Exact byte-array size required')
    array[:]=raw


def put_wide(array, value):
    if type(value)is not str or not value or '\0' in value:raise ValueError('Nonempty text required')
    raw=value.encode('utf-16le')
    if len(raw)>=C.sizeof(array):raise ValueError('Text too long')
    C.memset(C.addressof(array),0,C.sizeof(array))
    C.memmove(C.addressof(array),raw,len(raw))


def envelope(kind, operation, nonce):
    if kind not in OPERATIONS or operation not in OPERATIONS[kind]:raise ValueError('Dedicated three-slot type and operation required')
    if type(nonce) is not bytes or len(nonce)!=32 or not any(nonce):raise ValueError('Exact nonzero nonce required')
    obj=kind();obj.header=Header(MAGIC,VERSION,C.sizeof(kind),OPS[operation],0)
    put_bytes(obj.nonce,nonce)
    return obj


def decode(kind, operation, nonce, raw):
    if kind not in OPERATIONS or operation not in OPERATIONS[kind]:raise ValueError('Dedicated three-slot type and operation required')
    if type(nonce) is not bytes or len(nonce)!=32 or not any(nonce):raise ValueError('Exact nonzero nonce required')
    if type(raw) is not bytes or len(raw)!=C.sizeof(kind):raise ValueError('Response size differs')
    obj=kind.from_buffer_copy(raw);h=obj.header
    if (h.magic,h.version,h.size,h.operation)!=(MAGIC,VERSION,len(raw),OPS[operation]) or bytes(obj.nonce)!=nonce:
        raise ValueError('Foreign response identity')
    return obj


def values(obj):
    out={}
    for name,typ in obj._fields_:
        value=getattr(obj,name)
        if isinstance(value,Packed):value=values(value)
        elif isinstance(value,C.Array):
            if typ._type_==U8:value=bytes(value).hex()
            elif issubclass(typ._type_,Packed):value=[values(v) for v in value]
            else:value=list(value)
        out[name]=value
    return out


def prepare_from_capture(capture, save_directory, intent_directory):
    if capture.get('result')!='PASS_READ_ONLY' or not capture.get('sources_unchanged'):raise ValueError('Fresh successful capture required')
    p,s=capture['planning'],capture['storage'];context=p['context']['snapshot']
    if context['date']!=dict(year=203,month=8,day=11,period='中旬') or context['player']['force_id']!=12 or context['player']['ruler_id']!=666:
        raise ValueError('Only current fixed slot34 test supported')
    q=envelope(Prepare,'Prepare',secrets.token_bytes(32))
    q.pid,q.birth,q.base=p['pid'],p['birth'],p['base']
    for n in ('root','world','cache'):setattr(q,n,p[n])
    q.states[:]=p['states']
    put_bytes(q.roomId,secrets.token_bytes(32));q.nativeRoomEpoch=secrets.randbits(64) or 1
    put_bytes(q.native.attempt,secrets.token_bytes(16));put_bytes(q.native.attachment,secrets.token_bytes(16));q.native.ownerGeneration=1
    q.period=1;q.epoch=secrets.randbits(64) or 1;put_bytes(q.roomInputDigest,secrets.token_bytes(32))
    q.year,q.month,q.day,q.force,q.ruler=203,8,11,12,666
    put_wide(q.saveDirectory,str(Path(save_directory).resolve(strict=True)))
    put_wide(q.intentDirectory,str(Path(intent_directory).resolve(strict=True)))
    z=q.storage;z.pid=q.pid;z.birth=q.birth;z.base=q.base;z.attempt=secrets.randbits(64) or 1;z.generation=1
    put_bytes(z.id,secrets.token_bytes(32));put_bytes(z.gameSha256,p['gameSha256'])
    z.moduleCount=s['storageModuleCount']
    if not 1<=z.moduleCount<=3 or z.moduleCount!=len(s['storageModules']):raise ValueError('Module count differs')
    for dst,src in zip(z.modules,s['storageModules']):
        for n in ('base','sizeOfImage','timestamp','fileSize'):setattr(dst,n,src[n])
        put_wide(dst.path,src['path'])
        for n in ('fileSha256','headerSha256'):put_bytes(getattr(dst,n),src[n])
    for dstname,srcname in (('contextInit','contextInit'),('exists','exists'),('size','fileSize'),('read','read')):
        dst,src=getattr(z,dstname),s[srcname];dst.address=src['address'];dst.moduleIndex=src['moduleIndex'];put_bytes(dst.first32,src['first32'])
    for dst,src in (('storage','storage'),('vtable','storageVtable'),('counter','storageCounter'),('vtableModuleIndex','vtableModuleIndex'),('counterModuleIndex','counterModuleIndex'),('cachedGeneration','cachedGeneration')):
        setattr(z,dst,s[src])
    put_bytes(z.contextCode,s['contextCode'])
    return q
