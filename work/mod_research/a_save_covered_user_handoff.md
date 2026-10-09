# A 已排队 Save 与 covered User 故障复现

2026-10-09。只用自己启动的 fixture；不访问游戏/Steam/UI/存档，不修改冻结生产源。此记录是缺陷复现，不是保存成功。修复后继另见 covered integration。

发现两个前驱 fixture 未模拟的时序：

1. Driver 在 User AFTER enqueue Save 后，manager 仍为五状态，待应用队列已有一条 Save。如果此时调度 Game，scoped Gate 的 n==5 路径调用 Inspector；后者拒绝待应用队列，Gate Input → Owner.Stop。
2. Save 在顶层期间，原生调度仍调用下面的 User。固定 SHA 归档 writer_scope_audit 已证明 User 入口 3F9B09→509640 判非顶层，3F9B10→3FA0AE 直接返回，不访问 3F9B16 userTail。但旧 Owner AFTER 对 slot0 仍调用要求五栈的 rp::observe，六栈下撤销报告资格；随后存储验证被拒绝，Driver error54。

第一项只是足以导致错误的具体调度反例，不是实机首次 Game 栈/队列时序已采到。实机 Gate Input6、Owner 初始 error0/stopped1、afterRejected25、storageRejected1 与之相符，但不能宣称唯一真实根因。

rp::fields 的 report flag/cursor/tree 无证据需要放宽。旧手动49保存 trace 仅两条 serializer enter/return，没有这些字段；不能笼统取消检查。

测试从冻结 a_save_scoped_input_test.py 生成后继，仍链接真实 Parent/Host、Controller、Inspector、Gate、Owner、Driver、Mailbox/IPC。真正 enqueue 后增加 Game 调用，明确 current=Game；在模型应用六栈之后每个 Save 阶段前增加一次 current=User 的 covered 调用，共5次。旧 ActionRawUser 从来没有 IsTop 检查，因此只对这5次通过明确空返回业务替身表示另已归档证明的早退；不声称完整原生 User。Owner AFTER/FINALLY 没有改动。

最终外部记录 a_save_covered_user_runs/20261009-124826-411727/result.json，SHA256 fe539280566e71674ee053348e09df435c0647b4c89d48faa1c08cee429f0ae5。

测试 PASS、应用 FAIL_REPRODUCED。实际日志精确为：

    gate=6 earlyOwner=0 stopped=1 covered=5 afterRejected=5
    storageRejected=1 status=7 error=54 lease=1 copies=0 releases=0

真实 IPC 收到失败后关闭、server/child join，不伪造 Copy/Complete/lease 释放。业务、原生调度与载荷仍为自有替身。该两个运行目录无存活自有 fixture 或调试器。

保留失败124740-160167：已通过 queue-window 精确错误断言，但旧循环在终态后又进入 Submitted，再次断言绑定失败。新生成器限制只模拟一次，不重试 consumed Save，最终通过。
