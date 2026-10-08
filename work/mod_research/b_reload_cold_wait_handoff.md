# B 冷等待协调：独立的注册前有界组件

2026-10-09。后继于 [冷启动审计](b_reload_cold_start_handoff.md)，不改冻结 `RegisterColdPool`、Bootstrap 或两代 Runtime。本轮只编译、运行自建 EXE 和线程，没有访问游戏、Steam、当前存档或 UI。没有待用户操作、游戏补丁或调试器。

## 已实现的窄链路

`b_reload_cold_wait::Coordinator::Run` 每实例只允许一次尝试，失败也消耗本实例。它接受可信本地宿主给出的四个 worker 对象、control、TID、预期线程起始地址，以及宿主的 producer SRW 锁和单调任务启动计数。没有 `ready=true` 入口，也不会重置旧模块 claim。

在截止时间内取得 SRW 排他，复制固定线程及事件句柄；核对本进程、实际 TID、`NtQueryInformationThread` 的启动地址、主 PE 的 MEM_IMAGE 与归档 ThreadEntry/Runner 字节。每轮重新核查对象/control/runner 字段、句柄原值及 `CompareObjectHandles` 对复制句柄的对象身份。三处 Enter/Leave/SetEvent IAT 必须是系统函数，四个槽必须是主 PE 的只读 MEM_IMAGE；Wait 服务入口必须可执行且本次保持固定。**这不是 Wait 服务行为的完整审计**。

每轮暂停四线程，读取真实 OS CONTEXT 并使用系统展开表。只有准确的 `83A9D7` 和对象/control 寄存器匹配才算初始等待；看到 runner 或初始等待之后的 ThreadEntry 为已暖，立即拒绝。只有已审 ThreadEntry 初始等待之前的栈链可以暂等；不认识的上下文立即拒绝。**尚未进入 ThreadEntry、仍在 CRT/线程包装入口的启动阶段尚未覆盖**，不能说所有冷启动时序已解决。

四线程的事件必须是未触发的自动复位事件。每轮检查任务启动计数；任何提前任务、对象/来源变化、已暖等待或未知上下文均终止。自己的每次 Suspend 增量都配对 Resume；发现原有挂起只撤回自己的增量，保持原来的挂起状态。所有线程恢复后，仍持 producer 排他，调用一次 continuation；该 continuation 以后应执行真正的生命周期检查和 `RegisterColdPool`。**目前 callback 只是自有诊断回调，旧 Runtime 尚未接入，未创建新的生产登记许可。**

SRW 必须由所有生产者在触碰 worker/event 之前共同遵守，任务计数必须在派发前增加且不回退。当前证明只覆盖自有测试宿主，不能排除游戏中未知生产者或绕过此锁的写入。组件没有替生产宿主证明这些前提，也没有提供对外可信票据。

截止是协作式轮询预算，不是硬实时终止：Windows 调度、系统调用和 continuation 可以超过预算；本轮40ms截止观察到46–47ms返回。continuation 自身必须有界。若 Resume 失败，报告 `uncertain` 且不继续 callback；这是未知状态，**不能当作已经干净恢复，也不能重试旧 claim**。本轮没有人为制造 OS Resume 失败。

## 实际测试与身份

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机已有私有归档目录>'
py -3 work/mod_research/b_reload_cold_wait_test.py
```

使用固定私有 `game-runtime-image.bin` SHA-256 `5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`；不会自动取得游戏数据。VS2022 x64 编译组件，无 fixture 宏。自有 host 是 MEM_IMAGE，静态 PE 展开表复用冻结 worker fixture；生成文件只修改构造替身的“主动等初始wait”为“恢复线程后直接返回”，没有改原归档 ThreadEntry 或 Runner。

四个真实 Windows 线程执行归档 ThreadEntry。延迟场景由另一个自有线程实际持 manager 临界区，再延时释放，协调器先读到前链上下文，后读到准确初始等待；不是用信号标记直接授予通过。构造、cookie、CRT结束及 Wait 服务仍为显式 fixture 服务；Wait 最终调用系统 `WaitForSingleObject`。六处实际系统临界区均在退出后检查平衡并删除。

最终：`b_reload_cold_wait_runs/20261009-005017-529022/result.json`，**12/12 PASS，inputs_unchanged=true**；固定6份来源、1份私有输入、5份生成文件和3份产物身份。

| 场景 | 实际结果 |
|---|---|
| 延迟到初始wait | 12轮，44次pending观察，48次Suspend/48次Resume，四个准确wait，callback一次 |
| 到期 | 4轮后拒绝，16/16配对，无callback |
| 线程起始来源错误 | 暂停前拒绝 |
| 已暖worker | 实际先执行一次普通原生任务，再拒绝runner等待，4/4配对 |
| 提前任务计数 | 暂停前拒绝 |
| 事件已触发 | 拒绝，4/4配对 |
| callback拒绝 | 四个准确wait之后调用一次，失败终态 |
| 原先已暂停 | 只撤回自己的1次增量；测试随后恢复外层原暂停 |
| 错control绑定 | 拒绝，4/4配对 |
| 未知上下文 | 自建真实线程的非ThreadEntry栈被拒绝，不当pending |
| producer锁被占用 | 有界拒绝，无线程暂停 |
| 期间替换event句柄字段 | 先实际pending，字段被测试helper替换后拒绝；48/48配对 |

各场景都再次调用同一 Coordinator，验证拒绝且第一次报告逐字节保持。每个场景四个原生 worker exit0，六把临界区平衡；辅助线程也正常退出。12个自有 EXE 正常退出，没有后台进程、worker 或调试器残留。正常退出不等于游戏全局已隔离。

Result SHA-256：`f0cecc2b7626050a6c39ebdc187c0b5c9562e2ad42cc9ce23286bc3d0a424cc6`。

另一agent已独立只读审查004644版本的上下文分类、线程/事件身份、挂起恢复及callback边界，无阻断；之后只去掉测试脚本多余末尾空行并重跑为005017。最终6份来源、3份产物与5份生成文件已重新核验；上述生产接线限制保留。

产物 SHA-256：

- `owned_cold_wait.exe`：`4d0c5b961142aa3116001dc9485631a18745d667747ebe377db5577a9394ba32`
- `cold_wait.obj`：`79c7f78d57f56c108337aaf51486bb4c9bf94294e6353dcf27dc5f414a290bc6`
- `unwind.obj`：`b53be897505bc8438cec2499f158ecb319cb19f7a3621224171c2f6254c211db`

保留全部中间运行。`004303-696586` 编译日志写入遇默认GBK编码异常，在用例开始前退出；改为UTF-8写日志。`004314-410676` 为11/11初版，`004439-697523` 为11/11句柄复核版，`004532-203106` 为12/12新句柄替换反例；它们不能替代最终新增IAT连续性验证的源码身份。`004644-119054`为新增IAT验证的12/12成功；之后提交前检查指出测试脚本多余EOF空行，005017只去除此空行后全量重跑12/12，并更新源码/产物pins。最终新源码未修改冻结前驱。

## 下一步接线条件

1. 在真实初始化生命周期内先验证原来的 owner/frame/pool/caller 身份，再调用协调器；四线程到齐后才在同一持续 producer 排他内调用一次原生产 `RegisterColdPool`，由原组件再次自行验证/发布。不在旧失败终态后重置重试。
2. 找到并证明真实生产者能共同遵守的暂停范围和任务计数来源。当前传入本地SRW/计数不是这种证明。
3. 决定线程尚在 CRT/包装入口时可接受的准确上下文范围；在没有证据前继续拒绝未知，而不是把任意地址放入pending。
4. 与同PE/Provider的两代queue后继实际组合，再处理合法存档、启动来源就绪、完整世界/输入和房间链路。本轮没有新增双机实测通过证据。
