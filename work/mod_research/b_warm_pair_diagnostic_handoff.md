# B 两档无新命令诊断：可执行后继与离线验证

2026-10-09。入口为 `b_warm_pair_diagnostic.py`，复用原 `Resident/run_two`，不绕行严格 RemoteOwner/WorldLifecycle，也不填写虚假的输入锁 callback。这里只测同一游戏进程连续加载两份事先准备的合法档，首次可将 A 视角转为 B；不推进游戏、不建立网络房间、不安装双人 AI 规则。玩家在诊断期间不下令、不保存、不另读档、不推进、不修改其他 mod，是明确的人工条件；`--no-new-commands`记录这个条件，不能证明机器禁止了输入。

## 已检查的实际依赖

在本轮仓库 `acd517f` 基线上，旧生产构建文件和来源闭包仍可用，无需仅为本诊断重编：

- Pair result：仓库外 `work/mod_research/b_warm_factory_pair_runs/20261009-181448-912475/result.json`，SHA `c13390840e1fbeaf54fde8822add15ef9c44a75967b8c57ea2da2af73247a990`。89 sources、11 private、10 generated、67 binaries 均复核一致。所选生产 bank 为同目录 `composition/production/checkpoint_complete_live_owner_v2.dll`，SHA `e9766e073b4a4b63d230c1f7e788d477c4f5ebb7e660a2ed3dcc5b7c8342bf05`。
- Helper result：仓库外 `work/mod_research/b_warm_coordinator_build_runs/20261009-181031-457801/result.json`，SHA `4204df275c981b6c35c6bea01a25e040a0cea04be84e20ff2998079917e3b43a`。25 sources、3 generated、7 binaries 均复核一致，没有 private 字段。生产 `coordinator.dll` SHA `ba1c3f1ea7ae365be118807c38561bc01cf4765bbdd5b19d0c59c1525420b5e4`。helper 的全部 C++/头文件来源与 pair pins 一致。

本轮没有加载这些 DLL，没有打开游戏或 Steam 文件。旧 pair 的两代完整 factory 是自有进程测试，菜单、引擎加载及世界业务仍有明确替身；这份生产 DLL 尚不能因为“编译通过”直接称实机验证通过。

## 解决的具体执行缺口

旧 `b_warm_coordinator.py` 只检查五个 warm vtable 槽和 Steam Read 槽，并不检查人类规则六处 inline 来源是否恢复。新入口真正按已固定的 profile，读取四个 AI 入口 `C6660/C65F0/C6580/C66A0` 和两个收入 call `28DE71/28DAA5`，完整字节必须为原值；两遍采样均核 PID/birth/base/build，范围必须是本游戏映像可执行区。

检查发生于 claim 前，以及派生 `DiagnosticResident` 的构造、每次 open_bank、load 前后、finish 前后。它不恢复未知钩子，不调用 Revoke，不宣称未来没有其他发布者。源码原值只是这六处当前未被改写，不能证明所有其他插件都不存在或全世界完全静止。

文件/构建预检先于 GameReader：第一档已在真实 CC03 目标、第二源文件的 SHA/size、两期日期关系、两份档非同一文件、Steam 文件版本、批准 pair/helper 和生产 DLL 关联。打开游戏后仍重采样规划对象、实际 Steam 模块/存储接口、原来源、无 debugger 与旧 claim 排除，再做一次文件预检。`--check` 不创建游戏 attempt claim、不加载 DLL、不暂存文件，但会保存本地审计记录。

新执行分支直接消费经过预检返回的生产 DLL 绑定，不在 claim 后裸读另一份 result JSON 来重新选择 DLL。关闭 port 或 reader 异常会分别保留结果，而非跳过其他关闭与结果写入。继承原始失败语义：未知远程调用不重叠 Stop，不卸载、不清 claim、不重投。

本次又明确三处收尾：load 前先绑定当前 bank，第二代检查拒绝不能误 Stop 第一代成功 bank；原生完成退休后立即记录 bank 已退休，之后诊断失败不 Stop 该成功模块；尚未完成的加载错误才委托原 `Resident.abort()`。这些区别不把 Stop 写成已排空。

## 后续实机命令草案（本轮未执行）

先确认旧失败进程已正常退出；获取新进程显式 PID，不沿用任何历史 PID。准备两份确实由游戏生成的合法档并核其真实日期/势力，备份后把第一份放入准确槽 63 的 `svdexccSC03.s14`。本入口不会替首次暂存，也不会覆盖34号来准备样本。

plan 五个字段严格为 `profiles`、`target`、`second_source`、`expected_ruler`、`steam_paths`，格式与 [原协调器](b_warm_coordinator_handoff.md) 相同。两份 profile 的 source/target 相同；第二 before 必须等于第一 loaded，第二 loaded 是下一旬，第二 currentForce 是目标 B，文件 SHA 必须不同。`expected_ruler` 是此次新进程当前君主，不能只根据旧记录推断。此诊断不模拟中间一旬，因此不使用“B 已自行推演到目标日期”的 settled 协议合同。

从仓库目录，以下变量由本机操作者填好，路径全部是本次本机路径：

```powershell
$privateResearch = 'C:\Users\52708\Documents\Codex\2026-10-04\ni-li\work\mod_research'
$helperResult = "$privateResearch\b_warm_coordinator_build_runs\20261009-181031-457801\result.json"
$pairResult = "$privateResearch\b_warm_factory_pair_runs\20261009-181448-912475\result.json"
# $freshPid = 本次新进程 PID
# $planPath = 本次已准备的绝对 plan 路径
py -3 work/mod_research/b_warm_pair_diagnostic.py --check --pid $freshPid --plan $planPath --helper-build $helperResult --helper-sha256 4204df275c981b6c35c6bea01a25e040a0cea04be84e20ff2998079917e3b43a --pair-build $pairResult --pair-sha256 c13390840e1fbeaf54fde8822add15ef9c44a75967b8c57ea2da2af73247a990
```

只读结果是本次 `PASS_READ_ONLY_RULES_FREE_PAIR_CHECK` 后，正式诊断沿同参数将 `--check` 换为 `--execute --no-new-commands`。执行前仍会重新完整检查，不拿 check JSON 当许可。成功要求两个真正 warm 完成/退休回执、原六槽与保护恢复、实际新日期/B身份、真实 Handover stage3；不能用“文件已下载”“DLL成功加载”替代。

规则已经安装、存在旧失败 claim、规划对象不同、文件/源码变化或结果不明时停止本次流程，不用本命令恢复旧模块，不删除记录后再执行。失败需按保存的实际报告决定收尾；部分失败仍可能只能正常退出游戏。成功也仍不授予 Room Ready、输入锁或双人可玩权限。

## 本轮离线验证

`py -3 work/mod_research/b_warm_pair_diagnostic_test.py` 最终 8/8：

1. 真实固定六来源 profile，FakeReader 原值通过；每个入口分别改一个字节均拒。
2. 第二遍变化、birth 换代、执行区检查失败、错误 bool range 回调拒绝。
3. 默认 help 与文件预检失败均不打开 reader。
4. `--check` 走实际预检/批准构建/自有 Windows 文件，零 claim、零安装。
5. 原来源检查拒绝发生在 claim/安装之前。
6. 主 execute 编排使用明确 Reader/Storage/native port 替身，但实际读取 build、写 claim、备份及原子替换自有两档。
7. 第二次加载替身失败时文件仍由真实 Windows lease 保护，保留 claim，不重试；port.close 也失败时 reader.close 与结果记录仍完成。
8. 实际 `DiagnosticResident` 子类方法委托顺序；原生父方法为明确替身，验证第二代 precheck 不停旧成功 bank、退休后错误不 Stop、未完成原生错误委托 abort。

Steam-named 文件是自有临时字节，测试只替换允许的文件哈希字典；没有读取真实 Steam 文件。无游戏、UI、网络、debugger、驻留测试进程。也没有执行本工具的真实 `GameReader` 或加载两次实际游戏存档。测试代码调用 main 的 execute 分支仅在这些明确替身及私有目录内；不能把它记作实机执行。

最终私有记录：仓库外 `work/mod_research/b_warm_pair_diagnostic_test_runs/20261009-203017-218491/result.json`，SHA `edc74894d930c9e84fff091808822c66f2c6c2b41142e2fd50e86e4b21c36f6b`。29 sources、191 private、68 artifacts，全部独立重新核对匹配、inputs_unchanged=true；私有文件/claims/失败结果全部保留。前一轮 `202941-755288` 7项通过、1项 fixture 错误：旧测试用整数代替 bank 字典，新增退休标记正确要求字典，随后仅改替身并加入三项收尾断言；不是放宽生产检查。

审查/运行源码：

- `b_warm_pair_diagnostic.py` SHA `68a901077ed661f1ac709c664ccc079d7f718ac211ce006567fee79a57ba60aa`。
- `b_warm_pair_diagnostic_test.py` SHA `00bf8aa60c369e91ee8cecab773850db2c35d82960efed6fadd9e1484279d95f`。

集成与提交状态见[当前交接](../../docs/HANDOFF.md)。最短后续是准备两份合法档后执行上述新进程只读检查，检查合格再做受控两次真实加载，不继续增加全输入覆盖或更多协议 fixture 作为此诊断的先决条件。
