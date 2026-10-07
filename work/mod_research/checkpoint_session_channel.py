"""Bound local named-pipe client for a preconfigured native Session.

No process discovery, injection, game memory, file publishing or native-load
completion assertion. Server PID/birth must be supplied by the owning launcher.
This is the control/observation channel underneath the future NativePort, not a
replacement for missing input, full-world, planning and presentation adapters.
"""
from dataclasses import dataclass, field
import ctypes as C
from ctypes import wintypes as W
import math
import re
import struct
import threading
import time

MAGIC=0x31495043
VERSION=1
REQUEST=struct.Struct('<IHHQ32s16s16s')
RESPONSE=struct.Struct('<IHHQ16s16I')
SNAPSHOT,ARM_ONCE,STOP_KEEP_OBSERVING=1,2,3
FIELDS=('status','state','error','exception_code','armed','menu_bound','request_in_flight',
        'cas_published','may_have_published','stop_requested','hooks_restored',
        'bytes_ready','lifecycle_ready','identity_ready','active_callbacks','capabilities')
# A pending overlapped operation may still reference Python-owned memory.
# Keep it strongly pinned until terminal completion is proved. Unprovable
# cleanup quarantines this connection for the process lifetime, without retry.
_PINNED_IO={}


class ChannelError(RuntimeError): pass
class OutcomeUnknown(ChannelError): pass
class NativeRejected(ChannelError): pass


def require(condition,message):
    if not condition: raise ChannelError(message)


@dataclass(frozen=True)
class Endpoint:
    pipe: str
    server_pid: int
    server_birth: int
    secret: bytes=field(repr=False)
    attempt: bytes
    intent: bytes

    def validate(self):
        prefix='\\\\.\\pipe\\san14-checkpoint-'
        require(type(self.pipe) is str and self.pipe.startswith(prefix) and
                len(self.pipe)<240 and re.fullmatch(r'[A-Za-z0-9_-]+',self.pipe[len(prefix):]) is not None,
                'Explicit local checkpoint pipe required')
        require(type(self.server_pid) is int and 0<self.server_pid<2**32 and
                type(self.server_birth) is int and self.server_birth>0,'Server PID/birth required')
        for name,length in (('secret',32),('attempt',16),('intent',16)):
            raw=getattr(self,name)
            require(type(raw) is bytes and len(raw)==length and any(raw),'Invalid '+name+' binding')


@dataclass(frozen=True)
class SessionStatus:
    sequence: int
    opcode: int
    fields: dict

    def progress(self):
        return {**self.fields, 'sequence':self.sequence,
                'native_load_complete':False, 'native_input_barrier_proved':False,
                'full_world_verified':False,'planning_ready':False,
                'identity_receipt_only':bool(self.fields['identity_ready'])}


ULONG_PTR=C.c_size_t
class OVERLAPPED(C.Structure):
    _fields_=[('Internal',ULONG_PTR),('InternalHigh',ULONG_PTR),
              ('Offset',W.DWORD),('OffsetHigh',W.DWORD),('hEvent',W.HANDLE)]


class WinPipeTransport:
    """One overlapped connection; canceled I/O is drained before buffer release."""
    def __init__(self, endpoint:Endpoint):
        endpoint.validate()
        self.k=C.WinDLL('kernel32',use_last_error=True)
        signatures={
          'CreateFileW':(W.HANDLE,[W.LPCWSTR,W.DWORD,W.DWORD,C.c_void_p,W.DWORD,W.DWORD,W.HANDLE]),
          'CreateEventW':(W.HANDLE,[C.c_void_p,W.BOOL,W.BOOL,W.LPCWSTR]),
          'ReadFile':(W.BOOL,[W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.POINTER(OVERLAPPED)]),
          'WriteFile':(W.BOOL,[W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.POINTER(OVERLAPPED)]),
          'GetOverlappedResult':(W.BOOL,[W.HANDLE,C.POINTER(OVERLAPPED),C.POINTER(W.DWORD),W.BOOL]),
          'CancelIoEx':(W.BOOL,[W.HANDLE,C.POINTER(OVERLAPPED)]),
          'WaitForSingleObject':(W.DWORD,[W.HANDLE,W.DWORD]),
          'CloseHandle':(W.BOOL,[W.HANDLE]),
          'GetNamedPipeServerProcessId':(W.BOOL,[W.HANDLE,C.POINTER(W.ULONG)]),
          'OpenProcess':(W.HANDLE,[W.DWORD,W.BOOL,W.DWORD]),
          'GetProcessTimes':(W.BOOL,[W.HANDLE,C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),
                                     C.POINTER(W.FILETIME),C.POINTER(W.FILETIME)])}
        for name,(restype,argtypes) in signatures.items():
            f=getattr(self.k,name);f.restype=restype;f.argtypes=argtypes
        self.handle=None
        self.quarantined=False
        h=self.k.CreateFileW(endpoint.pipe,0xC0000000,0,None,3,0x40000000,None)
        require(h not in (None,C.c_void_p(-1).value),'Cannot connect to bound local pipe')
        self.handle=h
        try:
            pid=W.ULONG()
            require(self.k.GetNamedPipeServerProcessId(h,C.byref(pid)) and pid.value==endpoint.server_pid,
                    'Pipe server PID mismatch')
            p=self.k.OpenProcess(0x1000,False,pid.value)
            require(bool(p),'Cannot verify bound server creation time')
            try:
                created,exited,kernel,user=W.FILETIME(),W.FILETIME(),W.FILETIME(),W.FILETIME()
                require(self.k.GetProcessTimes(p,C.byref(created),C.byref(exited),C.byref(kernel),C.byref(user)),
                        'Cannot read bound server creation time')
                require((created.dwHighDateTime<<32|created.dwLowDateTime)==endpoint.server_birth,
                        'Pipe server birth mismatch')
            finally:self.k.CloseHandle(p)
        except BaseException:
            self.close();raise

    def _io(self,write,buffer,size,deadline):
        require(self.handle is not None and not self.quarantined,'Pipe is closed or quarantined')
        require(time.monotonic()<deadline,'Pipe request deadline expired')
        event=self.k.CreateEventW(None,True,False,None)
        require(bool(event),'Cannot create I/O event')
        ov=OVERLAPPED();ov.hEvent=event;n=W.DWORD()
        terminal=False
        # Register before submission, including asynchronous Python exceptions
        # at a ctypes return boundary after the kernel has accepted the I/O.
        pin=id(ov);_PINNED_IO[pin]=(self,event,ov,buffer)
        try:
            ok=(self.k.WriteFile if write else self.k.ReadFile)(self.handle,buffer,size,C.byref(n),C.byref(ov))
            if ok:
                terminal=True
            else:
                error=C.get_last_error()
                if error!=997:
                    terminal=True
                    raise ChannelError('Pipe I/O failed')
                ms=max(1,math.ceil((deadline-time.monotonic())*1000))
                if self.k.WaitForSingleObject(event,ms)!=0:
                    raise OutcomeUnknown('Pipe request timed out; native outcome unknown')
                ok=self.k.GetOverlappedResult(self.handle,C.byref(ov),C.byref(n),False)
                error=0 if ok else C.get_last_error()
                terminal=bool(ok) or error in (995,109,232,233)
                require(ok,'Pipe completion failed')
            require(n.value>0,'Pipe closed without a complete message')
            return n.value
        finally:
            if not terminal:
                try:
                    self.k.CancelIoEx(self.handle,C.byref(ov))
                    self.k.WaitForSingleObject(event,1000)
                    ok=self.k.GetOverlappedResult(self.handle,C.byref(ov),C.byref(n),False)
                    error=0 if ok else C.get_last_error()
                    terminal=bool(ok) or error in (995,109,232,233)
                except BaseException:
                    terminal=False
            if terminal:
                self.k.CloseHandle(event)
                _PINNED_IO.pop(pin,None)
            else:
                self.quarantined=True

    def exchange(self,request,timeout):
        deadline=time.monotonic()+timeout
        offset=0
        while offset<len(request):
            raw=C.create_string_buffer(request[offset:])
            offset+=self._io(True,raw,len(request)-offset,deadline)
        data=bytearray()
        while len(data)<RESPONSE.size:
            raw=C.create_string_buffer(RESPONSE.size-len(data))
            n=self._io(False,raw,len(raw),deadline)
            data.extend(raw.raw[:n])
        return bytes(data)

    def close(self):
        if self.handle is not None and not self.quarantined:
            self.k.CloseHandle(self.handle);self.handle=None


class SessionChannel:
    def __init__(self,endpoint,*,timeout=3.0,transport_factory=WinPipeTransport):
        require(type(endpoint) is Endpoint,'Typed endpoint required');endpoint.validate()
        require(type(timeout) in (int,float) and 0<timeout<=60,'Bounded timeout required')
        self.endpoint=endpoint;self.timeout=float(timeout);self.factory=transport_factory
        self.lock=threading.RLock();self.sequence=0;self.arm_consumed=False
        self.observation_only=False;self.closed=False;self.fault=None;self.last=None
        self.reconnect_disabled=False
        self.transport=self.factory(endpoint)

    def _decode(self,data,op,seq):
        require(type(data) is bytes and len(data)==RESPONSE.size,'Invalid reply length')
        magic,version,opcode,sequence,attempt,*values=RESPONSE.unpack(data)
        require((magic,version,opcode,sequence,attempt)==(MAGIC,VERSION,op,seq,self.endpoint.attempt),
                'Stale or foreign reply')
        fields=dict(zip(FIELDS,values))
        require(fields['status']<=6 and fields['state']<=13,'Unknown native status')
        for key in ('armed','menu_bound','request_in_flight','cas_published','may_have_published',
                    'stop_requested','hooks_restored','bytes_ready','lifecycle_ready','identity_ready'):
            require(fields[key] in (0,1),'Invalid native flag')
        require(fields['capabilities']==0,'This Session cannot prove world/input completion')
        require(not fields['cas_published'] or fields['may_have_published'],'Inconsistent publication status')
        return SessionStatus(seq,op,fields)

    def _request(self,op):
        require(not self.closed and self.transport is not None,'Explicit reconnect required')
        self.sequence+=1;seq=self.sequence
        request=REQUEST.pack(MAGIC,VERSION,op,seq,self.endpoint.secret,
                             self.endpoint.attempt,self.endpoint.intent)
        try:
            reply=self.transport.exchange(request,self.timeout)
            result=self._decode(reply,op,seq)
        except BaseException as error:
            self.observation_only=True;self.fault=type(error).__name__
            self.reconnect_disabled=bool(getattr(self.transport,'quarantined',False))
            self.transport.close();self.transport=None
            raise
        self.last=result
        if (result.fields['state'] not in (0,1) or any(result.fields[k] for k in
                ('armed','menu_bound','request_in_flight','stop_requested','may_have_published',
                 'hooks_restored','error','exception_code'))):
            self.observation_only=True
        if result.fields['status']:
            self.observation_only=True
            raise NativeRejected('Native session rejected opcode %d (status %d)'%(op,result.fields['status']))
        return result

    def snapshot(self):
        with self.lock:return self._request(SNAPSHOT)

    def arm_once(self):
        with self.lock:
            require(not self.arm_consumed and not self.observation_only,'Arm is permanently consumed or disabled')
            self.arm_consumed=True  # Before transport entry: timeout must not re-arm.
            return self._request(ARM_ONCE)

    def stop_keep_observing(self):
        with self.lock:
            self.observation_only=True
            return self._request(STOP_KEEP_OBSERVING)

    def reconnect_for_observation(self):
        with self.lock:
            require(not self.closed,'Channel explicitly closed')
            require(not self.reconnect_disabled,'Unfinished I/O quarantined; process restart required')
            require(self.transport is None,'Close failed connection before reconnecting')
            self.observation_only=True
            self.transport=self.factory(self.endpoint)
            # Sequence and arm_consumed deliberately survive the connection.
            return self.snapshot()

    def close(self):
        with self.lock:
            if self.transport is not None:self.transport.close();self.transport=None
            self.closed=True;self.observation_only=True

    def status(self):
        with self.lock:
            return {'sequence':self.sequence,'arm_consumed':self.arm_consumed,
                    'observation_only':self.observation_only,'connected':self.transport is not None,
                    'io_quarantined':self.reconnect_disabled,
                    'fault':self.fault,'native_port_implemented':False,
                    'native_gameplay_enabled':False}
