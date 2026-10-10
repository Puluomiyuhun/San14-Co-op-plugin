"""Dedicated three-slot reward/planning ABI data. Import is inert."""
import ctypes as C
import hashlib,struct
import a_save_three_runtime_contract as base
MAGIC,VERSION=base.MAGIC,base.VERSION
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
    if type(prepared) is not base.Prepare:raise ValueError('Exact three-slot Prepare required')
    value=Context();value.pid,value.birth=prepared.pid,prepared.birth
    value.native=prepared.native;value.period,value.epoch=prepared.period,prepared.epoch
    value.inputDigest[:]=prepared.roomInputDigest
    return value

class Open(base.Packed):
    _fields_=[('header',base.Header),('nonce',base.U8*32),('context',Context),
              ('generation',base.U64),('artifactSha256',base.U8*32)]
class PlanningSnapshot(base.Packed):
    _fields_=Open._fields_+[(n,base.U32) for n in ('state','error','hostThread','opened','receiptMatched','stopped')]
assert C.sizeof(Open)==192 and C.sizeof(PlanningSnapshot)==216
OPS.update(OpenPlanning=14,PlanningSnapshot=15)
OPERATIONS={'Configure':Configure,'Submit':Submit,'Snapshot':Snapshot,'OpenPlanning':Open,'PlanningSnapshot':PlanningSnapshot}
TYPES={t.__name__:t for t in (Context,Actor,Configure,Command,Submit,Snapshot,Open,PlanningSnapshot)}
def envelope(kind,operation,nonce):
    if OPERATIONS.get(operation) is not kind:raise ValueError('Exact three-slot reward type/operation required')
    if type(nonce) is not bytes or len(nonce)!=32 or not any(nonce):raise ValueError('Nonzero immutable 32-byte nonce required')
    obj=kind();obj.header=base.Header(MAGIC,VERSION,C.sizeof(kind),OPS[operation],0);obj.nonce[:]=nonce;return obj
def decode(kind,operation,nonce,raw):
    expected=envelope(kind,operation,nonce)
    if type(raw) is not bytes or len(raw)!=C.sizeof(kind):raise ValueError('Exact immutable response size required')
    obj=kind.from_buffer_copy(raw);h=obj.header;e=expected.header
    if (h.magic,h.version,h.size,h.operation)!=(e.magic,e.version,e.size,e.operation) or bytes(obj.nonce)!=nonce:raise ValueError('Foreign response envelope')
    return obj

