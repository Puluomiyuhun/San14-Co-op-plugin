"""Offline native reload entry investigation. Never opens a game process."""
import sys
from bisect import bisect_right
from pathlib import Path

targets = [int(arg, 0) for arg in sys.argv[1:]]
sys.argv = sys.argv[:1]
import disasm_chained as d

for target in targets:
    idx = bisect_right(d.starts, target) - 1
    if idx < 0 or target >= d.entries[idx][1]:
        raise ValueError(f"No unwind function for {target:#x}")
    root = d.primary(d.entries[idx])
    fragments = sorted(set(d.groups[root] + [root]))
    lines = [f"Primary {root[0]:#x}; target {target:#x}; fragments {len(fragments)}",
             "Offline linear decoding bounded by chained unwind metadata; indirect flow not resolved."]
    for a, z, _ in fragments:
        lines.append(f"\nFragment {a:#x}..{z:#x}")
        for ins in d.decoder.disasm(d.image[a:z], a):
            lines.append(f"{ins.address:#x}: {ins.mnemonic} {ins.op_str}")
    out = d.ROOT / f"reload-entry-{root[0]:x}.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out.name, len(lines))
