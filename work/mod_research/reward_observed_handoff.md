# 赏赐真实上下文与结果投影后继

2026-10-10。本轮关闭的是“现有房间执行端只有手造业务 context / sample”的读取与验收缺口。没有修改冻结模块，没有访问游戏、Steam、当前存档或 UI，没有安装入口。双机实测仍后推。

## 实际新增

- `reward_observed_context.py`：`ContextSampler` 直接复用生产 `GameReader.snapshot/state_objects`、`authority_reward.capture_context`、人员资格与池结构采样、城市资金/军团行动读取。没有另写一个只接受远端 JSON 的 context。
- `CheckedPort`：供原 `reward_room_flow.Replica` 使用。执行前重验原权限预检，执行后重新读取本机数据；只有原生返回、参数销毁、owned slot 清理均确认且投影匹配，才返回可供原 SQLite 日志封存的结果。
- `reward_observed_flow.py`：显式继承现有 `RewardFlow`，A、B 提案仍进入同一权威队列，沿用双 ExecutionJournal 与签名结果确认。`GuestConsumer` 在可信本地执行线程消费；TLS 线程不执行游戏调用。丢回执/未知结果终态，不自动重放或重连。
- `reward_observed_fixture.py`：完整的自有字段、池链、任务空表、人物/城市/军团/势力表。真实 GameReader 和原 context 算法读取这些字节；RTTI 服务与原生赏赐业务是明确替身。

机器可读能力/资源声明在 `reward_observed_flow.CAPABILITIES`；投影合同在 `reward_observed_context.CONTRACT`。本模块没有任何 native hook 写入，声明 `production_native_submit_bridge=False`、`observed_room_ready_integration=False`、`menu_interception_installed=False`、`ui_refresh_verified=False`、`input_exclusion_proven=False`、`full_world_verified=False`。

## 接口与约束

```python
sampler = ContextSampler(
    retained_game_reader, pid=pid, birth=birth,
    epoch=local_attachment_epoch, attachment_id=attachment,
    current_binding=trusted_local_owner_binding,
    node={"year": 203, "month": 8, "day": 11}, viewer=local_force,
    players={12: {"ruler": 666, "district": 11},
             2: {"ruler": 952, "district": 2}})
port = CheckedPort(sampler, trusted_same_owner_native_port)
```

`GameReader` 必须是实际类型，PID/birth/EXE/root/world/五个状态实例、日期/本机势力/君主和本机 attachment/epoch 固定。`current_binding` 是保留本机 Owner 的访问器，不是客户端可自行填的网络字段。生产默认 birth 使用已有 WinAPI 读取；测试只替换本机进程环境。

每次捕获两势力全部 context 两遍，要求相等，再核同一原生 attachment。失败后保留首错并永久退休；把日期/地址改回也不能重新使用旧 sampler。旧 `capture_context` 内已有池链、短读、任务类型、人员资格、城市访问器、名单与对象表、采样后重读等检查均执行。`strategy_mode==2` 是 User 对象 `+0x470` 的旧赏赐命令模式，不是已实测保存链的 `load_cache+8==0`；两字段不可混同。

投影只覆盖两绑定势力的声明字段：日期、君主/主军团，军团归属/行动，支持城市的资金/粮食/兵力/交易字段，人物身份/归属/位置/职级/忠诚/flags，以及已支持的任务/军团状态。它不包含对象地址、本机 viewer 或 PID，所以两个不同视角可以比较；这些本机身份在 hash 之外分别严核。

执行后严格检查：

1. 付款城市金钱精确减少 `100 × 选中人数`；对应军团行动精确减少 1。
2. 每名选中武将实际忠诚严格增加且不超过 100，flags 精确为旧值 OR 2；其他投影字段完全不变。
3. A、B 的实际投影摘要和累计执行前缀必须一致，才得到原协议的 PAIRED。

**没有把 fixture 的 +4 当成生产忠诚公式。** 原资格镜像已先排除忠诚≥100、君主职级、已赏赐、受限任务/部队等目标；若实际命令仍不增加忠诚，本适配器会报未知/持有而非放宽或再次执行。公式是否足以覆盖所有合法武将仍需原生算法/实证补充；本轮不宣称已证明。

## 当前没有完成的生产接缝

`trusted_same_owner_native_port` 需要提供 `identity() -> (pid,birth,local_epoch,attachment)` 和 `execute(command)`，后者必须接同一保留 User/Save Owner 的实际赏赐 lane 并返回完成/清理报告。本模块不根据远端报来的成功布尔值执行确认。

现 `a_native_turn_owner.cpp` 确实保留 `a_reward_save_owner::Bind/Submit/Snapshot` 与 owned replay，现有 typed Runtime 导出却没有完整开放赏赐 Submit/Report/生产 Source sampler。**该真实提交桥本轮没有实现，也不因 `CheckedPort` 接口存在而被算成完成。** 不能另装旧 Dispatcher 去争用同一个 User 槽。最短下一项是对当前唯一 Owner 加明确 typed 原生赏赐提交/观察后继，并用这里的上下文与效果核验接其报告。

同样，原 `RewardFlow` 的局部投影合同不等于当前 observed 保存/读档 Room 的投影合同。新 flow 复用原独立排序服务，但不换掉 observed Room 的 Coordinator，也不把其 Ready 当成 native 准备。`reward_ready` 与 `seal()` 在本后继明确拒绝；本机 native attachment epoch 与新赏赐 wire epoch 分开绑定，不强行改成相同值。它还没有被安装到 `observed_room_service` 或两侧启动入口。

真实菜单确认前接管、暂留/取消/安全关闭、跨 world 重新建立命令会话、UI 刷新仍缺。当前采样要求五态规划，不能对着未关闭的赏赐菜单六态假称已捕获成功。完整输入限制由独立输入线推进，这里的有限读验不是持续排他。

## 验证

```text
python work/mod_research/reward_observed_test.py
```

最终私有记录：`reward_observed_runs/20261010-013439-940413/result.json`，**6/6 PASS**（包含子场景），18份来源/26份产物全部重核一致，`inputs_unchanged=true`。结果 SHA256：`8fd26f888281bfe7f00330a59461faa927a107b246eeeca481afa0049fbfd1a4`。

- 两玩家并发提交仍同一队列；两端各两次实际本地端口调用、资金/行动/忠诚结果一致。
- 重复网络 request 和重复本地 intent 都没有增加原生业务调用。
- 错扣金、非选中人物变化、写后丢结果均持有，不能重试；未到 B 则 B 零调用。
- 日期、attachment、birth、world 改变使旧上下文退休；改回不解封。
- 忠诚100、资金不足、行动不足在原生调用前拒绝；未知任务实现、短读也拒绝。
- B 应用后丢签名回执：本机 SQLite 保留 APPLIED，consumer 终态断线，不再执行。

两个世界是同一测试进程内的独立 owned byte layouts，TLS 为实际 loopback，执行日志为实际 SQLite。未运行游戏或原生赏赐函数，未调用真实菜单，未验证 UI。旧两次中间 PASS `013249-269604`、`013406-127528` 保留；其后补了本机/房间玩家日期关联和本地 intent 重复确认，没有删除失败证据或重置任何 claim。

最终源哈希：context `a33288419b5dfec1f59f87e9075a01e1e80de4dbf34801d8a85120eba2eea386`；flow `9b87b492688da444e8f5c72ac00b8b78b913767d3771ce05ffdff8452d078f2c`；fixture `63faeaf6706e57b8566e2ba829e91534243a2f50ce7e1cb22267a8511a1d1e3b`；test `2248702b29192c9e7a0f242bc5b2c55e51b33cd161fccbf676d9779a984d5a4a`。

测试线程/网络连接已关闭；本轮没有游戏补丁或调试器，不等待用户操作。
