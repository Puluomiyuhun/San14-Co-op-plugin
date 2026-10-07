"""Compile real production guards separately; test only own-process layouts."""
from __future__ import annotations
import datetime
import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
CASES = (
    "all-phases", "bad-intent", "wrong-stamp", "wrong-image",
    "wrong-native-slot", "storage-rejected", "rng-stale", "mixed-cleanup",
    "wrong-queue-receipt", "foreign-owned-slot", "wrong-load-request",
    "wrong-title", "wrong-epoch", "game-reuses-load", "strategy-reuses-title",
    "wrong-load-type", "forged-game-name", "wrong-title-type", "phase0-still-rejected",
)

def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sources() -> dict[str, str]:
    names = {
        "checkpoint_live_runtime_guards_v2.cpp",
        "checkpoint_live_runtime_guards_v2_fixture.cpp",
        "checkpoint_native_queue_adapter_core.cpp",
        "checkpoint_bound_input_pending_adapter.cpp",
        "checkpoint_live_runtime_guards_v2_build.cmd",
        pathlib.Path(__file__).name,
    }
    todo = list(names)
    while todo:
        path = ROOT / todo.pop()
        for name in re.findall(r'^\s*#include\s+"([^"]+)"', path.read_text(encoding="utf-8-sig"), re.M):
            if name not in names and (ROOT / name).is_file():
                names.add(name)
                todo.append(name)
    return {name: sha(ROOT / name) for name in sorted(names)}

def main() -> int:
    run = ROOT / "checkpoint_live_runtime_guards_v2_runs" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    run.mkdir(parents=True)
    before = sources()
    build = subprocess.run(["cmd.exe", "/d", "/c", str(ROOT / "checkpoint_live_runtime_guards_v2_build.cmd")], cwd=ROOT, capture_output=True, timeout=90)
    (run / "build.log").write_bytes(build.stdout + build.stderr)
    rows = []
    if build.returncode == 0:
        for case in CASES:
            result = subprocess.run([str(ROOT / "checkpoint_live_runtime_guards_v2_fixture.exe"), case], cwd=ROOT, capture_output=True, text=True, timeout=20)
            (run / f"{case}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
            try:
                row = json.loads(result.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                row = {"case": case, "passed": False, "unparsed_output": result.stdout}
            row["exit_code"] = result.returncode
            row["passed"] = bool(row.get("passed") and result.returncode == 0)
            rows.append(row)
    after = sources()
    output = {
        "schema": "checkpoint-live-runtime-guards-owned-tests-v2",
        "passed": build.returncode == 0 and len(rows) == len(CASES) and all(x["passed"] for x in rows) and before == after,
        "production_compile_returncode": build.returncode,
        "source_unchanged_during_build_and_test": before == after,
        "source_sha256": after,
        "fixture_binary_sha256": sha(ROOT / "checkpoint_live_runtime_guards_v2_fixture.exe"),
        "production_object_sha256": sha(ROOT / "checkpoint_live_runtime_guards_v2_production.obj"),
        "cases": rows,
        "scope": {
            "game_access": False, "steam_access": False,
            "native_lifecycle_is_owned_model": True,
            "actual_production_guard_functions": True,
            "actual_private_pending_ticket_and_queue_adapter": True,
            "hardware_prefetch_execution": False,
            "full_session_owner_native_chain": False,
            "production_image_identity_checks_executed": False,
            "production_compiled_without_fixture_macros": True,
            "full_input_hold": False, "full_world_verified": False,
        },
    }
    (run / "result.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": output["passed"], "cases": len(rows), "result": str(run / "result.json"), "sha256": sha(run / "result.json")}, ensure_ascii=False))
    return 0 if output["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
