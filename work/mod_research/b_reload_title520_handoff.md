# B 连续加载：Finalize 与 Title +520 原生来源后继

2026-10-08。本轮新增 `b_reload_finalize_{source,ports}`、`b_reload_title520_{bridge,publish,router}` 和 `b_reload_title520_test.py`，复用冻结的 +590 / Title source v2 / Provider / worker ports，没有改写前版本。全程仅自有进程和只读私有输入；未访问游戏、Steam、游戏 UI 或安装实机钩子，没有等待用户操作。

## 接通的实际路径

归档中 Load 虚表 `base+12DBD68+10` 的原目标为 `497110`。它从 Load+48 取得 closure，并调用 closure 虚表+10；原生 thunk `4FAC30` 读取 Load 和 Title 后尾跳 `4CC690`，真实返回地址保留为 `497134`。`4CC690` 的成功分支调用 `4BEE50`；后者为 Title+520 创建 worker，并在 `4BEEBD` 调用 `834B60`，真实返回位置为 `4BEEC2`，payload 为 `4DA390`。

新增 Finalize source 在该固定只读虚表槽以一次 CAS 发布自己的常驻 PE FINALLY 桥，恢复原页保护。发布及 Verify 检查原始函数指纹、镜像所属、指针和只读页；已发布后 Stop 不卸载，不覆盖竞争指针。每代 Finalize ports 只为 Provider 已绑定的 Load、closure、Title 和正式状态栈建立作用域，捕获实际 `4CC690` / `834B60` 的 CONTEXT；返回地址、顺序、角色和当前线程继续由冻结 Provider 验证。没有调用测试的 `callbackPort()` 或合成这两个 Capture 来产生成功凭据。

+520 Publisher 复用 +590 已验证的等待证明：复制本进程线程/事件句柄，暂挂原本没有被暂停的 worker，展开到原生线程等待位置 `83A9D7`，核对 object/control/寄存器及尚未触发的自动重置事件，再以 CAS 发布 object+38 的 runner 桥。后置失败尝试撤回自己的指针，所有路径恢复自己的暂挂并关闭句柄。

+520 使用独立的 `BReloadTitle520Bridge` bank：slot 0 是 runner，slot 1 是 Finalize；上轮 `BReloadTitleBridge` 仍服务 +590 和 Title.Update。两者都保留原函数的一次调用、原生异常、返回值和 FINALLY。+520 runner 自动进入角色 1 的四点 worker ports；+590 保持角色 2。每个 Router 有两份不可变 generation 注册，不用“当前最新一代”作为迟到任务的兜底。

生产 Finalize scope 在每次启用前校验 `497110`、`4FAC30`、`4CC690`、`4BEE50`、Start、线程入口和 runner 的指纹与同一 MEM_IMAGE。原生 Call/Start 顺序不符、原有硬件寄存器被占用、辅助线程失败/超时、Stop 等均拒绝捕获或发布，不因此放行完成/Ready。状态保留到进程退出；没有添加卸载接口或全局 scheduler fence。

## 验证

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\san14-private\mod_research'
py -3 work/mod_research/b_reload_title520_test.py
```

需要同前版的私有运行时归档、存档字节输入和生成头。新增包含原生指令的 `b_reload_title520_profile.h` 仅在被忽略的运行目录生成，未进入 Git。脚本固定核对私有输入 SHA，检查运行前后所有源码和输入未变。没有私有输入不会运行或宣称可复现成功。

最终 **12/12 PASS**，五个新增和五个复用的 C++ 生产对象均在无 fixture 宏时编译通过，两个真实 PE 桥 bank 在 fixture 中执行。正常两代均经过实际虚表派发 Finalize、原生 closure thunk、回调与初始化器，以及真实 Win32 线程/事件和归档线程入口/runner，完成两个角色的自动观察和三个 join。

- 正常、全部历史地址复用、迟到旧任务、Title 等待分支：两代成功；两个角色各自一次自动入口、四个来源与一次 FINALLY，没有未知任务或串入另一 bank。
- +520 原生 payload 异常：第一代仅两个来源、异常 FINALLY 和原硬件恢复，不能生成成功收尾；第二代正常。
- +520 错误等待位置：不发布、不自动进入，恢复原 worker；第一代不能完成，第二代正常。
- Finalize 原生异常：真实 `4CC690` 回调已捕获，但 +520 未启动；异常经过 Finalize FINALLY，不能虚构完成；第二代正常。
- 上轮 +590 的异常与错误等待位置在新组合下仍正确拒绝第一代完成。
- Finalize 发布前停止、槽位漂移、代码漂移均不修改源槽。

生成器明确删除原人工 +520 `Begin`、`startEmbedded` 和 `callbackPort`，并断言它们不再存在。第二代重建跳过两个保留来源页，未通过重新写回来源或重置一次性 claim 使其通过。末尾检查两个角色各自精确调用数、FINALLY 数及零活跃/cleanup fault，并检查 Finalize 来源单次发布、原只读保护仍成立。

**仍为替身的部分：** 线程构造器 `833CB0` 使用自有 CreateThread 实现；`4BDD90` 是明确的准备业务替身；payload 仅执行归档前缀和自有业务体；+520 初始化器调用的 panel、同步辅助等仍为自有服务。父调度任务的 fresh/resume/完成上下文仍由 fixture 提供。两份字节输入不同，但第二份被人工改字节，不是新生成的合法游戏存档，读档业务也不是完整游戏解析器。这些证据不能证明两个真实客户端、连续真实读档或完整世界一致。

结果中的 `actual_finalize_context=true` / `owned_finalize_slot_published=true` 说明自有进程的实际来源。`load_finalize_source_installed=false`、`real_game_reload=false` 指本轮没有把来源装进游戏；不要混为生产代码尚未接通或实机已通过。

最终私有记录：`b_reload_title520_runs/20261008-095337-566788/result.json`。

| 项目 | SHA256 |
| --- | --- |
| result.json | `e437f50c2828baafbdaf37144c5108ecddb8359ccc09534bee412eda69224b79` |
| fixture.exe | `81c71b2c7872e3368af4f80762d56f7ac9a84571a430e30c0683aabd82b33ec3` |
| 新生产 bridge 对象 | `04e6d1eb5f07a39ef5b1fb01b5492d9de1454448843568331ebbf05ba2365753` |
| 新生产 router 对象 | `6e92a9cdef3eaff45d317302dceff994e0ccbf56c7fcdd3b0c2bb65597f8f62e` |
| 新生产 publish 对象 | `afd6a513a48cd195303c3d0eb5d9a0fce8f67c89338a03b13776289eda59e246` |
| 新生产 Finalize ports 对象 | `ba892e3384c9e8f21ee5b8764e8c4f14ec059fc5e3846906543a9cb869ca3e85` |
| 新生产 Finalize source 对象 | `26c5a3f36495887809b2796c7a5d6b410ffdb8a077e9ac880e5a1458d2287a91` |

失败记录保留：`20261008-095037-812515` 已通过生产对象编译，fixture 因删除人工调用后剩余两个未用函数触发 `/WX`，尚未运行场景；后继删除整段人工启动实现。`095119` 为首轮 12/12，`095337` 为补充两 bank 精确计数、原只读保护和禁止人工启动断言后的最终 12/12。

## 精确剩余边界

1. 父调度任务 fresh/resume/完成来源（`50B4B3`、`50B598`、`50B4AE`、`50B632` 等）仍缺完整生产接线；不把 fixture 的上下文当成安装证据。
2. **真实 Finalize 的调度边界尚未证明。** 当前测试在 Load.Update scope 的 FINALLY 已退出后，从独立线程调用 Finalize；若游戏把 Finalize 嵌套在仍持有 Load/Title 硬件寄存器的 scope 里，当前 helper 会以 Occupied 拒绝。应随父调度来源核实实际时序或设计明确的组合所有权，不能为了通过而抢占/放宽 occupied 校验。
3. 新来源依赖可信运行所有者配置正确镜像和两代 Session/Provider，并与已存在的六入口及 Title 来源统一组合。没有游戏发现/安装器、房间授权或完整输入排除接线；组件自身不发起读档，不放行 Ready。
4. 读档前撤回绑定旧 world 的双人规则并排空，新 world 后重新绑定；真实 B 势力/菜单和完整世界核对，以及等待画面仍待完成。
5. 最终还要同一个真实游戏进程连续加载两份不同合法新档，再做两电脑两旬端到端。两代静态容量是当前受控原型边界，不是无限旬常驻支持。

下一步优先补父调度来源并核实第 2 条，而不是再造一层模拟完成回执。本轮源码冻结，没有活动测试进程、游戏补丁或调试器。
