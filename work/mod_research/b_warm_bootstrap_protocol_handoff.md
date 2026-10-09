# 首次身份切换的正式收档与房间确认

`b_warm_bootstrap_protocol.py` 是 `bbfd2fc` 中 `BootstrapReceivedApply` 的明确后继；冻结前驱不变。此前首代只能做诊断，因为普通 Journal 要求读档前已是 B 势力。现在使用独立的 [BootstrapCheckpointJournal](../../outputs/san14-link/checkpoint_bootstrap_journal_handoff.md)，如实保留读档前的 A 势力，读档完成仍必须是 B。

## 调用顺序

1. 房间从开始声明 `san14.partial-world.object3001-force52-date.v1`，只验证已审计两表字段及日期；这不是完整世界覆盖。A 使用现有 `host_observation`、保存接口与 `FreshSaveBinding` 发布本期档案。
2. 第 1 期使用 `receive_bootstrap_staged`，通过现有 TLS 下载并直接创建新 schema 的 SQLite；不会迁移普通 Journal。`bootstrap_receiver_from_journal` 从已持久化的 B 收档重新核验 Receiver。
3. `BootstrapProjection.apply` 核对初始期、尚无已应用检查点、真实 source 当前身份及双方等待边界，调用实际 `begin_guest_load` 和 Journal `reserve_load`。
4. 本地 `native_load(permit)` 调用同一个 `FormalBootstrapReceivedApply.apply(..., reservation=permit)`，并返回它的 `completion`。后者沿已持有的 `BootstrapRulesBridge` 恢复旧规则、加载 bank0、切为 B、重装新规则，再保存本地结果并发诊断 ACK。不要从网络报文生成所谓 native 成功。
5. Projection 验证原生结果与加载后 B 身份、已声明数据对照，完成 Journal，再用新鲜的双方观察调用实际 `loaded()`。B attachment 和协议 epoch 更新；它不释放输入或授予 Ready。
6. 第 2 期使用普通 `receive_staged` / `receiver_from_journal` / `TrustedProjection`，继续复用同一个 bridge、warm、WorldLifecycle；`FormalBootstrapReceivedApply` 自动回到前驱的严格 B 视角检查，使用 bank1。

首代、后代分别使用新的收档目录和本期 adapter；不能重建 bridge/warm 来清掉代际历史。首次 formal 路径不接受无 reservation 的诊断调用。第 1 期并不单独证明原生第一次加载，仍由常驻 bridge 的历史和一次性加载器共同限制。

## 失败行为

预约后的错误留下 INTENT；加载完成但 ACK 回复丢失也保持等待，不再次读档。新建 Projection 对象不能恢复一个加载许可。普通库和 bootstrap 库互不解释，不能给旧 INTENT 改 schema 或把读档前实际 A 视角填成 B。

## 验证与边界

独立组合命令（不访问游戏或 Steam 存档）：

```powershell
py -3 work/mod_research/b_warm_bootstrap_protocol_test.py
```

5 项：首次 A→B 后同所有者第二次 B→B，伪造预载 B 视角拒绝，普通 Journal 拒绝，实际 TLS ACK 丢回复保持 INTENT，错误 source 完成身份拒绝。成功项连续调用真实 Journal/`PeriodCoordinator.loaded`，第 1→2→3 期，没有 `complete_model`；保留 3 代规则和 2 份真实临时文件备份。

实际执行范围是本机 TLS、SQLite、Windows 原子替换/读取租约、原 `ResidentPort` / `WorldLifecycle` 的检查。保存、加载、发布器、游戏内存和等待边界均是明确替身。此组合尚未与生产 `RulesFactory`、真实 `Resident.load`、真实输入/执行边界同场进游戏；也没有两个远端游戏。新模块是本地适配接口，不是可发朋友的一键安装包。

最终运行：`b_warm_bootstrap_protocol_runs/20261009-192704-289501/result.json`，SHA256 `12fff59a27f043f59bd81d4c92dc4a8edc125a6f1a3b0a7c5e3f74f97cf812dd`；33份源码及90份私有产物逐份核对一致。

精确运行哈希及本轮限制见 [公开证据](../../docs/evidence/2026-10-09-warm-bootstrap-protocol-factory.json)。原失败游戏退出仍未确认，本轮不重试、不清 claim、无新补丁/调试器。
