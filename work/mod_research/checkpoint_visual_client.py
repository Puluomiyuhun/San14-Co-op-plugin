"""Fail-closed JSONL client for the frozen map helper. No game/process discovery.

Only PopenJsonTransport.start explicitly creates a process: the supplied helper.
All window capture remains in that helper. Pixel receipts are not input/world
evidence. No destructor/context manager terminates a covered helper implicitly.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
from functools import wraps
from typing import Protocol


class VisualError(RuntimeError):
    pass


class TransportEOF(VisualError):
    pass


def require(test, message):
    if not test:
        raise VisualError(message)


def hexid(value, length=32):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{%d}' % length, value) is not None


def uint(value, *, positive=False):
    require(type(value) is str and re.fullmatch(r'0|[1-9][0-9]*', value) is not None,
            'Unsigned decimal string required')
    number = int(value)
    require(number <= 2**64-1 and (number > 0 if positive else number >= 0), 'Integer out of range')
    return number


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


class JsonTransport(Protocol):
    """receive raises queue.Empty on timeout and TransportEOF on closed output."""
    @property
    def pid(self) -> int: ...
    def send(self, value: dict) -> None: ...
    def receive(self, timeout: float) -> dict: ...
    def close_input(self) -> None: ...
    def wait(self, timeout: float) -> int: ...
    def terminate(self) -> None: ...


class PopenJsonTransport:
    """Continuously drains both pipes, even while the caller does other work."""
    def __init__(self, process):
        self.process = process
        self._incoming = queue.Queue(maxsize=256)
        self._io_fault = None
        self._output_done = threading.Event()
        self._write_lock = threading.Lock()
        self.stderr_tail = deque(maxlen=64)
        self._reader = threading.Thread(target=self._read, name='visual-stdout', daemon=True)
        self._stderr = threading.Thread(target=self._read_stderr, name='visual-stderr', daemon=True)
        self._reader.start()
        self._stderr.start()

    @classmethod
    def start(cls, executable, *, expected_sha256):
        path = Path(executable).resolve(strict=True)
        require(hexid(expected_sha256, 64), 'Pinned helper SHA required')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha256,
                'Helper binary differs from approved fixture')
        process = subprocess.Popen([str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=0,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return cls(process)

    @property
    def pid(self):
        return self.process.pid

    def _read(self):
        try:
            while True:
                raw = self.process.stdout.readline(65537)
                if not raw:
                    break
                if len(raw) > 65536 or not raw.endswith(b'\n'):
                    self._io_fault = 'Oversized or incomplete helper JSON line'
                    # Continue draining rather than blocking the child on stdout.
                    continue
                try:
                    value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object)
                    require(type(value) is dict, 'Helper JSON object required')
                    self._incoming.put_nowait(value)
                except Exception as error:
                    self._io_fault = type(error).__name__ + ': ' + str(error)
        except Exception as error:
            self._io_fault = type(error).__name__ + ': ' + str(error)
        finally:
            self._output_done.set()

    def _read_stderr(self):
        try:
            while True:
                data = self.process.stderr.read(2048)
                if not data:
                    break
                self.stderr_tail.append(data.decode('utf-8', errors='replace'))
        except Exception as error:
            self.stderr_tail.append('stderr drain: ' + repr(error))

    def send(self, value):
        raw = (json.dumps(value, ensure_ascii=True, separators=(',', ':')) + '\n').encode('ascii')
        require(len(raw) <= 65536, 'Command too large')
        with self._write_lock:
            try:
                offset = 0
                while offset < len(raw):
                    written = self.process.stdin.write(raw[offset:])
                    if not written:
                        raise OSError('Incomplete command write')
                    offset += written
                self.process.stdin.flush()
            except (OSError, ValueError) as error:
                raise TransportEOF('Helper input closed') from error

    def receive(self, timeout):
        if self._io_fault:
            raise VisualError('Helper stream rejected: ' + self._io_fault)
        try:
            return self._incoming.get(timeout=timeout)
        except queue.Empty:
            if self._output_done.is_set():
                raise TransportEOF('Helper output closed')
            raise

    def close_input(self):
        with self._write_lock:
            self.process.stdin.close()

    def wait(self, timeout):
        return self.process.wait(timeout=timeout)

    def terminate(self):
        self.process.terminate()


@dataclass(frozen=True)
class TargetBinding:
    hwnd: int
    pid: int
    birth: int
    window_class: str
    attachment: str
    view: str
    window_mode: str
    idle_timeout_ms: int = 30000

    def validate(self):
        require(type(self.hwnd) is int and 0 < self.hwnd < 2**64, 'Explicit HWND required')
        require(type(self.pid) is int and 0 < self.pid <= 2**32-1, 'Explicit PID required')
        require(type(self.birth) is int and 0 < self.birth < 2**64, 'Process birth required')
        require(type(self.window_class) is str and 0 < len(self.window_class) <= 256 and '\0' not in self.window_class,
                'Exact window class required')
        require(hexid(self.attachment) and hexid(self.view), 'Attachment/view binding required')
        require(self.window_mode in ('windowed', 'borderless'), 'Unsupported window mode')
        require(type(self.idle_timeout_ms) is int and 200 <= self.idle_timeout_ms <= 600000,
                'Invalid heartbeat deadline')


@dataclass(frozen=True)
class HelperSnapshot:
    session: str
    phase: str
    surface: str
    helper_pid: int
    helper_birth: int
    cover_hwnd: int
    visible: bool
    pixels_retained: bool
    binding_lost: bool
    hold_reason: str


@dataclass(frozen=True)
class CoverReceipt:
    session: str
    surface: str
    attachment: str
    view: str
    frame: str
    sha256: str
    capture_time: int
    cover_time: int
    cover_hwnd: int


@dataclass(frozen=True)
class PreparedReceipt:
    session: str
    surface: str
    attachment: str
    view: str
    frame: str
    sha256: str
    token: str
    capture_time: int
    minimum_time: int


@dataclass(frozen=True)
class RevealReceipt:
    session: str
    surface: str
    attachment: str
    frame: str
    prepared_token: str
    controller_grant: str
    capture_time: int
    minimum_time: int


def _serialized(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._operation_lock:
            return method(self, *args, **kwargs)
    return wrapped


class VisualClient:
    """One session, one helper, one transition. No automatic reveal or retry.

    Heartbeats are explicit ping() calls by the root's connected/current-epoch
    controller. The receiver itself never extends an abandoned hold's lease.
    """
    def __init__(self, transport: JsonTransport, *, session, timeout=8.0):
        require(hexid(session), 'Session nonce required')
        require(type(timeout) in (int, float) and 0 < timeout <= 60, 'Bounded timeout required')
        self.transport, self.session, self.timeout = transport, session, float(timeout)
        self._cv = threading.Condition(threading.RLock())
        self._commands = threading.Lock()
        self._operation_lock = threading.RLock()
        self._snapshot = None
        self._ready = False
        self._fault = None
        self._pending = {}
        self._retired = set()
        self._serial = 0
        self._stopping = False
        self._closed = False
        self.binding = None
        self.cover_receipt = None
        self.prepared_receipt = None
        self.reveal_receipt = None
        self.events = deque(maxlen=128)
        self._receiver = threading.Thread(target=self._receive, name='visual-protocol', daemon=True)
        self._receiver.start()
        with self._cv:
            end = time.monotonic()+self.timeout
            while not self._ready and not self._fault:
                left = end-time.monotonic()
                if left <= 0:
                    self._trip('Helper startup timed out')
                    break
                self._cv.wait(left)
            require(self._ready and not self._fault, self._fault or 'Helper not ready')

    @property
    def fault(self):
        with self._cv:
            return self._fault

    @property
    def snapshot(self):
        with self._cv:
            return self._snapshot

    def _trip(self, reason):
        with self._cv:
            if self._fault is None:
                self._fault = reason
            self._cv.notify_all()

    def _parse_snapshot(self, value, *, startup=False):
        require(type(value) is dict and type(value.get('id')) is str, 'Missing response ID')
        require(type(value.get('ok')) is bool, 'Response ok must be boolean')
        require(value.get('session') == ('' if startup else self.session), 'Foreign helper session')
        for key in ('input_gate_provided', 'physical_monitor_unoccluded_proved',
                    'native_load_requested', 'gameplay_authorized'):
            require(value.get(key) is False, 'Helper claimed unsupported authority: '+key)
        for key in ('cover_window_visible', 'old_pixels_retained', 'target_binding_lost'):
            require(type(value.get(key)) is bool, 'Invalid observation flag: '+key)
        require(value.get('phase') in ('NEW', 'BOUND', 'ARMING', 'COVERED', 'PREPARING',
                                      'PREPARED', 'REVEALING', 'REVEALED', 'HELD'), 'Unknown helper phase')
        require(hexid(value.get('surface')), 'Missing surface nonce')
        require(value.get('cover_class') == 'CheckpointMapWaitHelper', 'Wrong cover class')
        require(uint(value.get('cover_activations')) == 0, 'Cover unexpectedly activated')
        pid = uint(value.get('helper_pid'), positive=True)
        require(pid == self.transport.pid, 'Unexpected helper PID')
        created = uint(value.get('helper_birth'), positive=True)
        hwnd = uint(value.get('cover_hwnd'))
        require(type(value.get('hold_reason')) is str and type(value.get('error')) is str,
                'Invalid diagnostic fields')
        if value['phase'] in ('NEW', 'BOUND'):
            require(hwnd == 0 and not value['cover_window_visible'] and not value['old_pixels_retained'],
                    'Unexpected cover before arming')
        elif value['phase'] in ('COVERED', 'PREPARED'):
            require(hwnd > 0 and value['cover_window_visible'] and value['old_pixels_retained'] and
                    not value['target_binding_lost'], 'Active cover observation was lost')
        elif value['phase'] == 'REVEALED':
            require(hwnd > 0 and not value['cover_window_visible'] and value['old_pixels_retained'],
                    'Inconsistent revealed snapshot')
        if self._snapshot:
            require(value['surface'] == self._snapshot.surface and created == self._snapshot.helper_birth,
                    'Helper identity changed')
            if self._snapshot.cover_hwnd:
                require(hwnd == self._snapshot.cover_hwnd, 'Cover HWND changed')
        return HelperSnapshot(value['session'], value['phase'], value['surface'], pid, created, hwnd,
                              value['cover_window_visible'], value['old_pixels_retained'],
                              value['target_binding_lost'], value['hold_reason'])

    def _receive(self):
        while not self._closed:
            try:
                value = self.transport.receive(.1)
            except queue.Empty:
                continue
            except Exception as error:
                if not self._stopping:
                    self._trip(type(error).__name__ + ': ' + str(error))
                return
            try:
                with self._cv:
                    if not self._ready:
                        snap = self._parse_snapshot(value, startup=True)
                        require(value.get('event') == 'READY_NO_TARGET' and value['id'] == '' and
                                value['ok'] and snap.phase == 'NEW' and not snap.cover_hwnd and
                                not snap.visible and not snap.pixels_retained and not snap.binding_lost,
                                'Invalid helper startup')
                        self._snapshot = snap
                        self._ready = True
                    else:
                        snap = self._parse_snapshot(value)
                        rid = value['id']
                        if rid == '':
                            require(value.get('event') == 'HELD' and snap.phase == 'HELD',
                                    'Unknown unsolicited helper event')
                            self._snapshot = snap
                            self.events.append(dict(value))
                            self._trip('Helper HELD: ' + snap.hold_reason)
                        elif rid in self._retired:
                            # A delayed response cannot resurrect a timed-out request.
                            self.events.append({'late_response': rid})
                            self._trip('Late/duplicate response after completion')
                        else:
                            require(rid in self._pending, 'Unknown response ID')
                            item = self._pending[rid]
                            require(item['response'] is None, 'Duplicate pending response')
                            self._snapshot = snap
                            item['response'] = value
                            if item['op'] in ('stop', 'force_stop') and value['ok']:
                                self._stopping = True
                            if snap.phase == 'HELD' or snap.binding_lost:
                                self._trip('Helper HELD or target lost: ' + snap.hold_reason)
                    self._cv.notify_all()
            except Exception as error:
                self._trip('Protocol rejected: ' + str(error))

    def _call(self, op, *, allow_fault=False, **fields):
        with self._commands:
            with self._cv:
                require(not self._closed, 'Client closed')
                require(allow_fault or not self._fault, self._fault or 'Client failed')
                self._serial += 1
                rid = str(self._serial)
                item = {'response': None, 'op': op}
                self._pending[rid] = item
            try:
                self.transport.send({'id': rid, 'op': op, 'session': self.session, **fields})
                with self._cv:
                    end = time.monotonic()+self.timeout
                    while item['response'] is None:
                        if self._fault and not allow_fault:
                            raise VisualError(self._fault)
                        left = end-time.monotonic()
                        if left <= 0:
                            self._trip('Command timed out: '+op)
                            raise VisualError(self._fault)
                        self._cv.wait(left)
                    response = item['response']
                    require(allow_fault or not self._fault, self._fault or 'Client failed')
                    require(response['ok'], 'Helper rejected '+op+': '+response.get('error', ''))
                    return response
            except Exception as error:
                self._trip(str(error))
                raise
            finally:
                with self._cv:
                    self._pending.pop(rid, None)
                    self._retired.add(rid)

    def _validate(self, function):
        try:
            return function()
        except Exception as error:
            self._trip('Receipt rejected: '+str(error))
            raise

    def assert_current(self, receipt, phases):
        with self._cv:
            require(not self._fault and not self._closed, self._fault or 'Client closed')
            require(type(receipt) in (CoverReceipt, PreparedReceipt, RevealReceipt), 'Typed accepted receipt required')
            require(self._snapshot and self._snapshot.phase in phases and
                    receipt.session == self.session and receipt.surface == self._snapshot.surface and
                    not self._snapshot.binding_lost, 'Receipt is not current')
            expected = (self.cover_receipt if type(receipt) is CoverReceipt else
                        self.prepared_receipt if type(receipt) is PreparedReceipt else
                        self.reveal_receipt if type(receipt) is RevealReceipt else None)
            require(expected is not None and receipt == expected, 'Receipt was not accepted by this client')

    @_serialized
    def bind(self, binding: TargetBinding):
        require(type(binding) is TargetBinding, 'Typed target required')
        binding.validate()
        require(self.binding is None and self.snapshot.phase == 'NEW', 'Binding already consumed')
        # Bind is consumed before I/O, even if the outcome becomes uncertain.
        self.binding = binding
        r = self._call('bind', hwnd=str(binding.hwnd), pid=binding.pid, birth=str(binding.birth),
                       **{'class': binding.window_class}, attachment=binding.attachment,
                       view=binding.view, window_mode=binding.window_mode,
                       idle_timeout_ms=binding.idle_timeout_ms)
        self._validate(lambda: require(r['phase'] == 'BOUND' and r['cover_hwnd'] == '0' and
                                      not r['cover_window_visible'], 'Bad bind receipt'))
        return self.snapshot

    @_serialized
    def cover(self):
        require(self.binding is not None and self.snapshot.phase == 'BOUND', 'Cover out of order')
        r = self._call('cover')
        def validate():
            require(r['phase'] == 'COVERED' and r['cover_window_visible'] and r['old_pixels_retained'],
                    'Cover not retained/visible')
            require(r.get('old_attachment') == self.binding.attachment and r.get('view') == self.binding.view,
                    'Cover attachment/view mismatch')
            require(hexid(r.get('old_frame')) and hexid(r.get('old_frame_sha256'),64) and
                    r.get('cover_observation') == 'OWN_WGC_FRAME_ONLY', 'Bad cover frame evidence')
            old = uint(r.get('old_capture_time'), positive=True)
            shown = uint(r.get('cover_capture_time'), positive=True)
            require(shown > old, 'Cover acknowledgement predates source frame')
            return CoverReceipt(self.session, r['surface'], self.binding.attachment, self.binding.view,
                                r['old_frame'], r['old_frame_sha256'], old, shown,
                                uint(r['cover_hwnd'], positive=True))
        self.cover_receipt = self._validate(validate)
        return self.cover_receipt

    @_serialized
    def prepare(self, *, new_attachment, after_time):
        self.assert_current(self.cover_receipt, ('COVERED',))
        require(hexid(new_attachment) and new_attachment != self.binding.attachment, 'New attachment required')
        require(type(after_time) is int and 0 <= after_time < 2**63, 'Native cutoff required')
        r = self._call('prepare', new_attachment=new_attachment, view=self.binding.view,
                       after_time=str(after_time))
        def validate():
            require(r['phase'] == 'PREPARED' and r['cover_window_visible'] and r['old_pixels_retained'],
                    'Cover lost while preparing')
            require(r.get('new_attachment') == new_attachment and r.get('view') == self.binding.view and
                    hexid(r.get('prepared_token')) and hexid(r.get('new_frame')) and
                    r['new_frame'] != self.cover_receipt.frame and hexid(r.get('new_frame_sha256'),64) and
                    r.get('world_attribution') == 'CALLER_ASSERTION_ONLY', 'Prepared identity mismatch')
            captured = uint(r.get('capture_time'), positive=True)
            cutoff = uint(r.get('minimum_frame_time'), positive=True)
            require(captured > cutoff >= after_time and captured > self.cover_receipt.capture_time,
                    'New frame is not fresh')
            return PreparedReceipt(self.session,r['surface'],new_attachment,self.binding.view,
                                   r['new_frame'],r['new_frame_sha256'],r['prepared_token'],captured,cutoff)
        self.prepared_receipt = self._validate(validate)
        return self.prepared_receipt

    @_serialized
    def reveal(self, prepared: PreparedReceipt, *, controller_grant):
        self.assert_current(prepared, ('PREPARED',))
        require(hexid(controller_grant), 'Explicit controller grant required')
        r = self._call('reveal', prepared_token=prepared.token, new_attachment=prepared.attachment,
                       view=prepared.view, new_frame=prepared.frame, controller_grant=controller_grant)
        def validate():
            require(r['phase'] == 'REVEALED' and not r['cover_window_visible'] and
                    r.get('image_release_confirmed') is True and
                    r.get('new_attachment') == prepared.attachment and r.get('new_frame') == prepared.frame and
                    r.get('prepared_token') == prepared.token, 'Reveal identity or visibility mismatch')
            captured = uint(r.get('new_cover_capture_time'), positive=True)
            cutoff = uint(r.get('minimum_frame_time'), positive=True)
            require(captured > cutoff >= prepared.capture_time, 'Reveal frame is not fresh')
            return RevealReceipt(self.session,r['surface'],prepared.attachment,prepared.frame,
                                 prepared.token,controller_grant,captured,cutoff)
        self.reveal_receipt = self._validate(validate)
        return self.reveal_receipt

    @_serialized
    def ping(self):
        self._call('ping')
        return self.snapshot

    @_serialized
    def hold(self, message):
        require(type(message) is str and 1 <= len(message) <= 80, 'Bounded hold reason required')
        try:
            r = self._call('hold', allow_fault=True, message=message)
            require(r['phase'] == 'HELD', 'Helper did not enter HELD')
            return self.snapshot
        finally:
            self._trip('Controller hold: '+message)

    @_serialized
    def cleanup(self, *, accept_cover_loss=False):
        """Explicit, never automatic. No termination fallback on failed cleanup."""
        require(type(accept_cover_loss) is bool, 'Explicit cleanup choice required')
        if accept_cover_loss:
            r = self._call('force_stop', allow_fault=True, accept_cover_loss=True)
            require(r.get('cover_loss_explicit') is True, 'Explicit cleanup was not acknowledged')
        else:
            require(not self.fault and self.snapshot.phase in ('NEW','BOUND','REVEALED'),
                    'Cleanup could remove an active/uncertain cover')
            r = self._call('stop')
        self._stopping = True
        code = self.transport.wait(self.timeout)
        require(code == 0, 'Helper exited abnormally during cleanup')
        self._closed = True
        self._receiver.join(timeout=.5)
        return {'helper_exited':True,'cover_loss_accepted':accept_cover_loss,
                'native_input_released':False}

    @_serialized
    def terminate_helper(self, *, accept_cover_loss):
        """Last-resort explicit loss of this helper only. Never opens native input."""
        require(accept_cover_loss is True, 'Explicit cover loss acknowledgement required')
        self._trip('Explicit helper termination')
        self._stopping = True
        self.transport.terminate()
        self.transport.wait(self.timeout)
        self._closed = True
        self._receiver.join(timeout=.5)
        return {'helper_terminated':True,'native_input_released':False}
