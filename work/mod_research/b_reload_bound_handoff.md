# B 父调度观察的原子代次绑定

2026-10-08。只用已有私有归档、自有进程和明确 fixture 服务。没有访问游戏、Steam、UI 或当前存档目录，没有新增游戏补丁/调试器，也没有等待用户操作。

## 已修复的具体问题

上一版 parent 在 `Snapshot(old)` 后调用普通 `Observe(capture)`，外部线程可以在两者之间 `OpenWindow(new)`。旧窗口仍显示 open，但 fresh 捕获会使用新的 `current_`。这个问题不是文件哈希或再读一次 Snapshot 能解决的。

新 `checkpoint_native_task_provider_bound` 增加伴随接口 `ObserveExpected(provider, {generation, attempt, epoch}, capture)`。三个身份字段、当前 bank、open/closed/error 状态以及允许的 RIP，在 **Provider 原有同一把锁**里检查，并在释放锁前处理 Capture。错代时返回 false，不切回旧 bank，也不改写任一 bank 的事件。父来源沿用终态 `Error::Provider`；这不等于停止原生调度或冻结世界。

只允许四个 parent 点：fresh `50B4B3`、create `50B598`、resume `50B4AE`、complete `50B632`。body 的选择、查找和处理都限定 expected bank；resume/complete 要求唯一匹配，不能从另一代借任务。bound create 缺少 fresh selection 时明确 `Error::Order`，不再用 ignored=true 冒充成功。错身份或非这四点的请求在处理前拒绝，不伤及无关 bank。

伴随接口用 thread-local frame 传递本次身份，frame 含 Provider 指针；嵌套调用拒绝，FINALLY 清理。原 `Observe` 持锁后才能采纳 frame；已通过核验的 bank 是内存异常的归属，不能在 SEH 中改归“最新代”。旧 worker 的普通 Observe 保留已有 immutable record/TLS 归属，允许老任务在 current 已切换后继续返回和 done。

## 明确替换关系

- `checkpoint_native_task_provider_bound.cpp` 替换冻结 `checkpoint_native_task_provider.cpp`，公开类头和布局不变；不能两份实现同时链接。
- `b_reload_bound_parent_source.cpp` 替换冻结 `b_reload_queue_parent_source.cpp`，仍使用原 queue header/PE bridge/ABI。只把实际 capture 的提交改为伴随接口；原 Snapshot 是额外检查，不承担原子证明。
- 新 companion header、fixture 和 test 是 `checkpoint_native_task_provider_bound.h`、`b_reload_bound_fixture.inc`、`b_reload_bound_test.py`。冻结前驱没有修改，不重置 once-claim、不复用桥所有者。

Finalize/Title 的其他来源仍用原接口和既有 role/身份匹配。**此次只解决四个 parent 捕获点，不证明所有原生来源、加载窗口生命周期或全程执行排他已完成。** OpenWindow 本身仍可选择下一代；本后继的作用是在这种情况下拒绝旧 scope 的新观察。

## 验证层次

测试分三组，不能全部当作实机或全部当作原生来源测试：

1. 三个归档组合：success、全部历史地址复用、Title 等待。复用实际 parent 调度、type1 pop、Finalize 和两代 Title 来源，每项两个 queue pop、18 个有效 parent scope、2000 次不消耗 scope 的普通调度。两代 closed 后额外递交故意不可读的 Capture，必须在读取前拒绝且不污染已完成回执。
2. 十二个直接 Provider 反例/兼容性检查。Capture 是明确 fixture 数据；Provider 锁、真实线程、Core ticket 和事件状态机实际执行。包括错误 generation/attempt/epoch、非 parent 点、另一个未登记 Provider、另一线程抢先切 current 后的 old fresh/create、缺 selection、内存异常与 TLS 恢复，以及跨 bank resume/complete。旧 worker 在另一真实线程运行 entry/return/done，必须令旧 bank events 真正增加三次、新 bank 不增加；不能只凭 Observe 返回 true 判定成功。
3. 一个实际 parent 竞态组合 `bound-parent-switch`。归档调度器已进入旧 scope，在 F570 fixture 服务中由另一线程 OpenWindow 新代。随后真实硬件来源取得 fresh 的 OS CONTEXT，伴随接口拒绝；两个 bank 事件/创建均为零。fixture 的 pool 服务再抛出指定异常，实际 PE FINALLY 必须恢复六个调试寄存器、清 active、保持首个 Provider 错误，才能退休父窗口。**这个 pool 异常是测试排空办法，不是生产调度 fence，不能推导真实引擎已停。**

跨代 resume 反例使用仍 active 且真正 yielded 的旧任务：工作线程进入、Observe yield 后等待；父线程的新 expected resume 被拒绝，然后普通旧 Observe resume 必须成功，再释放工作线程正常返回/done。这样能区分“阻止跨代查找”与“任务早已结束所以任何 resume 都失败”。

自有 fixture 的事件/线程创建或等待失败立即以非零状态退出该自有进程，避免带活线程返回栈上 job 后发生 use-after-scope；这不是生产错误恢复策略。常规桥的 helper 超时后仍保留原有等待排空语义，不宣称保证有界延迟。

## 中间结果与修正

- `b_reload_bound_runs/20261008-135850-475087`：14项中11项通过。新 fixture 错把 parent/worker 设成同一线程，实际 Core 正确拒绝 creation；原生后继没有放宽此检查。
- `20261008-140035-382885`：换成真实独立等待工作线程、增加旧 bank events+3 断言后，15/15；另修 bound create 无 selection 的旧 ignored 语义。
- `20261008-140303-771629`：加入实际 parent 中途切代及 FINALLY 恢复，16/16。复审指出当时的 resume 反例使用已结束任务，缺乏辨别力；不是最终 resume 隔离证据。
- 最终版本把 resume 改为实际 active/yielded 任务，补上合法旧 resume 正例，并收紧 fixture 的失败等待生命周期。最终记录与摘要见下节及根公开证据；中间结果全部保留。

## 复跑与剩余工作

最终运行：`b_reload_bound_runs/20261008-140632-388321/result.json`，16/16，所有进程exit=0，129份源码及私有输入前后摘要一致。两份后继生产对象以无fixture宏配置编译通过。

| 项目 | SHA-256 |
| --- | --- |
| result.json | `00ae3d3b4042d8c53da1cc583a23e0078798e1792a69df8b675b20ff10a28cbc` |
| production Provider | `a24aded53d6572cc29e58c700ee3c225fbae3d758ff42caf2d3dc119d779cb8d` |
| production parent | `20101aa2c1559bfb79da9e7d8561be0c41007fb1eac720d7dd333436e974c377` |
| fixture.exe | `bdf0311c4d6244731b13cf0a03ee63b69239195315a71986b41e07199058d599` |

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机私有研究输入目录>'
py -3 work/mod_research/b_reload_bound_test.py
```

需要 Windows x64、VS2022 Community 默认 C++/MASM 路径、仓库前驱源码，以及 queue 交接所列私有运行时归档、固定历史输入档及 completion profile。缺失不补零、不放宽哈希。测试第二份文件仍是诊断变体，不是合法新 SAN 存档。

下一步优先接真正 Root worker 的入口/返回/完成来源，以及统一 native owner 的持续排他和异常撤权，再组合生产发布器、B 规则撤下/新 world 安装、原生加载许可、完整世界/身份/菜单/地图帧回执。最多两个 bank/窗口和有界 scope 的限制仍在，不是无限多旬实现；真实 scheduler resume 机器码分支仍未执行，resume 本轮验证的是 Provider 数据接口。

本模块没有触发真实保存/读档、完整世界证明或 Room Ready，不安排双机整旬操作。
