"""Offline timing audit of existing native load observations. No game access."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = (
    ("unchanged_Zhang_Lu", "startup-identity-traces/20261006-110512-181614/trace.jsonl"),
    ("handoff_to_Liu_Bei", "startup-switch-traces/20261006-124754-542123/trace.jsonl"),
)
POINTS = (
    "deserialize_return", "load_worker_result", "native_identity_initializer",
    "strategy_initialize", "user_strategy_initialize", "first_user_update",
)


def analyze(label, relative):
    path = ROOT / relative
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    assert rows[-1] == {"event": "detached", "captured": True, "registers_restored": True}
    assert not any(row["event"] in ("error", "error_cleanup", "process_exit") for row in rows)
    selected = []
    for name in POINTS:
        found = [row for row in rows if row["event"] == name]
        assert len(found) == 1
        row = found[0]
        assert isinstance(row["tick_ms"], int)
        selected.append({key: row[key] for key in ("event", "seq", "tick_ms", "thread", "states", "player")})
    assert all(a["seq"] < b["seq"] and a["tick_ms"] <= b["tick_ms"] for a, b in zip(selected, selected[1:]))
    assert "CLoadState" in selected[0]["states"]
    assert "CTitleState" in selected[0]["states"]
    assert "CUserStrategyState" in selected[-1]["states"]
    return {
        "label": label, "trace": relative, "trace_sha256": hashlib.sha256(raw).hexdigest(),
        "points": selected,
        "instrumented_partial_interval_ms": selected[-1]["tick_ms"] - selected[0]["tick_ms"],
        "stage_intervals_ms": [
            {"start": a["event"], "end": b["event"], "elapsed": b["tick_ms"] - a["tick_ms"]}
            for a, b in zip(selected, selected[1:])
        ],
        "not_an_end_to_end_load_benchmark": True,
    }


def main():
    cases = [analyze(*case) for case in CASES]
    values = [case["instrumented_partial_interval_ms"] for case in cases]
    assert values == [6063, 5687]
    auxiliary_path = ROOT / "lockstep-traces/load-rng-run-e/trace.jsonl"
    auxiliary = [json.loads(s) for s in auxiliary_path.read_text(encoding="utf-8").splitlines()]
    load_rng = next(r for r in auxiliary if r.get("states") and "CLoadState" in r["states"])
    user_rng = next(r for r in auxiliary if r.get("states") and "CUserStrategyState" in r["states"])
    result = {
        "schema": "san14.reload-latency-analysis.v1",
        "created": datetime.now().astimezone().isoformat(),
        "game_access": False, "game_memory_writes": 0, "debugger_attached_by_analysis": False,
        "cases": cases,
        "instrumented_partial_interval_range_ms": [min(values), max(values)],
        "auxiliary_different_boundary": {
            "trace": str(auxiliary_path.relative_to(ROOT)),
            "start": "rng setter inside load deserialization",
            "end": "first observed RNG call with CUserStrategyState already on state stack",
            "elapsed_ms": user_rng["tick_ms"] - load_rng["tick_ms"],
            "not_equivalent_to_first_user_update": True,
            "not_included_in_primary_range": True,
        },
        "timing_interpretation": {
            "clock": "GetTickCount64 at observation callback entry; wall clock includes debugger stops",
            "starts_after_file_read_and_deserialization": True,
            "includes": [
                "Native post-deserialization work, identity handoff and strategy/UI construction on this PC",
                "Debugger exception handling, ReadProcessMemory and synchronous log flush",
                "Adaptive hardware breakpoint rearming across roughly 106-107 traced threads",
                "For handoff: same-stage comparison of 783 records and durable one-time write reservation",
            ],
            "excludes_or_unmeasured": [
                "Manual slot selection and waiting for the user before deserialize_return",
                "File read and deserialization before deserialize_return",
                "Host save, checkpoint transfer, safe-boundary wait and verification",
                "First rendered frame, actual input-ready latency and camera restoration",
                "Uninstrumented native load timing on this PC or the friend's PC",
            ],
            "invalid_inferences": [
                "5.687-6.063 seconds is not a production reload estimate, limit or minimum",
                "Observer start-to-user-message duration is not a load time",
                "The difference between the two runs is not identity-switch performance overhead",
            ],
        },
        "state_route": {
            "observed": "CTitleState/CLoadState -> CTitleState identity handoff -> CGameState/CStrategyState/CUserStrategyState",
            "internal_title_state_proven": True,
            "visible_main_menu_required": None,
            "visible_loading_screen_duration": None,
            "currently_implemented_seamless_in_session_reload": False,
            "bypassing_title_state_proven_safe": False,
            "reason": "Class/state names and these breakpoints do not record displayed frames. Current executable observes a user-triggered native load; it does not implement an automatic room checkpoint reload command.",
        },
        "reuse_boundaries": {
            "may_preserve_external_state": ["Room connection", "Bound faction ID", "Checkpoint epoch and authority receipt", "Camera/selection preferences if later mapped to stable IDs"],
            "must_not_reuse_as_raw_pointers": ["Army display object", "Strategy state", "Player menu objects", "Entity references across deserialization"],
            "native_initialization_side_effects": "Observed RNG changes between deserialization and first player update. Strategy/UI initialization and derived fields are not proven presentation-only.",
        },
        "candidate_mitigations_not_implemented": [
            {
                "candidate": "Automated native reload with a synchronization overlay",
                "benefit": "No repeated slot selection or user clicks; retain room and restore B identity before menus construct",
                "limits": "Underlying native load/reconstruction cost remains. Overlay camera restoration and input gating still need implementation and proof.",
            },
            {
                "candidate": "Overlap receiving and verifying checkpoint bytes with B's final display/report time",
                "benefit": "Reduce visible serial waiting when a safe period boundary exists",
                "limits": "Never apply world state while B simulation workers run. Next planning remains closed until B verification; presentation overlap is not state mutation overlap.",
            },
            {
                "candidate": "Retain presentation resources or use an internal reload path",
                "benefit": "Potentially avoid reconstructing some scene assets and visible main-menu transition",
                "limits": "No captured timing breakdown identifies which part is assets, simulation, jobs or presentation. No implemented safe path bypasses title/strategy initialization.",
            },
            {
                "candidate": "Hot world replacement or semantic delta application",
                "benefit": "Potentially eliminate full-load scene transition",
                "limits": "Substantially more work: reconcile creation/removal, pointer/index ownership, queues, events, caches and UI references atomically, and prove complete state equality. Not a simple memcpy or troop-only correction.",
            },
        ],
        "next_measurement_contract": [
            "Monotonic timestamps at safe period boundary, host save begin/end, last byte received, reload start, deserialize return, player identity restored, first interactive frame, and final world digest verified",
            "Log CPU/game-stage timing separately from bytes/network and user/UI waiting",
            "Use lightweight native timestamps with buffered logging rather than hundreds of debugger rearm operations",
            "Repeat same snapshot and same hardware enough to report distribution; compare user-visible duration and native core duration separately",
            "Do not require a new user replay just to recover timestamps already available in existing logs",
        ],
    }
    (ROOT / "reload-latency-analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": [{"label": c["label"], "instrumented_partial_interval_ms": c["instrumented_partial_interval_ms"], "stages": c["stage_intervals_ms"]} for c in cases], "auxiliary": result["auxiliary_different_boundary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
