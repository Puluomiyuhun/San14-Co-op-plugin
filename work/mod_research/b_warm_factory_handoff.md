# Warm 实际 Owner factory 与完整 attachment guards 组合

2026-10-09。未访问游戏进程、Steam存档或UI；只执行仓库外自有测试进程。旧源与旧once均未改，没有卸载驻留模块。

## 关闭的具体缺口

此前profile与同六槽组合直接初始化Owner的内部Session等对象，完整业务观察链有效，但没有执行生产Owner::configure那组回调接线。上一轮已经发现这个盲区曾漏掉planningGraph固定force2。

本轮`b_warm_factory_fixture.inc`先在自有内存准备合法环境，再调用实际`InstallCheckpointCompleteLiveOwner`。Immutable Profile先通过真实Capture建立（没有重置）；随后执行真实installBody→shape→configure→reserve durable install intent→ArmHooks。没有调用旧CompleteOwnerChainMain或手动Initialize内部Session，不修改观察器完成回执。

configure真实建立的各组回调全部保留：

- Session、Request、Bytes、Load、Identity与Planning调用Owner的真实guards。
- Queue Adapter直接使用真实QueueGuard与真实Controller授权，不用旧完整fixture的queueGuard回调替身。
- Storage Gate、Binding及Owner/ReadHook回调保持真实，调用实际module/file/header/端点校验和AttachmentOnly，未用storageValid=true代替。
- 真实请求Verify/CAS、Worker/Read及FINALLY、Load update/join、Title identity pair、重建User配对与原User AFTER退休恢复实际执行。

每个成功场景实际guards调用57次，全部接受：Session19、Request16、Bytes5、Load9、Identity6、Planning2；实际Storage Validations72。最终OwnerState2、InstallCalls1、Installed1、SessionState13、HooksRestored1、PlanningObserved1、GuardError0。ReadyAuthorized仍为0，不凭本轮测试发放全房间就绪许可。

## 后继与环境界限

`b_warm_factory_owner.cpp`是`b_warm_profile_owner.cpp`显式后继。所有新增映射只在既有`CHECKPOINT_COMPLETE_LIVE_OWNER_FIXTURE`条件内：自有真实ASM originals、User/Menu/Game/Update/Worker/Read调用者与Read父返回地址。生产宏关闭时没有增加配置字段、导出许可或替换验证回调，guard行为仍使用上一轮修复后的`b_warm_two_bank_guards.cpp`。

六个实际槽位保持不同真实地址：五个base+原RVA和storageVtable+8；自有ASM调用器通过六个地址分别取当前函数。原生菜单/加载/读取/身份初始化/世界构造仍为明确的业务替身，经过真实桥转发。Source fingerprints在自有模拟image中按既有fixture准备；caller是自有ASM，fixture宏仍替换对应原游戏地址/PE环境约束。不能将“完整真实guards被调用”表述成原游戏代码已经执行、所有生产模块映射已实机验证。

旧fixture文件仅复用环境构造、业务函数与ASM ABI；其中旧true回调与旧完整链入口虽仍编译，在本轮实际factory配置中没有使用。单次成功不是实际typed `InstallBWarmProfileOwner`远程入口测试：Profile先Capture，再调用其使用的同一个实际Owner Install。Root已有独立typed ABI检查，实机启动仍须从动态Profile入口装配。

## 最终验证

入口：`python work/mod_research/b_warm_factory_test.py`。

最终private `b_warm_factory_runs/20261009-172050-464741/result.json`，SHA256 `d08889ffb8cdbf517c141e8b3b2a8e05d38374008cd7833a041713fb48720499`。Schema family=`san14.b-warm-factory.v1`，result=PASS，factory_complete_passed=true，inputs_unchanged=true。79源码、7私有输入、6生成文件、61二进制/对象/导入库/导出表均已逐份重新核对一致。

三项实际独立自有进程：

1. target2，203-08-11/current12，真实factory加载链、规划观察、封存与六槽恢复成功。
2. target9，before204-09-01/current2，loaded204-09-11，source7→target9，完整真实factory与guards链同样成功。输入仍是末尾追加32诊断字节的业务测试数据，**不是第二份合法游戏档**。
3. Menu AFTER已通过后改变自有模拟image的一字节源码指纹。下一Game真实Guard::Image拒绝，request CAS0、无request intent、无退休seal。未回写、清除失败或重试旧once；自有进程退出清理整个测试环境。

全生产宏关闭DLL也从同一后继源码完整编译链接，路径在最终result的production_dll：`checkpoint_complete_live_owner_v2.dll`，SHA256 `c4b32383ff4b278a835277d4e36308d21b4169fce59083e2b275a65ef2d7650b`。该生产DLL未在本轮加载入游戏，不能用自有fixture EXE代替生产DLL给启动器使用。

保留失败：171738-915961真实Install与Queue授权已经成功，但环境映射漏了Session.fixtureDispatchCaller，Menu配对在进入Request guard前被拒绝（Session Request错误、CAS0）。补齐实际ASM返回地址映射后171842-726765首个完整成功。最终172050新增target9与实际source guard拒绝，并冻结全部来源；没有改生产caller限制。

## 后续最短路径

本轮关闭单bank factory接线盲区。Root可使用动态profile只读采集、staging及严格构建身份入口准备一次fresh实机诊断。仍必须重新建立当前进程/模块/槽位/对象/真实文件证据；不得照抄本轮模拟地址。两bank同六槽退休接管已在独立组合通过，但这里三个场景是三个进程，**尚未在同一进程执行两次完整factory Install**，更不是两份合法真实存档跨旬加载。

自有host与构建子进程均正常返回，没有遗留游戏补丁或调试器；源码、EOF与尾空白已冻结，根文档及提交由root整合。
