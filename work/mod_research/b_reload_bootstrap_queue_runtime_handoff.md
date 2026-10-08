# B 同一 Bootstrap 所有者接两代队列

2026-10-09。明确后继 `b_reload_bootstrap_queue*`，冻结 Bootstrap、四 worker 和旧 queue 前驱均未编辑。全程仅新建自有测试进程、DLL及既有私有归档；未访问游戏、Steam、当前存档或 UI，无待用户游戏操作。

## 本次接通的实际链路

同一个主 PE/MEM_IMAGE、同一个 DLL、同一个 Provider，实际经过加载器暂停主入口、Bootstrap 初始化/发布/Arm、一次归档初始化器、四个真实冷 worker，随后执行两个完整的 Session/Input/Provider/queue 代次。每代八项 Root 任务和一项普通无票任务；两个代次使用同一已暖 worker，其余三个仍正常收尾。

两代各有实际输入硬件捕获、Load start/worker/join、Title520/590 start/worker/join、原生父调度器 queue pop/Finalize、身份回执、规划观察和 Provider window 关闭。末端核对16个 Root 任务、48次 Root 捕获、两次真实 queue pop、两个父窗口退休、四次 outer FINALLY；旧 Session、Provider 和 queue 回执不随新代修改。普通场景没有 Root yield；嵌套输入场景实际让出、父层恢复、输入租约恢复各两次。

新 Runtime 的首代注册要求本实例已成功 Bootstrap、相同主 PE、实际一次生命周期以及四个冷线程；第二代通过冻结 `Gate::RegisterAndOpen`，并提前拒绝另一主 PE。实际负例覆盖冷池前注册、未初始化的另一个 Runtime、未绑定完成来源的 OpenNext、异 PE 的下一代及重复注册。拒绝不清空旧报告，不重试已消耗 Gate。生产 Runtime 仍是可信串行宿主接口：Provider 引用提供给原生模块，Session/Input 对象由同 DLL 宿主创建并保持地址和生命期，Gate 保留真实前代来源；不是任意远端调用 API，也不是防止宿主绕过流程的隔离或全局调度锁。

## MEM_IMAGE 组合中解决的问题

- 新 host 不链接 CRT，将其人工区域放在 RVA 2000 起，覆盖归档 helper 的低 RVA；原 PE 头、host入口、导入表和真实系统展开表均独立。初始化调用点及完整原生范围在 Bootstrap 前准备，后续 world 仅更换明确的数据对象，未分配第二个程序映像，也没有逐页复制重置整个映像。
- 把22条人工执行范围放入 host 正式 `.pdata`，展开数据移到 RVA 2300000 区域。各准备函数调用 `RtlLookupFunctionEntry` 核对静态条目；不是返回成功但实际未被使用的动态表。
- 完整 DLL 导入后，观察到一个额外线程，其起始地址属于 ntdll。owned fixture 在首次 Bootstrap 前至多等待30秒让该线程自然退出；本机约30秒后退出。生产 Bootstrap 的完整线程集要求不变。没有挂起或终止该线程，也没有失败后重试 Bootstrap。具体是否为 loader/线程池线程仍为推断。生成的 owned loader 仅把相应内部等待限额改为45秒，外层120秒大于串行内部预算，冻结 loader未改。
- 主 PE 准备需要明确 RX/RW/RO，旧私有 fixture 恢复原 RW 保护的做法会被 Bootstrap 拒绝；本次改正确准备，不放宽来源校验。
- 真实系统 Enter/LeaveCriticalSection 需要真实构造的对象。除了2个全局锁、4个冷 worker 完成锁、6个 Load/Title 完成锁，父调度器、queue pop和yield恢复路径里跳过的占位 state 也访问各自完成锁，现全部初始化并登记。锁登记本身串行化；所有线程结束后逐一核递归数为0、可取得，再销毁。注册表启用分支仍使用原 fixture 的关闭标志，未宣传覆盖该分支。
- Runtime guards 的 owner_module 改为 `SessionGuard` 实际所在 DLL；不再沿用旧单 EXE fixture 的主模块身份。
- 保留主 PE 后，前代规划留下 cursor_enabled=1。正常菜单业务替身现在显式切回 cursor=0/controlPause=1，让严格 MenuAfter 检查观察实际内存；没有通过清整幅映像掩盖残留，也没有修改生产检查。

## 生产对象与 fixture 边界

`b_reload_bootstrap.cpp`、`b_reload_bootstrap_queue.cpp`、`b_reload_lifecycle.cpp`、`b_reload_lifecycle_activation.cpp` 在本次实际 DLL 中均无 fixture 宏。只能据此描述这四个执行对象，不能称整个 DLL 都是生产配置。

完整队列仍采用冻结 `checkpoint_task_completion_test.py::DEFS` 的诊断配置：人工物理入口槽、Session/输入离线激活、fixture caller、正常菜单和队列创建服务、文件读取/业务效果等仍是显式替身。observer claim 符号仍按原有连接映射。另仅 `b_reload_nested_root_ports` 保留 `B_RELOAD_ROOT_WORKER_FIXTURE`：允许输入的精确33字节块在 owned DLL汇编标签，而非主 PE固定 RVA；同时该宏不强制Root代码MEM_IMAGE，实际运行的Root来源仍为同主PE且受Bootstrap及来源核验。代码字节、RX保护、实际硬件上下文、绑定和嵌套寄存器租约检查仍执行。完整宏清单与执行对象身份见每次 result.json。

构造替身主动等待四个 worker 进入初始等待，不能证明真实构造器具备这个时序保证。第二个文件是归档副本的诊断变体，读写业务不是完整游戏反序列化，因而不代表两个合法新档已连续加载、全世界一致、地图呈现或 room Ready。未合并完整异常矩阵、外来 DR 事件、实际输入全覆盖、writer排空、规则跨 world 或网络发布。当前 Root任务容量仍64，未设计无限多旬。

## 复跑入口与证据

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机已有私有归档目录>'
py -3 work/mod_research/b_reload_bootstrap_queue_test.py
```

源输入缺失或哈希不符即停止，不会从运行游戏自动抓取。产物、完整归档和原始日志不提交。最终通过记录、源码/产物身份见本文末尾验证段；构建或执行失败的旧目录均保留。

最终记录：`b_reload_bootstrap_queue_runs/20261009-001829-293824-b86044/result.json`，**2/2 PASS，0 skips**。171份源输入、3份私有输入结束时身份不变；源码和产物又由另一 agent 独立重核。结果SHA256：`fc9c4b5d260a67f04f40e474753fecd648669fa040d72f6f28fc3b5d7dc5df43`。

普通场景核验并销毁78个真实CS（12个任务/全局锁、66个占位锁）；嵌套yield场景86个（另有恢复路径占位锁）。两个自有host均返回0，loader确认 `target_exit=0` 后退出，四worker退出0且全部outer FINALLY收尾；无活动自有worker或观察器，不存在本轮游戏补丁/调试器。

本地产物SHA256：

- `host.exe`：`c97ad1edbbf15e8686a52f0592fce9efd6557d8bda0dee4bc6d2da405276e0fe`。
- `loader.exe`：`251d9efe87ab47789901c5b31d7ebb46d65894c412835da18c6895be99948ef0`。
- `owned queue.dll`：`4374354df621a2e40d7eca2129f7868a6b0fd4401c4f32cbe343035286e6a4b7`。
- DLL实际链接的无fixture宏 `b_reload_bootstrap.obj`：`a58f4d5985476dfea4297701fd7796536f9b29f85112ced2550147ec4b17cb40`。
- 同配置 `b_reload_bootstrap_queue.obj`：`9e456bab54265e114ca61c91e2aca40364872114b775b4aa4cb9a65f26285233`。
- 同配置 `b_reload_lifecycle.obj`：`4918f73d00577d744eb2c7e54250f49e520652dcd4772c3e59a219685fbe0ece`。
- 同配置 `b_reload_lifecycle_activation.obj`：`e74ba513eb71469e5415301038dbe815e9200915bf8e85354342554387ba637e`。

另编译的production对象只属于编译检查；上述四项才是本次真实加载DLL里使用的无fixture宏对象。没有宣称另外生成或启动了一个完整生产配置的queue DLL。

## 保留的失败

- `20261008-235018-452599-1a4b76`：Runtime内直接含析构删除的Gate，默认构造被C++删除；改保留一次分配的Gate对象。
- `20261008-235100-208134-bbd32d`：拆除旧独立桥/空同步后留下未使用fixture函数，/WX拒绝；明确标注未用旧probe辅助函数。
- `20261008-235202-789440-64f412`、`235341-803615-de147f`：静态展开表payload结束位置差1字节；按实际23字节tail修正，严格核验保留。
- `235449-634980-e49042`、`235620-551951-8cea2e`、`235717-397799-84a49b`：完整DLL加载后额外ntdll入口线程导致严格线程集拒绝；加入首次Bootstrap前owned-only自然退出等待。
- `235853-910444-336afc`：线程集通过，原Root准备函数留下RW页导致Source拒绝；改准备为RX。
- `20261009-000037-699350-644702`：Bootstrap通过，queue Adapter的运行时guard拒绝错误主EXE owner_module；改实际DLL来源。
- `000308-932786-37d2ea`、`000551-796323-115aea`：实际父调度器访问未构造的占位完成锁，ntdll访问异常；后者捕获真实回溯至50B495，补上真实CS。
- `000740-880095-71cc1d`：输入借用拒绝在DLL标签的预取地址；明确保留上述owned Root输入fixture宏，没有改冻结模块。
- `001127-027856-fc627d`、`001345-662444-d61270`：第一代正常链完成，第二代MenuAfter被cursor残留拒绝；嵌套yield恢复还遗漏一处占位CS。均补在相应owned业务/对象构造中。
- `001603-932671-17b4bf`：两种场景实际完成且退出0，但运行期间加入Runtime同PE/实例负例，`inputs_unchanged=false`，总体正确标记FAIL，不作为最终源身份的通过证据。

失败只涉及本次新建的自有进程。关键断言直接结束该自有进程；loader等候并收尾。未卸载固定驻留DLL或改写旧claim；没有操作游戏中的补丁或调试器。

## 下一步

保留同一Runtime/Provider和已完成的两代组合，优先处理真实来源就绪与冷等待协调，再接合法新存档、真实文件/世界/地图结果。单次Bootstrap在冷等待检查失败后仍是终态；不能用reset/retry冒充有界初始等待协调。随后合并实际故障矩阵和统一房间所有者。不要把本次fixture组合当作可发给朋友直接游玩的加载后端。
