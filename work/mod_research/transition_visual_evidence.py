"""Offline audit of archived image, shipped executable and historical trace only."""
from pathlib import Path
from hashlib import sha256
import json, struct, sys

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P / "python_deps"))
import capstone

IMAGE = P / "game-runtime-image.bin"
EXE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Romance_of_the_Three_Kingdoms_14\SAN14PK_SC.exe")
TRACE = P / "startup-switch-traces/20261006-124754-542123/trace.jsonl"
SDK = Path(r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.22621.0")
expected_image = "5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268"
expected_exe = "42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025"
data = IMAGE.read_bytes()
assert sha256(data).hexdigest() == expected_image
assert sha256(EXE.read_bytes()).hexdigest() == expected_exe
dis = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
base = struct.unpack_from("<Q", data, 0x12cd408)[0] - 0x3f69f0

# Assertions are exact code statements. Semantic conclusions below remain scoped.
anchors = [
    (0x3f602f, "call qword ptr [rax]", "User+618 scalar deleting destructor, EDX=1"),
    (0x3f6031, "mov qword ptr [rbx + 0x618], rdi", "User+618 cleared, RDI=0"),
    (0x3f608e, "call qword ptr [rax]", "User+478 scalar deleting destructor, EDX=1"),
    (0x3f6090, "mov qword ptr [rbx + 0x478], rdi", "User+478 cleared"),
    (0x3f5e7a, "call 0xef97b4", "Strategy+480 storage free"),
    (0x3f5e9e, "call qword ptr [rax]", "Strategy+498 deleting destructor"),
    (0x3f5cda, "call qword ptr [rax]", "Game+480 deleting destructor"),
    (0x3f5d1d, "call qword ptr [rax]", "Game+488 deleting destructor"),
    (0x4a2ef5, "mov qword ptr [r15 + 0x4b8], rbx", "Title UI allocated before pending load check"),
    (0x4a3713, "cmp dword ptr [rax + 0x3ec], 0", "Title tests pending slot"),
    (0x4a3721, "call 0x4ceab0", "Title requests native CLoadState"),
    (0x4a3730, "xor edx, edx", "Title widget state argument false"),
    (0x4a3732, "call qword ptr [rax + 0xc0]", "Title widget method resolved to 789E80"),
    (0x789e8c, "and dword ptr [rcx + 0x40], 0xfffffffe", "widget flag bit0 cleared before EDX value applied"),
    (0x665cd0, "mov eax, 1", "Load vtable+20 returns true; not a discovered draw function"),
    (0x665cd5, "ret", "Load vtable+20 leaf ends immediately"),
    (0x4a861f, "jmp 0x4da240", "Load phase1 worker creation"),
    (0x4a8612, "jmp 0x4f7050", "Load phase2 worker polling/join"),
    (0x4a8605, "jmp 0x48aee0", "Load phase3 minimum time gate"),
    (0x4a85f8, "jmp 0x465ab0", "Load phase4 completion"),
    (0x48aef7, "call 0x8351f0", "engine timestamp in milliseconds"),
    (0x48aefc, "sub eax, dword ptr [rdi + 0x474]", "elapsed since state start"),
    (0x48af04, "jbe 0x48af10", "strict elapsed greater than configured seconds*1000"),
    (0x48af06, "mov dword ptr [rdi + 0x470], 4", "time gate to phase4"),
    (0x854c47, "call 0x838350", "D3D11CreateDevice import thunk"),
    (0x854c13, "lea r14, [rdi + 0x3078]", "D3D11 ppDevice target"),
    (0x854c0e, "mov qword ptr [rsp + 0x48], rsi", "D3D11 ppImmediateContext; RSI=renderer+10"),
    (0x84ef52, "lea r9, [rbx + 0x3080]", "CreateSwapChain output"),
    (0x84ef59, "mov rdx, qword ptr [rbx + 0x3078]", "CreateSwapChain input device"),
    (0x84ef90, "call qword ptr [rax + 0x50]", "IDXGIFactory::CreateSwapChain per local SDK"),
    (0x8547e6, "mov rcx, qword ptr [rdi + 0x3080]", "Present target swapchain"),
    (0x8547f8, "xor r8d, r8d", "normal Present flags=0"),
    (0x8547fe, "call qword ptr [rax + 0x40]", "IDXGISwapChain::Present per local SDK"),
    (0x8547e0, "lea r8d, [rdx + 1]", "alternate Present flags=1/test, not frame proof"),
    (0x510655, "lea rax, [rip + 0x1c94]", "window procedure 5122F0"),
    (0x510837, "mov qword ptr [rbx + 0x18], rax", "CreateWindowExA result stored window-manager+18"),
    (0x51234a, "call 0x510be0", "window procedure routes to manager dispatcher"),
]
out = []
for rva, expected, meaning in anchors:
    ins = next(dis.disasm(data[rva:rva+15], rva))
    actual = f"{ins.mnemonic} {ins.op_str}".strip()
    assert actual == expected, (hex(rva), actual, expected)
    out.append({"rva": hex(rva), "bytes": ins.bytes.hex(), "instruction": actual, "meaning": meaning})

trace = [json.loads(line) for line in TRACE.read_text(encoding="utf8").splitlines()]
events = {x["event"]:x for x in trace}
trace_summary = []
for name in ("deserialize_return", "load_worker_result", "title_selection_boundary",
             "native_identity_initializer", "native_identity_return", "strategy_initialize",
             "user_strategy_initialize", "first_user_update"):
    x = events[name]
    trace_summary.append({k:x[k] for k in ("event","seq","tick_ms","player","states") if k in x})
assert [x["seq"] for x in trace_summary] == list(range(1,9))
assert "CLoadState" in events["deserialize_return"]["states"]
assert "CGameState" not in events["deserialize_return"]["states"]
assert "CUserStrategyState" in events["first_user_update"]["states"]
assert events["first_user_update"]["player"] == 2

report = {
    "scope": "Archived image, local executable file, local SDK and old trace only; no game process access or current screenshot.",
    "executable_sha256": expected_exe, "runtime_image_sha256": expected_image,
    "runtime_image_base":hex(base), "version":"1.0.11.0",
    "anchor_count":len(out), "anchors":out,
    "load_minimum_seconds_snapshot":struct.unpack_from("<I",data,0x201ed00)[0],
    "window_class":data[0x12f2e58:].split(b"\0",1)[0].decode("ascii"),
    "title_widget_c0_target":hex(struct.unpack_from("<Q",data,0x12da968+0xc0)[0]-base),
    "historical_trace_sha256":sha256(TRACE.read_bytes()).hexdigest(),
    "historical_trace_sequence":trace_summary,
    "historical_worker_to_first_user_update_ms":events["first_user_update"]["tick_ms"]-events["load_worker_result"]["tick_ms"],
    "historical_timing_limit":"Instrumented identity-switch run only; not a current performance benchmark or presentation timestamp.",
    "sdk_files":{str(SDK/p):sha256((SDK/p).read_bytes()).hexdigest() for p in ("shared/dxgi.h","um/d3d11.h")},
    "known_limitations":["Active renderer/device instance not observed", "No Present return/frame content observation", "No proof of main-menu/black-screen pixels without coverage", "No native input interception implemented", "No load-time optimization established"],
}
(P/"transition_visual_evidence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print(json.dumps({"anchors_pass":len(out),"load_minimum_seconds_snapshot":report["load_minimum_seconds_snapshot"],"historical_sequence_pass":True,"process_access":False}))
