# B 冷等待、原登记与完整两代队列接同一 Bootstrap

2026-10-09。明确后继于 [原登记组合](b_reload_cold_registration_handoff.md)和[同PE两代queue](b_reload_bootstrap_queue_runtime_handoff.md)。仅新增 `b_reload_cold_bootstrap*`，冻结前驱未修改；全程自建进程、DLL、线程和已有私有归档，未访问游戏、Steam、当前存档或UI。生成源码、profile、产物与原始记录全部放在仓库外，没有待用户操作。

## 实际接通的链路

同一主PE、DLL、Provider通过自有loader停在主入口，调用新Bootstrap；新Bootstrap只把唯一 `lifecycle::Initialize` 换为 `cold_registration::Prepare(config,policy)`，由Prepare完成那一次原生命周期初始化。其余主线程、完整线程集、原字节、主PE、空池、模块固定、发布、Arm及恢复检查保留。没有先Prepare再调用会重复Initialize的旧Bootstrap，没有重置once。

主入口恢复后，实际归档初始化器创建四个worker；真实Bridge owner中调用冷等待协调，随后**真实调用冻结生产RegisterColdPool一次**，由原函数独立复核并发布四个worker入口。新Runtime的OpenFirst同时核对登记报告的base、Provider地址、一次尝试/一次原登记、四个准确初始wait，才允许打开第一代窗口。

之后，同一Provider和worker执行两代实际Session/Input/queue，第一代完成后经原Gate::RegisterAndOpen进入第二代；旧回执保留。没有重映射主程序、重新发布初始化入口、重新创建Provider或重新初始化pool。两个完整场景均执行16个Root任务、48次真实上下文捕获、两次queue pop/Finalize、两次窗口退休，以及四个outer FINALLY。

## 构造等待已移除，但启动排他仍有边界

实际初始化器所用的 `lifecycleCtor` 已删除“Resume后等initial事件”的主动等待，改为恢复线程直接返回。四线程使用同一个自有启动wrapper，再进入原来的归档ThreadEntry；协调器核对该真实起始地址及线程/对象身份。

自有helper实际持住manager临界区200ms，使四worker暂时停在已审ThreadEntry前链；协调器读取实际CONTEXT，先看到pending，后看到四个准确初始wait，最后由原RegisterColdPool再验证。最后一个构造保留30ms的诊断调度让步，让worker有机会进入前链；**该Sleep不是就绪证明**。仍未覆盖尚在CRT/包装入口、根本还没进入已审ThreadEntry的上下文；遇到它继续拒绝，不把任意位置当pending。

producer SRW和taskStarts只体现这个自有启动宿主的协议。本轮没有证明游戏所有任务生产者都遵守同一锁，也没有把后续两代queue每个生产者都改造到这把锁。因此这是接通启动协调，不是完整全局调度隔离。

## 显式诊断服务过渡

冷等待后继要求SetEvent槽是准确系统函数。旧queue fixture的SetEvent替身还承担completion和父队列记账，因此新fixture在**Bootstrap准备、初始等待及原登记全过程保持真SetEvent**；登记成功、helper退出后，才把这个owned映像的SetEvent槽切到原queue诊断服务，并恢复只读保护。

这处过渡有显式注释、来源断言和结果标志，不能据此宣称整个运行中所有原生服务来源始终不变。Leave槽一直是原生产activation发布的精确Bridge，没有回退系统Leave、重发Publish或放宽cold_wait验证。初始化调用点、归档初始化器/ThreadEntry/Runner、Enter服务和Provider身份均在主函数返回后重新核对。

Wait服务仍是诊断信号服务最终调用OS等待；归档构造、引擎业务、地图数据和第二份文件也仍是fixture。第二文件是首份归档的诊断变体，不是两份合法新存档。

## 编译与执行证据

实际DLL里不带fixture宏的6个对象：新Bootstrap、新Runtime、cold_registration、其wait后继、callee重定向的lifecycle后继、冻结原activation。callee后继只在自己的新TU里将AFTER调用改为协调入口；原RegisterColdPool定义没有改名。不能把这6项描述成“整个DLL没有fixture”。

其余queue组件仍使用冻结DEFS，observer仍沿用冻结别名；`b_reload_nested_root_ports`仍有明确的 `B_RELOAD_ROOT_WORKER_FIXTURE`，支持自有DLL输入前取址并省略该模块的Root页MEM_IMAGE限定。完整宏、别名及各对象哈希写在result。另4个production对象只是独立编译检查，不冒充实际执行路径。

沿用自有loader在第一次Bootstrap前有界等待额外本进程辅助线程自然退出的处理；观测到其入口位于ntdll不等于已证明线程来源。严格生产线程集检查不变；未重试消费过的Bootstrap，未单独终止该线程。loader只针对自身新建child。

最终原始目录位于仓库外：

`C:\Users\52708\Documents\Codex\2026-10-04\ni-li\work\mod_research\b_reload_cold_bootstrap_runs\20261009-092548-078626-d2cccb\result.json`

**2/2 PASS，inputs_unchanged=true**。179份来源、3份私有输入、8份生成文件、3份加载产物、6份实际对象及4份独立编译对象均已重核。首次完整运行即通过，本轮没有失败运行；未删除任何前驱的失败证据。

另一agent已独立重核上述全部身份，并确认去掉明确的include/namespace、policy形参和唯一Initialize→Prepare替换后，新Bootstrap函数体与冻结前驱逐字相同。result沿用旧字段名 `fixture_sha256`，其值对应 `owned queue.dll`；生成的 `fixture.cpp` 身份在 `generated` 字段，不要混淆。

| 场景 | 冷等待协调 | 原登记与队列 | 收尾 |
|---|---|---|---|
| success | pending48；暂停52/恢复52 | 原登记1，4worker；16Root/48捕获，2次pop | 4个FINALLY；78把实际CS平衡 |
| nested-input-yield | pending44；暂停48/恢复48 | 原登记1，4worker；16Root/48捕获，实际yield/恢复2次 | 4个FINALLY；86把实际CS平衡 |

暂停计数只属于协调器，不包含原RegisterColdPool随后自行执行的暂停/恢复。两场景均保留原来的普通无票任务每代一次、精确Load/Title join、前代报告不变和第二代Gate一次性验证。两次child退出码0、loader正常退出；worker/helper结束，无活动自建进程或调试器。非成功组合仍由冻结8场景原登记测试覆盖，本轮未重新合并全部故障矩阵。

Result SHA-256：`64f97e3661da9172d5ac9f48f99b67662f8b6c6079aa9d7a59454f0a38b856db`。

- `host.exe`：`cfc5e11a3c189fa2b232f981bdc23cbeefc2d66a6a0536bf3914c1b5aadbe96f`
- `loader.exe`：`d0beb0e5830af7848d253592f79470adc1723b7d847440c3794214f28fff87d5`
- `owned queue.dll`：`a8c7e0a12de2c314c28cc0921f250cf801cead48b6023fed1044dace1015a3f7`

## 复跑与下一步

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<仓库外已有私有归档根目录>'
py -3 work/mod_research/b_reload_cold_bootstrap_test.py
```

测试要求私有归档根不在本仓库内，并在该根下面建立全新run。不会从游戏取得缺失归档、查找现有游戏进程或操作用户存档。

已经消除“Bootstrap用旧准备入口、冷等待另一个组件、完整queue又是另一条链”的接线断层。剩下的生产门槛是：真实来源就绪、CRT更早启动上下文的可审查范围、真实生产者排他、真实合法存档连续加载、规则/输入/world切换和完整地图核验，再接真实房间Ready。本轮不授予实机加载许可，也不改变首次双机仍需验证的结果门槛。
