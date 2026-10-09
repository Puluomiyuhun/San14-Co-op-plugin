"""Read the covered Gate's first-failure DATA export, without target execution.

An observation is never a save receipt or a source-restoration permission.
Importing this module does not open a process. The opened handle permits only
query, memory read and wait; no debugger, input, write or remote-thread API.
"""
import ctypes as C
from ctypes import wintypes as W
import hashlib
from pathlib import Path
import struct

from a_save_runtime_control import require

FORMAT = struct.Struct('<II7Q5I')
FIELDS = ('size version stackCount queueCount current top saveState saveGeneration '
          'reservedGeneration saveStatus saveStopped saveError thread stage').split()
EXPORT = b'ASaveCoveredGateFirstFailure'
STAGES = {1: 'frame_or_source_caller', 2: 'source_bytes', 3: 'claim', 4: 'layout'}
READ_RIGHTS = 0x0400 | 0x0010 | 0x00100000


def digest(path):
    path = Path(path).resolve(strict=True)
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
            and after.st_size == len(data), 'Identity file changed during read')
    return hashlib.sha256(data).hexdigest()


def export_layout(path, expected_sha256):
    """Resolve a bounded writable non-executable data export from the pinned PE."""
    import pefile
    require(digest(path) == expected_sha256, 'Diagnostic DLL file identity differs')
    pe = pefile.PE(str(path))
    try:
        require(pe.FILE_HEADER.Machine == 0x8664 and pe.OPTIONAL_HEADER.Magic == 0x20b,
                'Diagnostic DLL must be x64 PE32+')
        symbols = [x for x in pe.DIRECTORY_ENTRY_EXPORT.symbols if x.name == EXPORT]
        require(len(symbols) == 1 and not symbols[0].forwarder, 'Unique DATA export required')
        rva = symbols[0].address
        sections = [s for s in pe.sections if s.VirtualAddress <= rva and
                    rva + FORMAT.size <= s.VirtualAddress + s.Misc_VirtualSize]
        require(len(sections) == 1, 'Diagnostic DATA range lies outside one section')
        flags = sections[0].Characteristics
        require(flags & 0x40000000 and flags & 0x80000000 and not flags & 0x20000000,
                'Diagnostic export is not writable non-executable DATA')
        require(rva % 4 == 0 and rva + FORMAT.size <= pe.OPTIONAL_HEADER.SizeOfImage,
                'Diagnostic DATA alignment/range differs')
        size = pe.OPTIONAL_HEADER.SizeOfHeaders
        require(0 < size <= 65536, 'Unbounded PE headers')
        return dict(rva=rva, size=FORMAT.size, image_size=pe.OPTIONAL_HEADER.SizeOfImage,
                    image_base_offset=pe.OPTIONAL_HEADER.get_field_absolute_offset('ImageBase'),
                    headers=pe.__data__[:size])
    finally:
        pe.close()


def decode_pair(first, second):
    require(len(first) == len(second) == FORMAT.size, 'Incomplete diagnostic read')
    a, b = (dict(zip(FIELDS, FORMAT.unpack(raw))) for raw in (first, second))
    require(all(x['size'] == FORMAT.size and x['version'] == 1 for x in (a, b)),
            'Diagnostic layout/version differs')
    require(a['stage'] in (0, *STAGES) and b['stage'] in (0, *STAGES),
            'Unknown first-failure stage')
    # Stage is published last by the owner. Even identical partially written
    # payloads with stage zero are NOT evidence that no failure occurred.
    if a['stage'] == b['stage'] == 0:
        return dict(status='NOT_PUBLISHED', first_failure=None)
    if first != second:
        return dict(status='UNSTABLE', first_failure=None)
    return dict(status='FIRST_FAILURE_OBSERVED', first_failure=b,
                stage_name=STAGES[b['stage']])


class MemoryPage(C.Structure):
    _fields_ = [('BaseAddress', C.c_void_p), ('AllocationBase', C.c_void_p),
                ('AllocationProtect', W.DWORD), ('PartitionId', W.WORD),
                ('RegionSize', C.c_size_t), ('State', W.DWORD),
                ('Protect', W.DWORD), ('Type', W.DWORD)]


class ReadOnlyProcess:
    def __init__(self, pid):
        require(type(pid) is int and pid > 0 and C.sizeof(C.c_void_p) == 8,
                'Explicit positive PID and 64-bit Python required')
        self.pid, self.handle = pid, None
        self.k = C.WinDLL('kernel32', use_last_error=True)
        bindings = {
            'OpenProcess': ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
            'CloseHandle': ([W.HANDLE], W.BOOL),
            'WaitForSingleObject': ([W.HANDLE, W.DWORD], W.DWORD),
            'GetProcessTimes': ([W.HANDLE] + [C.POINTER(W.FILETIME)] * 4, W.BOOL),
            'QueryFullProcessImageNameW': ([W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)], W.BOOL),
            'K32EnumProcessModulesEx': ([W.HANDLE, C.POINTER(C.c_void_p), W.DWORD, C.POINTER(W.DWORD), W.DWORD], W.BOOL),
            'K32GetModuleFileNameExW': ([W.HANDLE, W.HMODULE, W.LPWSTR, W.DWORD], W.DWORD),
            'ReadProcessMemory': ([W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)], W.BOOL),
            'VirtualQueryEx': ([W.HANDLE, C.c_void_p, C.POINTER(MemoryPage), C.c_size_t], C.c_size_t),
        }
        for name, (args, result) in bindings.items():
            f = getattr(self.k, name)
            f.argtypes, f.restype = args, result
        self.handle = self.k.OpenProcess(READ_RIGHTS, False, pid)
        require(self.handle, 'Cannot open process for read-only diagnosis')

    def close(self):
        if self.handle:
            handle, self.handle = self.handle, None
            require(self.k.CloseHandle(handle), 'Cannot close diagnostic process handle')

    def identity(self):
        require(self.k.WaitForSingleObject(self.handle, 0) == 258, 'Diagnostic process exited')
        times = (W.FILETIME * 4)()
        require(self.k.GetProcessTimes(self.handle, *[C.byref(times[i]) for i in range(4)]),
                'Cannot read process creation time')
        path, count = C.create_unicode_buffer(32768), W.DWORD(32768)
        require(self.k.QueryFullProcessImageNameW(self.handle, 0, path, C.byref(count)),
                'Cannot read process image path')
        return ((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime,
                Path(path.value).resolve(strict=True))

    def modules(self):
        entries, needed = (C.c_void_p * 2048)(), W.DWORD()
        require(self.k.K32EnumProcessModulesEx(self.handle, entries, C.sizeof(entries), C.byref(needed), 3)
                and needed.value <= C.sizeof(entries) and needed.value % 8 == 0,
                'Cannot obtain bounded module inventory')
        modules = []
        for base in entries[:needed.value // 8]:
            path = C.create_unicode_buffer(32768)
            n = self.k.K32GetModuleFileNameExW(self.handle, base, path, len(path))
            require(0 < n < len(path), 'Cannot obtain full module path')
            modules.append((base, Path(path.value).resolve(strict=True)))
        return modules

    def read(self, address, size):
        require(0 < size <= 65536 and 0 < address < (1 << 64) - size, 'Invalid diagnostic read')
        buffer, read = C.create_string_buffer(size), C.c_size_t()
        require(self.k.ReadProcessMemory(self.handle, address, buffer, size, C.byref(read))
                and read.value == size, 'Cannot read complete diagnostic range')
        return buffer.raw

    def data_page(self, address, size, module):
        page = MemoryPage()
        require(self.k.VirtualQueryEx(self.handle, address, C.byref(page), C.sizeof(page)) == C.sizeof(page),
                'Cannot inspect diagnostic page')
        require(page.State == 0x1000 and page.Type == 0x1000000 and page.AllocationBase == module
                and page.Protect in (0x04, 0x08) and address + size <= page.BaseAddress + page.RegionSize,
                'Diagnostic page is not readable DATA in the pinned image')


def observe(pid, birth, image_path, image_sha256, module, dll_path, dll_sha256,
            *, process_factory=ReadOnlyProcess):
    """Two RPM samples, with process and exact module identities on both sides."""
    image_path, dll_path = (Path(p).resolve(strict=True) for p in (image_path, dll_path))
    require(type(birth) is int and birth > 0 and type(module) is int and module > 0,
            'Explicit process birth and loaded module required')
    layout = export_layout(dll_path, dll_sha256)
    require(digest(image_path) == image_sha256, 'Diagnostic process image differs')
    process = process_factory(pid)
    try:
        def check():
            require(process.identity() == (birth, image_path), 'Diagnostic process identity changed')
            require([(b, p) for b, p in process.modules() if b == module or p == dll_path]
                    == [(module, dll_path)], 'Loaded diagnostic module identity changed')
            headers = process.read(module, len(layout['headers']))
            # The Windows loader may update OptionalHeader.ImageBase to the
            # actual mapping. Accept only the exact original or exact rebased
            # header, not arbitrary differences/ignored header bytes.
            rebased = bytearray(layout['headers'])
            struct.pack_into('<Q', rebased, layout['image_base_offset'], module)
            require(headers in (layout['headers'], bytes(rebased)), 'Loaded diagnostic image headers differ')
            process.data_page(module + layout['rva'], layout['size'], module)
        check()
        first = process.read(module + layout['rva'], layout['size'])
        second = process.read(module + layout['rva'], layout['size'])
        check()
        require(digest(dll_path) == dll_sha256 and digest(image_path) == image_sha256,
                'Diagnostic file identities changed during observation')
        result = decode_pair(first, second)
        result.update(pid=pid, birth=birth, module=module, dll_sha256=dll_sha256,
                      image_sha256=image_sha256, export_rva=layout['rva'],
                      raw_samples=[first.hex(), second.hex()], read_only=True,
                      target_calls=0, restore_permission=False, save_accepted=False)
        return result
    finally:
        process.close()
