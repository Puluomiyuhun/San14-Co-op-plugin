# B 父调度实际来源后继

2026-10-08。新增 `b_reload_parent_{source,bridge}`、测试与本交接，前驱是冻结的 `b_reload_title520*` / `b_reload_finalize*`。本轮只读私有归档并运行自有进程，没有访问游戏、Steam、UI 或安装实机钩子，没有等待用户操作。根任务统一维护总文档和 Git。

## 实际关闭的门槛

从归档定位到 `13DC09 call 509FE0`（返回 `13DC0E`），以及该调度函数内部 `50B41B call F570`（返回 `50B420`）。来源所有者准备两个精确的 5 字节 call-site 补丁和两个常驻 RX 叶子 relay，relay 只尾跳正常 PE 桥。`PreparedPlan` 不写代码；`Arm` 只核对已安装字节，不接受“所有线程已停”的布尔值，也不是实际游戏安装器。整段 `509FE0..50B690` 指纹只容许本所有者明确的内部 call-site 被归一化；其他指令、补丁、relay 或页归属漂移均拒绝。

外层桥保持原生调用的一次执行、返回值、异常与 FINALLY。队列处理阶段仅保留当前 OS 线程的外层作用域，不占用硬件断点；只有实际 F570 返回后的阶段桥才能安装 `50B4B3`、`50B598`、`50B4AE`、`50B632` 四个硬件观察点。所有 Capture 都由匹配的异常地址、CONTEXT、线程、DR 布局和唯一事件位生成，再交给冻结 Provider。没有将手填 RIP 当成父调度事件。

`50B632` 同时是正常完成和 yielded-skip 路径。新端口会检查实际正式栈、manager 当前状态、state+50 及 worker+78；仍有 yielded worker 时只记跳过，不交给 Provider 冒充完成。调度器实际清除 state+50 和 manager+48 的行为由 CPU 执行并核对。

生成的组合 fixture 删除了原 `parentPort()` 的人工 fresh/create/complete Capture，改为执行整个归档调度函数。正常两代产生 16 次实际父调度 scope、16 次 fresh/create/complete、8 次已识别的 yielded-skip，全部 16 次 FINALLY 恢复。+520/+590 仍使用前驱独立桥并通过原来两代的角色、三 join、Session 和 planning 核对。

**没有关闭的来源：** `50B4AE` 已列入真实端口，但这批用例没有走“同一父线程恢复一个已 yield 的真实 root worker”分支，不宣称 resume 已实测。root worker 的 entry/return/done/yield 来源仍是原 fixture 明确替身；本轮只替换父线程 fresh/create/complete。归档调度器使用自有 pool、同步服务和预置 callable；其前段 status 服务及正式栈业务也是替身，不等于整个游戏调度业务。

## Finalize 的明确阻断

发现四个真正 Finalize 间接调用点：`50AA53`、`50AD42`、`50AFFF`、`50B1B5`，返回分别为 `50AA56`、`50AD45`、`50B002`、`50B1B8`。它们位于前半队列阶段，早于 worker 阶段，因此不能在整个调度入口一开始占满四个 DR 槽。新阶段分界避免了这种设计冲突。

但真实调度器的 worker 收尾会将 **manager+48 清零**，队列 Finalize 阶段并不重新设成 Load。冻结 `b_reload_finalize_ports` 的 candidate 仍要求 `manager+48 == Load`；旧 fixture 恰好人工满足该值。新组合保留这个旧 Finalize fixture 边界，在单独调用 Finalize 前显式设置该字段，**不将它算成实际队列 Finalize 已接通**，也没有放宽旧 adapter。

下一步应新增明确后继，将 `CurrentQueueOwner` 与上述真实 caller、目标 Load/closure/Title 和不可变 generation 绑定，在 manager+48 为零的真正队列调用中观察 Finalize，再组合两 Title worker。`CurrentQueueOwner` 当前只证明线程/外层来源/queue 阶段，还没有代际授权，不能单独放行 Finalize。

## 有界与失败语义

- 当前最多 128 个父 scope，成功退出后也不回收。所有者尚未按实际 B 加载 window 限定入口；若 `509FE0` 高频逐帧执行，可能很快耗尽。它是有界来源原型，不能当作无限旬常驻观察已完成。下一步须增加可信加载窗口/代际所有权，或在严格正常排空后安全复用普通 scope 存储；uncertain tombstone 不能复用。
- 原 DR 被占用即拒绝；恢复时还比较 Dr6 的事件位，避免覆盖未认领的其他单步事件。Dr6 漂移拒绝经独立静态复审，本轮没有专门制造该漂移的运行反例，不把普通恢复检查当成它的动态证明。
- helper 超时先记录 Deadline/uncertain，然后 `Wait(INFINITE)` 等待自身 helper 排空，以免它稍后改写已弃用的上下文。这是保留所有权的排空等待，**不是有界退出保证**；不能因此声称同步延迟已有上限。
- Stop 后不发布新观察；已经装好的两处代码和驻留桥不会拆除。异常 FINALLY 尝试恢复本作用域的 DR；发生漂移则保留不确定状态，不覆盖他人寄存器。
- error/uncertain/stopped 目前由 Report 暴露，仍缺上层房间撤权、持续输入排他和全局 HELD 联动。组件不阻断游戏业务、不生成完整世界证明、不放行 Ready，也没有真实安装/恢复器。

## 测试入口与失败保留

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\san14-private\mod_research'
py -3 work/mod_research/b_reload_parent_test.py
```

需要前驱使用的私有归档和生成头。固定核对运行时镜像及存档输入 SHA；完整 scheduler 指令仅生成到被忽略的运行目录，未提交。新 bridge/source 的生产对象在无 fixture 宏时编译。fixture 执行两个不同字节输入，其中第二份仍是人工改字节的诊断数据，并非新的合法游戏存档；不是实机连续读档或两个真实客户端。

失败保留包括：103211/103231 的 `/WX` 编译诊断、103253 的驻留 Owner 静态析构错误；103335/103443 的旧 fixture 空 vtable；103619 的 status 检查处于嵌套 phase 桥以及替身 yielded-worker 污染业务边界；103741/103921 的二代旧生成器重写现已只读的父来源页。后继按页排除保留来源，旧 anchors 只核对，不重新写入，不 reset claim。

104348 与 104634 新增的两条异常负例正确暴露了 **fixture 动态函数表注册冲突**：旧多项表的最小/最大地址包络覆盖 scheduler，但表内没有它，`RtlLookupFunctionEntry` 在 `50A7A9` / `50B4B8` 返回空，随后把局部栈当 leaf 返回地址。修复生成后继为每个不重叠函数范围单独注册，并在两代都硬断言 Windows 查找精确命中 `509FE0..50B690 / unwind A00`。生产 PE 桥未为了让用例通过而改异常处理。

最终 **8/8 PASS**：正常、全历史地址复用、Title 等待、发布前 Stop、scheduler 代码漂移、自己的 call-site 补丁漂移、队列阶段原生调用异常、worker 阶段原生调用异常。后二例都在先完成两代后额外执行一次真实 scheduler：外层收到原异常，17 次 FINALLY / 17 次恢复，零活跃和零 uncertain；原生 returned 计数比 started 少一次，未把异常报成成功返回。生产两个新增 C++ 单元编译通过，源码与私有输入前后摘要均未变。

最终私有记录：`b_reload_parent_runs/20261008-104806-541650/result.json`。

| 项目 | SHA256 |
| --- | --- |
| result.json | `b7ede8c4c7462059eab397c338e35d3401bd56f8ed131ec0c6a9c2ba3b5e49e7` |
| fixture.exe | `d7b1eced6fd66e796d809e6c5b6283065e89e12b1feb70c4bf7a70acbbe932d5` |
| production parent bridge | `1f72ee7f5e953375fa4d0f1ad84844e6af9911ca1b97b5159a763915829a5f2e` |
| production parent source | `bda79d4cf33fc24017e1e990609152c7dbfa291e5d84e493e7d8e98f0d137145` |
| parent source.cpp | `c045e5e7bfa7368b03c9044eeb3105a611024b948037576b9ef3b4b3247ad34f` |
| parent test.py | `c29adf7230a1cca67786b302483ae7e3bcde82abee7cb67e10f8ee13eafb7867` |

本轮源码冻结。没有活动自有测试进程、游戏补丁或调试器。下一步是修复上述真实队列 Finalize 契约与受授权加载窗口，再移除 root worker 人工来源；不得把这一轮写成实机连续加载或远端双人原型已经可玩。
