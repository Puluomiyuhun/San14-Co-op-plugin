"""Local two-bank native handover ABI. Data and codec only, no process access."""
import ctypes as C
U8,U32,U64=C.c_uint8,C.c_uint32,C.c_uint64
MAGIC=0x53414E1442433031
class Header(C.Structure):
    _fields_=[('magic',U64),('size',U32),('version',U32),('operation',U32),('result',U32),('nonce',U8*32)]
class Prepare(C.Structure):
    _fields_=[('header',Header),('pid',U32),('reserved',U32),('birth',U64),('first',U64),('slots',U64*6),('originals',U64*6)]
class Authorize(C.Structure):
    _fields_=[('header',Header),('second',U64)]
class Observe(C.Structure):
    _fields_=[('header',Header),('stage',U32),('reserved',U32),('first',U64),('second',U64),('firstCompleted',U32),('secondCompleted',U32)]
class Description(C.Structure):
    _fields_=[('magic',U64)]+[(n,U32) for n in ('size','version','prepareSize','authorizeSize','observeSize','reserved')]
TYPES={k.__name__:k for k in (Header,Prepare,Authorize,Observe,Description)}
OPS={Prepare:1,Authorize:2,Observe:3}
def envelope(kind,nonce):
    if kind not in OPS or type(nonce) is not bytes or len(nonce)!=32 or not any(nonce):
        raise ValueError('Exact nonzero local nonce and supported operation required')
    x=kind();x.header.magic=MAGIC;x.header.size=C.sizeof(kind);x.header.version=1;x.header.operation=OPS[kind];x.header.nonce[:]=nonce
    return x
def decode(kind,raw,nonce=None):
    if kind not in TYPES.values() or kind is Header or len(raw)!=C.sizeof(kind):raise ValueError('Exact response ABI required')
    x=kind.from_buffer_copy(raw)
    if kind is Description:
        if (x.magic,x.size,x.version,x.prepareSize,x.authorizeSize,x.observeSize,x.reserved)!=(MAGIC,C.sizeof(kind),1,C.sizeof(Prepare),C.sizeof(Authorize),C.sizeof(Observe),0):raise ValueError('Description ABI differs')
    else:
        h=x.header
        if (h.magic,h.size,h.version,h.operation,bytes(h.nonce))!=(MAGIC,C.sizeof(kind),1,OPS[kind],nonce):raise ValueError('Response attachment differs')
        if kind is Observe and not h.result:
            if x.stage not in (1,2,3) or x.reserved or not x.first or x.firstCompleted not in (0,1) or x.secondCompleted not in (0,1):raise ValueError('Handover state differs')
            if x.stage>=2 and (not x.second or x.first==x.second or not x.firstCompleted):raise ValueError('Second handover binding differs')
            if (x.stage==3)!=(x.secondCompleted==1):raise ValueError('Second completion differs')
    return x
