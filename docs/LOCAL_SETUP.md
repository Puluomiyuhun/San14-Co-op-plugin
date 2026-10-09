# 在另一台电脑接手

原电脑最新自动保存试验已生成新文件，但最终校验失败；停止状态钩子保留，正在按正常退出游戏路径收尾。当前恢复状态以[交接](HANDOFF.md)为准。原存档全部备份且未改，34号未变；本机证据不放行另一台机器。

后续离线代码已补准确保存过渡、error54的限定失败退休和[只读首错诊断](../work/mod_research/a_save_failure_diagnostic_handoff.md)。新 `a_save_diagnostic_start.py` 仍是内部单次实机入口，默认只读，使用最新合并构建的内层`abi`目录和配套发布器。不能把新收尾能力追补给已加载旧DLL，也不能省略新进程/原入口/阶段预检；具体构建定位以当前交接为准。

连续加载的首测路线已重审：优先为已有warm实机成功入口补完成退休、六槽恢复和独立二代配置。下文cold组合保留为另一条研究路线；其早期启动/四线程接管条件不是warm首测的统一安装要求。参见[路线说明](../work/mod_research/b_reload_runtime_warm_review.md)。当前仍没有可供朋友直接运行的统一原生安装包。

最新离线后继已增加[A跨帧推演/新状态重绑定](../work/mod_research/a_native_turn_handoff.md)、[B同六槽两模块交接](../work/mod_research/b_warm_two_bank_handoff.md)、[文件暂存](../work/mod_research/b_warm_staging_handoff.md)和[B本代采样](../work/mod_research/b_warm_profile_capture_handoff.md)。它们仍需合并为本机启动流程，不能直接替换旧脚本的DLL路径执行；合法新档与连续实机加载尚待验收。`b_warm_profile_contract.py`的profile.ready只表示配置捕获，不代表安装或加载成功。最新交接明确修正了旧profile的固定势力guard遗漏。

## 最新两档诊断入口

最新增加[规则与换档本地适配](../work/mod_research/b_warm_rules_bridge_handoff.md)、[owned远程执行检查](../work/mod_research/b_warm_resident_handoff.md)和[部分世界读取](../work/mod_research/b_warm_world_handoff.md)。bridge是供常驻协调器调用的Python接口，没有自动发现游戏或安装命令；world采样器也只接受已有读取器。两项原生组合测试需要原机已固定的私有fixture输入，不能在新电脑复制一份结果JSON来授权执行。公开源码与精确构建依赖见各手册；它们没有新增朋友端一键启动器。

[B两档协调器](../work/mod_research/b_warm_coordinator_handoff.md)已新增，默认help。它使用本轮完整pair的生产bank和同源原生helper，要求fresh PID、本机profile/Steam路径、已暂存第一档及独立第二档；核本机全部构建身份后才有显式执行路径。不可重跑旧单次加载器或删除claim代替第二bank。两次完整factory/原生交接、真实文件事务和TLS房间回执已分层验证，整个新`Resident`流程仍待实机，尚非朋友电脑的一键包。

## 上轮新增启动入口的使用范围

最新[A跨旬启动](../work/mod_research/a_native_turn_start_handoff.md)和[B单代启动](../work/mod_research/b_warm_start_handoff.md)均默认仅显示help，显式参数才访问当前PID。A仍使用原机34号/存储绑定；B接本机明确Steam路径但仍核固定支持版本哈希。两者依赖各自完整私有构建证据，不是朋友电脑的一键安装包。B新启动器要求完整factory构建，旧部分组合结果不能替代；同PID/birth仅一次，失败Stop不授予换档/重试。后续持续协调器尚需连接第二代接管、暂存及房间。

## 先建立开发环境

```powershell
git clone https://github.com/Puluomiyuhun/San14-Co-op-plugin.git
cd San14-Co-op-plugin
git status --short
py -3 --version
```

阅读 `docs/HANDOFF.md` 和 `AGENTS.md`，再按 `tools/README.md` 做离线检查。只读协议源码可以在没有游戏的机器上进行；原生 C++/MASM 编译需要 Windows x64 和 Visual Studio C++ 工具链。历史脚本使用 Visual Studio 2022 Community 的默认 `vcvars64.bat` 路径，其他安装位置尚未全部参数化。

若只是准备朋友电脑的连接环境，可先按 [CONNECTION_CHECK.md](CONNECTION_CHECK.md) 从公开源码生成诊断包。这个入口不依赖原电脑私有catalog/profile，能独立检查可选EXE版本与实际TLS字节传输；它不是游戏安装器，也不会自动进入地图。

新的[单次正常保存观察工具](../work/mod_research/a_save_observation_status_handoff.md)与[赏赐菜单观察工具](../work/mod_research/reward_menu_observation_handoff.md)可从公开源码在 Windows 编译并做自有进程测试，不需要私有原生转储。新版共用DR6事件归属检查，避免退出时清除外来状态；冻结旧保存观察器只留作历史。测试命令不会查找游戏；`--preflight`/`--record` 是另外的显式实机步骤，要求当前明确PID，须按交接核对本机状态及刚通过的构建。B的[最新组合](../work/mod_research/b_reload_cold_bootstrap_handoff.md)已在同一自有PE/DLL/Provider接实际Bootstrap、冷等待、原登记和两代完整队列，普通及yield两场景通过；真实游戏来源就绪、生产者覆盖和合法档加载仍缺，不能当作可玩启动器。

Python 常见依赖：`pefile`、`capstone`、`cryptography`；执行归档机器码的测试还使用 `unicorn`。工具会区分缺少依赖和测试失败，不要把跳过当通过。以工具提供的依赖清单和实际安装状态为准。

## 本机私有输入

A最新[单次启动入口](../work/mod_research/a_save_runtime_start_handoff.md)已接typed导出、来源发布器和真实IPC，默认仅只读采样；显式实机试验已生成新文件但被收尾校验拒绝。不得在原失败进程重试或清除其claim；先按最新交接完成收尾和针对性修复。实机命令要求新PID、预检和本次测试通过的构建，不可复用旧运行许可。[fresh采样器](../work/mod_research/a_save_local_binding_handoff.md)的`--capture`只读规划/存储绑定，不授予保存许可。这仍不是可玩安装包。

游戏程序及本机私有运行数据不在 Git 中；用户指定的34号测试档是明确例外。实际需要时在 `.local/` 配置本机位置，禁止把原电脑用户目录直接当成自己的目录：

- 自己合法安装的 `SAN14PK_SC.exe`；目前核对的文件 SHA256：`42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025`。其他版本不能直接套入口偏移。
- 本机 Steam 的实际存档目录和单独测试存档。用户指定共享的历史[34号基线](../fixtures/saves/slot34/README.md)现已包含在仓库中；按说明校验、备份目标槽位并手动导入。该文件不能代替本机运行时profile、进程身份或加载完成回执。
- 某些研究测试需要本地 `game-runtime-image.bin`、自有 PE fixture、历史生成 profile 或冻结构建结果。它们的缺失应明确报错；不能随便补零、改哈希或拿诊断文件冒充真实存档。
- 完整原生函数字节生成 profile 不公开分发。保留生成它们的工具；需要本机生成后才能运行对应原生测试。部分生成器仍依赖原电脑历史证据，尚未全部可移植。

## 目前不能保证的重现范围

这是已有研究工程的源码迁移，尚不是一个命令完成安装的发行包。大量旧脚本引用本机固定进程、绝对路径、私有 JSON 记录和带时间戳的 `_runs` 产物。源码在不等于其历史运行条件也在。

接手时先运行可独立的协议检查；要运行一个原生测试，先审阅其输入与生成器，建立自己的构建目录、哈希、版本指纹和只读检查。新编译 DLL 的字节可能变化，相应发布器的 SHA 和计数器地址校验必须重新生成、验证，不能直接改为“接受任意 DLL”。

原电脑当前主线记录位于 `work/mod_research/mainline_20261007_live_resume.json`，但其中含绝对路径和本机生命周期，不随 Git 分发。公开替代入口是 `docs/HANDOFF.md` 及 `docs/evidence/` 的摘要；若需要完整原始实机证据，必须回原电脑核验或在新电脑重做实验。

特别注意：历史参数 `--dry` 不保证只读。例如 `run_reward_execution_pilot.py`、`run_second_force_reward.py` 和 `run_autonomous_pilot.py` 默认仍可能加载 DLL、安装钩子，只是不发业务命令；`run_reward_container_probe.py` 和 `run_reward_eligibility_probe.py` 默认会安装探针。`auto_cache_start.py --dry` 会安装回调，`auto_reload_start.py --dry` 会附加调试器。不要把这些当作环境检查命令；先用明确允许的 `tools/dev_check.py`。

具体被排除的本地生成输入见 [LOCAL_GENERATED_INPUTS.md](LOCAL_GENERATED_INPUTS.md)。

已检查“直接从安装EXE生成保存profile”的可行性：支持版本文件SHA正确，但79个所需范围的磁盘字节均与已采集运行时字节不一致；两种独立PE映射结果一致，且这些范围没有重定位覆盖。因此当前不能把磁盘EXE直接映射后当作 `game-runtime-image.bin`。没有实现解包或放宽指纹。新的保存组合测试仍需外部私有 `checkpoint_push_profile.h`；准确命令见[该模块交接](../work/mod_research/checkpoint_fresh_save_session_handoff.md)。

## 提交与多电脑协作

```powershell
git status --short
git fetch origin
# 工作区干净且分支未分叉时：
git pull --ff-only
# 完成改动、更新 HANDOFF / CHANGELOG、执行相关验证后：
git diff --check
git add <本轮源码和文档路径>
git commit -m "描述具体行为变化和验证"
git push origin main
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

每次实质进展都同步交接文档。GitHub 登录由各电脑自己的 Git 凭据管理器处理，不在聊天、代码、文档或提交中保存 token。
