"""Data-only ABI helpers. No process discovery, attachment, injection or game IO."""
import ctypes as C
import re
MAGIC=0x53414E144C495631
EXE_SHA256='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
PREFIX='C:\\Users\\52708\\Documents\\Codex\\2026-10-04\\ni-li\\work\\mod_research\\checkpoint_live_user_threads_v2_'
class Config(C.Structure):
    _fields_=[('magic',C.c_uint64),('size',C.c_uint32),('version',C.c_uint32),('pid',C.c_uint32),('flags',C.c_uint32),
        ('birth',C.c_uint64),('base',C.c_uint64),('attempt',C.c_uint64),('attachment',C.c_ubyte*32),
        ('root',C.c_uint64),('world',C.c_uint64),('states',C.c_uint64*5),('toolbar',C.c_uint64),('panel',C.c_uint64),
        ('expectedUserThread',C.c_uint32),('reserved32',C.c_uint32),('journal',C.c_wchar*512),('reserved',C.c_uint64*4)]
class ThreadStat(C.Structure):
    _fields_=[('threadId',C.c_uint32),('reserved',C.c_uint32)]+[(k,C.c_uint64) for k in ('before','after','firstCall','lastCall','pending')]
class Report(C.Structure):
    _fields_=[(k,C.c_uint32) for k in ('size','version','installed','stopped','error','exception','pid','ownerThread')]+[
        (k,C.c_uint64) for k in ('birth','base','attempt','user','slot','original','hook','before','after','matchingBefore',
        'matchingAfter','otherUser','unpaired','firstCall','lastCall','firstCaller','lastCaller')]+[
        ('firstArgs',C.c_uint64*4),('firstRax',C.c_uint64),('firstXmm0',C.c_ubyte*16)]+[
        (k,C.c_uint32) for k in ('firstPair','contextVerified','slotRestored','protectionRestored','modulePinned',
        'journalCreated','journalFlushed','active')]+[(k,C.c_uint64) for k in ('bridgeStarted','bridgeReturned','bridgeAbnormal')]+[
        (k,C.c_uint32) for k in ('queueCalls','requestCas','loadRequested','fullInputHold','schedulerFenceProven','completeSessionInstalled')]+[('reserved',C.c_uint32*2)]+[
        ('threadCount',C.c_uint32),('threadOverflow',C.c_uint32),('threadMigrations',C.c_uint64),
        ('lastObservedThread',C.c_uint32),('mode',C.c_uint32),('matchedPairs',C.c_uint64),
        ('pairOverflow',C.c_uint32),('pairErrors',C.c_uint32),('threads',ThreadStat*128),
        ('lateBefore',C.c_uint64),('lateAfter',C.c_uint64),('pendingPairs',C.c_uint64)]
assert C.sizeof(Config)==1216 and C.sizeof(Report)==6520
def config_bytes(*,pid,birth,base,attempt,attachment_hex,root,world,states,toolbar,panel,journal,expected_thread=0):
    assert all(type(x)is int and 0<x<2**64 for x in (pid,birth,base,attempt,root,world,toolbar,panel))
    assert pid<2**32 and type(expected_thread)is int and 0<=expected_thread<2**32
    assert type(states) in (list,tuple) and len(states)==5 and all(type(x)is int and 0<x<2**64 for x in states)
    assert type(attachment_hex)is str and re.fullmatch('[0-9a-f]{64}',attachment_hex) and any(bytes.fromhex(attachment_hex))
    assert type(journal)is str and journal.startswith(PREFIX) and len(journal)<512 and '..' not in journal
    assert re.fullmatch('[A-Za-z0-9_.-]+',journal[len(PREFIX):])
    c=Config();c.magic=MAGIC;c.size=C.sizeof(c);c.version=1;c.pid=pid;c.birth=birth;c.base=base;c.attempt=attempt
    c.attachment[:]=bytes.fromhex(attachment_hex);c.root=root;c.world=world;c.states[:]=states;c.toolbar=toolbar;c.panel=panel;c.expectedUserThread=expected_thread;c.journal=journal
    return bytes(c)
def decode_report(raw):
    assert type(raw)is bytes and len(raw)==C.sizeof(Report)
    r=Report.from_buffer_copy(raw);assert r.size==C.sizeof(Report) and r.version==2
    out={name:(list(value) if isinstance(value,C.Array) else value) for name,_ in Report._fields_ if name!='threads' for value in (getattr(r,name),)}
    assert 0<=r.threadCount<=128
    out['threads']=[dict(thread_id=t.threadId,before=t.before,after=t.after,first_call=t.firstCall,last_call=t.lastCall,pending=t.pending) for t in r.threads[:r.threadCount]]
    out['firstXmm0Hex']=bytes(r.firstXmm0).hex()
    for snake,camel in dict(thread_count='threadCount',thread_overflow='threadOverflow',thread_migrations='threadMigrations',matched_pairs='matchedPairs',pair_overflow='pairOverflow',pair_errors='pairErrors',pending_pairs='pendingPairs',late_before='lateBefore',late_after='lateAfter').items():out[snake]=out[camel]
    return out
