# 首轮双实机测试的最小范围与门槛

2026-10-09。本文是首测验收清单，不是实机放行记录；最新进度已纳入一次用户手动保存观察。当前结果以 [HANDOFF](HANDOFF.md) 最新里程碑为准；这里明确首测应完成什么，避免把完整产品的所有功能都堆到首测之前。

## 首测到底测什么

固定支持版本、固定34号起点、A张鲁/B刘备、窗口或无边框。两台电脑各运行自己的游戏，连接同一房间；连续推进两旬，不下新的内政或出征命令。每旬 A 产生新的权威存档，B 在同一个游戏进程中接收、加载、恢复刘备视角并通过既有核验，双方才进入下一旬。

一次性读取旧档成功不满足此目标。需要两份日期正确、真实生成、绑定各自旬次的新档；第二次不能靠重启游戏、删除 once-claim、重置旧模块或复制历史回执完成。若过程中出现需要决策的事件，先停止本次测试并保存证据；首测不自动代选，也不宣称验证过事件同步。

最新离线更新：原生日期边界16/16、同进程两期管道组合8/8。完整Room Scope、Session正式退休重绑已接，两份不同日期诊断数据经真实TLS传输；下一期只在模型B完成后产生。日期/战斗/保存业务仍替身，真实异步引擎、合法新档与B加载未完成。[两期组合](../work/mod_research/a_save_simulation_ipc_handoff.md)；[B同一启动所有者接线](../work/mod_research/b_reload_bootstrap_queue_handoff.md)。

最新接入准备新增[A跨线程邮箱](../work/mod_research/a_save_dispatch_mailbox_handoff.md)和[B冷等待协调](../work/mod_research/b_reload_cold_wait_handoff.md)。它们通过自有线程测试，但尚未接实际父宿主/断线协调及游戏生产者锁，不能将“端口可调用”和“已到初始等待”当成真实保存/加载完成。

本轮进一步接通[A真实管道与邮箱](../work/mod_research/a_save_dispatch_ipc_handoff.md)5/5和[B冷等待到原Register](../work/mod_research/b_reload_cold_registration_handoff.md)8/8。A的Owner/保存业务仍为替身，B还未合入远程Bootstrap/完整queue；这两项是组件接线证据，尚不关闭真实新档与连续加载门槛。

## 还有四道验收门槛

下表是四个可验收的结果，不是四个等量任务，也不是完成百分比。现有组件会复用，不能按测试用例数量推断还需几天。

| 门槛 | 已有基础 | 首测前仍须交付的证据 |
| --- | --- | --- |
| 1. A 每旬真实新档 | 最新Period Owner/Gate已与实际管道/TLS/接收日志组合，两逻辑期/两诊断保存与累计编号保留；上游已知updater受控 | 在真实游戏规划边界执行两次原生保存；由同一所有者控制相关写入与对象生命周期，补其他调用者和外部ABA、真实引擎调度和生产发布/IPC；完整网络scope已在两期诊断组合接入。真实保存后才发布 |
| 2. B 同进程连续两次真实加载 | 四线程启动来源已与完整两代queue/Title/输入/Load/yield合并4/4；实际Bootstrap现已接同PE/DLL/Provider四线程与普通任务2/2；后续两代queue已合入同Runtime（2/2）；真实来源/冷等待和合法档未证 | 补真实运行时代码可用阶段、初始wait时序、Bootstrap/来源发布器及其余故障组合；用两份合法新档验证整个原生生命周期。重复地址、晚回调、错代必须拒绝或正确归入原代 |
| 3. 同一运行所有者接通整条链 | 收件确认到 `bytes_received`、规则跨 world、加载许可/日志/世界/等待的接口已有各自验证 | A/B 本机可信所有者连接实际持续排他、旧六入口撤下、单次加载许可、原生加载、新规则安装、世界/身份/规划地图核验、恢复输入。断线和结果不明保持 HELD，不能凭协议成功自动继续 |
| 4. 两台电脑具备相同可运行配置 | 有不依赖私有归档的连接诊断包；共享34号档已提交 | 两机各自核对版本、运行时 profile、源码和产物身份及本机路径；异地实际 TLS/文件传输通过；在两端保存各自本次运行记录。连接包不是原生安装器 |

第4项的纯网络部分现在即可准备，与前三项并行；原生配置仍依赖前三项的实际产物。正式双机两旬测试应在第2项已完成单游戏进程的连续加载验证之后安排，避免让两个人反复重做尚未接通的底层步骤。

## 为什么还不能把现有入口直接串起来运行

源码中虽然有 `Owner`、`live`、`start`，但没有发现能承担上述完整生产链路的统一启动入口：

- [`checkpoint_persistent_physical_owner.h`](../work/mod_research/checkpoint_persistent_physical_owner.h) 的生产路径保留 bootstrap 转发，`PublishForOfflineExercise` 仅允许自有 fixture 换代；物理入口发布不等于原生加载许可。
- [`checkpoint_session_native_port.py`](../work/mod_research/checkpoint_session_native_port.py) 明确要求外部实现输入、世界和 bootstrap。其冻结生产 profile 仍限定研究过的旧 CC03 文件及日期，不能用放宽哈希的方式支持新旬档。
- [`checkpoint_complete_live_start_v2.py`](../work/mod_research/checkpoint_complete_live_start_v2.py) 是固定文件、固定产物、fresh process 的历史一次性加载实验；有不可重试的 claim，未接动态两旬 Room。
- [`checkpoint_guest_transition.py`](../work/mod_research/checkpoint_guest_transition.py) 的 `NativePort` 是待可信实现的边界。返回一个 `InputHold` 或 `WorldObservation` 数据对象不构成真实暂停或世界完成证明。
- [`checkpoint_delivery_control.py`](../work/mod_research/checkpoint_delivery_control.py) 到真实字节收件确认即止；成功后 B 日志还是 `STAGED`，它刻意没有加载或 Ready 端口。

因此下一步重点是把新原生来源接入一个实际拥有生命周期的生产所有者，不是另加一个把现有模拟回执全部填成 true 的总脚本。

## A 保存边界应收敛到什么程度

新[同world跨期后继](../work/mod_research/planning_period_owner_handoff.md)31项通过，关闭旧逻辑期后才绑定下一旬，已组合两诊断保存；日期仍由fixture写入，不是推演和真实存档验收。

新[跨旬管道组合](../work/mod_research/a_save_period_ipc_handoff.md)8/8，将最新Period Owner、Gate与原IPC正式链接；真实管道提交、双存储读取和TLS/SQLite已接两次诊断保存。停止后不能提交第二次或再导出旧结果。六项为协议反例、两项实际原生管道场景；日期/存档业务和B loaded仍替身/模型，当时完整网络scope的Session尚未合入；后继两期组合已补上，但不能据此放开生产permit。

后续[本地期次映射](../work/mod_research/planning_period_session_handoff.md)21项把完整网络 epoch 与累计 cut 接到正式原生生命周期；[常驻窗口](../work/mod_research/planning_input_resident_handoff.md)10项含同一 Session 的实际组合，跨期不用释放/重装已审计窗口入口。它们缩小了宿主接线缺口，仍不证明完整输入排他、网络生产接线、A新档或B加载。赏赐菜单完整收尾不阻塞“不下新命令”的首测范围。

首测不下新命令，因而**无需先做全内政并发同步**；但游戏自身仍有更新、报告、设备消息和后台工作。[上游门禁](../work/mod_research/a_save_upstream_handoff.md)已经挡住两个已知updater的User来源，原29项组合与7项审计沿用。

最新[writer范围审计](../work/mod_research/a_save_writer_scope_handoff.md)17项通过，明确缩小了范围：warm 509640只是栈顶读取，Save覆盖时User原生早退；Game尾部却仍能启动后台army路径更新，该更新确实改动原生序列化使用的army+48字段。特效节点倒计时尚无权威字段相关证据，不能仅因有写入就扩大成停止全部渲染。

本轮定位了army更新的start/poll/join顺序和保存读取live army指针的来源，没有证明真实线程排空，也没有证明原生保存发生损坏。已发现的root错误字符串锁在主要保存调用返回后才获取，不能拿它当保存区间锁；其他原生协调仍需核对。优先复用真实保存已有的串行化，确需新增保护时才持有对应队列与原生join后的窗口，不能用一个active字段的瞬时值替代排空。

新的[原生协调调查](../work/mod_research/a_save_native_coordination_handoff.md)48/48已找到普通队列生产者与Game初始化的内联生产者，确认16C160还会清理对象，不能把它直接当作Save排空入口。新的[正常保存观察器](../work/mod_research/a_save_observation_status_handoff.md)已完成一次用户手动保存实机记录：Save配对1次、army任务0次，102线程寄存器恢复、干净退出。83份原档备份校验后只改49号，34号未变。本次没有重叠不代表writer全排空；优先分析正常Save可信调度和生产者边界，避免重复相同空闲保存。[实测分析](../work/mod_research/a_save_first_live_handoff.md)。

真正需要的是本次保存区间中，影响权威存档、当旬语义与对象生命周期的写入具有可验证的顺序和所有权。它不必等同于停止所有渲染、音频和无关线程。如果另选原生已串行化的规划/保存边界，需要以新的来源与组合测试证明，并按后继实现更新契约；不能删掉现有 `permit`、报告或身份检查来提前放行。完整产品中任意内政按钮的并发体验可以延后，保存区间本身的一致性不能延后。

## B 还剩哪些替身

最新[自动接入完整队列](../work/mod_research/b_reload_activated_queue_handoff.md)已经将此前两组结果合为一条实际执行链，4项通过。每项两代16个Root任务都在同一个真实原生worker上自动启停观察，完成两次queue pop和Title/Load start/join；输入观察中的实际yield/reset/resume没有重复创建任务。这一条链不再由测试的runState手动Begin Root观察。

仍有明确替身：构造器、线程池选择、callable存储和引擎文件业务；第二输入是诊断变体。自动接入只支持初始wait冷池，不能直接接管已经运行的旧线程池。[启动生命周期后继](../work/mod_research/b_reload_lifecycle_handoff.md)最初2/2只衔接两个任务；最新[启动+完整queue组合](../work/mod_research/b_reload_lifecycle_queue_handoff.md)4/4已将实际1447B6/509580四线程初始化接到两代完整加载，同一已暖worker处理16个Root任务，每代无票普通任务透明。构造替身主动等待初始窗口，真实时序仍未验证。

新进程加载器的旧marker已由实际Bootstrap后继取代；最新[同PE四worker组合](../work/mod_research/b_reload_bootstrap_workers_handoff.md)2/2，实际Initialize/Arm、冷池注册、普通任务和正常收尾共用一个Provider及真实系统临界区。仍为人工准备的主PE，真实游戏来源可用阶段未证明。后续两代有票Session/Input/queue已在此Runtime组合2/2，下一步补真实来源/冷等待及两合法新档；完整世界核验和持续排他仍缺。

[嵌套故障后继](../work/mod_research/b_reload_fault_handoff.md)30项通过，包括4个新故障：输入前后实际SEH、观察回调异常、实际外来DR冲突；冲突后子/Root两层均不覆盖外来寄存器，保持不确定并拒绝后续观察。这4项仍使用fixture激活Root。另有[自动接入故障组合](../work/mod_research/b_reload_activated_fault_handoff.md)3项单任务测试，验证实际owner接到业务异常和外来DR冲突，保留唯一claim及错误；被容纳的Observer错误仍属子层，不冒充aggregate失败。它没有主动调度故障后的第二任务，也没有执行完整queue故障恢复。嵌套Load start/join异常及生产异常唤醒仍需覆盖。

最新[启动/故障组合](../work/mod_research/b_reload_lifecycle_fault_handoff.md)3/3补了一条具体缺口：同一四worker生命周期，两代各自的真实HWBP观察回调SEH均能阻止下一代Register/Open；健康对照完成两代16个Root任务。可信host必须经此本地闸且串行提供真实对象，绕过冻结Provider接口不受保护。异常发生在提交加载请求之前；它没有覆盖Load中途业务异常、外来DR或实际调度全局排他。

## 可以留到首次两旬通过之后

| 可延后的内容 | 首测时的明确边界 |
| --- | --- |
| 全部内政、赏赐、出征等操作同步 | 不下新命令；仍保留已存在任务的游戏正常推演 |
| 严格战斗锁步和逐帧动画一致 | 已接受旬末 A 权威校正；不能省掉校正后的世界核验 |
| 完整事件选择同步 | 意外出现选择事件就停止并记录，不冒充已支持 |
| 任意势力、任意剧本、无限多旬 | 固定张鲁/刘备、已核对版本和起点，只验两旬 |
| 自动重连、崩溃恢复、长期房间 | 失败保持等待并诊断，不自动重试已消费加载 |
| 一键安装、精美房间 UI、带宽和遮罩性能优化 | 可先用明确的测试脚本及现有窗口等待呈现；不能取消既有遮罩/输入/恢复许可要求 |

完整世界核验仍是现有生产放行契约的一部分；783条记录或48,400格的部分一致不能改名成完整世界一致。实际可先安排更窄的单模块实机研究来收集证据，但其结果必须写成模块研究，不能称为本页的双机两旬通过。

## 下一步顺序与通过标准

1. A 正常保存记录已取得，继续补可信执行边界、必要写入协调和 IPC 生产接线；B 同PE Bootstrap已接四worker和两代有票queue，接下来补真实运行时可用阶段、冷等待时序和故障组合；并行准备朋友电脑的 [连接检查](CONNECTION_CHECK.md)。
2. 生成有明确版本与来源的统一原生测试入口，先在单游戏进程完成真实两档的连续加载、规则撤回/重新安装、失败保留和正常退出观察。
3. 接实际远端许可与回执，确认控制器断开时原生等待仍有效，完成世界、双方视角与地图恢复核验，再安排双实机。
4. 两旬的每一旬都记录：日期与 generation、A新档摘要、B接收摘要、唯一加载 attempt/INTENT、旧新 world 规则生命周期、实际加载完成、世界核验、A/B视角与恢复操作。任何缺项不能计作通过。

完成第4步，才能说“首轮双人远端两旬原型通过”。这之后再从赏赐开始逐项增加玩家操作，避免把两旬基础链路与所有游戏功能同时调试。
