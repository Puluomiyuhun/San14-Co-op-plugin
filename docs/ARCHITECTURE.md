# 完整联机流程与实现边界

## 当前主线（2026-10-10）

最新后继已完成明确有限观察正式完成合同，并接入双侧启动/收尾：A `observed_host_start.py`＋`a_observed_start.py`，B `b_observed_start.py`，共享实际TLS `observed_room_service.py`。A等待B收尾通知再关网络；原生未知结果、回调排空和句柄恢复分别处理。联合测试使用实际协议/Session/Journal/观察算法，原生及RAM仍为替身，新CLI整组实机未跑。A七处保存入口与六处双人AI规则尚未合装，当前限于无新命令存档同步诊断。[启动手册](../work/mod_research/observed_start_handoff.md)。下文为历史阶段，旧缺口以最新HANDOFF为准。

A同进程跨旬两次自动保存、B同进程连续加载这两份实际产物已实机通过，详见[当前交接](HANDOFF.md)。下面按时间保留的“自动保存尚未通过/两载待测”属于旧阶段，不能覆盖新证据。

新开局协议明确首份为同日快照，正式B完成后清Ready、保持日期；双方准备并封口后才进入首次推演。新A控制已与真实TLS/独立B测试进程和正式回执联合通过，两次检查点对应“开局＋一个旬末”。本次组合中的原生和世界仍是替身；真实进程安装、有限观察合同的完成接口和两机启动编排尚待接入，不能将它与上轮分阶段实机证据拼成双机成功。

## 当前远端实现：复用原生刷新接口

`b_warm_refresh_remote_owner`选择新的普通/Bootstrap规则桥和ReceivedApply。接收文件仍在私有目录，Python只固定源并备份旧CC03；原生Resident负责写入、双读、目标锁和真实加载退休。刷新完成与目标完整字节通过后才重装规则，再按原路径完成本期Journal。已通过本机TLS两期组合，原生加载/内存/guard在该测试中仍为替身；不能将它与上轮单游戏两次加载拼成两真实客户端证明。

原 `b_warm_remote_owner` 冻结供历史核验。生产调用仍需要真实持久输入/执行guard；这个接线不提供guard，也不授Ready。A自动保存本轮fresh实测停在请求之前的父初始化，已恢复入口和存档核验，具体诊断见当前HANDOFF。

## 最新实证：一个B进程可连续原生加载并保持B势力

2026-10-09新实机流程两bank连续完成：中旬张鲁档→中旬刘备，随后下旬张鲁源档→下旬刘备，完整刷新和原生加载链/退休/Handover都通过。新`b_warm_stable_capture`仅在安装前有限重读不稳定的只读采样，每次保留原完整两样本检查；绝不重放写入/安装。实际成功两bank的采样都一次通过，重试分支仍以离线反例验证。

上述新远端接线已在离线组合中完成；真实规则安装后的远端加载仍待验证。A自动保存仍需独立实测；这次第二档是用户手工保存生成的真实新旬档。参见[当前实机边界](evidence/2026-10-09-real-two-warm-loads.json)。下节“真实游戏尚未重测”为本轮前一阶段记录，现以此节为准。

## 最新实现：原生刷新与加载共享同一确认边界

`b_warm_refresh_diagnostic`使用两份独立source和旧CC03身份。Python仅备份旧档并准备私有新档；实际`CommitGameBefore`在原guard/inspect之后调用新Owner，绑定当前Steam v014 FileWrite槽0及原读接口，核旧目标/备份和两次旧原生读取，写持久一次性意图，FileWrite一次并完整双读新内容。此后取得目标deny-write租约，再进入原来的Verify、请求CAS及加载链。`b_warm_refresh_retire_session`只在真实完成、封存、六槽恢复后释放该租约，释放失败令Session失败。第二bank仍须真实Handover，不重用上一代配置。

这条生产接线已编译并在自有宿主执行两代；真实Steam和游戏尚未重测。每次状态采样同时保存RefreshReport，避免原Request失败隐藏更早的存储原因。刷新可能在请求CAS前已写目标，因此Request的Rejected不等于没有文件副作用，不能自动回滚/重试。它仍是无新命令窄诊断，不实现持续玩家输入隔离或屏幕遮罩。下节实机失败是该改动的来源，旧文件暂存顺序保留为历史。[组合与范围](../work/mod_research/b_warm_refresh_pair_handoff.md)。

## 最新实机约束：磁盘暂存与原生存储视图是两个步骤

2026-10-09两档诊断首载发现：磁盘CC03已是274920字节的新档，原生GetFileSize仍返回274880，因而在FileRead/加载请求CAS之前拒绝。物理文件原子替换和备份成功，不代表游戏的存储接口已观察到新内容。两份一致的原生完整Evidence已离线解码，详见[实机证据](evidence/2026-10-09-warm-native-storage-mismatch.json)。

后继应先在已确认的实际调用边界保存旧档，保持独立私有新档副本不变，核旧原生内容，再原生发布并完整双读核新内容，最后获取目标文件租约进入加载。旧`run_two`持目标只读租约覆盖整个load的顺序不能直接容纳FileWrite；不能在持锁期间强写、放宽size/hash检查或先物理替换再假造原生刷新成功。每期都需要这一衔接；第二期仍须前期真实退休/Handover。刷新core测试不代替原生Write绑定、调用边界和真实两载验收。

## 玩家眼中的目标流程

1. A 创建房间和剧本，选择 A 势力并生成起始存档。B 连接房间，选择地图上另一个势力；其他势力照常由 AI 控制。
2. A 把同一世界的起始存档交给 B，工具在 B 的原生加载/身份初始化路径中选择 B 势力，使菜单、操作权限和事件跟随 B。不是只改屏幕上的君主名字。
3. 双方各自在自己电脑上操作本方菜单。赏赐等即时操作由 A 权威接受并按序应用、同步。出征等延时操作同步的是命令，实际移动和战斗随日期推进。
4. 一方准备后等待另一方；必须完成输入限制、已提交命令排空、序号与阶段检查，双方才能进入推演。
5. 推演中若一方遇到需要选择的事件，房间应停在对应的事件边界，等待该玩家处理，再恢复双方推进。该完整事件同步尚未完成。
6. 首版允许两端本地战斗过程有差异。旬末以 A 的完整世界为准，生成本轮新存档并传给 B；B 保留自己的势力视角加载后核对世界，再允许下一轮内政。
7. B 同步时应看到地图上的等待画面。首版支持窗口/无边框。遮罩是呈现层，不能把遮住加载界面等同于游戏已经完成异步加载。

## 当前技术取舍

- A 同时是玩家和权威服务端；TLS 房间、两席绑定、协议序号及检查点传输已在本机测试过。
- 各客户端在原生游戏里保持本方身份；远端势力的指令由工具转交。AI 的四类决策入口和两处收入归属判断需要识别两个人类势力。
- 双方主军团跳过 AI 决策，委任军团及其他势力保留原逻辑。收入规则只改已核对的两个调用点，不能全局替换所有“是否玩家”的判断，否则会影响本方菜单/权限。
- 原生代码接入采用外部协调脚本、进程内 DLL/汇编桥和经核对的钩子。不是远程桌面，也不是只在外部修改旬末数字。
- 严格确定性锁步尚未成立。随机种子相同并不足以涵盖执行顺序、视角相关路径、隐藏状态及事件交互。A 权威旬末校正是当前用户接受的首版方案。
- 长期目标是同一进程常驻、连续多旬。之前一次性成功的读档实验不能证明连续两次及更多次均可工作。
- 首个连续加载原型优先沿已有实机成功的warm六槽入口扩展：完整加载后封存业务观察、恢复六槽，旧DLL驻留并透明转交迟到调用；下一代使用新模块和独立文件配置。cold Bootstrap是完整Root任务方案的安装条件，不是引擎连续加载本身的必要条件。详见[路线重审](../work/mod_research/b_reload_runtime_warm_review.md)。
- warm文件配置把读档前日期/当前势力、存档日期/来源势力、目标B势力分开。第二次B可以当前已为刘备，仍读取A视角的文件再经原生初始化恢复刘备；不能沿用第一次张鲁菜单的检查条件。每驻留模块只捕获一次配置，文件hash/size、日期和武将/军团关系继续严格验证。当前原生文件名映射仍限定已验证的槽63，支持不同内容不等于支持任意槽位或任意文件名。
- [同槽接管后继](../work/mod_research/b_warm_two_bank_handoff.md)在一个自有host中持有固定原函数和同六槽，第一代实际封存/恢复后才准第二个独立DLL接管。跨代不重置Session或once。相应文件暂存与fresh planning采样已分别实现，但仍须由统一启动器在真实退休、无读者和输入边界下衔接；文件已暂存和采样相同都不是原生加载许可。此前profile的固定势力guard遗漏已由后继修复，旧target9 fixture成功不证明那层曾被执行。

## 最小原生连续加载诊断

已有Resident/run_two可直接加载两份已准备档，不依赖严格远端owner的全程guard。新增[窄诊断入口](../work/mod_research/b_warm_pair_diagnostic_handoff.md)用于未安装双人AI/收入规则、玩家不下新命令的本机两档测试。原始六规则来源需在claim前及每bank边缘保持原样；继承已有User/Menu/Game局部原生边界和真实退休/Handover，没有实现持续输入暂停，也不接房间Ready。

[文件/构建前检](../work/mod_research/b_warm_pair_preflight_handoff.md)先于进程打开和一次性claim，防止坏文件先消耗测试生命周期。诊断成功后仍须接正式远端owner与规则生命周期；不能把无规则局部诊断的约定填作严格guard。本机可用两份既有合法档证明B连续加载，无需先完成A自动保存；候选的实际日期/势力仍须确认。

## 同一B所有者与旬末校正

[RetainedRemoteOwner](../work/mod_research/b_warm_remote_owner_handoff.md)已将远端一次预约接到实际Bootstrap/普通ReceivedApply、同一加载/规则bridge和加载后采样，再给原远端通道发送正式完成。owner保留同一进程/对象图、两bank和三代规则历史，回包丢失锁住整个流程且不重做加载。它要求已有严格执行guard，未自行实现游戏暂停；测试原生行为仍为替身。

[SettledRemoteCompletionRoom](../work/mod_research/b_warm_settled_completion_handoff.md)是双方已自行推演到旬末时的明确日期合同：普通校正before=loaded=目标日期，首代身份切换仍从旧日期开始。与原地等待诊断使用的旧Room分别由A本地配置选择，不接受任意日期。owner组合已覆盖目标日期第二次校正；真实推演后的root/world与输入边界仍待验。

[本机密钥工具](../work/mod_research/b_warm_adapter_key_handoff.md)准备独立adapter key，并由两端本地load_key读入；人工私下转交、接收方重新以自己的Windows用户权限导入。它不自动启动网络房间或原生后端。

## A/B跨进程的完成确认与规则配置

[RemoteCompletion](../work/mod_research/b_warm_remote_completion_handoff.md)将原来同进程Projection的最后确认拆开：A独占PeriodCoordinator，B只持本机Journal/原生所有者；独立adapter密钥认证预约及加载观察，A以新鲜本机采样对照后才`loaded()`。B先核完整投影，网络传固定结构摘要，避免将压缩率当成64KiB上限内可传的保证。摘要依赖可信B所有者及其本地检查；HMAC认证来源本身不是native fence证明。

[RemoteRulesWorldCapture](../work/mod_research/b_warm_remote_rules_handoff.md)只通过真实B控制连接读取已确认scope，本机GameReader仍读取本机世界；不在B重建A的Room。明确后继factory复用已有真实Prepare/Seal/发布器。断线使capture/factory停止依赖工作并保留模块，不等于已自动恢复原入口。

现有[B边界审计](../work/mod_research/b_warm_boundary_audit.md)列明局部加载边界与持续输入暂停的差别。可做无新命令受控诊断，不应为它追加全引擎锁；正式可玩暂停需在B自己的warm原生Owner中衔接，不能叠加占同User/Game槽的A owner。

## 首次视角切换与后续房间确认

[Bootstrap正式后继](../work/mod_research/b_warm_bootstrap_protocol_handoff.md)将首代读档前的source视角作为独立数据库契约记录，加载后依然必须是targetB。第1期使用独立BootstrapJournal/Projection，第2期回到普通Journal/Projection；同一warm和规则生命周期先用bank0，再用bank1，不重建对象来清掉一次性历史。实际本机TLS/SQLite/Windows文件事务已在一条组合中由期1进入期2再到期3；原生加载、保存、内存和暂停仍是测试替身，没有两游戏闭环。

[RulesFactory](../work/mod_research/b_warm_rules_factory_handoff.md)补上RulesWorldCapture之后的原生准备端口：当前world配置→独立DLL→Prepare→Seal→ResidentPort。它保留模块和发布器所有权，不自行安装或推进游戏；六入口安装/撤回继续由ResidentPort/WorldLifecycle检查。调用者需保留同一真实输入/执行边界。factory与真实warm.load、A保存、跨机完成证明的联合实机仍未验证。

## 同进程两档协调与房间回执

[首次视角后继](../work/mod_research/b_warm_bootstrap_handoff.md)只在第一代允许旧规则source viewer→profile.target；随后交回原WorldLifecycle同viewer约束。它要求旧双人规则已安装，先恢复再加载，绝不在world换址后才试图恢复旧绑定。两代共享warm bank序列与规则生命周期；该模式没有实现第三bank。

[规则捕获适配](../work/mod_research/b_warm_rules_capture_handoff.md)从已绑定GameReader/房间得到新WorldGeneration和当前Config，区分固定房间binding epoch与本地规则代际epoch。准备、封存及发布由已新增的RulesFactory完成。首次source视角不能假造target视角调用旧Journal：冻结Received前驱仅做诊断ACK，正式路径使用Bootstrap后继及上文RemoteCompletion。

最新[收档适配](../work/mod_research/b_warm_received_apply_handoff.md)把B本机的实际收档记录、一次性加载意图、既有规则/warm桥和TLS诊断ACK接在一起。固定本期context和原生进程身份；已实际预约的Journal INTENT可交给该调用，但必须与本机持久记录精确匹配。回执丢失不重做加载。

[有限契约后继](../work/mod_research/b_warm_projection_handoff.md)使用明确的两表加日期契约，沿原Journal与`PeriodCoordinator.loaded`推进协议。协议中的`world_sha256`在这个契约下仅代表这份已声明投影，完整世界标志仍为false。它需要可信本机原生完成及当前A/B采样和真实等待边界；诊断ACK或文件SHA单独不能推进。A保存前读取不依赖未来文件SHA；B Receiver从已验证Journal字节重建。正式游戏输入释放仍由外部原生所有者负责。

新增[规则与warm适配](../work/mod_research/b_warm_rules_bridge_handoff.md)复用`WorldLifecycle.replace`：恢复旧规则六入口→真实文件事务→warm加载→实际新世界观察→新模块绑定/发布。输入与执行等待边界仍由可信本机所有者保持，bridge不以房间暂停或JSON代替，也不释放等待或设置Ready。新适配与真实规则发布器组合已验证，但warm加载在该组合中仍是替身；另一路实际远程原生测试不能拼成同一真实游戏联合成功。

[世界观察后继](../work/mod_research/b_warm_world_handoff.md)只比较两张已有精确字段清单的表及日期。所有物理槽均读，包括非活动槽；地址和本地玩家标签不参与共享散列，已审计业务字节不做猜测性屏蔽。结果命名为`partial_sha256`，缺失领域和非原子读取明确保留，不能作为现有更广世界契约的成功回执。其接点是原生保存/加载成功后的诊断，并非新的网络放行权。

最新[完整双factory](../work/mod_research/b_warm_factory_pair_handoff.md)在同一自有进程执行两次实际Install/configure/完整guards；[两档协调器](../work/mod_research/b_warm_coordinator_handoff.md)已经把原生Handover、两个bank、fresh采样与第二次文件备份替换接成单一本机流程。其整个远程执行路径未实机验证，文件检查的native port仍为替身。第一档须先暂存，CLI不接网络房间也不推进游戏。

[WarmRoom](../work/mod_research/b_warm_room_handoff.md)沿既有TLS/接收Journal增加诊断完成ACK，供A显示B本地加载验收情况。它不是原PeriodCoordinator.loaded：文件SHA与canonical world SHA用途不同。正式下一旬还需把同一原生所有者的实际世界观察、规则撤回/重装和回执接入房间；不能用测试complete_model或客端自报替代。受控两档诊断继续不授全世界核验/完整输入排他/房间Ready。

## 上一轮启动接线边界

[A跨旬启动后继](../work/mod_research/a_native_turn_start_handoff.md)已经连接生产Runtime新9/10、原IPC心跳与第二保存请求，运行期间仍由人正常推进。B的[完整factory组合](../work/mod_research/b_warm_factory_handoff.md)补上实际Install/configure与完整guard执行，一代成功不再依赖附件guard替身；游戏业务仍为明确替身。新[B单代启动入口](../work/mod_research/b_warm_start_handoff.md)绑定当前本机profile/Steam/生产DLL，实际完成报告、退休和fresh地图身份共同验收。单代启动不覆盖暂存档，不授权下一代；文件替换、真实native handover和两个完整factory还需持续协调器连接。两端房间Ready和规则跨world重装亦未在这两个启动器内闭环。

## 推演结束与下一旬的身份边界

旧A repeat的Retire保留ReadyFence/Gate，却等待被门禁挡住的日期推进。新的[a_native_turn后继](../work/mod_research/a_native_turn_handoff.md)已接独立跨帧Running：旧工具命令/保存请求继续退休，原User/Game透明执行，返回规划后核对日期并fresh绑定状态对象及新Guard。自有组合特意让User/Strategy离栈换址，随后第二份保存完成；真实游戏仍待验。Running目前放行普通菜单，测试必须不新增命令，不能称正式输入白名单。Stop时保持未决推演、不恢复旧对象检查。[身份采样工具](../work/mod_research/a_turn_identity_handoff.md)可伴随未来实机推进补地址观测。

旬初规划身份保持到本旬校正结束。旬末保存日期已经改变，但B尚未加载，下一旬身份还不存在。`checkpoint_planning_save_link.py`显式绑定这两个日期。新 `planning_simulation_boundary*` 在可信同步宿主回调前后核实际原生日期/桥收尾，以同epoch进入旬末；`planning_simulation_session.cpp`保留旬初Scope，只认可该明确边界的有效日期，随后正式退休重绑。`a_save_simulation_ipc*`已在同一自有进程接完整网络Scope、两期诊断保存和真实TLS，下一Scope仅在模型B完成后产生。日期/战斗与保存业务仍替身，没有接真实引擎调度或B加载。

B的最新 `b_reload_cold_bootstrap*` 已将实际Bootstrap、冷等待、原RegisterColdPool和两代完整queue接进同一主PE/DLL/Provider。Prepare承担唯一初始化，避免旧Bootstrap重复Initialize；普通和yield两条组合通过。测试采用自有映像与诊断文件业务，真实代码可用阶段、早期CRT上下文、生产者排他和连续合法档加载仍待验证。[当前组合](../work/mod_research/b_reload_cold_bootstrap_handoff.md)保留详细替身和服务切换边界。

## 已知模块与关键缺口

| 模块 | 现有入口 | 当前边界 |
| --- | --- | --- |
| 房间和协议 | `outputs/san14-link/room_session.py`, `room_transport.py`, `tools/prepare_connection_check.py` | 本机协议/TLS验证；有公开源码连接诊断包，原生游戏后端未接 |
| 即时命令 | `reward_room_flow.py`、`a_reward_save_owner*`、`authority_reward.py`、`execution_journal.py` | 固定赏赐历史单游戏执行；新唯一Owner及现代TLS/双日志/两个独立原生fixture已组合，业务效果替身。普通菜单捕获、真实双游戏执行/刷新、密钥引导及原生Ready仍缺；见[内政盘点](DOMESTIC_SYNC_STATUS.md) |
| 其他内政命令 | `domestic_reader.py`、`domestic_command_contracts.py` | 交易/移动草稿接严格语义提案与独立证据预检；缺价格/资格/时限不猜测，未接原生执行或房间路由 |
| 时间线/暂停 | `timeline_protocol.py` | 协议状态机原型；原生事件全覆盖未完成 |
| 双人 AI/收入 | `human_rules_activation_v2*`, `human_rules_world_lifecycle*`, `checkpoint_rules_context*` | 固定world实机曾通过；离线六来源换代及真实远端context已接，完整原生load/身份/排他/hold端口仍缺 |
| A 本轮存档 | `a_save_runtime_start.py`、`a_save_runtime_exports*`、`a_save_runtime_publish*` | 已实际安装并经自然父调度/真实IPC产生一个新文件；最终context验证拒绝，原生读未开始，来源因失败保留待正常退出。尚未得到合格artifact或连续两次保存；全writer/全输入许可仍缺 |
| B 连续加载 | `b_warm_two_bank*`, `b_warm_staging*`, `b_warm_profile_capture*`；前驱`b_warm_profile*`, `b_warm_retire*` | 同进程同六槽两代实际回执链/恢复已组合；暂存和本代采样分别验证。原生业务与环境仍替身，缺统一生产启动器、两份合法新档及连续实机验收 |
| B 收件确认 | `checkpoint_delivery_control*`, `checkpoint_rules_context*` | 独立B经TLS返回已STAGED的实际字节，A独立receiver确认bytes_received；额外一次全量传输，不创建加载INTENT或Ready |
| Ready 输入等待 | `planning_input_boundary*`, `planning_period_interlock.cpp`, `reward_ready_flow.py` | 同Owner局部观察已接TLS，新窗口边界覆盖已审计消息；未知消息/设备/后台writer仍缺。同world逻辑期已正式退役重绑；换world/整旬联机及完整输入许可未完成 |
| 菜单捕获准备 | `reward_menu_handoff_gate*`, `reward_menu_capture.py`, `reward_menu_observation*` | 归档Update确认前原生门禁已能单次领取纯ID并接TLS去重，正常取消/关闭与生产installer/lifetime仍缺。只读观察的自然执行记录仍不能发送 |
| 世界核验 | `checkpoint_world_snapshot_reader.py` 等 | 已覆盖记录与格子有核验；完整世界证明未完成 |

模块名用于定位，不是推荐直接运行这些历史脚本。新电脑先做本地检查与纯协议测试。

新的 [A跨旬管道组合](../work/mod_research/a_save_period_ipc_handoff.md)把最新Period Owner/Gate
与既有管道Server实际链接：房间先预约，再提交原生诊断保存；同一Owner正式退休/重绑后
完成第二次，两档经真实TLS进入接收日志。原生期次绑定仍由fixture提供，网络scope映射
Session尚未合入此链；日期/存档业务及B loaded仍是替身或模型，生产permit没有放开。

赏赐后继网络线程只排队，可信执行线程先持久化意图再调用唯一Owner；B独立执行并观察，
回执由独立adapter key认证，不能把B玩家登录凭据或裸JSON当已执行证明。A/B日记保存同一
权威意图，但本地视角context token分别重建。命令未知结果、换实例或断线终态等待，
不自动重试。最终Ready仍仅协议模型；生产必须由同一生命周期Owner补持续输入限制和
报告通道。详见[接线契约](../work/mod_research/reward_room_flow_handoff.md)。

新[Ready后继](../work/mod_research/reward_ready_flow_handoff.md)在双方准备且排空后固定同一
challenge，A/B持久化本机fence意图，实际观察原生User抑制后回报，再由A复查。协议
确认只有局部Owner coverage，不是全引擎排他；未知结果不重试setter，也不自动release。
retire使旧scope/key/cut失效，但没有执行规则撤回或世界替换。

新输入后继把Game/global UI/panel加入同Owner观察，端口本地验证扩展证据；旧Ready签名仍只陈述原User范围。新窗口边界另有原生消息ACK，不自动扩展网络签名的覆盖范围。

`planning_period_owner` 正式保留旧期回执，并在同root/world/User上重新绑定下一旬；
同一物理桥、错误与命令/Ready累计编号不清零，每期只允许一个新Controller。退休后
旧Controller必须在任何Gate操作前被拒绝。真实读档换world与保存配置仍需统一宿主
接通。参见[跨期交接](../work/mod_research/planning_period_owner_handoff.md)。

新 `planning_period_session` 保留完整网络房间/绑定/当期 epoch，按固定编码生成
本地原生 binding，真实调用同Owner的 Retire/Rebind/新Controller Adopt，累计命令
序号延续。它接可信本地 `PeriodCoordinator` 导出的期初身份；尚非生产TLS/IPC宿主，
不能把 Scope 或配置 Snapshot 当加载完成证据。新的 `planning_input_resident`
在逻辑换期期间保留同一窗口桥及已审计消息的 hold，窗口实际消费 Handoff 后才确认。
它避免正常换期时重装窗口入口，初装发布竞争、其他输入/后台writer及换world仍缺。

赏赐菜单的正常成功路径会排队一个不含菜单身份的“pop当前栈顶”命令。
权威回执到达时与队列真正消费时可能不是同一栈顶，因此单次菜单采样加返回成功
不能证明安全关闭。收尾研究与反例见[菜单交接](../work/mod_research/reward_menu_completion_handoff.md)。

## 换世界时的规则顺序

可信协调器先保留执行/输入排他，恢复旧模块拥有的六处原入口，并核对原始字节、活动计数归零和发布器已经解除调试。正常恢复与模块 `Revoke` 不同：后者永久进入故障，不能拿来正常换代。

加载请求只携带下一代编号、检查点、epoch与日期，不预先猜测新世界内存地址。加载之后再通过当前本机reader取得新root/world和两名玩家身份；核对后创建新驻留模块、Prepare/Seal、安装六入口并再次独立读取验证。历史模块地址和nonce都不能复用，旧DLL保留到进程退出。

规则换代完成仅说明这段生命周期成功。完整世界核对、B视角、待命命令排空及Ready仍由整体协调器负责；故障时不得自动释放等待或退回AI接管。

远端B使用自己的TLS控制连接获取固定协议context，不共享A的Python房间对象。规则Config使用稳定的房间binding_epoch；每旬epoch用于识别当旬请求。加载前后由B的当前原生reader取地址和字段，网络不提供地址。context核验是点检查，不能代替整个加载期间的执行/输入排他；正常切换阶段须显式核对谱系，故障才终态撤销下载。

当前收件确认到bytes_received为止：B重开并校验SQLite的两个parts，再经控制TLS回传全部字节；A独立receiver核对后通知原协调器。成功后B控制连接继续保持、日志仍STAGED。断线或绑定/字节变化终态HELD，不自动重试；协议撤权不代表游戏已暂停。这里额外传回完整存档是原型成本，后续可优化。仍没有跨机原生加载许可、完整世界回执或Ready放行接口。

## 保存请求与加载线程的宿主接线

当前A以[`a_save_local_runtime`](../work/mod_research/a_save_local_runtime_handoff.md)集中装配。真实父调度已观察16帧，核对当前规划边界manager.current为0；原生空队列也可能null/容量0。fresh Sampler每次取得新span，scoped Inspector仅在认证父控制窗口或Game桥接受对应current，不写游戏状态补齐假设。父原始scheduler内部即使持有Parent TLS也不属于控制窗口。

准备与发布顺序是：Prepare同一Owner/Gate/Parent→在可信发布窗口ArmOwner→发布两处Gate inline及一处父call→Gate/Parent Arm→自然父BEFORE初始化Controller/Host→配置真实邮箱IPC。全部生产代码编译链接已通过，尚无typed DLL启动导出、来源发布器或实际保存执行；准确作用域组合只验单期。producer锁仅协调本Runtime，完整输入和相关原生writer顺序仍需在实际保存验收中证明。下一项是独立真实新档，不能以编译产物代替。

`a_save_dispatch_mailbox*`把请求、宿主接纳和保存完成分开，兼容已有held IPC执行端口的函数签名。网络线程等待宿主接纳，不直接执行Controller；结果按身份深复制、一次交付，未知结果不重投。后续Host已经接实际pipe Server/Stop诊断组合；固定native room_epoch不等于网络每旬更换的timeline epoch。父调用本轮16帧保持同一TID且所观察任务尾部配对，但空闲样本不能泛化为所有阶段/全部后台工作的排空证明。

`b_reload_cold_wait*`在固定来源和对象身份下，通过真实线程上下文等待四个初始wait，成对恢复后仅调用一次后续入口。组件要求所有生产者服从可信宿主锁；这一契约尚未在游戏建立，旧Runtime也未接入此组件。不能拿一次扫描到的等待状态代替持续排他，不能重新使用旧RegisterColdPool claim。

后继 `a_save_dispatch_ipc*` 已将邮箱端口接入真实命名管道Server，并由独立monitor在Submit等待中检测外部shutdown/EOF；monitor只停止邮箱，Server继续保持具体Owner接口与认证/序列/结果检查。构建产物包含生产Server对象，组合测试中的Owner业务另由fixture TU替身提供。wire Stop仍是串行消息，不代替外部取消；析构也可能在生命周期宿主线程调用Owner.Stop。

`b_reload_cold_registration*` 已在实际初始化Bridge内调用原RegisterColdPool，保留真实Owner和原登记检查；新wait后继只接受明确已发布的activation Leave桥。新Prepare已经初始化生命周期，不能随后直接调用会再次Initialize的旧Bootstrap。下一步需明确Bootstrap后继使用同一准备入口，再接同Provider的完整queue；真实生产者锁覆盖仍不是传入一个SRW就完成。

最新 `a_save_dispatch_host*` 把管道邮箱接到实际Owner/Gate/Controller/Driver。BeforeFrame/AfterFrame是受信任的本地宿主边界，固定控制TID，提交前实际Begin/EndObservation；保存期间不重复观察，Driver完成后才Copy。停止后Copy接口拒绝，因此另从原Driver的同代Complete或零bind Cancelled收尾，只释放本宿主协作锁，保留Unknown且不放行下一期。调用Submit之前就标记可能受理，避免后验检查失败误解锁。

Host没有安装CApp/Root钩子，也未证明所有游戏writer参与锁；BeforeFrame返回false只表示本协调器不接纳操作，不能拿它阻止原生调度。原Owner的Stop可能转发User，保留Ready字段不等于全输入持续暂停。已有TLS/网络Scope路径尚未在本次新Host中重新组合；本次真实管道的两期数据仍是32字节诊断业务。

最新B接线已由 `b_reload_cold_bootstrap*` 完成：唯一Prepare与原登记、两代queue共享Provider，消除了上文原登记与旧Bootstrap二次Initialize冲突。SetEvent登记后切换是明确fixture服务，不代表原生引擎已完整接入；真实启动来源与生产者排他仍须单独建立。
