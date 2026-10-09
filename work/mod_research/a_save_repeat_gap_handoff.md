# A 单次实机保存之后的跨旬缺口审查

本次仅只读源码/既有归档，未访问游戏、Steam、存档当前目录；没有修改生产代码或运行实机入口。

## 已证范围

`a_save_runtime_live_runs/20261009-230910-151040` 是一次真实自动保存成功。其 mode-zero DLL 来自 `a_save_planning_mode_runs/20261009-230254-218464/candidate/launch`，但内部 Runtime 仍是单期 `a_save_local_runtime`。真实调用、文件和清理由该运行的 `independent-audit/result.json` 独立核验，SHA256 `863debe44b7278833174b9e5b48866f315d9e9977d98528595cdfe4969b90f3f`。

不能把这份成功解释为重复保存已实测。主线下一次 B 测试若使用此新 A 自动档和以前手动保存的 49 号档，第二份仍必须标为手动旧档，不能计作 A 第二代自动产物。

## 不是仅仅移除 launcher 的 Stop

- `a_save_diagnostic_start.py::execute` 只创建 generation 1 请求，取得 artifact 后主动停止管道，并在 finally 调用 Runtime Stop 和发布器恢复。
- 更直接的生产限制在 `a_save_local_runtime.cpp::Runtime::permit`：硬要求 `q.generation == 1`，请求 period 和日期必须等初始配置。`identity()` 同样固定首期日期；类只有初始 `controller_`，无 RequestNext。
- 当前 `a_save_abort_runtime_exports.cpp` 是旧 1–8 typed ABI，没有 RequestNext / RepeatSnapshot 导出。单纯给现有 pipe 再发 generation 2 会被 permit 拒绝。
- 完成后 `a_save_abort_host.cpp::Host::AfterFrame` 留在 Complete；只有 `Host::BindPeriod` 在同一原宿主线程、无 frame/lease、实际新期 Controller 和 period serial 验证通过后，才回到 Idle。
- 本次成功实例已经 Stop 并恢复入口。Stop、mailbox 和 Driver 标志是终态；不能把这个 retained 实例重新启用或重投一次性 claim。

## 底层已有两代能力，不必重写

`checkpoint_fresh_save.cpp::Driver::Submit` 已保存两份历史，最多接受两代：上次必须 Idle/Complete、未 stopped、无 active；后续 generation 单调增加、period 严格增加、文件名不同，同 room id/native room epoch，cut 不回退。`CopyArtifact` 能按 generation 读取已完成历史。

`a_save_dispatch_mailbox.h/.cpp` 有两条记录。后续 Enqueue 要求上一条 Delivered、generation 增、新 binding、同 room/native epoch、period 不回退；Driver 仍另行要求 period 严格增加。不能绕过 Host 与 Controller，直接利用这两个底层容量。

`planning_checkpoint_save_lifecycle.inc` 已有 `Retire / Rebind / ClaimController`；`a_save_abort_host.cpp::Host::BindPeriod` 已有可信宿主换期入口。退休记录、物理桥计数、Owner、Driver、旧对象继续保留，不清空历史制造新的一代。

## 已搜索并存在的上层接线

已检索 RequestNext、BindPeriod、RetiredWaitingDate、native-turn builder/start/exports 和最新 mode-zero Input 引用。下一步不应另建一个同类 Runtime：

1. `a_save_repeat_runtime.cpp::RequestNext / onRepeatBefore / onRepeatAfter`、`a_save_repeat_exports.cpp`、`a_save_repeat_contract.py` 已实现 typed 9/10 和下一期请求。旧 repeat 的 RetiredWaitingDate 仍维持规划门禁，不能单靠此版让用户自然推进。
2. 更进一步的现成后继是 `a_native_turn_runtime.cpp/.h`、`a_native_turn_parent.cpp`、`a_native_turn_owner.cpp`、`a_native_turn_gate.cpp`、`a_native_turn_control.cpp/.h` 和 `a_native_turn_exports.cpp`。该 exports 已包含正确的新 Runtime 头，避免类布局混用。
3. `a_native_turn_start_control.py::drive` 已通过现有 A pipe 做首份 Submit/Copy，RequestNext 绑定实际首档 SHA；保持同一连接心跳，等 Running 后提示用户正常推进；只在 ReadySecond 后提交 generation 2。
4. `a_native_turn_start.py` 已是受控两保存启动器，要求对应 native-turn 构建、9/10 ABI、启动器测试及严格 repeat 发布器。不是把单次启动器 DLL 路径换掉即可，也不能省掉 Running 的恢复门槛。

原生 turn 的具体生命周期已写成代码：首档真实 Delivered/Owner artifact SHA → 原父 BEFORE/AFTER 观察 → 同 TID Retire → Running 下原 User/Game 透明转发、父回调跳过旧规划五态检查 → 自然日期到下一旬 → 新读取五态地址/vtable/任务/队列、fresh Inspector 与安静报告 → 新 sampler/Guard → Rebind、第二 Controller Initialize、Host BindPeriod → ReadySecond。旧 User/Strategy 可以离栈，新地址重新读取，代码不写日期、不调用 autosave 伪装推演。

这些 native-turn 组合已有自有进程两保存和 Stop-running 反例；生产 DLL 与 ABI也曾构建通过，但没有这一整条真实游戏推演后的第二档实测。Running 中 Stop 保持透明/未决，不承诺可以立即恢复入口。

## 最小下一实现范围

当前 native-turn builder 仍继承 `a_save_scoped_input.cpp` 的末尾 cache mode 1 检查。最新 `a_save_planning_mode_input.cpp` 只接到单期 mode-zero 构建；搜索未发现已经把它接进 native-turn 生产组合的后继。因此直接运行旧 native-turn DLL 会保留今天刚定位的初始化拒绝条件。

最小可做的是新的窄构建/测试后继，复用全部上述 native-turn 生产模块：

- 把 Inspector TU 唯一替换成已经实测的 `a_save_planning_mode_input.cpp`，相关自有 fixture 的真实规划基线同步为 0；继续严格拒绝 mode 1/2 和其他待处理状态。
- 若保留初始化首错诊断，复用 trace Controller/记录器，并对 native-turn Owner 的 lifecycle include 做明确小后继。不能整份改用单期 `a_save_initialize_trace_owner.cpp`，否则丢失 Running/Refresh 行为。
- 保留 native-turn Runtime/exports 配套头、typed 9/10、严格 repeat 发布器恢复检查，以及 Stop 时 lease/frame/drainPending 的限制。复用已有正常换新 User 的两保存、Stop-running 测试和实际 DLL ABI/启动器接口检查，不再创建新的状态机或泛化矩阵。
- 新进程、重新读 34 后才做受控实测：自动保存第一份，达到真实 Running 后由用户不新增命令地推进一旬，关闭普通报告；未知选择暂停人工处理。实际下一旬规划重新绑定通过后，自动生成第二个不同文件。若未决则保留证据，不复用旧 claim/模块重试。

这仍是本机无新命令的两代诊断，不包含 B-loaded 证明、完整世界一致或全引擎输入隔离，也不把两个槽位容量解释为无限连续游戏。
