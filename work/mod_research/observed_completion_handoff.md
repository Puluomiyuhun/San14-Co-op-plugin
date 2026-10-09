# 有限观察正式完成：A Room 与 B Session 的共同合同

2026-10-10。只用于已约定双方不新增命令的窄诊断；本轮没有访问游戏、Steam 存档或 UI。冻结旧强完成接口不变，新源码不会将采样成功解释成持续持锁。

## 接口和生命周期

- `observed_completion_contract.py`：独立 action `observed_adapter_completion_v1`、HMAC domain 和合同 `san14.no-new-command-observed-boundary.v1`。签名包有压缩前后上限、规范 JSON 和固定字段检查。边界绑定 scope、epoch、period、checkpoint、profile、日期/势力、PID/birth、递增采样序号和样本哈希。
- `a_observed_room.py`：`ObservedRoom` / `ObservedProjection` / `ObservedFreshSaveBinding` 是同日 Room 的显式后继。拒绝旧强 action 和 `enroll_adapter`。新 `enroll_observed_adapter` 接可信本机 `host_boundary(profile,kind)`、`host_sampler(profile,receipt_key)` 和当前原生回执键；复用原文件、一次性 intent、原生完成及世界投影检查。
- [AObservedBoundary](a_observed_boundary_handoff.md) 实际检查 A 已安装的本机保存入口、Runtime 报告、当前规划及双读世界投影；调用者必须提供实际保留的 reader、plans 和 Runtime Snapshot 通道。
- [GuestCompletion](b_observed_completion_handoff.md) 接同一个实际 `Session`，完成 begin → durable reservation → apply_native → Journal.complete → signed complete。Session 仍负责本地原生对象，Guest 单独记录正式完成历史。

每次往返都返回 `human_no_new_commands=true`，但 `input_exclusion_proven/scheduler_fence_proven/atomic_snapshot=false`。`safe_boundary` 在此后继中仅表示本次观察空闲；不是冻结前驱强接口中的连续 fence。`native_gameplay_enabled/full_world_verified/ready_authorized` 也不因完成而变 true。本机回调必须来自可信启动编排，不能把网络包当本机观察源。

A 的观察日期是 manifest 的已保存日期，势力仍为 source。B begin 使用当前 before/currentForce；B complete 的实际观察 profile 已变成 loaded/target。两者都携带原始 profile 绑定，另校实际观察 profile SHA，避免把加载前检查冒充加载后验证。A provider 的 year/month/day 实际字段也检查，不能只在封装时填写期望日期。

## 已完成的同一组合

`b_observed_completion_test.py` 使用实际新 A provider、ObservedRoom、RoomTurnControl、同一 B Session、原完整规划检查、真实 loopback TLS 和 SQLite：

`submit1 → signed loaded1（仍为中旬）→ 双方 Ready/seal → RequestNext → submit2 → signed loaded2（下旬）`

同一 B 对象组保留两 bank、三代规则历史。没有旧 strong completion、恒 True held、run_model 或 complete_model 替代正式完成。重复相同 complete 只返回原回执，不加载第三次；丢 begin 回复时零次加载，丢 complete 回复时保留已完成的一次加载并终止，不自动重试。待处理输入和签名包中伪称完整 fence 均拒绝。

**这仍是离线组合。** 两 TLS 席位在同一 Python 进程中，保存、加载、发布、Runtime 和游戏 RAM 是明确替身；未成功调用生产 `Session.open` 安装整组对象，未运行两台游戏。旧独立 B 子进程测试是另一个已提交场景，不混入本轮表述。

## 验证与证据

- 共享合同 9/9：`observed_completion_contract_runs/20261010-003828-921664/result.json`。
- A provider 7/7：`a_observed_boundary_runs/20261010-003644-592578/result.json`。
- 同一组合 5/5：`b_observed_completion_runs/20261010-003948-526128/result.json`。
- 根独立复核全部来源、4 份归档输入和各产物哈希：`observed_completion_root_audits/20261010-004223-166770/result.json`，SHA `07bcddd7408b3447fba20253c3eb8e9b34d1ff33af6749f6e9d298853b80c48d`。

相对路径均在仓库旁私有 `../mod_research` 下；原始日志、私钥和产物不提交。公开概要见 [evidence](../../docs/evidence/2026-10-10-observed-completion.json)。早期成功记录保留；最终结果针对新增实际 A provider 接线和日期检查后的源码。

## 下一步：两侧启动编排，而非重做完成协议

1. A 显式新入口复用已批准的 `a_native_turn_start.py` 安装/收尾，Prepare 前组装真实 Room、binding、RoomTurnControl；把本机 retained Runtime Snapshot 接 A provider，artifact 与 receipt 来自同一 channel。旧 launcher 仍只是本地诊断，不能冒充联机入口。
2. B 显式新入口复用 `Session.open` 的本机构建、fresh 进程、reader/bridge/rules；同一 TLS、key 和 Session 交 `GuestCompletion`，接两次真实 ReceivedCheckpoint。失败保留 Session/原生对象和终态，不 reset claim 或重新加载。
3. 两侧入口就绪后配置真实可达地址、TLS 指纹、独立 key，先验证远端传输，再安排同日开局＋一次旬末的窄双机实测。另一电脑重新建立本机证据；不照搬 PID、内存地址或历史 receipt。

完整内政、任意势力、遮罩、持续输入限制、事件选择和超过两代的能力仍分项开发，不扩大这次零新命令首测门槛。当前不等待用户操作；本轮没有安装任何钩子或调试器，旧实机结束后的恢复事实未重新测量。
