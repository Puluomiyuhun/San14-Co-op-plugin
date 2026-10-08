"""Owned child adapter sending a real captured Room scope to native Session.

Test harness only. No game discovery, production launcher or command channel
on stdio. Submit/Copy still use the authenticated frozen pipe client.
"""
import ctypes as C
from ctypes import wintypes as W
import os
import queue
import secrets
import struct
import subprocess
import threading

import a_save_ipc_flow_test as flow
import a_save_ipc_client as ipc
from authoritative_sync import sha
from planning_period_scope import validate, native_digest

SCOPE = struct.Struct('<16s16s16s32sQQHBBB')
assert SCOPE.size == 101


def encode_scope(value):
    validate(value)
    d=value['date']
    return SCOPE.pack(*(bytes.fromhex(value[k]) for k in
        ('room_id','binding_epoch','timeline_epoch','scope_sha256')),
        value['period'],value['base_sequence'],d['year'],d['month'],d['day'],value['viewer_force'])


class ScopedFixture(flow.OwnedFixture):
    def __init__(self, folder, native_room_id, native_room_epoch, *, planning_scope, mode=None):
        scope_bytes = encode_scope(planning_scope)
        expected_digest = native_digest(planning_scope)
        self.process = None
        self.endpoint = self.final = None
        self._pin = None
        self._threads = []
        self._messages = queue.Queue(maxsize=8)
        self._done = threading.Event()
        self._io_error = None
        self._closed = False
        self.stderr_bytes = 0
        self.cleanup_errors = []
        self.k = C.WinDLL('kernel32', use_last_error=True)
        for name, result, args in (
            ('CreateFileW', W.HANDLE, [W.LPCWSTR, W.DWORD, W.DWORD, C.c_void_p, W.DWORD, W.DWORD, W.HANDLE]),
            ('CloseHandle', W.BOOL, [W.HANDLE]),
            ('GetProcessTimes', W.BOOL, [W.HANDLE, C.POINTER(W.FILETIME), C.POINTER(W.FILETIME),
                                        C.POINTER(W.FILETIME), C.POINTER(W.FILETIME)])):
            fn = getattr(self.k, name); fn.restype = result; fn.argtypes = args
        executable = flow.BUILD / 'fixture.exe'
        folder.mkdir(parents=True, exist_ok=False)
        try:
            for item in (executable, *executable.parents):
                info = item.lstat()
                ipc.require(not item.is_symlink() and not (getattr(info, 'st_file_attributes', 0) & 0x400),
                    'Owned IPC executable cannot use reparse paths')
            self._pin = self.k.CreateFileW(str(executable), 0x80000000, 1, None, 3, 0, None)
            ipc.require(self._pin not in (None, C.c_void_p(-1).value), 'Cannot pin own IPC executable')
            ipc.require(sha(executable.read_bytes()) == flow.BUILD_EVIDENCE['fixture_sha256'], 'Pinned IPC binary differs')
            ipc.require(mode in (None, 'permit-stop'), 'Unknown owned fixture mode')
            args = [str(executable), str(folder), flow.BUILD_EVIDENCE['fixture_sha256'], str(os.getpid())]
            if mode is not None: args.append(mode)
            self.process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                bufsize=0, creationflags=subprocess.CREATE_NO_WINDOW)
            for target in (self._stdout, self._stderr):
                thread = threading.Thread(target=target, daemon=True); self._threads.append(thread); thread.start()
            prepared = self.message()
            birth = self.birth()
            ipc.require(prepared.get('schema') == 'san14.a-save-ipc-fixture.v1' and
                prepared.get('event') == 'PREPARED' and prepared.get('pid') == self.process.pid and
                prepared.get('birth') == str(birth) and prepared.get('game_access') is False,
                'Owned IPC child identity differs')
            secret, nonce = secrets.token_bytes(32), secrets.token_bytes(16)
            bootstrap = flow.BOOTSTRAP.pack(secret, native_room_id, native_room_epoch, nonce) + scope_bytes
            ipc.require(self.process.stdin.write(bootstrap) == len(bootstrap), 'Private bootstrap incomplete')
            self.process.stdin.flush()
            bound = self.message()
            ipc.require(bound.get('event') == 'PLANNING_SCOPE_BOUND' and
                bound.get('native_digest') == expected_digest and
                bound.get('initial_day') == planning_scope['date']['day'] and
                bound.get('period') == planning_scope['period'] and
                bound.get('session_initialized') is True,
                'Native Session did not bind the exact captured planning scope')
            self.planning_bound = bound
            ready = self.message()
            pipe = '\\\\.\\pipe\\san14-a-save-' + nonce.hex()
            ipc.require(ready.get('event') == 'READY' and ready.get('pipe_name') == pipe and
                ready.get('pid') == self.process.pid and ready.get('birth') == str(birth) and
                ready.get('source_kind') == 'FIXTURE_ONLY' and ready.get('capabilities') == 0,
                'Prepared native pipe does not match private bootstrap')
            self.endpoint = ipc.Endpoint(pipe, self.process.pid, birth, secret)
            self.endpoint.validate()
        except BaseException:
            self.close()
            raise

    def provide_next_scope(self, scope):
        """Owned fixture config; caller must first obtain a new settled Room scope."""
        raw=encode_scope(scope)
        ipc.require(not self._closed and self.process is not None and self.process.poll() is None,
                    'Owned scope receiver unavailable')
        ipc.require(self.process.stdin.write(raw)==len(raw),'Next private scope incomplete')
        self.process.stdin.flush()
