# Retained production rules factory

本后继新增 `b_warm_rules_factory.py`、`b_warm_rules_factory_test.py`、`b_warm_rules_factory_fixture.inc`。不改冻结旧模块，不运行游戏、Steam、UI 或旧 live launcher。

## 本轮实际接通

`RulesFactory.prepare_rules(observed) -> ResidentPort` 接受真实 `RulesWorldCapture`、它同一个 reader 对应的已保留 ProcessAPI、显式批准构建和私有记录目录。它现在真正执行：

1. 核批准 DLL/发布器、实际进程 EXE/PID/creation time、无 debugger、当前 Room/设置与 held 边界，重新采样 Config 等于传入 WorldGeneration。
2. 新代目录及持久 claim；独立路径复制规则 DLL。实际远程 LoadLibraryW，按确切路径查找模块并核磁盘/内存 PE 身份。x64 的 LoadLibrary 线程退出码仅为 DWORD，模块身份不靠截断的返回值判定。
3. 真实一次 `HumanRulesActivationPrepare`，核 native descriptor/绑定/PID/birth/module/nonce/fixture 身份；再次核当前 Config。
4. 真实一次 `HumanRulesActivationSeal`；创建完整 ModuleIdentity，并返回带实际 RPM、当前身份、RulesWorldCapture.export_current 和外部 publisher 的原 `ResidentPort`。返回前实际 `observe(False)` 必须证明 Sealed、六来源仍原样、两个真实 active counter 为零。
5. 调用者的原 `WorldLifecycle` / `BootstrapRulesBridge` 调 `port.install()`；publisher 实际运行原六来源事务、持有初始 CREATE_PROCESS debug 事件核验/发布/解除。之后 `port.restore()` 仍走同一个外部发布器和原 ResidentPort 前后实读。

工厂不自行 install，因此可以直接作为 `prepare_rules=` 回调；它不是只返回字典的许可端点，也不自动开始推进或设置 Ready。

```python
capture = RulesWorldCapture(reader, room, settings,
    pid=pid, birth=birth, read_birth=lambda: process_birth(reader),
    guard_check=trusted_native_fence_check)
factory = RulesFactory(capture, retained_api,
    RulesBuild(approved_stage_path, approved_publisher_path),
    private_records, rulers={12: 666, 2: 952})

# 生命周期在旧规则已恢复、新world已观察之后调用：
new_port = factory.prepare_rules(observed_world_generation)
```

`RulesBuild` 的生产模式仅接受既有已批准 stage `29d0f6e8...`、publisher `3f321110...`、支持 EXE `42d53bb4...` 和固定两组 counter anchors；路径由本机传入，没有历史 PID 或自动进程发现。明确 `OWNED_FIXTURE` 构建另绑定自有 EXE/stage/publisher 的精确哈希，不把 fixture 模式冒充生产 DLL。工厂接受外部已有 API，但不负责关闭它；调用者须保留进程所有者生命周期。

## 失败与收尾契约

- 每代 claim、LoadLibrary/Prepare/Seal 意图和结果、publisher 意图/PID/完整日志都独立保留。相同 generation 或已存在目录不能重用；不重置 DLL once。
- 已进入 Prepare 的拒绝会锁住整个工厂。未知远程线程、未知 publisher 也使所有后续目标调用被拒绝。没有自动 Revoke、Stop、卸载或强杀。
- publisher 的 uncertain 在 Popen **之前**保守置位；只有实际退出且报告 detached=true、uncertain=false 才清除。创建后日志写入异常也不能被误记成已知结束。
- 正常序列必须由生命周期先恢复旧六来源，再读档/换 world，再准备新规则。不要提前为仍装着旧规则的 world 准备下一代后指望异常时自动撤旧。`factory.failed` 后也不开放普通 restore：这是明确保留与人工诊断状态，不是宣称恢复成功。
- 如果 native publication 未知，保留 factory 中的 child 对象及记录，不结束持有未决事件的 publisher。旧规则代码驻留到进程正常结束。

## 执行证据

本机复核入口：

```powershell
py -3 work/mod_research/b_warm_rules_factory_test.py
```

这会编译并运行自有测试宿主，需要 Visual Studio 2022 C++、Python 依赖及前驱 `human_rules_world_lifecycle` 的归档私有构建输入，还核对原机已批准的生产 DLL/发布器文件；不自动发现或访问游戏。另一台电脑缺少这些输入时应先按测试中的固定清单重建本机证据，不能复制结果 JSON 放行。

最终私有结果：
`work/mod_research/b_warm_rules_factory_runs/20261009-193128-959554/result.json`

SHA256：`fadd653391d377f5ffe64752c9660a257bf87dd9a1eae80488918604c20a21c6`

最终 65 sources、45 private inputs、10 generated、14 binaries、46 artifacts 全部哈希复核匹配。artifacts 包含每代嵌套 claim/prepared/Prepare/Seal/publisher/held JSON，不只终端输出。生产两产物也检查真实磁盘 SHA；本轮没有将生产 DLL 加入自有宿主。

源码：

- factory.py：`c48cbd2868cc05b9c1aec1d2e2e987d8528a6e975edad385a9be3f2f9fdf5a10`
- test.py：`49a7f6fd5dd405b5382cbe78d48d343393ea6682adf41edbc2028287765e5cc2`
- fixture.inc：`5bc8e828aa26181a0da8a3b33248cf66b46e1653ea6c234613748169e06d21f3`

实际成功场景：一个自有 Windows 进程，同一原六来源，两独立规则 DLL；Python 工厂亲自远程加载、Prepare、Seal，而非宿主代劳。每代实际 install → 8 次 AI 入口（4 次人类跳过、4 次原逻辑）和 6 次收入入口 → restore，active=0；第一代 viewer12，第二代 viewer2 且 world 地址改变。两个 DLL 地址不同，各自 native nonce、epoch、Config 保留。4 个真实 publisher 全部 detached、正常退出；自有宿主确认原来源恢复后正常 q 退出0，无存活自有线程/发布器需处理。

实际拒绝场景：自有宿主将 User phase 改为非 idle，但只读 world 捕获仍能通过；真正 Native Prepare 拒绝，返回13、State=Rejected(5)。工厂保存失败并拒绝重试，没有 Seal 或 publisher；模块不卸载，宿主正常退出0。

窄异常场景：成功链全部恢复后，替身 Popen 返回一个 fake child，再令 process.json 写入抛错。验证 factory.uncertain 和 held 被保留、fake child 被保留、未 wait/kill。该异常场景没有启动真正 OS publisher/调试器，不把它冒充真实超时注入。

### 业务与环境替身

自有宿主继续使用冻结规则 fixture 的归档指令和完整 resolver/guard/发布器。其 stage 是原 activation_v2.cpp 的既有 fixture 编译：只在自有 MEM_IMAGE 类型查询处做已声明的 MEM_PRIVATE 翻译；外部 publisher 使用真实 OS query，按新自有 EXE 哈希编译。宿主原生业务体、世界和规划对象为明确自有数据，换世界是宿主复制构造，**没有调用真正游戏读档**。

本轮 Reader 使用真实 ReadProcessMemory；snapshot/类型读取适配的是自有环境，不是真正 GameReader 的全游戏语义。冻结 fixture 的君主编号等于势力编号12/2，因此传入的 fixture ruler 为12/2，不伪报真实张鲁666/刘备952。实际生产 ruler 参数仍必须由真实视角/Profile提供。测试主线程等明确命令，作为自有执行边界；这不证明游戏上的完整输入/执行 fence 已实现。

### 保留失败

- `192738-816859`：首次实际捕获因误用真实君主666/952而被 owned 数据12/2拒绝；无 DLL 准备/发布，宿主正常退出0。
- `192828-142115`：两代成功链实际完成；负例测试误把 Rejected 状态5断言为 Faulted6，总结果失败。修的是测试断言，生产拒绝仍为13。两个宿主均正常退出0。
- `193040-805238`：全部执行通过的中间记录；最终仅补齐嵌套 JSON 产物 pins，再跑 `193128-959554`。未删改旧记录。

## 仍未证明的部分

这个工厂关闭了规则生产准备接口缺口，可与已实现的初次身份切换和普通 WorldLifecycle 接线；它没有把这些组件与真实游戏 warm load、真正 Room 的 native fence 联合运行。仍需要 fresh 实机在可信输入/执行等待边界下验证 A 新档、B 两份合法档、规则恢复/重装完整流程。正式首代 Journal/Projection 后继由 root 的独立模块处理，不属于此工厂的权限。
