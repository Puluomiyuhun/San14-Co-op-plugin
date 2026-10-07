"""Offline production compile and owned-process adapter contract checks only."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
CASES = (
    "empty-success", "existing-success", "no-authorization",
    "wrong-controller", "wrong-ticket", "wrong-caller", "wrong-thread",
    "stop-before-queue", "header-drift-before", "external-refusal",
    "native-cpp-exception", "native-seh-exception", "invalid-native-results",
    "full-span-noaccess", "header-drift-after", "stop-in-native",
    "resolver-exact-once", "resolver-header-stop", "repeat-queue-authorization",
    "profile-drift",
)
SOURCES = (
    "checkpoint_native_queue_adapter_core.h",
    "checkpoint_native_queue_adapter_core.cpp",
    "checkpoint_native_queue_adapter_profile.h",
    "checkpoint_native_queue_adapter_profile.json",
    "checkpoint_native_queue_adapter_fixture.cpp",
    "checkpoint_native_queue_adapter_build.cmd",
    "checkpoint_native_queue_adapter_test.py",
    "checkpoint_bound_input_pending_adapter.h",
    "checkpoint_bound_input_pending_adapter.cpp",
    "checkpoint_native_input_pending_adapter.h",
    "checkpoint_native_input_core.h",
    "checkpoint_load_dispatch_bridge.h",
    "checkpoint_push_bridge.h",
)

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fingerprint() -> dict[str, str]:
    return {name: sha(ROOT / name) for name in SOURCES}

def main() -> int:
    dest = ROOT / "checkpoint_native_queue_adapter_runs" / dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dest.mkdir(parents=True, exist_ok=False)
    before = fingerprint()
    build = subprocess.run(["cmd", "/c", str(ROOT / "checkpoint_native_queue_adapter_build.cmd")],
                           cwd=ROOT, capture_output=True, timeout=90)
    (dest / "build.log").write_bytes(build.stdout + build.stderr)
    results = []
    if build.returncode == 0:
        for case in CASES:
            run = subprocess.run([str(ROOT / "checkpoint_native_queue_adapter_fixture.exe"), case],
                                 cwd=ROOT, capture_output=True, timeout=15)
            try:
                evidence = json.loads(run.stdout)
            except (UnicodeError, ValueError):
                evidence = {}
            results.append({"case": case, "returncode": run.returncode,
                            "passed": run.returncode == 0 and evidence.get("passed") is True,
                            "evidence": evidence, "stderr": run.stderr.decode("utf-8", "replace")})
    after = fingerprint()
    passed = build.returncode == 0 and len(results) == len(CASES) and all(x["passed"] for x in results) and before == after
    result = {
        "schema": "san14.native-queue-adapter-fixtures.v1", "passed": passed,
        "production_compiled": build.returncode == 0,
        "cases": results, "case_count": len(results), "source_sha256": after,
        "sources_unchanged_during_build_and_test": before == after,
        "production_obj_sha256": sha(ROOT / "checkpoint_native_queue_adapter_production.obj") if build.returncode == 0 else None,
        "fixture_exe_sha256": sha(ROOT / "checkpoint_native_queue_adapter_fixture.exe") if build.returncode == 0 else None,
        "fixture_core_obj_sha256": sha(ROOT / "checkpoint_native_queue_adapter_fixture_core.obj") if build.returncode == 0 else None,
        "game_access": False, "steam_access": False, "installer_included": False,
        "scope": "Same production adapter validation/authorization/Queue/Resolve code with fixture-only native body and image/caller adaptation; actual frozen pending core creates and consumes private tickets.",
        "limitations": [
            "Native 411980/constructor bodies are owned doubles here, not real game execution.",
            "Standalone fixture upstream frames and prefetch observations are synthetic; full hardware/bridge/Session integration has separate evidence.",
            "Adapter does not independently authenticate private ticket internals; production controller must pass its just-created ticket directly.",
            "No full input hold, scheduler exclusion, world equality, load success or gameplay release is established.",
        ],
    }
    path = dest / "result.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"passed": passed, "cases": len(results), "result": str(path)}))
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
