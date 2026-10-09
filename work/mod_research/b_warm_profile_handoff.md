# Warm 每代不可变文件与世界配置后继

2026-10-09。未触碰游戏进程、Steam存档或UI；没有重投旧once，没有修改冻结前驱。本轮将上一版可退休的warm物理六桥接入每代不可变profile，生产不调用被禁用的dynamic Activate，也不要求cold Root。

## 具体接口与替换

`b_warm_profile.h/.cpp` 定义96字节Profile：file(size/hash/name/slot)、before日期、loaded日期、当前currentForce、存档source和收件方target的force/ruler/district。三个数据导出为DescribeBWarmProfileOwner、InstallBWarmProfileOwner、GetBWarmProfileReport。旧Owner完整报告和GetBWarmRetireReport仍可读取。

同DLL第一次profile Capture后不可更改；验证失败也保留once，不能改参数再试。Profile只表示绑定配置，不表示Owner已安装、加载成功或许可下一代。旧Install若没有Ready profile仍拒绝。

以下显式同ABI后继保持原physical Worker Claim/CurrentOwner，替换固定数据比较：

- bytes/lifecycle/request：实际文件读取长度、SHA、已读Load字节及请求intent绑定profile。
- identity：loaded日期和source→target指针关系、ruler/district关联；force+47采用既有dynamic算法，在实际已claim的Title BEFORE捕获opaque值，并在后续提交/AFTER验证稳定。没有在配置端猜测加载后对象地址。
- planning：重建规划栈、world日期、target关系及回执SHA按profile检查，原真实caller/TID/worker/前后配对保持。
- guards：初始日期/currentForce与加载后source/target日期、关系分开；模块、代码指纹、来源、存储与代际guard保持。
- owner：profile Ready才可配置；before参数明确写入input boundary，消除其默认203-08-11/force12依赖。安装intent追加完整Profile，新magic/size为Profile Config，configSha覆盖完整typed Config。

原 `b_warm_retire_session.cpp`、`b_warm_retire_admission.cpp` 不变。成功仍必须由该代真实Bytes/Load/Identity和配对重建User AFTER共同授权seal与六槽恢复。

保留了唯一已验证的原生运输映射：slot63↔svdexccSC03.s14。此名称不再表示固定文件字节，但不接受未知slot/任意文件名；游戏如何映射未知名字没有证据。后续两个检查点须先后通过有权限的staging流程放到此原生槽，不能仅改配置要求游戏读取任意文件。旧header兼容常量仍存在，后继实际业务校验不再依赖旧274880字节/SHA/年份/势力常量。

## 最终执行

入口：`python work/mod_research/b_warm_profile_test.py`。全部产物与日志在仓库外。

最终private `b_warm_profile_runs/20261009-154811-322893/result.json`，SHA256 `1fead4fef554b0d58caf09bf28c30d11c9e5e94b38ccca7f7b39e9f6a63f31a5`。4/4通过，74来源、57二进制/对象、5生成来源哈希当前全同，source_unchanged=true。

生产DLL为该run的 `composition/checkpoint_complete_live_owner_v2.dll`（继承builder文件名别名），SHA256 `0b3ec93697bf4361ba79c4164395315c52576159cac5fe2bf28607f19976d4e2`。全生产宏编译链接，未在游戏加载。

自有进程组合实际执行原物理六桥、Session、请求Verify/CAS、Worker claim/FINALLY、Bytes/Load/Identity/Planning、真实OS worker/join/HWBP与HookSet恢复。原游戏菜单/加载/世界重建/FileRead等仍为继承的明确业务替身，guard环境地址按fixture模式；不能说生产DLL已经完成真实双档读入。

四场景：

1. 274880字节，SHA `88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c`；before/loaded 203-08-11，current12，source12/666/11→target2/952/2。实际完成并seal/restored，六缓存旧入口各original一次且回执不变。
2. 274912字节，SHA `c3d73359c9c8c93f24592e871a84b11560a9fb21f072b1e86f7fc2bf1430bbfc`；before204-09-01/current2，loaded204-09-11，source7/111/6→target9/222/8。同样完成并退休恢复。第二字节流是在私有归档末尾追加32诊断字节的输入，**不是已验证合法游戏存档**；native业务替身按独立配置建世界。
3. 真实输入不变、声明SHA改错：实际Verify拒绝，request CAS次数0，未加载；允许既有preCAS六槽清理，postComplete退休未发生。
4. 声明loaded204-09-11，但业务替身建成204-09-21：Bytes核验/Load先完成，真实Identity返回World错误，identity CAS次数0，没有封存/恢复postCAS观察。

两套成功配置运行于两个独立自有进程，未证明同游戏进程两代接管或两份合法旬末新档。每次Capture后再次配置均拒绝。原归档保持原SHA。所有自有测试子进程退出0，无保留调试事件或游戏补丁。

失败/中间结果保留：154531-382952生产编译遇Windows max宏与新增include顺序冲突；仅后继bytes中改为括号化numeric_limits::max。154551-904963首个4/4；154639-617747补齐所有后继Initialize的Ready门后4/4；最终154811补安装intent精确新格式/hash后再次4/4。未沿用旧产物证明新源。

Root另有 `b_warm_profile_contract.py` 和 `_abi_test.py/.cpp`，本agent只读审查了字段布局、C++/Python状态契约和两真实DLL实例配置隔离测试，没有修改这些文件；最终ABI执行记录由root维护。

## 还差哪些实际接点

1. Root用当前进程与准确原入口重新预检，编码新typed Config；不要复制旧PID、对象地址、nonce或回执。
2. 第一代真实成功后核对sealed/restored与六槽原保护，保留DLL；不是只看profile.ready。
3. 针对另一份合法新档建立独立文件身份/loaded日期/source/target关系，同时采当前before world/状态/currentForce。每代新模块和once，旧模块保持驻留。
4. 完成同一进程、同一六槽、相同native originals的两模块顺序接管，并在真实两份合法档上跑通；这部分本轮未实现。
5. staging写入、外部launcher/房间跨旬握手与错误停止必须跟上。新profile接口不授予覆盖任意现有存档的许可，也不直接开放全房间联机。

本轮所有模块源码/测试已冻结，独立whitespace/EOF检查清洁。无需用户立即操作。
