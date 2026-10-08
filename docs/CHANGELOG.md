# 进展记录

## 2026-10-08 — B真实Root线程来源与首轮双机门槛

多agent离线开发/审阅，未访问游戏、Steam、UI或当前存档目录，无待用户操作。

- 新worker Provider同ABI后继：锁内固定expected bank，旧worker切代后可按原任务返回/done；旧parent接口保留current检查。新Root观察器从实际OS CONTEXT取得入口/返回/完成，PE FINALLY恢复六个DR，异常保留未完成任务。
- 最终23/23：16项前驱回归、7项独立Root（连续两个任务、异常和拒绝等）。首轮4个失败来自fixture误把yielded任务当正常完成，修正后继断言而未清零worker/伪造回执；失败保留。两新实现无fixture宏编译通过，最终输入摘要不变。
- 明确发现同线程Root/Load观察器的DR占用冲突，尚未组合；激活仍由fixture提供，实际yield/resume未覆盖，不能称两份真实档加载完成。A保存排他、统一owner、生产发布与跨机配置继续为门槛。
- 新增[首测清单](FIRST_TWO_PC_TEST.md)，限定张鲁/刘备、两旬不下新命令，区分四项验收结果与可延后功能。见[公开证据](evidence/2026-10-08-root-worker-sources.json)与[交接](HANDOFF.md)。

## 2026-10-08 — B父观察原子代次绑定与A报告边界审计

继续多agent离线工作，未访问游戏/Steam/UI或当前存档目录，无待用户操作。冻结前驱未改。

- 新Provider与queue parent同ABI实现后继，用伴随ObserveExpected在同一锁内核验current、generation/attempt/epoch及窗口状态，再处理四个parent点。错代拒绝，resume/complete只查expected bank；旧worker普通观察保留历史ticket归属，SEH/FINALLY固定异常归属并清理TLS。最终16项包含3个queue组合、12个直接Provider检查、1个真实OS捕获中途切代及PE收尾；不是全局调度fence。
- 首轮3个失败来自fixture误设parent/worker同线程，保留失败后改用真实线程；没有放宽Core约束。独立审阅补强active/yielded resume负例，并修复测试等待失败可能使线程借用过期栈job的问题，最终重新运行。
- A新增16项归档/模型审计，证明跳过flush call会清掉触发标志，更早User切点走原收尾能保留待办、避开selection/action。更早updater及外部生产者反例仍成立；未生成原生桥、发布器或保存permit。

精确结果和范围见[公开证据](evidence/2026-10-08-bound-provider-report-boundary.json)与[当前交接](HANDOFF.md)。Root worker来源、保存完整写入排他和整体原生owner继续作为实机前置工作，尚未完成双游戏整旬测试。

## 2026-10-08 — 报告检查接入保存、真实队列Finalize与远端收件确认

继续离线多agent开发和交叉审阅。未操作游戏/Steam/UI，未访问当前游戏存档目录，没有新的待用户操作请求。

- A新增同ABI `a_save_report_owner` 实现后继，把报告flag/队列/游标检查接入同Owner两保存，最终15项通过。修复并发初始化claim、旧代导出、Submit内存异常与Copy轮询误撤权；完成后异常能传到普通Owner终态。明确复现同次报告写后清零且游标不变的ABA旁路，完整排他/生产permit仍未放行；旧IPC构建尚未切换。
- B新增 `b_reload_queue_*`，用归档调度器真实type1队列pop调用Finalize，再组合两代Title +520/+590，移除人工Finalize调用。3项通过，各有两次pop、18个有效scope和2000次不消耗scope的普通调度。首次编译因变量遮蔽失败，修正后通过。审阅发现Provider快照与current_选择不是原子的，外部OpenWindow仍可能改变观察归属；这是下一步必须修的缺口，不算生产接通。Root worker和部分引擎业务仍是替身。
- 新增 `checkpoint_delivery_control`：独立B使用真实TLS/SQLite返回完整字节，A独立receiver核验后实际设置bytes_received；最终19项，含5个独立B场景。并发确认只调用一次received，真实确认回复丢失时HELD且不自动重放，日志仍STAGED、没有加载INTENT/Ready。全量回传多一次存档传输，后续优化。
- 保留全部中间/失败记录。没有改冻结前驱、重置once-claim或把离线结果写成实机双客户端通过。精确哈希与边界见[公开证据](evidence/2026-10-08-report-queue-delivery.json)，下一步见[当前交接](HANDOFF.md)。

## 2026-10-08 — 共享34号测试基线

按用户要求，将 `svdexSC34.s14` 固定副本加入 `fixtures/saves/slot34/`，提供导入说明和manifest。当前原档、历史备份和仓库副本均为274920字节，SHA-256一致；原档未修改。仅对此明确文件增加Git忽略例外，其他存档及私有运行资料仍排除。没有操作游戏或执行加载，也不将共享文件视为跨电脑加载已通过。

## 2026-10-08 — 保存早段写入、父调度来源与远端规则配置

多agent继续离线开发并交叉审阅。未操作游戏或Steam，未读取/改写当前游戏存档目录；已有私有归档副本仅用于自有进程和模拟器测试，无待用户操作。

- A `a_save_early_*` 的8条归档路径确认：现有动作拦截点之前，报告处理会改写报告记录及World游标。新增只读guard的生产构建与14项检查通过；flag和队列必须同时核对，Quiet仍不授予保存许可。修复结构体padding误判；归档外部模型及初始数据错误的失败运行均保留。非空渲染/选择对象下游、并发写入和完整保存排他仍缺。
- B `b_reload_parent*` 新增父调度及内部阶段调用桥；队列阶段不占硬件寄存器，后段四处观察用实际CPU上下文交给既有Provider。8项通过，包含两代Title +520/+590组合、拒绝条件和前后阶段异常展开。修复自有归档动态展开表区间重叠；保留先前两次异常失败。真实队列Finalize会清空当前manager对象，与旧候选的前置条件不兼容，仍需独立后继。Root worker业务/返回、真实发布器与无限期常驻均未完成。
- `checkpoint_rules_context*` 的18项测试通过：独立B进程使用实际TLS与SQLite，不共享A的Room对象；规则绑定稳定binding_epoch，以本机reader获取当前world，故障经TLS实际撤销下载。日志保持STAGED，不提前创建加载许可。原生身份/执行排他是明确替身，没有实机加载或跨机Ready放行。
- 交叉审阅修复故障context被重签、本机锁顺序倒置与正常切旬缺少显式context采用；加载后观察只代表字段采样，不能冒充真实完成回执。没有修改冻结前驱或复用旧模块claim。

准确构建、场景数量、失败及限制见[本轮证据](evidence/2026-10-08-native-boundary-context.json)和[当前交接](HANDOFF.md)。下一步优先完成真实queue Finalize/Root worker与A保存排他，再接完整运行owner；仍未进入双游戏整旬联调。

## 2026-10-08 — 保存动作隔离、Finalize工作线程、规则换代与连接包

继续不触碰游戏的前置开发，三名agent分工并交叉审阅，主agent完成便携连接入口和整合。没有访问游戏/Steam、改动真实存档或新增待用户操作请求。

- A `a_save_action_gate*` 替代旧输入组件，统一Game/UI、直接面板与User命令段的来源校验，组合同Owner两次保存。18项自有进程测试通过，另有4条归档路径在Unicorn中通过。首次因系统额外线程拒绝发布；后续采用真实暂停/上下文检查。审阅还发现正常场景未暴露的异常展开错误，修复固定栈帧及尾部后增加实际AV/展开检查。早段User仍可写入的反例保留，完整保存许可未开放。
- B `b_reload_finalize*` / `b_reload_title520*` 接通实际Finalize槽、原生上下文及+520自动runner，与+590独立桥组合12项通过；移除人工Begin及上下文填充。首轮编译因旧人工函数未使用而失败，删除后重新构建。父调度与嵌套scope时序仍缺，不能把自有执行写成游戏连续加载已完成。
- `human_rules_world_lifecycle*` 在同一自有进程验证两代规则模块，实际恢复六入口后才替换自有世界内存、加载后读取新地址、准备新实例并安装。12项通过，保留旧DLL、不reset/卸载，拒绝旧世界观察、历史实例复用及错误回调。真实加载器、持续执行排他与Room连接仍待接入。
- 新增公开源码连接诊断包生成器、本机配置/版本检查和中文入口，不依赖原电脑私有profile/catalog。8项测试通过，含搬移后的两个隔离Python进程真实TLS、129 KiB核对、错误指纹/版本与白名单打包。需Python和cryptography；只验证网络，不连接游戏原生后端。

精确结果、失败记录、源码及本地包摘要见[本轮公开证据](evidence/2026-10-08-prerequisite-integration.json)；连接用法见[CONNECTION_CHECK](CONNECTION_CHECK.md)。仍未完成两台真实游戏的整旬闭环，下一步按[HANDOFF](HANDOFF.md)的具体缺口继续。

## 2026-10-08 — 动态保存管道、独立UI来源与Title590自动启动

继续不需要用户操作的主线，多agent分工开发并交叉审查；没有访问游戏进程、Steam或安装实机钩子。

- 新增 `a_save_ipc` 原生本机服务与Python客户端：当旬Room先reserve，再经实际命名管道Submit给同一个常驻Owner；新字节CopyArtifact回传并交既有TLS/SQLite。12项动态流程/拒绝用例通过，包含连续两个请求和断线不重放。世界观察、B回执及原生保存业务仍是模型/替身，文件是32字节诊断数据，不是真实SAN存档。
- 修复首次动态测试抓到的Stop回执被立即断管丢弃问题，以及独立审查发现的permit期间停止/父进程退出窗口；停止连接使用固定截止时间，派发前重新核对存活。保留失败运行，新增permit内停止真实管道反例，确认零Submit、零完成。
- `a_save_input` 发布独立Game/globalUI槽，在raw User/Save仍执行时抑制一条实际UI路径。15个原生自有进程场景通过，包括两次保存组合和明确panel绕行；19个未覆盖锚点核对。仍不授予完整输入锁、保存准入或Ready。
- `b_reload_title_source_v2` / `b_reload_title590` 接通Title +590原生启动来源、等待线程/事件证明、runner发布与自动收尾观察。12个自有进程场景通过，父来源、Finalize和+520继续明确缺失；没有声称B真实连续读档已通过。
- 新增 `tools/check_dynamic_save.py`，明确构建并运行动态A流程；旧检查入口保留历史语义。准确证据见[本轮摘要](evidence/2026-10-08-dynamic-checkpoint.json)，剩余实机门槛见[当前交接](HANDOFF.md)。

## 2026-10-08 — 保存出口、当旬绑定与常驻原生来源

用户不能操作电脑时，完成离线接线与多agent交叉审查，未访问游戏或Steam。

- `a_save_user_owner` 将 raw保存观察和User子集等待放入同一物理槽所有者，同Owner两份不同文件导出；修复Stop或sticky error后无法解除实际抑制的问题。生产库及20个自有进程场景通过，保存业务仍是替身；已hold时仍不能提交保存，完整输入排除未完成。
- `b_reload_title_source` 实际发布Title.Update vtable来源，同一常驻来源服务两代；生产对象及12个自有进程场景通过。父来源、Finalize、Title worker创建/启动和真实连续读档仍未完成。
- `checkpoint_fresh_save_packet` 新增C++字节出口与Python严格解码，8项Python验证及原生编码器检查通过。格式完整性不冒充进程来源认证。
- `checkpoint_fresh_save_binding` 固定当旬完整scope/epoch/cut/attachment，核对原生请求、固定字节和独立世界观察后交既有Room发布；稳定native epoch与每旬协议epoch分开。20项测试通过，TLS验证接收两份Owner诊断文件、持久化重开、控制连接保留及旧代拒绝；世界观察/加载回执明确为模型。审查发现并修复安装后异常仅标记HELD却仍发下载票的问题，显式hold和异常均退休下载，清理失败不虚报成功。
- 增加明确allowlist的 `tools/check_checkpoint_components.py`，将新组件构建与字节链路检查接成可复跑入口。准确结果与证据范围见 [公开摘要](evidence/2026-10-08-checkpoint-components.json)。本轮不等于真实双客户端或完整一旬游戏流程通过。

## 2026-10-08 — 远端重新克隆验证

从GitHub拉取 `8f95d05` 到全新的带空格路径，未配置私有fixtures/原研究依赖目录，运行公开 `tools/dev_check.py`：18个原协议unittest、17项TLS自测检查均通过。缺capstone/pefile被正确报告。此验证确认公开源码满足协议检查，不冒充另一台物理机、原生编译或游戏联调。

## 2026-10-08 — A端保存常驻组合

新增 `checkpoint_fresh_save_session`：固定原生User/Save地址，专用两槽FINALLY桥、HookSet真实槽发布、live_storage_binding / serialized Gate与冻结FreshSave Driver连接。生产库编译成功，13个自有进程用例通过，包括同一Owner两次不同文件、User/Save异常、Stop在提交前后、存储generation漂移、字节不符及抑制回调不能冒充原生返回。新增原入口32字节复核，拒绝初始化后出现的detour。

未操作游戏进程/Steam；保存业务与文件接口是测试替身。真实A配置、与现有User槽/规划抑制模块的排他接线、完整输入边界及Room准备完成仍缺；最多两请求，非无限连续旬末保存器。

另检查磁盘EXE重建保存profile：支持版本SHA相符，但79个范围均与运行时指纹不同，不能直接生成；未放宽校验或输出错误头。

## 2026-10-08 — GitHub接手基线

将既有第一方源码迁入仓库，增加跨电脑交接、设计、配置和贡献流程说明。游戏、存档、私有记录、凭据和编译产物留在原电脑。仓库不是可直接开玩的发行包；历史固定路径脚本与私有profile依赖仍需逐步迁移。

新增 `tools/dev_check.py`：实际运行原协议18个unittest和原房间TLS自测17项检查；默认、严格依赖配置、带空格最小源码副本均通过。无游戏访问或外网下载，报告写入ignored `.local/`。明确区分协议通过、依赖缺失和未执行的原生验证。

## 2026-10-08 — 双人规则实机一旬

一个真实SAN14PK游戏进程、两个本机TLS诊断席位，绑定张鲁和刘备，203年8月中旬推进到下旬。120次AI调用中8次人类绕过、112次原生执行；1044次收入判断正常返回，无挂起/异常。六处来源恢复、调试器解除，用户恢复34号档且样本对照通过。

修复错误的官爵派生数量 `world+165D==1` 空闲条件、房间确认顺序和启动日志参数冲突。修正规则18项、发布器16项独立进程回归通过。收入比纯转发多348次仍待归因，未完成双游戏联调。

同时推进：A FreshSave两请求组件26项验证；B三处join收尾与两代任务组合6项；Ready三个消费入口相关组件验证。它们仍有生产接线和实机验证缺口。

## 2026-10-07 — 六入口真实转发

首次在真实游戏整旬执行四类AI入口120次、两处收入判断696次，均正常收尾；当时双人策略规则未启用。它只证明转接/恢复路径，不代表本轮策略启用或双客户端同步。
