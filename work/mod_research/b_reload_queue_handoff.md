# B 队列 Finalize 后继交接

2026-10-08。本轮新增 `b_reload_queue_parent_source`、`b_reload_queue_finalize_ports`、`b_reload_queue_finalize_source` 及对应 fixture/test。它们分别替代上一轮 parent source、旧 Finalize ports/source；复用既有 PE 桥、Provider 和 Title +520/+590 组件，不与前驱所有者叠装，也没有修改冻结前驱来复用旧摘要。

本轮只运行私有归档和自有测试进程，没有操作游戏、Steam、UI 或实机补丁，没有待用户操作请求。**生产安装器、真实游戏加载、完整世界核验和 Room Ready 均未完成。** 本文追加核对只读取结果、源码和产物，未另行启动 fixture。

## 这次实际接上的调用

旧 `b_reload_parent` 已证明调度器收尾会把 manager 当前对象清零，但旧 Finalize candidate 要求该字段等于 Load，组合测试只能人工设置当前对象后调用 Finalize。这次生成的 fixture 删除了这个人工 Finalize 调用和相应字段伪装。

新 fixture 向自有队列放入一条 **type 1 pop** 条目，然后从实际 `13DC09 → 509FE0` 调度入口运行归档机器码。调度器解析、复制并清理该队列，经 Load 的 `vtable+0x10` 调用 Finalize，弹出 Load，再进入后段 worker 循环。此次实际命中的 Finalize 返回地址是 `50B1B8`，进入时 **manager+0x48 为零**；正式栈在调用前有四项，调用后留下 Title 等三项。Exit/status/分配器是明确的自有业务服务，不能把这些替身的返回值算成整个游戏业务已执行。

`b_reload_queue_finalize_ports` 核对当前线程的父调度 queue 作用域、不可变 generation/attempt/epoch、Provider 对象、实际 caller、Load/closure/Title 身份及已完成的 Load worker join。它在真正的 Finalize 中观察 Title callback 和 +520 启动，随后复用 +590、三个 join、Session 及 planning 检查。源码还接受另三个已定位的 Finalize caller：`50AA56`、`50AD45`、`50B002`；**本轮没有动态覆盖这三个调用分支**。

父来源在 queue 阶段不占硬件断点；实际 F570 返回后才安装 worker 阶段的四个观察点。Finalize 的两个观察点在其 FINALLY 中恢复，随后父调度才使用自己的观察点，没有依靠同时占用超过四个 DR 槽通过测试。

## 加载窗口与仍未修复的代际竞争

新 parent source 提供 `RegisterWindow`、`BeginWindow`、`EndWindow`，最多记录两个不可重开的窗口。窗口身份从已经登记的 Provider generation/attempt/epoch 核对后固定；进入父作用域时复制该身份，退出不使用“最近一个窗口”替代它。Begin/End 要求没有活动父作用域，正常 End 要求 Provider 已闭合；错误/Stop 的退休条件独立保留，不能据此宣称正常完成。

没有已选择窗口的普通调度只转发、不分配加载 scope。本轮实际执行 **2,000 次**这类空闲调度，未消耗加载 scope，修掉了上一版普通空闲帧也一直占用 128 槽的问题。**窗口内部仍共用最多 128 个、成功后不复用的 scope 存储，且 Provider 仍只有两个常驻 bank；这不是无限旬常驻实现。**

另有本轮独立静态审阅发现、尚未修复的来源缺口：

- 冻结 `checkpoint_native_task_provider::Provider::OpenWindow` 设置指定 bank 的 `windowOpen` 和私有 `current_`，不会关闭另一个仍打开的 bank。
- `Provider::Snapshot(generation)` 只返回该代的记录，没有公开当前所选 bank、所有 bank 枚举或按 expected generation 原子提交 Capture 的接口。
- `Provider::body` 处理父 fresh 点 `50B4B3` 时，以 `current_` 选择起始 bank。新 parent 的 `providerBinding` 只核对指定代的 Snapshot。若外部在旧父作用域期间提前 `OpenWindow` 新 bank，旧 Snapshot 仍可显示 open，后续 fresh 却可能进入新 bank。相同 base/历史地址复用尤其不能作为代际证明。
- 因此 **Snapshot 校验不证明实际观察仍使用同一个 `current_`**。当前代码没有阻止外部 OpenWindow 抢占；本轮三个顺序用例未制造此竞争，也没有给它增加假通过用例。只检查“其他已登记窗口没有打开”至多是保守拒绝：未登记的 Provider bank 和检查到 Observe 之间的竞争仍未排除。

不能将窗口 API 的存在写成完整的 Provider 代际隔离或调度排他已实现。下一步需要明确后继，在同一个 Provider 锁内核对 expected generation/attempt/epoch 并处理 Capture，或由统一可信 owner 独占所有 Register/OpenWindow 操作、跨整个父作用域持有实际排他。后者必须真正接线并覆盖所有调用方，不能用一个布尔标志替代。不要原地修改冻结 Provider 或读取其私有内存布局绕过接口。

## 本轮验证结果

最终运行：`b_reload_queue_runs/20261008-114242-205322/result.json`，schema 为 `san14.b-reload-queue-owned.v1`，**3/3 PASS**，三个进程均 exit 0：

| 用例 | 本轮覆盖 |
| --- | --- |
| `success` | 同一自有进程顺序完成两个加载观察代际，实际 queue pop/Finalize 与两 Title 角色组合 |
| `reuse-full-addresses` | 第二代复用全部历史地址，仍按既定顺序完成两个窗口 |
| `completion-wait` | Title 等待分支，再完成第二代；第一代 completion scopes 为 4，普通情况为 3 |

每个用例记录两个 queue run、两次实际 pop、8 次 current=0 检查；18 个父 scope 全部恢复，16 次 fresh/create/complete、8 次 yielded skip，parent error 为零；两个窗口退休，空闲转发 2,000 次。每代实际观察 Load worker、Title +520/+590 的来源和三个 join，Provider 正常闭合。尾部沿用前驱的 `generations: 3` 计数包含初始代；**本轮真正执行的是两个加载观察代际，编号 2 和 3，不是三次加载**。

测试生成了两个不同字节输入。第一份是已有私有档副本；第二份由测试修改一个字节并追加 128 字节，仅是诊断数据，**不是新生成的合法 SAN 存档，也不是两份真实游戏文件连续读档验证**。root worker entry/return/done/yield、构造器、文件处理及部分引擎业务仍由明确替身提供。`50B4AE` 的真实 resume 分支依然没有动态覆盖；本轮移除的是人工 Finalize 调用，不是所有人工来源。

以下结论仍为 false：`production_installer`、`real_game_reload`、`full_world`、`room_ready`、`native_scheduler_fence`。局部 `identity_ready`、`planning observed` 或两个文件校验成功不得扩大成完整世界一致、持续输入排他或可继续游戏的许可。错误/Stop 与上层 Room 撤权的生产组合仍需接入。

旧 `b_reload_parent` 的 **8 项**负例属于前驱证据，不计入本轮，也不宣称已经在 queue 后继重跑。新 queue 的 Stop、异常、代码/补丁漂移及外部 OpenWindow 竞争负例仍需逐项验证。helper 超时后仍会等待自身线程退出，不具备有界退出时间保证；驻留桥、模块和不确定状态不能强行卸载或重置。

前一次 `b_reload_queue_runs/20261008-113937-009657` 在 `/WX` 编译阶段失败：fixture 局部 `pending` 遮蔽已有全局变量，C4459 被当成错误，**没有 result.json，也没有该次运行通过证据**。后继只把该 fixture 局部变量改名为 `queueEntry` 后重新构建；失败目录保留。

## 摘要复核与复跑

独立核对最终结果记录的 **126 个源码文件**、3 个私有输入、3 个 production object 及 fixture.exe：当前字节全部与结果摘要一致，未发现漂移；`inputs_unchanged=true`。三个新 C++ 单元均在无 fixture 宏的 production 配置编译通过，生成的 fixture 使用显式 fixture 配置。

| 项目 | SHA256 |
| --- | --- |
| result.json | `36efe604418692835daaf339c6f45e28542fd55a925cc9218bc770f8a93212f6` |
| fixture.exe | `a9f28335b72b87b3be87c86e1642700fbd02fef95a24379147477261655193ba` |
| production parent source | `c945e39ab452bc28c29d3db8d3fcfd913fc40369998564c36f1a1d0b0e209e2b` |
| production Finalize ports | `771bb3ab889f442e07f04e24ec3afb5fc857baf0090bd6a7274fce4e87bf9e8c` |
| production Finalize source | `f3da5d2e101db96ce1267ca66eae9c1a2f4b79baeaa2fffefee4586895da36fa` |
| parent source.cpp | `5461e6bab5bff5b614106ce9daea81184597c52651c24df0dfe0167822391ad7` |
| Finalize ports.cpp | `4c479b43fd84e486813f8d2fb3f858b0b98523d2f100c729ffd1441d0397deba` |
| Finalize source.cpp | `46ef6cddd0c77724cc4dc7acb4e81ba3ecb1eaeaa3628d89e9bbccc1a124e52b` |
| queue test.py | `5142f130c1aa9a109052d9dd0e97a03c4b7134473cb2ef7a6dd6503fa305ae47` |

在仓库根目录执行：

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\san14-private\mod_research'
py -3 work/mod_research/b_reload_queue_test.py
```

先核对脚本与本机输入；该命令构建并运行自有进程，不是游戏安装入口。需要 Windows x64、Python、Visual Studio 2022 Community C++/MASM（脚本当前使用默认 `vcvars64.bat` 路径）、仓库内前驱源码，以及下列私有输入。完整归档函数 profile 由测试生成到忽略目录，不公开分发；缺少或不匹配时停止，不能补零或放宽摘要。

| 私有输入，相对环境变量目录 | SHA256 |
| --- | --- |
| `game-runtime-image.bin` | `5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268` |
| `checkpoint_push_archives/20261006-204306-581930/mppush01.s14` | `88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c` |
| `checkpoint_task_completion_profile.h` | `b63ec279e34ea7f35c2345428572e9aaff7d4689c69b31c989b74a935f97292a` |

接手顺序：先解决 expected-generation 原子观察/统一 owner 排他并加入竞争反例，再补真实 root worker 来源与新 queue 失败分支。之后才组合生产发布/恢复器、规则跨 world 撤回和重新安装、B 本机身份/输入排他、文件与世界加载完成回执。仅此三项离线通过不安排实机操作，也不放行远端双人整旬测试。
