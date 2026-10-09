# Pending User：精确自有 Save 队列后继

2026-10-09。离线读取冻结源、固定归档并运行自有进程，没有访问游戏、Steam、UI 或当前存档。旧 covered Owner、Gate 与测试保持不变。

## 缺口与许可边界

五态栈且唯一待 push Save 时，Game 已有自有队列许可，但旧 User Entry 仍走要求 queue0 的规划观察，因而先抑制原 User、撤销报告授权。新增 a_save_pending_user_owner.cpp 是 covered Owner 的同 ABI 实现后继，不能同时链接前驱。独立 marker7 仅许可当前 checkpoint generation 对应的真实 Driver Queued、binds1/queues1、原五态身份、当前 User、唯一 type0 队列项指向该 Save、原 CSaveState 身份及 phase0。保留 caller、源字节、pinned report 字段、线程/物理 Owner claim 和真实 Before/After/Finally。没有把所有 pending 队列视为规划期。

原生 scheduler 确有暂缓 apply 的路径：50A7A6 调 state vtable+30，50A7AB 非零跳50B41B，绕过50A7BA起的 apply，接50B441 Update walk。任务结束50B63B/63F仅在队列数改变时终止遍历。故 pending User 有具体 CFG 前提，并非凭空安排；本轮未枚举各虚调用业务条件，也未证明先前实机正好命中该分支。归档 game-runtime-image.bin SHA256 5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268。

## 执行证据

私有证据目录均在仓库外 work/mod_research/a_save_pending_user_runs。

- 135057-113039：生成脚本首次绝对路径替换误改内层字符串，SyntaxError；保留失败。没有编译或启动自有目标。
- 20261009-135259-190602：冻结 covered Owner 加真实 pending User 回调，PASS / FAIL_REPRODUCED。实际 value1、stopped1、Owner Input11、entrySuppressed1、revoked1；并非只检查返回 boolean。result SHA256 8a2925e1a9049d13a763f18adbdf16f8049773e54245a5c053f6b55ce20430dd。
- 20261009-135331-717748：新 Owner 6/6 PASS。normal 依次 queued Game、pending User、五次 covered User、五段 Save、返回规划、真实文件核验/IPC Copy1/lease release1。pending User selected/claimed/returned/finally 各1，拒绝0。foreign/multi/wrong-generation仍被 Gate 拒绝；cursor-drift与user-foreign仍无 artifact，Driver Uncertain54/lease保留，不伪造清理。result SHA256 c5fb6db57b7ac02241cf6b85eb4d9d5106d92e6b65ee9a9e89379b57decabbbb。

最终83份 source、42份二进制/对象、6份生成文件均按结果再次核验，全部当前匹配；sources_unchanged/private_inputs_unchanged 为真。四个新增源码/测试文件均通过 EOF/尾空白检查。三个已知运行目录均无存活自有 fixture 进程。

生产 Owner SHA256 87300130d8dc4ce02e70b4b8959e5cd947af89c440f25d1586b969b5ddd29af2；header b4205b359a66de84e804f81b8ff1d6e4f3d1e11e68220a4bec1a3db26e586c83；fixture 047a161fc1c31a729ec77181761f6e9e352207f5236ba14d8a4acb329dd6b4b2；test 0830c9902a8687a1a357f40b35ffbeb9e5880ee01b758f02c982842291fe3f06。

## 生成与未证明范围

测试继承 covered integration 的 scoped Host 组合，明确替换 Owner TU、fixture helper，并给自有 fixture TU 增加 A_SAVE_PENDING_USER_SUCCESS。正常返回仍使用原 scoped fixture 的原生业务替身；不是完整游戏 scheduler/save serializer 执行，也不是生产整个 DLL 无 fixture 宏。实际 ParentAdapter、Host、Controller、Gate、Owner、Driver、mailbox 与 IPC 链仍执行；生产源校验的 fixture 分支沿用前驱限制。

这仍是一代保存窗口，不是连续跨旬或双客户端实测。原虚拟+30条件是否在目标现场发生，以及真实游戏新进程的完整保存、七来源撤回仍由下一轮实机证明。异常后的自有数据恢复只服务负例收尾，不构成真实 abort 功能。A agent 将以新的 combined Owner 明确合并独立 abort 差异；本文件与本次实现均已冻结。
