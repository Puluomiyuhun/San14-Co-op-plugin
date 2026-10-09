# 当前交接：另一台电脑的 AI 从这里开始

更新日期：2026-10-09（Asia/Shanghai）。这一页是当前状态；历史里程碑见 [CHANGELOG](CHANGELOG.md)。

## 用户目标和已接受设计

两台 Windows 电脑各运行自己的三国志14，各自操作一个不同势力，其他势力 AI。A 是权威端；指令按序同步，双方准备后推进，旬末 A 新存档校正 B，B 保持自己的视角。暂时接受本地战斗动画有差异，首版窗口/无边框。不要改成远程桌面或共享同一个游戏窗口。异地两台电脑尚未配置正式连接。

用户要求每次有实质进展 commit/push 此仓库，并持续维护本交接文档；允许多 agent 并行。没有要求无人值守后台持续运行，也没有设置定时任务。

## 最新：A已实际生成新文件，但校验拒绝，仍须完成失败收尾

这次已完成此前缺少的typed DLL启动ABI、来源发布器和单次本机启动入口，并在真实游戏中走完安装→自然父初始化→真实IPC Submit→原生Save。**游戏已生成一份独立新文件，但校验失败，不能称A保存验收通过，更不是双机可玩。**

- 原生证据：bind/queue各1次，阶段0–4完整、worker joined、finalizer returned；回到原张鲁203年8月中旬地图，未推进或读档。所有原存档未变，只新增指定独立文件。原文件完整备份在本机。
- 失败定位：Driver `Uncertain/error54`。只读提取保留对象发现Verify停在`context`，原生exists/size/read调用均0；serialized storage gate的下层Owner身份检查拒绝，而不是已观察到文件哈希不同。报告侧已有25次AFTER拒绝并被永久撤销，随后storageOwner拒绝。上游Game gate首错为`Input`；具体哪个最早布局条件失配尚未记录，不能把猜测写成已查清。
- 新工具验证：typed ABI实际导出测试、C++/Python字段布局核对、实际父FINALLY缓存与计数核对；发布器五项自有进程测试通过，包含安装/完整与部分恢复/写失败回滚/活动窗口拒绝。完整生产DLL编译通过。这些测试与上述失败实机分开记账。
- **针对性修复已完成离线验收**：原组合补入“Save已排队但未入栈的Game回调”和“Save覆盖下的User回调”后，精确复现Gate Input→Owner停止→报告撤销→error54。新Gate只接受同代、本Owner、唯一type0队列中的准确Save对象；新Owner只在准确六态自有Save覆盖路径中改用报告字段检查，继续走真实Driver claim和原生返回/FINALLY。正常流程与外来队列、多队列、错代、报告游标漂移共5项通过；正常只有1次Copy/释放，异常无交付。Save业务与covered早退仍是明确替身，不是新实机通过。新生产DLL及原typed ABI完整构建、字段编码核对通过，未注入游戏。
- **当前收尾：已停止IPC，IPC线程已退出，发布器已解除调试；停止状态DLL及7处来源仍保留，saveLane和host lease各为1，不能直接撤回或卸载。已请求用户正常关闭游戏，退出尚待核验。不要读档、推进、重投旧请求、清除once claim或强改终态。**

入口：[单次启动与实际失败](../work/mod_research/a_save_runtime_start_handoff.md)、[覆盖User后继](../work/mod_research/a_save_covered_owner_handoff.md)、[typed ABI](../work/mod_research/a_save_runtime_exports_handoff.md)、[来源发布器](../work/mod_research/a_save_runtime_publish_handoff.md)、[分层证据](evidence/2026-10-09-a-runtime-first-save.json)。私有原始运行`a_save_runtime_live_runs/20261009-123703-876595`，文件与原始对象诊断不进入Git。

下一步先核验旧游戏正常退出，再用新进程检查后继的一次真实新档。原启动器复用；新生产ABI目录是本机`a_save_covered_runtime_runs/20261009-125624-320549/abi`，发布器仍是`a_save_runtime_publish_runs/20261009-123624-806483`。这些是来源定位，不是绕过fresh身份与测试检查的许可；不要复用旧PID/claim。新Gate导出首次失败数据，避免把最早原因覆盖成末尾storage错误。一份新档必须同时通过内容校验和收尾才算关闭第一步。随后仍需A第二次保存、B两合法新档连续加载和同一房间的输入/规则/world衔接。

## 上一轮：A父调用实机观察，修复真实空队列和回调状态，装配本机保存Runtime

用户指出多轮进展仍停留在相同缺口，本轮集中到A真实新档。此前模块与离线测试确实增加，但尚未跨过实际保存/连续加载验收线；不要继续用测试数或百分比代表可玩程度。

- **真实游戏观察**：当前张鲁、203年8月中旬，CApp父调度16帧完整配对；每帧5个状态任务，80次创建和80次尾部配对。父边界的manager.current一直为0，所有已观察尾部均done1/yield0；这次空闲样本不是所有writer排空证明。102线程曾布置硬件观察，退出前仍存活的101线程调试寄存器恢复核对，另1线程已退出；事件排空、调试器退出、后检通过。未推进、保存或加载，无待用户操作，本轮未安装保存Runtime。
- **修复两个实际阻断**：本机命令队列是null/容量0/计数0，冻结旧Inspector会拒绝；新增同ABI后继接受这一个合法空形态，后续分配必须重新采样。另一个问题是父/Game/User回调的current不同，旧fixture一直填User；新增严格作用域认证，只在真实父控制窗口或认证Game桥中接受对应值，不写游戏manager伪装状态。父原函数内部的零状态仍拒绝。
- **接到同一Runtime**：fresh Sampler、Owner、Gate、ParentAdapter和邮箱/IPC配置已实际装配；明确ArmOwner→发布Gate/Parent来源→ArmPublishedSources→等待自然父回调初始化的顺序。全部生产对象编译、完整DLL链接通过，7条既有dllimport/本地定义链接警告保留。没有DLL导出启动ABI、来源发布器或实际游戏执行，不能称可注入运行包。
- **有针对性的验证**：旧Inspector拒绝真实空队列的复现及后继检查通过；Sampler真实读取自有内存的正常/失效情形通过；父Adapter两期旧fixture组合2/2；新增正确current作用域下单期组合1/1及三项拒绝检查通过。新的作用域组合只验证单期，不能借旧两期结果声称已跨旬。源码/产物身份已独立核对；编译失败和修正记录保留。

入口：[本机Runtime](../work/mod_research/a_save_local_runtime_handoff.md)、[父Adapter](../work/mod_research/a_save_parent_adapter_handoff.md)、[采样器](../work/mod_research/a_save_local_binding_handoff.md)、[作用域组合](../work/mod_research/a_save_scoped_input_handoff.md)、[实机父观察](../work/mod_research/a_save_parent_live_handoff.md)。[本轮分层证据](evidence/2026-10-09-a-native-integration.json)包含来源身份、实机/fixture/仅编译的边界。共享34号副本未变。

**下一项明确验收：在真实游戏里由新Runtime生成一份独立新档。** 接手先实现typed DLL导出/启动ABI、可信来源发布和本地单次受控保存入口；复用上述代码，不再另建一组外围模型。重做当前进程/来源预检，在实际父初始化完成后通过真实IPC提交唯一新文件名，检查原生保存收尾、文件内容、原档完整性及退出状态。当前admission仅generation1/cut0/固定本机身份实验，协作producer锁不等于全游戏输入或writer排他，不能作为正式房间许可。

一次真实新档通过后，再做正确父作用域中的第二次保存及B两份合法档连续加载；B真实启动阶段、生产者覆盖与整体规则/输入/world切换仍缺。本轮没有继续扩展B。双机四道结果门槛仍未关闭，见[FIRST_TWO_PC_TEST](FIRST_TWO_PC_TEST.md)。

## 上一轮：A真实保存控制器接管道宿主，B启动接冷等待与两代队列

本轮并行开发、交叉审查，全部离线。没有访问游戏、Steam、当前存档或UI，没有实机补丁、调试器或待用户操作。冻结前驱未改；所有新生成profile、日志与产物留在仓库外。

- **A宿主组合2/2**：真实命名管道和邮箱已接同一Owner/Gate/Controller/Driver。固定宿主在实际Game/User桥FINALLY后封存观察并接纳请求，原User AFTER绑定Save；两期诊断文件完成原存储校验后才Copy/回传，中间实际Retire/Rebind并换Controller。新增Host不安装真实父调用点，保存业务与日期仍是fixture。
- **A断线收尾**：实际Driver已bind/Queued后，客户端只关闭管道并保持进程存活。网络线程停止邮箱，宿主继续原Save/User回调直到原Driver Complete，才在原宿主线程释放协作writer锁；结果仍Unknown，copies=0，无重投。Stop后并非全输入持续暂停。静态审查另修正“Submit返回false可能已经受理”的误解锁路径；这一具体Gate竞态未动态注入，不混称断线测试覆盖。
- **B完整启动组合2/2**：同主PE/DLL/Provider实际完成Bootstrap→冷等待→原RegisterColdPool→两代完整queue。唯一Prepare替代旧Initialize，避免重复初始化。构造主动等初始wait已移除；普通与嵌套yield均完成16个Root任务、48次捕获、两次queue pop与四线程FINALLY。真实游戏来源、早期CRT上下文与全部生产者排他仍缺；登记后SetEvent有明确的fixture服务切换。

A早期编译失败和误用旧故障模式造成的报告漂移失败均保留；后者已用新fixture专用收尾序列消除无关干扰，生产Guard未削弱。两个最终组合均正常收尾，自有子进程/服务/worker/helper退出；共享34号副本未变。

入口与复跑：[A宿主](../work/mod_research/a_save_dispatch_host_handoff.md)、[B冷启动队列](../work/mod_research/b_reload_cold_bootstrap_handoff.md)。证据：[A](evidence/2026-10-09-dispatch-host.json)、[B](evidence/2026-10-09-cold-bootstrap-queue.json)。B的6份额外生成profile已由根agent按固定归档独立重建核对，生产Bootstrap除明确准备接点外与冻结前驱一致。

**下一步按实际缺口推进**：A把本地Host接真实CApp父来源并证明稳定线程/任务收尾及相关writer协调；B证明真实启动时机、线程初始上下文和生产者覆盖，随后用两份合法新档验证连续加载。再把规则撤回/重装、输入、world/地图核验及网络回执合进同一运行所有者。当前未执行真实新档生产或加载，也不是双机可玩闭环；四道实机结果门槛仍见[FIRST_TWO_PC_TEST](FIRST_TWO_PC_TEST.md)。

## 上一轮：A真实管道接邮箱，B冷等待接原注册

本轮全部离线，没有访问游戏、Steam、当前存档或UI，没有新增实机补丁、调试器或待用户操作。旧模块保持冻结；未执行真实游戏保存或读档。

- **A管道组合5/5**：独立客户端子进程通过真实命名管道，向新Server提交两期请求，经邮箱转给固定宿主，再取回两份诊断结果；真实packet编码/哈希和冻结Python解码均通过。请求等待中关闭连接但保持客户端进程存活，或发外部shutdown，都能唤醒等待并保留Cancelled/Unknown，不重投。生产Server保留具体Owner接口；本测试只有Owner三方法和保存业务是替身，没有执行实际Controller/Root/serializer。
- **B原登记组合8/8**：同一主PE/Provider/四线程，实际生命周期Bridge中先冷等待，再调用冻结生产RegisterColdPool一次，由原函数重新验证并登记四worker。修复已发布Leave桥与上一冷等待检查的来源冲突，没有放宽到任意IAT或重置claim。延迟成功、期限、两种来源漂移、提前任务、无owner、两种Stop均核对精确结果。尚未合入远程Bootstrap和完整两代queue，真实生产者排他/早期CRT上下文仍缺。

入口：[A管道组合](../work/mod_research/a_save_dispatch_ipc_handoff.md)、[B原登记组合](../work/mod_research/b_reload_cold_registration_handoff.md)。[分层证据](evidence/2026-10-09-ipc-cold-registration.json)含源码/产物身份及限制。自有服务、monitor、客户端和worker都正常收尾；共享34号副本未变。

下一步：A接真实父宿主和Controller/保存writer协调；B让Bootstrap使用新的准备入口，避免二次Initialize，再接同Provider两代queue。随后验证A两份真实新档与B两份合法档连续加载。四道双机实机结果门槛尚未全部通过，暂不要求用户操作。

## 上一轮：A请求跨线程转交与B冷等待协调

本轮全部离线，没有访问游戏、Steam、当前存档或UI，无实机补丁、调试器或待用户操作。没有生成真实新档，也没有执行真实读档。

- **A保存请求转交7/7**：新增有界邮箱与兼容held IPC Config签名的执行端口。网络侧等待指定宿主明确接纳才返回成功；排队/已领取/已接纳/保存完成/已交付分开，保留两代记录。真实自有线程验证并发去重、错线程、深复制、超时与Stop；未知结果不重投。实际Controller/Root/serializer和整个pipe Server没有执行，断线须由宿主先传播Stop，不能直接替换旧Server就宣称完成。
- **B冷等待协调12/12**：同一主PE四个自有线程执行归档ThreadEntry，通过真实Suspend/GetThreadContext/unwind辨别尚未到初始等待、已到等待与已暖线程。有界等待、事件/线程句柄身份及源码连续复核；成对恢复后在可信producer锁下只调用一次后续入口。生产者锁覆盖和后续RegisterColdPool仍是宿主待接任务；部分服务仍为自有替身，不是游戏冷启动通过。
- **A父层定位4/4**：确认CApp虚表方法里的实际调度call/return和旁路，调用前后仍有其它业务。所有子调用为替身，不能把一次父返回当作子任务完成、稳定控制TID或完整输入暂停。

入口：[A邮箱](../work/mod_research/a_save_dispatch_mailbox_handoff.md)、[B冷等待](../work/mod_research/b_reload_cold_wait_handoff.md)、[A父层](../work/mod_research/a_save_dispatch_parent_handoff.md)。[本轮分层证据](evidence/2026-10-09-dispatch-cold-wait.json)明确区分自有线程、归档执行和实机。

下一步把A邮箱接入已验证来源的单一父宿主及Stop协调、把B冷等待接同一生命周期且证明实际生产者排他；随后验证A两次真实新档和B两合法档连续加载。首个双机目标仍为34号两旬不下新命令，四道实机结果门槛没有全部通过。

## 上一轮：B同一启动环境接两代队列，A补真实User生命周期

本轮全部离线：没有访问游戏、Steam、当前存档或UI，无新增实机补丁、调试器或待用户操作。上次用户保存49号的备份与历史状态见下一节，不能当作本轮新采样。

- **B组合2/2**：同一主PE、DLL、Provider和四个worker，实际Bootstrap后连续执行两代加载队列；正常及嵌套输入yield场景通过。第二代经首代实际Session/Input/Root收尾检查再Register/Open，保留旧回执。修复模块归属、代码页保护、展开表及遗漏的占位worker临界区；失败保留。构造/引擎业务及部分底层fixture宏仍存在，第二文件为诊断变体，不是两份合法新档，也不是全DLL生产路径。
- **A生命周期3/3**：同一User连续两次原生Save push/pop，实际执行User四类生命周期和所覆盖回调容器清除、重建、析构；phase5反例保留phase5。没有执行序列化或写真实存档，不能称完整输入暂停已完成。生产调度要先证明Root父层线程/完成边界，再接邮箱；不能在活动User回调中硬调Controller。
- **冷启动审计2/2**：归档父构造链在显式延迟子线程的服务模型下仍返回成功。构造成功不证明四线程已经到初始等待；不是实机竞态证明，生产初始等待协调仍缺。

复跑与精确限制：[B两代组合](../work/mod_research/b_reload_bootstrap_queue_runtime_handoff.md)、[A生命周期与调度](../work/mod_research/a_save_dispatch_handoff.md)、[冷启动](../work/mod_research/b_reload_cold_start_handoff.md)。公开证据：[B](evidence/2026-10-09-bootstrap-two-generation-queue.json)、[A及冷启动](evidence/2026-10-08-save-lifecycle-cold-start.json)。

下一步优先真实启动来源就绪和冷等待协调、B两份合法档连续加载、A可信Root邮箱和保存写入协调；再合房间/规则换world/完整世界与地图核验。首次双机仍固定34号两旬不下新命令，四道实机结果门槛尚未全部完成。不按归档测试数量推断开发百分比。

## 上一轮：一次真实保存已记录，B 启动接四线程

用户本轮已配合正常保存到49号，无待游戏操作请求。观察器已完整退出、102个线程调试寄存器恢复，后检无调试器；没有新增保存/加载请求或游戏数据写入。原电脑最后核对仍为张鲁、203年8月中旬、可下令大地图；这是当时采样，不能代替后续预检。

- **真实保存一次**：Save入口/返回配对1次，army后台任务0次，记录完整；结论仅是本次未观察到重叠，不能证明所有writer被隔离。83份原存档事先逐份备份校验，保存后只有49号变化，其余82份及34号未变。原49号未恢复，新49号留在游戏目录；备份在本机该次观察目录，不提交其他存档。文件归因来自用户反馈和目录哈希，观察器本身没有捕获文件名。
- **B组合2/2**：同一个主PE、DLL和Provider实际完成Bootstrap、四个冷worker、一次普通无票任务及四个线程正常收尾；真实系统临界区配对。解决主PE展开表与空池零页准备差异，失败记录保留。仍未将两代有票queue接入这个Runtime，也不是两次真实读档。
- **A离线复核4/4**：复用冻结CPU模型核对start/pending/joined/空队列分支；空队列能解释没有后台任务，但不是本次实机原因证明。后续优先可信游戏线程上的正常Save接线及生产者协调，不重复同一种低信息量空闲保存。
- **连接诊断包已生成并自检通过**：可先给朋友验证异地TLS/文件传输，尚未实际连接，也不含原生游戏后端；详见[连接检查](CONNECTION_CHECK.md)。

入口：[真实保存分析](../work/mod_research/a_save_first_live_handoff.md)、[B组合与复跑](../work/mod_research/b_reload_bootstrap_workers_handoff.md)。证据：[保存](evidence/2026-10-08-first-normal-save-live.json)、[B组合](evidence/2026-10-08-bootstrap-workers.json)、[连接包](evidence/2026-10-08-connection-package-prepared.json)。下一步把两代Session/Input/queue放进同一个B Runtime，同时完成A正常保存的可信执行边界；然后用合法新档验证真实连续加载。双机首测四道结果门槛仍未全部通过。

## 共享的34号测试存档

按用户明确要求，原34号档的固定副本已加入 [`fixtures/saves/slot34/`](../fixtures/saves/slot34/README.md)，供其他电脑测试。274920字节，SHA-256 `afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95`，与当前槽位和历史备份逐字节一致；对应历史实机203年8月中旬、张鲁。导入说明与机器可读manifest在同目录。

共享存档那次只读取并复制该存档、修改仓库文档；没有启动或操纵游戏、加载存档、安装补丁或调试器。该副本不包含运行时镜像/profile或旧会话许可；其他电脑仍须重新建立本机运行身份与验证。原档未改，原生开发缺口继续见下文。

## 历史实机里程碑：双人势力规则

**原电脑的双人势力规则实机测试已收尾；用户已恢复34号档，无待操作请求。** 这是历史规则测试状态，不可用来假定新电脑或稍后启动的游戏也在相同状态。

- 实测游戏：`SAN14PK_SC.exe`，SHA256 `42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025`。
- 基线：203年8月中旬，张鲁（force12/ruler666）；第二人类势力刘备（force2/ruler952），主军团分别11和2。
- 在一个真实游戏进程中启用规则，正常推进至8月下旬。两个席位是本机真实 TLS 诊断连接，**不是两个游戏客户端**。
- AI四类入口调用 `[11,14,50,45]`；原生执行 `[10,13,46,43]`；按人类势力绕过 `[1,1,4,2]`。合计120次，绕过8次、原生112次。
- 收入归属判断1044次（人类524、AI520），全部返回。以上不是发钱次数，AI入口次数也不是具体命令数。
- 活动调用、挂起、异常均0。六处来源恢复原指令，安装/恢复各检查102个线程并解除调试器。诊断房间已关闭；DLL保留驻留到游戏退出，不卸载。
- 用户恢复34后：783条样本记录仅53个部队显示对象地址重建，其余已覆盖记录、任务、48400格序列字段及随机状态恢复一致。并非完整世界证明。
- 原34号档未变；正常推进更新了自动存档 `autosdexSC08.s14`。不要声称推进期间所有存档都没变化。

公开摘要：[实机规则验证](evidence/2026-10-08-human-rules.json)。私有原始目录名：`human_rules_activation_live_runs/20261008-001113-003013`，仅在原电脑。不要复制该运行的地址/epoch/claim去另一台电脑。

## 已解决但不能再踩的坑

1. Room 的任一方重新选势力都会清除确认。顺序必须是 A选、B选、A确认、B确认。
2. `world+0x165D` 是官爵派生的数组数量，张鲁2、刘备1均正常，不是空闲布尔标志。`human_rules_activation_v2` 与 `human_rules_activation_publish_v2` 删除了错误的 `==1` 门槛，其余阶段/世界/输入/来源检查保留。
3. live coordinator早期存在日志 `run` 参数名冲突；`human_rules_activation_live_session_v4.py` 是完成本轮测试的后继。但它固定原电脑产物路径，**不可在新电脑直接运行**。
4. `Report.installed=false` 是底层 adapter 未填充的安装标志，不代表来源没安装；这次安装证据是发布器检查六处字节、写入mask63和随后实际调用。
5. 不要把规划输入抑制 wrapper 的返回当成原生 User.Update 执行完成。FreshSave 必须观察真正的原生返回及 FINALLY。
6. 规则绑定当前 world；读档替换 world 之前先撤来源、确认无活动调用，再退休房间。

## 核心主线下一步

优先完成“完整一旬”可测试链路，避免只增加彼此未接通的测试组件。

内政线已经交付[唯一Owner赏赐后继](../work/mod_research/a_reward_save_owner_handoff.md)和[TLS/双日志/独立原生测试端组合](../work/mod_research/reward_room_flow_handoff.md)。不要叠装旧Dispatcher或同时链接两个Owner实现。接下来补真实菜单提交前捕获、可信采样/报告密钥引导、最终Ready输入限制、两个游戏的数值及界面更新；交易/移动只有严格提案预检，原生资格/成本观察与执行仍缺。

`planning_input_interlock` 已联合观察同Owner的User/global UI/panel，新窗口边界进一步覆盖已审计消息集合；未知消息、Root转换、设备缓存、其它消费者和后台writer仍有缺口。新 `planning_period_owner` 在同root/world/User上正式退役旧逻辑期、重绑新期，保留累计序号和历史；B读档换world仍拒绝。赏赐原生确认暂留组件已能在自有归档Update中阻止自然执行并领取一次，但实际安装、正常关闭和可信menu lifetime仍缺。只读[观察工具](../work/mod_research/reward_menu_observation_handoff.md)的自然执行记录仍只能shadow分析，不能转发重做。

**距离首轮双机测试的验收清单：** [FIRST_TWO_PC_TEST](FIRST_TWO_PC_TEST.md)。固定34号起点、张鲁/刘备、两旬不下新命令；还缺A真实两次新档、B真实连续加载、统一运行所有者接通、两机配置四项结果，不按离线用例数量估完成百分比。

1. **A 新存档生产接线。** 新[同world跨期后继](../work/mod_research/planning_period_owner_handoff.md)已将两期赏赐与两诊断保存接在同一物理Owner上，不清零桥/命令/Ready状态；真实日期引擎和合法新档未验证。[upstream门禁](../work/mod_research/a_save_upstream_handoff.md)仍为冻结基线，同Owner两诊断保存29/29。[writer范围审计](../work/mod_research/a_save_writer_scope_handoff.md)已定位Game尾部启动army后台任务及序列化字段交叉。新[原生协调调查和分析器](../work/mod_research/a_save_native_coordination_handoff.md)48/48：找到普通/内联队列生产者，确认16C160含对象清理，不能拿来纯排空；普通Save直接层尚未找到join，间接协调仍未证明。新[单次正常保存观察器](../work/mod_research/a_save_observation_status_handoff.md)39/39已准备，使用四个硬件点配对Save/worker，严格拒绝漏样本、错配及不完整收尾，并保留不属于自己的DR6事件状态。现已取得一次真实保存配对，army任务为0且干净退出；继续核对可信调度与生产者范围，不重复同一种空闲保存；最新[跨旬管道组合](../work/mod_research/a_save_period_ipc_handoff.md)已接实际IPC/TLS两诊断保存；新[父层协调](../work/mod_research/a_save_parent_coordination_handoff.md)11/11执行正常菜单七栈和逐状态Update，仍可到达独立army/Save启动点，OS服务是替身。最新[同进程两期组合](../work/mod_research/a_save_simulation_ipc_handoff.md)已把完整网络Scope、原生日期边界和Session正式换期接保存管道/TLS；日期推进及Save业务仍替身，B loaded仍模型。真实引擎调度、生产发布/permit、对象生命周期及两真实新档仍缺。观察结果不发permit。
2. **B 同进程连续加载两份不同档。** 最新[启动+完整queue组合](../work/mod_research/b_reload_lifecycle_queue_handoff.md)4/4：一次原生四worker初始化、同一已暖worker完成两代16个Root任务/48捕获、两次queue pop及Load/Title start/join；每代一个普通无票任务透明，yield场景两代各一次真实让出/恢复。两旧窗口退休，新代不改旧回执。构造替身仍主动等初始窗口，第二档仍诊断变体。旧[嵌套故障](../work/mod_research/b_reload_fault_handoff.md)30/30及[自动owner单任务故障](../work/mod_research/b_reload_activated_fault_handoff.md)3/3未全量与本次启动组合重跑；最新[启动/故障后继](../work/mod_research/b_reload_lifecycle_fault_handoff.md)3/3已补两代实际观察回调SEH及拒绝下一代的可信本地闸，业务跨Root异常和外来DR仍未合并。旧新进程DLL加载器的marker export已有新[Bootstrap后继](../work/mod_research/b_reload_bootstrap_handoff.md)7/7，实际初始化/发布/Arm；人工自有映像成功，不代表真实运行时来源就绪，后续[同PE四worker组合](../work/mod_research/b_reload_bootstrap_workers_handoff.md)已完成2/2，后续[同PE两代queue组合](../work/mod_research/b_reload_bootstrap_queue_runtime_handoff.md)已完成2/2；真实游戏来源/合法文件/故障矩阵仍缺。此前[B组合审查](../work/mod_research/b_reload_bootstrap_queue_handoff.md)要求同PE/DLL/Provider及真实配对临界区先接四worker，不能直接拼旧私有映像fixture。实际安装、两合法新档、持续排他和世界/地图证明仍缺。
3. **双人规则跨world与准备边界。** `human_rules_world_lifecycle*` 已有六来源恢复/新实例安装顺序；`checkpoint_rules_context*` 已接远端B规则配置及阶段切换，既有 `checkpoint_delivery_control*` 已接上B独立进程经TLS返回实收字节→A实际bytes_received。B日志仍STAGED，无加载INTENT；全量回传会额外增加一次存档大小的传输。Config使用稳定binding_epoch，B不持A的Room对象，正常换代不Revoke/reset旧DLL。下一步在同一可信owner中接B旧规则撤下、持续执行/输入排他、单次加载许可、原生加载及新规则安装，再做完整世界/菜单/地图帧核验和跨机Ready回执。context与observe_loaded都是点检查，不是持续锁或加载完成证明。
4. **收入增加348次的归因。** 历史纯转发测试696次，双人规则测试1044次。两条收入分支没有直接重入判断点；上层预测/结算调度或AI工作量变化尚需证据。最短有用新增记录：逐调用点、势力、日期阶段及父收入计算来源的有界聚合，另做实际数值对照。不要强行把次数改回696，也不要把“无异常”写成“经济正确性完全证明”。
5. **跨电脑启动与连接。** 已有可从干净公开仓库生成的Python源码连接诊断包，支持可选EXE摘要、本机配置、真实TLS和字节校验，详见[连接检查](CONNECTION_CHECK.md)。不依赖原电脑私有catalog/profile；它没有连接原生后端。两台异地电脑尚未配置直连/VPN，真实游戏profile/安装器/A/B整体配置仍缺。首个实机目标保持为两旬不下新命令，再逐项接赏赐、出征与事件暂停。

## 上一轮：完整Scope接同进程两期日期边界和保存

三路并行实现、独立交叉审查；全程离线，未访问游戏、Steam、当前存档或UI，无新增实机补丁、调试器或待用户操作。冻结前驱未改。

- **原生日期边界16/16**：可信同步宿主回调前封存旬初观察，回调返回后核对实际下一旬日期、同root/world和桥收尾；同一epoch/period/serial进入旬末保存状态。旧观察不能保存，新观察后Save/Copy，再正式退休重绑。错线程、过期观察、日期不变/跳旬、SEH、Stop、来源冲突均有实际反例。回调只写自建world日期并调用桥/业务替身，不是游戏战斗推进入口。
- **两期管道组合8/8**：5项协议/身份检查、3项实际管道场景。完整Room Scope通过101字节私有配置进入原生MakeBinding/Session；同一原生进程、Owner、管道完成日1→11与11→21的两份32字节诊断Save，经真实TLS进入各自STAGED日志并重开核字节。第二期仅在模型B loaded产生新epoch后，才执行Session.Retire/PlanNext/Rebind/Adopt。Ready保持，不重启、不重置桥；历史同时保留旬初Scope和旬末Receipt。实际反例拒绝改写旧Scope日期、旧epoch、错房间/cut/跳日期。
- **Session日期解释已接**：明确后继只允许同一成功原生边界解释旬末日期，原始Scope不改；其余Session函数与冻结前驱相同。`native_date_boundary_composed`与`session_next_period_composed`在上述自有进程层为true；真实battle/save/load仍false，B完成仍模型。
- **B组合只读审查**：发现旧queue用私有映像/另一Provider/空临界区函数，与新Bootstrap的主PE/真实系统函数条件冲突。不能硬拼两个测试；下一步先在同PE、同DLL、同Provider内实际Bootstrap→四worker，再接两代queue。未新增B测试通过数，具体位置见[B接线审查](../work/mod_research/b_reload_bootstrap_queue_handoff.md)。

原生首轮9/12的Controller部分请求错误已修；管道首轮7/8是停机异常类型预期过窄，已修测试并验证不重试，失败均保留。88份独立源码和全部声明的生产/fixture产物已统一重核；34号共享副本未变；自建进程、线程和TLS监听正常收尾。保持Ready请求不代表任何错误情况下完整输入隔离，Stop/来源错误的既有转发边界继续明确。

当前入口：[原生边界](../work/mod_research/planning_simulation_boundary_handoff.md)、[Session后继](../work/mod_research/planning_simulation_session_handoff.md)、[同进程两期组合及复跑](../work/mod_research/a_save_simulation_ipc_handoff.md)。[公开分层证据](evidence/2026-10-08-scoped-native-two-period.json)不含私有原始数据。

下一步：真实引擎异步推进/事件栈与边界兼容、正常保存写入协调和合法新档；B同一启动所有者的线程池/连续加载；统一宿主的输入/规则/world/地图核验及双机配置。近期仍是固定34号两旬不下新命令，尚未达到双实机可玩条件，没有待用户操作。

## 上一轮：保持准备状态保存，B 启动接实际初始化

三路并行开发、交叉审查，全部离线；未触碰游戏、Steam、当前存档或 UI，无新增实机补丁、调试器或待用户操作。冻结前驱未改。

- **等待中保存22/22**：新增明确保存入口，不必先解除 Ready。保存完成直到取回结果期间，禁止释放等待、退休期次或绕过专用 Copy；取回仅结束保存预约，仍保持 Ready/Gate。普通 Submit 保持原样拒绝 Ready。修复首轮19/22暴露的观察过期漏洞：只接受真正观察结束时封存的计数，普通 Snapshot 不能把旧观察刷新成许可。范围是可信线程、当前日期和已覆盖入口，不是完整后台写入隔离。
- **保存管道/传输6/6**：3项阶段/身份协议检查，3项实际自有进程管道场景。保存、原生存储读取和 Copy 接真实 TLS/SQLite STAGED，期间 Ready/Gate 未释放；cut 错配和停机不执行保存。诊断存档32字节，B loaded仍为模型。管道由测试进程初始化线程执行，生产游戏线程调度未接。
- **B启动7/7**：新 Bootstrap 导出实际完成生命周期初始化、入口准备/发布和 Arm；核验主线程仍暂停、完整线程枚举、运行时来源、IAT和空线程池。成功路径是人工准备的自有 MEM_IMAGE，来源未就绪、错IAT、已有线程池、多线程和重复启动均拒绝。此组合尚未启动四worker或执行连续加载，不能替代真实游戏运行时就绪阶段的证明。

**新明确的关键缺口：旬初身份与旬末保存日期不同。** 旧管道测试本地原生期次起于第11日，网络期次起于第1日；它证明传输，没有证明推演后的原生日期衔接。新网络接线保留原旬身份，把第11日明确作为保存节点；不能在B加载前提前获得下一旬epoch。当前保存原语仍限当前日期，下一步必须补原生推演结束边界，再把完整Session与它组合。`native_post_simulation_phase_composed=false`继续明确保留。

213份独立源码及全部声明的原生产/测试产物已统一重核，共享34号副本摘要未变。保存首轮失败、B构建/人工页面保护失败均保留；自建进程、线程和TLS监听均收尾。证据：[分层摘要](evidence/2026-10-08-held-save-bootstrap.json)。

入口及复跑：[等待中保存](../work/mod_research/planning_checkpoint_save_handoff.md)、[保存管道与阶段](../work/mod_research/a_save_held_ipc_handoff.md)、[B Bootstrap](../work/mod_research/b_reload_bootstrap_handoff.md)。下一步优先原生旬末阶段/可信宿主与真实保存协调；B将实际Bootstrap接四worker队列并确认真实就绪阶段，然后验证两份合法新档。首测仍是固定34号两旬不下新命令，尚未具备双实机开玩条件。

## 上一轮：跨旬保存接管道，连续加载加故障闸

三路并行开发及交叉审查，全程未触碰游戏/Steam/当前存档/UI，没有新增实机补丁、调试器或待用户操作。冻结前驱保持不变。

- **A跨旬管道8/8**：6项协议反例、2项实际原生管道场景。最新Period Owner/Gate只初始化一次，两次诊断Save、四次存储读，经既有真实管道/TLS进入SQLite STAGED/reopen；中间实际Retire/Rebind，累计赏赐序号与旧回执保留。主动停止后拒绝第二档和旧导出。日期/保存业务是替身，B loaded为模型；本地binding尚未接Session完整网络scope，不宣称真实存档或生产permit。
- **保存父层协调11/11**：正常菜单的归档队列得七层状态，保留Config父菜单；有界CPU执行Root调度、Game/User/Save Update与army待处理队列转移。下层Game仍更新；army未完成时可到独立Save启动点。另有真实状态转换队列变化会中止后续Update的正对照。OS线程服务、容器和UI外围是替身，未运行线程业务或世界序列化，不能断言实机已发生竞态或存档损坏。先用既有四点正常保存观察取得实证，必要时再加配对join/start观察。
- **B连续加载故障3/3**：一次四worker初始化，健康两代完整队列；另外分别在第一代、第二代实际输入观察回调抛SEH，真实VEH捕获/恢复。可信本地AdvanceGate核Provider/Session/Input/Root后才实际Register/Open下一代；故障时两个调用次数都为0，下一代确实不存在，旧代记录不改。故障发生在加载请求提交前，不是完整加载中途所有异常覆盖。冻结Provider直接调用仍可绕过此闸，不能称全局调度锁。

交叉审查补了B闸门必须包含当前代实际Root任务及attempt/epoch来源匹配。两次fixture编译集成失败均保留；首轮执行把成功收尾中的Session.Stop当故障，导致正常/第二代拒绝；已改为检查完整闭代/回执/三join等实际条件，失败运行保留后重跑。227份独立源码摘要与原生产/fixture产物已统一重核，自建进程、线程和TLS监听均收尾；共享34号副本摘要未变。

复跑、精确缺口和原始运行身份：[A管道](../work/mod_research/a_save_period_ipc_handoff.md)、[父层协调](../work/mod_research/a_save_parent_coordination_handoff.md)、[B故障](../work/mod_research/b_reload_lifecycle_fault_handoff.md)。公开[分层证据](evidence/2026-10-08-period-pipe-parent-reload-fault.json)只含摘要/源码身份，不复制私有运行数据。

下一步优先A正常保存最小观察与可信生产permit；B补Bootstrap/发布阶段与合法新档加载，随后接同一运行所有者。先验证单进程连续两档，再安排两个真实游戏两旬。当前没有待用户操作，不能把诊断管道或本地AdvanceGate作为启动历史实机脚本的授权。

## 上一轮：常驻窗口与网络期次接通，菜单收尾定位

三路并行开发和交叉审查，全程未访问游戏/Steam/当前存档/UI，无新增实机补丁或用户操作请求。冻结前驱不变。

- **本地期次映射21/21**：4项协议模型检查、17个自有原生场景。完整房间/稳定绑定/当期128位epoch参与定宽摘要，另映射本地递增编号。调用真实Period退休/重绑与Controller认领，第二期接续累计命令2，旧期/重复/跳号/错world拒绝。Coordinator中的loaded输入是显式模型，不是实机或本轮TLS。
- **驻留窗口10/10**：同一个实际HWND入口贯穿退休、重绑、新Controller观察和窗口Handoff；含实际链接上述Session的一条组合。正常路径只初装一次，窗口保持已审计输入hold，实际窗口消费和FINALLY后才ACK。窗口消息泵暂停时setter和重复请求都不能提前确认。
- **审查修复**：新窗口实现曾在来源检查失败后转发已审计按键，现保留已建立的hold，拒绝ACK/新请求；真实回调来源失效反例确认后续按键仍不进入业务。第三方绕过本入口、初装SetWindowLongPtr竞争、未知消息/设备/Root/后台writer仍不受此保证。
- **菜单收尾59/59**：24归档静态检查、7条实际CPU有界路径，其余为真实TLS/业务模型及只读APPLIED日志关联/拒绝。成功尾部入队的pop没有原菜单身份，消费时再取当前栈顶。换栈顶会触达DifferentMenu清理，重复或延迟pop会触达User；allocator回调仍替身，不声称游戏堆真实释放。未提供自动close API，也不将回执或采样当作持续生命周期锁。

三份最终结果的97份独立源码摘要已统一核对一致，三个原生fixture产物核对通过，仓库共享34号副本摘要不变。自建进程/窗口线程/TLS监听已正常收尾。菜单fixture漏填恢复vtable叶入口造成的失败AV运行已保留，补齐后最终重跑；不会删除失败或把中间窗口8/8当作错误路径持续hold证明。

入口及保留失败：[菜单](../work/mod_research/reward_menu_completion_handoff.md)、[窗口](../work/mod_research/planning_input_resident_handoff.md)、[Session](../work/mod_research/planning_period_session_handoff.md)。公开[证据摘要](evidence/2026-10-08-resident-session-menu-completion.json)分开原生CPU执行、自建窗口、协议/TLS模型与真实游戏。

下一步优先正常保存的最小实机观察及A/B生产宿主接线，再验证两份真实新档与B连续加载。窗口和Session已组合，但不是整条房间/推演/保存/加载链路；菜单完整收尾可留到“不下新命令”首测之后。无待用户操作，不用本轮测试结果启动历史实机脚本。

## 上一轮：确认前暂留、窗口消息边界与同world跨期

三路并行实现并交叉审查；全程不访问游戏/Steam/当前存档/UI，不开启实机记录或安装。冻结前驱不改，诊断业务与真实游戏能力分开。

- **菜单暂留67/67**：32归档静态检查、34个原生自建场景、1条真实TLS组合。145字节真实Update在确认call前转入门禁，纯ID最多领取一次，重复确认不自然赏赐。实际执行布局清理和析构片段后拒绝旧提案。领取结果接CaptureSession与TLS权威去重；双方效果仍业务模型。实际菜单安装、取消输入、正常关闭、多菜单lifetime及可信IPC未完成。
- **同Owner跨期31/31**：旧期退休后旧命令/Ready/Controller被拒绝，新期继续累计编号；两期各一次原生赏赐回放及诊断Save，共四次存储读，旧回执不变。13新场景、16前驱冲突和2持久worker视角。日期转换由fixture写入，同root/world/User；没有战斗引擎、B Load或真实新档。
- **窗口边界6/6、正式跨期组合7/7**：后者为六个窗口回归加一条跨期流程。原生WndProc和真实自建HWND线程处理已审计消息，Post请求只有窗口实际消费后才ACK。固定一次性桥槽保留旧实例，恢复本期原过程后新实例使用新槽；组合会调用真实Period.Retire/Rebind和新的Controller。最终场景与身份见[窗口交接](../work/mod_research/planning_input_boundary_handoff.md)。这不是全部消息覆盖，也没有证明物理按键已松开或OS队列已排空。
- **审查修复**：退休后旧Controller原先可能先释放Gate再被reward lane拒绝，现于所有多步操作前核逻辑绑定/退休状态/Controller身份；反例验证Gate仍held且revision不变。窗口回调改显式正常返回标记，避免将`__try`中的提前return误作异常。
- **审查留下的真实边界**：Win32替换WndProc不是CAS。另一个发布者在检查和替换之间插入，会出现已覆盖外来值才发现冲突；真实自建并发反例验证标记uncertain并拒绝ACK，不补偿覆盖未知链。生产还须实现可信唯一窗口发布者/排他，不能把预先发现外来入口的拒绝测试泛化成无竞争保证。
- 窗口退休顺序为Controller release→窗口release ACK→窗口retire ACK→重新hold/实际观察→Period.Retire。下一期rebind后再显式release和绑定新窗口边界。存在release间隙，**不等于跨期持续全输入暂停**。旧缓存WndProc的直接调用也不属于新窗口来源的完整覆盖。

四份最终结果关联的92份独立源码摘要已统一重核一致，冻结前驱无变，仓库共享34号副本摘要不变。自建进程、窗口线程与TLS监听均已收尾，本轮无新增游戏补丁或调试器。

失败与复跑：[菜单](../work/mod_research/reward_menu_handoff_gate_handoff.md)、[窗口](../work/mod_research/planning_input_boundary_handoff.md)、[跨期](../work/mod_research/planning_period_owner_handoff.md)。公开[证据摘要](evidence/2026-10-08-menu-window-period.json)记录最终来源。下一步仍是生产可信宿主、菜单安全收尾、输入/writer缺口与B换world连续合法新档；用户方便后先做既有只读正常保存/菜单来源观察，不直接把fixture补丁写进游戏。无待用户操作。

## 上一轮：菜单观察工具、扩展输入隔离与两代加载组合

三路并行开发/交叉审查，未访问游戏、Steam、当前存档或UI，无新游戏补丁/调试器；所有自建进程和TLS监听已收尾。原冻结模块不改，后继明确替代链接。

- 输入后继18/18：同一Owner联合请求User fence及Gate Hold，实际观察Game/UI/panel/User；核对精确Owner、当前四个发布槽、世界/日期、版本及FINALLY增量。setter不是观察，缺来源/异常不授予完整输入、保存或推进权限。
- TLS组合13/13（11实际双原生组合+2结构反例）：新端口严格检查扩展观察，旧HMAC协议仍只陈述原User范围；扩展记录保留本地。不将局部mask7/未知mask31升级为全输入暂停。
- B启动/两代queue4/4：源与完整两代加载首次合并，保留原线程池跨测试world；普通任务、地址复用、等待、实际yield/resume通过。不是两份真实新档，也未连A存档/TLS或人类规则换代。
- 菜单观察器60/60：9项自建debugger/退出检查、22项原生读取自有内存的来源情景及其余分析/入口反例；默认帮助且显式PID、已测产物/源码校验。真实菜单记录尚未采集，shadow输出没有可发送packet，不重复执行自然赏赐。
- 交叉审查发现旧观察器退出时只核对断点布局，可能覆盖外来DR6事件位。菜单与正常保存两个新后继共用修复：未知状态不清除、不脱离，记录不完整；旧源码不改。保存后继39/39。共享guard的26个检查分成9次真实OS读回和17个显式CONTEXT模型：本机OS清除了外部写入的事件位，因此不能把模型说成实际触发过BS/BD/BT；两工具各自9个真实debugger场景另通过。
- 交叉审查另明确跨旬缺口：Controller固定日期，赏赐binding不可变；下一期不能复用旧fence或重置旧模块。A真实保存边界仍等待正常保存观察，未假装本轮完成新档生产。
- 最终五份结果关联的243份独立源码摘要统一重核一致，冻结前驱无变；仓库共享34号副本摘要不变。原始失败保留在本机，公开摘要区分实际自建进程、归档代码执行和语义模型。

复跑/失败记录：[输入](../work/mod_research/planning_input_interlock_handoff.md)、[TLS组合](../work/mod_research/reward_interlock_flow_handoff.md)、[B加载](../work/mod_research/b_reload_lifecycle_queue_handoff.md)、[菜单](../work/mod_research/reward_menu_observation_handoff.md)、[保存工具](../work/mod_research/a_save_observation_status_handoff.md)。证据：[脱敏摘要](evidence/2026-10-08-menu-interlock-reload-composition.json)。下一步优先最小正常保存/菜单来源观察，之后实现真实菜单接管、正式跨旬retire/rebind及单游戏连续合法新档；暂无用户操作请求。

## 上一轮开发：双端Owner等待确认与赏赐菜单捕获准备

本轮三路并行开发/审查，冻结前驱不变，未访问游戏、Steam、当前存档或UI，无待用户操作。

- 新原生Ready worker **8/8**：setter ACK明确observed=false；fence_sample当前revision实际经过已发布User入口，Native增量0/0、FINALLY增量1才给observed。保留保存/排队/活动/未知结果/换world冲突拒绝。
- 新Ready组合 **Python19/19、双独立原生fixture11/11**：命令排空→双方Ready→A实际等待观察→B独立观察并签名→A再核验。包含新CaptureSession两视角提案和重复确认经TLS只执行一次的组合。仍全部是自建世界，菜单lifetime/context是fixture，业务效果替身。
- 失败/换实例/断线/退休保持等待，旧期和旧cut失效；未完成的fence请求不自动重试、不会自动解除。修复并发UNKNOWN覆盖、采样中换实例、IPC串配及目录名碰撞；保留失败记录。
- 菜单捕获 **53项语义+16项归档检查**：真实145字节UI Update有界执行（外部callee为替身），确认前候选67A993；包装忽略common返回值、零返回可重复触发，取消路径仍缺。仅生成不可变纯ID提案，未拦截游戏菜单。
- 所有生产Ready/推演/full-world权限保持false。retire只退役控制scope/key，不撤原生规则、不读档。两旬保存/连续加载主线四门槛仍未改变。

复跑与证据：[新组合](../work/mod_research/reward_ready_flow_handoff.md)、[原生worker](../work/mod_research/a_reward_ready_worker_handoff.md)、[菜单捕获](../work/mod_research/reward_menu_capture_handoff.md)、[公开摘要](evidence/2026-10-08-reward-ready-menu.json)。冻结前驱房间21/21、便携协议18项和TLS17项回归通过；环境检查仍缺pefile/便携私有输入配置。

## 上一轮开发：赏赐完整离线接线与交易/移动预检

本轮三路实现与交叉审查，冻结前驱未改；没有访问游戏、Steam、当前存档或UI，无新增游戏补丁/调试器，自建进程与TLS监听均退出。

- 原生Owner **11/11**：赏赐和保存共用唯一User/Save入口，连续两命令、保存/hold/最终Ready互斥、取消/异常/错world拒绝。实际桥/深容器/FINALLY执行，业务效果仍替身。51源码摘要重核无变。
- 房间组合 **21/21 Python故障与流程用例、13/13原生组合用例**：真实loopback TLS、独立B进程及两份日志，A/B共同排序，两边实际新Owner回放后独立观察；重复请求/丢回执不重复扣费，一人Ready不妨碍另一人操作。原生组合使用两个持续自建进程，不是两个游戏。
- 交叉审查修复裸报告伪造、换实例未统一HOLD、重复旧回执误停下一命令。报告验签密钥通过测试本地可信IPC建立，普通房间客户端无法仅靠抄摘要确认执行；真实游戏bootstrap尚未供给此通道。协议seal没有发原生推进许可。
- 交易/移动 **76/76**：严格ID/归属/资源/过期/报价绑定契约，含2项直接组合现有decoder与自有内存。未知价格/资格/耗时不猜测；证据齐全仍仅PRECHECK_ONLY，未接room/native/UI。

分层结果、失败与指纹见[公开证据](evidence/2026-10-08-domestic-offline-integration.json)。复跑：[赏赐组合](../work/mod_research/reward_room_flow_handoff.md)、[原生Owner](../work/mod_research/a_reward_save_owner_handoff.md)、[交易/移动契约](../work/mod_research/domestic_command_contracts_handoff.md)。这些用例不折算完整游戏开发百分比；保存/加载与双机验收四门槛仍保留。

## 前一次盘点：内政覆盖与可并行的离线开发

当时主线程和两名agent分别只读核查命令类别、赏赐执行、房间/日志/准备。确认旧房间与ExecutionJournal都只接赏赐schema；旧固定本机TCP/HMAC实机实验不是现代TLS房间或两游戏复制。当时最新A Owner尚未合入赏赐队列；本轮已新增离线组合后继，实机/UI边界继续保留。

[盘点文档](DOMESTIC_SYNC_STATUS.md)按类别列出实际覆盖，并拆出唯一Owner赏赐接入、TLS/双端回执、通用命令契约、交易/移动、施政/分配、延时事件六个离线工作包。只是待开发清单，不是新增功能。运行便携检查：18项协议/时间线单测、17项本机TLS具名检查通过；pefile缺失、私有输入未配置，原生环境仍未齐备。没有访问游戏、Steam、当前存档或UI，无新补丁/调试器和待用户操作。

来源与本次检查摘要见[证据](evidence/2026-10-08-domestic-sync-audit.json)。下一条内政验收以一次赏赐的完整流程为目标，同时保留保存/加载主线的实机门槛。

## 上一轮：正常保存观察器就绪，B启动时接入来源落地

用户本轮表示暂时不方便操作，继续多agent离线开发和交叉审查。只读进程列表未发现游戏；没有打开游戏进程、访问Steam/当前存档或操作界面，没有新游戏补丁/调试器和待操作请求。冻结前驱未改。

- A观察器34/34：9项真实自建进程调试、12项C++读取自有内存的语义模型、11项日志生命周期模型、JSON残片拒绝及默认帮助。生产版核对本机EXE/原指令和本次身份，只有显式record才附加；不发保存命令。交叉审查补齐清理时排队断点丢样本、异常/退出和计数不符拒绝；无Save的干净超时明确为无结论。下次最小实测是一项正常手动保存，见[操作与退出说明](../work/mod_research/a_save_observation_handoff.md)。
- A原生协调48/48：41个分析器反例/配对模型、6个有界原生片段、1个静态来源检查。定位普通与内联队列来源；16C160会清理对象，不能调用来纯排空。没有证明实际Save/worker重叠、数据竞争、存档损坏或完整排他。
- B生命周期2/2：实际原生初始化循环→四个真实线程初始等待→一次普通任务→同一worker两次被观察任务。构造与调用框架等仍替身；真实初始等待时序及与完整queue/Load/故障组合待验证。另有新进程启动加载器2/2、同二进制10次重复通过；修复调试事件句柄过早关闭导致detach失败。它仍未提供真实游戏Bootstrap和来源发布器。
- 最终171份独立依赖源码指纹统一重核一致；失败与中间记录保留。所有结果均为离线分层证据，不是双人实机通过。下一步A取得正常保存记录，B连接真实运行时可用阶段、Bootstrap及明确的启动发布，再进行单进程两档验证。

复跑和限制：[A原生协调](../work/mod_research/a_save_native_coordination_handoff.md)、[A观察器](../work/mod_research/a_save_observation_handoff.md)、[B启动后继](../work/mod_research/b_reload_lifecycle_handoff.md)。精确结果、产物及源码指纹见[公开摘要](evidence/2026-10-08-native-save-observer-startup-lifecycle.json)。

## 上一轮：自动接入完整加载队列，定位A后台存档字段写入

多agent继续离线开发并交叉审查。本轮未访问游戏、Steam、UI或当前存档目录，无待用户操作；没有新增游戏补丁/调试器，所有冻结生产源保持不变。

- B自动接入与完整queue首次在同一条链里通过，4/4。两代16个Root任务均由同一个真实原生worker自动启停观察，48次Root捕获、8个Load任务；输入观察中的实际暂停恢复没有重复创建任务。构造器/引擎业务仍为替身，仅支持初始wait冷池。
- B嵌套故障30/30（26前驱+4新增）：实际SEH、回调异常、外来DR冲突均有OS级执行证据。之后再接实际自动激活，新增3/3单任务故障组合；外来DR冲突保留子层、Root和自动owner的不确定状态。Observer错误仍属子层，原业务可正常返回；不能把它写成aggregate自动故障。无新授权或Ready。
- A范围审计17/17。warm栈顶检查仅只读，Save覆盖时User原生早退，这个疑点已关闭。Game尾部仍能发布army后台任务，实际路径字段写入与原生序列化相交；定位到start/poll/join和live army来源。尚无原生保存实际并发损坏证据，也没有伪造排空许可；下一步核对原生已有协调，必要时补最小队列保护。
- 失败运行保留，来源摘要在提交前统一重核。这里新增的是组合测试与范围审计，不是生产安装器或实机新档。A真实两次保存、B真实连续加载、统一所有者规则换代/世界地图核验及两机配置仍待验收。

复跑与边界：[A写入范围](../work/mod_research/a_save_writer_scope_handoff.md)、[B完整组合](../work/mod_research/b_reload_activated_queue_handoff.md)、[B嵌套故障](../work/mod_research/b_reload_fault_handoff.md)、[B自动接入故障](../work/mod_research/b_reload_activated_fault_handoff.md)。公开指纹与分层结果见[证据](evidence/2026-10-08-activated-queue-writer-scope.json)。

## 上一轮：A上游保护、B暂停恢复与线程自动接入

多agent实现和交叉审阅。本轮未访问游戏、Steam、UI或当前存档目录，无待用户操作，也没有新增游戏补丁/调试器。共享34副本摘要未变。

- A原生组合29/29，归档审计7/7。User来源提前挡在singleton/updater之前，正常释放恢复原调用链；短收尾与透明尾跳、异常FINALLY、精确prefix归属均有新证据。更早/外部写入仍作为未解决边界保留。
- B暂停恢复26/26。已执行原生yield、事件重置和parent resume；在实际输入观察尚有效时暂停，两代恢复后继续捕获并完成加载组合。修复resume误走fresh creation的问题，同一任务恢复后不会另造ticket。
- B自动激活独立3/3：初始线程等待窗口验证后发布外层PE桥，再由真实原生调用点为每个任务启停Root观察。既有已运行线程池尚不支持此发布方式；这组与完整queue/yield组合尚未合并。全部新结果合并179份独立源码摘要重核一致。其精确最终结果及限制见[B自动接入交接](../work/mod_research/b_reload_root_activation_handoff.md)。
- 所有失败保留。新增公开摘要区分独立activation、两代queue与归档审计，不能把几组结果拼成真实双档或双机已通过；A/B真实新档、统一所有者、排他/规则换代/世界地图核验及异地配置仍待验收。

复跑入口与失败说明：[A上游](../work/mod_research/a_save_upstream_handoff.md)、[B暂停恢复](../work/mod_research/b_reload_yield_handoff.md)、[B自动接入](../work/mod_research/b_reload_root_activation_handoff.md)。汇总见[公开证据](evidence/2026-10-08-upstream-yield-activation.json)。

## 上一轮：A早段门禁接入保存，B真实Root接入两代加载组合

多agent实现并交叉审阅，未访问游戏、Steam、UI或当前存档目录，无待用户操作，无新增游戏补丁/调试器。自有测试进程已结束，冻结前驱未修改。

- A最终25/25。同一report Owner两保存已使用新的早段门禁，报告晚到会保留并在binder前拒绝；User下游报告消费造成的本地ABA已阻断。实际cmp flags、真实AV→FINALLY、逐点unwind和精确两补丁验证通过。更早updater与外部ABA仍以反例证明未完成排他；PASS不能算这些风险已解决。
- B最终24/24。3个完整queue组合每项均经真实Root runner/thunk执行16个generic任务，与输入检查、Load start/join、两代Title同时工作。保留7项独立Root、12项直接Provider、实际parent切代及1项lease契约检查。观察地址/代次/线程错误仍拒绝；不是通过关闭整个Update观察绕开冲突。
- B四轮失败记录保留：首轮20/23暴露User输入观察器同样占DR；接入后21/24暴露OS规范化固定/保留位。增加原始寄存器记录确认后，限定修复新实现的比较规则，地址、使能、类型/长度和事件位仍严格校验。最后24/24，A/B共167份独立源码摘要重核一致。
- 仍未形成实机双档/双机放行入口。下一步补真实Root激活和可达yield/resume、A实际写入边界，再接统一owner的规则换代/世界/地图/Ready。异地配置可按既有连接诊断并行准备；没有要求用户现在重做游戏操作。

结果/产物/源码指纹和失败边界见[公开证据](evidence/2026-10-08-early-gate-nested-observers.json)，复跑见[A交接](../work/mod_research/a_save_early_gate_handoff.md)和[B交接](../work/mod_research/b_reload_nested_handoff.md)。[首测清单](FIRST_TWO_PC_TEST.md)已更新，四道门槛仍以真实结果验收，不按离线测试数折算进度。

## 上一轮：B工作线程真实来源与首测范围收敛

本轮未访问游戏、Steam、UI或当前存档目录，无新增游戏补丁/调试器、无待用户操作。自有测试进程全部退出；没有实机新读档或两个游戏整旬记录。

- 独立Root观察来源已从手工Capture改为归档runner/thunk执行产生的OS CONTEXT。7项新增覆盖正常、连续两个任务、异常、提前停止、错误绑定、代码漂移、切代后旧worker收尾；16项前驱回归同时通过。两个生产实现无fixture宏编译通过，最终源码/私有输入前后摘要一致。
- 首轮19/23，四个负例是fixture错误要求未完成worker清零；按原生yielded行为保留worker，并断言无return/done/completion回执，最终23/23。冻结前驱和生产约束未放宽，失败记录保留。
- 当前是独立Root成果，不是完整Load组合：Root与Load观察器会争用同一线程DR，尚无统一嵌套交接。生产激活、实际yield/resume、持续排他、两份真实档均未完成。下一步先解决该组合，不能把各自通过相加成全链通过。
- [首测范围](FIRST_TWO_PC_TEST.md)收敛为固定双势力、不下新命令的两旬校正；完整内政、事件选择、严格锁步与性能优化可后置。当前没有可承担完整生产链的统一启动入口，四项验收门槛仍在。

详细实现/复跑见[Root交接](../work/mod_research/b_reload_root_worker_handoff.md)，哈希与分层结果见[公开证据](evidence/2026-10-08-root-worker-sources.json)。A和网络沿用前轮成果，本轮没有重新验证或推进它们的生产接线。

## 上一轮：修复B观察代次竞态，定位A更早报告边界

本轮没有访问游戏、Steam、UI或当前存档目录，无待用户操作。原生检查只在自有进程执行已有归档；A审计使用Unicorn与明确模型。没有新的游戏补丁或调试器。

- B原子绑定后继最终16项：3项实际归档queue/两代Title组合、12项直接Provider反例/旧任务兼容、1项实际parent中途切代。错代/错误身份拒绝不污染其他bank；旧worker在真实另一线程返回/done；跨代resume使用确实active/yielded的旧任务并验证合法旧resume仍可成功。实际parent错代捕获拒绝后，经fixture指定异常验证PE FINALLY恢复6DR、active归零。这是错误观察的隔离，不是原生世界写入已经暂停。见[B交接](../work/mod_research/b_reload_bound_handoff.md)。
- A审计16项：3个原始归档基线、7个报告块对照、4个更早User收尾候选、2个纯模型。更早切点保留待办且归档原收尾能恢复所查寄存器/栈，但更早updater和外部生产者反例仍能写入。没有实现桥/发布器或新的Owner组合，完整保存排他仍未完成。见[A边界交接](../work/mod_research/a_save_report_boundary_handoff.md)。
- 保留首次B测试的3个失败：fixture把parent和worker误设同线程，Core正确拒绝，改用真实独立线程而未放宽生产检查。交叉审阅另补强了resume负例，并修正fixture线程等待失败时栈job生命周期。所有最终证据按新源码重新运行。

源码/结果/产物摘要、测试层次和剩余范围见[本轮公开证据](evidence/2026-10-08-bound-provider-report-boundary.json)。网络收件确认沿用上一轮已验证组件，本轮未改网络协议。下一步以真正Root worker来源与A写入排他为主，再连统一owner完成原生load/规则/世界/Ready；仍不能把本轮离线结果当成双机整旬已通过。

## 上一轮：报告感知保存、真实队列收尾与跨机收件确认

本轮未操作游戏、Steam或UI，也未访问当前游戏存档目录，无待用户操作、无新增游戏补丁或调试器。自有测试进程/TLS连接均已收尾。以下均为离线组合验证，**不是两台真实游戏已联机，也不是新的实机读档成功记录**。

- A最终15项通过：报告检查已接同一个实际Owner/Driver/动作桥的两次保存，包含正常保存期间Copy轮询、完成后异常终态、并发初始化只认一个Owner、旧代导出拒绝及不可读页处理。另一个PASS是成功复现仍未修的ABA旁路，不能算排他完成。未切换旧IPC构建，也未重跑IPC/TLS。见[A模块交接](../work/mod_research/a_save_report_handoff.md)。
- B最终3项通过：普通两代、全部地址复用、Title等待。每项实际执行两次type1队列pop及Finalize，检查8次manager当前对象为0，18个有效父scope；2000次空闲调度不耗scope，两个窗口均退休。首次编译因变量遮蔽被/WX拒绝，修正后重跑；并发Provider代次选择仍有源码级缺口，未宣称已测试或修好。Root worker、构造器、分配器和引擎业务仍有明确替身，第二份文件是诊断变体。见[B模块交接](../work/mod_research/b_reload_queue_handoff.md)。
- 网络最终19项通过：5个独立B进程场景用真实回环TLS/SQLite，成功场景下载并重开81959字节，然后经控制连接返回两份文件；A独立receiver核验并真正调用received。并发finish只确认一次；损坏/空日志拒绝；确认成功后丢失真实TLS回复进入HELD，不自动重连重放。B日志保持STAGED，没有加载许可或Ready。见[收件确认交接](../work/mod_research/checkpoint_delivery_control_handoff.md)。
- 交叉审阅修复A的并发claim、旧代游标背书、未捕获内存异常和正常轮询误撤权；网络helper改为从自己的连接创建context，避免错接另一房间后误撤权。B新发现的Provider选择竞态明确保留为下一步门槛；没有放宽旧模块校验来声称链路完成。

精确结果、当前源码与产物哈希、失败记录和范围见[本轮公开证据](evidence/2026-10-08-report-queue-delivery.json)。接手优先顺序：先补B原子代次选择与Root worker，A并行补报告写入排他；再由统一owner连接已完成的网络收件确认、原生加载、规则换代与世界核验。在单游戏进程连续加载两份真实新档之前，不安排双机整旬测试。异地网络诊断仍可独立进行。

## 上一轮：早段写入定位、父调度与远端规则上下文

本轮未操作游戏、Steam或UI，也未读取或改写当前游戏存档目录，无待用户操作。原生测试使用已有私有归档副本和自有进程；回环TLS测试不能替代实机双客户端整旬。

- A归档审计8项通过，确认报告处理位于现有动作拦截点之前，会写World报告索引及报告记录。新增只读guard生产库与14项自有进程检查通过；flag为零但队列仍有内容的反例表明必须同时检查两者。未改Driver、未接permit、没有清空用户待办。见[早段交接](../work/mod_research/a_save_early_handoff.md)。
- B父调度8项通过：普通两代、全部历史地址复用、Title等待、停止/代码漂移/补丁漂移拒绝，以及队列阶段和worker阶段的实际异常展开。移除人工填写父新建/完成上下文，改为归档调度器在CPU上产生的硬件上下文；恢复分支尚未实际覆盖。两代仍有明确的业务/Root worker替身，旧Finalize只在其人工边界组合，不能称真实队列加载已接通。见[父调度交接](../work/mod_research/b_reload_parent_handoff.md)。
- 新规则上下文18项通过：实际独立B进程经TLS获取房间/检查点信息、下载147472字节并写入SQLite，以自身RPM读取自有测试内存。B不接收A的Room对象，检查点日志仍为STAGED，未创建加载许可。错误本方viewer经TLS真正撤掉A下载；原生身份/执行排他仍为明确fixture替身。见[配置接线交接](../work/mod_research/checkpoint_rules_context_handoff.md)。
- 交叉审阅修复了核验context时覆盖故障撤权身份、本机Room/source锁顺序倒置，以及正常阶段变化会误挡旧模块恢复的问题。显式context采用不reset原生模块、不调用loaded、不释放等待；错误房间不会被连带关闭。失败和中间结果都保留。
- B异常测试先暴露自有归档的动态栈展开表区间重叠，两个返回位置查不到scheduler条目，导致异常无法到达FINALLY。改成按函数独立登记并断言查找结果后8项全部通过。Dr6恢复增加事件位漂移拒绝，已独立静态复审，尚无专门漂移运行反例。helper超时后仍等待其退出，不能声称保证超时返回。

精确结果、源码/产物摘要及剩余范围见[本轮公开证据](evidence/2026-10-08-native-boundary-context.json)。下一步先做匹配真实queue阶段的Finalize后继和Root worker来源；A继续补保存全过程的写入排他。再把原生组件、规则换代和网络回执接成同一运行owner，先证明单游戏进程连续加载两份真实新档，再进入双机两旬无新命令测试。没有凭当前离线结果安排用户操作。

## 上一轮：操作隔离、加载来源、规则换代与连接诊断

本轮继续离线开发，未访问游戏或Steam，未安装游戏补丁或操作界面，没有待用户操作请求。自有测试使用归档指令、明确替身业务和新建进程，不视为真实双游戏联机。

- A 后继在清菜单标志/改变推进阶段之前分流raw User动作，保存所需调用仍能返回；源码校验只允许自己明确拥有的两处补丁。18项自有进程检查通过，包含实际异常经过FINALLY、异常展开、早段绕行、晚到菜单/推进请求、来源漂移。另有4条归档路径在Unicorn中通过，分流决策和外部调用仍是模型；不能称为完整游戏执行。仍保留 `fullInputHold/saveAuthorized/roomReady=false`。[模块交接](../work/mod_research/a_save_action_gate_handoff.md)。
- B 已移除fixture中人工+520 Start/Begin/回调上下文，改由实际Finalize槽及归档调用链自动触发；+520/+590两桥均核对精确入口与FINALLY计数，12项整合场景通过。父调度时序和完整业务仍待实机证明。[模块交接](../work/mod_research/b_reload_title520_handoff.md)。
- 双人规则协调12项检查通过，使用同一自有进程的两个独立驻留模块，实际安装/恢复六入口并独立读回；旧模块保留、不卸载、不reset。生命周期接口先传不含地址的加载目标，加载后才由可信reader取得新root/world。错误进入HELD并调用保留等待/撤权端口，端口失败单独暴露；调用方仍须提供真实持续执行排他。[模块交接](../work/mod_research/human_rules_world_lifecycle_handoff.md)。
- 连接包8项检查通过，包含独立搬移目录、隔离Python导入、两个真实TLS进程、版本/指纹拒绝及严格打包白名单。明确只有网络诊断，不发起游戏加载；需要Python和cryptography，不是免运行时EXE。

本轮精确构建/测试、失败记录和源码摘要见[公开证据](evidence/2026-10-08-prerequisite-integration.json)。下一步优先补A早段实际写入与B父调度来源，再把这些原生组件、规则换代和动态Room出口接入一个真实运行所有者；连接诊断可以独立先在另一台电脑进行。

## 上一轮：动态保存与两个原生来源

本轮仍不要求用户操作，未访问游戏、Steam或安装实机钩子。开发与验证只用自有进程、本机TLS和只读私有归档。没有等待用户的操作请求。上一轮的“预先生成packet”限制已在自有A组件中补上，**真实SAN存档和真实B加载仍未验证**。

- `a_save_ipc*`：房间先固定当旬请求，Python经实际Windows命名管道交给同一个常驻A Owner；文件完成后CopyArtifact回传，再由原有Room经TLS发送并写入SQLite。单连接、当前用户SID ACL、拒绝远端管道连接、双方进程身份核对、固定帧/序号/绑定、最多两请求、不自动重连重放。生产组件不包含游戏发现/安装/Ready接口。详见[本机通道交接](../work/mod_research/a_save_ipc_client_handoff.md)。
- 独立审查发现并修复两个实际问题：Stop回执写入管道缓冲后立刻断开会丢失未读部分；完整请求及 `permit` 期间可能发生停止/父进程消失。现在停止后保留有截止时间的只读观察连接，完整frame及permit后重新检查存活/停止。保留首次失败记录，不宣称首次即通过。
- `a_save_input*`：15个自有进程场景通过，含raw User/Save与全局UI抑制同时工作、两次保存、异常/Stop/来源竞争，以及明确的panel绕行反例。19个未覆盖路径的归档锚点已核对；本模块永不授予完整输入锁、保存或Ready权限。见[输入来源交接](../work/mod_research/a_save_input_handoff.md)。
- `b_reload_title590*`：Title.Update作用域内捕获真实线程启动，验证worker尚在原生等待点、事件未发出，再接入自动runner和收尾观察。12个自有进程场景通过，+520、Finalize和父来源仍缺，不能把+590完成扩大成全链路完成。详见[加载来源交接](../work/mod_research/b_reload_title590_handoff.md)。
- 动态保存独立复跑入口：`py -3 tools/check_dynamic_save.py --fixture-root <本机私有研究输入目录>`。只构建新IPC并运行明确的动态流程测试，不导入历史live入口。本轮统一入口构建及12项流程检查PASS、无跳过；汇总 `.local/dynamic-save/20261008-022735-648613/summary.json`。其他两个来源模块用各自交接中的命令。精确运行、结果与源码指纹见[本轮公开摘要](evidence/2026-10-08-dynamic-checkpoint.json)。

**下一项优先任务：** 将A的panel和raw User命令消费纳入可信排他范围，同时推进B +520/Finalize/父来源；已有TLS、存档字节编码和房间绑定继续复用。随后把真实生产配置连起来，在单机先证实两份新档连续加载，再安排两台电脑。模型回执不得作为生产放行证据。

## 上一轮无人操作时完成的接线（历史证据）

用户本轮无法操作电脑。**未访问游戏进程、未操作游戏或Steam、未安装本轮补丁/调试器，没有等待用户的操作请求。** 自有测试进程和本机TLS监听器均已收尾；历史游戏状态仍以重新检查为准。

- 不重做传输层：`checkpoint_room_artifacts.py` / `checkpoint_room_lifecycle.py` 已有独立下载通道、下载票据、跨旬换代与旧连接拒绝；基础 `checkpoint_transfer.py` 顶部“Room无endpoint”不能理解成整个工程都没有。
- 新增[保存字节出口](../work/mod_research/checkpoint_fresh_save_packet_handoff.md)：C++从 `CopyArtifact` 生成明确小端格式，Python严格解码并重新校验摘要和完成报告。编码器生产编译、8项Python测试通过；它不认证来源，也不授予加载/Ready权限。
- 新增[当旬绑定](../work/mod_research/checkpoint_fresh_save_binding_handoff.md)：可信本地层在提交前固定完整scope、当旬epoch、period、命令prefix、attachment、日期，完成后重新核对世界观察再交既有Room发布。**原生room_epoch为稳定Owner标识，不能直接截断每旬变化的协议epoch。** 缺少观察、断线、旧产物冒充新旬、已停止或未完成的保存均拒绝发布。
- TLS整合使用同一自有Owner生成的两份不同packet，验证接收校验、SQLite落盘/重开、房间控制连接保留、第二代拒绝旧下载；绑定及网络共20项测试通过。交叉审查另修复“实际安装后抛错或显式hold，已暴露下载仍可用”的撤权漏洞，新票、旧票和现有下载连接均被拒，清理异常单独报告不虚称已关。世界观察和加载回执明确是模型；packet先在独立fixture生成，**尚未验证真实Room reserve到游戏Submit的动态时序、生产IPC或B原生加载**。详细计数/摘要见[本轮公开证据](evidence/2026-10-08-checkpoint-components.json)。
- 新入口：`py -3 tools/check_checkpoint_components.py --fixture-root <本机私有研究输入目录>`。只运行明确列出的编码器、A Owner、B Title来源和绑定/TLS测试，不导入历史live入口；缺输入或失败不报全链路通过。本轮统一入口四阶段PASS，私有汇总 `.local/checkpoint-components/20261008-015303-908168/summary.json`。用法见[tools/README](../tools/README.md)。协议回归仍是18个unittest、17项TLS检查通过，和原生场景分开统计。

上面的packet预生成限制属于上一轮；本轮动态后继见前节。禁止把旧历史档reader换日期后作为新保存来源。

## 本轮仓库化工作

- 把已有第一方源码按原目录布局迁入仓库。排除游戏/存档/内存dump/原始运行记录/凭据/二进制产物；大段原生生成profile改为本机生成输入，不公开分发。
- 新增 README、AGENTS、设计、本地配置、当前交接及公开验证摘要。
- 换电脑检查入口已完成：`py -3 tools/dev_check.py`。原协议18个unittest通过，原房间自测17项检查通过（真实本机TCP/TLS，两种统计不相加成测试数）。仅复制必要源码到带空格的新目录也通过；无游戏、存档、dump或历史run依赖。默认缺capstone/pefile会准确报告，`--strict-env`可要求依赖/MSVC齐全；环境可用不等于原生编译或实机通过。
- 本轮不需要用户操作游戏；仓库整理及新组件开发不触碰游戏。原始研究目录保留，后续开发以此Git工作区为主。
- 初始基线已推送 `6770aa5`。本轮新增保存组合的13项测试及源码指纹摘要见[保存组件验证](evidence/2026-10-08-fresh-save-session.json)。新增源码和交接会单独提交，实际最新提交请用 `git log -1` 查看，避免文档自引用提交号失真。
- 保存组合已推送 `8f95d05`。从GitHub真实重新克隆该提交到带空格的新目录，再运行 `py -3 tools/dev_check.py`：18个原协议unittest和17项原TLS检查通过；没有私有fixture配置，capstone/pefile缺失被准确报告，未影响纯协议检查。不是另一台物理电脑的实机验证；使用的是相同宿主Python和cryptography。
- 换电脑的明确限制：尝试用磁盘EXE生成保存校验profile，文件SHA虽与支持版本相符，但79个已知范围均与运行时资料不同；两种PE映射算法一致且无重定位覆盖，未放宽校验、未生成错误头。仍需私有运行时生成的 `checkpoint_push_profile.h`，不能把磁盘EXE直接当运行时镜像。没有进行解包或进程提取。

## 接手前五分钟

1. 检查 `git status --short`、`git log -5 --oneline`，fetch后判断是否需要干净工作区的 `pull --ff-only`。
2. 阅读本页和 `AGENTS.md`，用 `tools/README.md` 的检查命令建立本机环境结果。
3. 选择上述一项具体缺口，确认相关源文件及缺少的私有输入；先离线工作。
4. 需要实机时先重新识别进程/版本/阶段，不照抄这页的历史会话状态；准备好工具后再安排必要的用户操作。
5. 本轮结束更新本页和CHANGELOG，写验证和剩余缺口，提交、推送并确认远端SHA。
