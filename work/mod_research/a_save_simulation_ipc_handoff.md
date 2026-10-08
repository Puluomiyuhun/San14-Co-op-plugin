# 同一原生 Owner 的两期 Scope、日期边界与保存传输

2026-10-08。最终构建 PASS，组合 **8/8 PASS，零跳过**。全部在自建 Windows
进程、诊断文件和真实 loopback TLS 内执行；没有访问游戏、Steam、当前存档或 UI，
没有实机补丁/调试器，没有待用户操作。冻结前驱未改。

## 本轮接通的路径

1. A/B 通过真实 TLS 选势力、确认，建立真实 Room/PeriodCoordinator。A 在旬初捕获
   完整 Scope，包括三个128位身份、完整摘要、期次、累计命令cut和本方日期/势力。
2. 新 `a_save_simulation_ipc_child.py` 将该 Scope 编成固定101字节，只通过自建
   子进程的私有标准输入传配置。子进程实际 MakeBinding、Bind、Controller观察及
   Session.Initialize；父进程核对原生返回的完整摘要。Save/Copy仍走原认证管道，
   不通过标准输入调用业务。该子进程适配器不是生产游戏启动器。
3. 房间准备/封口进入 RUNNING，`PlanningSaveLink` 保留旬初身份并预约旬末请求。
   原生边界 Execute 接当前封存观察，在同可信线程包裹一次诊断推进回调；回调写
   自建world日期并派发真实桥的Game/User替身。完整epoch、period、serial保持不变。
4. 同一个Controller在实际新日期重新观察，旧旬初Evidence不能保存；新的Evidence
   经保持Ready的Save/Copy、实际存储读取、管道与TLS进入B的SQLite STAGED，再关闭
   重开日志核对字节。第一份诊断数据日期1→11，第二份11→21，数据摘要不同。
5. 在 RECONCILING 时仍禁止取得下一 Scope。**显式模型 B loaded** 完成后，房间才
   产生新epoch。父进程此时才向同一子进程传下一配置；新Session后继实际调用
   Retire→PlanNext→Rebind→新Controller.Initialize/Adopt，再执行第二期边界和保存。
   历史同时保存旧旬初Scope（日1）和旧旬末Receipt（日11），不改写旧记录。

两期保持同一物理Owner/Gate、进程、桥、保存Driver和管道；Ready revision仍为1。
这次没有中途恢复玩家下令，也没有把两期初始化为两个独立原生进程。第二期使用新
Controller，所有旧Controller/摘要/桥计数按正式生命周期检查，不删除once-claim。

## 实际源码与链接

- `a_save_simulation_ipc_build.py`：生产静态库与独立自建fixture；72份源码摘要。
- `a_save_simulation_ipc_fixture.cpp`：私有Scope接收、可信同步执行、两次边界/保存。
- `a_save_simulation_ipc_child.py`：保留原子进程出生时间/文件固定/有界输出/收尾，
  扩展Scope配置。第二Scope是fixture私有宿主输入，不是网络客户端提供的原生许可。
- `a_save_simulation_ipc_flow_test.py`：真实Room/TLS、两期生命周期和接收日志组合。
- 链接 `planning_simulation_boundary` 的四个实现，以及
  `planning_simulation_session.cpp`；不能同时链接旧Owner/Gate/Controller/Session。
  复用冻结 `planning_checkpoint_save.cpp` 和 `a_save_held_ipc.cpp`。

管道身份、密钥、序号、先消费后执行、完整artifact匹配、结果不明后禁止重试等逻辑
保持原样。网络线程调度到真实游戏线程仍未实现；fixture让管道主线程恰好就是初始化
和可信执行线程。标准输入配置读取也仅为此有界自建测试，不是生产异步调度方案。

Session明确后继只改变current日期解释：必须实际边界报告Checkpoint、线程/完整
binding/serial/cut/Ready和精确下一旬都匹配。其余Session实现保持原样。实际第二期
路径还验证：用旬末日改写旧Scope退休、只换epoch、重用旧epoch、换房间、错cut、
跳日期均拒绝。详情见 [Session交接](planning_simulation_session_handoff.md)。

## 测试层次与失败

8项由5项协议/身份检查和3项实际管道场景组成，不能算8次实机测试：

- 规划时捕获、身份/事件变化、失败预约不重试、101字节完整身份、无效Scope拒绝。
- 同子进程两期实际边界/保存/Copy/TLS/STAGED，累计2次保存及4次存储读取。
- 可信执行前停机：不调用边界/保存，管道结果不明后房间保持关闭且不重试。
- cut错配：进入可信backend但未执行日期回调或Save，保持Ready/Gate请求。

首次组合 `a_save_simulation_ipc_flow_runs/20261008-230448-390853` 为7/8；停机可返回
底层 `ChannelError`，新测试误只接受 `ASaveChannelError`。修正为这两个明确异常并
验证第二次Submit仍拒绝；未改生产通道行为。失败日志保留。单期中间8/8运行
`20261008-230647-147973`及两期中间`20261008-231047-349288`保留；最终又补实际
Session身份反例和源码空行整理后重建。原生边界9/12失败和最终16/16另见其交接。

## 最终复跑与身份

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='C:\Users\52708\Documents\Codex\2026-10-04\ni-li\work\mod_research'
py -3 work/mod_research/a_save_simulation_ipc_build.py
py -3 work/mod_research/a_save_simulation_ipc_flow_test.py --build-run work/mod_research/a_save_simulation_ipc_build_runs/20261008-231204-561776
```

换电脑必须使用本机刚生成的build-run和已有合法私有开发输入；示例路径是本轮记录。

- 构建：`a_save_simulation_ipc_build_runs/20261008-231204-561776/result.json`，SHA256
  `1b634c5ea727a518b11df354c0e37ab4a56b9f04ccfcc8901387c003f3e4d77f`。
- 组合：`a_save_simulation_ipc_flow_runs/20261008-231245-622762/result.json`，SHA256
  `2dd1af9c191771665aba9d6118162f2301f81873b628c1ecc9bd66f7498f163b`。
- 原生边界独立16/16，加此组合，合计88份独立源码摘要及全部声明的生产/测试产物
  已统一核对。34号共享副本未变。自建进程、线程和TLS监听正常收尾。

## 仍缺什么

`native_date_boundary_composed=true`、`session_next_period_composed=true`只描述上述
实际原生模块组合，**不表示真实战斗推演、完整暂停或合法存档**。回调自行改诊断日期，
两份保存各32字节，B loaded为模型；没有真实B加载。错误时不主动解除Ready/Gate请求，
但原模块Stop/source错误可能让某些入口转发，不能称任何故障都完整拦住全部输入。

下一步：真实引擎异步调度/事件栈与该边界的兼容；正常保存后台写入协调实证和合法新档；
B保持同PE/DLL/Provider的Bootstrap→四worker→连续加载；统一生产宿主的输入/规则/
世界/地图核验。没有获得新实机许可，不自动启动历史live脚本。
