"""Bound private stdio controller for our own Session/planning test process.

No game/Steam/window discovery or access. No arbitrary child path, raw address,
file path, command payload or network protocol is accepted. This is FIXTURE_ONLY.
An observed planning boundary is never full-world, input or gameplay authority.
The new child requires an actual verified staged archive; there is no fallback.
Native-game-code false means no live attached game call; an archived menu block
is executed in our owned RX fixture and reported separately.
"""
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import secrets
import subprocess
import threading
import time

HERE=Path(__file__).resolve().parent
EXE=HERE/'checkpoint_admitted_runtime_fixture.exe'
STAGES=HERE/'checkpoint_admitted_runtime_stages'
SHA='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
SIZE=274880
DOMAIN=b'san14.guest-runtime-fixture.binding.v1'
CASES=('success-new', 'success-reused', 'entry-pending', 'late-pending', 'entry-ui', 'missing-prefetch', 'wrong-site', 'wrong-menu', 'foreign-menu', 'queue-exception', 'original-exception', 'reentry', 'stop-original', 'stop-before-user', 'stop-queue', 'stop-after-cas', 'actual-byte-mismatch', 'user-exception', 'report-state', 'stale-attempt', 'epoch-after')


class RuntimeFixtureError(RuntimeError):pass


def require(ok,message):
    if not ok:raise RuntimeFixtureError(message)


def _hex(value,size=32):return type(value) is str and re.fullmatch('[0-9a-f]{%d}'%size,value) is not None and any(bytes.fromhex(value))


def binding_values(attempt,intent):
    require(_hex(attempt) and _hex(intent),'Nonzero 128-bit attempt/intent required')
    raw=hashlib.sha256(DOMAIN+bytes.fromhex(attempt)+bytes.fromhex(intent)).digest()
    a,e=int.from_bytes(raw[:8],'little'),int.from_bytes(raw[8:16],'little')
    require(a and e,'Zero derived native token is unsupported')
    return {'attempt':attempt,'intent':intent,'binding_sha256':raw.hex(),
            'native_attempt':str(a),'observer_epoch':str(e)}


def _json(raw):
    def pairs(items):
        value={}
        for key,item in items:
            require(key not in value,'Duplicate runtime output key');value[key]=item
        return value
    return json.loads(raw,object_pairs_hook=pairs)


class RuntimeFixture:
    provenance='FIXTURE_ONLY'

    def __init__(self,*,approved_exe_sha256,case='success-new',timeout=10):
        require(_hex(approved_exe_sha256,64) and case in CASES,'Pinned own fixture and supported case required')
        require(type(timeout) in (int,float) and 0<timeout<=30,'Bounded timeout required')
        self.approved=approved_exe_sha256;self.case=case;self.timeout=timeout
        self.process=None;self.identity=None;self.binding=None;self._pin=None;self._threads=[]
        self.lock=threading.RLock();self._q=queue.Queue(maxsize=16);self._done=threading.Event()
        self._io_fault=None;self.stderr_bytes=0;self.phase='NEW';self.closed=False
        self.prepare_consumed=False;self.bind_consumed=False;self.arm_consumed=False;self.result_consumed=False
        self.report=None;self.cleanup_errors=[]
        self.consumed_world_source=None;self.stage=None
        self.k=C.WinDLL('kernel32',use_last_error=True)
        for name,result,args in (
            ('CreateFileW',W.HANDLE,[W.LPCWSTR,W.DWORD,W.DWORD,C.c_void_p,W.DWORD,W.DWORD,W.HANDLE]),
            ('CloseHandle',W.BOOL,[W.HANDLE]),
            ('MoveFileExW',W.BOOL,[W.LPCWSTR,W.LPCWSTR,W.DWORD]),
            ('GetProcessTimes',W.BOOL,[W.HANDLE,C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME)])):
            f=getattr(self.k,name);f.restype=result;f.argtypes=args

    def _stdout(self):
        try:
            while True:
                line=self.process.stdout.readline(16385)
                if not line:break
                if len(line)>16384 or not line.endswith(b'\n'):
                    self._io_fault='INVALID_FRAME';continue
                try:
                    row=_json(line);require(type(row) is dict,'Runtime object required');self._q.put_nowait(row)
                except Exception:self._io_fault='INVALID_OUTPUT'
        except Exception:self._io_fault='STDOUT_FAILED'
        finally:self._done.set()

    def _stderr(self):
        try:
            while True:
                raw=self.process.stderr.read(4096)
                if not raw:return
                self.stderr_bytes+=len(raw)
        except Exception:self._io_fault='STDERR_FAILED'

    def _next(self,timeout=None):
        end=time.monotonic()+(self.timeout if timeout is None else timeout)
        while True:
            require(self._io_fault is None,'Runtime output failed')
            try:return self._q.get(timeout=min(.05,max(.001,end-time.monotonic())))
            except queue.Empty:
                require(not self._done.is_set(),'Runtime EOF before receipt')
                require(time.monotonic()<end,'Runtime receipt timed out; no retry is allowed')

    def _send(self,line):
        require(self.process is not None and self.process.poll() is None and not self.closed,'Own runtime unavailable')
        raw=(line+'\n').encode('ascii')
        require(self.process.stdin.write(raw)==len(raw),'Runtime command write incomplete');self.process.stdin.flush()

    def _birth(self):
        b,e,k,u=W.FILETIME(),W.FILETIME(),W.FILETIME(),W.FILETIME()
        require(self.k.GetProcessTimes(W.HANDLE(int(self.process._handle)),C.byref(b),C.byref(e),C.byref(k),C.byref(u)),
                'Cannot verify own child birth')
        return (b.dwHighDateTime<<32)|b.dwLowDateTime

    def _write_new(self,path,data):
        temp=path.with_name(path.name+'.tmp-'+secrets.token_hex(8))
        with temp.open('xb') as stream:
            require(stream.write(data)==len(data),'Incomplete fixture stage write')
            stream.flush();os.fsync(stream.fileno())
        require(self.k.MoveFileExW(str(temp),str(path),8),'Atomic fixture stage publication failed')
        require(path.read_bytes()==data,'Fixture stage readback differs')

    def _stage_world(self,attempt,intent,raw):
        if not STAGES.exists():STAGES.mkdir()
        require(not(STAGES.stat().st_file_attributes&0x400) and STAGES.is_dir(),'Invalid fixture stage root')
        stage=STAGES/attempt;stage.mkdir();self.stage=stage
        marker=json.dumps({'attempt':attempt,'intent':intent,'sha256':SHA,'size':SIZE},
                          sort_keys=True,separators=(',',':')).encode('ascii')
        self._write_new(stage/'stage-once.json',marker)
        self._write_new(stage/'world.s14',raw)
        self._write_new(stage/'stage-ready.json',marker)

    def prepare(self):
        with self.lock:
            require(not self.prepare_consumed and not self.closed,'Preparation already consumed');self.prepare_consumed=True
            try:
                require(EXE.resolve(strict=True).parent==HERE and not EXE.is_symlink() and
                        not(EXE.stat().st_file_attributes&0x400),'Unexpected own executable path')
                h=self.k.CreateFileW(str(EXE),0x80000000,1,None,3,0,None)
                require(h not in (None,C.c_void_p(-1).value),'Cannot pin runtime executable');self._pin=h
                require(hashlib.sha256(EXE.read_bytes()).hexdigest()==self.approved,'Runtime binary differs from approval')
                self.process=subprocess.Popen([str(EXE),'--case',self.case],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,bufsize=0,creationflags=subprocess.CREATE_NO_WINDOW)
                for target in (self._stdout,self._stderr):
                    t=threading.Thread(target=target,daemon=True);self._threads.append(t);t.start()
                row=self._next();birth=self._birth()
                require(row.get('event')=='PREPARED' and row.get('schema')=='san14.admitted-runtime-fixture.v1' and
                    row.get('provenance')==self.provenance and row.get('pid')==self.process.pid and
                    row.get('birth')==str(birth) and row.get('has_window') is False and
                    row.get('archive_sha256')==SHA and row.get('archive_size')==SIZE and
                    row.get('fixture_case')==self.case and row.get('fixed_archive_only') is True,
                    'Prepared runtime identity differs')
                self.identity={**row,'birth':birth};self.phase='PREPARED';return dict(self.identity)
            except BaseException:self.phase='UNCERTAIN';raise

    def bind(self,attempt,intent,*,world_bytes=None):
        with self.lock:
            require(self.phase=='PREPARED' and not self.bind_consumed,'Binding already consumed/not prepared')
            self.bind_consumed=True
            try:
                values=binding_values(attempt,intent)
                if world_bytes is not None:
                    require(type(world_bytes) is bytes and len(world_bytes)==SIZE and
                        hashlib.sha256(world_bytes).hexdigest()==SHA,'Received checkpoint is not the fixed supported archive')
                    self._stage_world(attempt,intent,world_bytes)
                    self.consumed_world_source='verified_workspace_stage'
                else:self.consumed_world_source='verified_workspace_stage' # Child refuses a missing/invalid prepublished stage.
                self.binding=values  # Before possibly ambiguous stdin publication.
                self._send('BIND '+attempt+' '+intent);row=self._next()
                require(row.get('event')=='BOUND' and all(row.get(k)==v for k,v in values.items()) and
                    row.get('archive_sha256')==SHA and row.get('archive_size')==SIZE and row.get('armed') is False,
                    'Runtime BIND receipt differs')
                require(row.get('consumed_world_source')==self.consumed_world_source,'Runtime loaded an unexpected source')
                self.phase='BOUND';return row
            except BaseException:self.phase='UNCERTAIN';raise

    def arm_once(self):
        with self.lock:
            require(self.phase=='BOUND' and not self.arm_consumed,'ARM already consumed/not bound')
            self.arm_consumed=True;self.phase='ARM_SENT'
            try:self._send('ARM '+self.binding['attempt']+' '+self.binding['intent'])
            except BaseException:self.phase='UNCERTAIN';raise

    def wait_result(self,timeout=None):
        with self.lock:
            require(self.phase=='ARM_SENT' and not self.result_consumed,'Result already consumed/not armed')
            require(timeout is None or(type(timeout) in (int,float) and 0<timeout<=30),'Bounded result timeout required')
            self.result_consumed=True
            try:
                row=self._next(timeout)
                require(row.get('event')=='RUNTIME_RESULT' and row.get('schema')=='san14.admitted-runtime-fixture.v1' and
                    row.get('provenance')==self.provenance and row.get('pid')==self.identity['pid'] and
                    row.get('birth')==str(self.identity['birth']) and row.get('fixture_case')==self.case and
                    all(row.get(k)==v for k,v in self.binding.items()),'Runtime result binding differs')
                require(row.get('consumed_world_source')==self.consumed_world_source,'Runtime result source differs')
                require(all(row.get(k) is False for k in ('fullWorldVerified','inputExclusionProven',
                    'pixelPresentationProven','native_gameplay_enabled','game_access','native_game_code_executed',
                    'upstream_receipts_fabricated','production_enabled','same_process_repeat_load_proven')) and row.get('fixed_archive_only') is True,
                    'Runtime claims unsupported authority')
                require(row.get('admission_wired') is True and
                    all(type(row.get(k)) is bool for k in ('admission_prefetched','admission_eligible','admission_blocked')) and
                    all(type(row.get(k)) is int and row[k]>=0 for k in ('admission_error','admission_queue_authorizations',
                        'admission_queue_calls','admission_queue_returned','admission_commit_succeeded','admission_menu_bound',
                        'admission_scope_started','admission_scope_finished','admission_original_abnormal')),
                    'Missing actual admission diagnostics')
                self.report=row;self.phase='RESULT';return dict(row)
            except BaseException:self.phase='UNCERTAIN';raise

    def status(self):
        with self.lock:
            return {'provenance':self.provenance,'phase':self.phase,'pid':self.process.pid if self.process else None,
                'birth':self.identity['birth'] if self.identity else None,'binding':dict(self.binding) if self.binding else None,
                'arm_consumed':self.arm_consumed,'closed':self.closed,
                'exit_code':self.process.poll() if self.process else None,'errors':list(self.cleanup_errors),
                'io_fault':self._io_fault,'stderr_bytes':self.stderr_bytes,'has_window':False,
                'consumed_world_source':self.consumed_world_source,'stage':str(self.stage) if self.stage else None,
                'fixed_archive_only':True,'native_gameplay_enabled':False,'full_world_verified':False}

    def close(self):
        """Explicitly close only the owned test process; retain its intent files."""
        with self.lock:
            if self.closed:return self.status()
            if self.process and self.process.poll() is None:
                try:
                    suffix=' '+self.binding['attempt']+' '+self.binding['intent'] if self.binding else ''
                    self._send('STOP'+suffix)
                    end=time.monotonic()+self.timeout
                    while True:
                        row=self._next(max(.001,end-time.monotonic()))
                        if row.get('event')=='CLOSED':break
                        require(time.monotonic()<end,'Runtime close not acknowledged')
                    self.process.wait(timeout=5)
                except BaseException:
                    self.cleanup_errors.append('OWN_RUNTIME_STOP_UNCONFIRMED')
                    if self.process.poll() is None:self.process.terminate()
                    try:self.process.wait(timeout=5)
                    except BaseException:self.cleanup_errors.append('OWN_RUNTIME_EXIT_UNCONFIRMED')
            self.closed=True
            if self.process and self.process.poll() is not None:
                for t in self._threads:t.join(timeout=1)
                for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
                    if stream:stream.close()
            if self._pin is not None:
                if self.k.CloseHandle(self._pin):self._pin=None
                else:self.cleanup_errors.append('RUNTIME_PIN_CLOSE_FAILED')
            self.phase='CLOSED' if not self.cleanup_errors else 'CLOSED_WITH_ERRORS';return self.status()
