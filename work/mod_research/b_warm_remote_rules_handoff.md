# B 通过真实房间连接捕获本机规则配置

`b_warm_remote_rules.py` 是 `35ac375` 中 `RulesWorldCapture` / `RulesFactory` 的明确后继。原接口要求 Python 内存中存在 A 的 Room；B 在另一台电脑不能直接使用它。新接口只保留 B 自己的 `RoomConnection`、本机读取器及已确认 scope，不复制 A 的 Room 或 PeriodCoordinator。

## 接法

A 使用 `RemoteCompletionRoom`，完成原有两席绑定及 coordinator 绑定。新增只读 `warm_rules_binding` 请求仅接受当前已认证 B 控制连接；A 核原控制连接、未关闭/未暂停及固定 scope，返回 scope，明确 `native_permission=false`。它不传 A 的内存地址，也不提供原生执行凭据。

```python
capture = RemoteRulesWorldCapture(reader, b_control, confirmed_scope, settings,
    pid=pid, birth=birth, read_birth=lambda: process_birth(reader),
    guard_check=trusted_local_boundary_check)
factory = RemoteRulesFactory(capture, retained_api, approved_build,
    private_records, rulers={12: 666, 2: 952})
```

capture 每次通过实际 TLS 连接核固定 scope/profile/settings、当前 B 席位和本机 PID/birth/image；再沿原 `_capture` / `export_current` 读取 B 自己的 RAM、日期、身份、root/world 和设置。首次可以从 source 视角捕获，加载后使用 target 视角；规则代际 epoch 与房间 binding epoch 仍分别验证。

factory 只明确修改接受的 capture 类型；批准构建、真实进程/模块校验、LoadLibrary/Prepare/Seal、ResidentPort 和外部发布器均直接继承上轮实现。不是为远程模式放宽原生指纹，也没有通过伪造本地 Room 绕过检查。

## 失败与边界

网络失联、authority关闭或 held、scope改变、进程身份或本地检查失败会锁存 capture 失败。不会自动重连、重试 native 或重建一个 Room。既有 port 的 restore 也依赖 capture 检查，因此失联并不表示旧规则已安全撤回：保留模块与原所有者进入处理状态，不能卸载或转交 AI。

TLS只证明房间来源和当前连接，不能证明游戏输入已经禁用。`guard_check` 仍是本机可信接口；测试的自有宿主等命令以及替身内存检查不能替换实际游戏的该依赖。首测可采用[边界审计](b_warm_boundary_audit.md)说明的受控无新命令窄诊断；不能将人工不操作写成完整排他。

## 验证

```powershell
py -3 work/mod_research/b_warm_remote_rules_test.py
```

5项：TLS固定绑定下source→target及world换址；外来scope/A席位/多余请求字段拒绝；本机进程与边界失败锁存；authority关闭拒绝；实际自有进程两代规则factory加真实TLS配置查询。

最后一项复用上轮固定哈希的自有构建，真实 ReadProcessMemory、远程Prepare/Seal、两独立DLL和四次发布器安装/恢复；viewer12→2，每代8次AI入口、6次收入判断，宿主原入口确认恢复后正常退出。自有数据、业务及主线程等待是fixture，未执行游戏读档；其他用例使用明确替身内存。此处也未将新的远端正式 completion 与真实游戏 warm.load 合成整条实机链。

测试需要本机归档 `b_warm_rules_factory_runs/20261009-193128-959554` 及其固定构建闭包。缺输入的电脑应按前驱手册重建并核验自己的产物，不复制运行结果作为许可。新代码是接口，不是朋友端一键安装包。精确结果及源码/产物哈希见[本轮证据](../../docs/evidence/2026-10-09-warm-remote-completion-rules.json)。
