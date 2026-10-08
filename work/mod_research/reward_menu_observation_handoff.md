# 赏赐菜单只读观察后继（2026-10-08）

已交付可构建的只读观察器、草稿解码与配对分析、现有 CaptureSession 的不可发送
shadow 接线。**本轮完全离线；没有查找／打开游戏、Steam 或当前存档，没有安装
菜单拦截，没有请求玩家操作。** 仓库提交与当前总交接见 `docs/HANDOFF.md`。

## 这一步实际补了什么

- 新 `reward_menu_observation.cpp` 复用冻结 `a_save_observation.cpp` 的完整 debugger
  事件循环、所有线程 DR 租约、未知异常转交、待处理事件排空和恢复退出。交叉审查
  发现前驱未校验DR6事件归属，故新后继增加下述入场／清理检查；测试严格限定核心
  差异为include/comment及这几处DR6接线。旧源未改，不为保持逐字相同而保留缺陷。
- 新 binding 复用原进程出生身份、EXE SHA、PE、原生 User 状态、远端 ntdll 断点
  身份检查；只更换入口和9处小版本指纹。生产产物拒绝 fixture/其它进程名。
  不覆盖已有启用的 DR，不和别的 debugger/注入 Owner 同时试运行。
- 新共享 `reward_menu_observation_debug_status.inc` 把DR6的B0..B3/BD/BS/BT
  (`E00F`)作为事件所有权：初始租约若有未知事件位则拒绝，不在arm时清除；清理
  只允许原事件位、当前真实DEBUG_EVENT确认的owned trap，或精确冻结的待决
  RIP/DR6/layout。仅layout相同不能覆盖未知DR6，未知状态会保留debugger和线程，
  记录 `cleanup_foreign_debug_status_retained` 并使capture不完整。即使外部日后
  修复并正常detach，这条记录也不能从采证完整性判断中消失。A保存修复后继可
  共享这一实现，冻结旧A观察器仍不改。
- 四点现在为 `67A930`（Reward Update 入口）、`67A993`（wrapper call 前）、
  `626275`（公共 handler call 前）、`67A998`（wrapper return 后）。用 Update
  替代上一轮建议的 event1 tailcall 点，以获得真实草稿与选择变更；event1仍不解释
  为取消。四个执行断点均不跳过原指令，只在读取后正常继续。
- Update 的相同语义读数去重；选择、raw UI event、root/world/viewer/date变化均
  记录或在配对时拒绝。限定最多256条语义记录、12000个硬件命中，并保留冻结内核
  的20000条 debugger事件上限。达到上限判记录不完整，不能拿不完整记录放行。
- 原生断点回调中读取实际 reward state、人物指针列表、资金军团及城市，再读取
  wrapper 栈上的整数 ID 列表。RTTI、表索引、持有势力、池容量/slot、链表计数／
  环／重复人物、ID列表前后链均校验；最多观察64人，现有 CaptureSession 仍限16人。
- 记录同线程、同 reward state。wrapper 前后 RSP必须相等；公共调用处必须是
  `RSP = wrapper_call.RSP - 0x890`、`RCX = RSP + 0x30`、`R13 = reward state`。
  UI草稿与common整数ID草稿、资金城市必须相同。绝不把公共args栈指针交给异步执行。
- `reward_menu_observation_events.analyze(rows, metadata)` 检查连续序号、无漏样本、
  同进程出生/run/base、线程/栈、世界/日期/视角、完整收尾，并产生纯ID对照结果。
  wrapper返回但没见common、仅改选/未知event/空闲超时均为 `INCONCLUSIVE`；完整
  对照成功叫 `MENU_CALL_SOURCE_MATCHED`，不是赏赐执行成功、UI取消成功或拦截许可。

## 与现有 CaptureSession 的实际接线和可信边界

`capture_shadow(analysis, trusted_context, now_tick=...)` 将经过分析的真实读取形状
传入冻结 `CaptureSession.capture/confirm`，重复confirm同一对象，并验证本机viewer。
返回人员ID、军团和语义摘要，但 **`network_packet=None`、`network_submission_allowed=False`**。

这不是网络队列生产者：只读记录会让游戏自然继续，观察到的赏赐**可能已经执行**。
把观察记录再提交到房间会重复执行。真正菜单接管必须由下一版原生 Owner 在本地
执行前拦住命令；本模块没有做到，也不允许用 `shadow` 替代。

`trusted_context` 仍来自独立宿主，不接受远程客户端提供的 room/viewer/期次权限。
自有测试提供明确 fixture room/epoch/attachment/menu lifetime；这些身份没有
被冒充成真实游戏生命周期证据。当前只能证明所记录的地址段、日期和草稿一致：

- Update并非构造函数，state地址重复也不能证明是同一次菜单生命周期。
- 没有 destructor/退出观察点；停止、timeout或未再命中不代表取消。
- event1及输入门控分支都不自动映射为cancel。
- wrapper返回EAX不代表common处理器返回值，也不证明具体忠诚/金钱变化。
- snapshot观测、DR暂停采样都不提供后续持续输入排他或完整世界稳定保证。

因此所有结果始终 `native_suppression=False`、`menu_lifetime_verified=False`、
`cancellation_mapping_verified=False`、`production_permit=False`。

## 下次实际采证入口（本轮没有运行）

先在目标电脑构建并运行仅自有进程的测试，不需要私有原生dump或游戏安装：

```powershell
py -3 work/mod_research/reward_menu_observation_test.py
```

记录新的测试结果目录。工具默认无参数只显示帮助；实机入口要求显式正整数PID，
CLI和Python API均拒绝缺PID、bool/0/负数，不进行自动进程发现。

当用户方便且游戏已回到**34号基线张鲁空闲大地图**时，另行运行：

```powershell
py -3 work/mod_research/reward_menu_observation.py --preflight --pid <current-pid>
py -3 work/mod_research/reward_menu_observation.py --record --pid <current-pid> --tested-build <new-passing-test-directory> --seconds 180
```

preflight核对203年8月中旬、张鲁/666、规划phase2、原始User/Game入口、无其它
debugger和九个小指纹；record在创建独立运行目录后再次检查构建/源码/产物身份，
原生端再核对pid出生时间/EXE/原入口/正式User。测试摘要改变或产物不符即拒绝。
新电脑不能复制旧PID、地址或原电脑运行目录来放行。

只有出现 `READY_FOR_MANUAL_MENU_OBSERVATION` 才安排用户操作。

1. 可先打开赏赐菜单、改选并取消，停止记录后检查Update/raw event和空记录含义。
   这一轮预期可能 `INCONCLUSIVE`，不会因没有common就自动宣称已找到取消路径。
2. 再用独立新run做一次正常确认，核对菜单前草稿→wrapper→common→wrapper return。
   **正常确认会产生游戏自身赏赐效果**。需要主线程在当时安排基线/收尾/恢复；
   本工具不执行存档、读档、点击或撤销。观察到一次wrapper return后自动收尾。
3. 最终 `result.json` 必须有完整序号、配对和 `cleanup_verified=true`。观察器还活着
   或有 `cleanup_pending` 时不得强杀；工具写 `.stop` 后保留恢复流程，先处理未决事件。

这轮记录将回答已读到的布局是否与真实菜单一致。仍须另查完整菜单生命周期和
安全取消/关闭来源，之后才能设计真正阻止本地先执行、交权威排队的原生捕获 Owner。

## 测试结果及冻结身份

最终：`reward_menu_observation_test_runs/20261008-202730-916615/result.json`，
**60/60 PASS**，其中9项真实自有进程debugger测试、22项原生自有内存sampler/context
情景，其余为来源分析反例、继承内核差异与入口拒绝检查。

- debugger：正常命中、timeout、取消、错误出生身份、生产拒fixture、外来DR、未知
  SEH/INT3转交、并发旧断点布局待处理、采样异常时完整清理。
- sampler：匹配/改选、wrapper没进common、event1、空选择、未返回，以及错误类型、
  viewer/栈、重复/环/超量人物、资金城差异、ID差异、公共frame错配、嵌套/孤立调用。
- C++ decoder输出直接与现有真实 `DomesticDecoder` 的 bytearray fixture比对，随后
 进入已有 `CaptureSession` shadow；这些内存、CONTEXT和生命周期是明确测试数据。
- 实际硬件调试测试使用冻结的tick fixture验证继承的DR内核；**菜单四点语义尚未在
  真游戏线程执行**，原生自有内存sampler使用显式CONTEXT模型，不混称实机菜单成功。
- 捕获后序号缺口、丢失、换进程/run/world/viewer/date、截断返回、错误字段/ID，
  以及清理阶段漏记/达到上限全部不能产生可发送请求。
- 额外的DR6 fixture有26项内部检查：9次真实自有线程Set/GetContext读回，以及
  17项显式CONTEXT事件归属模型。本机Windows将外部SetThreadContext请求的E00F
  位清掉，9次实际读回中非零事件位数量为0；**不能把请求位当作实际硬件事件**。
  模型验证BS/BD/BT/多点事件不会被恢复、精确owned/pending才允许；实际未知DR6
  出现后保留debugger的整条现场路径还没有被这些模型证明。
- 所有24份新源/冻结依赖测试前后哈希一致。源码无游戏搜索调用，测试不运行实机入口。

中间 `201424-200749` 的56/56、`201724-151347` 的58/58记录保留。DR6修复后首跑
`202529-540339` 构建成功但status fixture失败：它错误假定OS保留请求的B0位，
实际读回为0；按真实读回与显式模型拆分证据后重新全测60项。失败目录保留，没有
把旧成功摘要冒充修复后的结果。生成器最初一次默认GBK读取UTF-8前驱失败，尚未
产生launcher文件；显式UTF-8重读后生成。旧源没有被写入。

| 项目 | SHA-256 |
|---|---|
| 最终 result.json | `8a1e724c48eb09e345d2420979f8fb5fff4549a6bc76d6aab6a07b9cd6dd944c` |
| observer.exe | `713a3bfd5801c28a6eeb20b9bac9e1c4419cb5989989d7dc65d625c06cf76f5d` |
| `reward_menu_observation.cpp` | `83bef47ee1767d25e1a369120aec42597d23dc8b902ed002838b888cdbbdedc5` |
| `reward_menu_observation_payload.inc` | `8bdd6e0b2e7420104ad66a07b89b9135497b8f37c4fde7e1e0c844639dbc2c5d` |
| `reward_menu_observation_decode.inc` | `aa16d34f9cc89663774525919cc6c20309dafd9a704c18e83dbe3c0ecb9c328e` |
| `reward_menu_observation_debug_status.inc` | `2337f57a2b9cb284dccb9020be876a65c96bddedc81cb087772d348c31b56ef7` |
| `reward_menu_observation_status_fixture.cpp` | `20c8a4fe0f45a4d2bac27c8439621a65b5ed5dcf930cfdc5d2fd1ea250838595` |
| `reward_menu_observation_binding.inc` | `821b5670a7ba8c147b437080e06e6b14ccd8829510b1f45ab875e402e23a6770` |
| `reward_menu_observation_anchors.h` | `1dcbd1a6fc3fcd420a570ea083267ed74b1c6bd747f24885d36178e16bfb6c72` |
| `reward_menu_observation_semantic_fixture.cpp` | `63053bfac55e52cb120a8628e448d79b1c4445c93e9607e4dbbf64b6635d5b19` |
| `reward_menu_observation.py` | `355a58db6dbeb0f575d1d41d72ed89be52b5a4526ac701ab23a728d78b6a6b44` |
| `reward_menu_observation_events.py` | `360bee653cb749e5846af56721e567f1bd5512475b0b4cda71c21242d71c7e86` |
| `reward_menu_observation_test.py` | `704487a028f1e35e93ca81373ee5e66800956682fed4e2e6b192835aa58cf569` |

九个小指纹取自已有私有归档（与上一轮相同SHA），提取前后重新哈希一致；没有发布
完整函数或转储。最终工具构建及自有测试不依赖私有归档。

当前没有活动调试器、补丁或等待用户操作；仅为下一次有计划的真实只读采证准备。
