"""Offline diagnostic: strings referenced by decoded LEA instructions.
Only manually selected code ranges; potential matches, not coverage proof.
"""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path("work/mod_research/python_deps")))
import capstone

root = Path("work/mod_research")
image = (root / "game-runtime-image.bin").read_bytes()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
md.detail = True
results = []
for arg in sys.argv[1:]:
    data = json.loads((root / f"survey-{int(arg, 0):x}.json").read_text())
    for start, end in data["fragments"]:
        for ins in md.disasm(image[start:end], start):
            if ins.mnemonic != "lea" or len(ins.operands) != 2:
                continue
            mem = ins.operands[1]
            if mem.type != capstone.x86.X86_OP_MEM or mem.mem.base != capstone.x86.X86_REG_RIP:
                continue
            target = ins.address + ins.size + mem.mem.disp
            if not 0x123c000 <= target < 0x18c9000:
                continue
            raw = image[target:target + 400]
            candidates = []
            for encoding in ("utf-8", "cp932", "utf-16le"):
                try:
                    if encoding == "utf-16le":
                        stop = next((i for i in range(0, len(raw) - 1, 2) if raw[i:i+2] == b"\0\0"), 0)
                        value = raw[:stop].decode(encoding)
                    else:
                        value = raw.split(b"\0")[0].decode(encoding)
                    if len(value) >= 5 and all(c.isprintable() or c in "\n\r\t" for c in value):
                        candidates.append({"encoding": encoding, "text": value})
                except UnicodeError:
                    pass
            if candidates:
                item = {"function": arg, "at": hex(ins.address), "target": hex(target), "register": ins.reg_name(ins.operands[0].reg), "candidates": candidates}
                results.append(item)
                print(json.dumps(item, ensure_ascii=True))
(root / "battle-debug-string-candidates.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
