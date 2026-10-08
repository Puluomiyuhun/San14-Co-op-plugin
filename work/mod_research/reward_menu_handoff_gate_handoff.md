# 赏赐确认前暂留与一次领取后继（2026-10-08）

本轮完成一个**可编译的原生确认前门禁组件**，并在自建进程中执行已有私有归档
的真实 UI Update 来验证接入。它不是游戏安装器，不能直接用于联机。
没有访问游戏、Steam、当前存档或 UI；没有启动 preflight/record、注入或调试器。
冻结的 `reward_menu_capture` / `reward_menu_observation` / 房间协议均未修改。

## 做到了什么

- 自建进程将其自身副本的 `67A993 call626050` 改向新门禁；门禁从实际
  `67A998` 返回地址进入，校验登记的5字节 call 与12字节 relay，以及当前
  User/state/layout/root/world/势力/军团/日期和真实列表结构。
- 首次确认从复用的原生只读 decoder 复制纯 ID 提案。相同 Update 连续进入
  只保持等待，最多捕获一次；`TakeProposal` 也只能成功一次。没有调用原包装、
  公共赏赐或 UI pop。门禁始终返回包装层的0，**没有伪造赏赐成功返回值**。
- 领取前重新核来源、当前对象、event和列表；改选、世界/日期/布局变化、外来
  线程、释放布局或销毁选择列表等异常会保持阻止并拒绝旧提案。领取后再发现
  变化进入终态 fault，记录 `proposal_was_taken=true`，不会声称撤销已经领取的命令。
- 原生领取结果实际进入既有 `CaptureSession`，构造相同请求并经真实本机 TLS
  发送两次，只形成一个权威命令，两端业务模型各应用一次，再串到既有 Ready。
  本组合没有从只读 observer 的 shadow 提取可发送命令。

## 本轮新增的原生来源证据

固定归档：image SHA-256
`5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`；
历史 EXE SHA-256
`42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025`。
测试结束对 image 和 runtime-pdata 都重新哈希。源码只保留少量锚点和摘要；
提取的382字节代码只放在本机 ignored run 目录，不提交。

| 位置 | 已证实行为 | 没有据此声称的内容 |
| --- | --- | --- |
| reward vtable `1331078` 的 slot1 `674980` | 建立 layout，写入 `state+478` | 没有完整构造/进入菜单的运行证据 |
| slot2 `667B10` | 读 `layout+168` 到 `state+8`，依次调 layout虚方法+40/+28/析构(1)，将 `state+478` 写0，之后可通知 state+48 回调 | 未知哪个按键/取消事件会调用它，未证明实际调度方和排他 lifetime |
| slot0关联析构 `60B000` | 重写类型表，并调用 `1FED80` 释放 `state+480` 选择列表 | 没有执行 allocator/free 或整个 UI 状态弹出链 |
| slots3/4 `665CD0` | 同一个 `return 1` leaf | 不能从位置给它命名为取消检查 |
| slot5 Update `67A930` | event2经过 `67A993`；返回0直接回调用方，重复frame仍会再进这个 call | 只覆盖这个已证分支，不证明全部命令入口或全输入隔离 |

实际 CPU 执行包括145字节 Update、136字节 slot2方法和101字节析构主体。
所有外部 helper/虚函数均为明确的服务替身；清理场景实际执行原机器码的
`state+8` / `state+478` 写入，并检查 helper 顺序。
包装 `626050`、公共处理器 `1D6DA0`、实际 UI 控件和自然弹出调度没有执行。
ASM fixture 验证 Update 正常返回时 RSP/RBX 保持；没有声明异常能穿越未经
注册 unwind 表的归档副本，所有 gate 解码异常都在新编译组件内部捕获。

## 接口和失败行为

新文件均为 `work/mod_research/reward_menu_handoff_gate*`：

- `.h/.cpp`：纯本机原生组件；无进程查找、网络、远程写入、安装或执行 API。
- `_fixture.cpp/.asm`：自建内存、仅自有副本接线和实际 CPU 调用。
- `_audit.py`：显式指定私有输入，有限静态来源核对。
- `_test.py`：构建、独立进程反例与既有 TLS 组合。

`Bind(Binding)` 在调用前绑定真实对象、同一原生线程、menu_id、generation及
日期/视角，并要求原call五字节精确一致。**完整 Update、页面可执行属性、
进程身份和安装排他仍须由未来 installer/Owner 提供**；这里不是完整来源认证。

`RewardMenuHandoffGate_Entry(state)` 仅供该已登记 call 的原生入口。
`TakeProposal(menu_id,generation,out)` 必须在同一绑定线程领取，方便未来
可信宿主把 IPC 请求投递回原生 Owner；本组件没有提供 IPC。提案只有版本、
menu_id、generation、force/district/city和最多16个唯一人物 ID，不含进程指针。
错claim/重复领取/重复Bind只更新 `last_rejection/rejections`；`error` 专用于
终态失败，成功领取不会残留一个表示故障的旧错误。

`Retire()` 进入终态并拒绝领取，**不恢复原call、不关闭菜单、不清除event、
不伪造取消、不撤销已经送出的请求**。所有后续进入仍返回0保持阻止。
第一次 Bind（包括失败）占用本组件；这是单次菜单来源实验，不能 reset/rebind
来接下一菜单。实际多菜单/跨旬应由持有真实 lifecycle 的统一 Owner 后继完成。

API本身不是持续锁。Take 时的再次检查不能证明其后对象不会变化；菜单输入
仍可能走event0/1或其它消费者。TLS测试的房间/attachment/menu revision上下文
由明确 fixture 提供，尚无生产可信 context/IPC 生产者，也不把一个布尔字段
当作可发送或可执行许可。所有结果中的 production_permit 恒false。

## 最终验证及失败记录

复跑入口（只读私有归档、只创建自有进程）：

```powershell
py -3 work/mod_research/reward_menu_handoff_gate_test.py --archive-root <private-archive-folder>
```

最终 **67/67 PASS**，路径：
`reward_menu_handoff_gate_runs/20261008-205639-507224/result.json`。
32项归档静态检查 + 34个独立原生进程场景 + 1项真实 TLS 组合。
26份源码前后摘要一致，image/pdata结束摘要一致。关键反例包括重复/错误claim、
原call或relay变化、外来调用点/线程、变更视角/日期/world/stack/layout、循环或
重复人物列表、不可读world、领取前退出/析构、领取后修改、三种退休时机。

| 产物 | SHA-256 |
| --- | --- |
| 最终 result.json | `f922ab4d64c4fcb249a9df87a82f7713c1a7491c809cc467478c09b4378cc8bd` |
| fixture.exe（不提交） | `1bc0fe0dc14f87114d38c4de13a6fb2744953afda2395725418f740f3ab5f07b` |
| gate.h | `b88f8c8d151cdb20cf8b67a8996f95db80a2531b36091a3d45d0ac64392f3fc4` |
| gate.cpp | `6ec452afe4a4b774bd78cc43c558133d7fbdc8205babc549ec93bfe12e0f03c5` |
| fixture.cpp | `7961807285380cfdd7f8cff79fe785fa01739d7bcc878fff249fd842be22592d` |
| fixture.asm | `a7d3f9ca6e8ca8c5630eeb3cab7b386723347013cd02bcf1fe2c0b0689a6d22b` |
| audit.py | `0e91c87683e7542e018e8031b002e57bbccb14538ba94d1899c0af4cb50a90e0` |
| test.py | `c43389182b3ce5b5246bb77dd9be52373c81e3d019e33540dcab8e35ef8ed7f0` |

失败保留：`205238-963131/failure.json`记录测试器依赖清单误写不存在的
reward_protocol.py，尚未构建；`205341-659957/result.json`有32静态检查通过，
随后MASM的 `/Fo:bridge.obj` 参数导致未生成预期链接文件，改为正确参数后重跑。
`205417-295895`是65/65中间成功，新增两个反例/状态断言后以上67项才是最终来源。

## 下一步最小接线

1. 用户方便时用冻结的只读观察器采集一次真实菜单确认，并补 slot2清理/析构
   与状态调度者的有界观察；不要用自然执行后的shadow重复提交。
2. 找到能够持有菜单对象的真实 Owner，把上述 call 替换、源恢复、退出、
   提案领取和确认结果收尾做成一个生命周期；本轮清理方法提供精确来源点，
   仍缺取消输入→该来源及正常关闭时机。
3. 接当前统一规划Owner的可信 room/attachment/期次上下文与原生线程投递，
   再接已有权威去重日志。实际安装前要有完整指纹/页面/线程排他及恢复策略；
   不应为了测试直接把本fixture中的补丁写入游戏。

所有自建进程和 localhost TLS 已收尾；无活动游戏补丁/调试器、无待用户操作。
根文档、公开证据与 Git 提交由主 agent 处理。
