# Repeat Runtime 的发布器恢复门槛

2026-10-09。显式后继于冻结 `a_save_abort_publish.cpp`。本轮仅自有目标进程/DLL与实际外部调试发布器；没有访问游戏、Steam、当前存档或UI。A agent先实现三个新文件与7例，交给B agent独立复核、精确化布尔门槛和最终归档；旧文件未变。

## 唯一生产差异

`stopped()`开头新增 `s.restoreReady != 1` 即拒绝。该函数由restore的暂停前预检和持有调试事件后的计划重验共同调用，因此Idle、Complete、Cancelled和error54失败回执分支全受此条件约束。不是只在error54回执分支检查ready，也不接受其他非零整数。

原因是repeat Runtime在Save Complete之外还可能持有独立的下一期观察lease/frame/drainPending。typed Snapshot已把这些状态纳入restoreReady；发布器之前Complete分支会绕过该最终结论。新条件是额外必要条件，原实时桥计数、Host cache、来源字节/保护、PID/birth/模块身份、原生终态与error54精确回执全部保留。restoreReady不能单独授权恢复；它仍来自已验证构建与本次typed快照。

原error54检查不变：同base/generation/thread/Owner error、sequence稳定、retired1的实际导出DATA回执，Driver Uncertain54、阶段/队列/worker/return条件、无fileVerified等仍必须匹配。没有伪造成功Save或清除旧错误。

## 验证

私有前一运行 `a_save_repeat_publish_runs/20261009-142716-729345`：7/7通过，仅检查ready非零；保留该中间证据，不能代表最终严格编码要求。

最终 `a_save_repeat_publish_runs/20261009-142815-825524/result.json`：**8/8 PASS**，SHA256 `ff5136c9ed8a7fb304fec26d1d913d304f43627b7adfad8d1af90cf2bcdde941`。

- Complete + restoreReady1：实际attach、恢复、detach成功。
- Complete + restoreReady0：暂停前拒绝，写入0，来源保留。
- Complete + restoreReady2：暂停前拒绝，写入0，来源保留。
- 原error54同代已退休回执成功；缺回执、错代、Host仍持lease拒绝。
- 零绑定Cancelled + restoreReady1仍可恢复。

每例先执行实际install并由目标独立核实来源，然后设置该例诊断终态、执行restore、再次由目标核实实际来源。正常场景3处inline与2处已发布Owner槽发生还原；另外2个Gate槽本来为原值，仍在完整七来源核对中。不得把written_mask31写成七处都发生修改。

生产 `publisher.exe`实际编译并对自有目标执行拒绝预检；成功事务用同源码的 `A_SAVE_RUNTIME_PUBLISH_FIXTURE` 版本，允许自有stage Hook地址。调试attach/线程CONTEXT/来源写入/保护/回滚实现仍实际执行，但这不是生产发布器在游戏中通过。该宏边界沿用前驱，本轮未变。

18份source、8份二进制/对象、1份生成build.cmd全部再次核验与最终结果一致；三新增源通过EOF/尾空白检查。所有目标和发布器已退出，surviving_owned_pids为空，没有保留调试事件或新活动进程。本轮没有失败运行；中间7例与最终8例都保留。

最终生产publisher SHA256：`f0968d465fe57447de84ad4b60a420a3fdef98757a91ee69daa52fd164071ace`。

源码：

- `a_save_repeat_publish.cpp`：`4df56c09de0eb413b3c7823b1276e753dacaecf7009de741b0225fd9cbbfcf13`
- `a_save_repeat_publish_fixture.cpp`：`e6fca67456ea0800205483a4b3cd69dec0a370bd2ea782565ff7e128d6ff096c`
- `a_save_repeat_publish_test.py`：`a6effa18dc3f09cecad18db4064fa27c491c638c89ed5a2fd45b66e607f197fa`

CLI/typedPlans/Snapshot布局与前驱一致。后续repeat实机启动必须明确选这份经过验证的publisher构建，不能继续拿旧abort publisher绕过restoreReady。本测试的Complete/notReady是自有目标数据，Runtime是否真实消除repeat租约另由其组合证据负责；这里没有代替该证明。
