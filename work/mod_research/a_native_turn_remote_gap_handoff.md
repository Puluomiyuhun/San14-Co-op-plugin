# A 连续自动保存到远端 B：最小接线缺口

2026-10-09，只读源码审查；本轮不访问游戏、Steam 或网络，不修改生产模块。

当前已完成的实机事实是：A 同一进程生成 203-08-11 和 203-08-21 两份自动新档；另一真实游戏进程的 B 两 bank 随后逐份加载成功。当前仍不是两台电脑同时运行的远端房间。以下仅列三个具体下一接点。

## 1. A 启动控制必须接真实房间，并显式处理同日起始快照

已有可复用入口：`a_native_turn_start.py` 的批准构建、初始化、实际管道和收尾；`a_native_turn_start_control.py::drive/reservation/next_request` 的实际两次 Submit/Copy、RequestNext 与 Running；`checkpoint_fresh_save_binding.py::FreshSaveBinding.reserve/publish` 的实际 artifact 校验、`PeriodCoordinator.offer_checkpoint`、Room 下载服务；`b_warm_remote_completion.py::RemoteCompletionRoom.enroll_adapter` 的正式远端完成回执。

缺的是这几者的生产启动接线。当前 `drive` 在 `keep(1)` 后立即 RequestNext，`reservation` 的 binding 是本地 prep/filename 摘要，`next_request` 的下一 inputDigest 也是受控诊断摘要；它没有等 B 完成，也没有从当前房间封口/新 epoch 生成绑定。不能把已有 `keep` 回调简单改成上传后就称房间接通。

还有一个必须显式处理的日期差异：实际第 1 档是起始日，第 2 档才是下一旬。`FreshSaveBinding._capture_boundary` 要求 RUNNING、真实封口、无在途命令，并固定导出 `next_node(c.node)`；现远端 fixture 每档之前都执行模型推进。故“起始快照 + 一次真实推进”不是两个正式旬末。最小后继应明确加入同日 bootstrap 检查点阶段，完成 B 同日加载后才允许实际 RequestNext；旬末档再沿现有正常检查点路径。不能倒改 Room 起始日期、伪造一轮推演，或将历史 artifact 冒充本次 retained owner 的 Copy。

A 后继须保留同一真实管道和两个 generation，把本期房间身份/封口绑定到实际保存请求，并将上一份真实 artifact、远端正式完成、下一期身份串起来。普通 `warm_load_ack` 只是诊断确认；正式完成在 `RemoteCompletionRoom._complete` 内通过校验后调用真实 `c.loaded`。等待 B 期间仍须保持原管道 heartbeat 与失败不重试语义，不能使用有期限的轮询等待把已失败 native 请求重新提交。

## 2. B 增加一个保留真实对象的接收端启动入口

现成调用链是：`b_warm_room.receive_staged` / bootstrap 接收后继 → `b_warm_refresh_remote_owner.RetainedRemoteOwner.apply` → `b_warm_refresh_bootstrap.BootstrapRulesBridge` → 同一 `b_warm_stable_refresh_coordinator.Resident` → 原生 refresh/load/retire → `WorldLifecycle` 新规则绑定 → 本机 world sample → `RemoteGuestCompletion` 正式回执。后期使用普通 Journal，同一 owner 保留 warm bank、规则历史、PID/birth 和失败状态。

`b_warm_remote_rules.RemoteRulesWorldCapture/RemoteRulesFactory` 已通过 `warm_rules_binding` 从 B 的真实 TLS 连接核固定 scope；不需要在 B 复制 A 的 Room 或 Coordinator。刷新接收 owner 也已使用正确的独立源文件、备份及原生目标锁顺序，不应退回旧的 Python 物理暂存。

实际尚缺一个生产启动器，把批准的 stable Resident、真实 reader/profile、RemoteRulesFactory、初始已安装规则、WorldLifecycle、TLS connection、私有 adapter key 和上述 retained owner 组装并留存两次。现 remote-owner 测试确实执行 TLS、SQLite 和 Windows 文件，但 native load、游戏内存、publisher/guard 使用明确替身；不能据此声称这个真实对象组合已在游戏执行。真实 native 两载诊断则未经过 TLS/该规则生命周期，二者不能拼成远端实测结论。

最小无新命令试验无需先补全内政菜单或遮罩，也不应新加“全引擎暂停已证明”门槛。若采用窄诊断启动后继，应明确现有 User/Menu/Game 验证、短暂停发布事务、人工不操作约定及错误终态的范围；原强合同仍须保留，不能向 `guard_check` / `verify_held` 填空函数或无条件 True，冒称持续原生排他。具体已有边界及冲突见 `b_warm_boundary_audit.md`。

## 3. 用同一 A 房间与独立 B 进程跑上述启动入口

真实 TLS、下载分连接、邀请/证书指纹、私有 adapter key、B 独立子进程签名回执和实际 `Journal.complete → c.loaded` 已有代码及离线组合；不要另造网络协议。复用 `RemoteCompletionRoom` 与 `b_warm_adapter_key`，给两台机器配置真实可达地址/端口和本机批准产物即可进入此项部署工作，但此前仍须完成上面两个启动接点。

首测可先让 B 等待 A 校正，不必同时要求 B 自行推演；普通已自行推进的下一旬校正另有 `b_warm_settled_completion.SettledRemoteCompletionRoom` 明确日期策略。两种模式不要混用。世界比较采用已声明的两表加日期契约；签名 witness/文件 SHA 都不能冒充全世界或完整暂停。测试只接受一次本地 native 意图，回复丢失保持 HELD，不重放加载。

验收顺序应是：真实起始保存 → 跨机接收/同日 bootstrap → 正式匹配完成 → A 正常推进 → 真实旬末保存 → 同 B 的第二 bank 加载/正式完成 → 两边原生收尾。起始快照的协议后继未完成前，不将这条顺序描述为已存在的一键命令，也不把两档诊断称作两次真实推演。

本次只读审查未运行新 fixture，也未安排用户操作。上面是生产编排和起始阶段语义接缝；A 自动保存/换旬、新 User 重绑和 B 两次原生读回本身已经有实机证据，不再列为待实现。
