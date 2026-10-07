"""Capture a paused planning baseline including discovered random-state fields.
Reads only. Existing record reader is deliberately a partial-world observer.
"""
import argparse
import hashlib
import json
from pathlib import Path
from run_reward_execution_pilot import capture, BattleObserver

ROOT = Path(__file__).resolve().parent
RNG_RVA = 0x18EB8B0

def sample(reader):
    result = capture(reader)
    m = reader.memory
    root = reader.pointer(m.base + 0x1FCA1E0)
    world = reader.pointer(root + 0x85130)
    reader.require_type(world, "CWorldData")
    values = m.read(world + 0x450, 16)
    result["random_inputs"] = {
        **{f"world_{offset:x}": int.from_bytes(values[offset-0x450:offset-0x44c], "little")
           for offset in (0x450, 0x454, 0x458, 0x45C)},
        "global_18eb8b0": int.from_bytes(m.read(m.base + RNG_RVA, 4), "little")
    }
    result["random_scope"] = "Discovered world and global RNG fields; not an exhaustive inventory"
    return result

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("name")
    args = p.parse_args()
    if not args.name.replace("-", "").isalnum():
        raise SystemExit("Use a simple sample name")
    reader = BattleObserver()
    try:
        result = sample(reader)
        if result != sample(reader):
            raise RuntimeError("Planning baseline changed during capture")
        path = ROOT / "lockstep-traces" / (args.name + ".json")
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            raise RuntimeError("Refusing to overwrite an existing sample")
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"path": str(path), "date": result["focused"]["critical_state"]["date"],
                          "random_inputs": result["random_inputs"],
                          "sampled_records": len(result["records"])}, ensure_ascii=True))
    finally:
        reader.close()
