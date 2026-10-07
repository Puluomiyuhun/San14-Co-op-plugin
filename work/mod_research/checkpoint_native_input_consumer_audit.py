"""Bounded archive-only audit; never imports game/process/device helpers."""
from pathlib import Path
import hashlib
import json
import sys

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P / "python_deps"))
import capstone

EXPECTED_IMAGE = "5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268"
image = (P / "game-runtime-image.bin").read_bytes()
assert hashlib.sha256(image).hexdigest() == EXPECTED_IMAGE
decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
decoder.detail = True

start, end = 0x3A2920, 0x3A2945
code = image[start:end]
instructions = list(decoder.disasm(code, start))
assert sum(i.size for i in instructions) == len(code)
assert len(code) == 37 and instructions[-1].mnemonic == "ret"
for instruction in instructions:
    assert instruction.mnemonic != "call"
    for operand in instruction.operands:
        if operand.type == capstone.x86.X86_OP_MEM:
            assert operand.mem.base != capstone.x86.X86_REG_RIP
        if instruction.group(capstone.CS_GRP_JUMP):
            assert operand.type == capstone.x86.X86_OP_IMM
            assert start <= operand.imm < end

def region(at, count):
    return [{"rva": hex(i.address), "bytes": i.bytes.hex(),
             "instruction": i.mnemonic + " " + i.op_str}
            for i in decoder.disasm(image[at:at + count], at)]

def exact(at, text):
    instruction = next(decoder.disasm(image[at:at + 15], at))
    assert instruction.mnemonic + " " + instruction.op_str == text, (hex(at), instruction)
    return {"rva": hex(at), "bytes": instruction.bytes.hex(), "instruction": text}

anchors = [
    exact(0x3F9DBF, "mov r14d, dword ptr [rax + 0x88]"),
    exact(0x3F9E04, "lea edx, [rax - 3]"),
    exact(0x3F9E07, "mov rcx, r15"),
    exact(0x3F9E0A, "call 0x3a2920"),
    exact(0x3F9E0F, "test eax, eax"),
    exact(0x3F9EE3, "lea edx, [rax - 3]"),
    exact(0x3F9EE6, "mov rcx, r15"),
    exact(0x3F9EE9, "call 0x3a2920"),
    exact(0x3F9EEE, "test eax, eax"),
    exact(0x3F9EFA, "call 0x3a2da0"),
    exact(0x3F9EFF, "test al, al"),
    exact(0x509BEA, "call 0x3a35d0"),
    exact(0x509BFA, "call 0x3a3210"),
]
output = {
    "schema": "checkpoint-native-input-consumer-audit/v1",
    "scope": "fixed_regions_of_workspace_archived_image_only",
    "image_sha256": EXPECTED_IMAGE,
    "real_game_accessed": False,
    "leaf": {
        "rva": hex(start), "end_exclusive": hex(end), "length": len(code),
        "sha256": hashlib.sha256(code).hexdigest(), "bytes": code.hex(),
        "instructions": region(start, len(code)),
        "external_calls": False, "rip_relative_references": False,
        "abi": "Windows x64: RCX=mouse-cache pointer, EDX=uint32 button index, EAX=uint32 0/1; caller tests EAX, not only AL.",
        "relocatable_fixture_only": True,
    },
    "anchors": anchors,
    "consumer_callsite_contexts": [region(0x3F9DFB, 0x1C), region(0x3F9ED5, 0x2C)],
    "ordering_conclusion": "The bridge can neutralize immediately before this specific leaf reads the mouse button cache. The earlier pending menu read and the later raw modifier query remain outside this boundary.",
    "native_installation_proven": False,
    "global_input_hold_proven": False,
    "blockers": [
        "3F9DBF reads pending menu into R14D before both mouse queries; this query boundary is too late to prove no pending gameplay action.",
        "3F9EFA reaches raw modifier query 3A2DA0 after the second mouse query; cache-only bridge does not cover it.",
        "CRootState conversion order is static; actual owner thread/update-to-consumer lifecycle and hook installation remain unverified.",
        "Mouse-cache direct reads, other query families, raw/providers, queued messages, physical release, and complete native fence remain missing.",
    ],
}
(P / "checkpoint_native_input_consumer_audit.json").write_text(
    json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
header = "#pragma once\n#include <array>\n#include <cstdint>\nnamespace checkpoint_native_input_consumer {\n"
header += f"// Exact archive leaf {start:#x}..{end:#x}; SHA256 {output['leaf']['sha256']}\n"
header += "inline constexpr std::array<std::uint8_t, 37> kArchivedMouseQuery = {\n    "
header += ", ".join(f"0x{b:02x}" for b in code) + "\n};\n}\n"
(P / "checkpoint_native_input_consumer_archived.h").write_text(header, encoding="utf-8")
print(json.dumps({"anchors": len(anchors), "leaf_bytes": len(code),
                  "leaf_sha256": output["leaf"]["sha256"], "native_installation_proven": False}))
