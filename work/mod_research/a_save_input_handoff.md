# A 保存时独立输入来源：全局 UI consumer

2026-10-08。仅新增 `a_save_input*`，未修改冻结 `a_save_user_owner*` 或 `checkpoint_ready_input_gate*`。**生产组件编译，15/15 自有进程场景通过；无游戏、Steam、实际键鼠或其他应用操作。**

## 接通的实际来源

原有 Ready gate 的 fixture 直接调用 entry shim，没有发布实际全局 UI 来源。本模块发布两个真实 vtable 槽：

| 来源 | 原入口 | 作用 |
| --- | --- | --- |
| `12CC9B8+28`，CGame.Update | `3F8140` | 原生父更新仍正常执行，实际 PE 桥维护调用与 FINALLY 作用域 |
| `1297CF8+18`，全局 UI Update | `1AC3C0` | 仅在上面真实父作用域内、原生调用点 `3F85F2`（返回 `3F85F6`）按请求抑制 |

两处均执行 HookSet CAS 与只读页保护恢复；没有写 User/Save 槽，未叠挂旧规划 wrapper。生产校验原始槽、MEM_IMAGE/AllocationBase、RX/RO 页及完整原生函数哈希：Game `3F8140..3F871B`、global UI `1AC3C0..1AC423`。支持 EXE SHA/当前附着身份仍由可信外层安装器核对。

这一步将两个原本互斥的动作分开：User 不必为了阻止这条 UI 路径而整体停掉，保存所需的 raw User/Save 可以继续运行。调用 `Hold(binding,true,revision)` 只是请求；首次实际 Game 作用域还须通过冻结 pending inspector，绑定当前 root/world/状态对象及实际返回来源。之后仅允许相同五层规划栈，或明确的第六层 `CSaveState`（vtable `12DC5F8`，phase0..4）；未知模态或换 world 会报错，后续透明转发，绝不自动授权保存。

Stop 和 sticky error 后不再持续压住 UI；模块保留驻留，不卸载、不恢复可能被别人接管的槽。已发布后若出现竞争指针只报错，测试确认不覆盖。普通 Game 更新与异常继续传递，完整 RAX/XMM0 和 FINALLY 保留。

## 组合测试与边界

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\san14-private\mod_research'
py -3 work/mod_research/a_save_input_test.py
py -3 work/mod_research/a_save_input_sources.py
```

第一个命令只读引用私有 `checkpoint_push_profile.h`，编译生产库和自有 fixture；第二个只读固定哈希的归档 `game-runtime-image.bin`。不调用历史 live 脚本、不打开任何游戏进程。

最终原生记录 `a_save_input_runs/20261008-021122-993826/result.json`：**15/15 PASS**。包含 open/hold/release/Stop/实际回调内Stop、未知模态、待处理菜单、换 world、外来调用、SEH 异常、发布前停止/来源变化、发布后竞争来源。

- 原生结果 SHA256：`856dd8f78ee95f91bbb2f6f2c7e32718ecdd6163c1a0f51d7b78ba9b6e9baa28`
- 生产库 SHA256：`462ad2135b1a85a5f32807f6f889bfc58e0598c71426dd0a58d95374a775ae45`
- fixture SHA256：`933378f639a13cb8e90a3765077a0625c1b274a7500436745528d5c96541047c`
- 归档覆盖结果 SHA256：`54ad047d2b4cbb87a432e0cc5122dc7327701ef794812d11585925c13e01ec06`

组合 `two-saves` 直接复用冻结 A Owner 和其明确替身保存业务：同一进程同时发布四个不同槽，实际经对象 vtable 间接调用。在全局 UI 持续被抑制时，raw User、五个 Save 阶段及返回 User 都执行；同 Owner 完成两次 binder、两次 queue 和四次 native API 全量读回。输出仍是 32 字节诊断文件，**不是 SAN14 存档**。Game/globalUI/User/Save/Steam 业务均是明确自有替身；实际执行的是发布、PE 桥、TLS/SEH、状态检查与已有 A 保存组合。

另有 `panel-bypass` 反例：全局 UI 被确实抑制，但独立 Game 路径仍可置入 panel 请求；原 Fresh Driver 发现待处理请求后拒绝保存，没有 binder/queue。这个反例证明 `coveredGlobalUiHeld` 只能描述本调用范围，不能当作完整写入排除。`fullInputHold`、`saveAuthorized`、`roomReady` 始终 false。

归档覆盖记录 `a_save_input_sources_runs/20261008-021002-757265/result.json`：19 个未覆盖锚点与两个完整函数哈希通过。首次检查因手写 `3F9EFA` 的 rel32 字节拼写错误失败；读取固定归档的原始五字节后更正指纹，未放宽校验或改归档。

## 明确未覆盖的来源

| 未覆盖路径 | 为什么仍可产生操作 |
| --- | --- |
| `3F8606 → 3FA820`，读取 panel`+1B0` 的 `3FA857` | Game 的直接 panel 消费绕过全局 UI vtable；不是本模块子调用 |
| `3F9EFA → 3A2DA0`，`3A2DA9` 读 raw keyboard`+50` | 保存必须继续的 raw User 仍可读物理修饰键；旧 neutral shadow/query router 尚未发布这些实际调用来源 |
| `3F9F9D`、`3F9FA6`；`3FA06D → 2E84A0`、`3FA09A → 3FC270` | 已锁存 advance、Game`+47C` 和规划命令执行路径仍存在，不能只清屏幕菜单 |
| `51234A → 510BE0`；`510C1C → 3A39D0` | Windows 消息和鼠标预处理不在 Game/globalUI 作用域里 |
| `510D59`、`510D7C`、`510E0F` | Enter/Escape/Backspace 可重新发布鼠标业务消息，目前没有原生 WndProc/真实队列接线 |
| `F4C948 [rax+50]`、`F4B458 [rax+48]` | 真实键盘缓冲事件、鼠标设备状态仍可进入缓存；本模块没有拦设备轮询 |
| `F4AB13 [rax+48]`、`F4AAB9 [rax+8]` | DirectInput 与另一套手柄回调均未接入 |
| `509BEA → 3A35D0`、`509BFA → 3A3210` | Root 输入转换可能重新填入缓存，未证明其与所有消费者的跨线程顺序 |

通过 `1AC3C0` 进入的两条子 UI 调用 `1AC3FB [r8+18]` / `1AC40D [r8+18]` 会随父入口一起被跳过；其他地方直接调用这些动态子对象的路径仍未覆盖。还缺真实物理松键/焦点变化后的隔离、未枚举脚本/间接消费者和全部线程业务写入排除。

下一步优先把 `3F8606` panel 来源与 raw User 的输入读取/命令路径接到同一可信排他生命周期，再处理 `510BE0` 消息链。当前不得以本模块的 receipt 放行 Room Ready 或实际保存。B/world重建后也不能复用旧 root/world 绑定。

本轮没有活动游戏补丁、调试器或等待用户的操作请求。所有 fixture 子进程已退出。
