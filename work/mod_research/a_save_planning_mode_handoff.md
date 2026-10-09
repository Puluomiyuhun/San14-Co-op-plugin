# A 规划模式 0 显式后继

2026-10-09。本模块只做离线源码/归档审查、生产编译和自有进程验证，没有访问游戏、Steam、UI、当前存档，没有向已失败模块重试。用户本轮实机由主 agent 独立操作；以下严格区分其已有记录和本模块测试。

## 实际问题与最小改动

实机 `a_save_runtime_live_runs/20261009-225620-723897` 首错为 Controller fresh Inspector：stage46、error0、StateTransition4、stack5/queue0、userPhase2、menu-1，gameTransition/loadQueued/advance/panelAdvance均0。记录 `a_save_initialize_trace_read_runs/20261009-225635-061434/result.json` SHA `a57535df718ce5f37fafec6c6200be1249d148bbdb0e5f64c179ee0bc139df06`。

装前capture的 `planning.expectedMode=0` 直接来自 `cache+8` 的u32读取，其余隐藏transition字段均为规划初值。主 agent 随后五次只读交叉采样，`cache+8`稳定0、user+660/user+68/Game+68/cache+3F0均0、cache+3EC为-1：同实机目录 `readonly-transition-225847-685382/result.json` SHA `ff9c64f067ab11c09f641065dcfcda391249c3ed394de382d8b8db9c05b08f54`。这些前后采样不是原失败瞬间的额外字段记录，不把它们冒充同一原子快照。

源码直接存在不一致：冻结 `a_save_scoped_input.cpp` 规划末尾硬要求 cache+8==1，否则返回StateTransition；而它的既有fixture明确写入1。现有B加载路径已支持其不可变配置中的实证模式0，A Save Driver也捕获并保持真实初始模式，并未要求只能1。因此不该靠向游戏写1来满足旧fixture假设。

新增 `a_save_planning_mode_input.cpp` **只有一处生产谓词变更**：由冻结scoped_input的唯一 `cache+8 != 1` 改成 `cache+8 != 0`，另加说明注释。每次构建逐字核对这一转换，拒绝锚点不唯一或生成文本漂移。当前版本只支持已观察到的规划模式0；模式1和任何未知模式仍被拒绝，不是“0或1都行”，也不是取消检查。

所有其它状态字段、五/六栈、队列身份、授权Load的mode0要求、Parent/Game原始来源/TLS凭证、任务状态、call/thread/depth与生命周期判断保持原样。没有新native写入、没有修改其它Owner/Gate/Driver/规则，也不替换全局输入隔离机制。原初始化首错记录继续链接。

## 构建和测试

入口 `python work/mod_research/a_save_planning_mode_test.py`。它基于已冻结初始化trace runner生成明确后继，分别编译完整无fixture宏生产DLL与已有宏边界的自有组合，实际替换Inspector链接单元；保留生成diff和命令。正常fixture在构造配置前设初始cache mode0。原生世界/业务/存储仍是明确替身；实际Parent、Controller、Claim、Inspector、Owner、Driver、IPC与收尾检查执行。

最终记录（仓库外）：

- `a_save_planning_mode_runs/20261009-230254-218464/result.json`，SHA `626abbe26375cf03c85507f918eae90a8e7e1a03757d64e3df015ae2de7c2683`。
- `candidate/result.json`，SHA `2669fa2e5c803ba123077a53ec070d5f3c91355e30baa7b91c5f8effee77c10a`。
- 内层112份来源、23份私有输入、13份生成文件、82份产物、17份日志/记录均复核相同；外层固定4来源与生成runner/diff/日志。
- 四项全部通过：mode0完整一次观察/Submit/Copy/释放；mode1、未知mode2、user+660非零分别拒绝，均保留原Config/ParentInitialize错误以及stage46/StateTransition，sample各一次、无保存提交或文件产物。
- 正常场景仍检查未claim current0、错误current、父原函数内部current0不能冒充Host boundary。
- 原ABI schema.exe和abi.exe对新生产DLL执行通过；旧启动器的源码、schema及唯一产物读取验证直接离线调用通过。所有自有子进程均退出，没有新增游戏钩子或调试器。

受pins来源已冻结：Input SHA `29468a1a709b818eebfe46f1f8bf0535e8d8c4d519fc19c7e2478d75e308f84f`；runner SHA `e28027f9ee1f65665b1ef519aea09b97d706aafa33eca73e6186cc488c442dc2`。

## 可供下一次独立实测的构建输入

兼容现有 `a_save_diagnostic_start.py --build-run` 的目录是上述最终run的 `candidate/launch`。其result SHA `34171de9d918bf0d00951692f8f5129b35adb3b3c3229e975bd9906723f30cb5`；唯一生产DLL SHA `ad0bf55dc8a4c8e542c6d3be211779fe84edda8557f744597a654e063c9ee922`。仍需独立fresh游戏生命周期、全新本机预检/claim及已批准publisher；本模块没有运行这个启动命令。

新DLL仍有144字节 `ASaveInitializeFirstFailure` DATA，可由 `a_save_initialize_trace_read.py --observe --run <新实际run>` 只读诊断。不能复用已失败PID/once/claim，不能用该离线PASS宣布真实A自动新档或两机通过。

## 保留的首轮失败

`20261009-230148-104553` 已保留。该轮mode0完整保存、mode1和mode2拒绝已通过；user+660反例在后续自有父原函数内的旧“只允许Pointer拒绝”测试断言失败。因为Inspector先检查user+660，合理结果应是更早StateTransition，而不是Pointer。后继仅调整这个生成fixture断言：必须已有stage46、实际user+660==1且Inspector返回StateTransition/error0才接受该提前拒绝；没有改生产检查，也没有把这个故障下的父原函数调用当可执行许可。第二轮四项和完整ABI全部通过。
