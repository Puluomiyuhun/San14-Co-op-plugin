# Bootstrap 接四 worker / 两代加载：组合审查

2026-10-08。本次是源码及既有私有归档的只读审查，没有新增执行组件或测试通过数。
没有查找或操作游戏、Steam、当前存档、UI，没有启动子进程、加载器、调试器或补丁。
冻结前驱未改；没有待用户操作。

## 结论

可以继续组合，但不能把现有 Bootstrap 测试和 queue 测试直接拼接后称为完成。
两者对映像、Provider、同步原语及准备时机的假设不同。最小有意义的下一步是：
**同一自建 PE、同一个 DLL 所有者和 Provider，实际 Bootstrap 后启动四个 worker，
再由同一个 Provider 驱动两代队列。** 不新增一个只接收“已经启动”布尔值的状态机。

目前 [Bootstrap](b_reload_bootstrap_handoff.md) 的 7/7 与
[lifecycle queue](b_reload_lifecycle_queue_handoff.md) 的 4/4 是两份独立证据。
本审查没有将它们合并为新的成功结果。

## 已定位的具体接线障碍

| 位置 | 当前行为 | 真组合必须满足的条件 |
| --- | --- | --- |
| `b_reload_bootstrap.cpp::entry/sources` | base 必须是当前主 PE；严格要求 MEM_IMAGE，主线程仍停在真实 PE 入口 | 队列使用同一主 PE 的受控区域；不能随后换到另一个 VirtualAlloc 映像 |
| `b_reload_lifecycle_activation.cpp::iatIdentity` | 生产分支要求 MEM_IMAGE/READONLY 与实际系统 LeaveCriticalSection；旧 fixture 分支反而要求 MEM_PRIVATE | Lifecycle/activation/Bootstrap 组合使用生产对象；不能靠宏关闭来源检查 |
| `b_reload_bootstrap_export.cpp` | export 持有其自己的静态 Provider | 后续 Register/Open/OnCreation 必须使用这一个对象；另建 Provider 会被地址身份检查拒绝 |
| `b_reload_lifecycle_fixture.inc::lifecyclePrepare` | 自行 Initialize、写调用点、Arm，然后调用初始化器 | 新 fixture 只能执行 Bootstrap 已发布的调用点；不得第二次 Initialize/Arm，也不得重写已经发布的来源 |
| `checkpoint_task_completion_fixture.cpp::setup` 及生成器 | 合成新 world 时复制整段映像，再按页保留旧 worker 来源 | 主 PE 上禁止照搬整段 memcpy；新代仅更新明确的 fixture 数据和新 world 对象，保留代码/IAT/池/回执 |
| `b_reload_root_worker_fixture.inc::rootPrepareMachine` | 把 EnterCriticalSection 和 LeaveCriticalSection IAT 都设为 `rootSync` 空函数 | 实际系统 Leave 必须配对实际 Enter，且被访问的临界区先真实初始化；不能把旧的全零业务对象交给系统 Leave |
| `b_reload_bootstrap.cpp::Snapshot` | 返回启动结束时封存的 lifecycle/activation 副本 | 后续读取真实 `b_reload_lifecycle::Snapshot` 和 `b_reload_root_activation::Snapshot`；不能用启动快照推断 worker 仍为零或已完成 |

同步原语问题不能只靠修改测试预期解决。只读检查既有归档的 runner/thread-entry，
确认它们实际调用临界区入口，涉及线程管理器、全局任务计数和 worker 完成状态。
旧空函数允许未构造临界区的对象通过，新系统 IAT 会实际访问这些对象。
本次未运行这些归档函数，也没有把静态调用关系当成完整锁顺序证明。

## 建议的最小实施顺序

1. 新建 `b_reload_bootstrap_queue_export.cpp`，作为明确后继；在同一 DLL 内保留
   一个 runtime 所有者，内含 Provider、每代 Session/Input/queue 对象及启动回执。
   export 仍调用现有 `InitializeAndArm(info, runtime.provider)`。把后续可信本地
   注册操作也放在这个所有者中，不导出任意远端指针，不另行链接第二份 Provider
   或 activation 实现。Bootstrap 原 export 留作冻结前驱。
2. 新建独立自有 PE fixture。其人工数据/代码区域与主入口、CRT、PE 头和真实 unwind
   不重叠；准备在 Bootstrap 之前完成，且当时池为空。为所有归档入口登记正确的
   unwind，预置真实临界区及 Enter/Leave IAT。保留来源校验、实际系统 IAT 和真实
   MEM_IMAGE 条件。业务/构造替身仍可保留，但必须逐项标识。
3. 第一项执行验收只做 Bootstrap → 原生初始化调用点 → 四个冷 worker → 一个普通
   无票任务 → 正常停止。主线程真正经过原加载器恢复；Bootstrap 只 Initialize/Arm
   一次，初始化器只进入一次。所有后续数据从实际模块 Snapshot 读取，不能填字段。
   必须证明没有替换 base、重建 Provider、二次写 IAT 或重新发布调用点。
4. 在此同一个所有者中移入现有 queue 的真实 Session/Provider/Register/Open 和
   调用链。优先移植 lifecycle fault 的 `Gate::RegisterAndOpen`，而不是重新采用
   可绕过它的直接下一代注册。保持该 Gate 的可信串行宿主前提，不能称其为全局锁。
   两代都经过真实 Root/Load/Title/queue pop/finalize；每代一个无票普通任务，
   第二代不重置或修改第一代报告。
5. 首批只跑正常和嵌套 input-yield 两项。随后加入第一/第二代观察故障、启动来源
   失配、错 IAT、已有池、重复 Bootstrap、不同 Provider 拒绝。失败保留，禁止
   重置 once-claim、卸载驻留 DLL、静默退回旧测试路径。每个自建子进程独立一次。

建议新文件族为 `b_reload_bootstrap_queue_*`，复用冻结的 loader、Bootstrap core、
lifecycle、activation、Provider/queue 生产源；fixture 生成器只变换新输出，不编辑
旧文件。链接清单只能包含 `b_reload_lifecycle_activation.cpp` 这一个 activation
实现，不能同时链接旧 `b_reload_root_activation.cpp`；Provider 后继同样只选一个。

现有可复用代码位置：

- `b_reload_bootstrap_test.py::main`：真实 loader/PE/DLL 构建与启动反例。
- `b_reload_lifecycle_queue_test.py::fixture_sources`：两代页面/普通任务保留逻辑，
  需要改为主 PE 明确区域初始化，不能原样运行整映像复制。
- `b_reload_lifecycle_fixture.inc::lifecycleCtor/lifecycleStopWorkers`：实际线程构造、
  等待和收尾；构造替身主动等待初始窗口的限制继续保留。
- `b_reload_lifecycle_queue_fixture.inc::lifecycleQueueFinish`：16 个任务、48 次捕获、
  两代身份、同 worker、普通任务和四个外层 FINALLY 的实际报告核验。
- `b_reload_lifecycle_fault_guard.cpp::Gate::RegisterAndOpen`：可信宿主下一代门槛。

## 不能被这次组合替代的事实

- **真实来源就绪阶段。** Bootstrap 现在固定在 PE 入口前；历史磁盘/运行时 79 个
  范围不一致。尚不知真游戏何时同时满足“六处归档来源就绪”和“池尚未创建”。
  如果二者无法在该入口前成立，应另做有实证的新生命周期接入阶段，不能允许任意
  时刻来源变好就继续，也不能接管已暖池。
- **真实冷等待时序。** `RegisterColdPool` 立即要求四线程都位于准确初始等待。
  fixture 构造器主动等待；真实构造器没有相同保证的实证。只读识别到构造器下层
  调用，不足以断言它是否在所有时序下等待完成。
- **合法新档与游戏业务。** 合成队列的第二份输入仍是诊断变体；不能作为 A 新档、
  实机连续加载、世界全量一致或地图呈现证据。
- **持续保护与房间。** Bootstrap/queue 组合不等于持续全输入暂停、后台 writer
  排空、旧规则撤回/新规则安装或网络 Ready。存档身份必须来自实际收到的文件，
  加载完成回执来自真实完成链，不可由启动成功生成。
- **容量。** 当前 activation 保留最多 64 个任务，已完成任务不清零。两代各 8 个
  的首测在界限内，但不能据此宣传任意长期连续加载；需要明确容量拒绝和后续有界
  归档设计，不能清旧记录换取继续运行。

## 本次验证与下一步

完成源码逐项对照、生产/fixture 宏及链接清单检查，以及本机既有归档中少量相关
调用点的只读反汇编检查。没有新增二进制、运行结果或通过计数，不复用旧成功作为
新组合证明。没有删除失败运行，也没有操作当前游戏或用户存档。

下一步先实施上述第 1–3 步，再推进同进程两代队列。若只完成第 3 步，准确报告
“真实 Bootstrap 接四 worker”，不要写成“连续加载已接通”。
