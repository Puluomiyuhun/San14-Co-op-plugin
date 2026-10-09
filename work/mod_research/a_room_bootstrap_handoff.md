# 同日起始快照 → 正式 B 完成 → 一次真实旬末的协议后继

2026-10-10。仅新增 `a_room_bootstrap_protocol.py` / `a_room_bootstrap_test.py`，冻结前驱未改。本轮没有访问游戏、Steam、存档目录或 UI。

## 接口与期次

`BootstrapCoordinator` 从原 `PeriodCoordinator` 派生，`BootstrapRoom` 从真实 `RemoteCompletionRoom` 派生。先按原 TLS 流程绑定两席及 Coordinator，再构造 `BootstrapFreshSaveBinding`。

1. `c.begin_bootstrap()` 只接纳初始期次 1、原日期、零命令原前缀、无在途命令/事件、两连接完整且尚未准备的边界，进入独立 `BOOTSTRAP_EXPORT`。没有调用 `begin_simulation`，没有把日期临时改成上一旬。
2. 首次 `binding.reserve(1, filename, observation)` / `publish(1, observe)` 沿原真实 artifact 校验、CheckpointPackage 和下载服务发布同日档。旧数据读取器必须来自本轮 retained native channel，不能绑定归档文件重放。
3. 原 RemoteCompletionRoom 的签名 `_begin/_complete`、持久 INTENT、加载完成及世界投影核对全部保留。仅原 `Coordinator.loaded` 严格接受完成后才标记 bootstrap 完成；原 loaded 自然将 period 增到 2、更新随机 wire epoch、清 Ready，日期沿 manifest 保持原日。
4. 之后两席真实 Ready、`seal_inputs()`、`begin_simulation(permit)` 才能进入下一阶段。普通第二档继续要求 `next_node(c.node)`；首份正式完成前不能 seal 或获得下一原生绑定。没有自动 Ready、自动推进或模型 loaded。

这里 period 是**检查点代次**：1 为同日起始快照，2 为首次实际旬末。两个成功检查点不表示推进了两旬。旧 `BootstrapCheckpointJournal` 仍只表示首次 source→target 视角转换，独立 schema/一次性 SQLite 和完成 target 校验均原样复用；它本身不定义同日起始阶段。

## A 控制接法

```python
binding = BootstrapFreshSaveBinding(room, c,
    native_room_id=bytes.fromhex(digest(c.scope)),
    native_room_epoch=fixed_native_room_epoch,
    artifact_reader=control.copy_artifact,
    source_kind='LOCAL_NATIVE_PROVIDER')
c.begin_bootstrap()
prep = prepare_from_room(fresh_native_prepare, binding)
# 实际安装和原父回调就绪仍由批准的本机启动器完成。
# control.drive 用同一真实 channel，经正式 B 完成后才 RequestNext。
```

`c.native_binding(native_epoch_base)` 返回固定六字段：`generation, period, epoch, input_digest, node, descriptor`。本机 Runtime 的数值 epoch 是 `base + period - 1`，满足现两代 Runtime 的严格 `+1`；独立随机 128 位 wire epoch 原样保留在 descriptor 中，不截断或冒用为 native epoch。`native_room_epoch` 两次保持不变。input_digest 是真实 scope、wire epoch、period、attachment、当前日期、完整 seal 和阶段的规范化摘要。

`binding.validate_context()` 在 room→coordinator 锁序下核当前实例、固定 scope、原连接、host attachment、封口及阶段，返回 boundary 副本。`host_observation(binding, ..., expected_node=None)` 使用已有完整两表读器和三次上下文/两次数据读。默认采本次导出日；RequestNext 前可显式采当前原日，且只接受当前日或导出日。数据/身份/边界必须仍完整相等，强 `verify_held` 检查没有放宽。原 `binding.reserve` 仍只接受导出日，所以旧日观察不能拿来提交旬末 Save。

本文件保留强边界合同，并不提供游戏 fence。自有测试中的 True 是标明的 held 替身，不能移植到生产。若采用无新命令窄诊断，需要另一个明确弱合同后继；不能把稳定采样改称持续排他。本后继没有因全内政或遮罩未完成而新增首测门槛。

## 与冻结源的差异范围

- Coordinator 新增初始阶段及同日首次 offer，loaded 本体直接调用原实现，后续 offer/seal/begin 保留原语义。
- Room 的 bind/install、ArtifactService 构造、Projection 构造、FreshBinding 构造是显式窄后继：将原 exact Coordinator 类型改成精确 BootstrapCoordinator；Room 接受该明确类层级。首次安装日期由 next_node 改成初始原日并核 bootstrap checkpoint；二代 `_next_checkpoint` 直接继承原完整 receipt/attachment/date/epoch 校验。
- ArtifactService 完整重算字节和原限额/票据/连接检查不变；Projection 的采样、完成检查及 RemoteCompletionRoom 签名协议不改。
- 换新检查点时仍清上一代 `warm_completion` 诊断 ACK，与原 WarmRoom wrapper 一致。相同检查点重复安装不重置票据或 ACK。
- FreshBinding 的 reserve/artifact/publish/hold/status 原样继承；仅初始 boundary 日期和阶段是明确后继。

## 最终验证

命令：`py -3 work/mod_research/a_room_bootstrap_test.py`。5/5 PASS，真实 loopback TLS，B 为独立 Python 子进程，真实接收文件和 SQLite Journal，所有正式 loaded 均来自原签名回执服务，没有 `run_model` 或 `complete_model`。

- 同日起始快照 → target B 完成 → period2 仍同日 → 实际 Ready/seal/begin → 下一旬检查点 → 正式完成。第一旧回执在第二完成后只精确幂等，不回退期次。
- 当前原日观察合法，跳旬观察/初档错误日期/非零命令前缀拒绝，未完成不取得下一绑定。
- 错误 target 完成进入 HELD，不解锁 bootstrap。
- 丢失完成回复不重做 native；持久 Journal 保留 COMPLETED，Ready 仍空，不能因此自动推进。
- 联合 **实际 `RoomTurnControl`**：`submit1 → signed loaded1 → ready/seal → RequestNext → submit2 → signed loaded2`。两档来自本次 channel 替身结果，绑定真实房间；原生调用和 RAM 是明确业务替身。保存日期为 11/21，两个 protocol period 为 1/2，最终 period3/day21。TLS/Journal/room/control 为实际模块。

最终私有记录：`a_room_bootstrap_runs/20261010-001421-328274/result.json`。

- result SHA256：`d9c3098cb7cedf6869e7aa96457a26d1b7da6ecd2cba803aa71550c8d7e3b280`。
- 38 份来源和 56 项产物均复核一致，来源运行前后稳定；子进程、TLS 服务按原 fixture 正常退出。
- protocol SHA256：`6a16d7782a9f8d220edc0095ea46349fcce533d7cc1a1a4d8227490e881e1290`。
- test SHA256：`996d18c8189679c8dda4dfba41fa28d9a8e8dc4e32ab2561f6a697857af8877d`。

早期 import 缺失注解依赖失败保留于 `001128-561908`（含当时源副本）；之后 `001128-812853` / `001255-744562` 为四项中间 PASS。最终在 WarmRoom ACK 复位、当前日观察及 root 控制接线修正后执行五项，未修改旧结果。

仍未证明真实双机 native 组合。此模块解决了同日起始阶段及 A 控制与远端正式回执的协议接缝；批准本机安装、真实规则/加载持久对象、明确诊断边界合同和双机启动编排由后续启动器接入。
