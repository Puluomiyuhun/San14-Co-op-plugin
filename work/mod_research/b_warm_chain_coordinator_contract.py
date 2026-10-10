"""Three distinct native banks. Typed local ABI, never room or input permission."""
import ctypes as C
U8,U32,U64=C.c_uint8,C.c_uint32,C.c_uint64
MAGIC=0x53414E1442433331
EXPORTS=tuple(n+'BWarmChainCoordinator' for n in ('Describe','Prepare','Authorize','Observe'))
class Certificate(C.Structure):
    _fields_=[('version',U32),('pid',U32)]+[(n,U64) for n in ('birth','generation','attempt','previous','next')]+[('nonce',U8*32),('fileSha256',U8*32)]+[(n,U64) for n in ('userCall','identityCall','loadCall')]
class Header(C.Structure):
    _fields_=[('magic',U64)]+[(n,U32) for n in ('size','version','operation','result')]+[('nonce',U8*32)]
class Prepare(C.Structure):
    _fields_=[('header',Header),('pid',U32),('reserved',U32),('birth',U64),('first',U64),('slots',U64*6),('originals',U64*6)]
class Authorize(C.Structure):
    _fields_=[('header',Header),('next',U64),('generation',U32),('reserved',U32)]
class Observe(C.Structure):
    _fields_=[('header',Header),('currentGeneration',U32),('reserved',U32),('banks',U64*3),('completed',U32*3),('certificateCount',U32),('certificates',Certificate*2)]
class Description(C.Structure):
    _fields_=[('magic',U64)]+[(n,U32) for n in ('size','version','prepareSize','authorizeSize','observeSize','certificateSize')]
TYPES={k.__name__:k for k in (Certificate,Header,Prepare,Authorize,Observe,Description)}
OPS={Prepare:1,Authorize:2,Observe:3}
def envelope(kind,nonce):
    if kind not in OPS or type(nonce) is not bytes or len(nonce)!=32 or not any(nonce):raise ValueError('Exact nonzero nonce and operation required')
    x=kind();x.header.magic=MAGIC;x.header.size=C.sizeof(kind);x.header.version=1;x.header.operation=OPS[kind];x.header.nonce[:]=nonce
    return x
def decode(kind,raw,nonce=None):
    if kind not in (*OPS,Description) or type(raw) is not bytes or len(raw)!=C.sizeof(kind):raise ValueError('Exact response ABI required')
    x=kind.from_buffer_copy(raw)
    if kind is Description:
        if tuple(getattr(x,n) for n,_ in kind._fields_)!=(MAGIC,C.sizeof(kind),1,C.sizeof(Prepare),C.sizeof(Authorize),C.sizeof(Observe),C.sizeof(Certificate)):raise ValueError('Description ABI differs')
        return x
    h=x.header
    if (h.magic,h.size,h.version,h.operation,bytes(h.nonce))!=(MAGIC,C.sizeof(kind),1,OPS[kind],nonce):raise ValueError('Response attachment differs')
    if h.result:return x
    if kind is Prepare and (x.reserved or not x.pid or not x.birth or not x.first or len(set(x.slots))!=6 or not all(x.slots) or not all(x.originals)):raise ValueError('Prepare binding differs')
    if kind is Authorize and (x.reserved or x.generation not in (2,3) or not x.next):raise ValueError('Authorization binding differs')
    if kind is Observe:
        g=x.currentGeneration
        if g not in (1,2,3) or x.reserved or x.certificateCount!=g-1:raise ValueError('Generation differs')
        if len(set(x.banks[:g]))!=g or not all(x.banks[:g]) or any(x.banks[g:]):raise ValueError('Bank lineage differs')
        if list(x.completed[:g-1])!=[1]*(g-1) or x.completed[g-1] not in (0,1) or any(x.completed[g:]):raise ValueError('Completion differs')
        for i,c in enumerate(x.certificates):
            if i>=g-1:
                empty=Certificate();empty.version=1
                if bytes(c)!=bytes(empty):raise ValueError('Unissued certificate not empty')
                continue
            if (c.version,c.generation,c.previous,c.next,bytes(c.nonce))!=(1,i+2,x.banks[i],x.banks[i+1],nonce):raise ValueError('Certificate lineage differs')
            if not all((c.pid,c.birth,c.attempt,c.userCall,c.identityCall,c.loadCall)) or not any(c.fileSha256):raise ValueError('Incomplete certificate')
            if i and (c.pid,c.birth)!=(x.certificates[0].pid,x.certificates[0].birth):raise ValueError('Certificate process differs')
    return x
