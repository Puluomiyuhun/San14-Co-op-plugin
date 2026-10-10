# 三国志14双客户端联机：当前交接

更新：2026-10-10（Asia/Shanghai）。本页替代旧的滚动交接；历史记录见 [CHANGELOG](CHANGELOG.md)。本次是用户明确要求的代码与交接提交，不表示以后每轮自动提交。

## 先看结论

**尚未实现两台真实游戏连续多旬出兵、赏赐的完整闭环。** 先验收“同日开局＋两次旬末”，即三份检查点、两个可操作阶段；不是不限回合系统。已完成的组件、诊断入口和测试不能拼接成已经实机成功的结论。

本次整理自上次提交 `c5ead23` 后积累的源码，包括赏赐原生接口、菜单与结果观察、输入控制、远端配置工具、三检查点链以及出征接单。不要只取最新几个文件而漏掉同次提交的依赖。

用户目标：A、B各运行一份游戏，各操作一个势力，其余势力由AI控制。A权威排序指令，双方准备后推进；旬末A生成新存档传给B，B恢复本方视角。接受首版窗口/无边框、战斗动画可能不同步，旬末世界以A为准；不接受远程桌面替代。完整暂停事件选择、断线恢复、无限回合与加载画面遮罩仍未完成。

## 本次已完成什么

| 部分 | 现在可以证明的内容 | 边界 |
| --- | --- | --- |
| 三检查点存档链 | A三次保存、两个推进阶段；B三次加载、正式回执和网络收尾已有后继入口及离线组合 | 诊断要求不新增命令；保存/加载游戏作用有历史分阶段实机证据，但三代新组合不是两台游戏实机证明 |
| A两窗赏赐原生层 | 同一Runtime两个窗口、四次赏赐、三次保存；新版生产DLL、实际导出调用和ABI核验完成 | 自有宿主中的游戏业务替身；新DLL尚未接入正式房间mount与批准安装链 |
| B两窗赏赐 | 每窗独立native owner、上下文和SQLite日志；先核验旧桥退休再开下一窗；保留共享unknown状态和一次性记录 | Python生产接线执行过，原生业务/加载/房间在此测试中为替身；正式runner未装配 |
| 输入跨旬 | 同一输入owner逐检查点重绑；room epoch与原生奖励epoch明确映射；Ready前必须实际LOAD确认 | 只覆盖已审计窗口消息，不代表全部引擎输入排他或菜单已拦截 |
| 出征 | 当期房间接单、TLS席位/期次绑定、去重、待处理命令阻止Ready | 原生执行默认关闭，不能把接单当成已出兵；仅接受已有固定pilot命令合同 |
| 菜单/赏赐结果 | 提交、生命周期、取消、关闭保护及结果观察/差量/频道等研究模块已入库 | 仍未完成正常游戏菜单到双端执行和UI刷新的整体接入 |

赏赐共享同一个未知结果阻断状态；失去原生调用结果后不重试。已修正：预装输入首窗使用另一份state、先发Ready再进入LOAD、输入窗口与赏赐锁的获取顺序。第二窗不能复用第一窗的上下文、日志、native owner或一次性claim。

## 从哪些源码接着做

### 三检查点诊断链（无新命令）

- A：`a_save_three_exports_build.py`、`a_save_three_build_approval.py`、`a_observed_three_start.py`、`a_observed_three_native_control.py`、`a_observed_three_boundary.py`。
- 房间：`observed_three_room_service.py`、`a_observed_three_room.py`、`a_room_three_protocol.py`、`checkpoint_three_save_binding.py`。
- B：`b_observed_three_start.py`、`b_remote_chain_session.py`、`b_observed_chain_completion.py`、`b_warm_chain_resident.py`、`b_warm_chain_coordinator_*`。
- 三份检查点是bootstrap、第一旬末、第二旬末。第四份明确拒绝；B保留三代模块，不能卸载后偷偷复用。

### 两窗赏赐与输入（新组件，尚未替换诊断入口）

- A核心生成器：`a_runtime_reward_three_sources.py`；正式导出：`a_runtime_reward_three_exports.{h,cpp}`、`a_runtime_reward_three_exports_sources.py`；精确Python合同：`a_runtime_reward_three_contract.py`。
- 新构建schema：`san14.a-three-reward-exports-build.v1`。它不同于纯三保存构建 `san14.a-three-runtime-exports-build.v1`。**不能用旧 `a_save_three_build_approval` 的通过记录批准新奖励DLL。** 仍需新批准逻辑、publisher绑定及房间mount。
- B：`b_chain_reward_native_port.py`、`b_chain_reward_session.py`、`b_chain_reward_flow.py`。
- 输入：`player_input_rebind_*`、`b_chain_input_transition.py`、`reward_rebind_context.py`、`b_chain_reward_input.py`。
- 目标调用顺序：保留输入owner并保持LOAD → 完成本次正式加载 → `rebind_after_load` → 新 `RewardSession.open` → `Window.open` → 赏赐 → `Window.finish_input` → 共享队列收口及旧桥还原 → `ensure_load_before_ready`实际确认LOAD → 才启用下一次加载并发Ready → `prepare_load`复核 → 下一检查点。
- 不要跳过输入安装、复用测试中的held布尔或伪造Session。测试的 `Harness`、`__new__` 和替身仅用于离线验证。
- 旧 `reward_planning_discovery.py`、`a_reward_runtime_mount.py`、`b_reward_runner.py` 等仍限定第一窗/旧两代。新组件并没有自动使这些旧入口支持第二窗。
- `a_simple_remote_host.py`、`b_simple_remote_guest.py`、`b_input_reward_runner.py`、`b_portable_guest.py` 仍是旧两检查点路线，不能用来声称三检查点与两窗赏赐已装配。A新 `a_observed_three_start.py` 提供 `RoomEntry + execute`，CLI仅展示接口，并非已经完成外层房间配置启动器。

### 出征

- `sortie_room_admission.py`复用既有PeriodCoordinator的pending/Ready屏障。远端无权声称执行成功；目前只能由可信本地执行前拒绝清除提案，执行接口明确关闭。
- 历史实机pilot固定张鲁/宛/1300兵/指定阵形到长安；`sortie_reader.py`的输出仍是partial_order，缺behavior_settings。`live_draft_demo`仅传草稿。
- 已有AuthorizeSortie/ReplaySortie受控原生转发基础，不能说完全没有原生入口；但完整菜单捕获、A/B不同势力的合法性及拥有参数生命周期的执行器、与赏赐共享排序和双方执行回执尚未接通。

## 下一步：按此顺序推进

1. **把两窗赏赐装进三检查点正式流程。** 新A奖励构建批准/发布器 → 新房间每旬discovery与mount → A/B当前期绑定 → 输入owner与规则保护按序安装、退休。旧第一窗discovery不能用来冒充第二窗。
2. **补出征的真实执行链。** 完整纯ID指令、玩家归属/资源/参数检查、抑制本地重复执行、A/B原生执行器、与赏赐同序列及双端回执、跨旬重新绑定。不要解除现有admission的执行禁止而跳过这些条件。
3. **补正常菜单入口并验收两机两旬。** 两机版本/本地构建/连接配置核验；开局各自势力 → 双方出征/赏赐 → Ready → A推进/自动保存 → B加载 → 下一旬再次操作。然后才扩展更多回合和体验优化。

A AI保护已有独立保护入口及历史规则测试，但必须验证在新的奖励三代流程中共存；不能拿B规则或旧保护入口的PASS替代新A组合证明。其他内政仍未完整支持，不要报“全内政已接”。

## 最新可复核证据

本次只整理/验证离线代码；没有访问游戏、Steam存档或UI，没有安装新游戏钩子/调试器。不重新查询进程，因此不推定当前游戏已关闭。此刻没有要求用户操作。

公开摘要：[2026-10-10多旬开发快照](evidence/2026-10-10-multiturn-snapshot.json)。它只提供来源与范围索引，不能替代原始记录或用作安装放行。

| 套件 | 结果 | 测试层次 |
| --- | --- | --- |
| `a_runtime_reward_three_exports_test.py` | 2个原生场景通过；26种结构ABI和15个生产导出入口核验 | 自有宿主实际新导出、生产DLL加载检查；游戏业务替身 |
| `b_chain_reward_test.py` | 16/16 | 真实Python工厂、SQLite与内存投影；原生/房间替身 |
| `b_chain_reward_input_test.py` | 7/7 | 两窗赏赐/准备/LOAD/重绑；输入RPC、原生和加载替身 |
| `b_chain_input_transition_test.py` | 8/8 | 真实TLS、正式三检查点回执；窗口RPC/加载/规则替身 |
| `sortie_room_admission_test.py` | 8/8 | 真实TLS、SQLite和Ready屏障；零出征原生调用 |

历史真实游戏验证包括A同进程跨旬两次自动保存、B同进程读回两份档并保持刘备视角，用户曾确认画面。这些是分阶段证据，不等于本次两机联机成功。此前失败运行全部保留，不通过删除claim重试旧进程。

## 本地验证与其他电脑限制

仓库根为 `work/san14-coop`；源码在 `work/mod_research` 与 `outputs/san14-link`。本机私有证据为**仓库旁的** `../mod_research/*_runs/<run>/result.json`，不是全部在仓库内。公开摘要用相对此私有根的run名及SHA标识。

离线验证（从仓库根执行；会创建独立测试记录）：

```powershell
py -3 -B -X utf8 work/mod_research/b_chain_reward_test.py
py -3 -B -X utf8 work/mod_research/b_chain_reward_input_test.py
py -3 -B -X utf8 work/mod_research/b_chain_input_transition_test.py
py -3 -B -X utf8 work/mod_research/sortie_room_admission_test.py
```

原生导出构建测试为 `py -3 -B -X utf8 work/mod_research/a_runtime_reward_three_exports_test.py`，需要本机MSVC/Windows SDK及经哈希固定的私有构建输入、历史fixture。其他电脑仅clone源码不能保证重建这些研究测试；不要复制本机PASS、PID、地址、密钥或claim作为放行。缺私有输入应明确报告并重新建立当地证据，不能删校验。连接工具与portable模块已入库，不等于有可直接发朋友的一键完整玩法包。

具体依赖包括私有 `checkpoint_push_profile.h`、`checkpoint_planning_hold.dll/.lib`，`a_native_turn_mode0_runs/20261009-232744-407945`，`a_runtime_reward_planning_runs/20261010-021152-669026`，固定哈希的 `game-runtime-image.bin`，以及B旧factory/refresh-pair/rules-publisher构建。部分生成器还校验绝对路径或历史来源哈希；跨电脑须重新生成或提供经验证的完整构建包，单独复制result.json无效。Python依赖含pefile、cryptography，部分分析测试另需unicorn、capstone。新 `.h` 生成物应由对应生成器产生，不逐文件直接编译。

仅公开自编源码、文档和脱敏摘要。游戏EXE/DLL、构建DLL/EXE、其他存档、内存/原始日志、连接私钥/邀请凭据不提交。唯一获用户授权的存档例外仍是 `fixtures/saves/slot34/svdexSC34.s14`；本次未添加其他存档。
