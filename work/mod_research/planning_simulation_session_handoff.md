# Session 保留旬初 Scope，接收本期旬末日期

2026-10-08。新增 `planning_simulation_session.cpp`，显式替代冻结
`planning_period_session.cpp`；头文件、类布局、调用 API 不变。只能链接一个实现。
本文件依赖 `planning_simulation_boundary` 的实际保留报告，不能与没有该原生边界的
旧 Owner/Gate/Controller 实现混用。

## 修改原因与行为

旧 `Session::current` 始终要求原生期次日期等于旬初 Scope 日期。因此即使同一
Owner 已完成可信回调、来到旬末并保存，Session 仍不能 Retire/PlanNext。

后继保留原有正常日期路径，只增加一条明确的旬末检查。所有原有已初始化、线程、
退休状态、完整 Binding、无未完成赏赐等条件先通过；然后额外要求：

- 实际边界报告为 `Checkpoint`，报告线程和原生期次线程都等于 Session 线程。
- 边界确实进入并正常返回、执行 FINALLY，累计 entered/returned/finally 数相等。
- 边界仍保持 Ready；起点 Ready revision、命令 cut 等于当前原生报告。
- 起点 Binding 全字段相同，含 native attachment/attempt/generation、period、
  local epoch 和完整房间摘要；起点 serial 相同。
- 起点日期仍为 Session 中保存的旬初日期；边界记录的 checkpointDate 等于原生
  期次日期，且严格为原旬初日期的下一旬。

此分支不改写 Scope，不生成网络 epoch，不建立新许可。`Retire` 仍调用实际原生
退役门槛，因此完成 Save/Copy 前不能退休；历史同时保存旬初 Scope 和旬末 Receipt。
`PlanNext` 保持旧实现：下一 Scope 必须同房间/绑定、下一 period、严格下一旬、
累计 cut 相同，且 timeline epoch 从未使用。`Rebind` 仍重新核对该计划及采样器
身份，并调用原生 Rebind；到达日期的确认由新的边界 Owner 后继负责。

## 拒绝范围审查

- 只改内存日期，没有实际成功边界：报告不是 Checkpoint，拒绝。
- 不同房间/绑定、旧 serial、旧命令 cut、Ready revision 变化：拒绝。
- Running、Failed 或上一期 Rebind 后变回 Idle：不能借用旧 checkpoint 报告。
- 用旬末日期伪造旧 Scope 调 Retire：完整 Scope 比较拒绝；保留的旧 Scope 不改。
- 下一期继续使用旧 timeline epoch、跳期、错日期或错累计 cut：原 PlanNext 拒绝。
- 篡改 Next.binding 后 Rebind：重新生成期望 binding 的原有检查拒绝。
- 任意修改下一期采样回调或 context：原 Rebind 检查拒绝。

快照不是持续调度锁。本地可信宿主必须串行调用这些接口，并由网络协调器确认何时
真的获得下一 Scope；C++ Session 不鉴权远端 JSON。Ready、世界身份和日期的实际
检查仍由 Owner/Gate/Controller 执行。没有增加全输入/后台 writer 排他或真实战斗
推演保证。

## 验证与集成

源码对照确认，冻结前驱未改，除新增边界头文件和 `Session::current` 外，其余实现
保持一致。后继已在 `a_save_simulation_ipc_build.py` 中链接，由实际同一物理 Owner
的两网络期组合验证：完整 Scope 从 Room 传入，旬末 Save/Copy 后等模型 B loaded
生成下一网络 Scope，再执行 Retire/PlanNext/Rebind/Adopt。该组合仍是自有进程、
诊断日期/保存业务和模型 B loaded，不是双游戏或合法新档。

不要给本次静态审查另加测试通过数。具体构建/运行结果以
[原生阶段及管道交接](a_save_simulation_ipc_handoff.md) 中的最终运行记录为准。
本模块开发没有操作游戏、Steam、当前存档或 UI；无待用户操作，也没有新增实机
补丁或调试器。
