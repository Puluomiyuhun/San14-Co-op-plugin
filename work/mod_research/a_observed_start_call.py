"""Narrow remote_call successor: unresolved status survives cleanup/log failures.
Original allocation/thread/wait/response/free predicates are unchanged.
"""
import ctypes as C
from ctypes import wintypes as W
import hashlib
import os
from pathlib import Path
import time
from a_save_runtime_control import require,save_new,RemoteCallUnknown


def remote_call(api, address, payload, run, label, *, timeout_ms=10000):
    """One typed in/out LPVOID call; never call while a debugger holds target.

    A retained buffer on uncertain completion is intentional. No thread kill,
    DLL unload or automatic repeat is allowed. The caller must stop dependent
    work after RemoteCallUnknown and inspect this exact record.
    """
    require(type(payload) is bytes and 0 < len(payload) <= 65536, 'Bounded typed payload required')
    require(type(address) is int and address > 0 and 0 < timeout_ms <= 30000, 'Invalid remote call')
    require(label and all(c.isalnum() or c in '-_' for c in label), 'Invalid call label')
    run = Path(run)
    save_new(run / (label + '-intent.json'), dict(address=address, input_sha256=hashlib.sha256(payload).hexdigest(),
        size=len(payload), automatic_retry=False, created=time.time()))
    allocation = thread = None
    completed = False
    attempted = False
    creation_failed = False
    tid = W.DWORD()
    result = dict(completed=False, may_have_started=False, retained_buffer=False)
    fault = None
    try:
        debugged = W.BOOL()
        require(api.k.CheckRemoteDebuggerPresent(api.handle, C.byref(debugged)) and not debugged.value,
                'Do not execute target code while debugger is attached')
        allocation = api.k.VirtualAllocEx(api.handle, None, len(payload), 0x3000, 4)
        require(allocation, 'Cannot allocate call buffer')
        value = C.create_string_buffer(payload)
        written = C.c_size_t()
        require(api.k.WriteProcessMemory(api.handle, allocation, value, len(payload), C.byref(written))
                and written.value == len(payload), 'Cannot write complete call buffer')
        # Persist buffer/address before crossing the OS thread-creation boundary.
        save_new(run / (label + '-buffer.json'), dict(address=allocation, size=len(payload)))
        attempted = True
        thread = api.k.CreateRemoteThread(api.handle, None, 0, address, allocation, 0, C.byref(tid))
        creation_failed = not thread
        require(thread, 'Cannot create control thread')
        require(api.k.WaitForSingleObject(thread, timeout_ms) == 0,
                'Control call unresolved; retain its buffer and do not replay')
        completed = True
        code = W.DWORD()
        require(api.k.GetExitCodeThread(thread, C.byref(code)), 'Cannot read control exit code')
        response = api.reader.memory.read(allocation, len(payload))
        require(len(response) == len(payload), 'Incomplete call response')
        with (run / (label + '-response.bin')).open('xb') as stream:
            stream.write(response)
            stream.flush()
            os.fsync(stream.fileno())
        result.update(exit=code.value, output_sha256=hashlib.sha256(response).hexdigest())
    except BaseException as exc:
        fault = exc
        result['error'] = repr(exc)
    finally:
        result.update(completed=completed, may_have_started=attempted and not creation_failed,
                      thread_id=tid.value)
        # Resource/log failures cannot replace an unresolved-call classification.
        try:
            if thread and not api.k.CloseHandle(thread):
                result['thread_handle_close_error'] = C.get_last_error()
        except BaseException as exc:
            result['thread_handle_close_exception'] = repr(exc)
            if fault is None: fault = exc
        release = completed or not attempted or creation_failed
        if allocation:
            if release:
                try:
                    if not api.k.VirtualFreeEx(api.handle, allocation, 0, 0x8000):
                        result['buffer_release_error'] = C.get_last_error()
                except BaseException as exc:
                    result['buffer_release_exception'] = repr(exc)
                    if fault is None: fault = exc
            else:
                result.update(retained_buffer=True, buffer=allocation)
        try:
            save_new(run / (label + '-result.json'), result)
        except BaseException as exc:
            result['result_log_error'] = repr(exc)
            if fault is None: fault = exc
    if result['may_have_started'] and not completed:
        raise RemoteCallUnknown(str(fault or 'Control call unresolved'), result) from fault
    if fault:
        if result['may_have_started'] and not completed:
            raise RemoteCallUnknown(str(fault), result) from fault
        raise fault
    require(not result.get('thread_handle_close_error') and not result.get('buffer_release_error'),
            'Control call resource cleanup failed; inspect record before proceeding')
    return result['exit'], response
