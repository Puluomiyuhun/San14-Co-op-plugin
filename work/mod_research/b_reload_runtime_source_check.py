"""Read explicit files only; compare cold Bootstrap's six bounded source ranges.

No process, launch, debugger, injection, storage-save or publication API. Disk
bytes are not evidence of bytes available at the running program's PE entry.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

GAME_SHA = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
RUNTIME_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
SPANS = (
    ('InitCall', 0x1447B6, 5, 'c198388cb4ef5d72722d3b962e757cad87f4153f4cb9387612cca5ce0aea4beb'),
    ('Init', 0x509580, 185, 'f72ed230854d8a9451dc4825b54b4885cf04f04e52ac61739e2952409c911a8f'),
    ('Runner', 0x834D10, 357, 'a5cedc660029881dc83d3b0ffe7c1279b383be3512edd2a0e23cf61c8efe6669'),
    ('Thunk', 0x50B730, 106, 'adf3173d8052d92bca07c64fb6e8763fd076ad7bab4fbd6f02ffa68e231b06d0'),
    ('Yield', 0x50B690, 111, 'bb26acbe0d4b82f8ca2a5f18fe4abf1da30f26453ecd16e4d9176bc7aefbc773'),
    ('ThreadEntry', 0x83A930, 253, 'ff1470c31b30f148ee067fab286db3ec778ae0623d369b5f4f23c8ffc55ad49f'),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stable_read(path, expected):
    path = Path(path).resolve(strict=True)
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    require(before.st_size == after.st_size == len(data) and before.st_mtime_ns == after.st_mtime_ns,
            'File changed during read: ' + str(path))
    require(sha(data) == expected, 'Unsupported file identity: ' + str(path))
    return path, data


class PeFile:
    """Minimal strict x64 disk RVA mapper; never maps/loads an executable."""
    def __init__(self, data):
        self.data = data
        require(len(data) >= 0x40 and data[:2] == b'MZ', 'Missing DOS header')
        pe = struct.unpack_from('<I', data, 0x3c)[0]
        require(0x40 <= pe <= len(data) - 24 and data[pe:pe+4] == b'PE\0\0', 'Invalid PE header')
        machine, count, _, _, _, optional_size, _ = struct.unpack_from('<HHIIIHH', data, pe+4)
        optional = pe + 24
        require(machine == 0x8664 and 0 < count <= 96 and optional_size >= 240
                and optional + optional_size + count*40 <= len(data), 'Invalid x64 optional/section headers')
        require(struct.unpack_from('<H', data, optional)[0] == 0x20b, 'PE32+ required')
        self.entry = struct.unpack_from('<I', data, optional+16)[0]
        self.image_base = struct.unpack_from('<Q', data, optional+24)[0]
        self.image_size = struct.unpack_from('<I', data, optional+56)[0]
        require(0 < self.entry < self.image_size, 'Entry outside image')
        self.sections = []
        for i in range(count):
            at = optional + optional_size + 40*i
            vs, rva, raw_size, raw = struct.unpack_from('<IIII', data, at+8)
            flags = struct.unpack_from('<I', data, at+36)[0]
            require(rva <= self.image_size and max(vs, raw_size) <= self.image_size-rva
                    and raw <= len(data) and raw_size <= len(data)-raw, 'Section range overflow')
            self.sections.append((rva, max(vs, raw_size), raw, raw_size, flags))
        directories = struct.unpack_from('<I', data, optional+108)[0]
        self.relocations = []
        if directories > 5:
            rva, size = struct.unpack_from('<II', data, optional+112+5*8)
            require(bool(rva) == bool(size), 'Partial relocation directory')
            if size:
                raw = self.read(rva, size)[0]
                at = 0
                while at < size:
                    require(size-at >= 8, 'Truncated relocation block')
                    page, length = struct.unpack_from('<II', raw, at)
                    require(length >= 8 and length % 2 == 0 and length <= size-at, 'Invalid relocation block')
                    for pos in range(at+8, at+length, 2):
                        entry = struct.unpack_from('<H', raw, pos)[0]
                        kind, offset = entry >> 12, entry & 0xfff
                        if kind:
                            require(kind == 10, 'Unexpected non-DIR64 relocation')
                            self.relocations.append((page+offset, 8))
                    at += length

    def read(self, rva, size):
        require(size > 0 and 0 <= rva < self.image_size and size <= self.image_size-rva, 'RVA overflow')
        ranges = [s for s in self.sections if s[0] <= rva and rva+size <= s[0]+s[1]]
        require(len(ranges) == 1, 'RVA outside unique section')
        start, _, offset, raw_size, flags = ranges[0]
        relative = rva-start
        require(relative+size <= raw_size, 'RVA range has no disk bytes')
        at = offset+relative
        return self.data[at:at+size], at, flags


def inspect(disk, runtime):
    disk_path, disk_data = stable_read(disk, GAME_SHA)
    runtime_path, runtime_data = stable_read(runtime, RUNTIME_SHA)
    pe = PeFile(disk_data)
    rows = []
    for name, rva, size, expected in SPANS:
        actual = runtime_data[rva:rva+size]
        require(len(actual) == size and sha(actual) == expected, 'Runtime span differs: ' + name)
        raw, offset, flags = pe.read(rva, size)
        relocations = [a for a, n in pe.relocations if a < rva+size and rva < a+n]
        rows.append(dict(name=name, rva=rva, size=size, file_offset=offset,
                         runtime_sha256=expected, disk_sha256=sha(raw), equal=raw == actual,
                         different_bytes=sum(a != b for a, b in zip(raw, actual)),
                         section_executable=bool(flags & 0x20000000),
                         intersecting_dir64_relocations=relocations))
    require(sha(disk_path.read_bytes()) == GAME_SHA and sha(runtime_path.read_bytes()) == RUNTIME_SHA,
            'Input changed before comparison completed')
    return dict(result='PASS_FILE_COMPARISON', disk_sha256=GAME_SHA, runtime_sha256=RUNTIME_SHA,
                disk_path=str(disk_path), runtime_path=str(runtime_path), rows=rows,
                same_ranges=sum(r['equal'] for r in rows), differing_ranges=sum(not r['equal'] for r in rows),
                disk_entry_rva=pe.entry, preferred_image_base=pe.image_base,
                exe_disk_read=True, game_process_access=False, steam_save_access=False,
                pe_entry_availability='UNOBSERVED', producer_exclusion='UNPROVEN',
                install_authorized=False, sources_unchanged=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disk-pe', type=Path, required=True)
    parser.add_argument('--runtime-image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.disk_pe, args.runtime_image)
    result['source_sha256'] = sha(Path(__file__).read_bytes())
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(result, out, indent=2)
        out.write('\n')
    print(json.dumps(dict(result=result['result'], differing_ranges=result['differing_ranges'],
                         same_ranges=result['same_ranges'], output=str(args.output))))


if __name__ == '__main__':
    main()
