# 同一原生 Owner 的规划期退役与重新绑定

2026-10-08。本轮只做离线开发：未发现或打开游戏进程，未访问 Steam、当前存档或游戏界面，无新的游戏补丁、调试器或待用户操作。

## 补上的实际连接

过去 `a_reward_save_owner` 只绑定一次 period/epoch，`planning_input_interlock::Controller` 也只接受 Ready revision 为零的初始状态。这意味着下一旬不能合法沿用这组组件，清零旧模块会丢掉历史与迟到消息保护。

新增 `planning_period_owner.cpp` 显式替代原 Owner 实现，`planning_period_interlock.cpp` 替代原 Controller 实现。头文件/物理桥 ABI 不变；**不可同时链接两份实现**。上游 Game/UI/panel Gate 仍为冻结 `planning_input_interlock_gate.cpp`。

新逻辑保持同一个物理 User/Save Owner、桥银行、输入来源和本地附件：

1. 每个逻辑规划期只能由一个 Controller 认领。新建第二个 Controller 不能重置当期观察。
2. 赏赐排空且本期 Ready 已设置后，还必须实际经过 Game/User 回调，得到局部 UI/panel/User 观察，才能 `Retire`。
3. 退休回执由原生实现内部保存，包含绑定、日期、累计命令编号、Ready revision 与局部观察。退休后旧 `Bind/Submit/ReadyFence/Cancel` 路径不能重新打开该期；User fence 保持关闭，Save admission 也被拒绝。
4. `Rebind` 只接受可信执行线程、精确退休序号、紧接的下一旬、本机同 root/world/User/附件、下一 period、递增的本地 epoch 及新的非零输入摘要。它重新检查真实指针、四个发布槽和当前五层规划栈/phase2，再替换逻辑绑定。
5. 不清零命令序号、Ready revision、错误、物理 claim、存档 Driver 或历史回执。新期仍保持 User fence，必须用新绑定显式释放。旧绑定与旧 Controller 不能继续下令或确认新期。
6. 下一期建立新的 Controller，其初始 revision 从同一个 Owner 的累计值继续；不要求冒充零状态。最多保留 16 份退休回执，达到容量不会覆盖历史。

本地 `ph::Binding.epoch` 是此原生接口的递增整数，不是网络随机十六进制 epoch。正式宿主还需核实网络谱系并建立本地映射；普通房间客户端不能直接填这些配置来取得权限。

已有保存 Driver 的静态 `room_epoch`/附件保持原值，各次保存仍使用独立 generation/period。本后继只更新赏赐与 Controller 的逻辑期；尚未声称网络 period、赏赐 epoch 和保存配置已由一个生产宿主统一映射。

## 重要边界

- **仅同一 root/world/User。** B 真正读档后的对象替换仍拒绝。它没有解除原规则、安装新规则或给原生 Load 发许可。
- 实际门禁采用已有局部观察；窗口消息、设备缓存、其他消费者与后台 writer 仍不是完整覆盖。`Retire/Rebind` 的点检查不是持续执行锁，可信调度器还须保证阶段转换期间的独占调用。
- 生命周期操作只能在已认领的可信线程执行；`sample` 与原 Owner 一样要求只读、不重入，不得回调 Owner/Controller。网络提案不能携带函数或地址。
- 实际宿主必须保留旧 Controller 及物理 Owner 的存活期，尤其不能删除仍被窗口边界引用的对象；没有卸载、析构或回收旧回调的生产 API。
- 退休回执证明逻辑期关闭，不证明已推进战斗或完整世界相等。所有 `fullInputHeld/saveAuthorized/simulationPermit/worldReplacement` 恒为 false。
- 新期的 User 释放不自动改变上游 Gate。测试为了诊断保存继续保持 Gate；真实调度器仍需明确管理“准备、推演、保存、下一期”的各段输入范围。
- 真正保存/推演需要的生产发布器、全输入及 writer 排他、两份真实新档与 A→B 连续加载还未完成。

## 离线验证

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT = '<本机私有归档目录>'
py -3 work/mod_research/planning_period_owner_test.py
```

需要原有私有 `checkpoint_push_profile.h` 和 PlanningHold 库。Runner 只编译与执行自建进程，生产对象使用不含 fixture 宏的独立编译。业务实现、世界内存、日期变化和存档内容是明确测试替身；真实 C++/ASM 桥、深容器、原生存储读取、FINALLY 和唯一 Owner 调用执行。

最终结果：`planning_period_owner_runs/20261008-210101-627017/result.json`，**31/31 PASS**，57 份来源摘要重核一致。

- 16 个已有 input/Ready 来源、日期、线程、排队、Save、异常与世界冲突用例。
- 2 个持久自建进程视角，执行原赏赐/Ready 请求协议。
- 13 个新跨期用例：两期奖励、两期奖励+保存、缺实际观察、重复 Controller、退休旧接口、相同日期、跨过一旬、换 world、错附件绑定、旧退休序号、错线程、缺采样器，以及另一真实线程读取有效 Controller 的只读 Snapshot。
- `period-two-saves` 实际执行两次奖励、两次 Save binder/queue、四次原生存储读，两个不同诊断文件回读；命令序号到 2、Ready revision 到 3、两份退休回执。第一份回执在第二期后逐字节不变。
- 两旬日期由 fixture 显式写入；**没有执行真实战斗日期引擎，也没有 B Load**。不得把两份诊断文件说成 A 已生成合法 SAN14 新档。

失败保留：

1. `20261008-204549-834816`：生产构建冲突，原 Gate 头与 ABI 后继头同时包含；新 Owner 改为只用后继头，旧头不改。
2. `20261008-204605-766271`：生产对象已编译，fixture 的外层 `main` 宏与前驱嵌套宏冲突；只在生成的本地 fixture include 中显式重命名入口。
3. `20261008-204650-726161`：完整 30/30。交叉审查随后发现退休后旧 Controller 可先释放 Gate 再被赏赐 lane 拒绝，不能作为最终版本。
4. 增加 `CurrentController` 在所有多步控制前核精确逻辑绑定、退休状态和 Controller 身份，拒绝后才不会碰 Gate；所有退休场景新增旧 Controller open/close/observe 均拒绝且 Gate 仍 held、revision 不变断言。`20261008-205926-596450` 为修复后 30/30。
5. 为独立窗口线程组合，身份只读检查允许跨线程 Snapshot，变更和领取仍限定原可信线程；新增真实线程场景后 `20261008-210101-627017` 最终 31/31。前两次没有运行测试业务，没有删除失败或中间成功目录。

精确源和产物身份记录在 result.json。原始运行和诊断文件留本机，不提交。

下一步：在同一可信宿主中连接正式阶段切换、网络 epoch→本地绑定映射，以及跨 world 的旧来源撤回/新来源建立；与菜单暂留、窗口消息边界组合后再验收真实两旬。
