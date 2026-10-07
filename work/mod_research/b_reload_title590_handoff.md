# B 连续加载：Title +590 启动与自动 runner 接线

2026-10-08。本模块是 `b_reload_title_source` 和冻结 `checkpoint_task_completion*` / `checkpoint_task_native_*` 的明确后继，未修改前版本。本轮没有打开游戏进程、安装游戏钩子或发送游戏操作，所有执行验证均在自有测试进程进行。

## 本轮补上的具体来源

新增 `b_reload_title590_ports`、`b_reload_title590_publish`、`b_reload_title590_router`、独立 `b_reload_title_bridge`，以及使用这些后继的 `b_reload_title_source_v2`。选择的是 **Title +590 worker 启动到自动观察器激活**；没有把 Title +520 或父任务来源也算完成。

归档指令证据：Title.Update `4AA7B0` 的阶段 15 在 `4AAF53` 调用 `4BEEE0`。该初始化器在 `4BEF1A` 调用 `833CB0`，payload 为 `466600`、control 为 Title+590；在 `4BEF26` 调用 `834B60`，返回地址为 `4BEF2B`。原生线程入口 `83A930` 等待结束的位置是 `83A9D7`，其后通过 object+38 间接调用 runner，返回位置是 `83A9DF`。原始 runner 是 `834D10`。阶段 16 的 +590 join 返回位置是 `4AAF89`。

新的 Title scope 在原有两个 join 硬件来源之外，增加 `834B60` 启动来源。实际 CONTEXT 满足 RCX=Title+590、调用返回地址=4BEF2B，且前序 +520 join 已被接受时，才送入冻结 Provider 并尝试发布。不是由测试主动合成这次 Start Capture。

Publisher 复制本进程线程和事件句柄，暂挂 worker，并要求它原本未被暂停；检查该线程确实处于 `83A9D7` 的原生等待栈、寄存器对应同一 object/control、自动重置事件未触发、原 runner 指针仍为 `834D10`。全部通过后以 CAS 将 object+38 改为自己的 runner 桥，再核对事件状态；失败则按已发生的操作收尾，始终恢复自己的暂挂并关闭复制句柄。不修改原始函数代码。

新的独立桥有自己的两个一次配置槽，避免挤占原 Load bridge bank。它具有实际 PE 展开及 FINALLY 信息，原函数只执行一次，保留返回值并传播原生异常。runner 桥根据当前线程、object/control、调用来源和不可变 generation 注册自动进入冻结 role 2 的四点观察器；测试不再手动调用该角色的 Begin。迟到旧对象不会落到“最新一代”兜底。

Title vtable 来源仍只发布一次、恢复原只读页保护、保留常驻所有权，两代复用同一来源，不覆盖竞争指针。v1 与 v2 不能叠加安装。生产构建对新增初始化器、Start、线程入口和 runner 指纹要求同一 MEM_IMAGE；fixture 宏只在自有测试构建中启用。每代 scope 的硬件寄存器在 FINALLY 恢复。

`Stop()` 关闭尚未开始的发布及该代观察，不声称已发布桥已卸载或回调已排空。Router 中继承的 `sourcePointerInstalled` / `productionPublication` 为 false：真正发布证据在 Publisher，不应把路由报告当作来源报告。Publisher 复用的旧 Report 中无关的父 scope 字段保持零；父 scope 的恢复应读取 Ports 报告。全局 scheduler fence、完整输入排除、Ready、真实游戏验证均未开放。

## 自有进程验证与边界

运行命令：

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\san14-private\mod_research'
py -3 work/mod_research/b_reload_title590_test.py
```

需要此前私有归档镜像、fixture 存档和相关生成头；仅只读使用，不扫描或附着游戏。新增包含归档字节的 `b_reload_title590_profile.h` 只生成在被忽略的运行目录，不进入源码或 Git。没有私有输入时不能宣称新电脑可直接执行该验证。

测试保留前版两代 Session/Provider/身份和 Load 流程，通过真实虚表间接派发 Title.Update。实际在 CPU 执行归档 `4BEEE0`、`834B60`、`83A930`、`834D10`，捕获真实硬件上下文，暂停真实自有线程，使用真实 Win32 自动重置事件；+590 runner 自动发布并激活观察器。第二代重建不覆盖保留的 Title 虚表来源页。

**线程构造器 `833CB0` 是使用 CreateThread 的自有替身，辅助 `394470` 是自有空实现，payload 仅保留必要归档前缀，业务主体是自有替身。** Title +520 仍使用显式 Begin；父调度来源和部分完成上下文仍由 fixture 提供。因此这是生产接线代码加归档指令执行验证，既不是整套游戏业务执行，也不是两次真实读档证明。

最终 **12/12 通过**：

- 4 个正常两代流程：正常、全部历史地址复用、迟到旧任务、Title 尚未完成分支。两代均捕获一次 +590 Start、成功等待核验及发布、一次自动 runner 激活、四次 role 2 来源、正常 FINALLY 和三个 join。
- 原生 payload 异常：第一代仅有两次 role 2 来源，FINALLY 和硬件恢复成立，拒绝第一代成功收尾；第二代正常。该用例不是两次完成读档。
- 错误等待位置：第一代返回 WaitStack 错误，无 runner 发布及激活；worker 恢复后原函数继续执行，不能取得完成凭据；第二代正常。
- 6 个来源拒绝场景：发布前停止、槽位漂移、代码漂移、虚表页可写、adapter 停止、发布后竞争指针。

五个新增 C++ 生产对象在无 fixture 宏时编译通过；独立 ASM 桥在实际 PE fixture 中链接和执行。没有构建或安装可在游戏中使用的最终完整模块。源码及私有输入哈希保持不变，测试进程已退出。

最终本机记录：`b_reload_title590_runs/20261008-022152-474574/result.json`。

| 项目 | SHA256 |
| --- | --- |
| result.json | `b0262258f05a33b1a8730ef587979ae0a7bc40705c5438fc9c5446d96c388f73` |
| fixture.exe | `0d79e219bb2fc2986f69e7cbec89170502af1213c02497c7aa4d858cc2b8de1f` |
| 生产 bridge 对象 | `1eee84499bcef6cb8aef5fa00e4d076cb5a00410dc1a469717cd846354ede4c6` |
| 生产 router 对象 | `4f8212a39c834a2d25645b0e5c1000172eeec63c44c4c229851763bd9a94634d` |
| 生产 publish 对象 | `be38daf06df03e908f5da4acbf9a8c628d301245876f184c3e33ce315d1240bb` |
| 生产 ports 对象 | `2f5cfd9bdf41378d37281c7a2ac58cb471df1535bfb2120b08f1deeca19742d8` |
| 生产 source v2 对象 | `888bc123984cc596525048037cbbaab934a0ce553904859ace601702c99b2c53` |

保留失败记录，没有将它们改写成通过：`021527` 是 fixture 文本转换锚点不唯一；`021547` 是嵌套 include 选到冻结旧 fixture，打印编译错误时另有终端编码异常；`021737` 是旧 fixture 的人工四参数常量断言误用于实际仅有两个整数参数的 native runner。分别用精确锚点、明确后继 include 名称、区分真实调用 ABI 修正。`021900` 为中间 12/12，通过后增加初始化器/线程入口/runner 指纹与发布模块钉住；`022152` 为对应最终源码的 12/12。

## 精确剩余缺口及接手顺序

1. Title +520 的创建/启动和自动 runner 激活仍缺生产接线。它来自不同的 `4BEE50` 路径，不能直接复用本轮 +590 的 `4BEF2B` 归因；+520 已知 Start 返回位置为 `4BEEC2`，payload 为 `4DA390`。
2. Load Finalize `4CC690` 的真实来源捕获仍未安装。该路径会调用 `4BEE50`，宜与 +520 一起核对，不由调用者手工报完成。
3. 父调度任务 fresh/resume/完成来源（`50B4B3`、`50B598`、`50B4AE`、`50B632` 等）仍未全部安装。现有 fixture 提供的上下文不能算生产来源。
4. 需要可信运行所有者组合原六入口、本次 Title 来源、各代 Session/Provider、房间授权和完整输入排除；还要处理读档前双人规则撤回旧 world、新 world 重绑定。当前模块不发起读档，不发 Ready。
5. 最后需在同一个真实游戏进程，连续加载两份不同的真实存档，核对 B 势力、整个世界和恢复下令，再做两台电脑端到端测试及等待画面验证。当前 constructor/payload 替身不能证明这些成立。

本轮源文件已冻结，可继续从 +520 / Finalize 或父调度来源推进；无需用户操作即可开展下一段自有进程开发。没有残留活动游戏补丁或调试器。
