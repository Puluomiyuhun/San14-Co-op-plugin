# A Save 排队、覆盖态与返回规划的组合修复

2026-10-09。本轮是明确的新 Gate/Owner 后继，不修改冻结 scoped Gate、planning Owner 或已失败真实进程。全部组合测试只运行自有进程；真实执行另由主线程记录。

## 已复现的旧缺陷

见 a_save_covered_user_handoff.md。旧组合跳过了 enqueue 后五栈且 queue1 的 Game 窗口，以及六栈期间的 covered User 回调。新基线实跑重现 Gate Input→Owner.Stop→报告撤权→Storage拒绝→Driver54；这证明一种足以失败的路径，不证明实际游戏第一次错误的全部调度顺序已抓到。

## Gate 后继

a_save_covered_gate.cpp 从冻结 a_save_scoped_gate.cpp 显式复制。普通规划仍执行真实 Inspector，仍要求 QuiescentObserved。只有 Inspector 已检查其他字段并返回 UnownedStateQueue，且 count1、stack5 时，才额外判定是否本次保存：

- 原 checkpointReserved、Controller 和非零保留 generation 已存在。
- 真实 Save Owner 没有停止/错误，saveLane 为真、无活动 scope，Driver 状态 Queued，generation 相同、binds/queues各1。
- 队列唯一 type0 对象必须等于真实 Driver.save_state；对象为原 CSaveState、phase0。
- 原五态身份、root/world、来源字节及 Game caller/TID 不变，已 claim 的实际 Game bridge owner 代号/深度/call_id 均匹配，manager.current 为 Game。

此分支只维持本次 Game UI/panel 的已有局部限制，不授权导出，不修改 Inspector、manager、队列或任何游戏字段；其他队列及 modal 仍失败。六栈分支保留原规则。

ASaveCoveredGateFirstFailure 是本 DLL 的固定结构 DATA 导出，仅记录第一条 Game-before 失败。size/version 后含 stackCount、queueCount、current、top、saveState、saveGeneration、reservedGeneration、saveStatus/stopped/error/thread。stage 由 MemoryBarrier + InterlockedExchange 最后发布：1 frame/caller，2 source，3 claim，4 layout。全局 alignas(8)，stage偏移有4字节对齐静态断言；外部按相同非零 stage 前后双读可核稳定数据。无 reset API，后续错误不覆盖第一条。

生产 Gate cpp SHA256：729792f89b9831a4faff0e39250ddf96877a5acd55564729c17943501a7b8a8f。

Gate h SHA256：33ac3554a4995797816c3e330627f39a802515b6749b63135cf191d5372e3019。

## Owner 与 fixture

Owner 由另一 agent 实现 a_save_covered_owner.cpp/.h：六栈且精确本次 Save 覆盖 User 时使用独立标记6，保留真实 Driver Before claim、source/字段 pin、After/FINALLY；普通五栈检查不变。生产明确核验 IsTop、singleton 和暖初始化来源及正常 covered 返回 RAX=0。实现细节见 Owner handoff。

测试仅替换原组合中的 Gate/Owner TU；Parent、Host、Controller、Mailbox、IPC、Driver 仍实际执行。新增 fixture ASM 是 a_save_upstream_fixture.asm 的显式后继，只给 covered 模型增加零 RAX 返回。旧 fixture 从不模拟原生 IsTop，而是直接进入下游 snippet，所以这5次将 snippet 指向空返回业务替身，并使用独立标志让 ASM 返回0；正常调用仍原 fixture 常量返回。另已归档验证的真实 User 早退不是本测试重复执行原游戏全函数。

wrong-generation 负例仅在 A_SAVE_ACTION_FIXTURE 编译中令比较用的预期保留代号加1，验证真实代号不匹配被拒；生产该变量及分支不存在。foreign/multi 负例修改自有队列，再在已终止 Gate 后恢复自有数据，仅让已绑定 Save 继续正常排空；不重试 Gate，不说明真实运行有 abort 恢复能力。

## 最终结果

外部 a_save_covered_integration_runs/20261009-125734-923360/result.json。

SHA256：32bdc51feaf2b8e14692bc2e66815fd6a3ca3f959d7f4b42cba91ff7a7602dd2。

81 来源、42 二进制/对象、6 生成物当前哈希全部匹配，sources_unchanged 为 true。Owner cpp 为38882de5bdab99b07e3adce5baa9ef4aa2b57624adc82b32b17a2f8cfd3e69e0。/W4 /WX 完整编译及实际执行通过。

5/5：

- normal：唯一已排队 Save 的 Game窗口通过；五次 covered User 的 selected/claimed/returned/finally均5、rejected0；5阶段Save后返回规划，真实Driver Complete、IPC Copy1、Host release1。
- foreign：非type0仍Gate Input，FirstFailure.stage4；已绑定工作排空，邮箱Unknown且Copy0。
- multi：多条队列同样拒绝，stage4、Unknown、Copy0。
- wrong-generation：保留代号故障注入同样拒绝，stage4、Unknown、Copy0。
- cursor-drift：保存对象正确但报告游标变化仍撤权，Driver Uncertain54、无核验产物、Copy0/release0、lease保留；父回调保持配对，明确 Host 错误允许被记录，未伪装成功。

所有这些已知运行目录无存活的自有 fixture 进程，没有调试器。原负例和编译错误未删除：

- 125239：fixture LONG 位于 Windows 头之前，编译失败。
- 125313：正常通过；三拒绝例因 harness 错误要求保留lease而失败，新Owner实际上已正确允许原生排空。
- 125419：正常与三拒绝例通过；cursor首次被正确抑制，普通返回模式断言不适用。
- 125518：Owner生产来源/零返回条件收紧期间的旧fixture运行，保留。
- 125640：正常与三拒绝例通过；cursor导致真实Parent Host错误，旧断言只允许无错误而退出。
- 125734：最终在精确相应状态断言下5/5通过，未放宽生产 Guard。

## 仍未证明

这里只是一周期自有业务模型，未执行真实序列化、真实游戏 scheduler 或两个游戏。没有新增全writer锁、完整输入暂停、连续跨旬或合法双人许可。真实故障进程仍不能凭此新源码卸载旧DLL或重置旧claim；需正常退出并建立新身份后才可另做实际测试。第一失败快照将帮助确认下一次真实 Game 到底在哪个阶段拒绝。
