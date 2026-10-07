"""Assemble the small review artifact from preserved local experiment evidence."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRACES = ROOT / "lockstep-traces"
OUT = ROOT.parents[1] / "outputs" / "san14-link"
read = lambda path: json.loads(path.read_text(encoding="utf-8"))
comparison = read(TRACES / "compare-run-a-run-b.json")
detail = read(TRACES / "first-divergence-detail.json")
closeout = read(TRACES / "closeout.json")
baseline = read(TRACES / "run-a" / "before.json")
names = {p["id"]: p["name"] for p in baseline["eligibility"]["persons"]}
assert comparison["completed_both"] and comparison["sampled_baselines_equal"]
assert comparison["observed_repeatability_pass"] is False
assert comparison["first_stage_difference_with_rng"]["index"] == 168
assert closeout["result"] == "PASS" and not closeout["debugger_attached"]
assert len(detail["run-a"]["events"]) == 0
assert len(detail["run-b"]["events"]) == 16
for row in detail["run-b"]["troop_changes"]:
    row["officer_name"] = names.get(row["officer"])

anchors = [
    {"rva": "0x2F9610", "finding": "World serialization includes world+450/+454/+458/+45C and the global RNG via 3AA390/3AA3E0", "source": "survey-2f9610.txt", "status": "static code plus observed save34 restoration"},
    {"rva": "0x3AA2C0", "finding": "Integer keyed random calculation reads world+45C and world+450; this function does not consume global RNG or call the clock", "source": "survey-3aa2c0.txt", "status": "static, one random function only"},
    {"rva": "0x2FCBC0", "finding": "Adds 2 to world+38, wraps at 24 and increments calendar/counters", "source": "disasm-2fcbc0.txt", "status": "static; subday byte not included in A/B stage snapshots"},
    {"rva": "0x3F8E10", "finding": "Stage12 tests RBP before calling B11E0/16C640; RBP derives from subday/2 == 5. Loop has a clock budget comparison against 30", "source": "survey-3f8e10.txt", "status": "static gate candidates; branch registers were not logged"},
    {"rva": "0x16C640", "finding": "Pending +94 and effect queue count select waiting/cleanup versus generating pairs and applying combat", "source": "survey-16c640.txt", "status": "static gate candidate; flag and queue at first fork unknown"},
    {"rva": "0x16CB30", "finding": "Checks/starts worker task and updates manager+90", "source": "survey-16cb30.txt", "status": "static scheduling candidate; no causal proof"},
]
for anchor in anchors:
    p = ROOT / anchor["source"]
    anchor["source_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()

evidence = {
    "schema": "san14.lockstep-feasibility.observed-repeatability.v1",
    "created": datetime.now().astimezone().isoformat(),
    "result": "OBSERVED_REPEATABILITY_FAILED_CAUSE_UNRESOLVED",
    "summary_zh": "同一进程两次原生读同档推进，在部分起点数据及已发现随机状态一致时仍分叉。未证明完整起点一致，不能据此否定补齐状态后的确定性锁步。",
    "experiment": {
        "game_build_sha256": baseline["focused"]["exe_sha256"],
        "start": {"year": 203, "month": 8, "day": 11},
        "end": {"year": 203, "month": 8, "day": 21},
        "new_commands": False, "speed": "User instructed to keep unchanged; not independently captured",
        "native_load_restored_discovered_rng": True, "manual_seed_memory_write": False,
        "two_game_processes_tested": False, "two_computers_tested": False,
        "instrumentation": "Hardware execution breakpoints; no game code/data writes or new DLL this experiment; debugger changes wall-clock scheduling",
        "breakpoint_rvas": {"stage": "0x3F9219", "casualty_request": "0x16AC60", "position_write": "0x2A9DA4", "planning_return": "0x3F9B00"},
        "baseline_record_counts": {"person": 571, "city": 52, "district": 52, "force": 52, "army": 56, "total": 783, "sampled_tasks": 108},
        "record_coverage": baseline["record_scope"],
        "stage_coverage": "Date Y/M/D, stage, four world fields, one global RNG, active-army and city bytes [0x10,0x68). Not full logical world, event/animation coverage or subday/register/queue coverage.",
        "metadata": {name:read(TRACES / name / "metadata.json") for name in ("run-a", "run-b")},
    },
    "comparison": comparison,
    "first_fork_detail": detail,
    "per_field_stage_comparison": closeout["stage_field_comparison"],
    "first_observed_global_rng_difference": closeout["first_rng_difference"],
    "static_evidence": anchors,
    "closeout": closeout,
    "observer_fixture_results": read(ROOT / "lockstep-observer-fixtures.json"),
    "limits_zh": [
        "样本一致不等于全部逻辑状态一致；已识别显示对象指针以外的内部队列/进度/对象内部状态可能没有覆盖。",
        "初次伤害批次差异已观测，阶段门控、等待标志、交战列表和工作线程是否致因仍未知。",
        "硬件断点影响实际耗时，夹具通过不能排除对游戏调度的影响。",
        "相同移动次数不能证明移动顺序或路线相同；函数入口伤害请求不等于全部实际施加。",
        "首个兵力分叉处所监测随机状态相同，后来不同；没有穷尽所有随机来源。",
        "最终读档后采集的调度诊断只能供下次参考，不能反推两轮分叉时的取值。",
        "两客户端、不同视角/帧率/控制势力、完整战法与人类事件暂停尚未实测。"
    ],
    "next_diagnostic_plan": [
        "Capture native subday, RBP/RSI branch gate, battle manager+90/+94 and effect/pair counts near first divergence",
        "Observe whether stage12 is skipped, waiting, empty of combat pairs or processing different candidates",
        "Audit native load/turn initialization and worker completion before designing reset or synchronization",
        "After correction, rerun with reduced instrumentation, then fresh processes and separate player/view contexts",
        "Only commit to lockstep after matching per-step state and semantic event streams; retain authority simulation as fallback"
    ],
}
destination = OUT / "确定性锁步初步证据.json"
destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
assert read(destination) == evidence
print(json.dumps({"output": str(destination), "bytes": destination.stat().st_size,
                  "result": evidence["result"], "restored": closeout["result"]}, ensure_ascii=True))
