# A 更早 User 门禁后继：报告消费与保存 Owner 接通

2026-10-08。只编译、运行自有进程并读取固定私有 profile；未访问游戏进程、Steam、游戏 UI、游戏安装目录或当前存档目录。无待用户操作。本轮 fixture 全部退出，无本轮游戏补丁或调试器。冻结前驱未修改；本模块不自行提交 Git。

## 这次推进了什么

`a_save_early_gate` 明确替代 `a_save_action_gate`，仍由同一组件拥有两处补丁：原 Game panel `3F8606` 与提前后的 User `3F9BA8`。旧 User `3F9DAF` 保持原指令；不是在旧 gate 之上增加第三处补丁。

在同一个 A 保存代、实际 User claim、正确对象/世界/阶段与父作用域下，新的六字节补丁把 User `cmp [rsi+660],ebp` 替换为受校验的 call。held 路径选择原 `3FA09F` 收尾，覆盖报告 flush/clear、selection 和 action；普通路径真正执行原 compare 的语义并恢复其 flags，使紧接的原 `je` 保持原行为。User 入口与外层 Save Owner 原生返回、AFTER、FINALLY 来源没有被手写成功字段代替。

这是**原生局部门禁后继已接保存 Owner**，并非完整世界写入排他。原 Game/global UI 桥、panel 桥和保存代绑定检查继续使用；完整 User 函数体已变换，不能称未修改。

## 组成与替换关系

- 编译 `a_save_early_gate.cpp` **替代** `a_save_action_gate.cpp`；公开接口改用 `a_save_early_gate.h` 命名空间。
- 编译 `a_save_early_gate_bridge.asm` **替代** `a_save_action_gate_bridge.asm`；复用冻结 `a_save_action_gate_bridge.cpp/.h` 的固定桥 bank 和符号。不能同时链接两份 ASM/Owner。
- 编译 `a_save_early_gate_guard.cpp` **替代** `a_save_early_guard.cpp`；维持 `a_save_early_guard::Guard` ABI。
- 继续使用冻结 `a_save_report_owner.cpp`，它仍替代 `a_save_user_owner.cpp`；复用原 User/Save 桥、Driver、storage binding/gate/readback、输入检查器。
- `a_save_early_gate_test.py` 的 production lib 已包含以上实际替换组合，所有生产单元先在没有 fixture 宏时构建。

Guard 不能再盲目要求早切点维持原 cmp 字节。新的来源检查只允许原始19字节（尚未 Arm），或**本 gate 已发布的精确六字节补丁、原有13字节后缀、RX近跳板和固定桥目标**（已 Arm）。其余报告游标/队列来源指纹仍严格匹配。没有接受任意补丁后“归一化”的接口。

来源计划通过 Interlocked 发布后不可变，检查不取得 Gate 锁。原因是 User gate 已有 Gate → Save Owner Snapshot 顺序；report Guard 可在 Save Owner 持锁时调用，反向取得 Gate 锁会产生 ABBA。该只读 plan 证明代码归属，不证明安装时所有线程已排空或持续排他。

生产全函数来源摘要仍只还原本组件拥有的两处精确补丁。Stop 或故障不会擅自恢复竞争来源，不卸载桥；已经进入的保存仍按原 Owner 收尾。当前仍无生产安装器与持续运行总 Owner。

## 桥与异常验证

早切点原 EBP 为0，但桥不假设任意调用者 EBP：从固定 frame 中取回 caller EBP，在原 compare 语义中使用。普通路径保存 CMP flags 到恢复槽，不改变原 RAX 与其余寄存器/XMM；held 路径保留原 flags。桥保持原来的固定 RBP 和规范 Win64 epilogue，faultable compare 在 frame 仍有效时执行。

新增 CMP flags 的 `pushfq`/`pop [rsp+...]` 两个控制点也经 `RtlVirtualUnwind` 校验；原恢复区各字节、临时 flags push/pop 与 epilogue 各状态继续校验。测试在真正进入原生 User 后将自有 User 页改为 NOACCESS，让原 compare 发生真实 AV，异常经过桥和动态 snippet unwind，到达外层 User FINALLY：native_started=1、native_returned=0、abnormal=1、finally=1、active=0，没有伪造 AFTER。

与前驱一样，held 路径选择原返回位置，硬件 shadow stack/CET 开启时明确拒绝初始化；不关闭系统保护。该限制仍需生产适配。

## 25项自有进程结果

最终 `a_save_early_gate_runs/20261008-145742-459523/result.json`：**25/25 PASS**，源码与私有 profile 前后摘要一致，生产库构建成功。

- 同一 report-aware Owner 两个不同32字节诊断文件：binder 2次、queue 2次、真实存储 readback 4次；4次 User 原生返回、10次 Save 原生返回；早段抑制4次，报告 flush/selection/action doubles 均0。
- Submit 前或入口前报告待办仍按前驱拒绝；入口拒绝不制造 native return。随后明确 Stop、正常调用所产生的 return/flush 另计，不能把最终汇总当作被拒绝那次调用的结果。
- `late-flag`、`late-queue`、`consumed`、`local-aba-blocked`：待办在原生 User 内出现，新早切点保留待办，原生返回后 Owner 在 binder 前拒绝。旧本地“写入后被 User 清掉，前后采样均为空”路径不能再通过。
- `release-report`/`release-quiet`：真正的 compare flags 分别选择有报告/无报告路径；停止本门禁后原消费、selection 和 action 正常执行，没有强制丢弃待办。
- 保存中变化、storage append、copy前flag/cursor变化、并发Owner争用、不可读页、补丁/后缀漂移、未安装/只装一处均检查拒绝/撤权与收尾。
- `external-aba` **PASS表示成功复现剩余风险**：在覆盖分支之外，显式 producer/consumer double 写后清零且不改游标，Owner仍可能导出诊断文件。`early-bypass` 同样复现切点之前的写入double仍可发生并排入保存。这两项不是已解决排他的证明。

测试执行的原生19字节 report cmp/call/clear围绕明确的 report flush double；selection/action、Game/global UI/Save业务和存储方法均为自有替身。早段与原尾段构成一个实际可执行、正确登记动态 unwind 的自有 snippet。**不是完整归档 User 函数或真实 SAN 存档**；前轮完整原 prolog/epilogue 的归档模拟证据不能自动升级成本轮完整实机来源证明。

fixture 发布器仍只暂停、枚举、检查、恢复自有进程其他线程，实际写两处源并核对；不是任意游戏安装器。

运行记录全部保留：

1. `20261008-145546-950966` 首跑25/25；当时尚未单独验证新增CMP flags capture两控制点。
2. `20261008-145742-459523` 补齐这两点及旧切点未变、精确两补丁断言，25/25；没有失败或跳过。主 agent独立静态复核frame/flags/锁顺序，未发现阻塞。

最终摘要：

- 结果 SHA256：`a73793f118d1106d50f977a83b260877e296544415c867bc5b8e2517814e39ff`
- 生产 lib SHA256：`580664fd3ab628d6c3b44123e1b379782aa0cf962fb3b4dc4ed702043f23f681`
- fixture EXE SHA256：`5bfd0a02138c5d888e1284086b9a7af46ccb3e56911fa0052606d6d47e655169`

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机私有研究输入目录>'
py -3 work/mod_research/a_save_early_gate_test.py
```

需要 MSVC/MASM 与私有 `checkpoint_push_profile.h`；缺失明确失败，不读取当前游戏。原始日志、profile、构建产物留本地ignore，不提交。

## 尚缺与下一步

`fullInputHold / reportWriteExclusion / saveAuthorized / roomReady / production_permit` 始终 false。

当前切点仍在 `15FA20`、`16C5F0` 两 updater 之后；其非空路径、其他report生产者/消费者、消息/设备来源、后台写入者和对象生命周期尚未形成持续排他。这个较早切点解决了已知 User 下游消费旁路，不能把“测试期间没有新命令”替代可信写入边界。

下一步沿前轮 `a_save_report_boundary_handoff.md` 列出的 updater/生产者继续归因，或设计覆盖真实写入者与对象生命周期的持续 Owner；再接 IPC生产出口及两份真实新档。不要仅因这25项通过发放生产 permit、放行 Ready 或直接安排双机整旬测试。
