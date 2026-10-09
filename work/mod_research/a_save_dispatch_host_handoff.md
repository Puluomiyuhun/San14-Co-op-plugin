# A 保存宿主、真实 Owner 与 IPC 邮箱组合（2026-10-09）

## 本轮结果与边界

`a_save_dispatch_host.{h,cpp}` 把既有 `a_save_dispatch_ipc::Server` 和 `Mailbox` 接到**同一实际 Owner、Gate、Controller、Driver**。不再提供 Owner::Snapshot/Stop/构造函数替身。正常两期真实 pipe Submit/Copy 均完成；另一例在 Driver 已 bind/Queued 后断开 pipe，继续真实桥和 Driver FINALLY，最终只由宿主线程释放 producer 锁，邮箱仍为 Unknown，没有导出或重投。

这仍是自有进程诊断组合：虚构世界、正常帧调用位置、binder/queue/原生 Save 业务及存储接口均为明确替身。实际被保存的数据为 32 字节诊断内容，并非游戏存档。没有碰游戏、Steam、UI、当前存档，也没有安装父回调、提高 permit 或证明所有游戏 writer 已冻结。

## 接入方式

1. A 角色的可信固定线程初始化真实 Owner/Gate/Controller、Ready，随后初始化 Mailbox 与 Host；Server.Config.owner 指向这个**相同 Owner**。Server 在线程内运行，submit/copy 用 Mailbox::Adapter，executionStop 只停止邮箱。
2. 可信父调用者用 `BeforeFrame()` / `AfterFrame()` 包围正常 Game/User 调度，不能在活跃 User/Game/Save 回调内部调用。Host 固定初始化 TID、精确 CurrentController 与 period serial；网络报文没有原生地址、回调或 TID 字段。
3. 有待处理请求时，Host 取得宿主 producer 排他锁，调用实际 Controller::BeginObservation；正常桥 FINALLY 之后 EndObservation 验证真实计数，再构造 Evidence、领取请求、调用实际 planning_checkpoint_save::Submit。只有其接受成功才 mailbox.Accept，因而 IPC Submit 的 true 不等于仅入队。
4. 随后正常 Save/User 桥推进实际 Driver。Submitted 阶段不重复 Controller Begin/End；真正 Complete 后实际 planning_checkpoint_save::Copy 再 mailbox.Complete，宿主释放 producer 锁。原子拷贝、SHA、phase/worker/return 检验仍走原有生产实现。
5. 第二期先交付第一期包，再由可信宿主实际 Retire/Rebind、初始化下一 Controller、Host::BindPeriod；物理 Owner/Gate/bridge 不重建。fixture 的日期/绑定变化明确是业务替身，不代表实际跨旬模拟已接。

**每一个 BeforeFrame 返回 false 都不表示跳过正常原生帧。** 已 bind 的工作必须继续正常原生回调，再在后续安静宿主边界重新检查排空。Host 不拥有调度器，不能据 false 停掉原生推进。

## Stop 与锁的准确含义

- monitor/pipe 线程不会碰 Controller，也不会释放 producer SRW；只有初始化宿主 TID 可以释放。其他自有 writer 线程确实测试了持锁期间拒绝共享访问，真实完成/排空后可获得共享锁。
- IPC Server 的 Stop 仍会调用实际 Owner.Stop。停止邮箱不代表原生回调排空。已接受请求被保留为 Unknown，不再产生成功的 Copy；即使真实 Driver 后来 Complete，也仅用于释放宿主资源。
- 停止后的安全 drain 要求实际 Owner/Gate/Driver 无 active，再检查目标 generation 的 Complete、worker joined、finalizer returned、return matched、file bytes verified；或零 bind/queue 的 Cancelled。不能达成则保留 Unknown 和 lease，所有依赖必须持续存活，不能自动销毁、重新提交或伪称干净收尾。
- `pcs::Submit == false` 可能发生在实际 Owner 接受后、Gate 后验失败；代码在调用前就记录可能发生副作用，故不能按 false 直接释放。这处为独立代码审查修正，**没有**声称 bound-disconnect 动态覆盖了这种后验竞争。若 Submit 在更早处失败，Driver 未进入目标 generation，仍保守保留 lease，待额外排空证据；没有添加自动恢复路径。
- 没有显式调用 Ready(false)，但冻结 Owner.Stop 会在 lane 结束后透明转发 User；因此**不保证 Stop 后仍完整暂停输入**。
- 跨帧 producer SRW 仅覆盖 fixture 自愿参与的竞争 writer。真实游戏的 writer 集合、锁顺序及 Save 自身所需任务不能被这把锁反向挡住，均未证明；不能把它直接装成游戏全局大锁。
- Host 限 A 角色。未来同进程动态切换 A/B 时，不能在 13DC09/13DC0E 叠装两个父来源 Owner。

## 可复核运行

运行：`py -3 work/mod_research/a_save_dispatch_host_test.py`。测试只生成独立自有 EXE、子进程客户端、命名管道和诊断文件；需要本机已有私有 fixture profile/runtime。默认所有生成物在仓库外的相邻 `work/mod_research/a_save_dispatch_host_runs`。冻结 held builder 的生成副本及逐行 diff 随 run 保留，不修改旧源。

最终：`20261009-093718-864497/result.json`，**2/2 PASS**。

- Result SHA256：`42243bce19340631cf25ce01b6e7ab053df2c99740878bb8e3884302907ca396`。
- 69 个来源、36 个二进制/对象、5 个生成 include/build 文件、3 个私有输入均有 pins；来源及私有输入前后相同。生成 builder 自身另有 SHA。
- fixture.exe：`07ef045a608119cdd0a92602537501256348db9a27080ee85bda7ab8075156b1`。
- 无 fixture 宏库（沿用生成器文件名 `a_save_held_ipc.lib`）：`fcc5578d06878a294acffa109913bf56175b51a16363441251e2c50342ad5449`。
- 实执行 Host `host.obj`：`e10cc281f3e65b3ec51314b7a1ea738df59f6950601f0019857fbf05a5e99ded`。

无宏库完成编译，但实际运行 EXE 链接了带既有 fixture 宏的 Owner/Gate/Driver/native-binding 对象，以接受自有映像及业务替身；Host/IPC/mailbox/interlock/held 和其控制逻辑实际执行的是无宏对象。不要把无宏库成功编译写成真实游戏已运行。

正常例：观察/Submit/Copy/释放各 2 次，同一物理 Owner 完成 2 个请求；第二期真实 Retire/Rebind，Ready revision 保持，两个收到的实际 wire packet 由冻结 Python decode_packet 再核 SHA、日期、32 字节及 phase/worker 证据。另测错线程 Host 调用、重复 BeforeFrame 拒绝。

断线例：原生 Driver bind=1、Queued 后子进程只关闭 pipe 并保持存活，最终运行取消计数字段为 1（GetTickCount64 差值加 1，只证实在 1500ms 界限内唤醒，不是精确延迟基准）；monitor 不释放宿主锁，随后真实五段 Save 与 User 返回令 Driver Complete，Host 仅释放一次。最终 mailbox Unknown，copies=0，无重新领取/提交。它验证断线后的完整 drain，不只是 snapshot 替身改变状态。

## 保留的失败

- `093321-791417`：fixture 局部 b/mode 遮蔽继承全局，在 /WX 下编译失败；重命名后解决。
- `093408-307532` 与 `093448-860576`：正常两期通过，断线例失败。为跳过旧 helper 的 `!stopped` 断言误用了已有 `during-save` 模式；该模式还在 Save phase2 注入报告漂移，因此出现 Driver54/Owner11。已改为自有 completeOwnedSave helper，保留原五 phase/User 路径，只省略旧 healthy poll 断言，不改变原始业务模式。失败并非游戏行为，也不是冻结 Stop 校验拒绝的证据。
- `093611-742419`：首次 2/2 PASS；最终 run 额外补齐对象/私有输入/Python 解码器 pins，并收紧无 Submit 时必须 !save_lane 才释放。

## 尚缺的关键接入口

需要**有真实来源和完整 writer 协调证据的父宿主边界**来调用 Host，而非 fixture 手工包围回调。已知 13DC09/13DC0E 归档调用链只证明一个父调度位置，尚不证明跨帧固定 TID、所有输入/子任务/writer 排空或可以发布正常 Save 的许可。下一步应在独立来源后继里证实这些合同，再连接本 Host；不应放松现有 permit 或从当前 fixture 成功推导实机许可。

本轮没有活动游戏补丁/调试器，不等待用户操作。所有冻结前驱未修改，公共文档与 Git 交由主 agent 整合。
