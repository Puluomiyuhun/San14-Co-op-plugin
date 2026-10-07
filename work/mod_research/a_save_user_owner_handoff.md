# A 保存与 User 子集等待：同一槽所有者后继

2026-10-08。前驱是冻结的 `checkpoint_fresh_save_session*`。本后继只新增 `a_save_user_owner*`；旧文件未改。**生产库已编译，20 个自有进程场景通过；没有接触 SAN14、Steam 或真实存档。**

## 具体解决了什么

旧保存 Owner 必须独占 User 的 vtable 槽，规划 Dispatcher 同样需要该槽。两者不能直接套在一起：规划 wrapper 可以不执行原生 User，而它的返回不能作为保存的 AFTER。现有 Dispatcher 和保存 Driver 的 claim token 也不同，不能让两者同时声称拥有同一调用。

本后继面向首轮“连续两旬、不新增命令”测试：由一个进程生命周期 Owner 发布 User/Save 两个槽；在同一个物理桥内选择“原生保存观察”或“User 子集等待”。没有把规划 wrapper 当成原函数，也没有在抑制分支合成保存完成回调。

- 原函数仍固定 `base+3F9B00`、`base+4AA650`，沿用生产映像/profile 校验、入口字节固定、槽 CAS、存储身份和文件固定。
- 新 `SetUserHold(bool, revision)` 使用递增 action；等待只有在一次实际 User 调用经过已冻结 `checkpoint_native_input_pending::Adapter` 检查后才形成子集 receipt。检查实际调度器返回地址、线程、固定 manager 地址、当前 cache 地址、绑定身份和真实 User/span/stack/pending 状态。
- 实际抑制分支不调用原函数、BEFORE 或 AFTER，也不能 claim 保存 token；只执行物理 FINALLY。统计清楚区分 physical started、native returned 和 suppressed scopes。原生分支继续保留完整 RAX/XMM0 与 SEH。
- `Submit`、`SetUserHold` 和物理入口的路由选择共享控制锁及活动作用域计数。正在执行的原生函数不能被后来的 hold 重标记成“已经停住”。保存期间拒绝新的 hold；已 hold 时拒绝保存，**不会偷偷放开 User**。
- 同一个 Owner 可以先实际抑制 User、明确 release、导出两份不同的文件，再恢复 User 子集等待；不重置桥 bank、代次或 once 状态。
- 未知菜单、身份漂移或外来调用不获得抑制授权，转发原生处理并停止后续准入。Owner 已出错时不再导出 artifact。Stop 后已承诺保存仍可收尾；模块和 Owner 不卸载。

## 如何验证

需要 Windows x64、VS 2022 Community C++ 和外部只读私有 `checkpoint_push_profile.h`：

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT = 'C:\san14-private\mod_research'
py -3 work/mod_research/a_save_user_owner_test.py
```

脚本只编译生产静态库并启动自己的 fixture 子进程。缺 profile 直接退出；不查找游戏进程、不运行历史 live 脚本。private profile 通过 `/I` 引入，不复制到仓库。

最终运行：`a_save_user_owner_runs/20261008-014011-202116/result.json`，20/20 PASS，源码和私有输入在编译测试期间未变。

- 结果 SHA256：`0397a32fc4da6ab37fe7dd4a52470f90ed666f53c5c57aaf1b81405d7cf68db4`
- 生产库 SHA256：`c9a6673233a7b6d3a2994a7be19866bff2aea8cf2ffcb1468caa8b37f82f8873`
- fixture SHA256：`e6b79fbdc70d77d4f653769695b4211a38ec6c692d848cd0ebb069de9f9f43b7`
- 私有 profile SHA256：`8b221226843ed047fe24b3599c9141219c48bbe101191e7c0c4dc1f01a2497ed`

覆盖前驱的原函数替换拒绝、Stop 边界、异常、存储代次、读取字节和阶段跳跃；新增同槽 hold/save 两代、已 hold 拒绝保存、菜单/绑定/调用来源拒绝、原生回调内申请 hold 拒绝，以及使用真实线程和事件的“原生 User 尚未返回时另一线程申请保存/hold”拒绝。成功例两次 binder、两次 queue、四次 native API 全量读取，两份日期和摘要不同的固定文件。

成功例还直接调用 `checkpoint_fresh_save_packet::Encode`：输入来自同一 Owner 的 `CopyArtifact(1)`、`CopyArtifact(2)`，在该运行 `success/` 下写出 `first.packet` 和 `second.packet`，供后续 Python/真实本机 TLS 组合使用。本组合用例未手工填写保存成功 receipt，而是使用执行保存组合后取得的完整 report 和固定 bytes。packet 本身仅检查格式与完整性，不能证明来源；来源必须由可信本机 Owner/coordinator 的持有关系保证。两份各 316 字节（284 字节头、32 字节诊断内容），仍不是实际游戏存档。

独立审查发现并修复 `Stop` 或 sticky error 时正在 hold 会持续抑制 User 的缺陷。最终新增 `stop-while-held` 场景，并增强菜单/绑定/调用来源拒绝场景，验证同一发布槽在停止或错误后恢复透明原生转发，真实 AFTER 不产生未请求的保存证据；已承诺的保存仍沿原 save lane 收尾。旧通过记录保留，但未覆盖这些边界，不能代替最终 20 项结果。

第一次运行 `20261008-013123-206634` 失败：沿用前驱 fixture 的 cache mode=0，不能通过冻结 pending inspector 要求的规划 cache mode=1。修正的是测试世界的初始状态，没有放宽生产检查；原失败记录保留。后续来源核验和并发补充均有独立运行记录。

原生 User/Save/binder/queue 业务和 Steam 文件方法仍是明确的替身，32 字节输出不是 SAN14 存档。真实的是编译后的 PE 桥、实际自有对象的 vtable 发布/调用、TLS/SEH、冻结状态检查器、存储绑定/Gate 和 Windows 文件操作。**20 项通过不等于真实游戏连续保存已成功。**

## 仍不能做的事与下一步

1. **这不是完整 Dispatcher 集成。** 现有远端赏赐队列不在这个 Owner 内；不可再安装旧 Dispatcher/六桥来占同一 User 槽。下一步应从唯一 Owner 扩展经核验的规划命令 lane，或把 Dispatcher 的队列与原生调用证据拆开整合，不能叠挂 wrapper。
2. `user_subset_held` 不是全输入锁。`all_input_held`、`room_ready`、`full_world` 始终 false。父 Game/UI、子界面、消息和已锁存输入仍需要完整排除。**由于保存要求真实 User 返回，已 hold 状态直接保存目前明确拒绝**；应先建立独立的真实输入排除，再有证据地开放必要原生更新，而不能调用 release 后假称安全。
3. `sample_input` 必须是当前进程的只读、不可重入配置采集器，不可调用 Owner 方法。实机 Config/安装器和房间 epoch/命令排空授权还没接入。当前 hold binding 固定于这个 Owner，不代表跨 world 换代。
4. 最多两份保存、一个常驻 bridge bank；无无限旬数、卸载或重复初始化。B 连续加载和 world 换代后的规则重绑定也不属于此模块。

本轮没有等待用户操作，也没有安装游戏补丁或附加调试器。下一步可继续离线整合；实机运行前仍需重新核对当前游戏和安全阶段。
