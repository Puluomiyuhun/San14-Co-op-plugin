# A 报告块边界审计与统一排他契约

2026-10-08。只读取固定 SHA 的私有历史归档和仓库源码，在 Unicorn 与纯 Python 模型执行。没有访问游戏进程、Steam、当前存档或 UI，没有安装补丁、调试器或新增实机发布器；无等待用户操作。此轮没有修改冻结前驱、根文档或 Git。

## 结论和最小可推进边界

已有 `a_save_report_owner` 的反向采样依然不能排除 ABA。单独观察或跳过报告 flush 不是完整修复；报告消费和报告生产都必须受同一个保存期排他所有者管理。

本轮定位的精确原始顺序是：

1. `3F9B16 → 15FA20` 与 `3F9B1E → 16C5F0` 在报告切点之前。
2. `3F9B9C` 将 EBP 清零，`3F9BA8` 比较 `User+660` 与 EBP。
3. `3F9BAE` 为零时跳到 `3F9BBB`；非零时 `3F9BB0 → 2A1EC0`。
4. `3F9BB5` 清零 `User+660`，然后到 `3F9BBB`。原 flush 自身包含报告写入和队列清理。
5. `3F9BBB` 之后仍有 selection 查询/更新/清理，随后才到旧 action gate `3F9DAF`。

**只跳 `3F9BB0` 的 call 是错误方案：真实 clear 指令仍执行，queue 留着但 flag 被清零。** 完整跳过 `3F9BA8..3F9BBB` 可以保留二者，但仍保留了下游 selection 写入。

更合适的局部候选是：在已证明是本 Owner 保存代、同一实际 User 调用、phase=2 的前提下，把旧 User action-tail 分流点提前到 `3F9BA8`，直接选原 epilogue `3FA09F`；普通调用走原路径。这一条分流可同时绕过报告 flush/clear、selection 和 action-tail，不需以清待办换取“空闲”。本轮归档执行已证实该点之前的原 prolog 和该 epilogue 能正确恢复 RBX/RBP/R14/R15/RSI 以及调用者栈/返回位置。

这仍仅是**控制流候选**：决策由模拟器改 RIP，未生成机器码桥、实际 call patch、unwind、SEH 或 CET 兼容证明。不能直接替换现有生产发布器。实际执行仍必须经过原 User 入口、原返回和已有 After/FINALLY；不能把抑制 wrapper 的返回伪装成 Driver 所需的原生返回。

已有 action gate 的完整 User 哈希只允许它拥有的旧 `3F9DAF` 补丁；early guard 也固定核对原 `3F9BA8` 片段。因此后继必须由同一个所有者明确管理全部实际补丁、源身份和恢复顺序，更新相关校验契约。不能额外装第三个无主补丁，也不能把任意来源变化统一还原后当作通过。倾向用更早 User 切点替代旧 User 切点，保留原 Game panel 切点；本轮未实现此替换。

## 排他所有者的必要契约

如果需要“保存期间没有世界写入”的结论，边界必须覆盖整个时间区间，而不是增加采样次数：

1. 固定 attachment、world、User、当前保存 generation 和对象生命周期，取得统一排他；等待先前已进入的相关写入者退出。
2. 在该排他内检查 flag、报告树、阶段、已排空命令。已有待办拒绝本次保存，不清 flag、不丢队列、不在持有消费抑制时等待它自行排空。
3. 排他持续覆盖 User 真返回、binder、Save、存储读取/校验和最后的 CopyArtifact。期间每个相关生产者、消费者和后台写入者都必须加入同一协议；不能只挡这一条 User 消费路径。
4. 遇到晚到待办或身份变化取消导出资格，保留真实待办，完成已进入调用的 FINALLY，再由同一 owner 安排合法恢复。故障撤权不等于自动解除房间等待。
5. 模型中将事件留在独立 deferred 列表并按序恢复只是契约演示。原生回调能否延后、参数/对象如何保活、报告与 UI 的顺序语义均未证明；不得照搬列表模型为游戏实现。

## 尚未覆盖的写入者

| 类别 | 已有可核对锚点/已知事实 | 本轮覆盖边界 |
| --- | --- | --- |
| 报告消费和清理 | User `3F9BB0 → 2A1EC0`，flush `2A24B7 → 240310`，User `3F9BB5` 清 flag | 候选更早 User 分流可避开这条调用；其他调用者不自动覆盖 |
| 报告记录与游标写入 | flush `2A236F → 835800`，`835C2C` 写 World+165A | 原始归档执行已验证；没有给该写入函数安装所有者边界，其他来源未枚举完整 |
| 报告生产者 | `User+660`、全局报告树、节点及向量生产/追加/删除 | 本轮没有完整静态交叉引用/线程证明；函数与线程全集未知，不能声称都经 User |
| 较早 updater | `15FA20`、`16C5F0`；后者按模式调 `163C80`、`16C6D0`、`16BEF0` | 原有审计只覆盖前两者空列表分支；非空对象虚调用与另一模式未证明无业务写入。新切点仍在其后 |
| selection | `3FB9B0 → 3EC960`、`3E8EF0 → 337BB0` 非空对象路径 | 直接走 epilogue 可绕过当前 User 的这些路径，不能覆盖其他 caller 或内部对象生命周期 |
| 消息与设备消费者 | `51234A → 510BE0`、`510C1C → 3A39D0`；keyboard `F4C948`、mouse `F4B458`、controller `F4AB13/F4AAB9` | 未加入统一排他；旧 action gate 的局部抑制不能扩展为全局设备/消息锁 |
| Root 输入缓存转换 | `509BEA → 3A35D0`、`509BFA → 3A3210` | 未纳入；其他线程和异步任务同样未覆盖 |
| 保存与复制之间的其他写入 | world/报告地址复用、后台字段更改、生命周期终结 | point check 只能发现部分变化；没有持有生命周期或完成写入者排空 |

上表是已知缺口清单，不是所有写入者已枚举完成的证明。更早切点消除了若干已知 User 下游路径，不能解决所有外围写入。

## 可执行证据

入口 `a_save_report_boundary_audit.py`：只读取 `SAN14_PRIVATE_FIXTURE_ROOT/game-runtime-image.bin`；复核完整归档及冻结 early audit 的 11 段代码哈希，不输出游戏机器码。

最终 **16/16 PASS**，分开理解：

- 3 个原始归档基线，调用冻结 `a_save_early_audit.execute`：report-one 真实执行报告插入、游标递增和清理；report-other-owner 真实执行 flush/clear 但不进入 insert，游标不变；flag-zero-queued 真实保留队列。外部文本/对象查询等模型沿用冻结审计，并逐项列入结果。
- 7 个小块对照：4 种 flag/queue 组合在整块分流下保留待办；1 个只跳 call 的错误反例；1 个普通 call/clear；1 个保留后恢复的模型。原 cmp/branch/clear 指令真实执行于模拟器，flush 外部 callee 和分流决策是明确替身。仅核对所列寄存器与栈，不构成完整桥 ABI/unwind 证明。
- 4 个更早 epilogue 候选：quiet、原有 pending、updater 模型产生 late-pending、updater 模型先写入。原始 User prolog/phase 检查/epilogue 执行，3 个早段外部调用和切点决策是模型。归档指令不消耗待办并正确返回；upstream-writer 反例显示提前到这里仍挡不住更早的业务写入。该模型写的是自有诊断字段，不是声称发现真实 updater 的某个世界字段写入。
- 2 个纯模型：六种外部 producer/filtered-consumer ABA 排列都能绕过前后采样；理想统一 owner 在取得排他到产物 Copy 的区间延后所有模型事件并按序恢复。后者以“所有写入者都服从”为显式假设，**不是已实现锁的验证**。

两类反例的 PASS 意为稳定复现风险。没有原生 Owner、桥、真实存档或 IPC 组合测试；`production_permit/full_write_exclusion/native_owner_composed` 始终 false。

运行记录全部保留：

- `a_save_report_boundary_runs/20261008-135757-636690/result.json`：首次 12/12，尚无更早 epilogue 用例。
- `20261008-135931-917418/result.json`：16/16，随后仅将结果字段 native_return 改名 archived_return，避免误认实机返回。
- 最终 `20261008-135953-165928/result.json`：16/16，无失败或跳过。

最终脚本 SHA-256：`f825292379a6160505768f33f96f3bce6bd71edc1f04ebf9e9b58fcba540c502`。

最终结果 SHA-256：`4aa1c6d3b0bc587adee7b7ab3f442f2454d3e38a23d314ae1aebdcc64fae6e73`。

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机私有研究输入目录>'
py -3 work/mod_research/a_save_report_boundary_audit.py
```

下一步首先实现/审查一个明确替代旧 action gate 的早段来源后继，并保留真实 User 返回证据；同时定位报告生产者与 updater 非空路径，把它们接入持续排他的可信 owner。仅完成更早 User 分流仍不能接 IPC permit 或放行 Ready。本轮新增文件仅 audit.py 和本 handoff。
