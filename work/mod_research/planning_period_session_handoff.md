# 网络规划期到同一原生 Owner 的本地映射

2026-10-08。本轮完全离线，不查找或打开游戏/Steam/当前存档/UI，没有新实机补丁或待用户操作。只编译并执行自建进程，冻结前驱保持不变。

## 解决的接线问题

网络 `PeriodCoordinator` 使用完整的随机十六进制 epoch，而原生 `ph::Binding.epoch` 是本地递增整数。两者不能截断互换，也不能在下一期清零原生命令编号。新增 `outputs/san14-link/planning_period_scope.py` 和 `planning_period_session.h/.cpp` 把这层映射实际接到 `planning_period_owner`：

- Python 从可信本地 Coordinator 的已同步、无待执行指令、未 Ready 的规划状态导出期初身份。包含房间、稳定势力绑定 epoch、当期 timeline epoch、完整 scope/cut 摘要、日期、累计序号与本机势力。
- 三个128位标识和32字节 scope 摘要全部参加版本化 SHA-256；C++ 使用同一固定宽度小端编码，逐字节与 Python 核对。原生 epoch 另从1递增，不截取网络标识。
- 一个驻留 Session 只能认领一次既有物理 Owner；初始 Controller、日期、原生 binding、空命令历史必须匹配。第二个 Session 不能重新映射同一物理桥银行。
- `Submit` 接累计全局序号，验证完整期次身份，再调用真实 `ar::Submit`。第二期继续 sequence=2；旧期请求、重复、零序号或跳号均不触发回放。持久去重仍由上层 journal 负责，不能拿本模块代替它。
- `Retire` 调用真实 Period.Retire，要求实际 Game/User 观察；内部历史关联网络 Scope 与原生 Receipt。`PlanNext` 只产生下一旬/下一期映射，要求稳定房间/势力绑定、未使用的 timeline epoch，以及与原生累计完成值相等的 cut。
- `Rebind` 逐字段复核计划及原采样器/context，调用真实 Period.Rebind；没有重置物理来源、Save 配置、Ready revision 或命令计数。随后仍封闭，必须由正式新 Controller claim 后 `Adopt`，再由调用者显式 release。mapper 不会自动释放输入或推演。

## 明确边界

这是可信本地宿主组件，不是网络 JSON 入口，也不是游戏注入器/房间启动器。Coordinator 的身份、采样器和物理实例必须由正式宿主取得。没有完成 TLS/IPC 与本 Session 的生产连接、密钥引导或异常重启恢复。

`from_coordinator` 必须在期初调用一次并保留不可变结果；它不是期初缓存。如果调用者在同一期中途重新导出不同 cut，新 Scope 会被已绑定原生 Session 拒绝。`Session::Snapshot` 只报告配置和历史，不重新读取当前游戏，因此不是 fresh 原生回执。变更方法仅允许初始化时的可信线程，并要求采样器不重入 Session/Owner/Controller；代码不建立对其他引擎线程的持续排他。

仅支持原生同 root/world/User。真正 B 读档换 world 仍由前驱拒绝。保存 Driver 的静态 room_epoch/附件未改变，本组件不新增保存许可、保存 generation 分配或存档产出。完整输入、保存、推演、世界替换权限全部 false。

Session、Controller 和物理 Owner 必须驻留至进程结束，Session 禁止析构。历史至多16期，容量达到后拒绝；这仍是有界研究组件，不能宣传为无限回合发行版。

## 验证与复跑

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机私有归档目录>'
py -3 work/mod_research/planning_period_session_test.py
```

最终 `planning_period_session_runs/20261008-213504-354624/result.json`：**21/21 PASS**，62份源码摘要重核一致。

- 4项 Python 协议/数据检查：完整 epoch 字节、非法字段、未同步/非规划拒绝，以及真实冻结 Coordinator 状态转换后的累计 cut。`loaded()` 的输入是明确业务模型，字节是诊断字符串；没有真实 B Load，没有本轮 TLS。
- 17个自建原生场景：两期两次实际 Owner 回放/深容器清理，另有错初始摘要、缺观察、未退休、房间/稳定绑定变化、旧 epoch、cut 清零、跳期/跳日、错势力、计划/回执篡改、采样器/context变化、错线程、实际日期未变及换 world 拒绝。
- 两期日期由 fixture 写入。原生回放桥、Controller 与 Period 生命周期真实执行；赏赐业务是前驱的明确替身。未执行战斗/日期引擎或真实保存。
- 生产对象以无 fixture 宏编译，和诊断 fixture 分开。自有子进程均正常退出，无活动游戏调试器。

result SHA：`1a7a9688d4bbb15ad41e893272e3e4559342841b8b47bdc9a1a622a887a7c8d4`

fixture SHA：`a7290ad4f99b29fa120d5156f72f5dbeb51f6c704d4e4c8d463699850990659c`

production library SHA：`91ff0133e8a287fece3aa76071b639f21213794f4a14bbf76a3ce0648278f949`

本模块本轮无失败构建/测试。`20261008-213240-333350`为21/21中间通过，随后增加禁止析构及 Snapshot 限定说明，最终重跑；中间记录保留。

另有[常驻窗口组合](planning_input_resident_handoff.md)的 resident-session 场景，实际链接本 Session，经过 Initialize/Retire/PlanNext/Rebind/Adopt 再调用同一窗口桥 Handoff，并等真实窗口 ACK。该场景的 Scope 是显式 fixture 值；不是新增 TLS 或双游戏证据。

下一步将可信本地宿主的 Coordinator/执行日志/原生 Session 通过同一串行通道接通。仍需正常保存的最小实机观察、连续真实新档/加载，以及完整输入与 writer 保护；不要用本次 Scope 或模型 loaded 回执放行实际游戏。
