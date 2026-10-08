# A 保存动作来源后继：2026-10-08

本轮只读私有归档、构建和执行自有进程；未访问游戏进程、Steam、游戏目录、真实存档或游戏 UI。无等待用户操作；全部 fixture 已退出，没有本轮实机补丁或调试器。`a_save_action_gate*` 是新增后继，冻结旧模块均未修改。

## 实际接通的范围

这是 `a_save_input*` 的**替代后继**，不是可同时安装的额外小模块。它统一拥有 Game/global UI 两个槽及两处动作来源，知道本组件自己修改的精确字节范围；不要同时安装旧 `a_save_input`，旧版本的全函数哈希会正确拒绝新 Game call-site。

- Game `12CC9B8+28 -> 3F8140` 仍执行原函数；global UI `1297CF8+18 -> 1AC3C0` 在有效 Game 来源作用域内抑制。
- Game `3F8606 -> 3FA820` 的直接面板调用改为经保留的近跳板进入 PE 桥。核对实际返回点 `3F860B`、Game 身份、已 claim 的父 Game call/thread/depth 后才抑制；否则透明转发并撤销本地准入。
- User `3F9DAF` 的原指令 `mov rax,[rsi+478]` 改为受核验的 call。只有已有 A Owner 当前保存代的真实 User claim、原返回点 `3F9DB4`、世界/对象/阶段身份均对应时，才把该调用的返回点选为原 User epilogue `3FA09F`。原生 User 函数前段及原生 epilogue 仍执行，保存桥真实观察 Before/native return/After/Finally。
- **User 函数体已明确变换，不能称整个 User 原封不动运行。** 没有把另一个 suppression wrapper 的返回伪装成原生 User 完成，也没有手工填写 Driver 成功状态。
- 选择该点是因为 `3F9DBF/3F9DC6` 的工具栏读取/清除及推进标志消费均尚未发生。只拦 `3FA06D -> 2E84A0` 太晚：此前已写 `3FA01D/3FA03C`，后面仍会写 User phase。正常放行时执行原 `mov`，保留寄存器及 flags。

保留的近跳板是 14 字节无栈变化的间接尾跳，不复制函数 prolog。中段桥有实际 PE unwind 元数据和固定 RBP；原始 faultable load 在 frame 有效时执行。flags 的临时 push/pop 期间固定 FP 仍有效，真正 epilogue 只有 `lea rsp,[rbp+70]; pop rbp; ret`。

由于 held 路径选择原 User epilogue 返回点，**启用硬件 shadow stack/CET 的进程明确拒绝初始化**，查询策略失败也拒绝；没有关闭系统保护。该限制不是完整生产适配。

## 发布与保存组合

`Initialize` 在原字节仍在时检查并生成两个精确 `Patch` 和 RX 近跳板；`PreparedPlan` 只提供计划。外部安装器负责真实线程排空/写入。`Arm` 核对实际 patch 字节后才发布 Game/UI 槽；计划、外部布尔值或“已准备”回执不能代替实际字节。

代码身份检查覆盖整个 Game/global UI/User 源码范围及 panel 前 32 字节。计算原始摘要时只把本组件的两个已核对补丁还原为固定原字节；任何第三处变动仍拒绝。代码的整个跨度逐 region 检查 RX、AllocationBase，生产还要求 MEM_IMAGE；包含 User 跨页尾部。槽位、跳板、补丁范围另查保护和字节。

组合顺序是 A `a_save_user_owner` 在原始 User 字节下初始化并安装自己的 User/Save 槽，然后本后继准备、受控发布两补丁、Arm、Hold。A 保存期间允许必需的 User/Save 调度；本后继抑制指定动作消费者。未 claim 的普通 User 不冒充保存代，遇到此情况撤销准入并透明转发。保存之间仍需要协调器使用已有 User hold，并正确切换保存代；这个完整生产协调器尚未接入。

Stop、粘性错误及部分安装失败后不继续授予抑制；必要的原始调用透明执行。错误还 Stop A Owner，阻止新保存提交；已经提交的保存继续由原 A Owner 保留的回调记录收尾。不卸载常驻桥、不覆盖竞争来源、不自动恢复代码。真实生产安装器/完整生命周期仍未提供。

## 验证及失败记录

入口：

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机私有研究输入目录>'
py -3 work/mod_research/a_save_action_gate_test.py
py -3 work/mod_research/a_save_action_gate_sources.py
```

前者需要私有 `checkpoint_push_profile.h` 及 MSVC/MASM；后者只读指定 SHA 的 `game-runtime-image.bin`，使用私有 `python_deps` 的 Capstone/Unicorn。缺少输入时明确失败，不导入 live 入口、不读取当前游戏。

最终原生结果：`a_save_action_gate_runs/20261008-100652-794864/result.json`，**18/18 PASS**，生产库构建成功，源码/私有 profile 未变。

- 两保存：11 次 global UI 抑制、11 次 panel 抑制、4 次 User tail 抑制；4 次真正 User native return；两次 binder、两次 queue、4 次 native API read-back。两个不同 32 字节诊断文件由同一 A Owner 完成，仍非 SAN 存档。
- 晚到工具栏菜单值 10、panel=1/Game+47C=1 都保持原值；User phase 保持 2。Driver 检查到仍 pending 后在 binder 前拒绝，未以丢掉输入来制造保存许可。
- Stop/release 后原 User 动作继续运行，测试中的推进按原逻辑转 phase 5。包括 Game 中途 Stop、未 claim 的 User、竞争来源、跨页非 RX、未安装、只装一处等反例。
- `tail-av` 在进入原生 User 后才将自有 User 对象页设为 NOACCESS，使原 `mov` 真正 AV。异常经过实际 PE 桥和 fixture 动态 unwind 后到达外层 A User FINALLY：native_started=1、native_returned=0、abnormal=1、finally=1、active=0。没有伪造 AFTER。
- `unwind` 对恢复区每个字节控制 PC（涵盖所有指令起点）、flags 临时 push/pop、规范 epilogue 各边界执行 `RtlVirtualUnwind`，精确核对恢复的 caller RIP/RSP/RBP；该场景 223 项内部检查通过。
- `early-bypass` 刻意在 User cut **之前**执行一个诊断写入：尽管尾段确实被挡，该写入仍发生，且 Driver 仍可能排入保存。这个反例明确说明局部 gate 不能成为生产 IPC 的完整写排除 `permit`。

发布 fixture 的实际线程证据：系统/加密初始化会创建额外线程。fixture 在任何测试游戏执行前，实际枚举本进程其他线程、逐个 Suspend/GetThreadContext、再次枚举稳定后才写两来源；finally 恢复它自己增加的暂停计数。它是**受控自有 fixture 的发布器**，不等于任意真实游戏的安装器。未用手工“单线程/已停止”布尔值替代。

保留的中间记录：

1. `20261008-095652-627876`：首次构建成功，15 个需安装用例因“只有主线程”检查发现系统额外线程而拒绝；`no-install` 通过。拒绝时没有发布补丁。
2. `20261008-095815-143644`：实际暂停/核验/恢复 fixture 其他线程后 16/16 正常场景通过。独立 review 随后发现旧恢复尾部 `popfq` 和释放 frame 后的 faultable `mov` 不满足 Win64 unwind；**16/16 不能当作异常安全证明**。
3. `20261008-100305-050181`：固定 FP/规范 epilogue 修复及两项针对性异常测试 18/18 PASS。独立 agent 只读复核新 ASM，无新增阻断问题。
4. 最终 `100652`：将后继头注释及结果 schema/scope 写准确后，同一 18 项复跑通过；没有扩大用例集合。

归档审计：`a_save_action_gate_sources_runs/20261008-100516-000704/result.json`，四路径 PASS。真实原始 User action-tail 在 Unicorn 执行：正常菜单路径确实清菜单、正常推进路径确实清双标志并写 phase 5；held 路径跳原 epilogue 后四个字段不变，原始 epilogue 正确恢复 RBX/RBP/R14/RSI。**分流决策及外部 callee 在此审计中是模型**，不是 SAN 完整推演；实际补丁/汇编/调用来源另由上面的 PE fixture 验证。报告不包含私有游戏字节。

最终指纹：

- 原生结果 SHA256：`69cd6bd3186035485516ec91ddc9a1940d92ffd9c18449655717ca2be7b8cad2`
- 生产库 SHA256：`8095b5f0ec89b1be2d002fe0939f8dadcf8c0f962ecb6626535d7fbab036bb59`
- fixture EXE SHA256：`bcc73522bad83fb4f7aa6dbaaca5871b087c75acdbee0caa3ead87a1b4e7dd7b`
- 归档结果 SHA256：`bd75828f94c35bd5e12589e9038628e07bfc31d579a8c639f783611795ca9c01`

## 精确剩余与下一步

`fullInputHold/saveAuthorized/roomReady` 一直为 false。不要将本组件接成 IPC `permit=true`。

- User 切点以前仍执行：`3F9B16 -> 15FA20`、`3F9B1E -> 16C5F0` 两 updater；`3F9BB0 -> 2A1EC0` selection cleanup；`3F9C75/3F9CDF/3F9D45 -> 3FB9B0` 对象更新；`3F9D7F -> 3E8EF0`。归档已核对这些确切入口，但没有证明它们只影响显示。下一项最有价值的离线工作是沿这组原生来源缩小可能的世界写入，不能只凭 pending fields 为零放行。
- 窗口 `51234A -> 510BE0`、消息预处理 `510C1C -> 3A39D0`、Enter/Esc 等消息转换、其他直接调用 menu/panel/input leaf 的路径没有由本 gate 全局覆盖。
- 物理 keyboard `F4C948 [rax+50]`、mouse `F4B458 [rax+48]`、controller `F4AB13 [rax+48]`、备用 controller `F4AAB9 [rax+8]`、Root `509BEA -> 3A35D0` / `509BFA -> 3A3210` 缓存转换仍执行。只能说同一已抑制 tail 内的 `3F9EFA Modifier22` 不会运行，不能说该键盘 leaf 的所有调用都已屏蔽。
- 多线程其他写入、失焦/释放隔离、现场 profile/版本、生产源发布与排空、完整保存准入、Room 协调与两个真实 SAN 新文件仍缺。

本次没有改根文档、tools 或 Git；由主 agent 汇总交接和提交推送。
