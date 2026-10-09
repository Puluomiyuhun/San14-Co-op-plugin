"""Data-only refresh-owner ABI. No process access or native authority."""
import ctypes as C
import b_warm_profile_contract as warm
import checkpoint_complete_live_owner_contract as old

U32,U64=C.c_uint32,C.c_uint64
MAGIC=0x53414E1457524631

class Identity(C.Structure):
    _fields_=[('volume',U32),('indexHigh',U32),('indexLow',U32),('lastWriteLow',U32),('lastWriteHigh',U32)]

class Config(C.Structure):
    _fields_=[('magic',U64),('size',U32),('version',U32),('warm',warm.Config),('write',old.Endpoint),
              ('previousSize',U32),('reserved',U32),('previousSha256',C.c_uint8*32),
              ('sourceIdentity',Identity),('previousTargetIdentity',Identity),
              ('targetPath',C.c_wchar*512),('backupPath',C.c_wchar*512),('refreshIntent',C.c_wchar*512)]
    def __init__(self):
        super().__init__();self.magic=MAGIC;self.size=C.sizeof(type(self));self.version=1;self.warm=warm.Config()

class Report(C.Structure):
    _fields_=[('magic',U64),('size',U32),('version',U32)]
    _fields_ += [(n,U32) for n in 'state error captured executeCalls writeAttempts writeReturned intentCreated intentDurable matched leaseHeld leaseReleased releaseCalls previousSize newSize osError exceptionCode previousReads newReads'.split()]
    _fields_ += [('previousSha256',C.c_uint8*32),('newSha256',C.c_uint8*32),('stage',C.c_char*64),('firstFailure',C.c_char*64)]
    _fields_ += [(n,U64) for n in ('attempt','epoch','generation')]

class Description(C.Structure):
    _fields_=[('magic',U64),('size',U32),('version',U32),('configSize',U32),('reportSize',U32),('warm',warm.Description)]

def decode(kind,raw):
    if kind not in (Description,Report) or len(raw)!=C.sizeof(kind):raise ValueError('Refresh exact response ABI required')
    value=kind.from_buffer_copy(raw)
    if (value.magic,value.size,value.version)!=(MAGIC,C.sizeof(kind),1):raise ValueError('Refresh ABI header differs')
    if kind is Description:
        if (value.configSize,value.reportSize)!=(C.sizeof(Config),C.sizeof(Report)):raise ValueError('Refresh described ABI differs')
        warm.decode(warm.Description,bytes(value.warm))
    return value
