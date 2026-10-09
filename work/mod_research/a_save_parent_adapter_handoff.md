# A 真实父调用来源到保存宿主的适配器

本轮新增 `a_save_parent_adapter.{h,cpp}`，不再新增抽象邮箱模型。它准备 **13DC09→509FE0→13DC0E** 一处正常父调用的接入计划，复用冻结 `b_reload_parent_bridge.{h,cpp,asm}` 的四整数参数、完整 RAX/XMM0 返回和 SEH FINALLY。A 角色独占这组桥；没有引入 B 的 Provider、debug-register 四点或双重父来源。

## 已实现的实际入口

- `Adapter::Initialize(Config)` 仅校验固定来源、建立近跳 relay、配置桥，不调用保存、不初始化 Controller、不猜测游戏执行线程。
- `PreparedPlan()` 返回明确的五字节 before/after 及 relay；仍须由真实发布器在线程/指令指针检查下发布。`Arm()` 只检查已经发布的准确来源，没有 `all_threads_paused=true` 之类参数。
- 生产检查包括 CApp 函数 `13D9C0..13DD03` 的固定 SHA（只归一化自己的那五字节 call）、CApp 虚表 `+10` 指向、MEM_IMAGE/RX、目标 `509FE0` 原始前32字节固定指纹、relay 字节与绑定地址。小指纹来自既有固定归档；没有提交函数转储。
- 第一次认证父 BEFORE：实际 `RCX=base+19E7310`、返回 `13DC0E`、桥 call/token、当前 TID 都正确，才执行**具体** `Controller.Initialize/Request`、`Mailbox.Initialize`、`Host.Initialize`。这些操作不在安装线程或活动 User 回调内执行。
- 后续相同父线程 BEFORE/AFTER 分别调用 Host.BeforeFrame/AfterFrame；认证 call/TLS 深度、同线程和来源；FINALLY 成对收尾。
- `CurrentBoundary(base)` 仅实际初始化/Host.BeforeFrame 与 Host.AfterFrame 控制窗口为真，`__finally` 退出即清除；在原 scheduler 两任务间即使父 TLS 仍存在，也不被称为控制边界。
- 失败、Stop、错线程或异常不会跳过原 `509FE0`，不会强行解 producer 锁。已停止保存仍须继续正常原生帧；底层 Host 的真实终态 drain 负责在原宿主线程处理资源。异常未排空保留未知，不给成功回执。

这些是可链接的真实适配器接口，**本轮尚未安装进游戏**。Config 指向实际 Owner/Gate、Controller、Mailbox、Host、producer 锁和固定 planning identity；不是网络可任意传原生地址的接口。

## 有界验证

入口：`py -3 work/mod_research/a_save_parent_adapter_test.py`。

最终外部目录 `work/mod_research/a_save_parent_adapter_runs/20261009-112339-948964`；**2/2 PASS**。本轮三次窄范围运行均通过；后两次分别补源入口指纹及精确 CurrentBoundary 后重跑，没有扩大矩阵。result SHA256：`c7f0a599887e4b0b6b4e181e342cf1ce02e1b189586233de8dad8ef92e977047`。

74 来源、40 产物/对象、5 生成文件、3 私有输入均 pins 且前后未变。fixture EXE：`c4d76442d80c8ad864bb106c8ad87aef8ed1c54b11d13e410e898df84f070522`；无宏 adapter.obj：`72d0c8628720b657ce3cee413abf82d4ed71d934dea6ccd4f338d37014b05e05`。

原 Host 两例仅改为由自有映像中的准确 call/return 地址调用原 ABI 桥→新 Adapter→实际 Host/Controller；fixture 不再直接驱动 BeforeFrame/AfterFrame。检查安装时 Host 未初始化、真实父 BEFORE 初始化固定 TID、父 Before/After/Finally 配对、64 位返回保留。正常两期实际 Owner/Controller/IPC 提交和回包；已 bind 后仅关闭 pipe、客户端仍存活，继续 Save FINALLY 排空且 Unknown 不发包。使用本轮 `checkpoint_native_input_pending_empty_queue.cpp` 后继链接，现有 allocated 队列路径也一起实跑。

真实 CApp 整个函数、真实 scheduler/serializer、Steam 数据写入仍未执行；自有 parent call stub 与原生业务是替身。生产 adapter 编译通过；执行版本带唯一 `A_SAVE_PARENT_ADAPTER_FIXTURE` 源映像检查分支，以接受自有 MEM_PRIVATE call stub，实际桥、初始化、线程/作用域、Host 逻辑不替换。不要把它写成实际父 hook 已安装或全 DLL 生产已实测。

## 本轮新增的真实来源证据（由主 agent 执行）

私有 `a_save_parent_live_runs/20261009-111212-863846/result.json` SHA：`4bd9272db15065d208747b87eb77b085d68b801b0e80a9d21f3336831b90e09e`。本子 agent 仅只读审阅结果，没有触碰游戏。

主 agent 已连续记录 16 个真实父帧，固定 TID12864；5 个 state 共80个创建点及80个 tail，父前后 state+50 均0，tail done1/yield0/stateworker0。创建点 done1 可能是复用槽残留，不能单独解读为任务完成。观察器恢复调试寄存器并正常退出，后检张鲁203-08-11、无调试器。

这让当前闲置地图的真实父边界成为**已有实测来源**，不应再用同类 fixture 重复证明。它不是所有时期、所有未来任务或所有后台 writer 的排他证明，也不代表本 Adapter 已发布。

## 下一步实际运行装配，避免继续停在外围测试

1. 新 `A Runtime::Prepare`：用本轮主 agent 的 `a_save_local_binding::Sampler`、本机 storage bindings、当前进程身份及固定新目标目录，初始化真实 Owner、Gate 和 reward lane；保留同一实例，拿到 Gate 两处 inline 来源计划及本 Adapter 一处父来源计划。Owner 的存储 `Open` 是只读绑定，不调用原生保存。
2. 新本机发布器：当前进程、源字节、EXE/模块身份/保护、线程 RIP 覆盖检查后发布以上计划，Arm，并实际等父 BEFORE 上报 Host initialized。保留源码/二进制与这个进程 lifetime 的一次性证据。不能复用旧 PID/claim 或用远程线程直接硬调 scheduler/User。
3. 新受控单次请求入口：仅向这一实例的实际 IPC 提交一个全新 `mpXXXXXXXX.s14` 文件名和 durable intent；从原生 User AFTER 自然触发真实 Driver 的 `2FC750` binder、**正确 type0 `2DF990` queue**。原 `private_checkpoint_save_pilot` 的 `412520/type2` 永久退休，不能复活。
4. 实际核验：相同 User/world/date 返回、原生 Save phase0..4、worker start/join/finalizer、文件稳定可读及 SHA、原有所有存档不变、来源/活动作用域清理。这才关闭“A 真正生成一份新档”的结果门槛。然后同一保留 Owner 做第二份、再接 B 合法新档。

已有 `checkpoint_push_pilot`/`checkpoint_push_start.py` 可借鉴一次性 intent、正确 push/返回观测、既有存档比对，但启动器硬编码原电脑路径、旧历史产物与一次性目标，不应直接重跑或清除旧 claim。新 Runtime 应用现有 Driver 路径，不叠装那份旧 User hook。

**受控原型与生产承诺分开**：当前用户授权的闲置测试局、无手动下令/推进、新文件及恢复备份，可进行一次正常保存生命周期的实测；没有必要先完成整个游戏所有 writer 的静态闭包才能测试正常 native Save。这个实验只能声明本次成功/失败，不能发 full-input/all-writers/房间可用许可。跨帧 producer SRW 此时至多是本 Runtime 请求的协调锁，绝不能假称游戏线程都参与、把 Save 必需的后台任务锁死。生产无人值守保存还需明确实际输入/相关后台 writer 的协调合同；若这次出现异常，以 Unknown 收尾而不是重试或放宽字段。

本适配器没有安装器和 DLL 导出 bootstrap。同轮已新增 `a_save_local_runtime` 并完整生产编译链接，将上述第1步实际落代码（详见其handoff）；仍欠来源发布器/one-shot launcher 的真正装配。这是具体实现工作，不应再以增加模型数量替代。公共文档与提交由主 agent 处理。

同轮真实 current 语义修复另由根/B agent 验证：父 current0、Game currentGame、User currentUser 的区别由 scoped input/gate/helper 接口处理，不能把本ABI组合的旧User常驻fixture当作该项证据。根另只读核了实际CApp完整指纹与scheduler前32字节，两者匹配，记录 `a_save_parent_source_checks/20261009-112357-755908`；本Adapter仍未安装。
