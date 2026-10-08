# B 冷等待接原始 RegisterColdPool

2026-10-09。[冷等待组件](b_reload_cold_wait_handoff.md)的明确后继，只新增 `b_reload_cold_registration*`，冻结前驱均未修改。全程离线，只执行自建主 PE 和线程；未访问游戏、Steam、当前存档或 UI，无待用户操作。

## 这次真正接通了什么

同一主 PE/MEM_IMAGE、同一个 Provider、四个真实 Windows worker，实际执行新 Prepare → 原生命周期初始化 → 发布原生初始化调用点 → Arm/发布 activation IAT → 归档初始化器 → 原生 Bridge owner → 冷等待协调 → **冻结 activation.cpp 中的原生产 `RegisterColdPool`**。成功后原函数自己重新检查真实 owner、对象/线程/事件、CONTEXT和初始等待，再发布四个worker入口。收尾实际通过四个 activation outer FINALLY。

本轮没有使用远程 Bootstrap loader，也没有串联两代queue。Prepare是可信启动宿主的准备接口，发布/Arm在自有fixture中执行；它不是可以对已运行游戏随时调用的安装器。不能把本轮写成完整 Runtime 已接好、两份合法档已加载或双机可玩。

### 为什么需要两个明确后继

冻结生命周期 AFTER 直接调用 RegisterColdPool，没有注册前协调扩展点。新 `b_reload_cold_registration_lifecycle.cpp` 包含原文件，并且只在这个新编译对象内将 `RegisterColdPool` 名字改成 `CoordinatedRegisterColdPool`。其余生命周期检查与实现保持原样；**这是新对象，不能沿用旧对象哈希**。冻结 `b_reload_lifecycle_activation.cpp` 不改、不带此宏，它仍定义真实的原 RegisterColdPool。新wrapper的callback准确调用这个原函数，没有替换成成功bool。

另一个实际冲突是：Arm已经把LeaveCriticalSection IAT换成 `BReloadRootActivationBridge0`；上一cold_wait要求此槽仍为系统Leave，直接拼接一定拒绝。因此 `b_reload_cold_registration_wait.h/.cpp` 明确派生上一组件，仅修改这处来源契约：要求原activation快照 initialized/published、无错误/不确定、iatSlot匹配、original精确为系统Leave、replacement精确为该真实Bridge，槽内容必须等于replacement。不是允许任意IAT，也没有先恢复旧值再重发Publish claim。

Enter/SetEvent仍要求准确系统函数；Wait服务仍只核可执行MEM_IMAGE及本次固定身份，不保证该服务完整行为。所有线程/事件身份和CONTEXT检查、每次暂停成对恢复、截止及单次调用规则继承前驱，没有删减。

### 真实来源、一次性与失败

Prepare把同一base、Provider和协调策略放进唯一状态，并用这组Config初始化原生命周期；wrapper首先检查真实Bridge owner的slot/depth/token/call_id/thread和原caller返回地址，才派生四个pool对象并进入协调。无owner不能消耗原cold registration claim。

协调成功后先恢复四线程，仍持producer SRW排他调用原Register一次；该原函数再次独立暂停/验证/恢复并发布入口。本wrapper检查原统计coldPools=1、threads=4、initialWaitVerified=4、无错误/不确定。失败与成功都拒绝再次尝试，保留首次报告；不重置任一旧claim。

producer锁及taskStarts仍依赖真实宿主让所有生产者遵守；目前只覆盖自有测试宿主。也仍拒绝尚未进入已审ThreadEntry的未知CRT/包装入口上下文。本fixture在最后一个构造恢复线程后Sleep30ms，让线程有机会进入前链；另外的真实manager临界区保持阻挡到150ms。因此不是构造替身主动等到初始wait，但也**没有解决所有调度时序**。通过条件始终来自实际CONTEXT，Sleep不是许可。

期限是协作式预算而非硬实时保证；操作系统调用和callback可能超过预算。Resume失败仍为uncertain未知状态，不可继续，不可把其称为已恢复。本轮没有制造OS恢复失败，也没有测试原函数发布四worker到一半的故障。

## 复跑与测试范围

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机已有私有归档目录>'
py -3 work/mod_research/b_reload_cold_registration_test.py
```

仅使用已有固定runtime archive与私有profile，不会从游戏提取。所有实际链接对象无fixture编译宏；唯一明确callee宏仅存在新lifecycle TU中。宿主自身仍包含人工MEM_IMAGE准备、构造、cookie、CRT结束、Wait信号服务与业务替身，不能据“无fixture宏”宣称没有fixture。

8个场景：延迟后真实原登记成功；到期、来源字节漂移、已发布IAT漂移、提前任务、无owner均不调用原Register；Stop提前或期间发生会在协调到齐后调用原Register一次，并由原函数拒绝，原coldPools仍0。每个场景随后再次调用wrapper，验证它拒绝且旧报告逐字节不变。

成功场景原登记1次、原coldPools1、四个原initialWaitVerified、四个outer FINALLY；各场景四worker exit0、六把实际临界区平衡，所有辅助线程及自有进程正常退出。来源漂移测试只恢复本次自建映像里的诊断改动，不重置任何模块状态。没有活动游戏补丁、调试器或自有残留线程。

初版 `b_reload_cold_registration_runs/20261009-010328-486049/result.json` 为8/8成功；其后补足transitive Python导入来源pins和build脚本身份，最终结果见下方。没有删除任何中间运行或失败证据。

## 最终验证

最终运行：`b_reload_cold_registration_runs/20261009-010649-154425/result.json`，**8/8 PASS，inputs_unchanged=true**。147份来源、2份私有输入、5份生成profile、生成fixture与build脚本均记录身份；5份EXE/关键对象产物末端重核一致。

Result SHA-256：`7a72289d54b321d56f99cb3ed94304d87d981df383ccb5777fd8115c6acea41e`。

成功场景协调器40次暂停/40次恢复，34次pending观察后核准4个wait；原Register额外执行自己的生产暂停/恢复（不混入前述计数），登记一次、四worker全部发布/收尾。负例现在核对精确错误枚举：期限为Deadline；两种漂移为Source且必须已有pending；任务提前为TaskStarted且无暂停；无owner为Owner且未启动协调；两种Stop为Registration/Callback且协调已证4个wait，但原登记仍为0。不是只检查任意失败。

关键产物 SHA-256：

- `owned_registration.exe`：`6a4ad90a1b336012380cf20fb5931ca95320a03458cb8377e4a644f6beca5294`
- `b_reload_cold_registration.obj`：`7bd3ddf3c3be262e7b7618367564850fdc2d1bf122d9b19d06fcd0e068d2beca`
- `b_reload_cold_registration_wait.obj`：`5ff72061dd46e041cc99d735d1595ed64f5f4cb40d6b3c5bfec41f09d2c3ea2c`
- `b_reload_cold_registration_lifecycle.obj`：`daf1df1f845c8391d319f67e003e51c94eec248aa64120548ee8248b0a11ae5a`
- `b_reload_lifecycle_activation.obj`：`2e6eae219109737459a72bfed78bc7b13282cf8c1622a1217e60a5d093502580`

`010558-155247`为补足Python来源pins后的8/8成功；后续仅加强上述精确断言和结果字段，再全量跑成010649。所有运行保留。本组目前没有失败运行，不能把上一cold_wait的失败冒充这一组。

最终源/产物身份、单个末尾换行、行尾空格均已检查；逐个新文件运行 `git diff --no-index --check -- NUL <file>` 无空白诊断。没有修改冻结前驱，也没有复制旧claim。

另一agent独立只读复核147份来源与5份关键产物均一致，并核对已发布IAT身份后继、单callee重定向、真实Bridge owner与原登记调用，未见本次有界组合的新阻断；宿主排他、Wait行为、未知启动上下文和未接Bootstrap/queue等限制保留。

## 下一步

先将这个明确生命周期callee后继接入Bootstrap同Provider Runtime，验证完整启动来源、持续生产者排他及旧规则退出，再接两代queue。现在Prepare已直接初始化生命周期，不能再调用会第二次Initialize它的旧Bootstrap来硬拼；需要一个明确的Bootstrap调用准备后继，而非重置once字段。两合法存档、完整世界/输入与房间回执仍未由本轮验证。
