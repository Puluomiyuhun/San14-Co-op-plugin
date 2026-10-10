"""Local typed reward adapter for the retained Runtime, never a network executor.

Import is inert. The existing ExecutionJournal must persist an INTENT before
execute. Unknown submission/completion retires this adapter without replay,
Stop, unload, or claiming that input is excluded.
"""
from copy import deepcopy
import ctypes as C
from ctypes import wintypes as W
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import struct
import threading
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'outputs/san14-link'),str(ROOT.parent/'mod_research/python_deps')]
import execution_journal as journal
from reward_observed_context import ContextSampler,CheckedPort,reward
from a_save_runtime_control import require,save_new,RemoteCallUnknown
from a_observed_start_call import remote_call
from checkpoint_complete_live_capture import module_approval,process_birth,readable
import a_save_runtime_contract as base

OPS={'Configure':11,'Submit':12,'Snapshot':13}
class Context(base.Packed):
    _fields_=[('pid',base.U32),('birth',base.U64),('native',base.NativeBinding),
              ('period',base.U64),('epoch',base.U64),('inputDigest',base.U8*32)]
class Actor(base.Packed):
    _fields_=[('force',base.U8),('district',base.U8),('ruler',base.U16)]
class Configure(base.Packed):
    _fields_=[('header',base.Header),('nonce',base.U8*32),('context',Context),('actors',Actor*2)]
class Command(base.Packed):
    _fields_=[('nonce',base.U8*32),('year',base.U16)]+[(n,base.U8) for n in ('month','day','viewer','actor')]
    _fields_ += [('ruler',base.U16),('city',base.U16),('district',base.U8),('reserved',base.U8),
                 ('count',base.U32),('officers',base.U32*16),('expiresAtTick',base.U64)]
class Submit(base.Packed):
    _fields_=[('header',base.Header),('nonce',base.U8*32),('context',Context),('sequence',base.U64),('command',Command)]
class Snapshot(base.Packed):
    _fields_=[('header',base.Header),('nonce',base.U8*32),('context',Context)]
    _fields_ += [(n,base.U64) for n in ('sequence','submitted','completed')]
    _fields_ += [(n,base.U32) for n in ('state','error','configured','queued','active','readyResealed','uncertain','stopped','hostThread',
        'ownerError','replayState','replayError','nativeReturned','argsReleased','ownedSlotCleared','ctorCalls','appendCalls','dtorCalls','captureCalls','executeCalls')]
    _fields_ += [('finallyCalls',base.U64),('abnormalCalls',base.U64),('commandSha256',base.U8*32),('semanticSha256',base.U8*32)]
    _fields_ += [(n,base.U32) for n in ('fullInputHold','worldFenceProven','nativeGameplayEnabled')]
assert tuple(C.sizeof(t) for t in (Context,Configure,Command,Submit,Snapshot))==(100,160,120,280,348)


def command_hash(context,command):
    c=command;n=context.native
    raw=bytes(n.attempt)+bytes(n.attachment)+struct.pack('<QQQ',n.ownerGeneration,context.period,context.epoch)+bytes(context.inputDigest)
    raw+=bytes(c.nonce)+struct.pack('<QHBBBBHHBI',c.expiresAtTick,c.year,c.month,c.day,c.viewer,c.actor,c.ruler,c.city,c.district,c.count)
    raw+=struct.pack('<'+'I'*c.count,*list(c.officers)[:c.count])
    return hashlib.sha256(raw).digest()


def context_from_prepare(prepared):
    require(type(prepared) is base.Prepare,'Exact previously approved Runtime Prepare required')
    value=Context();value.pid,value.birth=prepared.pid,prepared.birth
    value.native=prepared.native;value.period,value.epoch=prepared.period,prepared.epoch
    value.inputDigest[:]=prepared.roomInputDigest
    return value


def ticks():
    k=C.WinDLL('kernel32',use_last_error=True);k.GetTickCount64.restype=C.c_uint64
    return k.GetTickCount64()


class SharedCallState:
    """Retained owner's common gate for reward, Snapshot, Stop and publication.

    Existing launchers must explicitly use invoke for ALL target operations.
    Merely sharing its lock does not propagate uncertainty or authorize cleanup.
    """
    def __init__(self,lock,mark_unknown):
        require(lock is not None and callable(mark_unknown),'Owner lock and unknown callback required')
        self.lock,self.mark_unknown=lock,mark_unknown;self.unknown=None
    def require_known(self):
        require(self.unknown is None,'Native control outcome unknown; no Snapshot/Stop/dependent call')
    def invoke(self,operation):
        with self.lock:
            self.require_known()
            try:return operation()
            except RemoteCallUnknown as exc:
                self.unknown=dict(error=repr(exc),record=deepcopy(exc.record))
                try:self.mark_unknown(exc)
                except BaseException as notification_error:
                    exc.owner_notification_error=repr(notification_error)
                raise


class RemoteTransport:
    """Explicit already-loaded module/API, with approved file and process pins.

    Uses the same call lock as Runtime Snapshot/Stop/publication. No DLL load or
    arbitrary address supplied by a command is supported.
    """
    def __init__(self,api,*,module,dll,dll_sha256,pid,birth,records,call_state):
        self.api,self.module,self.dll=api,module,Path(dll).resolve(strict=True)
        self.sha,self.pid,self.birth=dll_sha256,pid,birth
        self.records=Path(records).resolve(strict=True)
        require(self.records.is_dir() and journal.hex_id(dll_sha256),'Approved private output/build required')
        require(type(call_state) is SharedCallState,'Shared native call state required')
        self.state=call_state;self.lock=call_state.lock;self.calls=0;self.failed=None;self.approval=None
        self._identity()

    def _identity(self):
        self.state.require_known()
        require(self.failed is None,'Native reward transport terminal; no dependent call')
        k=self.api.k;k.GetProcessId.argtypes=[W.HANDLE];k.GetProcessId.restype=W.DWORD
        k.GetProcessTimes.argtypes=[W.HANDLE]+[C.c_void_p]*4;k.GetProcessTimes.restype=W.BOOL
        times=[C.c_uint64() for _ in range(4)]
        require(k.GetProcessId(self.api.handle)==self.pid and
                k.GetProcessTimes(self.api.handle,*(C.byref(t) for t in times)) and times[0].value==self.birth,
                'Native execution handle belongs to another process incarnation')
        require(self.api.reader.pid==self.pid and process_birth(self.api.reader)==self.birth,
                'Native process incarnation changed')
        require([(a,Path(p).resolve()) for a,p in self.api.modules() if Path(p).resolve()==self.dll]
                ==[(self.module,self.dll)],'Pinned reward Runtime module changed')
        now=module_approval(self.api.reader,self.module,self.dll,self.sha)
        if self.approval is None:self.approval=now
        require(now==self.approval,'Loaded reward Runtime identity changed')

    def call(self,name,payload):
        return self.state.invoke(lambda:self._perform(name,payload))

    def _perform(self,name,payload):
        import pefile
        with self.lock:
            try:
                self._identity()
                require(name in ('ASaveRuntimeRewardConfigure','ASaveRuntimeRewardSubmit','ASaveRuntimeRewardSnapshot'),
                        'Unsupported reward operation')
                pe=pefile.PE(str(self.dll))
                try:
                    matches=[s for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name==name.encode('ascii')]
                    require(len(matches)==1 and not matches[0].forwarder,'Unique local code export required')
                    rva=matches[0].address;address=self.module+rva
                    expected=pe.get_data(rva,32)
                finally:pe.close()
                require(len(expected)==32,'Complete export prefix required')
                readable(self.api.reader,address,32,allocation=self.module,execute=True)
                require(self.api.reader.memory.read(address,32)==expected,'Native export bytes changed')
                self.calls+=1
                result=remote_call(self.api,address,payload,self.records,f'{self.calls:04d}-{name}')
                self._identity()
                return result
            except BaseException as exc:
                self.failed=repr(exc)
                raise


def pending_intent(db,command,attachment):
    """Read the actual local SQLite reservation, not a caller's JSON permit."""
    require(type(db) is journal.ExecutionJournal,'Actual local execution journal required')
    require(db.identity['attachment_id']==attachment,'Journal attachment changed')
    with db._transaction() as conn:
        meta=conn.execute('SELECT identity,halt FROM metadata WHERE id=1').fetchone()
        require(meta and meta['identity']==journal.canonical(db.identity) and meta['halt'] is None,
                'Execution journal held or rebound')
        rows=conn.execute("SELECT * FROM entries WHERE status!='APPLIED' ORDER BY sequence").fetchall()
        require(len(rows)==1 and rows[0]['status']=='INTENT','Exactly one durable INTENT required before Submit')
        row=rows[0];intent=json.loads(row['intent']);journal.validate_intent(db.scope,intent)
        require(row['fingerprint']==journal.digest(intent) and row['sequence']==intent['sequence'] and
                row['player']==intent['player_id'] and row['request_id']==intent['request_id'] and
                journal.hex_id(row['token'],32),'Stored reservation identity changed')
        semantic=lambda c:{k:v for k,v in c.items() if k!='context_sha256'}
        require(semantic(intent['command'])==semantic(command),'Reserved command differs from local submission')
        return deepcopy(intent)


class RuntimeRewardPort:
    """CheckedPort.native, single attachment and native planning epoch.

    Configure only once. Bind the existing Replica.journal using attach_journal
    before dispatch. The outer Journal owns APPLIED/dedup; this class never
    invents a receipt after a timeout and never retries a Submit.
    """
    def __init__(self,sampler,transport,*,nonce,context,records,wait_seconds=10,poll_seconds=.02,
                 monotonic=time.monotonic,sleep=time.sleep,tick_count=ticks):
        require(type(sampler) is ContextSampler and type(context) is Context,'Exact local sampler/context required')
        require(type(nonce) is bytes and len(nonce)==32 and any(nonce),'Runtime nonce required')
        require(context.pid==sampler.pid and context.birth==sampler.birth and context.period and context.epoch and
                context.native.ownerGeneration and any(context.native.attempt) and any(context.native.attachment) and any(context.inputDigest),
                'Current Runtime process/native binding required')
        require(bytes(context.native.attachment).hex()==sampler.attachment_id,'Sampler must bind actual native attachment')
        require(0<wait_seconds<=30 and 0<poll_seconds<=1,'Bounded completion wait required')
        self.sampler,self.transport=sampler,transport;self.nonce=nonce;self.context=Context.from_buffer_copy(bytes(context))
        self.records=Path(records).resolve(strict=True);require(self.records.is_dir(),'Existing private records required')
        self.binding=(sampler.pid,sampler.birth,sampler.epoch,sampler.attachment_id)
        self.wait,self.poll=wait_seconds,poll_seconds;self.clock,self.sleep,self.ticks=monotonic,sleep,tick_count
        self.lock=threading.RLock();self.failed=None;self.configured=False;self.config_attempted=False
        self.db=None;self.attempted=set();self.calls=0;self.receipts=[]

    def identity(self):
        with self.sampler.lock,self.lock:
            require(self.failed is None,'Reward port terminal; native result must not be replayed')
            require(self.sampler._identity()==self.sampler.local_identity,'Reward Runtime attachment changed')
            return self.binding

    def attach_journal(self,db):
        with self.sampler.lock,self.lock:
            require(self.db is None and type(db) is journal.ExecutionJournal,'Attach actual journal once')
            require(db.identity['attachment_id']==self.binding[3],'Journal is from another attachment')
            require(set(v['force_id'] for v in db.scope['bindings'].values())==set(self.sampler.players),
                    'Journal actors differ from native actors')
            self.db=db

    def _request(self,typ,op):
        q=typ();q.header=base.Header(base.MAGIC,base.VERSION,C.sizeof(typ),OPS[op],0)
        q.nonce[:]=self.nonce;q.context=self.context
        return q

    def _call(self,op,q):
        self.identity();self.calls+=1;label=f'{self.calls:04d}-{op}'
        # Durable typed intent precedes every call; a failed log prevents call.
        save_new(self.records/(label+'-request.json'),base.values(q))
        code,raw=self.transport.call('ASaveRuntimeReward'+op,bytes(q))
        require(type(raw) is bytes and len(raw)==C.sizeof(q),'Reward response size differs')
        value=type(q).from_buffer_copy(raw)
        require(bytes(value.header)[:16]==bytes(q.header)[:16] and bytes(value.nonce)==self.nonce and
                bytes(value.context)==bytes(self.context),'Foreign reward reply binding')
        save_new(self.records/(label+'-reply.json'),dict(exit=code,report=base.values(value)))
        require(code==0 and value.header.result==0,'Native reward request rejected')
        if op!='Snapshot':require(raw[20:]==bytes(q)[20:],'Native request payload echo changed')
        self.identity()
        return value

    def _fail(self,exc):
        if self.failed is None:self.failed=repr(exc)
        self.sampler.retire(self.failed)
        try:save_new(self.records/'terminal.json',dict(error=self.failed,attempted=sorted(self.attempted),automatic_retry=False))
        except BaseException as record_error:
            try:exc.record_error=repr(record_error)
            except Exception:pass

    def configure(self):
        with self.sampler.lock,self.lock:
            try:
                self.identity();require(not self.config_attempted,'Reward configuration is once-only')
                self.sampler.capture();q=self._request(Configure,'Configure')
                for dst,(force,actor) in zip(q.actors,sorted(self.sampler.players.items())):
                    dst.force,dst.district,dst.ruler=force,actor['district'],actor['ruler']
                self.config_attempted=True;self._call('Configure',q);self.configured=True
            except BaseException as exc:self._fail(exc);raise

    def execute(self,command):
        with self.sampler.lock,self.lock:
            try:
                self.identity();require(self.configured,'Configure retained Runtime before dispatch')
                intent=pending_intent(self.db,command,self.binding[3]);seq=intent['sequence']
                require(seq not in self.attempted,'Submit was already attempted; never replay')
                contexts,_=self.sampler.capture();force=command['force_id']
                preview=reward.validate_reward(command,contexts[force],force)
                require(len(command['officer_ids'])<=16,'Native owned reward limit is sixteen officers')
                q=self._request(Submit,'Submit');q.sequence=seq;c=q.command
                c.nonce[:]=bytes.fromhex(journal.digest(intent));c.year=command['date']['year'];c.month=command['date']['month'];c.day=command['date']['day']
                c.viewer=self.sampler.viewer;c.actor=force;c.ruler=self.sampler.players[force]['ruler'];c.city=command['funding_city_id']
                c.district=preview['expected_costs']['charged_district_id'];c.count=len(command['officer_ids'])
                c.officers[:c.count]=command['officer_ids'];c.expiresAtTick=self.ticks()+int(self.wait*1000)
                expected_hash=command_hash(self.context,c);deadline=self.clock()+self.wait
                self.attempted.add(seq);self._call('Submit',q)
                while True:
                    s=self._call('Snapshot',self._request(Snapshot,'Snapshot'))
                    require(s.configured==1 and s.sequence==seq and
                            not any((s.error,s.ownerError,s.replayError,s.uncertain,s.stopped,s.abnormalCalls,
                                     s.fullInputHold,s.worldFenceProven,s.nativeGameplayEnabled)),
                            'Reward report failed, foreign, or claims unsupported coverage')
                    require(s.state in (2,3,4),'Reward left admitted execution lifecycle')
                    if s.state==2:
                        require(s.submitted==s.completed==seq-1,
                                'Queued request must retain the preceding completed native lane')
                    else:
                        require(s.submitted==seq and s.completed in (seq-1,seq),
                                'Native lane does not belong to this submitted sequence')
                    if s.state==4:
                        require(s.completed==seq and s.readyResealed==1 and s.queued==0 and s.active==0 and s.hostThread!=0 and
                                s.replayState==3 and s.nativeReturned==s.argsReleased==s.ownedSlotCleared==1 and
                                s.ctorCalls==s.dtorCalls==s.executeCalls==1 and s.appendCalls==c.count and s.captureCalls>0 and
                                s.finallyCalls>0 and bytes(s.commandSha256)==expected_hash and any(s.semanticSha256),
                                'Native completion, cleanup, or exact command proof missing')
                        result=dict(native_returned=True,args_released=True,owned_slot_cleared=True,error=0,uncertain=False,
                                    sequence=seq,command_sha256=expected_hash.hex(),report=base.values(s),
                                    input_exclusion_proven=False,native_gameplay_enabled=False)
                        self.receipts.append(result);return result
                    require(self.clock()<deadline,'Reward completion unresolved; retain INTENT and never replay')
                    self.sleep(min(self.poll,max(0,deadline-self.clock())))
            except BaseException as exc:self._fail(exc);raise
