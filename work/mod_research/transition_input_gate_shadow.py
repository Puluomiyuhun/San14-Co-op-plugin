"""Run archived input functions in Unicorn only; never open a game process.

Functions execute their original bytes. The one environmental stub is the
input singleton accessor 292220. TLS is configured as already initialized.
This proves specific omissions in native cache flush, not a complete gate.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P / "python_deps"))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import (
    UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX,
    UC_X86_REG_RIP, UC_X86_REG_RSP, UC_X86_REG_GS_BASE,
)

BASE = 0x7FF749440000
IMAGE_SHA256 = "5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268"
ARENA = 0x300000000
STOP = ARENA + 0x1000
RAW = ARENA + 0x2000
TEB, TLS_SLOTS, TLS_DATA = ARENA + 0x3000, ARENA + 0x4000, ARENA + 0x5000
CACHE, MOUSE = BASE + 0x1FCA0A0, BASE + 0x19E1D30


def qword(value):
    return struct.pack("<Q", value)


class Shadow:
    def __init__(self, image):
        self.u = Uc(UC_ARCH_X86, UC_MODE_64)
        self.u.mem_map(BASE, (len(image) + 4095) & ~4095)
        self.u.mem_write(BASE, image)
        self.u.mem_map(ARENA, 0x20000)
        self.u.reg_write(UC_X86_REG_GS_BASE, TEB)
        self.u.mem_write(TEB + 0x58, qword(TLS_SLOTS))
        self.u.mem_write(TLS_SLOTS, qword(TLS_DATA))
        self.u.mem_write(TLS_DATA + 0x10, bytes(4))
        self.u.mem_write(BASE + 0x203ABC0, bytes(4))
        self.u.mem_write(BASE + 0x19E1D98, bytes(4))
        self.calls = []
        self.visits = []
        self.allowed = ()

        def code(uc, address, size, _):
            if address == STOP:
                uc.emu_stop()
                return
            rva = address - BASE
            self.visits.append(rva)
            if rva == 0x292220:
                self.calls.append("292220: singleton pointer only")
                uc.reg_write(UC_X86_REG_RAX, CACHE)
                sp = uc.reg_read(UC_X86_REG_RSP)
                target, = struct.unpack("<Q", uc.mem_read(sp, 8))
                uc.reg_write(UC_X86_REG_RSP, sp + 8)
                uc.reg_write(UC_X86_REG_RIP, target)
                return
            if not any(lo <= rva < hi for lo, hi in self.allowed):
                raise AssertionError(f"unexpected instruction/call {rva:#x}")

        self.u.hook_add(UC_HOOK_CODE, code)

    def run(self, start, end, rcx=CACHE, rdx=0):
        self.allowed = ((start, end),)
        self.visits = []
        sp = ARENA + 0x1FEF8
        self.u.mem_write(sp, qword(STOP))
        self.u.reg_write(UC_X86_REG_RSP, sp)
        self.u.reg_write(UC_X86_REG_RCX, rcx)
        self.u.reg_write(UC_X86_REG_RDX, rdx)
        self.u.emu_start(BASE + start, STOP, count=10000)
        assert self.u.reg_read(UC_X86_REG_RIP) == STOP, "instruction cap reached"
        return self.u.reg_read(UC_X86_REG_RAX) & 0xFF

    def read(self, address, size):
        return bytes(self.u.mem_read(address, size))

    def dword(self, address):
        return struct.unpack("<I", self.read(address, 4))[0]


def main():
    image = (P / "game-runtime-image.bin").read_bytes()
    assert hashlib.sha256(image).hexdigest() == IMAGE_SHA256
    s = Shadow(image)
    u = s.u
    checks = []

    def check(name, condition, **facts):
        assert condition, name
        checks.append({"name": name, "pass": True, **facts})

    cache = bytearray(0x78)
    struct.pack_into("<Q", cache, 0, RAW)
    struct.pack_into("<II", cache, 8, 0, 1)
    cache[0x14:0x65] = b"\x01" * (0x65 - 0x14)
    struct.pack_into("<IIII", cache, 0x68, 3, 7, 11, 13)
    u.mem_write(CACHE, bytes(cache))
    u.mem_write(RAW + 0x50, struct.pack("<I", 0x22))
    u.mem_write(RAW + 0x158 + 0x1E, b"\x01")
    u.mem_write(MOUSE, bytes(0x68))
    u.mem_write(MOUSE + 0xC, struct.pack("<IIIIII", 1, 1, 1, 1, 1, 1))
    normal_before = s.run(0x3A2900, 0x3A291B, rdx=0)
    raw_before = s.run(0x3A2DA0, 0x3A2DB1)
    mouse_before = s.run(0x3A2920, 0x3A2946, rcx=MOUSE, rdx=0)
    check("actual queries detect seeded normal/raw/mouse input",
          normal_before == raw_before == mouse_before == 1)
    s.run(0x3A2700, 0x3A27FB)
    flush_instructions = len(s.visits)
    normal_after = s.run(0x3A2900, 0x3A291B, rdx=0)
    raw_after = s.run(0x3A2DA0, 0x3A2DB1)
    mouse_after = s.run(0x3A2920, 0x3A2946, rcx=MOUSE, rdx=0)
    check("native flush neutralizes tested normalized button query", normal_after == 0)
    check("native flush neutralizes tested normalized mouse query", mouse_after == 0)
    check("native flush DOES NOT neutralize raw modifier query", raw_after == 1,
          query_rva="0x3a2da0", raw_modifier_bits=s.dword(RAW + 0x50))
    check("raw keyboard pointer survives flush", s.read(CACHE, 8) == qword(RAW))
    check("raw held key survives flush", s.read(RAW + 0x158 + 0x1E, 1) == b"\x01")
    check("all four special repeat counters survive flush", s.read(CACHE + 0x68, 16) == cache[0x68:0x78])
    check("both normalized button masks cleared", s.read(CACHE + 0x14, 8) == bytes(8))
    check("both normalized key slots cleared", s.read(CACHE + 0x58, 8) == bytes(8))

    # Native conversion after flush, on the next active input frame. It consumes
    # the preserved physical raw data and can repopulate normalized input.
    u.mem_write(BASE + 0x1905654, struct.pack("<I", 1))
    s.run(0x3A3810, 0x3A39D0, rdx=RAW)
    conversion_instructions = len(s.visits)
    check("actual conversion repopulates key after one-off flush",
          s.dword(CACHE + 0x58) == 0x1E and s.dword(CACHE + 0x60) == 1,
          key=s.dword(CACHE + 0x58), repeat=s.dword(CACHE + 0x60))
    check("actual conversion advances preserved special repeat", s.dword(CACHE + 0x6C) == 8,
          counter_before=7, counter_after=s.dword(CACHE + 0x6C))

    # Releasing raw keys before another real conversion is a different action
    # from cache flush; this models device evidence, not a deployed gate.
    u.mem_write(RAW + 0x50, bytes(4))
    u.mem_write(RAW + 0x158 + 0x1E, b"\0")
    s.run(0x3A3810, 0x3A39D0, rdx=RAW)
    check("real conversion clears special counters after raw release", s.read(CACHE + 0x68, 16) == bytes(16))
    check("real raw query is neutral after raw release", s.run(0x3A2DA0, 0x3A2DB1) == 0)

    report = {
        "schema": "san14.transition-input-gate-shadow.v1", "result": "PASS",
        "image_sha256": IMAGE_SHA256, "base": hex(BASE),
        "checks_passed": len(checks), "checks": checks,
        "code_sha256": {hex(a): hashlib.sha256(image[a:b]).hexdigest() for a, b in (
            (0x3A2700, 0x3A27FB), (0x3A2900, 0x3A291B), (0x3A2920, 0x3A2946),
            (0x3A2DA0, 0x3A2DB1), (0x3A3810, 0x3A39D0))},
        "executed_unchanged_functions": ["3A2700", "3A2900", "3A2920", "3A2DA0", "3A3810"],
        "flush_instructions": flush_instructions, "conversion_instructions": conversion_instructions,
        "external_stubs": s.calls,
        "environment": "Private emulator memory, fake TEB/TLS already initialized, active-input-frame flag, synthetic device state.",
        "proved": "A one-off native cache flush leaves raw modifiers, raw keys, and special repeat counters; actual conversion can recreate input on the next frame.",
        "not_proved": ["all native input paths covered", "live game-thread ordering", "DirectInput provider behavior",
                       "window message drain/filter correctness", "controller alternate provider handling", "native release gate installed"],
        "game_process_access": False, "game_memory_writes": 0, "game_calls": 0,
        "visible_windows_created": 0, "native_gate_complete": False,
    }
    (P / "transition_input_gate_shadow.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"result": "PASS", "checks_passed": len(checks), "native_gate_complete": False}))
    return report


if __name__ == "__main__":
    main()
