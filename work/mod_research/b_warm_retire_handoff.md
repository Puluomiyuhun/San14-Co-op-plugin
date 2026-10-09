# Warm 完成后退休与六槽恢复后继

2026-10-09。本轮不访问游戏进程、Steam存档或UI，不运行历史live脚本。新增源码全部以前驱为明确后继，未改旧once、claim或旧源。此模块解决成功加载后旧观察器继续干预第二次加载的问题，尚未执行第二份加载。

## 生产接线

- `b_warm_retire_session.cpp/.h` 替代 `checkpoint_forward_native_session.cpp`，保持原Session类ABI。每个永久驻留DLL拥有一个独立sidecar，由 `Bind(Session, actualPlanningObserver)` 一次绑定；Bind本身不授权退休。
- `b_warm_retire_admission.cpp` 替代原authorized admission TU。封存后User原函数包装器直接调用已固定的native original，不再改变旧admission报告或触及其旧pending对象。
- `b_warm_retire_owner.cpp` 替代complete owner v2 TU；唯一装配差异是在真实planning observer初始化后绑定退休sidecar。旧安装/Stop/报告ABI保留，增加只读 `GetBWarmRetireReport(void*)` 导出。
- 冻结旧组件、物理六桥及ASM、HookSet、实际Bytes/Load/Identity/Planning校验继续使用。新代码不复用cold Bootstrap，不改变引擎worker runner，不卸载DLL。

授权点是实际Session配对的User AFTER最后清理段：原生User及观察者AFTER已经返回；规划回执必须正是当前f的call/TID/self，并与该Session attempt和实际Bytes、Load join/exactPop/frozen、Identity nativeReturn/FINALLY等完整回执匹配。只允许自身User dispatch active1；其他业务active及物理桥活动须0，无异常/未配对/未决请求/Stop，HookSet六项已正确发布。

随后在同一准入gate内减掉本业务计数，原子seal，调用原 `HookSet::RestoreAll`，逐槽expected-hook→original CAS并恢复原保护。不是inline多字节补丁，无需另找Parent0或暂停整个进程。Stop与seal使用同一gate：先Stop会拒绝退休，先seal则Stop不能撤销已经发生的完成。Owner外层Stop标记可能先于Session线性化点；不会授权新工作或回滚已完成结果。

已缓存的旧函数指针可继续到达，所以DLL、Session、原函数及callback上下文必须永久驻留。新BEFORE在同一gate下看到sealed便跳过业务观察，AFTER/FINALLY同样跳过；仍由旧物理桥调用native original。物理bridge统计可增加，旧Bytes/Load/Identity及admission业务回执保持不变。没有声称所有引擎线程已停机。

恢复假定本工具是六槽及所在页保护的唯一写者。第三方改槽时原CAS不会覆盖第三方指针；五个可恢复槽仍收尾，整体restoreFailed=1、sealed保持1，禁止下一代。当前未提供失败恢复/自动重试。只有一次规划完成的精确User call可退休：该边界遇其他活动时之后的任意active0不能放行。`completionSeen/refusalStage`记录已匹配完成边界后的拒绝段（1上游/活动，2物理桥，3HookSet）；无匹配完成边界仍为0。读取诊断后停止，不能宣传“多等几帧就好”。

## 执行证据

入口：`python work/mod_research/b_warm_retire_test.py`。所有生成、编译、运行文件在仓库外private `b_warm_retire_runs`，不打开安装游戏/当前存档。

最终 `20261009-151544-026573/result.json`：

- SHA256 `4963df27b79f37a9fc9347af2d4d06dd44eace6302f71cd6c5be0174280267b6`。
- 5/5：正常实际完成与恢复；report-state不完成不退休；User原生替身异常保留观察；Stop-during-load即便后来观察完成也不退休；第三方改槽导致封存后恢复不确定。
- 66来源、53 EXE/DLL/OBJ产物、5生成文件哈希，复核时均与记录一致，source_unchanged=true。
- 完整生产DLL以无fixture宏编译/链接。DLL文件名沿用旧builder别名 `checkpoint_complete_live_owner_v2.dll`，内容为本后继；SHA256 `2d600fb0b70b6ff3786a2fc9d2a9c9d87f48266ccd0a0b2b5a26a2be394ab3e9`。离线PE导出检查证实含 `GetBWarmRetireReport`，见同目录exports_check.json。
- 执行用自有fixture EXE，原六物理桥、实际Session/原生任务归属claim、配对FINALLY、文件字节核验、Load/Identity/Planning回执、实际OS worker/join/HWBP、真实原子HookSet恢复均执行。world/menu/FileRead/重建等native业务及环境来源地址为继承旧测试的明确替身，环境guard仍使用其fixture宏；不能写成生产DLL全链已在游戏运行。
- 正常与冲突场景都在旧Load/Title和world为PAGE_NOACCESS时，直接调用六个缓存旧桥，各原生业务替身恰好一次；业务回执和旧admission报告逐字未变，Session业务计数0。原函数替身允许这些晚到测试参数，仅桥观察器被要求不得解引用；不是宣称真正原生函数可接受失效this。
- 正常六槽指针及原页保护全部恢复；冲突槽保持第三方值，页保护仍恢复，其余五槽恢复。
- 五个自有子进程均正常退出0；没有保持调试事件的发布器、驻留测试进程或游戏补丁。

保留：首次生成脚本因嵌套Python引号出现IndentationError，尚未生成任何可执行产物；首个运行 `20261009-151332-072433` 为4/4中间成功，之后补Stop串行和诊断/只读导出后按新源重跑，不沿用旧pins。

最终生产源：Session cpp `2b203bfdfebb90033da4fa03552b0948101c834cfe4e813da3420e51f0b4a8d7`；h `0030530b515b24f0a896a1206f289d7f5b9a038e0c8758acbc0c637326fa6892`；admission `5f727d3c93e6ce2269becb959cebef0314869db30b34e9e0e929d27a00ba8f6a`；owner `f36799e7034b77fe8c85e0a429c8bde41537341b65ed09be30b0a2ff976b8ace`。所有新源码独立git whitespace/EOF检查无错误。

## 剩余最短路径

先在新真实进程中按已支持单次加载完整重新预检，验证本后继完成后自动sealed/restored及六槽/保护。不要直接运行旧launcher或重装旧once。

随后新bank必须使用新nonce/attempt/epoch、当前重建的world/UI/状态指针、第二份明确合法档的独立profile。旧profile仍固定CC03和203-08-11/张鲁→刘备，不能只换文件名直接假称支持动态下一旬。第二DLL/同进程两份合法档连续加载、新B当前势力和日期映射、跨旬房间接线均未实施；不要求为这些先完成cold Root方案。生产安装入口和首轮实机仍由主agent整合，当前不需用户新操作。
