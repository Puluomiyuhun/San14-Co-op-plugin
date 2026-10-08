# 当前交接：另一台电脑的 AI 从这里开始

更新日期：2026-10-08（Asia/Shanghai）。这一页是当前状态；历史里程碑见 [CHANGELOG](CHANGELOG.md)。

## 用户目标和已接受设计

两台 Windows 电脑各运行自己的三国志14，各自操作一个不同势力，其他势力 AI。A 是权威端；指令按序同步，双方准备后推进，旬末 A 新存档校正 B，B 保持自己的视角。暂时接受本地战斗动画有差异，首版窗口/无边框。不要改成远程桌面或共享同一个游戏窗口。异地两台电脑尚未配置正式连接。

用户要求每次有实质进展 commit/push 此仓库，并持续维护本交接文档；允许多 agent 并行。没有要求无人值守后台持续运行，也没有设置定时任务。

**本轮用户暂时不方便操作，先继续开发。** 新的单次正常保存观察工具已完成离线验证；尚未启动游戏检查或记录。下次用户方便时，按 [新版观察工具交接](../work/mod_research/a_save_observation_status_handoff.md) 先验证本机构建与只读状态，记录器 READY 后才安排一次保存。新版修复退出时可能清除外来调试事件状态的问题；冻结旧工具仅留作历史。没有当前待操作请求。

最新按用户要求三路并行开发内政：新赏赐队列合入同一User/Save Owner，现代TLS房间→A/B独立日志→两个自建原生进程的实际回放/结果核对已组合通过；交易/武将移动新增严格语义提案和可信证据预检。真实游戏菜单捕获、双端数值/UI刷新及最终原生Ready仍未闭合。[内政状态](DOMESTIC_SYNC_STATUS.md)、[赏赐组合交接](../work/mod_research/reward_room_flow_handoff.md)。本轮完全离线，没有待用户操作。

继续开发已将双方准备接到两个原生Owner的实际等待观察，并串过“菜单语义提案→TLS去重→双端赏赐→等待确认”。新结果19项Python、11项原生组合通过；菜单确认前候选已定位。局部User/赏赐/保存入口证据不是全输入排他，不发推演许可。[本轮交接](../work/mod_research/reward_ready_flow_handoff.md)。

**最新继续推进（用户明确暂不方便，本轮全部离线）：** 输入隔离同Owner后继18/18，接双端TLS组合13/13；B启动四线程来源与两代完整queue组合4/4，消除两者仅分别测试的缺口；新赏赐菜单只读观察器60/60、新正常保存观察器39/39已就绪，但未运行实机preflight/record。没有待用户操作。[输入组合](../work/mod_research/reward_interlock_flow_handoff.md)、[B组合](../work/mod_research/b_reload_lifecycle_queue_handoff.md)、[菜单工具](../work/mod_research/reward_menu_observation_handoff.md)、[保存工具](../work/mod_research/a_save_observation_status_handoff.md)。

## 共享的34号测试存档

按用户明确要求，原34号档的固定副本已加入 [`fixtures/saves/slot34/`](../fixtures/saves/slot34/README.md)，供其他电脑测试。274920字节，SHA-256 `afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95`，与当前槽位和历史备份逐字节一致；对应历史实机203年8月中旬、张鲁。导入说明与机器可读manifest在同目录。

共享存档那次只读取并复制该存档、修改仓库文档；没有启动或操纵游戏、加载存档、安装补丁或调试器。该副本不包含运行时镜像/profile或旧会话许可；其他电脑仍须重新建立本机运行身份与验证。原档未改，原生开发缺口继续见下文。

## 已确认的最新实机状态

**原电脑的双人势力规则实机测试已收尾；用户已恢复34号档，无待操作请求。** 这是历史最后确认状态，不可用来假定新电脑或稍后启动的游戏也在相同状态。

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

最新 `planning_input_interlock` 将同Owner的User/global UI/panel本轮观察合并，已接原Ready流程；窗口消息、Root转换、设备缓存、其它消费者和后台writer仍不在覆盖内。Controller及赏赐绑定只对应一个规划期，跨旬需正式退役/重绑定，不能重置旧模块。菜单四点只读[观察工具](../work/mod_research/reward_menu_observation_handoff.md)已完成，用户方便后按该交接执行；未抑制自然赏赐的记录只能作shadow分析，不能再送权威队列造成双执行。取消/安全关闭与完整menu lifetime仍未证实。

**距离首轮双机测试的验收清单：** [FIRST_TWO_PC_TEST](FIRST_TWO_PC_TEST.md)。固定34号起点、张鲁/刘备、两旬不下新命令；还缺A真实两次新档、B真实连续加载、统一运行所有者接通、两机配置四项结果，不按离线用例数量估完成百分比。

1. **A 新存档生产接线。** [upstream门禁](../work/mod_research/a_save_upstream_handoff.md)仍为冻结基线，同Owner两诊断保存29/29。[writer范围审计](../work/mod_research/a_save_writer_scope_handoff.md)已定位Game尾部启动army后台任务及序列化字段交叉。新[原生协调调查和分析器](../work/mod_research/a_save_native_coordination_handoff.md)48/48：找到普通/内联队列生产者，确认16C160含对象清理，不能拿来纯排空；普通Save直接层尚未找到join，间接协调仍未证明。新[单次正常保存观察器](../work/mod_research/a_save_observation_status_handoff.md)39/39已准备，使用四个硬件点配对Save/worker，严格拒绝漏样本、错配及不完整收尾，并保留不属于自己的DR6事件状态。下一步在用户方便时取得一次真实记录，再决定必要保护范围；生产发布/IPC、对象生命周期及两真实新档仍缺。观察结果不发permit。
2. **B 同进程连续加载两份不同档。** 最新[启动+完整queue组合](../work/mod_research/b_reload_lifecycle_queue_handoff.md)4/4：一次原生四worker初始化、同一已暖worker完成两代16个Root任务/48捕获、两次queue pop及Load/Title start/join；每代一个普通无票任务透明，yield场景两代各一次真实让出/恢复。两旧窗口退休，新代不改旧回执。构造替身仍主动等初始窗口，第二档仍诊断变体。旧[嵌套故障](../work/mod_research/b_reload_fault_handoff.md)30/30及[自动owner单任务故障](../work/mod_research/b_reload_activated_fault_handoff.md)3/3未与本次启动组合重跑。另有新进程DLL加载器独立2/2及10次重复，但只是marker export，未接SAN14 Bootstrap/发布器，PE入口运行时字节可用性未证明。实际安装、两合法新档、持续排他和世界/地图证明仍缺。
3. **双人规则跨world与准备边界。** `human_rules_world_lifecycle*` 已有六来源恢复/新实例安装顺序；`checkpoint_rules_context*` 已接远端B规则配置及阶段切换，既有 `checkpoint_delivery_control*` 已接上B独立进程经TLS返回实收字节→A实际bytes_received。B日志仍STAGED，无加载INTENT；全量回传会额外增加一次存档大小的传输。Config使用稳定binding_epoch，B不持A的Room对象，正常换代不Revoke/reset旧DLL。下一步在同一可信owner中接B旧规则撤下、持续执行/输入排他、单次加载许可、原生加载及新规则安装，再做完整世界/菜单/地图帧核验和跨机Ready回执。context与observe_loaded都是点检查，不是持续锁或加载完成证明。
4. **收入增加348次的归因。** 历史纯转发测试696次，双人规则测试1044次。两条收入分支没有直接重入判断点；上层预测/结算调度或AI工作量变化尚需证据。最短有用新增记录：逐调用点、势力、日期阶段及父收入计算来源的有界聚合，另做实际数值对照。不要强行把次数改回696，也不要把“无异常”写成“经济正确性完全证明”。
5. **跨电脑启动与连接。** 已有可从干净公开仓库生成的Python源码连接诊断包，支持可选EXE摘要、本机配置、真实TLS和字节校验，详见[连接检查](CONNECTION_CHECK.md)。不依赖原电脑私有catalog/profile；它没有连接原生后端。两台异地电脑尚未配置直连/VPN，真实游戏profile/安装器/A/B整体配置仍缺。首个实机目标保持为两旬不下新命令，再逐项接赏赐、出征与事件暂停。

## 最新开发：菜单观察工具、扩展输入隔离与两代加载组合

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
