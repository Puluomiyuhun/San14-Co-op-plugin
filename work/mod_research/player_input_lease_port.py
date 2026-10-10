"""Typed control of an already installed HWND input owner; no installer.
A lease spans the actual CheckedPort before/native/after operation. Native
callbacks and other input paths are not claimed to be globally fenced.
"""
import ctypes as C
from dataclasses import dataclass
import threading,time
from pathlib import Path
import a_runtime_reward_port as common
from a_runtime_reward_port import require,save_new

U8,U32,U64=C.c_uint8,C.c_uint32,C.c_uint64
class Packed(common.base.Packed):pass
MAGIC=0x31455341454C4950
OPS=dict(Request=2,Acquire=3,Complete=4,Snapshot=5,Unknown=6)
class Header(Packed):_fields_=[('magic',U64),('version',U32),('size',U32),('op',U32),('result',U32)]
class Binding(Packed):_fields_=[('room',U8*16),('attachment',U8*16),('epoch',U8*16),('period',U64),('seat',U32)]
class Request(Packed):_fields_=[('header',Header),('nonce',U8*32),('binding',Binding),('phase',U32),('localReady',U32),('revision',U64)]
class Lease(Packed):_fields_=[('header',Header),('nonce',U8*32),('binding',Binding),('revision',U64),('sequence',U64),('lease',U64)]
class Snapshot(Packed):
    _fields_=[('header',Header),('nonce',U8*32),('pid',U32),('birth',U64),('window',U64),('windowThread',U32),('binding',Binding)]+[
        (n,U32) for n in ('phase','localReady','error','initialized','installed','pending','acknowledged','held','uncertain','destroyed')]+[
        (n,U64) for n in ('revision','acknowledgedRevision','active','finally','leaseId','leaseSequence','leaseRevision','leasesIssued','leasesCompleted','suppressed','auditedForwarded','lifecycleForwarded','uncoveredForwarded','unclassifiedForwarded','publicationWrites')]+[
        (n,U32) for n in ('remoteMessagesAllowed','remoteExecutionPolicyOpen','localCommandPolicyOpen','allInputHeld','osQueueDrained','nativeReceiptVerified','controlMessage')]
assert tuple(C.sizeof(t) for t in (Header,Binding,Request,Lease,Snapshot))==(24,60,132,140,328)

class Transport(common.RemoteTransport):
    def _perform(self,name,payload):
        import pefile
        with self.lock:
            try:
                self._identity();require(name in {'PlayerInput'+n for n in OPS},'No input installer or arbitrary export calls')
                pe=pefile.PE(str(self.dll))
                try:
                    matches=[s for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name==name.encode('ascii')]
                    require(len(matches)==1 and not matches[0].forwarder,'Exact input export required')
                    rva=matches[0].address;address=self.module+rva;expected=pe.get_data(rva,32)
                finally:pe.close()
                common.readable(self.api.reader,address,32,allocation=self.module,execute=True)
                require(len(expected)==32 and self.api.reader.memory.read(address,32)==expected,'Input export bytes differ')
                self.calls+=1
                result=common.remote_call(self.api,address,payload,self.records,f'{self.calls:04d}-{name}')
                self._identity();return result
            except BaseException as exc:self.failed=repr(exc);raise

@dataclass(frozen=True)
class Ticket:
    revision:int
    sequence:int
    lease:int

class InputLease:
    def __init__(self,transport,*,nonce,binding,pid,birth,window,records,wait_seconds=3):
        require(type(transport) is Transport and type(transport.state) is common.SharedCallState,'Actual shared input transport required')
        require(type(binding) is Binding and all(any(getattr(binding,n)) for n in ('room','attachment','epoch')) and binding.period and binding.seat<2,'Exact live input binding required')
        require(type(nonce) is bytes and len(nonce)==32 and any(nonce) and pid>0 and birth>0 and window>0,'Input native identity required')
        require(0<wait_seconds<=10,'Bounded input wait required')
        self.transport,self.state=transport,transport.state;self.nonce=nonce;self.binding=Binding.from_buffer_copy(bytes(binding))
        self.local_binding=(pid,birth,bytes(binding.epoch).hex(),bytes(binding.attachment).hex());self.window=window
        self.records=Path(records);self.records.mkdir(parents=True,exist_ok=False)
        self.wait=wait_seconds;self.lock=threading.RLock();self.calls=0;self.active=None;self.failed=None
        self.snapshot()
    def _request(self,typ,op):
        q=typ();q.header=Header(MAGIC,1,C.sizeof(typ),OPS[op],0);q.nonce[:]=self.nonce;q.binding=self.binding;return q
    def _call(self,op,q):
        self.state.require_known();self.calls+=1;label=f'{self.calls:04d}-{op}'
        save_new(self.records/(label+'-request.json'),common.base.values(q))
        code,raw=self.transport.call('PlayerInput'+op,bytes(q));require(type(raw) is bytes and len(raw)==C.sizeof(q),'Input reply length differs')
        r=type(q).from_buffer_copy(raw)
        require(bytes(r.header)[:20]==bytes(q.header)[:20] and bytes(r.nonce)==self.nonce and bytes(r.binding)==bytes(self.binding),'Input reply identity differs')
        save_new(self.records/(label+'-reply.json'),dict(exit=code,report=common.base.values(r)))
        require(code==0 and r.header.result==0,'Native input request refused')
        if op in ('Request','Complete','Unknown'):require(bytes(r)[24:]==bytes(q)[24:],'Input request echo differs')
        if op=='Acquire':require(r.revision==q.revision and r.sequence==q.sequence and r.lease==q.sequence,'Input lease reply differs')
        return r
    def snapshot(self):
        s=self._call('Snapshot',self._request(Snapshot,'Snapshot'))
        require((s.pid,s.birth)==self.local_binding[:2] and s.window==self.window and s.windowThread and
                s.initialized==s.installed==1 and not any((s.error,s.uncertain,s.destroyed,s.allInputHeld,s.osQueueDrained,s.nativeReceiptVerified)),
                'Input owner missing, terminal, or claims unsupported coverage')
        require(s.phase<=5 and s.localReady in (0,1),'Invalid input state')
        return s
    def verify_binding(self,binding,native=None):
        with self.lock:
            require(self.failed is None and tuple(binding)==self.local_binding,'Input/reward attachment differs')
            if native is not None:
                require(getattr(getattr(native,'transport',None),'state',None) is self.state,'Input and reward must share the same unknown-call gate')
            return self.snapshot()
    def request_phase(self,phase,local_ready=False):
        with self.lock:
            require(self.failed is None and self.active is None,'In-flight/unknown reward blocks phase transition')
            require(type(phase) is int and 0<=phase<=5 and type(local_ready) is bool and (phase==0 or not local_ready),'Invalid requested phase')
            try:
                s=self.snapshot();require(not s.pending and not s.leaseId,'Input owner is busy')
                q=self._request(Request,'Request');q.phase=phase;q.localReady=int(local_ready);q.revision=s.revision+1
                self._call('Request',q);end=time.monotonic()+self.wait
                while True:
                    s=self.snapshot()
                    if s.acknowledged and not s.pending and s.acknowledgedRevision==q.revision:
                        require(s.phase==phase and s.localReady==local_ready and not s.active,'Wrong HWND acknowledgement')
                        held=int(phase!=0 or local_ready)
                        require(s.held==held and s.localCommandPolicyOpen==1-held and
                                s.remoteExecutionPolicyOpen==int(phase==0),
                                'HWND acknowledgement does not enforce requested input policy')
                        return common.base.values(s)
                    require(time.monotonic()<end,'Input phase acknowledgement unresolved')
                    time.sleep(.01)
            except BaseException as exc:self.fail(None,exc);raise
    def begin(self,binding):
        with self.lock:
            s=self.verify_binding(binding)
            require(self.active is None and s.phase==0 and s.remoteExecutionPolicyOpen and s.acknowledged and not s.pending and not s.leaseId and s.revision==s.acknowledgedRevision,'Reward requires acknowledged Planning input state')
            q=self._request(Lease,'Acquire');q.revision=s.revision;q.sequence=s.leasesIssued+1
            self.active=Ticket(q.revision,q.sequence,q.sequence)
            self._call('Acquire',q)
            s=self.snapshot();require(s.leaseId==q.sequence and s.leaseRevision==q.revision and s.leaseSequence==q.sequence and s.held,'Native lease not held')
            return self.active
    def complete(self,ticket):
        with self.lock:
            require(self.failed is None and ticket is self.active and ticket is not None,'Exact active input ticket required')
            q=self._request(Lease,'Complete');q.revision=ticket.revision;q.sequence=ticket.sequence;q.lease=ticket.lease
            self._call('Complete',q)
            s=self.snapshot();require(not s.leaseId and s.leasesCompleted==ticket.sequence,'Native input lease not drained')
            self.active=None
    def fail(self,ticket,exc):
        with self.lock:
            if self.failed is not None:return
            self.failed=repr(exc)
            # If any shared native call is unknown, even a cleanup RPC is unsafe.
            if self.state.unknown is not None:return
            current=self.active;s=self.snapshot()
            if s.leaseId:
                require(current is not None and s.leaseId==current.lease and s.leaseSequence==current.sequence and s.leaseRevision==current.revision,'Foreign active input lease; do not clean it up')
                q=self._request(Lease,'Unknown');q.revision=current.revision;q.sequence=current.sequence;q.lease=current.lease
                self._call('Unknown',q)
            else:
                q=self._request(Request,'Request');q.phase=5;q.revision=s.revision+1
                self._call('Request',q)
