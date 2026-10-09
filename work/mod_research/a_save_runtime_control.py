"""Local A-save coordination primitives. Importing never accesses a process.

An uncertain remote call keeps its input/output buffer alive; its durable intent
must not be replayed. File backups never overwrite originals or prior evidence.
"""
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import shutil
import time


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def inventory(directory):
    directory = Path(directory).resolve(strict=True)
    require(directory.is_dir() and not directory.is_symlink(), 'Save directory is not a real directory')
    result = {}
    for path in sorted(directory.glob('*.s14')):
        require(path.is_file() and not path.is_symlink(), 'Non-file save entry')
        before = path.stat()
        digest = sha(path)
        after = path.stat()
        require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                'Save changed while hashing: ' + path.name)
        result[path.name] = dict(size=after.st_size, sha256=digest)
    require(result, 'No original saves found')
    return result


def backup_saves(directory, destination):
    """Fresh complete backup, then compare the original inventory again."""
    source = Path(directory).resolve(strict=True)
    dest = Path(destination).resolve()
    require(dest != source and not dest.is_relative_to(source), 'Backup must be outside save directory')
    before = inventory(source)
    dest.mkdir(parents=True, exist_ok=False)
    for name, expected in before.items():
        with (source / name).open('rb') as inp, (dest / name).open('xb') as out:
            shutil.copyfileobj(inp, out)
            out.flush()
            os.fsync(out.fileno())
        require((dest / name).stat().st_size == expected['size'] and sha(dest / name) == expected['sha256'],
                'Backup identity mismatch: ' + name)
    require(inventory(source) == before, 'Original saves changed during backup')
    save_new(dest / 'manifest.json', before)
    return before


def compare_saves(before, after, new_name, new_hash=None):
    missing = sorted(set(before) - set(after))
    changed = sorted(name for name in before if name in after and before[name] != after[name])
    added = sorted(set(after) - set(before))
    result = dict(missing=missing, changed=changed, added=added,
                  originals_unchanged=not missing and not changed)
    result['only_expected_new_file'] = added == [new_name]
    result['new_hash_matches'] = bool(new_hash and after.get(new_name, {}).get('sha256') == new_hash)
    return result


class RemoteCallUnknown(RuntimeError):
    def __init__(self, message, record):
        super().__init__(message)
        self.record = record


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
        if thread and not api.k.CloseHandle(thread):
            result['thread_handle_close_error'] = C.get_last_error()
        release = completed or not attempted or creation_failed
        if allocation:
            if release:
                if not api.k.VirtualFreeEx(api.handle, allocation, 0, 0x8000):
                    result['buffer_release_error'] = C.get_last_error()
            else:
                result.update(retained_buffer=True, buffer=allocation)
        save_new(run / (label + '-result.json'), result)
    if fault:
        if result['may_have_started'] and not completed:
            raise RemoteCallUnknown(str(fault), result) from fault
        raise fault
    require(not result.get('thread_handle_close_error') and not result.get('buffer_release_error'),
            'Control call resource cleanup failed; inspect record before proceeding')
    return result['exit'], response
