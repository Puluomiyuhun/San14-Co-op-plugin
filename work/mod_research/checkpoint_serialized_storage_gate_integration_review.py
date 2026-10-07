"""Independent offline evidence binding; no game/process/Steam imports or calls."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent
checks = []


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(path, expected):
    path = Path(path)
    if not path.is_absolute():
        path = P / path
    actual = digest(path)
    checks.append(dict(path=str(path), expected=expected, actual=actual,
                       passed=actual == expected))


def read(path):
    return json.loads((P / path).read_text(encoding="utf-8-sig"))


def main():
    checked("checkpoint_live_runtime_guards_handoff.json", "0b61a236212ffb339f13dbd933935b88a489a420c5520d7b2b56daab7514c676")
    guard = read("checkpoint_live_runtime_guards_handoff.json")
    for name, expected in guard["source_sha256"].items():
        checked(name, expected)
    checked(guard["result"], guard["result_sha256"])
    checked("checkpoint_live_runtime_guards_fixture.exe", guard["fixture_binary_sha256"])
    checked("checkpoint_live_runtime_guards_production.obj", guard["production_object_sha256"])
    checked("checkpoint_live_runtime_guards_notes.txt", guard["notes_sha256"])
    gr = read(guard["result"])
    assert gr["passed"] and len(gr["cases"]) == 13 and all(c["passed"] for c in gr["cases"])
    owner_path = "checkpoint_complete_live_owner_runs/20261007-152852-469134/result.json"
    checked("checkpoint_complete_live_owner_handoff.json", "06e3ca650080027743ff9cf7f6dd9a20d583b9229d951a8f0a464cb707010314")
    handoff = read("checkpoint_complete_live_owner_handoff.json")
    checked(owner_path, handoff["result_sha256"])
    owner = read(owner_path)
    assert owner["source_sha256"] == handoff["source_sha256"]
    for name, expected in handoff["evidence_sha256"].items():
        checked(name, expected)
    for name, expected in owner["source_sha256"].items():
        checked(name, expected)
    checked("checkpoint_complete_live_owner.dll", owner["dll_sha256"])
    checked("checkpoint_complete_live_owner_fixture.exe", owner["fixture_exe_sha256"])
    assert owner["passed"] and len(owner["cases"]) == 12 and all(c["passed"] for c in owner["cases"])
    for case in owner["cases"]:
        if "binary_report_sha256" in case:
            checked(Path(owner_path).parent / case["case"] / "report.bin", case["binary_report_sha256"])
    launcher_path = "checkpoint_complete_live_launcher_tests/20261007-153153-539299/result.json"
    launcher = read(launcher_path)
    checked("checkpoint_complete_live_start.py", launcher["source_sha256"])
    assert launcher["result"] == "PASS" and len(launcher["cases"]) == 10 and all(c["passed"] for c in launcher["cases"])
    assert all(c["passed"] for c in checks), [c for c in checks if not c["passed"]]
    paths = ["checkpoint_serialized_storage_gate_handoff.json", "checkpoint_live_runtime_guards_handoff.json",
             "checkpoint_complete_live_owner_handoff.json", "checkpoint_complete_live_capture.py",
             "checkpoint_complete_live_start.py", "checkpoint_complete_live_launcher_test.py", owner_path, launcher_path]
    evidence = {name: digest(P / name) for name in paths}
    report = dict(schema="san14.serialized-storage-owner-independent-review.v1",
        result="NO_NEW_BLOCKER_WITHIN_REVIEWED_SCOPE", checks=checks, evidence_sha256=evidence,
        source_and_artifact_checks=len(checks), guard_cases=13, owner_cases=12, launcher_mock_cases=10,
        fixed_findings=[
            "Owner Stop now atomically revokes owner, queue, controller and Session before waiting for install control lock.",
            "Owner explicitly refuses initial nonempty queue capacity/pointer; guards require the witnessed fresh allocation path.",
            "Launcher reads all six actual hook slots and protections before install, after accepted receipts and after Stop.",
            "Launcher checks post-Stop late errors, unchanged completion bindings and callback/bridge drain before PASS.",
            "Uncertain cleanup Stop is now recorded as uncertain remote lifetime; no retry or post-CAS detach is introduced."],
        observations=[
            "All production owner validator families bind the real guard context; request Api and guard callbacks share the serialized Gate.",
            "Storage owner/hook callbacks do not recurse into Gate or Session Snapshot; native methods and joins remain outside validation lock.",
            "Ordinary Session Stop retains storage and load/identity/planning observers after possible CAS.",
            "Guard Title/planning phases do not dereference retired old world/UI/Load/Title objects; protected-page fixtures exercise that boundary.",
            "Durable launcher claim precedes remote LoadLibrary; uncertain threads retain argument memory and no automatic retry occurs."],
        limits=[
            "This review only reads workspace source and prior own-process results; no fixtures rerun and no game/Steam/process/window access.",
            "Factory fixture reaches production configure, real guards/Gate and six-hook Arm, then rejects a pending player command; it does not execute a production-guard full load.",
            "Full Session lifetime fixtures use owned native bodies/environment doubles; 29 guard phases use an owned lifecycle model.",
            "Actual loaded-image identity, Steam lifetime and live callback scheduling still require the separate controlled live test.",
            "No full input hold, complete world equality, pixels/visibility, room READY, or post-CAS unload authority is established.",
            "Launcher remains unapproved until root pins the independently reviewed owner artifact hashes; changing approval constants is a separate root step."],
        game_access=False, steam_access=False, fixtures_rerun=False, native_load_authorized=False)
    target = P / ("checkpoint_serialized_storage_gate_integration_review_" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json")
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(path=str(target), sha256=digest(target), checks=len(checks))))


if __name__ == "__main__":
    main()
