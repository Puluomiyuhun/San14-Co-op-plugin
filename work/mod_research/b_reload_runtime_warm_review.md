# 连续加载是否必须冷启动：基于真实单次成功重新审查

2026-10-09。本轮只读源码与已保存证据，没有访问游戏进程、安装文件、Steam存档或UI，没有重投请求、重置once或运行队列fixture。结论：**引擎连续加载并不必然要求cold Bootstrap。cold是现有完整Root任务归属方案的前提，不是历史实际成功的warm加载路径前提。** 首个两次连续加载原型值得优先采用独立、永久驻留的代际bank，补明确postComplete退休，再切回原六槽；此文最初是设计审查；同轮已新增 b_warm_retire 后继完成自有进程的实际退休/六槽恢复，但尚未实机或第二份加载。

## 真实成功究竟证明了什么

私有 `checkpoint_complete_live_v2_runs/20261007-163447-239499/result.json` 的SHA256为 `4d5c166ee752463f3c7c40dc90f9b5249f0a683f3f239281bc2d3daf5e3ce1a1`。记录确为 `PASS_NATIVE_LOAD_IDENTITY_PLANNING`：Bytes Worker before/after/finally各1、读数匹配1、Load join/exactPop/receipt各1、Identity CAS/nativeReturn/receipt各1、PlanningObserved1。三个active计数均0。加载后重建User，PlanningUserReused0。

之后Stop成功，但SessionState10、HooksRestored0；旧六槽仍在，DLL保留。这是一次真实warm原生加载及身份/规划成功，明确full_world_verified=false、ready_authorized=false、scheduler_fence_proven=false。它既不是失败模型，也没有证明postComplete可撤回或下一次可以直接重跑。

旧 `checkpoint_complete_live_owner_v2.cpp:105–145` 配置User/Menu/Game/Load四个Update槽、公共callable槽和storage read槽。公共callable槽为 `base+138E8D0`，原函数 `4FABC0`；没有给四个池线程的object+38安装外层Root wrapper。

`checkpoint_cc_load_observer.cpp:72–87` 在真实callable回调检查payload `508B40`、caller `834D9B`、callable vtable及Load.worker+48精确指向，然后实际 `CheckpointLoadWorkerClaim`。`checkpoint_title_identity_adapter.cpp:93–110` 类似地检查payload `4DA390`和Title+520+48，并实际claim后提交身份pair。读回通过真实嵌套owner与文件hash。这些检查与已暖线程相容，已有实际成功证明，不能被后来cold路线的门槛倒写为“原先还不能加载”。

## cold为什么被引入，哪些可以推迟

`b_reload_lifecycle_handoff.md:13–17` 所述限制是真的：已经在834D10内部等待834DFD的worker，不会重新读取threadObject+38，所以无法靠改该字段补入外层Root FINALLY。因此**如果继续使用现Root任务票据/上下文观察方案**，必须在首次83A9D7前接入，不能把warm池伪装为cold。

但旧真实路径包装的是每项业务的callable vtable，不是已进入的worker runner。为首个受控两次加载实验，可以暂时推迟：PE入口source-ready观察、1447B6冷初始化发布、四worker初始wait协调、Root Leave-IAT激活、所有Root/yield票据的同Provider连续生命周期。这不等于删除这些模块；它们仍可服务以后更全面的任务归属和长时运行。

不能推迟：准确文件字节/身份转换、原生Load/Title完成与join、当前重建的规划world/状态、输入准入、已有自己的异步任务排空、来源归属/线程边界、停止和不确定态处理。warm后继不能把这些校验删掉来换取“第二次成功”。

## 旧版本为什么不能简单再调一次

1. `checkpoint_forward_native_session.cpp:15,41–44` 的Session初始化和物理bridge配置均为once；`checkpoint_complete_live_owner_v2.cpp:33–104` 是单个静态Owner，install自己也有once。不能清这些标记。
2. 同文件 `102–106` 的RestoreBeforeCommit明确在mayPublished后拒绝，真实成功当然已经发布过请求。`checkpoint_session_generation_owner.cpp:43–54` 也直接以Published拒绝postCAS换代；现two-bank组件只覆盖preCAS隔离。
3. `Session::Stop`（101）只停止新请求，不使完成后的观察器永久惰性。164–169仍依据mayPublished调用旧Bytes/Identity观察。旧Observer按payload匹配，第二次相同业务可能触发旧workerClaimed/identity claimed重复，或触及旧对象。不能在Stop后假设旧DLL已成为安全空壳。
4. 旧文件profile固定CC03、274880字节与单个hash（`checkpoint_cc_load_observer.h:11–13`）；旧identity代码 `checkpoint_title_identity_adapter.cpp:47–55` 固定203年8月11日、张鲁→刘备及具体军团关系。旧Owner.configure没有覆盖input boundary默认force12/date。第二次当前玩家已是刘备，故不只换target文件或nonce就能通过。
5. 新dynamic profile模块已经能表达独立文件/date/identity，但 `checkpoint_dynamic_native_session.cpp:51–58` 的离线Activate生产直接拒绝，且其观察器走persistent logical owner。不能仅改宏或调用离线入口绕过真实激活。可复用数据/校验算法，不应为了warm原型强行接回整个Root票据链。

## 最短可信warm后继

建议先只做两个独立bank、两份明确合法档，维持同一游戏进程；每bank拥有自己的不可重配Session/bridge/claim/intent。它可以是两个独立模块，也可以是同DLL中两组真正独立的编译符号与静态存储；前者更接近现有代码，不需要先做通用长期router。两份bank都永久驻留，保留第一份报告及来源描述。不是重复初始化旧Owner。

**第一小步：仅实现成功后RetireComplete，而不是直接发第二档。**

- 新独立后继的RetireComplete只接受原bank的完整Bytes+Load+Identity+重建Planning回执、精确attempt/filehash、无异常/无正在提交。只允许同一次完成后退休，失败不恢复旧once。
- 先关闭新admission并建立明确退休状态。已进入的真实bridge scope须按既有配对完成；退休后新进入的旧桥只透明调用原函数，不再读旧对象、再做身份CAS或改变已封存业务回执。物理计数仍保留，可继续诊断迟到的旧入口。
- 后继复用原 User BEFORE→original→AFTER 来源及实际 Planning observer，要求该次完成的 call/TID/attempt 和完整 Bytes/Load/Identity 回执一致。当前态是 User，不是 Parent0。其他业务与物理桥活动须为零，仅允许当前 User AFTER 本身；外部两次active0不能代替授权。
- 在该 User AFTER 末尾原子关闭旧观察准入，然后直接调用原 HookSet::RestoreAll，逐槽CAS hook→original并恢复原保护；这是指针槽，不要求外部全线程暂停。前提是本工具为槽及页保护的唯一写者。缓存旧函数指针仍可迟到，旧桥透明转发，DLL永远驻留；第三方改槽导致恢复失败时保持sealed/uncertain，禁止下一代。
- 新bank仅在该退休/来源恢复回执后采当前world、重建states、UI、rng、storage与新文件身份；第二份使用新的nonce/attempt/epoch和独立once。不能沿用第一次pre-load的指针或默认force12/date。

**第二小步：两份合法文件的有限profile和二代装配。** 可以先每份文件构建一份精确不可变profile（hash/size/date/保存势力/B身份），不必同时完成任意文件/任意房间协议。仍要显式替换硬编码旧年月日和当前势力字段，使用准确存储字节/原生关系核验；不能用诊断变体冒充第二合法存档。复用动态profile的数据表达是可行节省，物理warm Owner接口需单独接通。

**验收先后：** 第一bank实际加载成功→实机RetireComplete并恢复六槽→当前规划可读/无旧业务访问→第二bank实际安装并加载另一个合法档→第二份身份/规划/字节完成→再次退休。第一份错误、不确定或退休失败就停止，不继续装第二份。两次同文件重读若用来排查生命周期，只能叫生命周期试验，不能叫两个旬末新档已同步。

## 当前判断与最小开发项

静态分析没有发现迫使该有限warm方案先走cold Bootstrap的引擎级障碍；它比同Provider长期重绑少了启动解码阶段、池捕获和全Root/yield链。**新增后继把唯一 User AFTER 的业务退休与六槽恢复接到了真实组件；尚未证明全游戏异步活动停机，也未进行实机退休或第二次加载。**

本轮实现、产物及5个针对性场景见 `b_warm_retire_handoff.md`。下一步固定产物后验证真实第一档完成时的封存/六槽恢复，再接第二份独立文件profile和新驻留bank。若唯一完成边界仍有其他活动/异常，后继保留观察而不在下一帧仅凭active0重试；须读取诊断并停止，不把它说成自动等待后会成功。
