# 双侧启动和收尾入口

2026-10-10。本轮新增可执行网络入口，旧诊断模块冻结不变。先读 [HANDOFF](../../docs/HANDOFF.md) 当前状态。尚未用这些新入口操作真实游戏，不照抄原电脑 PID、claim 或历史回执到另一台电脑。

## 已接的实际调用

`observed_host_start.py` 是 A 配置入口，先检查批准源码、构建、DLL/依赖/发布器及独立 adapter key，再只读捕获显式 PID，核对真实34号起点。`HostService` 创建实际 TLS 控制/下载端口：A 先选张鲁，B 加入选刘备并确认，A 随后确认并绑定同日 Coordinator。初始 digest 是配置的开局文件身份标记，不声称两台游戏内存已经相同；首份原生导出使用实际两表/日期投影。

两席绑定后，A [RoomEntry/execute](a_observed_start_handoff.md) 在原生 Prepare 前绑定真实 room scope；安装原已批准 native-turn 模块，接保留的真实 reader、Plans、Runtime Snapshot 和同一 IPC channel。首份正式 loaded 后，A 与 B 各经自己的 TLS 连接发送 Ready；服务端只有两者均准备且首档已正式完成，才 seal/begin。`ready_for_turn` 不阻塞 A 的 IPC heartbeat。只有实际原生状态返回 Running 的 `running-await-human` 事件可通知玩家推进，不因网络 phase 或计时器直接操作游戏。

B [b_observed_start.py](b_observed_start_handoff.md) 从 `pilot_context` 取实际 scope/期次/附件和当前 manifest；接真实收档/SQLite、从当次文件构 Profile、`Session.open`、同一 GuestCompletion。完成首档后，在下一期仍保留旧 manifest 的等待阶段继续等待新档，不能把上一档再载一次，也不能据此报错。两次完成后恢复当前双人规则，核原六入口、规划、无调试器和目标字节，再关闭本机句柄。

## 收尾顺序

1. A 先排空正在执行的 TLS 观察回调，并关闭新的观察入口，再 Stop/等待/drain/恢复七入口/只读后验/关闭本机句柄。尚未完成的原生调用必须保持 unknown；新 `a_observed_start_call.py` 保证日志或本地句柄清理错误不能把 unknown 变成可继续撤钩的普通异常。
2. B 正常完成两次正式回执后执行实际 helper.finish 和当前 rules.restore。原入口恢复与本地句柄关闭分别记录；句柄未关完时不宣称完整 cleanup。安装前没有 retained_session 的纯 reader 失败可以关闭 reader；已有原生对象或未知调用时保留终态，不重装、不卸载 DLL。
3. B 在本机收尾成功或明确保留失败状态后，仅发送一次 `pilot_guest_finished`，随后保持连接并只读等待 `pilot_host_finished=true`。A 的原生入口返回后设置这道收尾标志，再等 B 通知和 B 实际断线，最后关闭房间。这样既不切断 B 规则恢复需要的连接，也不会让 B 抢先断线而使 A 来不及确认第二份 loaded。通知/标志都不是另一端原生清理的独立证明，不授新一期 Ready；A 标志仅表示本地入口已返回，具体成功与否仍看原生报告。
4. 失败通知立即 HELD、清 Ready 并撤销下载。已经派发的原生动作不能靠房间关闭撤回。回复丢失保留证据，不重试加载或清理通知。
5. 网络服务独立报告 `network_closed`。新有界 TLS Handler 保留分片缓存，在短超时中检查退出标记，解决 Windows `socket.makefile` 引用导致对方仍空闲时关闭不了阻塞 SSL read 的问题；没有靠延长超时或忽略线程残留来假称关闭。

加载 DLL 保持驻留直到正常退出游戏。B 旧 CC03 私有备份保留；游戏运行时不做物理回滚。**旧 CC03/原生自动档恢复仍需正常退出游戏后的已核验恢复流程**，不是 native cleanup 自动恢复了文件。A 自然推进可能更新旧自动档；严格 inventory 会如实给 INCOMPLETE，组件两保存成功不能改写成所有旧档未变。

## 配置和命令

所有配置、TLS 私钥、邀请凭据、adapter key、运行目录放在仓库外。两边先人工启动已支持游戏并读取34号档，停在空闲张鲁地图。入口暂不负责启动游戏或代替读开局档。

A 配置 schema 为 `san14.a-observed-host.v1`，精确字段：

- `manifest`：现有 Room manifest（profile/forces/source），game/rules/slot34 SHA 真实匹配；支持 A 张鲁12/主军团11、B 刘备2/主军团2。
- `rules`：真实配置的 human-rules 内容；它在此描述兼容性，**不代表 A 已安装 AI 保护**。
- `network`：`listen_host, advertise_host, control_port, download_port, directory`。两个不同固定端口，可达 advertised host，新私有目录。
- `native`：显式 `pid, wait_seconds` 及五个绝对目录 `build_run, repeat_abi_run, publisher_build, launcher_test_run, entry_test_run`。前四沿已批准本机构建，第五为本轮 A 入口测试结果目录，执行前逐项复核来源。
- `adapter_key_path`：本机独立 key 文件，使用既有 Windows 私有 ACL 格式；不是房间邀请码，也不通过 `pilot_context` 下发。

从仓库根执行以下**入口形式**，文件路径须换成实际完成核验的本机配置：

```powershell
py -3 -X utf8 work/mod_research/observed_host_start.py --check --config C:\private\san14-a.json
py -3 -X utf8 work/mod_research/observed_host_start.py --execute --no-new-commands --config C:\private\san14-a.json
```

A `--check` 只查文件，不打开游戏或网络。执行后只打印新 `invitation.json` 路径，不打印凭据。把邀请内容私下放入 B 配置的 `network`；两机 adapter key 另行用已有私有导入流程保持一致。

B 配置 schema 为 `san14.b-observed-start.v1`，顶层 `schema,network,local`。`network` 为此次 A 创建的邀请，不能复用旧房间。`local` 的精确 build/source manifest、进程身份、原 CC03、规则、Steam 模块路径和超时字段见 [B 手册](b_observed_start_handoff.md)。

```powershell
py -3 -X utf8 work/mod_research/b_observed_start.py --check --no-new-commands --config C:\private\san14-b.json
py -3 -X utf8 work/mod_research/b_observed_start.py --execute --no-new-commands --config C:\private\san14-b.json
```

B `--check` 会只读检查显式游戏进程和文件，不入房、不创建 claim、不安装。成功 check 后也须保持不操作；执行会重新检查。默认不传模式只显示 help。新电脑必须准备自己的已批准构建/源码结果，不能复制原电脑 receipt 或修改 PASS 值来通过。

## 本轮验证与当前范围

26/26 通过：A入口7项，B入口9项，网络服务与CLI检查10项。根独立复核三套87/86/39来源、9份归档输入及407/225/17产物；私有审计 `observed_start_root_audits/20261010-011121-056593/result.json` SHA `f2eb8f5bb926d1d5319eae4b893656d38f796bec45f778b5d1f9be401044998d`。公开来源哈希见 [本轮证据](../../docs/evidence/2026-10-10-observed-start.json)。A 测试执行新 `execute` 的完整分支和实际 TLS；B 测试执行新 Runner、真实 HostService/TLS、原 Session/GuestCompletion/Journal 与规则恢复谓词。原生保存/加载/发布、游戏 RAM 和若干环境工厂为明确替身。生产 `Session.open` 整组安装仍需实机；测试没有碰游戏、Steam 存档或 UI，不等于两个新 CLI 已在两台游戏同时通过。

**A 目前只装七处保存/父入口，没有一起装六处双人 AI 规则。** B 安装的规则不能保护 A 权威端的远端势力。因此当前是“零新命令、同日快照＋一次旬末”的存档同步诊断，不是可正常游玩的双人联机。A 规则与保存父入口共存/跨旬生命周期应独立接入，不暗中夹进未验证的安装。

接下来无需重写 Room/完成协议：准备两机实际地址/TLS/key/本机构建配置，核对新入口在真实 fresh 进程的整组安装/收尾，再跑窄诊断。完整游玩还需 A 规则共存、命令同步覆盖、事件选择、超过两代和界面遮罩。当前不等待用户操作，本轮没有安装任何游戏钩子或调试器。
