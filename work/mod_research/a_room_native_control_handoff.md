# A 从同日开局等待到下一旬的控制后继

2026-10-10。`a_room_native_control.py` 只组装既有 typed Runtime 接口和新的真实房间状态，不发现进程、不安装 DLL、不自动点击推进。旧 `a_native_turn_start_control.py` 及实机成功入口保持不变。

## 已实现的顺序

1. 本地启动器在原生 Prepare **之前**调用 `prepare_from_room(prep, binding)`：核固定连接和导出阶段，将实际 scope、当前封口、协议 epoch 和本机原生 epoch 绑定到 Prepare。不能在 Runtime 安装后才替换这些字段。
2. `RoomTurnControl` 只允许执行一次。绑定的 artifact_reader 必须是同一对象的 `copy_artifact`，取得本次同一 channel 的 `wait_artifact` 返回，不能从历史档案导出，也不能第二次发布同一代。
3. 首次 reserve/Submit/Copy/keep/publish 导出同日开局档；等待当前 Coordinator 的正式 `loaded` 记录。普通诊断 ACK、文件下载完毕、对端自报成功均不放行。
4. B 正式加载后仍等待双方真实 Ready、封口和 `begin_simulation`。本窄测试只允许零条新命令；控制器不替玩家 Ready。等待期间继续对同一原生管道 Snapshot，避免服务端因空闲失联。
5. 核 A 仍为开局世界，使用真实第二阶段 descriptor 的 inputDigest 发一次 RequestNext。原生实际报告 Running 后才发 `running-await-human`；由玩家正常推进。控制器不写日期。
6. 原生验证返回新规划状态后，导出第二档、等待第二次正式 B 加载完成，再返回。任一超时、断线或不一致都保留终态，不重投原生请求。原生 Stop、发布器收尾、必要时正常退出仍由外层启动器处理。

`observe_world(node)` 必须针对给定日期做真实本机观察：等待结束、RequestNext 之前是当前日；第二次保存才是下一旬。回调本身不授予持续输入隔离。强合同可用 `a_room_bootstrap_protocol.host_observation(..., expected_node=node)`，仍须有真实 `verify_held`；无新命令诊断不能把空函数当作该保证。

## 验证与限制

`py -3 -X utf8 work/mod_research/a_room_native_control_test.py`：11 项控制测试，实际 BootstrapRoom/Coordinator/FreshSaveBinding/loaded 状态机；原生 channel、Runtime 和世界为替身，不使用历史 packet 或游戏档。覆盖正确两次完成、ACK 不放行、已加载但未准备、断线、等待中 A 变化、新命令拒绝、原生失败、第二次回执缺失、不重试、旧连接在安装前拒绝及 Prepare 绑定差异。

首次新增旧连接测试时误把另一个测试末尾两行插入该 case，产生一次测试组织错误；记录 `20261010-001357-441857` 保留。修正测试位置后 11 项通过，没有放宽生产校验。

TLS/独立 B 子进程组合另见 `a_room_bootstrap_test.py`。具体最终运行摘要在 `docs/evidence/`，本模块通过测试不能单独证明真实游戏联网。

**尚未成为游戏启动入口。** 现有 `a_native_turn_start.py` 仍使用原本地控制；它未创建实际 Room，也未调用本后继。下一步需在明确边界合同下组装 Room 服务、真实观察和本控制，再接既有 fresh 进程批准/Prepare/安装/收尾流程。B 的窄诊断边界与旧强完成接口的差异也要显式接好，不能用测试 callback 启动实机。首版只支持起始快照和一次真实推进，共两代，不是无限多旬。
