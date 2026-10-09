# Declared partial-world projection → real checkpoint journal

本后继只新增 `b_warm_projection.py`、`b_warm_projection_test.py`，冻结前驱不改。它把房间**明确声明的** `san14.partial-world.object3001-force52-date.v1` 投影合同接入既有 `LocalWorldObservation`、SQLite `CheckpointJournal`、`PeriodCoordinator.loaded()`。协议里的 `world_sha256` 在这个合同下表示所选两张表及日期的摘要，不能被解释为全游戏内存已核对。

## 接口与真实接点

- `host_observation(coordinator, reader=..., read_birth=..., verify_held=..., source_ruler=...)`：A 在 Save 前、Copy 后可调用。复用 `b_warm_world.context/payload_pass` 真正读取完整已选表两遍，前中后核上下文、核当前房间与外部 held 边界；不需要尚未产生的新档文件大小或 SHA，也不制造占位 Profile。
- `receiver_from_journal(journal)`：从本机已收到、重哈希的两份 SQLite bytes 按真实 CHUNK 格式重新构造 `CheckpointReceiver`，无需保留 A 的包对象。
- `TrustedProjection(c, host_sampler=..., guest_sampler=..., verify_held=..., guest_before=..., native_load=..., source_kind=...)`：受信**本地**回调装配，不是网络入口。两个 sampler `(profile, receipt_key)` 返回原 `b_warm_world.sample()` 的结构；`guest_before()` 返回旧 B attachment、viewer、safe boundary；`native_load(permit)` 只在实际 `reserve_load()` 已持久化 INTENT 后调用一次。
- `apply(journal, receiver, profile, host_receipt_key=...)`：核房间/文件/Profile/日期/旧 attachment、A 投影、实际字节 → 实际 `received/begin_guest_load/reserve_load` → 一次本地原生加载 →核退休回执和 B 投影 → 重采 A/B →实际 `Journal.complete/apply_to_coordinator/loaded`。一次错误终止此 adapter；加载后的失败保留 INTENT，不重发原生加载。
- Root 的 `ReceivedApply.apply(..., reservation=permit)['completion']` 可作为 `native_load` 回调。其 TLS ACK 仍只是诊断进度，真正周期推进发生于上述 Journal/loaded 路径。联合 TLS 实跑由 `b_warm_joint_test.py` 的独立证据负责，本文件不把它计入本地六测试。

`verify_held` 必须由实际宿主独立证明执行/输入排他。Python callable、`source_kind` 字符串、网络 JSON、两次读值相同，均不能代替真实排他或原生完成证明。`native_load` 返回值的深层 native receipt 验收由既有本地 Resident/ReceivedApply 保留；本适配另校 Profile SHA、文件与 checkpoint 绑定、回执身份、进程、日期和视角。不会从收到的网络 ACK 构造这份证据。

## 验证

最终私有结果：
`work/mod_research/b_warm_projection_runs/20261009-184926-947510/result.json`

- result SHA256：`c70e671bebf8a84d7e4d34b590951941e997b90dadbbf4ecc64ab649ffb97c82`
- 6/6 PASS，20 份 Python 来源执行前后相同，产物哈希在 result 内。
- `b_warm_projection.py`：`c75de6b32c536a9824bbcea987a2f1197391af7d74ec8e8c760da44c3501a4e6`
- `b_warm_projection_test.py`：`a8f5c9fe6ba6279bbacff797a93999b2c9a04a5510ed149750c9bca2d98abee6`

成功例实际调用 FreshSaveBinding、CheckpointRoom、Receiver、SQLite Journal、PeriodCoordinator 两期：period 1 → 2 → 3；第二期出版由第一期真实 `applied_receipts` 放行。没有调用 `complete_model()`。日期依次为 203-08-11、203-08-21，每期真实 Journal 为 COMPLETED、B attachment 更新、Ready 清空，外部 held 标记保留。

反例覆盖更广合同拒绝、投影差异后保留 INTENT/不 loaded/不重复 native、错误 native Profile 保留 INTENT、错 scope 及 held=false 在 native 前拒绝。独立用完整 FakeReader 表内存运行无文件 Profile 的 A 前 Save 采样并与原 `world.sample` 摘要一致。

本测试的 Save artifact、native load、局部样本为显式替身；A 前 Save 采样使用原采样逻辑但读的是 FakeReader 内存。无游戏、进程、Steam、UI、合法存档或 TLS 访问，无原生执行。初轮 `184852-770819` 保留：5/6 PASS，第六测试把 `c.ready` 的 set 当成 dict 调用 `.values()` 导致测试断言错误；没有修改协议实现绕过该失败。

## 准确范围与下一步

协议允许显式覆盖合同，不要求把每个游戏内存字节都纳入摘要。这个后继关闭的是“合同已经声明局部覆盖，却没有正式 Journal/loaded 接口”的接线缺口。它仍没有覆盖人物、军队、城市、军团、格子、任务、随机数、事件等其他数据，不宣称全世界一致。所有返回 `native_gameplay_enabled/full_world_verified/native_full_world_coverage_verified/ready_authorized/fence_released` 保持 false。

最短待接点是：实际 room 持有该合同，A/B 各自受信原生边界提供 `verify_held` 与样本，将 ReceivedApply 的真实退休 completion 接入此 adapter。离线两期协议成功不授权开始游戏推进。

首测的开局加载次数不能一概写成 3 次：若 A 的两份档分别为第一次、第二次旬末，B 可以在 bank0 首次加载时由 A 视角切到 B，bank1 做第二旬校正，总共两次；但当前 WarmRulesBridge 要求旧规则 viewer 已等于 target，故仍缺**首代 bootstrap 分支**（没有旧 B 规则，或先恢复旧 A 视角规则后再建 B 规则）。若先建立正式共同开局再各推进两旬，则需要开局 + 两次校正共三次加载，当前两 bank/一次 Handover 也不足。两种模式都不必把 cold Bootstrap 当作固有前置，本轮未实现首代分支或第三 bank。
