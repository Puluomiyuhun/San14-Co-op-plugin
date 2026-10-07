# B 连续加载：Title.Update 来源发布

2026-10-08。第一方后继模块；未修改冻结的 `checkpoint_task_completion*` / `checkpoint_task_native_*`。本轮没有打开游戏进程、安装游戏钩子、向游戏发送操作，也没有请求用户操作。

## 本轮接通了什么

此前 `checkpoint_task_completion::Adapter::ConfigureTitle` 只配置 `CheckpointLoadWorkerBridge1`，测试直接调用该桥。它没有把游戏实际的 Title.Update 虚表入口交给该桥。

新增 `b_reload_title_source.{h,cpp}` 的常驻 `Owner`：

- 固定来源槽为 `base+0x12DAAF0+0x28`，原生目标为 `base+0x4AA7B0`；不允许传入任意函数或另一个 wrapper 冒充原目标。
- 初始化和发布前检查同一镜像的只读虚表页、原始指针、完整 Title.Update 和 Load join 指纹。生产构建要求 `MEM_IMAGE` 及相同 `AllocationBase`。调用方仍需完成支持 EXE 的 SHA 校验和本机附着检查。
- 复用冻结的 `ConfigureTitle`、真实 PE FINALLY 桥及 `checkpoint_load_hook_set::Set`。实际执行一次 CAS，并恢复原页保护；没有改游戏函数代码。
- 一个进程最多一个发布所有者，桥和所有者所在模块钉住；两代 completion adapter 共享同一个 Title 来源，不重新配置桥，不重置一次性状态。
- 发布前停止、adapter 已停止、指令变化、虚表变化或页保护变化均拒绝发布。发布后发现竞争指针只报告错误，不覆盖别人的指针。
- `Stop()` 只关掉尚未开始的发布；已发布来源保持常驻。停止某一代观察仍由该代 adapter 处理。没有声称回调已排空，没有危险卸载或自动拆钩子。

`Report.published` 记录本所有者曾成功发布，不是任意时刻的所有权保证；使用时必须同时检查 `verified` 和 `error==None`。`parentSourcesInstalled`、`titleStartsInstalled`、`fullInputHold`、`roomReady`、`gameValidated` 均继续为 false。

## 自有进程验证

命令（私有输入路径须在本机自行配置）：

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\san14-private\mod_research'
py -3 work/mod_research/b_reload_title_source_test.py
```

需要原研究私有 `checkpoint_task_completion_profile.h`、相关生成头、运行时归档镜像及既有 fixture 存档字节输入。脚本核对已知哈希，仅从私有目录读取；不复制生成头到仓库，不扫描或打开运行中的游戏。没有这些输入会明确失败，不能声称新电脑开箱即用。

测试只在被 ignore 的运行目录生成冻结 fixture 的明确后继，转换前校验文本锚点。Title 调用改为读取 `[this]` 的 vtable，再间接调用 `[vtable+0x28]`，不直接调用桥。第二代模拟 world 重建会跳过已发布的整个 Title 虚表页，不重写或重新发布该页。实际执行归档 Title.Update 指令、Win64 FINALLY 及三处 join 的硬件上下文记录；原生游戏业务服务、父任务来源和 Title worker 创建/启动仍为显式替身。

最终 **12/12 用例通过**，生产所有者及冻结 completion 对象在无 fixture 宏情况下编译通过：

- 4 个正常两代流程：正常、复用全部历史地址、迟到的旧任务、Title 尚未完成分支。
- 2 个两代异常流程：第一代 Title 原生异常或观察器 Stop，第二代仍由原常驻来源处理；拒绝伪造第一代成功收尾。
- 6 个来源拒绝流程：发布前 Stop、槽位变化、代码变化、虚表可写、adapter 停止、发布后的竞争指针。

所有原始源码和私有输入哈希保持不变；两个 fixture 文件副本保持原样。正常调用与 FINALLY 配对，异常正常传播，硬件断点恢复，无桥 cleanup fault。

最终私有记录：`b_reload_title_source_runs/20261008-013449-575217/result.json`。

| 项目 | SHA256 |
| --- | --- |
| result.json | `120179ce6bf3bcd976186d4eff825f77941affaaaf800803692568e0d646284f` |
| 生产 Owner 对象 | `6f8a574b502522c74784b8aa2d4a98c21f4340022979262d5680275064715117` |
| 生产 completion 对象 | `25a305cf120d1cafb08b1ff5f2e0a81845ca689e73e89c7369477ae75af2c280` |
| fixture.exe | `98689dde92e8acc0a02d1638069b48f8c5843c0641107fcdb0bd1f6fbd560a9f` |

首轮 `20261008-013142-164737` 保留为 FAIL：测试错误地把异常/Stop 分支也要求为 4 次 Title 调用，实际第一代 1 次、第二代 2 次，共 3 次。原生异常传播及 FINALLY 没有失败。后继按各分支明确要求 3/4/5 次，不放宽为任意调用数。中间通过记录保留；最终记录对应当前源码和不会重写来源页的 fixture。

## 精确剩余缺口

**这补上了一个实际来源的生产发布代码，不代表真实游戏已连续读档两次。** 生产代码仅编译，实际 CAS/派发在自有进程执行。

1. 父调度任务的真实 fresh/resume/完成来源（`50B4B3`、`50B598`、`50B4AE`、`50B632` 等）仍未全部安装；fixture 仍显式提供这些上下文。
2. Load Finalize 到 Title 的 `4CC690` 回调尚缺生产来源捕获。
3. Title `+520` / `+590` worker 创建与 `834B60` 启动，仍需生产捕获与角色对应的自动 runner 激活。当前 fixture 显式启动 `checkpoint_task_completion_worker_ports::Begin`；本模块不覆盖它。
4. 六处原有来源、此 Title 来源、每代 Session/Provider 的配置、房间授权与完整输入排除仍需由可信运行所有者组合；本模块不发起读档，也不自动放行 Ready。
5. 读档前撤回绑定旧 world 的双人规则，换 world 后重新绑定；连续两份不同真实存档的同进程验证、B 势力及最终世界核验、等待画面仍待完成。

下一步优先补 Title worker 真实创建/启动及自动激活，或父调度来源，不要再把测试中的 `provider.Observe` 替身算作已安装。无需用户操作即可继续开发和自有进程验证；本轮无活动游戏补丁或调试器。
