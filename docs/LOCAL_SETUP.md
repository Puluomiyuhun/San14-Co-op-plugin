# 在另一台电脑接手

## 先建立开发环境

```powershell
git clone https://github.com/Puluomiyuhun/San14-Co-op-plugin.git
cd San14-Co-op-plugin
git status --short
py -3 --version
```

阅读 `docs/HANDOFF.md` 和 `AGENTS.md`，再按 `tools/README.md` 做离线检查。只读协议源码可以在没有游戏的机器上进行；原生 C++/MASM 编译需要 Windows x64 和 Visual Studio C++ 工具链。历史脚本使用 Visual Studio 2022 Community 的默认 `vcvars64.bat` 路径，其他安装位置尚未全部参数化。

若只是准备朋友电脑的连接环境，可先按 [CONNECTION_CHECK.md](CONNECTION_CHECK.md) 从公开源码生成诊断包。这个入口不依赖原电脑私有catalog/profile，能独立检查可选EXE版本与实际TLS字节传输；它不是游戏安装器，也不会自动进入地图。

新的[单次正常保存观察工具](../work/mod_research/a_save_observation_status_handoff.md)与[赏赐菜单观察工具](../work/mod_research/reward_menu_observation_handoff.md)可从公开源码在 Windows 编译并做自有进程测试，不需要私有原生转储。新版共用DR6事件归属检查，避免退出时清除外来状态；冻结旧保存观察器只留作历史。测试命令不会查找游戏；`--preflight`/`--record` 是另外的显式实机步骤，要求当前明确PID，须按交接核对本机状态及刚通过的构建。B启动加载器目前仅通过自建EXE/DLL检查，未接真实游戏Bootstrap，不能当作可玩启动器。

Python 常见依赖：`pefile`、`capstone`、`cryptography`；执行归档机器码的测试还使用 `unicorn`。工具会区分缺少依赖和测试失败，不要把跳过当通过。以工具提供的依赖清单和实际安装状态为准。

## 本机私有输入

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
