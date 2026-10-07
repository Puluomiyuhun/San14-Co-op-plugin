"""Read-only SAN14PK_SC memory diagnostics. No game field is certified yet."""
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
from pathlib import Path
import struct
import sys

EXPECTED_NAME = "san14pk_sc.exe"
OLD_CANDIDATES = [0x19E6644, 0x19E68E0, 0x1A19500, 0x19E6350,
                  0x1FC91D0, 0x1A1E6B0, 0x18EA620]


def find_game_pid():
    if sys.platform != "win32" or C.sizeof(C.c_void_p) != 8:
        raise RuntimeError("Requires 64-bit Python on Windows")
    class Entry(C.Structure):
        _fields_ = [("dwSize", W.DWORD), ("cntUsage", W.DWORD),
                    ("th32ProcessID", W.DWORD), ("th32DefaultHeapID", C.c_size_t),
                    ("th32ModuleID", W.DWORD), ("cntThreads", W.DWORD),
                    ("th32ParentProcessID", W.DWORD), ("pcPriClassBase", W.LONG),
                    ("dwFlags", W.DWORD), ("szExeFile", W.WCHAR * 260)]
    kernel = C.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = W.HANDLE
    for name in ("Process32FirstW", "Process32NextW"):
        function = getattr(kernel, name)
        function.argtypes = [W.HANDLE, C.POINTER(Entry)]
        function.restype = W.BOOL
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.CloseHandle.restype = W.BOOL
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == C.c_void_p(-1).value:
        raise C.WinError(C.get_last_error())
    matches = []
    try:
        entry = Entry()
        entry.dwSize = C.sizeof(entry)
        ok = kernel.Process32FirstW(snapshot, C.byref(entry))
        while ok:
            if entry.szExeFile.lower() == EXPECTED_NAME:
                matches.append(entry.th32ProcessID)
            ok = kernel.Process32NextW(snapshot, C.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one running SAN14PK_SC.exe, found {len(matches)}")
    return matches[0]


class Memory:
    def __init__(self, pid):
        if sys.platform != "win32" or C.sizeof(C.c_void_p) != 8:
            raise RuntimeError("Requires 64-bit Python on Windows")
        self.k = C.WinDLL("kernel32", use_last_error=True)
        self.p = C.WinDLL("psapi", use_last_error=True)
        self.k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
        self.k.OpenProcess.restype = W.HANDLE
        self.k.CloseHandle.argtypes = [W.HANDLE]
        self.k.CloseHandle.restype = W.BOOL
        self.k.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)]
        self.k.QueryFullProcessImageNameW.restype = W.BOOL
        self.k.ReadProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
        self.k.ReadProcessMemory.restype = W.BOOL
        self.p.EnumProcessModulesEx.argtypes = [W.HANDLE, C.POINTER(C.c_void_p), W.DWORD, C.POINTER(W.DWORD), W.DWORD]
        self.p.EnumProcessModulesEx.restype = W.BOOL
        # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ. No write/operation rights.
        self.handle = self.k.OpenProcess(0x0400 | 0x0010, False, pid)
        if not self.handle:
            raise C.WinError(C.get_last_error())
        try:
            name = C.create_unicode_buffer(32768)
            size = W.DWORD(len(name))
            if not self.k.QueryFullProcessImageNameW(self.handle, 0, name, C.byref(size)):
                raise C.WinError(C.get_last_error())
            self.path = Path(name.value)
            if self.path.name.lower() != EXPECTED_NAME:
                raise RuntimeError("Refusing to inspect a process other than SAN14PK_SC.exe")
            modules = (C.c_void_p * 2048)()
            needed = W.DWORD()
            if not self.p.EnumProcessModulesEx(self.handle, modules, C.sizeof(modules), C.byref(needed), 3):
                raise C.WinError(C.get_last_error())
            if needed.value == 0 or not modules[0]:
                raise RuntimeError("No main module returned")
            self.base = modules[0]
            header = self.read(self.base, 4096)
            pe = struct.unpack_from("<I", header, 60)[0]
            if header[:2] != b"MZ" or header[pe:pe+4] != b"PE\0\0":
                raise RuntimeError("Main module is not a PE image")
            self.image_size = struct.unpack_from("<I", header, pe + 24 + 56)[0]
            self.sections = []
            count = struct.unpack_from("<H", header, pe + 6)[0]
            optional_size = struct.unpack_from("<H", header, pe + 20)[0]
            for i in range(count):
                at = pe + 24 + optional_size + 40 * i
                name, size, rva = struct.unpack_from("<8sII", header, at)
                self.sections.append(dict(name=name.rstrip(b"\0").decode("ascii", errors="replace"),
                                          rva=rva, size=size))
        except Exception:
            self.close()
            raise

    def read(self, address, length):
        if not 0 < length <= 4 * 1024 * 1024:
            raise ValueError("Read size must be 1..4 MiB")
        data = C.create_string_buffer(length)
        received = C.c_size_t()
        if not self.k.ReadProcessMemory(self.handle, address, data, length, C.byref(received)):
            raise C.WinError(C.get_last_error())
        if received.value != length:
            raise RuntimeError("Short process-memory read")
        return data.raw

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None

    def inspect(self, rva):
        result = {"rva": hex(rva), "verified_field": False}
        if not 0 <= rva <= self.image_size - 64:
            result["error"] = "candidate outside main module"
            return result
        try:
            data = self.read(self.base + rva, 64)
            result["bytes"] = data.hex(" ")
            result["u16"] = list(struct.unpack("<32H", data))
            ptr = struct.unpack_from("<Q", data)[0]
            result["first_qword"] = hex(ptr)
            if 0x10000 <= ptr < 0x7FFFFFFFFFFF:
                try:
                    result["pointer_target_64_bytes"] = self.read(ptr, 64).hex(" ")
                except OSError:
                    result["pointer_target_readable"] = False
        except OSError as error:
            result["error"] = str(error)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--rva", action="append", type=lambda x: int(x, 0))
    args = parser.parse_args()
    memory = Memory(args.pid)
    try:
        report = dict(mode="read-only", process=memory.path.name, pid=args.pid,
                      image_base=hex(memory.base), image_size=memory.image_size,
                      exe_sha256=hashlib.sha256(memory.path.read_bytes()).hexdigest(),
                      sections=memory.sections, game_fields_verified=False,
                      candidates=[memory.inspect(rva) for rva in (args.rva or OLD_CANDIDATES)])
        text = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(f"Read-only diagnostic saved to {args.output}")
        else:
            print(text)
    finally:
        memory.close()


if __name__ == "__main__":
    main()
