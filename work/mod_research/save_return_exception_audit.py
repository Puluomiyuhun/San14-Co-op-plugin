"""Offline-only exception-source audit; no game access or observer modification."""
from pathlib import Path
from bisect import bisect_right
from datetime import datetime
import hashlib, json, struct, sys

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import disasm_chained as d

EXPECTED = "5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268"
BASE = 0x7ff749440000
assert hashlib.sha256(d.image).hexdigest() == EXPECTED
u16 = lambda at: struct.unpack_from("<H", d.image, at)[0]
u32 = lambda at: struct.unpack_from("<I", d.image, at)[0]
u64 = lambda at: struct.unpack_from("<Q", d.image, at)[0]

def cstring(at):
    if not 0 <= at < len(d.image):
        return None
    end = d.image.find(b"\0", at, min(at + 256, len(d.image)))
    if end < 0:
        return None
    return d.image[at:end].decode("ascii", errors="backslashreplace")

def import_slots():
    # Captured image intentionally omitted its PE header; parse the local file.
    raw = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Romance_of_the_Three_Kingdoms_14\SAN14PK_SC.exe").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025"
    read16 = lambda at: struct.unpack_from("<H", raw, at)[0]
    read32 = lambda at: struct.unpack_from("<I", raw, at)[0]
    pe = read32(0x3c)
    assert raw[pe:pe+4] == b"PE\0\0"
    optional = pe + 24
    assert read16(optional) == 0x20b
    section_table = optional + read16(pe+20)
    mapped = bytearray(read32(optional+56))
    header_size = read32(optional+60)
    mapped[:header_size] = raw[:header_size]
    for n in range(read16(pe+6)):
        at = section_table + n*40
        _, virtual_address, raw_size, raw_offset = struct.unpack_from("<IIII", raw, at+8)
        mapped[virtual_address:virtual_address+raw_size] = raw[raw_offset:raw_offset+raw_size]
    r32 = lambda at: struct.unpack_from("<I", mapped, at)[0]
    r64 = lambda at: struct.unpack_from("<Q", mapped, at)[0]
    def name_at(at):
        end = mapped.find(b"\0", at, at+256)
        assert end >= 0
        return mapped[at:end].decode("ascii")
    start = r32(optional + 112 + 8)
    rows = {}
    for off in range(start, start + 20 * 1024, 20):
        original, _, _, name, first = struct.unpack_from("<IIIII", mapped, off)
        if not any((original, name, first)):
            break
        assert original and first
        dll = name_at(name)
        for n in range(65536):
            thunk = r64(original + 8 * n)
            if not thunk:
                break
            symbol = f"ordinal:{thunk & 0xffff}" if thunk >> 63 else name_at(thunk + 2)
            rows[first + 8 * n] = {"dll": dll, "symbol": symbol}
    return rows

imports = import_slots()
assert imports[0x123c2e0]["symbol"] == "RaiseException"
literal_rows = []
at = 0
while True:
    at = d.image.find(struct.pack("<I", 0x406d1388), at)
    if at < 0:
        break
    entry = d.entries[bisect_right(d.starts, at)-1]
    if entry[0] <= at < entry[1]:
        root = d.primary(entry)
        instructions = []
        for a, z, _ in sorted(set(d.groups[root] + [root])):
            for ins in d.decoder.disasm(d.image[a:z], a):
                if ins.address <= at < ins.address + ins.size:
                    instructions.append({"rva": hex(ins.address), "asm": ins.mnemonic + " " + ins.op_str})
        unwind = root[2]
        flags = d.image[unwind] >> 3
        n = d.image[unwind+2]
        tail = unwind + 4 + ((n+1) & ~1) * 2
        literal_rows.append({
            "literal_rva": hex(at), "function_rva": hex(root[0]),
            "instructions": instructions, "unwind_rva": hex(unwind),
            "unwind_flags": flags,
            "handler_rva": hex(u32(tail)) if flags & 3 else None,
            "handler_data_first_100_bytes": d.image[tail+4:tail+104].hex() if flags & 3 else None,
        })
    at += 1

table = []
for i in range(3):
    ptr = u64(0x1922af8 + i * 8)
    table.append({"index": i, "pointer": hex(ptr), "rva": hex(ptr-BASE), "string": cstring(ptr-BASE)})

trace_path = P / "save_return_observer_live/20261006-194514-137991/trace.jsonl"
lines = trace_path.read_text(encoding="utf-8").splitlines()
rows = [json.loads(line) for line in lines]
exceptions = []
callbacks = []
for index, row in enumerate(rows):
    if row.get("event") == "other_exception":
        def compact(item):
            return {key: item[key] for key in ("event", "tick", "code", "first_chance", "thread", "callback", "boundary", "call_id") if key in item}
        exceptions.append({"line": index+1, "event": row,
                           "prior_events": [compact(x) for x in rows[max(0,index-2):index]],
                           "next_events": [compact(x) for x in rows[index+1:index+3]]})
    if row.get("event") == "callback":
        item = {key: row[key] for key in ("event", "boundary", "thread", "call_id", "callback", "return_address", "entry_rsp", "rax", "tick") if key in row}
        item["return_address_rva"] = hex(int(row["return_address"],16)-BASE)
        callbacks.append(item)

result = {
    "schema": "san14.save-return-exception-static-audit.v1",
    "scope": "offline captured image and historical trace only; no live access",
    "runtime_image_sha256": EXPECTED,
    "trace_sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
    "raise_exception_iat": {"rva": "0x123c2e0", **imports[0x123c2e0]},
    "exception_code": {"decimal": 1080890248, "hex": hex(1080890248)},
    "literal_sites": literal_rows,
    "literal_names": [{"rva":hex(x), "string":cstring(x)} for x in (0x1391940, 0x15650d8, 0x15657b8)],
    "thread_name_table_1922af8_first_three": table,
    "name_pointer_1925210": {"pointer":hex(u64(0x1925210)), "string":cstring(u64(0x1925210)-BASE)},
    "exceptions": exceptions,
    "callback_records": callbacks,
    "frozen_run_status": "INCOMPLETE (unchanged)",
    "limit": "The live exception records omit thread, address, flags and arguments; static emitters cannot uniquely attribute those two events.",
}
out = P / ("save_return_exception_static_" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json")
with out.open("x", encoding="utf-8") as file:
    json.dump(result, file, indent=2, ensure_ascii=False)
print(out.name)
print(json.dumps({k:result[k] for k in ("raise_exception_iat", "literal_names", "thread_name_table_1922af8_first_three", "name_pointer_1925210", "callback_records")}, ensure_ascii=False, indent=2))
print("callback record keys", sorted({k for row in callbacks for k in row}))
