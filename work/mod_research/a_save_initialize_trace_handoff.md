# A 初始化首错记录后继

2026-10-09。仅离线开发和自有进程验证；没有访问游戏、Steam、UI 或当前存档。此改动增加证据，不修复尚未定位的初始化拒绝，也不构成新实机通过。

## 为什么新增

真实运行 `a_save_runtime_live_runs/20261009-222056-638412` 停在父 Host 初始化、尚未提交保存。后续 RPM 证明 Controller.error=Config、initialized=0，缓存 clean 各项正常，但旧 DLL 没有记录 `read()` 最后即时槽读取与 `ClaimController/fresh()` 哪一项失败。不能从事后 clean 值推断首次失败原因。

## 实际链接变化

`a_save_initialize_trace_generate.py` 对冻结 `planning_checkpoint_save_interlock.cpp`、`planning_checkpoint_save_lifecycle.inc`、`a_save_abort_pending_owner.cpp` 做逐锚点、唯一命中转换。提交的三个显式后继每次构建先和转换结果逐字相等核对。旧文件未改。

- Controller 保持 read → clean → Claim 原短路顺序；原谓词只求值一次，失败仍走原错误码。
- Owner 只改变 lifecycle include；Claim 保持原 Owner 控制锁和 quiet → retired → binding → date → fresh → controller → thread/date 顺序。
- fresh 保留一次原 sample、原绑定/身份检查、实际 Adapter.Bind/InspectCurrent；生产 reward 函数来源判断仍生效。
- Begin 在 Initialize 原 `__try` 内；finally 按进入标志 End，始终释放原锁。没有诊断锁、业务调用、重复采样、重试或新许可。
- 仅 Initialize 动态作用域记录，记录本模块生命周期遇到的第一个初始化失败；不声称仅记录第一次 Initialize 调用。Request/Retire 等调用不会另开记录范围。

`ASaveInitializeFirstFailure` 是 DATA 导出，144 字节、version1、8字节对齐。内部 CAS 争抢一次发布权，填 payload 后通过 Interlocked 最后发布 offset140 的 stage。没有 reset 导出。stage0 只表示尚未发布失败，不能证明 readiness。

主要阶段：1初始化配置、2clean、3Claim未留下更内层记录的兜底；10 Owner/Gate匹配、11 CurrentController、12日期漂移、13日期读取异常、14 reward snapshot、15 hook集合、16 hook元数据、17即时槽值、18槽读取异常；30 Claim基本身份、31quiet、32retired、33binding、34date、35已claim、36thread/date；40缺sample、41fresh日期、42sample拒绝、43采样身份不符、44reward来源、45Adapter.Bind、46Inspector结果、47fresh异常。4是最终日期捕获异常。此编号不改变任何旧业务 Error 枚举。

Record 的 pid/thread/controller/owner/base/root/world 绑定本次初始化；a/b/c 记录该阶段已读标量。stage17 保存 slot/actual/expected；stage45保存Bind错误；stage46同时复制本次 Inspector Report 的 error/decision/stage、stack/queue count、menu、userPhase/gameTransition/loadQueued/advance/panelAdvance，不额外读取游戏。详细 ABI 见新头文件，size144、stage140 编译期断言。

## 验证与候选包装

最终执行记录位于仓库外 `a_save_initialize_trace_runs/20261009-224411-509053/result.json`，SHA `2de52a527763f354ee7b4905b838ad7eb70b7d0dbe8fee3b43d3b4c5b608ecc0`。110份来源、23份私有输入、13份生成源码/命令、82份二进制/对象、21份日志/原始记录/包装JSON逐项复核相同。运行命令是 `python work/mod_research/a_save_initialize_trace_test.py`；该脚本仅编译及启动其新建的自有测试程序。

六个独立进程场景：正常实际 Parent/Controller/Owner/Inspector/Driver/IPC/Copy 链；即时槽漂移17（sample未调用）；采样拒绝42、采样身份错43、Bind拒绝45、Inspector拒绝46（sample各一次）。每个故障保持父Initialize拒绝、Controller原Config错误，记录固定初始化身份，故障后尝试其它诊断写入不能覆盖首错；每个落原始144字节 trace.bin。正常链实际一次观察/提交/复制/释放，初始化不发布失败。

自有 fixture 的世界、原生业务、存储及父入口来源仍是前驱明确替身；这不是实机失败复现，也不证明真正失败属于这五个故障之一。Owner/Gate/Driver/存储绑定 fixture 编译宏继承旧组合，Controller、Claim、Inspector及trace实际谓词仍执行。另完整生产DLL独立关闭所有fixture宏编译，新增DATA通过dumpbin导出校验。

实际冻结 ABI schema.exe 与 abi.exe 重新编译并对本次新生产DLL执行。`launch/` 包装仅放唯一新DLL、依赖DLL、schema.json及兼容result.json；原 `a_save_diagnostic_start.py` 的 verify_sources、validate_schema、verified_artifact 在离线测试中直接调用通过。该目录是以后新生命周期 `--build-run` 参数的构建输入，不是本轮执行授权。普通typed ABI未改。启动器本身仍只自动读取旧Gate首错；新增初始化记录应由根的新 RPM-only `a_save_initialize_trace_read.py --observe --run <新实际运行目录>` 获取，默认help，不调用目标导出、不创建claim。

最终DLL SHA `8a69512acc0bfc8f8691166d5264ab7dd64e8d1b04bcc504a36f5d0be955c9ef`，`launch/result.json` SHA `44cccd825784a4f238d7d67876d4c4ced45fdbc6753464c73ac615d6233096eb`。新reader独立10/10通过：`a_save_initialize_trace_read_test_runs/20261009-224735-598004/result.json` SHA `63a4ab94b0db9140a15e4573fbe5b62d45930985ce51ca14aa5e4b6c405b65a6`。它用上述最终Inspect真实DATA记录与新DLL跨语言核实144字节布局、stage46/errorPointer7/decision0/phase2/stack5/menu-1，验证未发布/半发布/身份不符拒绝，以及超出DWORD范围的PID在打开进程前拒绝；进程读取接口在该测试中为明确替身，没有访问游戏。所有本轮自有fixture/ABI子进程已返回退出，没有遗留调试器或发布器。

## 证据来源和保留失败

实际组合继承固定 `a_save_abort_pending_runs/20261009-135450-754156/case/result.json`（SHA9eae1e…7cda）及其已哈希生成fixture/Build.cmd。生产继承 `a_save_abort_pending_runtime_runs/20261009-135510-973447/abi/production/result.json`（SHAddf4c7…f64f）命令。所有实际复用生成include、schema/ABI命令、依赖DLL/lib均在使用前逐项核对并固定。源和产物全量哈希在新result。

唯一排除的旧来源项是没有执行的 `a_save_abort_pending_test.py`：旧记录29f19f…9463、当前602ba1…262b。它是历史生成器而非本轮编译输入；本轮直接使用旧已固定生成fixture，明确记录漂移，不跳过任何native源码不符。

失败目录全部保留：223652因上述旧生成器pin不同而在编译前拒绝；223804生产编译成功，但owned链接遗漏trace.obj；223911正常链成功后runner组装重复case键失败；224011正常通过、slot故障注入直接写自有只读页退出，随后仅将fixture注入改为临时VirtualProtect并恢复页属性。224127六例和生产通过，224317增加兼容ABI包装通过；最终224411只补齐Python验收依赖来源pin重跑。没有对失败游戏模块重试，没有删除claim。

首错只能解释未来该后继模块实际初始化时捕获的失败。没有修复或重放当前失败实例；已请用户正常退出，尚待确认；本轮不再实测。完整输入暂停、A自动新档、两机联机仍须各自真实证据。
