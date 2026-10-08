# A 报告检查接入实际保存 Owner

2026-10-08。仅自有进程构建/执行，无游戏、Steam、当前存档目录或 UI 访问；无等待用户操作、无本轮游戏补丁或调试器。fixture 均为独立进程，结束即退出。

## 本轮实现与替换规则

`a_save_report_owner.cpp` 是冻结 `a_save_user_owner.cpp` 的明确实现后继，保留 `a_save_user_owner::Owner` 公开 ABI。构建时必须用新 cpp **替换**旧 cpp，禁止两份实现同时链接。旧 header、PE bridge、FreshSave Driver、storage gate、action gate 和 early guard 均未修改。

`a_save_report_owner.h` 另提供只读 `Snapshot(exactOwner, report)`。全局报告 sidecar 和原 User/Save bridge bank 都只归一个 Owner；全局不可重置 CAS claim 防止两个不同 Owner 并发初始化。失败初始化不释放 claim；Snapshot 先 acquire ready 再核对 Owner 身份，失败/无关 Owner 不能操作该 sidecar。

本轮真正组合了：

- 原 User/Save 槽 CAS、原 PE bridge、真实 Before/After/FINALLY、原 Driver 保存状态机与 native API 文件回读。
- 冻结 `a_save_action_gate` 的 Game/global UI 槽、两处实际动作补丁及真实线程暂停/检查/恢复的自有发布器。
- 同一个报告感知 Owner 完成两次不同文件的 binder、queue、Save 回调、原生读取接口和 CopyArtifact，并生成 first.packet/second.packet。

它不是又一个只生成回执的独立 guard。但仍是**负向准入组合，不是报告写入的完整排他**，没有生成 production permit。

## 检查实际插入在哪里

1. **Submit 之前**检查 early guard 的 User flag、队列数量/空树哨兵、身份、规划阶段和固定源片段。非空直接拒绝，不消耗 Driver generation，也不清掉报告。报告游标在受 SEH 的两次读取间复核，异常停止 Owner，不能在 noexcept 下直接崩溃。
2. **成功 Submit 后、实际 User 槽入口**再查。若此时出现报告，只抑制这一条尚未 claim Driver 的 User 调用，记实际 suppressed scope，取消该 Owner，不生成 native-return/After 证据。请求不会“等着自己排空”：阻止的正是可能 flush 报告的 User，永远等下去会死锁。
3. **原生 User 返回后**检查报告状态及绑定的 `World+165A` 游标。观察到变化先 Stop 再进入原 Driver.After，后者不会执行新的不可逆 binder。
4. **已进入 Save 阶段**仍检查固定 Root/World/User、报告 flag/队列形状和游标。发现变化取消导出资格，原生 Save 回调继续执行并收尾；不丢弃已提交工作的 FINALLY。
5. **实际 storage.validate 与 CopyArtifact 出口**继续做负向检查。已 Complete 的保存回执也不能覆盖此刻出现的报告变化。

CopyArtifact 先核对 generation 和 Driver Complete。正常六状态 Save、或 Finalized 但还没回到 User 时，只返回未就绪，不执行五状态 planning guard，更不会撤权。这是旧 IPC 高频轮询所需的行为；测试在每个 Save 阶段前以及 Finalized 后反复调用 Copy，再确认同代完成后确实能导出。真正的 Copy 报告异常同步进入普通 Owner 的 `error=Input / stopped=true` 并 Stop Driver；storage 回调发现的撤权在 Owner FINALLY 传播。上层无需读专属 sidecar 才能知道终态，后续 Submit 也不能绕过撤权。

五项检查都不清 flag、不清队列、不调用 flush 强行凑“空闲”。在入口取消的测试里，随后显式停止 action gate，下一次真正的 User 可以继续处理报告；flag=0 但队列非空本来就不会自动 flush，不能宣称所有 pending 都会自己消失。

Save 阶段管理器有六个状态，不能放宽旧 early guard 的五状态规划条件。新实现为 Save 阶段使用单独、只拒绝的固定报告字段检查，保持旧 guard 不变。此检查不等于完整状态阶段认证；原 Driver 仍负责自己的 Save 阶段、身份、来源与返回核验。

## generation 与导出边界

成功 Submit 固定自己的 generation 和报告游标。**第二代成功 Submit 后，不再允许重新 Copy 第一代**；调用方此前取得的第一代字节仍归调用方保存。旧代 Copy 仅拒绝该请求，不撤销正在执行的第二代。

这是后继对旧 Driver“两代产物可重复 Copy”能力的明确收紧：不允许最新报告游标替旧产物背书。没有 reset generation、重新签发旧文件或重试终态 Owner。当前 IPC 构建还没有切换到这个后继，本轮没有重跑 IPC/TLS，也不宣称 A 整体生产配置已接通。

`fullInputHold`、`reportWriteExclusion`、`saveAuthorized`、`roomReady` 始终 false。旧 Owner/action gate 的完整锁和 Ready 字段也保持 false。

## 实际机器码与替身

自有 User 小片段执行已确认的 19 字节 `cmp User+660 / je / call 2A1EC0 / clear flag`，指令地址和相对调用目标与 guard 指纹一致。外层栈准备/返回是 fixture；目标 `2A1EC0` 在 fixture 中跳到 **ReportFlushDouble**，并非执行完整 SAN 报告函数。所有报告树清理和游标递增在此轮组合测试中是明确的业务替身。

同样，Game/User/Save 和存储方法业务是既有自有替身；实际执行的是 Owner/Driver/桥/槽发布/文件 API 的组合机制。没有把这些小文件说成真实 SAN 保存。上一轮 `a_save_early_audit.py` 的归档实际报告写入证据仍独立有效，本轮未重复跑它。

旧 fixture 的 SaveState 对象放在 `base+240000`，与 guard 必须读取的真实代码锚点 `2403C2` 冲突。生成测试源时仅把该**测试对象**搬到 `base+340000`；生产地址不变。源码来源和生成规则均记录在测试脚本中，冻结 fixture 不改。

## 验证与明确未解决的反例

最终 15 个独立进程场景：

| 场景 | 验证行为 |
| --- | --- |
| two-saves | 同 Owner 两次 binder/queue，4 次读取接口，4 次真实 User 返回，10 次真实 Save 返回；第二次使用新游标；拒旧代 Copy 后第二代仍成功 |
| pending-flag / pending-queue | Submit 拒绝且字段不变、不消耗代次；测试业务显式清理后再完成两次保存，不冒充 Owner 自动排空 |
| entry-flag / entry-queue | Submit 后出现报告，只抑制当前未 claim 调用；无 binder/queue/native-return，取消后下一次原生调用确实返回 |
| late-flag / late-queue / consumed | User 内出现报告，或 flag/队列已清但游标变了；实际 After 拒绝，binder/queue 为零 |
| storage-append | 第一次真实存储 exists 调用后追加报告，后续实际 validation 阻止 binder |
| during-save | 已提交的一次保存仍有 5 次真实 Save 返回并排空，但不能导出产物；此时文件可能已经生成，不声称没写文件 |
| copy-flag / copy-cursor | 保存已 Complete，Copy 前出现报告或只有游标改变，旧完成回执仍不能导出 |
| competing-initialize | 两个独立 Owner 并发初始化仅一个胜出；失败者不重置 claim、不读取或撤销胜者 sidecar |
| submit-unreadable | 报告游标所在自有页实际 PAGE_NOACCESS，SEH 拒绝并停止，generation/binder/queue 仍为零 |
| aba-no-index | **成功展示尚存旁路**：报告在每次 User 内产生、消费、清零而游标不变，前后采样看不见，当前组合仍能得到文件 |

`aba-no-index` 的 PASS 表示反例被稳定复现，不表示旁路已修好。它证明需要实际报告作用域/写入来源或更早统一排他，不能将本轮检查作为生产许可。即使游标变化能识别部分“写后清零”，也不能推广为所有报告写入都可见。

## 运行记录与修正

- `a_save_report_runs/20261008-113538-568960`：首轮 11/11，尚无完成后 Copy 游标反例。
- `113653-130249`：补 Copy 独立字段检查与两例后 13/13；该中间版尚未修正独立 Owner 并发 claim 和旧代导出语义。
- `114137-369301`：复审后加入不可重置 CAS、generation 导出边界及 Submit SEH，15/15。
- `114330-628266`：收紧失败 Owner 的 Copy 身份检查，并在并发用例验证它不能撤销胜者 sidecar，15/15；此时尚未加入 Save 期间 Copy 轮询。
- `114627-439280`：最终 15/15，增加每阶段 Copy 轮询不撤权、Finalize 后未就绪，以及 Copy 故障进入普通 Owner 终态/拒绝下一次 Submit。

上述中间记录全部保留。不将早先通过的子集当成后来修正的证据；交叉审查确实发现了并发 claim、旧代导出、缺少 SEH，以及正常 Copy 轮询会误撤权四类先前测试未覆盖的问题，都修正并增加了针对性断言。本轮没有删除失败或重置 once-claim。一次工具 patch 因路径拼接错误在写入前被拒，重新正确应用，未造成源码部分更新。

复跑（仓库根；仅需原有私有 push profile，不访问游戏）：

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\Users\52708\Documents\Codex\2026-10-04\ni-li\work\mod_research'
py -3 work/mod_research/a_save_report_test.py
```

## 下一步精确缺口

- 真实源中 `3F9BA8` 在 call/clear 之前是可进一步统一观察/分流的候选。只跳过 `3F9BB0` 的 call 会继续清 `User+660` 并丢待办，不能这样安装。要分流整个块，必须同时保留正常分支、报告数据和原生返回路径。
- 若改 User 早段字节，冻结 action gate 的完整 User 哈希会冲突；必须用协调所有补丁的新后继，不能把任意外部 patch 归一化后放行。本轮未增第三处补丁。
- 未覆盖报告队列写入者、同次 User 内的 ABA、采样到 binder/存储复制之间的后台竞争、对象生命周期、非空渲染/选择下游及设备/消息消费者。生产安装器和全程输入排他仍缺。
- 本轮能说“报告检查已实际接入两次保存 Owner 的负向路径”，不能说“真实保存完整性已证明”“完整输入锁已完成”或“双机已能开始”。

新增文件范围：`a_save_report_owner.{h,cpp}`、`a_save_report_fixture.{cpp,asm}`、`a_save_report_test.py`、本 handoff。未改冻结文件、根 docs、tools 或 Git。

## 最终可复核标识

- 结果：`a_save_report_runs/20261008-114627-439280/result.json`，15/15，全部进程 exit=0，源码与私有 profile 未变化。
- result SHA-256：`1b0b55659bd6bb3f7c45d73c6414d27458b839abbe66dc61ed55340131f43a5d`
- 生产库 SHA-256：`5e4acbb045a23e6d78d17df36c38e4bc4d41f5bb5dc0a54246c1e6a77cec8f10`
- fixture EXE SHA-256：`37dd087c397b7548dea88a3b1d649d268977a35374f1769e4634f07faebfa102`

这些标识认证这一轮自有组合产物和结果，不是当前游戏对象、真实 SAN 保存或完整同步的运行证明。
