# 同一驻留窗口桥跨规划期交接 — 2026-10-08

本轮完全离线，只新建 `planning_input_resident.h/.cpp/_fixture.cpp/_test.py` 和本交接。冻结 `planning_input_boundary*`、正式 `planning_period_owner*` / `planning_period_interlock.cpp` 未修改。未查找或打开游戏、Steam、现存 UI、当前存档；未启动实机工具。测试只有自建隐藏 message-only ANSI HWND 与自有线程/进程，已正常退出，无活动调试器或游戏补丁。

## 已接通的具体缺口

前驱正常跨期要先 release 窗口、恢复原 WndProc，再新建窗口桥。本后继只初装一次：旧 Controller 已 hold 且获得真实 Game/User 和窗口 ACK 后，正式 Period.Retire/Rebind 期间保持审计范围消息的物理 `held=true`。新 Controller 绑定同一物理 Owner 的下一逻辑期并获得实际 Game/User 观察，才允许 Handoff；窗口线程处理真实 control 消息并完成 FINALLY 后才 ACK 新期。

全过程无窗口 release、没有恢复/重装 WndProc、没有更换桥槽、没有重置物理 Owner/claims/累计 revision。正常自建场景记录 `publication_writes=1`、`handoffs_accepted=1`、`handoffs_acknowledged=1`。退休与重绑间、新 Controller 观察之前、新期 ACK 之后发送的 Enter 均实际被拦；业务替身 `body_audited=0`。这只消除了**正常同 world 换期路径里已审计窗口消息**的释放间隙，不是完整输入暂停。

## API / 线程和身份

命名空间 `planning_input_resident`，类 `Boundary`：

- `Initialize(Config{controller, owner, binding, base, window})`：只在该 HWND 线程调用，完整校验正式 CurrentController/Owner/binding 和前驱原始 WndProc/profile 身份。仍要求初装时 Controller 尚未请求 fence。
- `Request(held, revision, duplicate)`：在既有 Controller 执行线程串行调用；要关闭时必须已有该 revision 的实际 Game/User 7/31 观察。显式 release API 仍存在，但本轮 Handoff 流程从不调用 release。
- `Handoff(nextController, nextBinding, retiredSerial, revision, duplicate)`：只在 Owner 线程串行调用。必须找到正式 Historical 旧期 receipt，旧 receipt 的 binding/revision 必须与本窗口上一次 ACK 对齐；正式当前 serial 必须是旧 serial+1、period+1，native attempt/attachment/generation 不变。新 Controller 必须是 CurrentController 认领者、为不同对象，并有当前较大 revision 的真实 Game/User 观察。旧绑定/旧 Controller/未退休/未 Rebind/错误日期/未观察/未知来源均拒绝。
- `Snapshot`：初始化后只在 Owner 线程调用。`acknowledged` 是当前 Controller 身份有效的窗口回执；`residentHold` 则是同一物理窗口桥仍保持本地 hold 的瞬时证据。旧 Controller 退休使前者失效，不会隐式释放后者。

Handoff 先验证，再投递 immutable ticket；实际 HWND 回调只转移局部 serial/period/epoch 与 ACK，不取 Controller/Owner/Gate 锁、不调用它们的 API，也不执行任何 SetWindowLongPtr。Owner 线程串行更新 Controller 引用；Snapshot/Request 的错线程检查发生在读取可变 Controller 引用之前。Controller、Boundary、Owner 及桥代码必须驻留，不能释放/卸载；本轮复用同一个桥槽。8 个物理初装槽保持永不复用，正常逻辑换期不多占槽。

在真实自有窗口业务回调中暂停消息泵后投递 Handoff，实测 setter 返回和重复请求都没有提前 ACK；只有解除暂停、实际 control delivery/FINALLY 后才 ACK。重复 pending/completed 请求不再次投递、不增加 handoff 计数；旧 revision、旧 binding 和错线程请求拒绝。

## 正式跨期组合证据

测试链接未修改的 `planning_period_owner.cpp` 和 `planning_period_interlock.cpp`，不是手工编 receipt：旧实际 Controller 的 `Retire` 生成历史记录；fixture 把同一 world 日期从 203-8-11 改为 203-8-21，正式 `Rebind` 变更 period/epoch/digest；新 Controller claim、较大 revision Request、实际 Game/User 回调观察；然后调用 Handoff。

日期变化是明确 fixture 写入，不是真实旬末推演、保存或加载。原始归档 WndProc 5122F0..512368 在真实窗口调用链执行，510BE0 handler 为显式业务替身。没有执行完整游戏 handler。生产无 fixture 宏对象及 library 同时编译。测试沿用私有归档 SHA `5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`，小段 WndProc profile 只生成在忽略的运行目录。

本轮另有 `resident-session` 组合，实际链接 `planning_period_session.cpp`：MakeBinding/Initialize → Session.Retire/PlanNext/Rebind/Adopt → resident.Handoff → 实际窗口 ACK；同一物理 Owner/窗口桥跨过完整本地 scope 映射。Scope 字段是明确 fixture 值，未接 TLS，也不把它等同 root 独立 Python PeriodCoordinator 导出测试。

## 保留的限制

初装 SetWindowLongPtr 仍无 CAS；必须由可信唯一 publisher 在正确 GUI 线程安排，生产 bootstrap/发布排他尚未实现。此后继继续实际运行初装竞争反例：在 identity 与 Set 之间自有另一线程先发布 foreign WndProc；后续冲突报告 `publicationConflict/foreignSourceMayHaveBeenReplaced/uncertain`，无 ACK，不做危险补偿恢复。这证明已知限制，不证明消除了外来覆盖。

换期不再调用 Set，因此新增 Handoff 不产生前驱的退休/重装写入窗口。但任何第三方后续更改 WndProc 仍会失去窗口控制；遇到未知来源 Handoff 拒绝且不覆盖，Snapshot 不保留物理 hold/ACK 证明。未排除检查后发生的外来 writer，并未证明外部并发排他。

未知窗口消息、Root 转换、设备缓存/轮询、其他消费者、后台 writer、物理按键释放、完整 OS 队列排空仍缺。前驱 7/31 覆盖数不变。`fullWindowInputHeld/allInputHeld/physicalReleaseProven/osQueueDrained/roomReady/saveAuthorized/nativeGameplayEnabled` 全为 false。window residentHold 只是该瞬时、指定窗口、已审计消息的来源证明；不能用它发保存/推演许可。

没有 cross-world/B加载交接、网络/IPC host、完整原生异常跨 WndProc unwind、新用户菜单或奖励业务测试。保留的 Controller 引用已与可信本地 Session 实现组合，尚未接线上房间。

主 agent 复审发现初版 callback 的 `held && error==None` 会在错误后主动放行审计输入，虽初版8项通过但缺该反例。最终版已修正：错误撤销 ACK/coverage/新请求，不清除已建立的 held，回调对本 HWND 的已审计输入继续拦截。新增 `resident-callback-source` 保持真实本桥 WndProc，改变 engine HWND 来源，实际 SendMessage 触发 Identity/uncertain；该次及后续 Enter 均未进入业务替身、无 ACK/coverage。它证明自身错误不会主动放行，不证明被第三方绕过本桥时仍可拦截，也不是实际 SEH unwind 测试。

## 最终运行

`planning_input_resident_runs/20261008-213605-310761/result.json`：**10/10 PASS**，61 个源码 SHA 再次核对无变。用例：正常两期、错误 binding、旧 Controller、未退休、错误日期、未知 WndProc、缺新 Controller 观察、初装竞争、真实回调来源失败后仍拦截、本地 Session 映射组合。各进程最后 active=0，正常关闭；正常例及 Session 组合各产生一份 handoff ACK，其余无新 handoff。

- result SHA `b27cd5c506735fe9701d14f41152f61432cc17ebfb005c745dd27e12926627f0`
- fixture SHA `0229db6445ac55272a9b7700204721bb0122cb3f3b0a9903e6c63677e528a2b9`
- production library SHA `1cfbcfa2fa16a88a33afed22d7256c09a31f6e0d90edcbd5785b26325d56835c`

本轮没有失败编译/失败测试，但有上述源码复审发现的真实遗漏。`212744-269984` 和 `212953-443690` 都是修复该遗漏前的8/8，不能作为最终错误后持续拦截证据。`213430-446104` 是补真实回调反例后的9/9；最后加 Session 组合重跑10/10。所有中间记录保留。前驱已记录的编译/AbnormalTermination 失败仍归前驱 handoff，未隐藏或重写。

## 复跑与下一步

仓库根目录：

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机私有归档目录>'
py -3 work/mod_research/planning_input_resident_test.py
```

下一步可将已组合的可信本地 Session/Controller 引用与受控宿主接线，保留 HWND ACK 前不可用的状态；仍需真正 GUI bootstrap/唯一 publisher、剩余输入消费者和 cross-world 生命周期。当前没有待用户操作，也不授予运行实机工具的新增入口。
