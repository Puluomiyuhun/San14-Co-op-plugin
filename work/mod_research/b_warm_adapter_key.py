"""Local-only independent adapter keys; never a room join-token endpoint.

CLI output contains only public fingerprints. Windows files created by this
module have a protected DACL granting full access only to the current token user.
Explicit import accepts transferred bytes; normal loading verifies the private ACL.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import secrets

HEADER = b'SAN14-LOCAL-ADAPTER-KEY-V1\n'
SIZE = len(HEADER) + 65
DOMAIN = b'san14.adapter-key-fingerprint.v1\0'


class KeyFileError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise KeyFileError(message)


def encode(key):
    need(type(key) is bytes and len(key) == 32 and any(key), 'Key must be 32 nonzero bytes')
    return HEADER + key.hex().encode('ascii') + b'\n'


def decode(raw):
    need(type(raw) is bytes and len(raw) == SIZE and raw.startswith(HEADER) and raw.endswith(b'\n'),
         'Invalid key file format')
    text = raw[len(HEADER):-1]
    need(all(c in b'0123456789abcdef' for c in text), 'Invalid key file encoding')
    key = bytes.fromhex(text.decode('ascii'))
    need(any(key) and encode(key) == raw, 'Invalid key file value')
    return key


def public(key):
    encode(key)
    return dict(schema='san14.local-adapter-key.v1', fingerprint=hashlib.sha256(DOMAIN + key).hexdigest(),
                secret_disclosed=False, native_permission=False)


class SA(C.Structure):
    _fields_ = [('length', W.DWORD), ('descriptor', C.c_void_p), ('inherit', W.BOOL)]


class ACLINFO(C.Structure):
    _fields_ = [('count', W.DWORD), ('used', W.DWORD), ('free', W.DWORD)]


class Native:
    def __init__(self):
        need(os.name == 'nt', 'Windows private key files required')
        self.k = C.WinDLL('kernel32', use_last_error=True)
        self.a = C.WinDLL('advapi32', use_last_error=True)
        for dll, name, args, result in [
            (self.k, 'GetCurrentProcess', [], W.HANDLE),
            (self.k, 'CloseHandle', [W.HANDLE], W.BOOL),
            (self.k, 'LocalFree', [C.c_void_p], C.c_void_p),
            (self.k, 'CreateFileW', [W.LPCWSTR,W.DWORD,W.DWORD,C.POINTER(SA),W.DWORD,W.DWORD,W.HANDLE], W.HANDLE),
            (self.k, 'ReadFile', [W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.c_void_p], W.BOOL),
            (self.k, 'WriteFile', [W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.c_void_p], W.BOOL),
            (self.k, 'FlushFileBuffers', [W.HANDLE], W.BOOL),
            (self.k, 'GetFileInformationByHandle', [W.HANDLE,C.c_void_p], W.BOOL),
            (self.k, 'GetVolumeInformationW', [W.LPCWSTR,W.LPWSTR,W.DWORD,C.c_void_p,C.c_void_p,C.POINTER(W.DWORD),W.LPWSTR,W.DWORD],W.BOOL),
            (self.a, 'OpenProcessToken', [W.HANDLE,W.DWORD,C.POINTER(W.HANDLE)],W.BOOL),
            (self.a, 'GetTokenInformation', [W.HANDLE,W.DWORD,C.c_void_p,W.DWORD,C.POINTER(W.DWORD)],W.BOOL),
            (self.a, 'ConvertSidToStringSidW', [C.c_void_p,C.POINTER(C.c_void_p)],W.BOOL),
            (self.a, 'ConvertStringSecurityDescriptorToSecurityDescriptorW', [W.LPCWSTR,W.DWORD,C.POINTER(C.c_void_p),C.c_void_p],W.BOOL),
            (self.a, 'GetSecurityInfo', [W.HANDLE,W.DWORD,W.DWORD,C.POINTER(C.c_void_p),C.c_void_p,C.POINTER(C.c_void_p),C.c_void_p,C.POINTER(C.c_void_p)],W.DWORD),
            (self.a, 'GetSecurityDescriptorControl', [C.c_void_p,C.POINTER(W.WORD),C.POINTER(W.DWORD)],W.BOOL),
            (self.a, 'GetAclInformation', [C.c_void_p,C.c_void_p,W.DWORD,W.DWORD],W.BOOL),
            (self.a, 'GetAce', [C.c_void_p,W.DWORD,C.POINTER(C.c_void_p)],W.BOOL),
        ]:
            f = getattr(dll, name); f.argtypes = args; f.restype = result
        token = W.HANDLE(); count = W.DWORD()
        self.check(self.a.OpenProcessToken(self.k.GetCurrentProcess(), 8, C.byref(token)))
        try:
            self.a.GetTokenInformation(token, 1, None, 0, C.byref(count))
            raw = C.create_string_buffer(count.value)
            self.check(self.a.GetTokenInformation(token, 1, raw, count, C.byref(count)))
            self.sid = self.sid_text(C.c_void_p.from_buffer(raw).value)
        finally:
            self.k.CloseHandle(token)

    @staticmethod
    def check(value):
        need(bool(value), 'Windows private file operation failed (code %d)' % C.get_last_error())

    def sid_text(self, sid):
        out = C.c_void_p()
        self.check(self.a.ConvertSidToStringSidW(sid, C.byref(out)))
        try:
            return C.wstring_at(out)
        finally:
            self.k.LocalFree(out)

    def path(self, value):
        p = Path(value)
        need(p.is_absolute() and len(p.drive) == 2 and p.drive[1] == ':' and
             ':' not in str(p)[2:] and not str(p).startswith('\\\\') and p.name not in ('', '.', '..'),
             'Explicit local drive file path required')
        need(not any(x in ('.', '..') for x in p.parts), 'Relative path segments refused')
        reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {x+str(n) for x in ('COM','LPT') for n in range(1,10)}
        need(p.name == p.name.rstrip(' .') and p.name.split('.')[0].upper() not in reserved,
             'Ambiguous/device file names refused')
        # No broad ACL changes to an existing directory or its siblings.
        flags = W.DWORD()
        self.check(self.k.GetVolumeInformationW(p.anchor, None, 0, None, None, C.byref(flags), None, 0))
        need(flags.value & 8, 'Volume must support persistent Windows ACLs')
        return str(p)

    def acl(self, handle):
        owner = C.c_void_p(); dacl = C.c_void_p(); descriptor = C.c_void_p()
        need(self.a.GetSecurityInfo(handle, 1, 5, C.byref(owner), None, C.byref(dacl), None,
                                   C.byref(descriptor)) == 0, 'Cannot inspect private ACL')
        try:
            control = W.WORD(); revision = W.DWORD(); info = ACLINFO(); ace = C.c_void_p()
            self.check(self.a.GetSecurityDescriptorControl(descriptor, C.byref(control), C.byref(revision)))
            need(owner.value and self.sid_text(owner) == self.sid and dacl.value and control.value & 0x1000,
                 'Private file owner/protected DACL differs')
            self.check(self.a.GetAclInformation(dacl, C.byref(info), C.sizeof(info), 2))
            need(info.count == 1, 'Private file ACL is broader than current user')
            self.check(self.a.GetAce(dacl, 0, C.byref(ace)))
            head = C.string_at(ace, 8)
            need(head[0] == 0 and head[1] == 0 and int.from_bytes(head[4:8], 'little') == 0x1f01ff and
                 self.sid_text(ace.value + 8) == self.sid, 'Private file ACE differs')
        finally:
            self.k.LocalFree(descriptor)

    def file_check(self, handle):
        # BY_HANDLE_FILE_INFORMATION is 52 bytes; attribute and link count used.
        info = C.create_string_buffer(52)
        self.check(self.k.GetFileInformationByHandle(handle, info))
        raw = info.raw
        need(not int.from_bytes(raw[:4], 'little') & (0x10 | 0x400) and
             int.from_bytes(raw[40:44], 'little') == 1, 'Directory/reparse/hardlinked key refused')

    def write_new(self, path, key):
        raw = encode(key); name = self.path(path); sd = C.c_void_p()
        resolved = Path(name).parent.resolve(strict=True) / Path(name).name
        need(not any((parent / '.git').exists() for parent in resolved.parents),
             'Private key targets inside Git worktrees are refused')
        self.check(self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            'O:'+self.sid+'D:P(A;;FA;;;'+self.sid+')', 1, C.byref(sd), None))
        attributes = SA(C.sizeof(SA), sd, False)
        try:
            handle = self.k.CreateFileW(name, 0x40000000 | 0x20000, 0, C.byref(attributes), 1,
                                        0x80 | 0x200000 | 0x80000000, None)
        finally:
            self.k.LocalFree(sd)
        need(handle not in (None, C.c_void_p(-1).value), 'Key target exists or cannot be created exclusively')
        try:
            self.file_check(handle); self.acl(handle)
            done = W.DWORD(); data = C.create_string_buffer(raw)
            self.check(self.k.WriteFile(handle, data, len(raw), C.byref(done), None))
            need(done.value == len(raw), 'Incomplete private file write; retain failed target')
            self.check(self.k.FlushFileBuffers(handle)); self.acl(handle)
        finally:
            self.k.CloseHandle(handle)

    def read(self, path, *, private):
        handle = self.k.CreateFileW(self.path(path), 0x80000000 | (0x20000 if private else 0),
                                    1, None, 3, 0x80 | 0x200000, None)
        need(handle not in (None, C.c_void_p(-1).value), 'Key file unavailable')
        try:
            self.file_check(handle)
            if private: self.acl(handle)
            buffer = C.create_string_buffer(SIZE + 1); count = W.DWORD()
            self.check(self.k.ReadFile(handle, buffer, len(buffer), C.byref(count), None))
            return decode(buffer.raw[:count.value])
        finally:
            self.k.CloseHandle(handle)


def create(path):
    key = secrets.token_bytes(32)
    Native().write_new(path, key)
    return public(key)


def load_key(path):
    return Native().read(path, private=True)


def status(path):
    return public(load_key(path))


def export_file(source, destination):
    key = load_key(source)
    Native().write_new(destination, key)
    return public(key)


def import_file(source, destination):
    # Explicit trust boundary: transferred source may already have broad ACLs.
    # This does not repair prior exposure or authenticate who sent the file.
    key = Native().read(source, private=False)
    Native().write_new(destination, key)
    return public(key)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local private adapter key files; never prints key material.')
    commands = parser.add_subparsers(dest='operation', required=True)
    for operation in ('create', 'status'):
        commands.add_parser(operation).add_argument('--file', required=True)
    for operation in ('export', 'import'):
        sub = commands.add_parser(operation)
        sub.add_argument('--source', required=True); sub.add_argument('--destination', required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == 'create': answer = create(args.file)
        elif args.operation == 'status': answer = status(args.file)
        elif args.operation == 'export': answer = export_file(args.source, args.destination)
        else: answer = import_file(args.source, args.destination)
        print(json.dumps(dict(ok=True, operation=args.operation, **answer), sort_keys=True))
        return 0
    except (KeyFileError, OSError):
        # Never echo malformed bytes, paths, or exception details to CLI output.
        print(json.dumps(dict(ok=False, operation=args.operation, error='PRIVATE_KEY_OPERATION_REFUSED')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
