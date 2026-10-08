# 双人规则跨 world 生命周期

2026-10-08。本轮只操作明确创建的自有进程、其自有 MEM_IMAGE 和私有归档输入，未访问游戏、Steam 或实际存档。没有等待用户操作、没有在游戏中安装补丁。12 个离线场景通过；这不是 SAN14 真读档或双游戏联机证明。

## 新增文件与用途

- `human_rules_world_lifecycle.py`：可信本机编排及 `ResidentPort`，复用既有外部发布器恢复/安装协议；用当前读取器独立核对原生配置、六来源完整字节和两个活动计数，不接受网络回执作为原生来源。
- `human_rules_world_lifecycle_fixture.cpp`：一个自有进程、两个不同文件路径的独立驻留规则 DLL 实例。复用冻结 target 的内存/原生调用帮助函数，没有调用旧 main，没有修改旧源码。
- `human_rules_world_lifecycle_test.py`：明确私有输入构建，实际运行旧 `human_rules_activation_publish_v2.cpp` 发布器并使用独立 `ReadProcessMemory` 读取；原生来源安装/恢复使用真正的 OS 调试事件。

旧代码没有 reset 或 rebind API。`HumanRulesActivationPrepare` 只接受一次，底层 AI/收入适配器也是不可变配置。新世界使用**新模块地址、新 nonce、独立静态数据**，旧 DLL/跳板固定驻留、不卸载。当前工具拒绝所有历史 module 地址或 nonce 再次出现，不能只拒绝上一代。

## 正常撤回不是 Revoke

`HumanRulesActivationRevoke` 会将状态永久改为 Faulted；随后调用会永久保留，恢复方式是进程重启。先 Revoke 再尝试正常 restore 会被既有发布器拒绝，不能当作普通“暂停规则”。

正常流程是：在可信的业务/输入排他范围内调用旧发布器 `restore`，它在尚未继续的调试事件下校验六来源、线程上下文和原生 active 计数、恢复完整来源并解除调试器。编排再独立读取六处原字节、Sealed 配置、AI/income active=0；全部通过才调用加载端口。旧配置仍保持不可变，模块只是从来源上退休。

调用入口只收 `NextWorldRequest(generation, checkpoint, epoch, year, month, day)`，**不要求事先知道新 root/world 地址或完整 Config**。恢复后依次调用 `load(request)`、`observe_loaded(request)`；可信观察器在加载完成后采样新指针和 Config。编排核对目标代际、检查点、epoch/日期以及稳定的进程/游戏/房间/玩家身份/设置，才调用 `prepare(observed_world)`。

随后使用新的模块 Prepare/Seal，由旧发布器 `install` 发布六来源，再次读取实际 replacement 字节、当前绑定和 active=0，才返回 `RULES_REBOUND`。新 root/world 地址允许由加载后读取器决定，不能从旧地址推测。结果始终 `ready=false`、`full_world_verified=false`，不会释放外部排他范围。

恢复允许同一 world 的日期正常向前推进，例如原绑定 8 月 11 日，到 8 月 21 日才恢复；world 指针、房间、势力、设置等其他绑定仍逐项一致。新安装必须精确匹配新日期，不借恢复时的宽容跳过新代检查。

## 可信端口与必须遵守的调用方式

`NextWorldRequest` 是不含原生地址的逻辑加载目标。加载后才取得的 `WorldGeneration` 绑定本机递增代际、检查点摘要和完整 136 字节原生 Config。`ModuleIdentity` 绑定 PID/birth、module、descriptor、nonce、DLL 摘要，以及由固定 DLL 导出的计数器指令/地址 profile。

`ResidentPort` 的依赖只能由保留本机进程/模块所有权的安装器构造：

- `identity_check`：核对存活进程句柄、PID/birth、文件和已映射模块身份。不是读取对端 JSON 的字段。
- `read`：该进程的实际精确字节读取器。
- `publisher`：调用已批准的原发布器，固定此 PID/birth、descriptor、nonce、DLL 和 Config 文件。不能只返回一个“成功”字典。独立字节复核可以识别假成功，但不能代替发布器的调试事件与线程检查。
- `export_current`：用当前原生读取器生成 Config，生产接线可复用 `human_rules_activation_room.export_config`；不返回缓存配置。该函数不是完整世界校验器。
- `observe_loaded`：仅在 load 返回之后，从可信原生来源取得新 root/world 和当前 Config；返回 `WorldGeneration`。代际/检查点标签绑定当前已消费的请求，不由对端 JSON 自证；只改标签而保留旧 epoch/日期会在新模块 Prepare 之前被拒绝。
- `check_scope`：使用现有 `require_current` 等逻辑核对实际 Room 及双方认证绑定。调用者必须在整个替换过程保留 Room scope 的锁/所有权和外部排他范围，不能只间歇读一个 epoch。测试内 Room scope 明确是 MODEL。
- `guard_check`：证明从恢复前、加载中直到重新安装后的游戏执行/输入排他仍有效。本模块不安装此排他设施；只暂停 Room 协议不满足要求。
- `on_hold`：保留排他、撤销网络放行等故障收尾。异常或错误返回会单独记入 `hold_error`，不能称为已经安全暂停。

所有 check/guard/hold/load 回调成功必须返回 **None**，失败必须抛异常，True/False 均拒绝。`observe_loaded` 返回 `WorldGeneration`，`prepare` 返回新的 `ResidentPort`；新实例由生产安装器先保留生命周期，即使 Prepare 失败也不能卸载。编排保留已返回的实例，失败后不自动再次加载、不重新安装旧 world、不改用 AI，也不放行 Ready。

`fence_released=false` 只表示本模块没有发出释放动作，不证明外部 fence 仍有效；特别是 `hold_error` 非空时，操作者必须处理真实端口故障。原发布器如保留未决调试事件，不能杀发布器或目标来冒充收尾。

## 已执行验证

```powershell
py -3 work/mod_research/human_rules_world_lifecycle_test.py --fixture-root <本机私有研究输入目录>
```

当前输入仍使用私有目录内固定归档 `human_rules_stage_debug_rollback_runs/20261007-214414-327573/inputs` 的自有 PE 与运行时 image，以及 `python_deps` 中的 capstone/pefile。这不是任意电脑可直接构建的发行包；缺文件会失败并保留运行记录，不扫描游戏或生成伪输入。

最终结果：`human_rules_world_lifecycle_runs/20261008-100221-226218/result.json`，12/12 PASS、0 skip、sources_unchanged=true。结果 SHA-256：`2061b5b4dff4b4e73f6d27db8cff30e375c4df3795284d65579ef547717f7b87`。

主链中两个模块在同一进程，实际 world 从 `0x71000000` 换到自有 `0x76000000`；四次安装/恢复均 written_mask=63，每次检查 3 个线程，debugger detached。每代实际 AI 入口调用 8 次，其中人类绕过 4 次；收入判断 6 次。最后两实例 active=0，所有来源为原字节，自有进程自然退出。仅称为**自有世界内存替换**，不是游戏 LoadFinalize 或真实存档加载。

自有目标也拆为 `n`（只替换 world，尚不准备新模块）和 `p`（观察后才 Prepare）；Python 不含目标 world 地址常量。报告明确记录加载完成 → 实际 RPM 采样新指针 → 新模块准备的顺序。新增反例在真正换内存世界后返回旧观察，验证新模块 Prepare 根本不会被调用。

反例覆盖实际 active=1 阻止恢复/加载、假 restore 成功回执但来源未恢复、新 world 读取器仍返回旧状态、同实例复用、旧代请求、实际新安装完成后异常、恢复后 fence 丢失、False 回调/加载结果，以及 hold 失败可见。第三代重用第一代地址的反例只有编排候选是 MODEL；只实际加载两个 DLL，未声称三次真加载。

早期运行 `20261008-095449-806775` 为 8/8、`20261008-095607-191184` 为 10/10、`20261008-095654-662393` 为 11/11。通过后根据独立审阅增加历史实例复用、严格回调语义，并修正“调用前预知新 world 地址”的不适用 API。旧 11 项通过不能证明真实加载后地址发现，只有最新 12 项覆盖后采样时序。记录均保留，没有被覆盖；本轮未出现失败测试，但审阅发现的设计缺口按上述修正记录。

## 仍缺的生产接线

1. 游戏中可信、完整的执行/输入排他端口。当前 fixture 的主线程停在命令读取循环，不能拿它证明实际游戏所有路径已锁。
2. 正式安装器向 `ResidentPort` 提供已固定的原生 process/module/file 身份与生产 publisher profile，并在 Room 锁下连接真实 `export_config/require_current`。当前实际 publisher 执行只针对自有 fixture；未创建新的实机安装入口。
3. B 加载端口的父任务/worker/finalize 完成证据。`load` 成功返回本身不是世界就绪证明，必须再走当前原生读取和新代发布；本轮没有真 SAN 文件加载。
4. 更长会话的新模块实例策略。当前方法明确保留旧模块，两个实例已验证；没有无限代际资源上界或模块回收方案，不能擅自改成卸载/reset。
5. 完整世界、本方权限/菜单、命令排空和两端 Ready 的独立验证与房间协调，最后才安排双机连续旬测试。
