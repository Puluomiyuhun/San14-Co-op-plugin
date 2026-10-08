# 进展记录

## 2026-10-09 — A真实管道与邮箱组合，B实际调用原冷池登记

- A5/5：独立客户端进程、实际Server/管道/邮箱两期传输，原packet编码及Python解码通过；连接EOF与外部shutdown在阻塞Submit期间停止邮箱，未领取与已领取分别取消/未知，不自动重试。Owner本体和游戏业务仍是替身。
- B8/8：实际生命周期Bridge内冷等待后调用一次原RegisterColdPool；精确接受已发布activation桥的IAT身份，修复两个原组件直接拼接的冲突。原注册真实验证/发布四worker，负例不重试claim；远程Bootstrap/完整queue仍待组合。
- 交叉审查、源码产物身份和自有线程收尾均核对。全部离线，不新增实机操作；细节见最新交接。

## 2026-10-09 — 保存请求跨线程转交与冷等待协调

- A邮箱和held IPC执行端口7/7自有线程测试：两期记录、并发去重、宿主接纳后才回应、一次交付、超时/Stop未知不重试；真实Root/Server/Serializer尚未接入。
- B冷等待12/12：真实线程暂停/上下文展开、延迟到初始等待、错源/已暖/事件/句柄变更拒绝，四worker及六个锁正常收尾。尚未接旧Runtime，不证明全游戏生产者隔离。
- CApp父层归档4/4定位调度旁路及前后业务，不能把父返回当全部任务完成。全部离线，失败记录保留，详见最新交接。

## 2026-10-09 — 同一Bootstrap运行环境接两代加载队列

- B同PE/DLL/Provider四worker后两代队列2/2，覆盖普通与输入yield；首代收尾后经Gate开第二代，保留旧回执。构造/业务、部分fixture宏和第二份诊断变体仍明确，尚非真实连续读档。
- 修复真实模块归属、展开范围、代码页保护、占位worker遗漏临界区及Runtime实例启动归属；保留所有失败。自有进程启动前有界等待额外线程自然退出，没有放宽生产线程检查。
- A3/3执行两次真实User生命周期和回调容器操作；phase5负对照不被保存pop修成规划态。序列化/Root邮箱/完整输入与writer保护仍缺。
- 冷启动2/2归档父链审计定位构造返回不等于初始wait到达；OS调度为模型。全部离线，无游戏操作请求。详见[交接](HANDOFF.md)及分层证据。

## 2026-10-08 — 正常保存实机观察与同PE启动四线程

- 用户手动保存49号：1次完整Save配对、0次army任务；102线程寄存器恢复并退出。仅证明本次无观测重叠，不授予生产保存许可。
- 83份原档已备份并校验，只有49号变化；34号与其余82份不变，原49号备份保留、尚未恢复。
- B新组合2/2：同PE/DLL/Provider实际Bootstrap→四worker→普通无票任务→正常收尾，真实系统临界区；修复主PE unwind与空池页面准备。两代queue、真实来源阶段和两合法档仍缺。
- 独立复核冻结A模型4分支，未追加实机操作。连接诊断包准备和自检通过，尚无异地连接。
- B147份来源及6份产物、观察器20份来源身份重核；失败记录保留。交接与证据见[HANDOFF](HANDOFF.md)。

## 2026-10-08 — 完整Scope、原生日期边界与同进程两期保存

- 原生边界16/16：同epoch/period推进到实际诊断旬末日期，新观察才可Save/Copy；异常/错日期/来源漂移等拒绝。
- 组合8/8：实际Room Scope进入原生Session；同Owner日1→11→21，两份诊断数据经真实管道/TLS/STAGED，模型B完成后才正式退休重绑下一期。完整两期身份与日期衔接已接，真实引擎与合法档未验证。
- Session明确后继保留旬初Scope，接精确成功边界的旬末Receipt；真实错scope/epoch/cut/日期反例保留旧检查。
- B只读审查定位主PE、Provider、真实临界区及页面重建冲突，给出同一所有者接四worker再两代queue路径，未新增B成功测试。
- 88份独立源码及产物核验；失败保留，未触游戏/当前档/UI，共享34号未变。见[交接](HANDOFF.md)及[证据](evidence/2026-10-08-scoped-native-two-period.json)。

## 2026-10-08 — 保持Ready保存、阶段身份与实际Bootstrap

- 保存22/22：新专用入口保持Ready/Gate，封存实际观察防止查询刷新掩盖过期；结果Copy前禁止退休/释放，普通Submit行为不变。
- 管道6/6：实际自有进程保存/Copy接TLS及STAGED；旬初scope与旬末存档日期分开，明确原生推演后日期阶段尚未组合，B loaded仍模型。
- B启动7/7：导出实际初始化/发布/Arm，人工准备自有映像成功及来源/线程/IAT/池/重复反例；真实游戏就绪阶段与四worker队列组合仍缺。
- 213份独立源码和产物重核；保留失败，未触游戏/当前档/UI，34号共享副本未变。见[当前交接](HANDOFF.md)和[证据](evidence/2026-10-08-held-save-bootstrap.json)。

## 2026-10-08 — 跨旬保存管道、父层协调与连续加载故障

- A跨旬管道8/8：最新Period Owner/Gate接实际IPC、TLS与接收日志，正式退休/重绑后完成第二诊断保存；主动停止拒绝第二次及旧导出。尚未合入完整网络scope Session，生产permit保持关闭。
- 保存父层协调11/11：正常菜单七栈与归档Root/Game/Save顺序执行，确认等待Update不覆盖另行启动的army后台生命周期；有状态转换队列屏障正对照。OS线程/外围服务替身，不声称实机竞态或坏档。
- B启动/故障3/3：健康两代完整加载队列、两代各自输入观察回调SEH；真实本地闸拒绝故障后的下一代注册/打开，保留原代历史。保留首轮错误拒绝正常Session.Stop的失败与修正依据。
- 全程离线，未触游戏/Steam/当前存档/UI；无实机补丁或待用户操作。见[当前交接](HANDOFF.md)与[分层证据](evidence/2026-10-08-period-pipe-parent-reload-fault.json)。

## 2026-10-08 — 驻留窗口跨期、网络身份映射与菜单关闭队列

- Session21/21：完整网络epoch映射到本地binding，保留累计指令编号，正式退休/重绑后只接受新Controller；协议加载回执仍模型。
- 驻留窗口10/10：含实际Session组合，同一入口保持已审计消息hold直至新期实际ACK；不释放/重装。修复错误后意外转发输入的审查遗漏，保留反例与中间运行。
- 菜单收尾59/59：定位无菜单身份的pop队列，消费时栈顶可能变化；以归档CPU反例和只读APPLIED日志关联明确缺口，未新增自动close许可。保留fixture缺恢复入口导致的AV失败。
- 97份独立源码摘要统一重核，全程离线，未触碰游戏/Steam/当前存档/UI；真实新档/连续加载、全输入和生产宿主仍缺。见[当前交接](HANDOFF.md)与[分层证据](evidence/2026-10-08-resident-session-menu-completion.json)。

## 2026-10-08 — 确认前原生暂留、窗口消息边界与同world跨期

- 菜单67/67：归档Update确认前阻止自然执行、单次纯ID领取；实际清理/析构片段拒绝旧提案，接既有CaptureSession/TLS去重。业务效果模型，未完成真实菜单安装/正常关闭/lifetime。
- 跨期31/31：同物理Owner两期奖励和两诊断保存，保留累计编号、退休记录及旧消息拒绝。修复旧Controller退休后先释放Gate的顺序缺陷；窗口线程可只读Snapshot，变更仍限定可信线程。
- 窗口独立6/6、正式跨期链接7/7（六个回归加一条组合）：执行自有HWND消息和归档WndProc、来源退休与新实例接管，并与Period.Retire/Rebind组合。未知消息、设备/写入、窗口发布竞争与release间隙仍未覆盖，不发完整输入或推演许可。
- 保留构建/回调异常判定失败和Win32发布竞争反例；92份独立源码摘要统一重核一致。本轮未触碰游戏/Steam/当前存档/UI。见[交接](HANDOFF.md)及[分层证据](evidence/2026-10-08-menu-window-period.json)。

## 2026-10-08 — 菜单来源观察、同Owner输入隔离与启动加载队列组合

用户暂不方便操作，三路全部离线推进，未触碰游戏/Steam/当前存档/UI，无待操作请求。

- 输入后继18/18：User fence与Game/global UI/panel观察绑定同一Owner，拒绝来源/日期/槽/版本漂移；完整输入、保存、推进权限保持false。新端口接旧Ready/TLS双原生组合13/13（11流程+2结构检查）。
- B生命周期+完整queue4/4：原四线程启动一次，同一已暖worker两代16任务/48捕获、两次queue pop；真实yield/resume及每代普通任务通过。构造器/业务仍替身，第二文件仍诊断变体。
- 真实菜单只读观察工具60/60：明确PID与已测构建，四点当场解码、配对、严格退出；取消/lifetime仍unknown。没有生产捕获拦截；已自然执行的记录禁止重新提交。
- 交叉审查修复观察器退出时可能覆盖外来DR6事件状态的问题，菜单与正常保存后继共用归属guard；保存后继39/39。共享guard的9次OS读回与17个CONTEXT模型分层记录，未把OS不保留的事件位写成实际触发。旧源码冻结、失败保留。
- 保留组合中的构造服务/跨代参数及断言修复、输入release测试失败。明确单规划期绑定不能直接跨旬复用；A真实新档及两合法档实机仍缺。见[当前交接](HANDOFF.md)和[证据](evidence/2026-10-08-menu-interlock-reload-composition.json)。

## 2026-10-08 — 双端Owner等待回执与赏赐菜单确认前捕获准备

三路离线开发及交叉审查，旧模块保持不变，未操作游戏/Steam/当前存档/UI，无新游戏补丁或待操作请求。

- 新Ready worker8/8：设置请求与实际观察分开；通过已发布User入口确认原生增量0/0、FINALLY增量1，拒绝过期revision、排队、保存、活动/未知状态及换world。
- 新房间后继Python19/19、原生组合11/11：A/B赏赐排空后绑定同一challenge/cut，双方实际等待观察，B签名、A复查后确认；重复回执不重调setter。串入两视角菜单纯语义提案去重→TLS→双原生执行→fence的组合。
- 菜单53项语义、16项归档检查通过；确认前候选67A993，不能靠公共处理器返回0模拟取消。145字节UI Update为实际归档，其外部callee仍替身，取消及真实菜单收尾未确证。
- 修复并发晚成功覆盖UNKNOWN、报告采样中换实例、IPC响应串配和并行测试目录名碰撞；失败保留。局部Owner证据不等于全输入排他，原生推进/full-world权限仍false。见[交接](../work/mod_research/reward_ready_flow_handoff.md)与[证据](evidence/2026-10-08-reward-ready-menu.json)。

## 2026-10-08 — 赏赐同Owner与现代房间双端离线组合，交易/移动提案

三路并行开发，复用冻结Room/TLS、ExecutionJournal及PeriodCoordinator，不操作游戏。

- 新赏赐/保存Owner **11/11**：同一User/Save发布槽，连续两次、保存前后互斥、Ready/hold/取消/异常/错world；新增持久双视角fixture供网络集成。生产对象编译通过；业务效果仍替身，失败运行全部保留。
- 新房间流程 **Python21/21、原生组合13/13**：独立B和两份日志、两持续原生fixture，经TLS统一A/B提交顺序、执行端重验、真实回放/容器清理、双方独立结果核对。修复报告伪造、宿主异常未HOLD、迟到确认误停；实际执行报告用独立adapter key认证，真实密钥引导和原生Ready仍未接。
- 交易/武将移动 **76/76**：不可变能力清单、版本化纯ID提案、独立可信资格/成本/时限观察契约，缺证据拒绝放行；2项直接连现有decoder。没有新增两类原生执行能力。
- 未改冻结前驱，未访问游戏/Steam/当前存档/UI，无新游戏补丁或待用户操作。完整世界、菜单更新、异地双机、保存/连续加载主线仍待验收。见[证据](evidence/2026-10-08-domestic-offline-integration.json)和[赏赐接线交接](../work/mod_research/reward_room_flow_handoff.md)。

## 2026-10-08 — 内政同步覆盖与离线开发盘点

按用户问题，三路只读审计现有源码和历史证据。新增[内政状态表及工作包](DOMESTIC_SYNC_STATUS.md)：区分赏赐局部实机、交易/移动草稿、施政/登用/搜索等候选入口及未映射菜单。确认现代房间和执行日志仍只接受赏赐，最新A Owner未整合旧Dispatcher队列；没有双游戏即时属性/UI更新证明。

列出可并行交付的唯一Owner赏赐接入、TLS与双端执行回执、通用契约、交易/移动适配、内政分配decoder和事件流程；复用已有日志/鉴权/准备组件。这是审计文档更新，未新增游戏执行能力。便携检查18项单测、17项TLS具名检查通过；pefile缺失、私有输入未配置，未跑原生测试。未访问游戏/Steam/当前存档/UI，无新补丁或待操作。[本次证据](evidence/2026-10-08-domestic-sync-audit.json)

## 2026-10-08 — 单次保存观察工具与B启动生命周期

用户暂时不方便操作，继续多agent离线开发、独立审查与整合。没有打开游戏进程、访问Steam/当前存档或操作UI，无新游戏补丁/调试器，冻结前驱不变。

- A正常保存观察器34/34：四硬件点与严格Save/worker配对分析接通；默认仅帮助，显式record需完全匹配的已测试产物和当前游戏身份。补齐清理时漏样本、异常/退出、事件上限及计数不符拒绝，无Save干净超时保留无结论。实际游戏观察尚未执行。
- A原生协调48/48，定位普通与内联队列生产者，确认16C160含清理副作用。模型41、原生片段6、静态1分层记录；没有把无重叠、active=0或原生join调用等同完整排空。
- B新启动来源2/2，实际四线程初始化接初始等待注册，一次普通任务透明，同一worker两任务6次Root捕获；真实构造抵达初始等待的时序仍待证。新进程DLL加载器独立2/2并重复10次，修复调试事件句柄生命周期；尚未提供游戏Bootstrap/发布器或验证真实启动运行时代码。
- 中间失败全部保留，最终171份依赖源码摘要重核一致。四道实机验收门槛仍按真实结果计；下一次最小人工步骤是单次保存观察，不是启动完整双人房间。见[公开证据](evidence/2026-10-08-native-save-observer-startup-lifecycle.json)及[交接](HANDOFF.md)。

## 2026-10-08 — B自动接入完整队列与异常组合，A后台writer范围确认

多agent离线推进、主线程整合与交叉审阅；未访问游戏、Steam、UI或当前存档，无待用户操作，冻结生产源未改。

- 新activated queue将真实自动激活接到两代完整queue/Title/User/Load，4/4；同一原生worker、16个Root任务、48次捕获、8个Load任务。实际输入yield恢复不重复创建任务，已有运行池仍不支持。
- 新nested fault 30/30含26回归与4实际故障；新activated fault 3/3将Observer异常、业务SEH与DR冲突接到真实自动owner。保留子层错误、任务abandon和恢复不确定性，不伪造正常完成或Ready。故障测试仍为隔离单任务，生产异常唤醒未完成。
- 新writer scope审计17/17，关闭warm 509640写入疑点；归档Game在Save pending下仍可启动army后台更新，实际army+48写入进入原生序列化字段。路径搜索/OS线程/memcpy明确为替身。保留已有原生协调待查，未宣称损坏、排空或生产permit。
- 完整两档/双机验收仍未通过；源码、产物、失败与精确边界见[公开证据](evidence/2026-10-08-activated-queue-writer-scope.json)和[交接](HANDOFF.md)。

## 2026-10-08 — A上游来源、B原生暂停恢复及自动线程接入

多agent离线开发与交叉审阅；未操作游戏、Steam、UI或当前存档目录，无待用户操作，冻结前驱未改。

- A新upstream gate将同一User来源移到3F9B16，使用原短收尾3FA0AE；透明路径尾跳原singleton。新Owner只接受登记的5字节来源，报告块恢复原样。29项同Owner保存组合及7项归档审计通过；对象/updater副作用有实证，其他writer与生命周期仍未全部排他。
- B新yield parent解决resume后50B598被误当fresh creation的问题。26项通过，实际归档暂停、reset和resume在Root及两代输入观察中运行，保留同ticket；第二个输入文件仍为诊断变体。
- 新root activation独立3/3，使用已核对的初始wait发布与实际IAT调用来源，支持同一长寿命runner为每项任务自动接入，并保留异常外层FINALLY；独立验证不等于完整queue/实际游戏接线。已有运行池不支持首版安装，不能回填成功。
- 保留fixture声明顺序、临时状态重建、预期计数、callable复制和构建失败；交叉审阅补强vtable固定、IAT身份核对和不确定恢复报告。见[公开证据](evidence/2026-10-08-upstream-yield-activation.json)及[HANDOFF](HANDOFF.md)，结果与源码摘要以最终冻结记录为准。

## 2026-10-08 — A早段门禁和B嵌套观察器完成组合

多agent并行实现、主线程整合及交叉审查；未操作游戏、Steam、UI或当前存档，无待用户操作。

- A新early gate实际替代旧action gate，同一Owner持有Game panel和前移User两处来源，接report Owner两保存。25/25：保留晚到报告、阻断旧User消费后的本地ABA，cmp flags/AV FINALLY/逐点unwind及源漂移拒绝通过。外部ABA与更早updater仍有反例，未发生产permit。
- B新nested后继按真实Root阶段保留return/yield，给User输入、Load start/join借用空余DR，保留旧ABI。3个完整两代queue场景各16个Root任务、48次实际Root上下文、8个Load任务；加前驱/独立Root/lease契约合计24/24。激活与业务仍fixture，第二文件是诊断变体，非双实机。
- B保留四轮失败：先遗漏User admission也是DR owner，后发现Set/Get真实规范化DR6保留位和DR7固定bit10，原逐字节比较误拒绝。仅修新后继比较语义，实际地址/控制/事件位仍严格核验、原始报告不改。没有重置旧claim或放宽占用。
- 更新首测四门槛及精确缺口。A/B最终167份独立源码指纹重核一致；见[证据](evidence/2026-10-08-early-gate-nested-observers.json)、[A交接](../work/mod_research/a_save_early_gate_handoff.md)、[B交接](../work/mod_research/b_reload_nested_handoff.md)。

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
