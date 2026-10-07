"""Check selected offline code anchors; never opens or writes the game process.

This is evidence packaging, not a multiplayer adapter or a complete CFG proof.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT = Path("work/mod_research")
OUT = Path("outputs/san14-link")
sys.path.insert(0, str(ROOT / "python_deps"))
import capstone

image = (ROOT / "game-runtime-image.bin").read_bytes()
metadata = json.loads((ROOT / "runtime-203-08-zhanglu.json").read_text(encoding="utf-8"))
base = int(metadata["image_base"], 16)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
md.detail = True
anchors = [
    (0x15C162, "call 0x166cc0"),
    (0x15C174, "call 0x15c260"),
    (0x15C185, "call 0x15cd80"),
    (0x15C196, "call 0x15cbc0"),
    (0x15C1A7, "call 0x15c9b0"),
    (0x15C1BB, "call 0x161f10"),
    (0x15C1CD, "call 0x166aa0"),
    (0x15C1E5, "call 0x166f30"),
    (0x15CAEC, "call 0x15c400"),
    (0x15CB10, "mov word ptr [rbp + 0x20], bx"),
    (0x166B82, "movzx r8d, word ptr [rbp + 0x20]"),
    (0x166B8B, "add r8d, ecx"),
    (0x166B9C, "call 0x16ac60"),
    (0x16AD97, "mov rsi, qword ptr [rax + rcx*8 + 0x7df60]"),
    (0x16ADCF, "cmovl r12d, eax"),
    (0x16AEFC, "mov word ptr [rsi + 0x16], ax"),
    (0x16B0DC, "call 0x249600"),
    (0x166BE7, "mov word ptr [r15 + 8], ax"),
    (0x166C10, "mov dword ptr [r15 + 0x10], r12d"),
    (0x166C9E, "call 0x2ba810"),
    (0x2BA828, "mov rcx, qword ptr [rbx + 0x148]"),
    (0x2BA834, "add rcx, 0x580"),
    (0x2BA83D, "call 0x1b7390"),
    (0x1B7395, "mov dword ptr [rcx + 0x14], edx"),
    (0x164ED4, "call 0x15fb70"),
    (0x164EE8, "call 0x166090"),
    (0x15FBC1, "call 0x159f40"),
    (0x165E1E, "call 0x16a790"),
    (0x16640B, "call 0x16a790"),
    (0x16A9C6, "call 0x168ba0"),
    (0x1691A7, "call 0x16ac60"),
    (0x1691D8, "call 0x16bd40"),
    (0x1B4F31, "call 0x15ef40"),
    (0x1B4F4D, "call 0x336bf0"),
    (0x1B4F6D, "call 0x16ba50"),
    (0x336C4D, "jb 0x336dc8"),
    (0x3371C1, "mov qword ptr [rbx + 0x28], r8"),
    (0x3371CF, "call 0x337cf0"),
    (0x337CF4, "cmp r8, qword ptr [rcx + 0x28]"),
    (0x337D78, "movaps xmmword ptr [rcx + 0x30], xmm0"),
    (0x16BA71, "call 0x337bb0"),
    (0x337BCE, "mov qword ptr [rcx + 0x28], rax"),
    (0x337BB5, "jne 0x338450"),
    (0x16BF4D, "call 0x337200"),
    (0x16BFAF, "call 0x1b1b80"),
    (0x1B1B87, "jmp 0x1feac0"),
    (0x164084, "call 0x164390"),
    (0x16409F, "call 0x164390"),
    (0x1641A5, "call 0x1954c0"),
    (0x1648C4, "add dword ptr [rbx + 0x28], r15d"),
]
checked = []
for rva, expected in anchors:
    ins = next(md.disasm(image[rva:rva+16], rva, count=1))
    actual = f"{ins.mnemonic} {ins.op_str}".strip()
    assert actual == expected, (hex(rva), actual, expected)
    checked.append({"rva": hex(rva), "bytes": ins.bytes.hex(), "instruction": actual})

# Known switch table, excluded from executable code.
stage_entries = [0x15C15C, 0x15C169, 0x15C17D, 0x15C18E, 0x15C19F, 0x15C1B0, 0x15C1C2]
assert list(struct.unpack_from("<7I", image, 0x15C244)) == stage_entries
code_starts = {i.address for i in md.disasm(image[0x15BE80:0x15C244], 0x15BE80)}
assert all(address in code_starts for address in stage_entries)

# Verify both constructor reference and actual MSVC RTTI type descriptor.
ins = next(md.disasm(image[0x159F61:0x159F71], 0x159F61, count=1))
assert ins.mnemonic == "lea"
vtable = ins.address + ins.size + ins.operands[1].mem.disp
assert vtable == 0x128F970
locator = struct.unpack_from("<Q", image, vtable - 8)[0] - base
sig, _, _, descriptor, _, locator_self = struct.unpack_from("<6I", image, locator)
assert sig == 1 and locator_self == locator
type_name = image[descriptor+16:descriptor+144].split(b"\0")[0].decode("ascii")
assert type_name == ".?AVCTacticsManager@@"

record = {
    "date": "2026-10-05",
    "scope": "offline static anchors plus separately recorded read-only planning-state sample",
    "exe_sha256": metadata["exe_sha256"],
    "captured_image_sha256": hashlib.sha256(image).hexdigest(),
    "dynamic_battle_recorded": False,
    "native_event_replay_tested": False,
    "two_game_clients_tested": False,
    "checked_instruction_anchors": checked,
    "checked_combat_stage_table": {
        "rva": "0x15c244", "indices": "1..7",
        "entries": [hex(x) for x in stage_entries],
        "note": "Branches may exit early; this table does not prove coverage of all attack types."
    },
    "checked_tactics_manager_type": {
        "constructor": "0x159f40", "vtable_reference": "0x159f61",
        "vtable": hex(vtable), "type_name": type_name,
        "accessor": "0x15fb70", "singleton_rva": "0x1a38ad0"
    },
    "findings": [
        {"id": "casualty-write", "strength": "direct-static-dataflow",
         "detail": "16AC60 resolves target kind 0x1B through army table, caps requested loss, writes CArmyUnitData+0x16 at 16AEFC. It also changes other gameplay fields and invokes other logic; never replay it merely to create an animation."},
        {"id": "separate-display-amount", "strength": "direct-static-dataflow",
         "detail": "166AA0 passes scratch words +0x20 plus +0x22 to casualty application, but accumulates +0x20 into the target numeric record. Requested loss, actual state difference and display amount must not be assumed equal."},
        {"id": "damage-reaction-bridge", "strength": "direct-static-dataflow",
         "detail": "166AA0 -> 2BA810 resolves army+0x148 runtime, adds 0x580, calls 1B7390 to raise CDamageArmy+0x14. The leaf only compares/writes this presentation state; its later consumers still require audit."},
        {"id": "tactics-casualty-route", "strength": "static-branched-call-path",
         "detail": "CTacticsManager paths 164F60 and 166090 call 16A790; one branch calls 168BA0, which can call the same 16AC60. Not proof that every tactic effect, healing or collateral consequence passes here."},
        {"id": "recurrent-presentation", "strength": "local-static-body",
         "detail": "1B4DD0 revisits retained pair records, creates formation-dependent effects through 336BF0, and can retire/recreate a prior effect. Effect instance count is not authoritative attack count."},
        {"id": "effect-owner-not-callback", "strength": "direct-static-dataflow",
         "detail": "In the inspected constructor/update path, effect+0x28 stores the pair association and 337CF0 compares it before copying geometry. It is not a function pointer at this use. Other callbacks elsewhere remain unproven."},
        {"id": "local-presentation-conditions", "strength": "conditional-branch-verified-setting-meaning-unconfirmed",
         "detail": "F720 -> D390/D140 supplies a local parameter used by effect skip conditions; exact relation to camera zoom/quality has not been verified. Do not use local particle presence/count/finish as authoritative game time."},
        {"id": "tactics-timed-presentation", "strength": "partial-static-audit",
         "detail": "16C2E0 -> 164000 -> 164390 aggregates temporary per-object values and creates effects; 164000 consumes aggregates via 1954C0. Direct inspected bodies do not call 16AC60, but this is not an exhaustive indirect/transitive side-effect proof."},
    ],
    "capture_plan": [
        {"point": "0x1622f0 / 0x1629b0", "purpose": "candidate pair production and selection; copy source/target descriptors before lists mutate"},
        {"point": "0x166aa0", "purpose": "outer combat-pair context: source, target, scratch values and output aggregates"},
        {"point": "0x16ac60", "purpose": "entry/exit requested amount and actual authoritative state changes; include caller and thread; never block here for network"},
        {"point": "0x16a790 / 0x168ba0", "purpose": "tactics context and multiple targets; link nested changes without counting them twice"},
        {"point": "0x162180 / 0x1b09e0 / 0x1b4dd0", "purpose": "presentation batches, pair reuse and source-target identities; do not infer an attack per frame or effect"},
        {"point": "0x16c2e0 / 0x164000", "purpose": "tactics countdown, presentation dispatch and lifecycle"},
        {"point": "0x16bef0", "purpose": "pair retirement boundary; do not retain pool pointers past cleanup"},
    ],
    "replay_design_constraints": [
        "Host emits ordered semantic batches containing typed object IDs + generations, logical state changes, pair relationships, display records and retire markers.",
        "A batch may contain multiple targets, nested tactics, combined numbers and repeated local effects; packet/effect/casualty counts are not interchangeable.",
        "Receiver must not enter candidate-selection/casualty/application routines to obtain visuals. Merely intercepting 16AC60 would leave other rules active.",
        "Apply state and presentation at matching logical time; require complete batches and existing objects. Do not advance through missing data.",
        "Reconstruct process-local native objects/ownership; do not transport pointers, queue nodes or resource handles.",
        "Distinguish viewer-specific display flags from shared world state; 166AA0 compares source faction to current player before setting a numeric-record flag.",
        "Keep local effect/resource cleanup alive without allowing it to author authoritative object death or date progression.",
    ],
    "remaining_gates": [
        "One real encounter trace including a tactic and multiple possible targets.",
        "Gameplay suppression while retaining local presentation, with no additional authoritative state mutations.",
        "Complete mapping of troop loss, recovery, facilities, city/gate damage, status changes, retreat, capture and destruction.",
        "Two real games with different camera/FPS conditions and delayed packets, comparing event identities plus actual images.",
    ],
    "limitations": [
        "Byte checks validate specified instructions, not a complete control flow graph or safe callable API.",
        "No hook, injector, runtime replay adapter or synchronization loop is created or enabled by this script.",
        "Read-only planning snapshot does not demonstrate battle-time order, event frequency, visibility or network timing."
    ]
}
snapshot_path = ROOT / "battlefield-phase2-readonly.json"
if snapshot_path.exists():
    sample = json.loads(snapshot_path.read_text(encoding="utf-8"))
    record["readonly_sample"] = {
        "date": sample["critical_state"]["date"], "player": sample["critical_state"]["player"],
        "state_stack": sample["state_stack"], "active_unit_count": len(sample["all_active_units"]),
        "critical_state_sha256": sample["critical_state_sha256"],
        "scope": sample["scope"]
    }
save = Path(r"C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14")
backup = Path("work/mod_test/replay-checkpoint-34/svdexSC34.s14")
if save.exists() and backup.exists():
    current_hash = hashlib.sha256(save.read_bytes()).hexdigest()
    backup_hash = hashlib.sha256(backup.read_bytes()).hexdigest()
    record["save34_check"] = {"sha256": current_hash, "equals_checkpoint_backup": current_hash == backup_hash}
destination = OUT / "战斗结算与动画边界证据.json"
destination.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"output": str(destination), "anchors_checked": len(checked), "stage_entries_checked": len(stage_entries),
                  "type_checked": type_name, "save34_check": record.get("save34_check"),
                  "dynamic_battle_recorded": False}, ensure_ascii=True))
