# A 本机运行宿主装配：生产编译完成，尚未发布到游戏

本轮把 parent adapter 交接中的 Runtime 准备步骤写成了实际 `a_save_local_runtime.{h,cpp}`，加独立生产编译/链接脚本。没有 publisher/launcher、游戏执行或测试保存，也没有修改冻结模块。

## 具体装配

`Runtime::Prepare(Config, Plans&)` 一次性复制当前 PID/birth/base、固定 root/world/cache/五 state、日期/势力/君主、native binding、planning binding、cached Steam storage binding、新文件与intent目录。核对本进程身份，建立真正 fresh Sampler、实际 Owner、Gate、ParentAdapter；返回 Gate 两处 inline、Parent 一处 call 和四个 vtable slot 的明确来源记录。它只准备，不安装来源。

Storage callback 由本 Runtime 内部提供，比较真实本机 PID/birth/main image/base/root/world/cache/date/君主和原 attachment，且不重入 Owner/Gate/Driver。外部 Config 不允许自行塞 checkOwner/checkOwnedReadBridge/owner；当前首版也不接另一个 owned read bridge。

Sampler 每次从真实内存取得 fresh span；Prepare 在安装线程只 Capture+Bind 验证结构，**不**把该线程上的 `manager.current==0` 当成正在执行 User，不在错误作用域调用 InspectCurrent 判空闲。实际 Controller 与保存许可检查仍在认证父边界里完成。

## 不能颠倒的发布顺序

1. Prepare 返回的来源计划仍为原始字节。
2. 外部发布器建立实际发布窗口后调用 `ArmOwner()`，这一步实际 CAS 发布 Save/User 两个 vtable slot，然后绑定仅只读的 planning/reward lane。此时 Gate inline 必须仍原样；否则冻结 Owner 的原始 User prefix 检查会拒绝。
3. 外部发布器发布 Gate 两处 inline 与 Parent 一处 call。Runtime 自己没有写这些来源。
4. `ArmPublishedSources()` 先 Gate.Arm（发布 Game/UI slots 并令规范化 User 源就绪），最后 Parent.Arm。发布器恢复正常帧后，**真实父 BEFORE**才初始化 Controller、Ready、Mailbox、Host；安装线程不调用这些初始化。
5. 通过 Snapshot 等到 `readyForControlledRequest`，`ConfigureTransport()` 才会把同一 Owner、真实邮箱执行端口和有限实验 admission 填入 IPC Config。它不打开 pipe、不创建服务线程，也不发送命令。

Prepare/Arm 是由一个可信本地发布器串行执行的生命周期操作，不支持并发重复初始化；所有对象和已公开回调必须驻留至进程退出，Runtime 析构明确禁止。Stop 停邮箱/父 admission/Owner，但不在调用线程释放 producer 锁，也不假称原生工作已排空。

## 没有新增赏赐业务

既有 Controller 的 lifecycle::fresh 需要一个已绑定的 reward lane，但这不等于执行赏赐。Runtime 的 `planningSample` 只提供真实 binding、pending spans、base/root/world/User/势力身份，以及既有校验要求的原生 reward 地址 `base+1D6DA0`。

Replay ctor/append/dtor/predicate、命令 capture、输入 buffers 都保持空；Runtime 无 Reward Submit 接口。既有正常初始化回执的 submitted/completed 是实际0，没有捏造已执行回执。IPC admission 只允许 generation1、当前period/date、固定势力/君主/room、cut0 的受控保存请求；完整文件名/一次性规则仍由冻结 Server/Driver 检查。没有开启自由下令、连续两旬或玩家赏赐同步。

## 必须链接的当前作用域后继

- `a_save_scoped_gate.cpp` 替代旧 Gate 实现。
- `a_save_scoped_input.cpp` 替代 empty_queue/旧 inspector。
- 追加 `a_save_native_input_scope.cpp` 和新版 ParentAdapter 的 `CurrentBoundary`。

原因来自本轮真实观察：父 BEFORE/AFTER manager.current 是0；Game作用域是Game地址，而旧fixture一直放User。新的特定作用域检查分别验证认证父控制窗口/明确Game桥，不改原生 manager，不泛化“current任意值都空闲”。这项动态组合由根/B agent独立完成，本 Runtime 构建只证明正确链接，不冒充运行证据。

## 生产编译证据

运行 `py -3 work/mod_research/a_save_local_runtime_build.py`。只在仓库外生成产物，不加载或运行生成 DLL。

最终外部 run：`a_save_local_runtime_build_runs/20261009-112329-697520`；**PASS**。

- result SHA256 `740ea4327fc52ad30fdd15a365ac2aa916407af2d85fcf01d46fb146e459a631`
- 77 个来源，31 个产物/对象，生成器与build/include、3个私有输入均记录身份；构建前后来源相同。
- DLL `5da295269d1f1117ccf012995b13747cf03ae2904dfce331d52868e5cab6cb07`
- runtime.obj `6fbb16ee9e49ed2bbf8ea12a6ccafa54b49ecc6729d2b99ff9c8442c29c6ea8b`

全部实际编译命令没有 fixture 宏；完整链接 scoped Gate/input/helper、Owner、Host、Parent、Sampler、IPC、Driver 与生产 reward 对象。已有 planning DLL/import library 是私有依赖，只用于链接，没有执行。

编译通过 `/W4 /WX`。链接有7条 LNK4217：冻结 Owner 把 RewardOwned API 声明为 dllimport，而本检查把 production_reward.obj 同DLL合入，MSVC linker接受并将引用解析到本地定义。没有隐去警告，也不把本产物称作已部署包。后续可让生产 reward 单独成DLL保持原import ABI；本轮没有改冻结API。Runtime C++类未提供外部DLL导出bootstrap，因此这不是可直接注入并启动的发行DLL。

保留失败 `112218-392347`：新scope helper把Span字段 `game.data`误写成函数调用，生产编译明确报错；该文件所有者改正后重新全编译通过。最初生成脚本的临时here-string转义错误没有运行任何编译/进程，该问题已在脚本落盘前修复。

## 尚欠的真正动作

需要实际 publisher/导出bootstrap 将这份 Runtime 配置和已验证来源安装到当前进程，再通过真实本地 IPC 提交一份新保存，观察原生 phase/worker/finalizer/User返回及文件，并保留旧档完整性检查。本轮没有这份新存档，不是实际联机成功。

当前受控新档实验不需要先静态遍历整个游戏所有writer，但必须诚实保留边界：producer锁仅协调本Runtime，未证明游戏所有writer参与；没有 full-input/full-writer 或正式房间可用许可。父16帧真实来源、准确的空vector和current作用域修复均已成为具体输入，应继续接真实保存，不再用外围模型数代替结果。
