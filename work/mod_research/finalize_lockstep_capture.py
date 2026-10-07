"""Read-only closeout and trace statistics for the first lockstep experiment."""
import ctypes as C
import argparse
from ctypes import wintypes as W
from datetime import datetime
import hashlib
import json
from pathlib import Path
from lockstep_baseline import sample, BattleObserver
from analyze_lockstep import load, rows, baseline_difference
from run_reward_execution_pilot import CHECKPOINT

ROOT = Path(__file__).resolve().parent
TRACES = ROOT / "lockstep-traces"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def diagnostics(reader):
    m = reader.memory
    root = reader.pointer(m.base + 0x1FCA1E0)
    world = reader.pointer(root + 0x85130)
    reader.require_type(world, "CWorldData")
    # These three accessors return addresses of inline globals, not heap pointers.
    u32 = lambda addr: int.from_bytes(m.read(addr, 4), "little")
    u64 = lambda addr: int.from_bytes(m.read(addr, 8), "little")
    return {
        "world_subday_38": m.read(world + 0x38, 1)[0],
        "battle_manager_1a24cf0": {
            "worker_90": u32(m.base + 0x1A24CF0 + 0x90),
            "pending_94": u32(m.base + 0x1A24CF0 + 0x94)},
        "effects_1a38a20": {
            "count_38": u64(m.base + 0x1A38A20 + 0x38),
            "pending_98": u32(m.base + 0x1A38A20 + 0x98)},
        "pairs_1a38840_count_c0": u64(m.base + 0x1A38840 + 0xC0),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-name', default='closeout')
    parser.add_argument('--report-rng-mismatch', action='store_true',
                        help='Report, never hide or repair, a discovered RNG mismatch after gameplay restoration')
    args = parser.parse_args()
    assert args.output_name.replace('-', '').isalnum()
    destination = TRACES / (args.output_name + '.json')
    if destination.exists():
        raise RuntimeError('Refusing to overwrite closeout evidence')
    before = load(TRACES / "run-a" / "before.json")
    reader = BattleObserver()
    try:
        restored = sample(reader)
        comparison = baseline_difference(before, restored)
        assert not comparison["sampled_record_changes_excluding_known_runtime_pointer"]
        assert all(comparison[k] for k in ("focused_state_equal", "person_task_sample_equal"))
        if not args.report_rng_mismatch:
            assert comparison['random_inputs_equal']
        root = reader.pointer(reader.memory.base + 0x1FCA1E0)
        links = []
        for unit in restored["focused"]["all_active_units"]:
            address = reader.pointer(root + 0x7DF60 + unit["id"] * 8)
            old = int.from_bytes(bytes.fromhex(before["records"][f"army:{unit['id']}"])[0x138:0x140], "little")
            ptr = int.from_bytes(reader.memory.read(address + 0x148, 8), "little")
            assert bool(old) == bool(ptr)
            if ptr:
                reader.require_type(ptr, "CUnitArmy")
                assert reader.pointer(ptr + 0x40) == address
            links.append({"army_id": unit["id"], "runtime_present": bool(ptr), "pointer_rebuilt": old != ptr})
        k = reader.memory.k
        k.CheckRemoteDebuggerPresent.argtypes = [W.HANDLE, C.POINTER(W.BOOL)]
        k.CheckRemoteDebuggerPresent.restype = W.BOOL
        debugger = W.BOOL()
        if not k.CheckRemoteDebuggerPresent(reader.memory.handle, C.byref(debugger)):
            raise C.WinError(C.get_last_error())
        assert not debugger.value
        original_update = reader.pointer(reader.memory.base + 0x12CC4A8 + 0x28) == reader.memory.base + 0x3F9B00
        assert original_update
        diag = diagnostics(reader)
        assert diag == diagnostics(reader)
        assert restored == sample(reader)
        checkpoint_hash = sha(CHECKPOINT)
        backup_hash = sha(ROOT.parent / "mod_test" / "replay-checkpoint-34" / "svdexSC34.s14")
        assert checkpoint_hash == backup_hash == "afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95"
        report = {
            "created": datetime.now().astimezone().isoformat(), "pid": reader.pid,
            "result": "PASS" if comparison['random_inputs_equal'] else "SAMPLED_GAMEPLAY_RESTORED_RNG_DIFFERS",
            "rng_state_rewritten": False,
            "date": restored["focused"]["critical_state"]["date"],
            "player": restored["focused"]["critical_state"]["player"],
            "sampled_records": len(restored["records"]), "comparison": comparison,
            "runtime_pointer_validation": {"field": "army+0x148", "type": "CUnitArmy", "backlink": "+0x40", "links": links},
            "debugger_attached": bool(debugger.value), "original_strategy_update_restored": original_update,
            "save34_sha256": checkpoint_hash, "backup_sha256": backup_hash,
            "restored_diagnostics": diag,
            "diagnostic_scope": "Captured after final restore only, NOT captured in runs A/B; cannot explain the earlier fork retrospectively.",
            "complete_world_equality_proven": False,
        }
    finally:
        reader.close()

    runs = [[r for r in rows(TRACES / name / "trace.jsonl") if r["event"] == "stage"] for name in ("run-a", "run-b")]
    assert len(runs[0]) == len(runs[1]) == 3720
    stats = {}
    for field in ("date", "stage", "world_inputs", "global_rng", "armies", "cities"):
        differing = [i for i, (a, b) in enumerate(zip(*runs)) if a[field] != b[field]]
        stats[field] = {"different_samples": len(differing), "first_difference": differing[0] if differing else None}
    report["stage_field_comparison"] = stats
    report["first_rng_difference"] = None
    first_rng = stats["global_rng"]["first_difference"]
    if first_rng is not None:
        report["first_rng_difference"] = {"index": first_rng, "a": {k:runs[0][first_rng][k] for k in ("date", "stage", "global_rng")}, "b": {k:runs[1][first_rng][k] for k in ("date", "stage", "global_rng")}}
    report["artifacts"] = [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in [ROOT / "observe_lockstep.exe", ROOT / "observe_lockstep.cpp",
                     TRACES / "run-a" / "trace.jsonl", TRACES / "run-b" / "trace.jsonl",
                     TRACES / "run-a" / "before.json", TRACES / "run-b" / "before.json"]]
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result": report["result"], "date": report["date"], "sampled_records": report["sampled_records"],
                      "debugger_attached": report["debugger_attached"], "restored_diagnostics": report["restored_diagnostics"],
                      "stage_field_comparison": stats, "first_rng_difference": report["first_rng_difference"]}, ensure_ascii=True))

if __name__ == "__main__":
    main()
