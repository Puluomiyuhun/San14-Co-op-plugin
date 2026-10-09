# Warm 两个驻留模块依次接管同六槽

2026-10-09。只运行自有进程，没有访问游戏进程、Steam存档或UI，没有重置旧once或卸载任何bank DLL。冻结前驱未改。

## 本轮实际改变

`b_warm_two_bank_owner.h/.cpp` 是可信本地host使用的有界交接检查。Bind接收六个独立槽地址（不要求游戏槽位连续）和稳定originals。AuthorizeSecond先从精确第一模块的真实导出读取Profile、Owner与Retire报告，核对Bytes/Load/Identity/Planning完成、同attempt与各call、file SHA、sealed/restored、全部六槽原指针和原保护及无错误/活动调用。第二模块须不同且未配置、未安装、未Stop、无Owner/Session错误；只发出一次许可。提前/停止候选拒绝不消费许可。

调用前host必须核准DLL文件身份并串行持有安装/槽位写者权限。本组件核MEM_IMAGE与精确AllocationBase、导出/桥归属，**不负责批准DLL hash，也不证明其他所有生产者遵守排他**。它不安装钩子，不提供跨线程通用事务锁，不能把一次检查当未来永久许可。

`b_warm_two_bank_fixture.cpp` 的host只有一个共享模拟image和一个只读六槽页。原函数、真实ASM调用者及返回地址均在host，两个独立DLL导入它们；每个DLL各自拥有原物理六桥、Session、Owner内部对象、Admission与immutable Profile，不把旧桥路由至新Session。只有明确的native业务替身由host选择当前bank。

第一bank执行菜单/请求校验与CAS、Worker/Read/Load/Title/新User实际观察链，配对User AFTER封存并真实HookSet::RestoreAll。host核真实完成后才允许第二bank在**同一槽页、同一originals、同一image**安装，第二bank再完成整条链与恢复。两bank均保持驻留。每代world/Load/Title等模拟业务对象可重建；没有清空、重新分配共享image或替换槽页。

第二bank已经arm、槽位确为第二bank桥时，缓存第一bank六入口各执行一次，参数为PAGE_NOACCESS内存。它们只进入稳定native originals；第一bank完整业务回执不变，第二bank六桥统计不变。原有每bank自身完成后的旧world保护/六入口迟到校验也保留。这个native original在专门迟到测试期间只计数返回，未调用任何bank的业务替身，不能据此声称任意真实游戏原函数能处理无效self。

## 生产目标势力遗漏修复

`b_warm_two_bank_guards.cpp` 是`b_warm_profile_guards.cpp`显式后继，唯一业务改变为planningGraph中的world+3A从固定2改为immutable profile.target.force。上一轮target9的成功链使用了fixture规划guard回调，并没有执行这个生产planningGraph，所以没有覆盖该生产缺陷；不能继续引用上一轮4/4作为完整生产guard已正确参数化的证明。

本轮将冻结旧planningGraph函数体原样重命名编入对照，再执行后继相同谓词：target9时旧谓词拒绝，后继接受；将world force临时改为错误值时后继拒绝；target2仍接受。`b_warm_two_bank_guard_fixture.inc`只为这项定向测试通过生成头公开Context私有成员，设置测试前提；它证明的是实际planningGraph谓词，**不是完整common/source/stamp链或生产factory安装**。生产DLL使用原私有头和无fixture宏的新guard TU另行完整编译链接。

## 组合限制与失败归因

组合继承此前明确的native菜单、磁盘读取、世界重建等业务替身以及环境guard回调。执行实际Session/桥/请求/观察器/硬件断点/worker/join/FINALLY/HookSet，但没有执行两次生产Owner::configure/Install全链。Owner导出读取的是这些实际内部对象的回执，fixture只补诊断attempt/epoch，不伪造完成回执。两个bank都是attempt17，跨bank的身份来自不同物理模块、独立Profile/Session/once；不是一个Provider内重置17号claim。

第二输入是在私有归档末尾追加32诊断字节的不同输入，日期/势力由native业务替身建立，**不是第二份已验证合法的游戏存档**。不能称两旬真实加载或两客户端联机已通过。

保留的运行：

- 165411：host多源编译误用了单文件/Fo，构建失败；改为正常多源对象输出。
- 165426：自有文件命名bank1.s14违反原Verify的basename约束，Request在CAS前拒绝；改成两个目录各自svdexccSC03.s14，没有放宽验证。
- 165627：第一bank已完整通过；第二bank共用image，保留上一代规划cursor=1，而旧孤立fixture依赖初始零内存。为明确native Menu业务替身增加进入菜单时cursor=0/controlPause=1转换，没有清整个image或绕过检查。
- 165800：同槽两bank与迟到入口首个完整成功。
- 165917：两链/生产编译成功，但构建期间源码迭代导致inputs_unchanged=false，整体保留FAIL，不作为新源身份通过证据。
- 170016：生产修复、同槽组合、旧谓词对照和停止候选拒绝全部通过；收尾发现前驱来源列表漏一个ASM include，下一最终运行补pin。

## 下一接点

Root已有profile-aware只读采集/typed包装与staging接口。还需在真实fresh本机阶段以当前完整模块、槽位/来源、对象和文件身份安装第一代，实际成功后按同六槽恢复回执允许第二代；两份真实合法文件、正确staging顺序与卸载禁止均不可省略。当前host替身的世界重建、菜单UI转换不能充当实机来源证据。

测试入口为`python work/mod_research/b_warm_two_bank_test.py`。依赖已pin的前驱私有生成fixture和私有归档；新机器须具备相应证据或重新生成，不可复制旧PID/地址/once。最终结果、源码/生成代码/二进制身份见下面追加段。

## 最终冻结记录

最终private `b_warm_two_bank_runs/20261009-170127-894275/result.json`，SHA256 `d75d16aa61b93b2c695fe3ad7100ec09a33ce521375177e800641b6d839756e2`。PASS，inputs_unchanged=true；81源码、8私有输入、9生成来源、66二进制/对象/导入库均已重新逐份核对一致，包含实际ASM的`checkpoint_native_input_prefetch_archived.inc`及本轮guard fixture来源。

生产全宏关闭DLL：该run的`production/checkpoint_complete_live_owner_v2.dll`，SHA256 `0e53219602a1f3aa12981dcfb432a72cd53021cd552a54da984448cf1f5b618e`；仅编译链接，未访问游戏或执行生产Install。自有组合DLL `bank.dll` SHA256 `a40b2ff7956cd07c6bf7e91abc6bdfde43a98c50c5282ab337ff7d1360c11518`，host EXE SHA256 `ee268c17769367e6e4026c2d63c709d92e675cfa430b1c59d643364267dff4d2`。

实际日志两次BANK completed/sealed/restored=1，slot_page与base完全一致；第二次arm期间LATE_FIRST_DURING_SECOND six=6/no_new_bank_callbacks=1。GUARD target9 corrected_accept=1/other_force_reject=1/legacy_accept=0，target2同样corrected_accept=1而legacy_accept=1。无游戏进程句柄、无附加调试器；自有host与构建进程均已返回，DLL保留至自有进程正常退出。源及EOF/尾空白检查冻结；后续只由root整合根文档和提交。
