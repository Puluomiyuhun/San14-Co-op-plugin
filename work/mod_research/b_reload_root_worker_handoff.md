# B Root 工作线程的真实观察来源

2026-10-08。本轮只在自有进程执行已有私有归档，没有访问游戏、Steam、UI 或当前存档目录，无待用户操作、无新增游戏补丁或调试器。不是双游戏联机验证。

## 改了什么

新增 `b_reload_root_worker_ports`：在当前工作线程观察 Root entry `50B730`、return `834D9B`、done `834DB4`、yield `50B690`。实际 VEH 从操作系统 CONTEXT 取得寄存器，再提交 Provider；不在成功测试中人工填写 Root Capture。入口核对归档代码、可执行页、worker/callable/threadObject 链及代次。四个硬件观察位置必须空闲，恢复时核验包括 DR6 事件位在内的所有权，冲突保留为不确定状态，不覆盖其他观察器。

新增 `checkpoint_native_task_provider_worker.cpp` 是 bound Provider 的同 ABI 实现后继，构建时替换 `checkpoint_native_task_provider_bound.cpp`，不能同时链接。原 bound parent 接口保持 current 匹配规则；新 worker 伴随接口在同一 Provider 锁中核验 expected bank、attempt、epoch、窗口及允许点，查找仅限本代，但不要求它仍是 current。这样下一代已打开时，旧 worker 的真正返回/done 仍能归入旧任务。未匹配任务不再以 ignored=true 冒充成功；embedded Title 不能借用 generic Root 身份。

观察器 `Context` 一次使用、驻留至进程退出，最多64个；Provider 原有两代等限制没有取消。`Stop` 是停止接受观察，不是暂停原生引擎。PE bridge 的 FINALLY 负责恢复调试寄存器；仍 active 的 Provider scope 通过 Abnormal 收尾。helper 超时后仍需等待排空，不能据此保证有界延迟。没有生产安装器或持续调度排他。

## 验证范围

最终运行 `b_reload_root_worker_runs/20261008-143326-676396/result.json`：**23/23**，输入前后摘要一致；两个新 C++ 实现也以无 fixture 宏配置编译通过。精确源码、结果和产物摘要见[公开证据](../../docs/evidence/2026-10-08-root-worker-sources.json)。

- 16项前驱回归：3个实际归档 queue/两代 Title 组合、12个直接 Provider 检查、1个实际 parent 中途切代。该组仍沿用明确的 Root fixture，不能说整条加载链已换成新来源。
- 7项独立 Root：正常任务、同代两个连续任务、原生调用中的异常展开、启动前停止、错误绑定、代码漂移、旧 worker 在新 current 打开后收尾。真实父调度在另一线程运行；真实 `834D10` runner 调用归档 `50B730` thunk，业务 Update 是明确替身。
- 正常任务实际捕获 entry/return/done 三点，连同 parent fresh/create/complete 共6事件；连续两个任务共12事件。跨代旧 worker 共5事件，新代0事件，旧 parent completion 因 current 已变化拒绝。异常任务只捕获 entry，FINALLY 恢复6个 DR 并废止 active scope；不伪造 return/done。三项提前拒绝不运行 worker body，capture 为0。

本测试注册 runner/thunk 的实际 Windows unwind 描述，经实际异常展开和 PE FINALLY 验证。新 Root 组合由 fixture 直接配置和调用 bridge；不是发现并替换真实游戏线程入口。构造器、分配器、事件服务和业务 Update 仍有替身。两个连续任务不等于两份真实存档，也不等于连续两旬。

首轮 `20261008-142656-952527` 为19/23：四个负例沿用“worker 必须被正常完成清零”的旧 fixture 断言，但本例以 yielded 状态释放等待，正确原生行为是保留未完成 worker。只在后继生成器中区分未完成/完成断言，保留前驱不改，不清零 worker、不补完成回执。随后补指令缓存刷新、按实际 capture 数报告来源、冻结恢复检查源码再完整重跑。失败记录保留。

## 下一个必须解决的问题

Root 观察器从 runner 入口持续占用线程的4个硬件观察位置，而嵌套 Load.Update 内的原生 Start/completion 观察器也需要4个空闲位置。**当前两者尚不能组合。** 不能删除 Occupied 检查，也不能在整个 Update 期间关掉 Root 后仍声称记录了 yield。应设计同一所有者的嵌套观察位置交接或其他真实来源，证明异常、恢复冲突、晚回调和每个嵌套区间的覆盖，再替换原16项组合中的 Root fixture。

`50B690` 已列为观察点，但本轮没有实际执行 yield/resume；旧 Provider 的直接 yield/resume 检查不能替代归档机器码该分支。真实路径会进入时，需补实际分支验证。Finalize/Title 的其余来源仍未全部采用 expected 接口。

随后才是生产入口安装、统一 native owner 持续排他、旧规则撤下/新规则安装、两份合法新档连续加载、世界/身份/菜单/地图恢复及 Ready。A 保存排他和远端配置也仍未完成；完整首测清单见[双机门槛](../../docs/FIRST_TWO_PC_TEST.md)。

## 复跑

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机私有研究输入目录>'
py -3 work/mod_research/b_reload_root_worker_test.py
```

需要 Windows x64、VS2022 Community 默认 C++/MASM 工具链及前驱私有输入：固定历史输入档、`game-runtime-image.bin` 和 completion profile。缺失或摘要变化立即拒绝；生成的完整机器码 profile、二进制与日志不提交。第二份文件仍为前驱诊断变体，绝非合法 SAN 新档。公开仓库包含复跑源码，但不包含这些私有运行资料。
