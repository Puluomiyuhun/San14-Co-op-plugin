"""Data-only ABI helpers. No process discovery, attachment, injection or game IO."""
import ctypes as C
import re
MAGIC=0x53414E1450465631
EXE_SHA256='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
PREFIX='C:\\Users\\52708\\Documents\\Codex\\2026-10-04\\ni-li\\work\\mod_research\\checkpoint_live_prefetch_'
class Config(C.Structure):
    _fields_=[('magic',C.c_uint64),('size',C.c_uint32),('version',C.c_uint32),('pid',C.c_uint32),('flags',C.c_uint32),
        ('birth',C.c_uint64),('base',C.c_uint64),('attempt',C.c_uint64),('attachment',C.c_ubyte*32),
        ('root',C.c_uint64),('world',C.c_uint64),('states',C.c_uint64*5),('toolbar',C.c_uint64),('panel',C.c_uint64),
        ('expectedUserThread',C.c_uint32),('reserved32',C.c_uint32),('journal',C.c_wchar*512),('reserved',C.c_uint64*4)]+[(n,C.c_uint64) for n in ('cache','stack','stackCapacity','queue','queueCapacity')]+[('expectedMode',C.c_uint32),('helperDeadlineMs',C.c_uint32),('generation',C.c_uint64)]
class ThreadStat(C.Structure):
    _fields_=[('threadId',C.c_uint32),('reserved',C.c_uint32)]+[(k,C.c_uint64) for k in ('before','after','firstCall','lastCall','pending')]
class Binding(C.Structure):
    _fields_=[('attempt',C.c_ubyte*16),('attachment',C.c_ubyte*16),('owner_generation',C.c_uint64)]
class PendingReport(C.Structure):
    _fields_=[(n,C.c_uint32) for n in ('decision','error','stage')]+[('call_id',C.c_uint64),('menu_command',C.c_int32)]+[(n,C.c_uint32) for n in ('user_phase','game_transition','load_queued','advance','panel_advance')]+[(n,C.c_uint64) for n in ('stack_count','queue_count')]+[(n,C.c_bool) for n in ('read_only','pending_admission_candidate','native_hook_installed','all_pending_sources_covered','full_input_hold')]
class HardwareReceipt(C.Structure):
    _fields_=[(n,C.c_uint32) for n in ('capture_kind','error','os_error','exception_code','thread')]+[(n,C.c_uint64) for n in ('call_id','site_rip','user')]+[('binding',Binding),('pending',PendingReport)]+[(n,C.c_uint32) for n in ('entered','captured','restored','finished','module_pinned','helper_deadline_exceeded','restore_uncertain','observer_calls')]+[('gpr',C.c_uint64*16),('rflags',C.c_uint64),('xmm',C.c_ubyte*256),('mxcsr',C.c_uint32),('original_dr',C.c_uint64*6),('restored_dr',C.c_uint64*6)]+[(n,C.c_bool) for n in ('original_code_unchanged','queue_authorized','full_input_hold')]
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
        ('lateBefore',C.c_uint64),('lateAfter',C.c_uint64),('pendingPairs',C.c_uint64)]+[('pendingBefore',PendingReport),('pendingAfter',PendingReport),('hardware',HardwareReceipt)]+[(n,C.c_uint32) for n in ('admissionClaimed','admissionStarted','admissionFinished','admissionClosed','admissionErrors','admissionAbnormal','admissionBindError','admissionCloseError','admissionBeginOk','admissionResolverCalls')]
assert C.sizeof(Config)==1272 and C.sizeof(Report)==7400 and C.sizeof(PendingReport)==72 and C.sizeof(HardwareReceipt)==696
def config_bytes(*,pid,birth,base,attempt,attachment_hex,root,world,states,toolbar,panel,journal,cache,stack,stack_capacity,queue,queue_capacity,expected_mode,helper_deadline_ms,generation,expected_thread=0):
    assert all(type(x)is int and 0<x<2**64 for x in (pid,birth,base,attempt,root,world,toolbar,panel))
    assert pid<2**32 and type(expected_thread)is int and 0<=expected_thread<2**32
    assert type(states) in (list,tuple) and len(states)==5 and all(type(x)is int and 0<x<2**64 for x in states)
    assert type(attachment_hex)is str and re.fullmatch('[0-9a-f]{64}',attachment_hex) and any(bytes.fromhex(attachment_hex))
    assert type(journal)is str and journal.startswith(PREFIX) and len(journal)<512 and '..' not in journal
    assert re.fullmatch('[A-Za-z0-9_.-]+',journal[len(PREFIX):])
    c=Config();c.magic=MAGIC;c.size=C.sizeof(c);c.version=1;c.pid=pid;c.birth=birth;c.base=base;c.attempt=attempt
    c.attachment[:]=bytes.fromhex(attachment_hex);c.root=root;c.world=world;c.states[:]=states;c.toolbar=toolbar;c.panel=panel;c.expectedUserThread=expected_thread;c.journal=journal
    assert all(type(x)is int and 0<x<2**64 for x in (cache,stack,generation))
    assert type(stack_capacity)is int and 5<=stack_capacity<=4096 and type(queue_capacity)is int and 0<=queue_capacity<=4096
    assert type(queue)is int and 0<=queue<2**64 and bool(queue)==bool(queue_capacity)
    assert type(expected_mode)is int and expected_mode in (0,1) and type(helper_deadline_ms)is int and 1<=helper_deadline_ms<=10000
    assert any(bytes.fromhex(attachment_hex[:32])) and any(bytes.fromhex(attachment_hex[32:]))
    c.cache=cache;c.stack=stack;c.stackCapacity=stack_capacity;c.queue=queue;c.queueCapacity=queue_capacity;c.expectedMode=expected_mode;c.helperDeadlineMs=helper_deadline_ms;c.generation=generation
    return bytes(c)
def decode_report(raw):
    assert type(raw)is bytes and len(raw)==C.sizeof(Report)
    r=Report.from_buffer_copy(raw);assert r.size==C.sizeof(Report) and r.version==3
    out={name:(list(value) if isinstance(value,C.Array) else value) for name,_ in Report._fields_ if name not in ('threads','pendingBefore','pendingAfter','hardware') for value in (getattr(r,name),)}
    assert 0<=r.threadCount<=128
    out['threads']=[dict(thread_id=t.threadId,before=t.before,after=t.after,first_call=t.firstCall,last_call=t.lastCall,pending=t.pending) for t in r.threads[:r.threadCount]]
    out['firstXmm0Hex']=bytes(r.firstXmm0).hex()
    for snake,camel in dict(thread_count='threadCount',thread_overflow='threadOverflow',thread_migrations='threadMigrations',matched_pairs='matchedPairs',pair_overflow='pairOverflow',pair_errors='pairErrors',pending_pairs='pendingPairs',late_before='lateBefore',late_after='lateAfter').items():out[snake]=out[camel]
    def pending(p):return {n:getattr(p,n) for n,_ in PendingReport._fields_}
    h=r.hardware
    out['pending_before']=pending(r.pendingBefore);out['pending_after']=pending(r.pendingAfter)
    out['hardware']={n:(list(getattr(h,n)) if isinstance(getattr(h,n),C.Array) else getattr(h,n)) for n,_ in HardwareReceipt._fields_ if n not in ('pending','binding')}
    out['hardware']['pending']=pending(h.pending)
    out['hardware']['binding']={'attempt_hex':bytes(h.binding.attempt).hex(),'attachment_hex':bytes(h.binding.attachment).hex(),'owner_generation':h.binding.owner_generation}
    out['hardware']['xmm_hex']=bytes(h.xmm).hex()
    for snake,camel in dict(admission_claimed='admissionClaimed',admission_started='admissionStarted',admission_finished='admissionFinished',admission_closed='admissionClosed',admission_errors='admissionErrors',admission_abnormal='admissionAbnormal',admission_bind_error='admissionBindError',admission_close_error='admissionCloseError',admission_begin_ok='admissionBeginOk',admission_resolver_calls='admissionResolverCalls').items():out[snake]=out[camel]
    return out
