# 赏赐之后的双端 Owner 等待确认

2026-10-08。`reward_ready_flow.py` 组合冻结的 `reward_room_flow` 和新
`a_reward_ready_worker`，将协议准备接到两个独立自建原生进程的真实 Owner 观察。
所有旧文件保持字节不变。没有操作游戏、Steam、当前存档或 UI；无待用户操作。

## 本轮交付

- **原生观察 worker 8/8**：setter 只表示请求；实际已发布 User 入口的一次回调
  被抑制、Native started/returned 增量为0/0、FINALLY增量为1，才表示本轮观察成功。
- **组合19/19 Python流程/故障、11/11原生流程**：真实loopback TLS、独立B进程、
  两份执行日志和两份fence日志；两边持续Owner，实际赏赐之后再实际观察等待入口。
- 其中一条新组合直接使用 `CaptureSession`：A/B各自视角生成菜单语义提案，重复确认
  得同一request，经TLS只排两条命令，两端各执行两次，随后完成双方Owner等待确认。
  **菜单事件、lifetime和context仍由fixture提供**，不等同游戏点击已被拦住。
- 菜单独立语义53项、归档检查16项的来源与取消/关闭缺口，见
  [赏赐菜单捕获交接](reward_menu_capture_handoff.md)。没有改变其能力false标志。

## 准备流程及线程分工

1. 一人准备只封住自己的新请求，仍可接收另一人的赏赐；此时不设置最终Owner fence。
2. 两人准备且命令全部PAIRED/REJECTED后，可信协调线程调用 `begin_seal()`：读取最新
   日志，固定challenge（scope、epoch、实例、revision、序号/状态/前缀摘要），先落盘INTENT。
3. A的 `FenceReplica` 先落盘本机INTENT，再调用 `request_fence(revision)`。
   ACK不能替代证据；必须继续 `observe_fence(revision)` 走实际User回调，并重新读日志。
4. B通过TLS `reward_fence_next` 取得同一challenge，在自己的可信执行线程做相同步骤。
   B用独立adapter key签名challenge、日志观察和原生fence证据。网络处理器只验签/记录，
   不在TLS线程设置fence或触发该User观察回调。
5. B回执仍不立即完成；A可信协调线程调用 `complete_seal()`，再次观察A的fence及状态，
   再封协议输入。所得状态为 `OWNER_FENCES_CONFIRMED`。

继承的普通赏赐报告/Ready处理器仍可做只读 `port.observe()`，不要说所有网络处理器
完全没有本地端口调用。新实际fence操作只出现在可信协调/消费线程。

## 这份证据到底证明什么

固定coverage为 `user-callback-and-reward-save-admission.v1`：观察了当前Owner的User
入口抑制及赏赐/保存接纳互斥。这个局部入口外的UI、engine writer和后台任务仍未全覆盖。
所有结果继续 `all_input_held=False / native_gameplay_enabled=False /
native_simulation_permit=False / full_world_synchronization_proven=False`。

`period.cut` 只是既有协议协调器的输入摘要，不是原生推进票据。本模块既不推进游戏，
也不自动解除等待、调用保存、撤规则或读档。用户接受的完整双端Ready仍需总体原生
输入/执行排他；本轮是把实际局部Owner证据接进现代房间，不是完成全部排他。

## 重复、错误与换世界

- 同一已成功challenge重试只重新观察，不重调setter、不增加revision。
  B执行后回执丢失可以再次观察并回报；缺B回执时A不得完成。
- 每份fence日志只允许一个challenge。INTENT未得到结果、UNKNOWN、原生异常、观察错误
  或持久化冲突均不能自动重试setter；也不自动release可能已经生效的fence。
- `FenceReplica.apply` 全流程互斥；最终SQLite更新还要求同challenge且旧状态为
  INTENT/OBSERVED，晚到成功不能覆盖UNKNOWN。私有IPC请求/响应也逐次加锁避免串配。
- 每次观察前、报告采样前后都核对固定attachment；相同语义摘要不能替代加载实例身份。
  每次实际fence观察后还检查当前世界/日志仍属于同一输入cut。
- 最终等待期间不允许修改Ready或新增请求。错误、断线或 `retire(reason)` 清准备并
  将协议协调器置HELD；旧cut不能再经原协调器进入推演状态。retire还废止旧报告key。
- **retire仅控制面退役**，没有执行世界替换或六处规则撤回。实际换world前仍要按
  原项目规则恢复旧入口、确认活动调用退出、保持输入限制，再由新世界建立新实例/key。
  本模块没有给跨旬自动恢复开绿灯。

## 复跑

纯Python世界替身，仍用真实TLS/独立B进程：

```powershell
py -3 work/mod_research/reward_ready_flow_test.py
```

按 [原生worker交接](a_reward_ready_worker_handoff.md) 编译并取得本机新的PASS结果后：

```powershell
py -3 work/mod_research/reward_ready_flow_test.py --native-fixture '<new ready worker run>/fixture.exe'
```

端口检查新worker结果schema、EXE/两DLL/51份源码指纹，只启动那个自建fixture。
不从进程列表找游戏，不复制原电脑PID/地址/once claim。样本的资金/行动力/忠诚度
业务仍是替身，且一次worker最多256条IPC请求。

最终记录：

- `reward_ready_flow_runs/20261008-194915-698410-model-999eea/summary.json`：19/19。
- `reward_ready_flow_runs/20261008-194915-679295-native-b4151e/summary.json`：11/11。
- 原生来源：`a_reward_ready_worker_runs/20261008-193737-390733/result.json`：8/8，
  SHA256 `2ed702ff37a25076ada8ef71cdab0f984cd3a2958f0c3d2724f445785033157c`。
- 冻结前驱房间回归21/21；便携协议18项、TLS具名检查17项通过。便携环境检查仍缺
  pefile且未设置私有输入，不能写成全部开发依赖齐全。

19项中有8个仅Python故障注入；不把它们写成原生异常实验。原生11项覆盖两命令后等待、
菜单语义去重组合、零命令、丢回执、单人准备、未排空、封口后新请求、伪签名、旧期、
退休、实例变化（这些状态/网络条件外的真实User抑制来自原生worker）。

## 审查与保留的失败

修复并加反例：并发晚成功覆盖UNKNOWN、重复观察前缺实例核验、最终采样期间实例改变
仍用旧摘要签收、退休后原协调器仍可接受旧cut。新端口为共享IPC加逐次互斥。

两组组合测试并行时曾取得相同时间戳：模型组在独占创建目录时以WinError183拒绝启动，
没有覆盖同目录原生10/10结果。记录保留为
`reward_ready_flow_runs/startup-collision-20261008-194509.json`；新目录名增加模式和随机后缀。
之后完整重跑。早期14/10、17/10、18/11项通过目录保留，但以上最终19/11为当前证据。
原生worker早期7/8失败、菜单归档的两次失败均在各自交接中保留。

## 下一步

1. 先准备菜单四点只读观察，确认真实取消/关闭及状态请求收尾，之后再写真正拦截Owner；
   不能仅跳过公共赏赐或伪造返回成功。
2. 接实际游戏的上下文/加载实例及密钥引导通道，补全部需要限制的输入来源。
3. 将此规划边界接原生推进、A新档、B连续加载、规则换代及新epoch；每项仍需实机验收。

本轮自建进程/监听已退出，无新游戏补丁或调试器，无待用户操作。
