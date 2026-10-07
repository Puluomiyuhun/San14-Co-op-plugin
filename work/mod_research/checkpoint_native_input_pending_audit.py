"""Inspect fixed workspace archive regions only; no live process or game paths."""
from pathlib import Path
import hashlib, json, sys
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P / "python_deps"))
import capstone
image = (P / "game-runtime-image.bin").read_bytes()
sha = hashlib.sha256(image).hexdigest()
assert sha == "5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268"
d = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64); d.detail = True
def exact(at, wanted):
    i = next(d.disasm(image[at:at+15], at))
    assert i.mnemonic + " " + i.op_str == wanted, (hex(at), i.op_str)
    return {"rva": hex(at), "bytes": i.bytes.hex(), "instruction": wanted}
checks = [
    exact(0x3F9B06, "mov rsi, rcx"),
    exact(0x3F9B23, "mov eax, dword ptr [rsi + 0x470]"),
    exact(0x3F9DAF, "mov rax, qword ptr [rsi + 0x478]"),
    exact(0x3F9DB6, "or r14d, 0xffffffff"),
    exact(0x3F9DBD, "je 0x3f9dd0"),
    exact(0x3F9DBF, "mov r14d, dword ptr [rax + 0x88]"),
    exact(0x3F9DC6, "mov dword ptr [rax + 0x88], 0xffffffff"),
    exact(0x3F9F96, "mov rax, qword ptr [rax + 0x480]"),
    exact(0x3F9F9D, "cmp dword ptr [rax + 0x1b0], 1"),
    exact(0x3F9FA6, "cmp dword ptr [rbx + 0x47c], ebp"),
    exact(0x3FA094, "mov edx, r14d"),
    exact(0x3FA09A, "call 0x3fc270"),
]
a, z = 0x3F9DAF, 0x3F9DD0
body = image[a:z]
instructions = list(d.disasm(body, a))
assert sum(i.size for i in instructions) == len(body) == 33
for i in instructions:
    assert i.mnemonic != "call"
    for o in i.operands:
        if o.type == capstone.x86.X86_OP_MEM:
            assert o.mem.base != capstone.x86.X86_REG_RIP
        if i.group(capstone.CS_GRP_JUMP):
            assert o.type == capstone.x86.X86_OP_IMM and a <= o.imm <= z
# Fixture envelope only: save RSI/R14; set RSI from argument RCX; execute the
# exact native read-and-clear block; return the fetched R14D; restore registers.
prefix = bytes.fromhex("56 41 56 48 8b f1")
suffix = bytes.fromhex("41 8b c6 41 5e 5e c3")
fixture = prefix + body + suffix
out = {
    "schema": "checkpoint-native-input-pending-audit/v1", "image_sha256": sha,
    "real_game_accessed": False, "anchors": checks,
    "observation_site": "0x3f9daf BEFORE mov rax,[rsi+478]",
    "entry_is_only_prescreen": "0x3f9b00 precedes UI callbacks and cannot prove no new request before 3f9dbf.",
    "fragment": {"start": hex(a), "end_exclusive": hex(z), "bytes": body.hex(),
                 "sha256": hashlib.sha256(body).hexdigest(), "length": len(body),
                 "writes": "Original 3F9DC6 clears toolbar+88 after loading into R14D; the admission adapter itself must never perform this write.",
                 "fixture_wrapper_hex": fixture.hex(), "fixture_wrapper_sha256": hashlib.sha256(fixture).hexdigest()},
    "load_authorization_evidence": [
        "checkpoint_load_mode_pilot.cpp queueOnce: empty queue then nativeQueue creates exact CSaveLoadState push entry (op=0,pointer).",
        "checkpoint_guest_native_session.cpp BindQueuedMenu: binds same User AFTER call/thread/attempt and exact menu identity.",
        "checkpoint_load_input_boundary.cpp: User+470, toolbar+88, Game+474/+478/+47C, panel+1B0, manager stack/queue and cache mode/pending checks."
    ],
    "menu_id_assumed_for_load": False,
    "native_hook_installed": False, "all_pending_sources_covered": False,
    "hook_requirements": ["RSI must be bound User at 3F9DAF; preserve live volatile/nonvolatile registers, flags, stack alignment and unwind metadata.",
                          "Do not skip the original update/pump when admission is rejected.",
                          "Before/after snapshots are observations, not an all-thread mutation lock; real owner-thread fence and input hold still required."]
}
(P / "checkpoint_native_input_pending_audit.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
header = "#pragma once\n#include <array>\n#include <cstdint>\nnamespace checkpoint_native_input_pending {\n"
header += "// Fixture-only envelope around exact archive read-and-clear block; never an installed trampoline.\n"
header += f"inline constexpr std::array<std::uint8_t, {len(fixture)}> kArchivedFetchFixture = {{\n"
header += "  " + ",".join(f"0x{x:02x}" for x in fixture) + "\n};\n}\n"
(P / "checkpoint_native_input_pending_archived.h").write_text(header, encoding="utf-8")
print(json.dumps({"anchors": len(checks), "native_fragment_bytes": len(body), "wrapper_bytes": len(fixture), "native_hook_installed": False}))
