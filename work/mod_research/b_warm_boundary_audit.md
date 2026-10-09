# B warm 边界审计：两份合法档的受控诊断与正式暂停分开

审查日期：2026-10-09。基线提交 `35ac375ad619408b5cf19d4a7f2621bca3a5efa0`。
本轮仅静态读取仓库源码；没有访问游戏、Steam、存档或 UI，没有编译、执行、安装、进程发现或新测试。本文件不是执行许可，也没有增加恒 false 的 Boundary 模块或修改冻结接口。

## 结论与首测范围

现有 warm 链已经有实际原生回调身份校验，不需要为“两份合法档、玩家不下新命令”的诊断重建 cold Bootstrap、全引擎锁或完整输入覆盖。可复用的最小链为：同一 User 调用的 BEFORE／原生取命令点／AFTER，之后原生 Menu AFTER 与 Game BEFORE，加载完成后的实际 User AFTER 退休。它们约束这次加载的实际提交与完成位置，不能被描述成贯穿外部规则恢复、加载和规则重装的持续锁。

首测的人为“不下令、不推进、不另读档”约定与上述局部检查可以明确列为受控诊断条件；它不是机器强制禁止输入的证据。全输入暂停未完成不应再次成为这个诊断的新增硬门槛。另一方面，不能把相同约定、重复读到空闲或一个 Python 锁填入现有 `guard_check=lambda: None` / `verify_held=lambda: True`，冒充冻结接口原本要求的持续执行／输入排他。若采用较窄诊断语义，应使用明确后继合同，保留 `input_exclusion_proven=false`，不改旧合同文字来追认测试替身。

## 已存在的可复用执行边界

| 位置 | 实际约束和来源 | 不代表什么 |
| --- | --- | --- |
| 只读安装前采样 | `b_warm_profile_capture.py:129` 要求五个 vtable 槽都是原函数，并记录 formal states/task pointers；重复读取。`:136` 明确 `atomic_snapshot=False`。 | 不是新任务永远不会出现，不是暂停进程，也不是驻留 token。 |
| 同一次原生 User 调用 | `checkpoint_authorized_forward_admission_controller.cpp:51` 绑定调用；`:90` 在真正原函数前启动硬件执行点观察；`:118` 验 `3F9DAF`、同 TID/call/User/attachment 和 DR 恢复；`:149` 在配对 User AFTER 取得唯一 ticket 后走真实 queue。 | provider 是取命令点观察器，不是禁用所有命令的输入 owner。`:159` 和 `:167` 明确 Stop/复查都不是 fence。 |
| Menu AFTER / Game BEFORE | `b_warm_retire_session.cpp:172` 起进行配对，`:184` 提交 Game request；`:207` 观察 Menu 返回。`checkpoint_load_input_boundary.cpp:44` 起核同调用、同 TID、原生返回地址 `50B785`、六态栈、current worker/callable/native thread 和非 current worker 为零。`:97` 起核 `control_pause=1`、`cursor_enabled=0` 及各 pending/input 字段。 | 原生菜单提供本阶段控制暂停，检查证明当时这组值成立；`:151` 明说复读不是锁或全线程快照，头文件 `:50` 的 globalPause/allInput 均 false。 |
| 完成退休 | `b_warm_retire_session.cpp:26` 的 eligible 绑定同 attempt、配对 User AFTER、字节／原生加载／身份／规划 receipts 和活动数；`:215` 起在同 gate 内封存业务准入，再 RestoreAll 六槽。 | 只退休本 bank。不是未来整个游戏仍暂停；旧入口晚到只透明转原函数。唯一匹配 AFTER 错过不能假称后续任意 idle 都能补授权。 |
| 下一 bank | 已有实际 Handover 在首代完整退休且六槽为 originals 后授权新模块，旧 once/Session/profile 不重置。 | 不是另一套全输入锁，不解决两代之间 UI 或规则恢复前后的持续 exclusion。 |
| 规则发布器 | `human_rules_activation_publish.cpp:163` 只在独占初始 CREATE_PROCESS 调试事件中校验身份、线程现场、计数与入口，执行六处发布/恢复；`:184` 起最终 detach。 | 真实暂停仅覆盖该次补丁事务，detach 后已恢复线程；不能把两次 publisher 调用之间称仍被同一暂停持有。不能在持有该事件时远程调用 Prepare/Seal/Load。 |

前述位置可复用于实际诊断，不需要凭冷线程池新建另一个 Root owner。当前生产验收已准确返回 `input_exclusion_proven=false` 和 `scheduler_fence_proven=false`，见 `b_warm_start_acceptance.py:199`；不要为了接 Python callback 改成 true。

## 为什么旧 A 输入 owner 不能直接拿来包住 B

`planning_input_interlock.h:10` 的 `BoundedCoverage` 是 User／GlobalUi／Panel，值 7；`:11` 的 missing 为 WindowMessages／RootConversion／DeviceCaches／ExternalConsumers／BackgroundWriters，值 31。`planning_period_interlock.cpp:63` 的 AuthorizeFullBoundary 始终 false。它不是尚缺一个 Python 包装的全覆盖 provider。

此外有具体来源冲突，而非泛泛“还不安全”：

- A User owner 的槽为 `base+0x12CC4A8+0x28 = base+0x12CC4D0`，原函数 `base+0x3F9B00`，见 `a_save_user_owner.cpp:10`。
- A Game gate 的槽为 `base+0x12CC9B8+0x28 = base+0x12CC9E0`，原函数 `base+0x3F8140`，见 `a_save_upstream_gate.cpp:41`。
- B warm 的同两槽加 Menu／update／worker／Steam read 共六槽，见 `b_warm_profile_owner.cpp:113` 起。配置与发布要求原值，不能在 A 桥外再套一层未知桥，也不能把 A 桥填为 native original 来骗 guard。
- A period Controller 绑定具体 A owner、gate、root/world；`planning_period_interlock.cpp:10` 在 date/viewer 改变后拒绝。B 读档会改变 world 与身份，不能保持旧 Controller 后直接再使用。

`planning_input_boundary.h:3` 明确 WndProc boundary 不是第二个 Game/User Owner，必须在 HWND 自身线程初始化，并要求唯一 WndProc 发布者。它依赖上述 Controller；`:22` 的 fullWindow/allInput/physicalRelease/osQueueDrained 永久 false。`planning_input_resident.h:3` 的 handoff 只是同 world 不同 planning periods，并没有独立 B 世界切换支持。当前 WndProc 消息分类还会转发未审计消息；“已装 WndProc”也不是全设备/所有后台写者覆盖。

## 同一持久 B owner 的具体接缝

现有 Python 接点本身不是实现：

- `RulesWorldCapture._check` 在 `b_warm_rules_capture.py:41` 调 guard，然后核 PID/birth、Room/设置及 world。它没有安装或获取 boundary。
- `WorldLifecycle` 的 `human_rules_world_lifecycle.py:234` 明确要求从 restore 到 rebind 期间持续 exclusion；`:267-307` 多次调用 guard；异常 `:314-320` 调 on_hold 并分别保留 hold_error。若 on_hold 抛错，`phase=HELD` 只是本地流程终态，不证明游戏真的停住。
- `b_warm_projection.py:88` 要求 verify_held() 恰为 True。这是受信本地 callback 的合同，不是自动从 raw sample 算出的结论；partial 世界契约也不赋予输入权限。
- `RulesFactory._identity` 与准备过程还会调用同一个 capture guard。工厂的成功远程 Prepare/Seal 和发布收据只证明相应动作，不能额外证明全程等待。

本机持久 owner 应保留同一个 PID/birth、Room/代际、bank 及规则对象，集中持有上述 callback；不应让网络 JSON 提供任意 callback/token，也不应把“TLS 已收到”当进入游戏的凭据。这是接口的已有前提，不是要求另开发全新授权系统。

## 最小下一步，不再扩外围模型

1. 首测继续采用明确无新命令的两档诊断：复用现有 warm 真实 User/Menu/Game 边界、实际 rules publisher 的短暂停事务、读取器/profile/完成退休检查，并明确 gap 期间由本地操作约定约束。若本轮 persistent owner 仍以现有严格 WorldLifecycle/Projection 接口组装，它必须保留真实 callback 为调用方未提供依赖，不用空函数掩盖；仅能说接口已接，不能说 native hold 已装好。
2. 若要把这个诊断变为可直接执行的窄后继，最少是为本机诊断路径明确写出上述有限合同和状态，不自动开放 Ready 或新的玩家命令；复用同一持续 owner 的身份/错误状态。它不是先实现全引擎锁才能试两个合法档。如何选择该后继由主线负责人决定，本审计不修改冻结接口。
3. 正式可玩的持续暂停真正缺的是 B 自身 warm owner 的 native admission 边界与跨期交接，接入点应是现有认证 User 调用及本 bank Menu/Game 转换，而不是叠加 A owner。范围至少区分：规则 restore 前、warm 首次准入前、正在原生 Load、已完成但规则未 rebind、错误终态；不得阻断完成加载所需的原生回调。需将“新命令禁止”和“允许本次 Load 继续”分开，完成后在实际新 User 身份下交接。现有 Session 的 Stop 只关新业务准入、旧晚到桥继续转原函数，不能拿它当 native input hold。

本轮未找到需要立即改冻结源的新增具体 bug；找到的是旧强合同与窄诊断目标之间的明确接线/表述差异。没有新增代码、fixture 矩阵或更广 Ready 门槛。本文件的源码行是审查版本定位，下面哈希固定其来源；未来后继变动后应按新源码重新核对。

## 审查来源 SHA-256
- `b_warm_profile_capture.py` — `7dac0e85a292cf7aca24fd126dc21bc677810c44733dd18af00ce7ba2a55e3cd`
- `checkpoint_authorized_forward_admission_controller.cpp` — `b9a46a16e5e6e02ca69111591298a8ada8003e725307993dbadf7fb8154aa123`
- `checkpoint_load_input_boundary.h` — `8f777298294db466cfbb65396b3cb503cc0d99197bc26236413db5d771007897`
- `checkpoint_load_input_boundary.cpp` — `b3defafffe9af24dc8dbac6be27df15e2185a618ad8aa696e1081d82bb06a18c`
- `b_warm_retire_session.cpp` — `2b203bfdfebb90033da4fa03552b0948101c834cfe4e813da3420e51f0b4a8d7`
- `b_warm_profile_owner.cpp` — `2d8749c245e9324486b4dd626c2864a283b4883e3195749c26b925208c9f2310`
- `human_rules_activation_publish.cpp` — `019f9ffd8932f9b300c6dd6435f0274abd4d4a73fcc647271e0075bbca75ce52`
- `planning_input_interlock.h` — `b1228ba37df58097cb0d175231d02a0be2992e511cded014859f42584cf44438`
- `planning_period_interlock.cpp` — `898494ad25e24ac964af008d9c48c3fbe76f7470c1371d59cfa6bb8e23022f09`
- `planning_input_boundary.h` — `f246051ad508ac657d715ec11d1c1e4cdd508cfb73f0690006d2372a135e1ecf`
- `planning_input_resident.h` — `b8dc2eafc6232db6987d10e7c1a86a4a7ac51d2c62683a9527ddad820d65d290`
- `a_save_user_owner.cpp` — `f140a79e49d567186dd70d1f26415ee988b27b20d6dccd9b4bfbd618175a5854`
- `a_save_upstream_gate.cpp` — `f3ffb7678596ce4073e271867749f25dadb71a8bd3c50d8568b3d5eaded1f74b`
- `b_warm_rules_capture.py` — `92641c5e5dde826465e198cf21a84e12513791cc851a10318c2780e7459c6b94`
- `human_rules_world_lifecycle.py` — `a89484d2d1b4bf562a02d155a71966d7060bf25d4758297c285bee3e5968bce1`
- `b_warm_projection.py` — `c75de6b32c536a9824bbcea987a2f1197391af7d74ec8e8c760da44c3501a4e6`
- `b_warm_rules_factory.py` — `c48cbd2868cc05b9c1aec1d2e2e987d8528a6e975edad385a9be3f2f9fdf5a10`
- `b_warm_start_acceptance.py` — `2fb3d8ae131228f6635dc161f3417282a3a609d591ee6ed611c8b05f445c8bb0`
