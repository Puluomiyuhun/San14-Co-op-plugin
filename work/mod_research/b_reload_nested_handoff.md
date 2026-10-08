# Root 与内层观察端口的硬件断点组合

本后继只在自有进程读取已有归档运行。没有游戏发现、Steam访问、实机补丁安装、加载许可或世界一致证明。主线程维护组合测试和最终结果；下面是源码接口与约束，不能据此声称实机双客户端已可用。

## 为什么需要后继

完整 Root runner 进入 User/Load 后，旧 User 输入、Load start 和 Load join 观察器都要求 DR0–3 空闲。让 Root 永久占四个槽会导致这些内层观察器拒绝；整个 Update 期间关闭 Root 又会丢失 yield。

Root 后继在真实入口 CONTEXT 中释放不再需要的 entry/done 点，只保留 DR1 return 和 DR3 yield。内层可借 DR0/DR2；真实 return 后，内层必须已经在 FINALLY 归还，Root 再切为只观察 DR2 done，最后还原原始六个调试寄存器。不是按用户提供的时间推测阶段，也不伪造 Capture。

## 替换关系

- `b_reload_nested_root_ports.cpp` 替换 `b_reload_root_worker_ports.cpp`，旧头/API不变。共享租约的实现也在本文件。
- `b_reload_nested_start.cpp` 替换 `checkpoint_task_native_start.cpp`，旧头/API不变。
- `b_reload_nested_completion.cpp` 替换 **`b_reload_title590_ports.cpp`**，保留 Title 的三点观察、自动 +590 发布与原 namespace/API。
- `b_reload_nested_input.cpp` 替换 `checkpoint_persistent_input_hwbp.cpp`，保留原 namespace/API。
- `b_reload_nested_debug.h` 是内部合作接口。不能把新旧同名实现同时链接。

Root 全部 API、Provider 的 immutable task 归属与物理桥仍沿用原组件。仅更换观察实现，不把 User 改回人工 Root Capture。

## 租约与失败路径

Acquire 在真正 Root 所在线程执行，核当前 Provider、base、generation、entry 已接受、active execution、无其他借用、未终止及未发生错误。只有固定 Load start pair、Load join，或者经过完整字节核验的 User input 单点可借用。User input 还要求调用对象就是当前 Root callable 所指的 User；生产地址固定为 base+3F9DAF，fixture 也必须是 MEM_IMAGE 的原33字节块。

租约记录 Root 所有者、递增 serial 和线程，不靠断点地址相同认领。helper 可在另一线程读取该不可替换记录，但目标线程暂停时必须核完整借用前/后的六寄存器布局与 DR6 事件位。任意外来占用仍拒绝。内层只在精确恢复 Root 布局、无不确定状态之后归还；Root return 若发现尚未归还则标 Conflict，Root FINALLY 不覆盖活动借用。跨线程 Release、错代、重复归还或过期 serial 均拒绝。

helper 超时是拒绝继续放行，不是强制取消线程；旧排空等待与驻留约束保留。代码不修改普通参数/结果、真实返回地址或原生指令。Root yield 在整个 Update 内始终被观察；这不等于已经验证真实 yield/resume 的完整业务分支。

## 尚未涵盖

组合 harness 使用实际归档 runner、thunk、scheduler 与 OS CONTEXT，但构造器、业务函数及 Root 激活仍是明确 fixture。测试第二个文件仍是诊断变体。没有真实世界载入、无限代次、生产安装器或 Room Ready。

Title 三点观察不能与 Root return+yield同时容纳，当前不批准在 generic Root 下借用该布局；既有 Title 独立队列路径保留。未知嵌套、外部调试器、硬件状态漂移均不放宽。

最终命令与逐例结果由 `b_reload_nested_test.py` 的新运行记录、根公开证据和 docs/HANDOFF.md 给出。失败运行必须保留，不能拿改动前的源码哈希证明改动后结果。

## 已定位并修正的组合问题

第一轮三条完整 queue 组合在更早的 User 输入观察拒绝：该单点观察器也要求所有 DR 空闲。没有把 User 退回手工来源；新增同 ABI `b_reload_nested_input`，借用空闲 DR0，保留 Root return/yield。

第二轮真实 Root 入口之后，Windows 报告的 DR6/DR7 位值与 SetThreadContext 后返回的原始值不同；旧子观察器用整个数组逐字节比较，导致 Publish/Restore 拒绝。150519 诊断实际记录到 DR6 ffff0ff0→0、DR7 445→45（恢复时444→44），Set/Get均成功。四份新后继的验证改为Dr0–3全值、DR6 E00F事件位、DR7除固定bit10外全部位；硬件执行观察的事件与启用/类型/长度控制仍严格。报告继续保留原始值，不把它们改成看似逐字节相等。临时printf已移除，失败诊断日志保留。

## 最终离线验证

2026-10-08 最终运行：`b_reload_nested_runs/20261008-150658-885882/result.json`，**24/24 PASS**。137份源码和私有输入的运行前后身份不变，四份新生产对象在无fixture宏配置下编译通过。

三条完整 queue 组合（success、reuse-full-addresses、completion-wait）每条均有两代、16个真实 Root 任务、48次真实 Root 入口/返回/done 捕获，其中8个Load任务。原先组合里的手工 Root Capture 已移除；parent仍为18个scope、两个真实queue pop、2000次普通调度透明转发。User输入、Load start/join和Root事件在实际归档执行链上组合，所有观察scope收尾核验通过。

其余用例保留此前的Root正常/异常/停用/错身份/代码漂移/旧worker新current及Provider代次反例。新root-lease-refusals在真实Root任务内部检查错generation/provider/site、重复借用、伪serial、DR6事件位、异线程Release和过期租约不影响新租约。**这些lease反例中的寄存器数组是明确的契约测试数据**，不是实际第三方篡改硬件寄存器的动态实验证据；不能把24项都写成整条加载测试。

真实 yield/resume 分支、借用期间外部DR实际漂移、生产Root激活/安装以及真实两份游戏加载仍未测试。root return活动borrow的源码拒绝逻辑也不冒充已动态执行负例。

| 产物 | SHA-256 |
| --- | --- |
| result.json | `6575289644c38488d367041331faba970a7663222e378593f013b7000c3a6da6` |
| production Root ports | `6373644e836da753e7ea37aa67814a0386bf33da0be3f18c5b0358a670a5f787` |
| production Load start | `7657dad93324513d1cbf1e92151db07f960e85544f98cc4b5050fdecd961f801` |
| production completion | `042a8ad60cc5bc2c63d31410069685472627175ec661f74f2271c02de03864f4` |
| production User input | `cc89302d134777ac8c25ee3d5c96a4be43d77a209bb8e6ef6d88febb4ceb0d64` |
| fixture.exe | `bc3fccdb0d727d6571289e2b02ca9db6c3503bb73cfaa251d349f90397c9c1f3` |

失败历史全部保留：145635为20/23（User输入端口冲突）；150025、150207、150519均21/24（Set/Get规范化误判，后两次补诊断，其中150519留下确切原始寄存器对照）。最后通过结果不得覆盖这些失败。

复跑：

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机已有私有归档目录>'
py -3 work/mod_research/b_reload_nested_test.py
```

依赖Windows x64、VS2022 Community默认C++/MASM环境、前驱冻结模块以及原有固定哈希的私有归档。源码没有访问游戏/Steam/当前存档。没有遗留实机补丁或调试器，没有等待用户操作。不要把fixture启动方式改称为生产安装器。
