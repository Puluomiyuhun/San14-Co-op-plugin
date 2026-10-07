"""Workspace-only bootstrap for the explicitly launched native Session fixture.

FIXTURE_ONLY: no game/Steam/window lookup, publisher, input or world evidence.
prepare_fixture obtains PID/birth before GuestTransition creates its attempt.
bootstrap is called by SessionNativePort *after* its durable journal INTENT.
The child accepts only two nonsecret IDs over its private stdin, then serves
the unchanged authenticated Session IPC. A fresh child never resumes an old
stage directory. Failed/ambiguous stages and once records are retained.
"""
from copy import deepcopy
from dataclasses import asdict
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import secrets
import subprocess
import threading
import time

from checkpoint_session_native_port import (SessionProfile, EvidenceRequest,
    BootstrapEvidence, FIXTURE)
from checkpoint_session_channel import Endpoint, SessionChannel
from checkpoint_visual_client import require, hexid
from authoritative_sync import canonical, digest, validate_manifest

HERE=Path(__file__).resolve().parent
EXE=HERE/'checkpoint_session_ipc_fixture.exe'
STAGES=HERE/'checkpoint_test_bootstrap_stages'
TARGET='svdexccSC03.s14'
SIZE=274880
SHA='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
GAME_SHA='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
NODE={'year':203,'month':8,'day':11,'phase':'PLANNING_BOUNDARY'}


def _sha(raw):return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    obj={}
    for key,value in pairs:
        require(key not in obj,'Duplicate fixture JSON member')
        obj[key]=value
    return obj


def _json(raw):
    def constant(_):raise ValueError('Nonfinite JSON number')
    return json.loads(raw,object_pairs_hook=_unique,parse_constant=constant)


def _plain(path,*,directory=False):
    s=path.lstat()
    require(not (getattr(s,'st_file_attributes',0)&0x400) and not path.is_symlink(),
            'Fixture path cannot be a reparse point')
    require(path.is_dir() if directory else path.is_file(),'Unexpected fixture path kind')
    if not directory:require(s.st_nlink==1,'Fixture file cannot have multiple links')


def _workspace_paths():
    # Check lexical ancestors before resolve; no target discovery is performed.
    for p in [HERE,*HERE.parents]:_plain(p,directory=True)
    if not STAGES.exists():
        try:STAGES.mkdir()
        except FileExistsError:pass
    _plain(STAGES,directory=True)


def _kernel():
    k=C.WinDLL('kernel32',use_last_error=True)
    signatures={
        'CreateFileW':(W.HANDLE,[W.LPCWSTR,W.DWORD,W.DWORD,C.c_void_p,W.DWORD,W.DWORD,W.HANDLE]),
        'CloseHandle':(W.BOOL,[W.HANDLE]),
        'GetProcessTimes':(W.BOOL,[W.HANDLE,C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),
                                 C.POINTER(W.FILETIME),C.POINTER(W.FILETIME)]),
        'MoveFileExW':(W.BOOL,[W.LPCWSTR,W.LPCWSTR,W.DWORD])}
    for name,(result,args) in signatures.items():
        f=getattr(k,name);f.restype=result;f.argtypes=args
    return k


class WorkspaceFixtureBootstrap:
    """A single prepared child and one bootstrap, never an automatic retry.

    Call prepare_fixture(), bind the returned PID/birth as a fixture target,
    construct GuestTransition, then let SessionNativePort call bootstrap.
    The latter verifies its complete request, but does not independently own
    the room journal: the caller's durable-permit validation remains mandatory.
    close() is explicit and only stops/terminates this object's own child;
    it retains all stage/intent files. No destructor or restart recovery.
    """
    provenance=FIXTURE

    def __init__(self,*,profile:SessionProfile,manifest:dict,
                 approved_fixture_sha256:str,timeout=10,idle_ms=15000,lifetime_ms=120000):
        require(os.name=='nt','Windows fixture backend required')
        require(type(profile) is SessionProfile and profile.provenance==FIXTURE,
                'This backend is FIXTURE_ONLY')
        profile.validate();validate_manifest(manifest)
        require(hexid(approved_fixture_sha256,64) and
                profile.session_binary_sha256==approved_fixture_sha256,
                'Fixture binary must match independently approved profile')
        require(profile.game_build_sha256==GAME_SHA and profile.target_basename==TARGET and
                profile.world_size==SIZE and profile.world_file_sha256==SHA and
                profile.node_sha256==digest(NODE) and manifest['node']==NODE and
                manifest['state_contract']==profile.state_contract and
                manifest['parts']['world.s14']=={'size':SIZE,'sha256':SHA},
                'Fixture supports only the fixed archived checkpoint')
        require(type(timeout) in (int,float) and math.isfinite(timeout) and 0<timeout<=30 and
                type(idle_ms) is int and 100<=idle_ms<=60000 and
                type(lifetime_ms) is int and 100<=lifetime_ms<=300000,
                'Invalid bounded fixture lifetime')
        self.profile=profile;self._manifest=canonical(manifest);self.approved=approved_fixture_sha256
        self.timeout=float(timeout);self.idle_ms=idle_ms;self.lifetime_ms=lifetime_ms
        self.k=_kernel();self.lock=threading.RLock();self.process=None;self._exe_pin=None
        self._channel=None;self._prepared=None;self._prepare_consumed=False;self._bootstrap_consumed=False
        self._phase='NEW';self._closed=False;self._q=queue.Queue(maxsize=4)
        self._stdout_done=threading.Event();self._io_fault=None;self._stderr_bytes=0
        self._threads=[];self._stage=None;self._receipt=None;self._binding_sha=None
        self._close_errors=[];self._bind_sent=False

    @property
    def channel(self):return self._channel

    @property
    def manifest(self):return json.loads(self._manifest)

    def _read_stdout(self):
        # Deliberately never keep a raw diagnostic tail: handshake contains a
        # secret. Generic errors exclude source lines and exception arguments.
        try:
            while True:
                raw=self.process.stdout.readline(8193)
                if not raw:break
                if len(raw)>8192 or not raw.endswith(b'\n'):
                    self._io_fault='INVALID_STDOUT_FRAME';continue
                try:
                    obj=_json(raw)
                    require(type(obj) is dict,'Expected fixture object')
                    self._q.put_nowait(obj)
                except Exception:self._io_fault='INVALID_STDOUT_OBJECT'
        except Exception:self._io_fault='STDOUT_READ_FAILED'
        finally:self._stdout_done.set()

    def _read_stderr(self):
        try:
            while True:
                raw=self.process.stderr.read(4096)
                if not raw:return
                self._stderr_bytes+=len(raw)
        except Exception:self._io_fault='STDERR_READ_FAILED'

    def _receive(self):
        end=time.monotonic()+self.timeout
        while True:
            require(self._io_fault is None,'Fixture output failed (raw output withheld)')
            try:return self._q.get(timeout=min(.05,max(.001,end-time.monotonic())))
            except queue.Empty:
                require(not self._stdout_done.is_set(),'Fixture output ended before acknowledgement')
                require(time.monotonic()<end,'Fixture acknowledgement timed out; do not retry')

    def _birth(self):
        b,e,k,u=W.FILETIME(),W.FILETIME(),W.FILETIME(),W.FILETIME()
        require(self.k.GetProcessTimes(W.HANDLE(int(self.process._handle)),C.byref(b),C.byref(e),
                    C.byref(k),C.byref(u)),'Cannot verify own child birth')
        return (b.dwHighDateTime<<32)|b.dwLowDateTime

    def prepare_fixture(self):
        with self.lock:
            require(not self._prepare_consumed and not self._closed,'Preparation already consumed')
            self._prepare_consumed=True
            try:
                _workspace_paths();_plain(EXE)
                # Prevent replacement between approval and CreateProcess and
                # retain the exact executable for this child's lifetime.
                h=self.k.CreateFileW(str(EXE),0x80000000,1,None,3,0,None)
                require(h not in (None,C.c_void_p(-1).value),'Cannot pin fixture executable')
                self._exe_pin=h
                require(_sha(EXE.read_bytes())==self.approved,'Fixture executable changed')
                self.process=subprocess.Popen([str(EXE),'--client-pid',str(os.getpid()),
                    '--idle-ms',str(self.idle_ms),'--lifetime-ms',str(self.lifetime_ms),
                    '--defer-bind','1','--staged','1'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,bufsize=0,creationflags=subprocess.CREATE_NO_WINDOW)
                for target in (self._read_stdout,self._read_stderr):
                    thread=threading.Thread(target=target,daemon=True);self._threads.append(thread);thread.start()
                ready=self._receive();birth=self._birth()
                require(set(ready)=={'fixture_prepared','server_pid','server_birth','waiting_for_binding','has_window'}
                    and ready['fixture_prepared'] is True and ready['server_pid']==self.process.pid and
                    ready['server_birth']==str(birth) and ready['waiting_for_binding'] is True and
                    ready['has_window'] is False and self.process.poll() is None,
                    'Own fixture preparation identity mismatch')
                self._prepared={'pid':self.process.pid,'birth':birth,'has_window':False,'provenance':FIXTURE}
                self._phase='PREPARED';return deepcopy(self._prepared)
            except BaseException:
                self._phase='UNCERTAIN';raise

    def _check_request(self,request,parts):
        require(type(request) is EvidenceRequest,'Typed bootstrap request required')
        b=request.binding;c=b.context;m=self.manifest
        b.target.validate()
        require(request.purpose=='BOOTSTRAP_BOUND_SESSION' and hexid(request.challenge) and
                type(request.requested_monotonic_ns) is int and
                0<request.requested_monotonic_ns<=time.monotonic_ns() and
                request.channel_sequence==0 and request.grant_json is None,
                'Foreign bootstrap request purpose/freshness')
        require(all(hexid(s) and any(bytes.fromhex(s)) for s in
                    (c.attempt,c.presentation,b.intent,b.lease,b.old_host,b.old_guest,b.epoch)) and
                b.old_host!=b.old_guest and b.target.attachment==b.old_guest and b.new_attachment is None,
                'Missing immutable attempt/intent/lease/attachments')
        require(b.target.pid==self._prepared['pid'] and b.target.birth==self._prepared['birth'] and
                self.process.poll() is None and self._birth()==b.target.birth,
                'Target must be the already prepared own fixture')
        require(b.profile_sha256==self.profile.sha256 and b.manifest_sha256==digest(m) and
                c.checkpoint_id==digest(m) and c.state_contract==self.profile.state_contract and
                b.epoch==m['epoch']==request.current_room_epoch and b.viewer_force==2 and
                b.semantic_world_sha256==m['world_sha256'] and b.world_file_sha256==SHA and
                b.adapter_file_sha256==m['parts']['adapter.json']['sha256'],
                'Bootstrap binding differs from approved checkpoint')
        require(type(parts) is dict and set(parts)=={'world.s14','adapter.json'} and
                all(type(parts[n]) is bytes and len(parts[n])==row['size'] and
                    _sha(parts[n])==row['sha256'] for n,row in m['parts'].items()),
                'Verified checkpoint parts differ from manifest')
        try:adapter=_json(parts['adapter.json'])
        except Exception:raise ValueError('Invalid adapter JSON') from None
        require(type(adapter) is dict,'Adapter state must be a JSON object')

    def _write_new(self,path,raw):
        temporary=path.with_name(path.name+'.tmp-'+secrets.token_hex(8))
        with temporary.open('xb') as f:
            require(f.write(raw)==len(raw),'Incomplete workspace stage write');f.flush();os.fsync(f.fileno())
        # MOVEFILE_WRITE_THROUGH, no REPLACE_EXISTING: Windows atomically
        # publishes each complete file, and a previous attempt is never erased.
        require(self.k.MoveFileExW(str(temporary),str(path),8),'Atomic workspace stage publish failed')
        _plain(path);require(path.read_bytes()==raw,'Workspace stage readback differs')

    def bootstrap(self,request,parts):
        with self.lock:
            require(self._phase=='PREPARED' and not self._closed and not self._bootstrap_consumed,
                    'Bootstrap already consumed or not prepared')
            self._bootstrap_consumed=True
            try:
                self._check_request(request,parts);_workspace_paths()
                b=request.binding;m=self.manifest;self._binding_sha=digest(asdict(b))
                stage=STAGES/b.context.attempt;stage.mkdir()  # exclusive attempt claim
                self._stage=stage;_plain(stage,directory=True)
                once={'schema':'san14.fixture-bootstrap-once.v1','provenance':FIXTURE,
                      'binding':asdict(b),'binding_sha256':self._binding_sha,
                      'profile_sha256':self.profile.sha256,'fixture_sha256':self.approved,
                      'manifest_sha256':digest(m),'parts':deepcopy(m['parts']),
                      'native_gameplay_enabled':False,'window_created':False}
                self._write_new(stage/'stage-once.json',canonical(once))
                for name in ('world.s14','adapter.json'):self._write_new(stage/name,parts[name])
                self._write_new(stage/'manifest.json',self._manifest)
                for name,row in m['parts'].items():
                    _plain(stage/name);raw=(stage/name).read_bytes()
                    require(len(raw)==row['size'] and _sha(raw)==row['sha256'],'Stage verification failed')
                receipt={'schema':'san14.fixture-bootstrap-stage.v1','provenance':FIXTURE,
                         'attempt':b.context.attempt,'intent':b.intent,'checkpoint_id':b.context.checkpoint_id,
                         'binding_sha256':self._binding_sha,'once_sha256':digest(once),
                         'manifest_sha256':digest(m),'profile_sha256':self.profile.sha256,
                         'fixture_sha256':self.approved,'parts':deepcopy(m['parts']),
                         'server_pid':b.target.pid,'server_birth':b.target.birth,
                         'verified_bytes_only':True,'native_load_complete':False}
                self._write_new(stage/'stage-ready.json',canonical(receipt));self._receipt=receipt
                # Mark consumed BEFORE the first possible write. An ambiguous
                # stdout response never causes a second BIND or a second child.
                self._bind_sent=True;self._phase='BIND_SENT'
                message=('BIND '+b.context.attempt+' '+b.intent+'\n').encode('ascii')
                require(self.process.stdin.write(message)==len(message),'Fixture binding write incomplete')
                self.process.stdin.flush();ready=self._receive()
                require(set(ready)=={'ready','pipe','server_pid','server_birth','attempt','intent','secret'} and
                        ready['ready'] is True and ready['server_pid']==b.target.pid and
                        ready['server_birth']==str(b.target.birth) and ready['attempt']==b.context.attempt and
                        ready['intent']==b.intent and hexid(ready['secret'],64) and self.process.poll() is None,
                        'Fixture ready binding differs from durable request')
                endpoint=Endpoint(ready['pipe'],b.target.pid,b.target.birth,bytes.fromhex(ready['secret']),
                                  bytes.fromhex(b.context.attempt),bytes.fromhex(b.intent))
                ready.clear();endpoint.validate()
                # The real transport independently checks server PID/birth
                # before sending the secret. Constructor performs no Arm.
                self._channel=SessionChannel(endpoint,timeout=min(self.timeout,5))
                self._phase='READY'
                attachment=secrets.token_hex(16)
                while attachment in (b.old_host,b.old_guest):attachment=secrets.token_hex(16)
                return BootstrapEvidence(request,self._channel,self.profile.sha256,self._manifest,
                    digest(receipt),SIZE,SHA,len(parts['adapter.json']),_sha(parts['adapter.json']),TARGET,
                    attachment,True,True,time.monotonic_ns())
            except BaseException:
                self._phase='UNCERTAIN';raise

    def status(self):
        with self.lock:
            return {'schema':'san14.fixture-bootstrap-status.v1','provenance':FIXTURE,'phase':self._phase,
                'prepared':deepcopy(self._prepared),'bootstrap_consumed':self._bootstrap_consumed,
                'binding_dispatched':self._bind_sent,'binding_sha256':self._binding_sha,
                'stage':str(self._stage) if self._stage else None,
                'stage_receipt_sha256':digest(self._receipt) if self._receipt else None,
                'fixture_sha256':self.approved,'exit_code':self.process.poll() if self.process else None,
                'io_fault':self._io_fault,'stderr_bytes':self._stderr_bytes,'closed':self._closed,
                'close_errors':list(self._close_errors),'native_gameplay_enabled':False,
                'native_input_barrier_proved':False,'full_world_verified':False,'has_window':False}

    def close(self):
        """Explicit fixture-only cleanup. Intents/staged artifacts stay on disk."""
        with self.lock:
            if self._closed:return self.status()
            self._closed=True
            if self._channel:
                try:self._channel.stop_keep_observing()
                except BaseException:self._close_errors.append('SESSION_STOP_UNCONFIRMED')
                try:self._channel.close()
                except BaseException:self._close_errors.append('CHANNEL_CLOSE_UNCONFIRMED')
            if self.process:
                try:
                    if self.process.stdin:self.process.stdin.close()
                    if self.process.poll() is None:
                        # This is our isolated fixture, never an attached game.
                        self.process.terminate()
                    self.process.wait(timeout=5)
                except BaseException:self._close_errors.append('FIXTURE_EXIT_UNCONFIRMED')
                for thread in self._threads:thread.join(timeout=1)
                if self.process.poll() is not None:
                    for stream in (self.process.stdout,self.process.stderr):
                        if stream:stream.close()
            if self._exe_pin is not None:
                if self.k.CloseHandle(self._exe_pin):self._exe_pin=None
                else:self._close_errors.append('EXECUTABLE_PIN_CLOSE_FAILED')
            self._phase='CLOSED' if not self._close_errors else 'CLOSED_WITH_ERRORS'
            return self.status()
