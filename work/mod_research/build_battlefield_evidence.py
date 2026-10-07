"""Produce checked static evidence. Reads existing files only; does not attach to the game."""
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT = Path("work/mod_research")
OUT = Path("outputs/san14-link")
sys.path.insert(0, str(ROOT / "python_deps"))
import capstone

image = (ROOT / "game-runtime-image.bin").read_bytes()
metadata = json.loads((ROOT / "runtime-203-08-zhanglu.json").read_text(encoding="utf-8"))
decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
decoder.detail = True
anchors = [
    (0x3F8598, "call", "0x1ba2d0"),
    (0x3F85AA, "call", "0x1b5e30"),
    (0x1BA30C, "call", "qword ptr [rax + 0x20]"),
    (0x1B90A8, "movzx", "ebx, word ptr [rax + 0x2a]"),
    (0x1B90C3, "call", "0x1b0400"),
    (0x1B90E1, "call", "0x1b8880"),
    (0x1B88C9, "call", "0x1b8b90"),
    (0x2A9D53, "mov", "byte ptr [rdi + 0x36], al"),
    (0x2A9DA4, "mov", "word ptr [rdi + 0x2a], ax"),
    (0x162197, "call", "0x163c80"),
    (0x163EB0, "mov", "rcx, qword ptr [rdi + 0x148]"),
    (0x163EC8, "call", "0x1b09e0"),
    (0x1B0A33, "call", "qword ptr [rax + 0x10]"),
    (0x1B0A46, "call", "0x20b410"),
    (0x1B0A53, "lea", "rcx, [rsi + 0x8c8]"),
    (0x1B0A9D, "lea", "r8, [rdi + 8]"),
    (0x1B0ABD, "call", "0x15ef40"),
    (0x15EF6A, "movzx", "r8d, word ptr [r8]"),
    (0x15EF81, "mov", "edx, dword ptr [rdi + 4]"),
    (0x15EFB3, "call", "0x160e20"),
    (0x1B0ADC, "call", "0x336bf0"),
    (0x162213, "mov", "rdi, qword ptr [rax + rcx*8 + 0x7df60]"),
    (0x162246, "call", "0x195320"),
    (0x195390, "call", "0x1a8320"),
    (0x3F9355, "call", "0x16c640"),
    (0x16C657, "cmp", "qword ptr [rax + 0x38], 0"),
    (0x16C680, "call", "0x1622f0"),
    (0x16C697, "call", "0x15be80"),
    (0x16C6B9, "call", "0x162180"),
    (0x3F8623, "call", "0x16c2e0"),
    (0x16C47F, "call", "0x164000"),
    (0x16C484, "dec", "dword ptr [rbx + 0x310]"),
    (0x16C4C5, "call", "0x16e500"),
    (0x1BA32E, "call", "0x20fc40"),
]
checked = []
for rva, mnemonic, operands in anchors:
    ins = next(decoder.disasm(image[rva:rva+16], rva, count=1))
    assert (ins.mnemonic, ins.op_str) == (mnemonic, operands), (hex(rva), ins.mnemonic, ins.op_str)
    checked.append({"rva": hex(rva), "bytes": ins.bytes.hex(), "instruction": mnemonic + " " + operands})

# Verify RIP-relative LEAs to known type vtables, not mere nearby strings.
type_references = []
for rva, expected in [(0x15FAE8, 0x128F960), (0x1A83CD, 0x1298F28)]:
    ins = next(decoder.disasm(image[rva:rva+16], rva, count=1))
    assert ins.mnemonic == "lea"
    operand = ins.operands[1]
    assert operand.type == capstone.x86.X86_OP_MEM and operand.mem.base == capstone.x86.X86_REG_RIP
    actual = ins.address + ins.size + operand.mem.disp
    assert actual == expected, (hex(rva), hex(actual), hex(expected))
    type_references.append({"rva": hex(rva), "vtable_rva": hex(actual), "bytes": ins.bytes.hex()})

# This region is a jump table after the return, NOT executable instructions.
body = list(decoder.disasm(image[0x3F8E10:0x3F9610], 0x3F8E10))
assert body[-1].mnemonic == "ret" and body[-1].address + body[-1].size == 0x3F9610
starts = {i.address for i in body}
targets = struct.unpack_from("<31I", image, 0x3F9610)
assert all(target in starts and 0x3F923C <= target < 0x3F958F for target in targets)
table = [{"stage_index": n, "entry_rva": hex(target)} for n, target in enumerate(targets)]

evidence = {
    "date": "2026-10-05",
    "scope": "static-disassembly-and-readonly-rtti; no dynamic battle or two-game validation",
    "exe_sha256": "42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025",
    "captured_image_sha256": hashlib.sha256(image).hexdigest(),
    "checked_instruction_anchors": checked,
    "checked_type_references": type_references,
    "progress_stage_table": {"rva": "0x3f9610", "entry_count": 31, "entries": table,
                             "note": "Program stages; not days, frames, or a network tick rate."},
    "readonly_live_type_sample": json.loads((ROOT / "battlefield-runtime-types-live.json").read_text(encoding="utf-8")),
    "candidate_bridges": [
        {"name": "logical-position-to-native-motion", "chain": ["1B9020", "1B0400", "1B8880", "1B8B90"]},
        {"name": "typed-source-target-record-to-native-effect", "chain": ["162180", "163C80", "1B09E0", "15EF40", "160E20", "336BF0"],
         "note": "Branched call relationships, not one serial stack; exact attack coverage unverified."},
        {"name": "unit-number-and-value-to-layout", "chain": ["162180", "195320", "1A8320"]},
        {"name": "progress-waits-for-effects", "chain": ["3F8E10", "16C640", "15FAA0"],
         "parallel_native_update_path": ["3F8140", "16C2E0"]},
    ],
    "limits": [
        "Checked instruction bytes and manually inspected local data flow are not a complete control-flow/call-graph proof.",
        "No claim that CGameState or unit updates are pure rendering.",
        "No proof that callbacks never mutate gameplay or that all battle types use the selected paths.",
        "No network-supplied event replay, gameplay suppression, latency or animation-fidelity measurement performed.",
        "Runtime pointers, linked-list internals and resource handles are process-local, not transportable.",
    ],
}
destination = OUT / "战场动画同步静态证据.json"
destination.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"output": str(destination), "instruction_anchors_checked": len(checked),
                  "vtable_references_checked": len(type_references), "stage_entries_checked": len(table),
                  "dynamic_multiplayer_tested": False}, ensure_ascii=False))
