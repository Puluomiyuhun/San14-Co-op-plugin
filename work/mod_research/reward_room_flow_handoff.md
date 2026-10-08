# 赏赐房间、两份日志与独立执行端的离线组合

2026-10-08。新 `outputs/san14-link/reward_room_flow.py` 接通现有 Room/TLS、
`authority_reward`、`ExecutionJournal` 和 `PeriodCoordinator`。主线程编写组合，
两名 agent 分别交付原生 Owner 和交易/移动契约，并交叉审查网络边界。

**21/21 Python 业务替身用例、13/13 新原生 Owner 组合用例通过。** 后一组有
独立 B Python 进程、两份独立 SQLite 日志、两个持续存活的原生 fixture 进程。
每个原生进程有自己的世界、User/Save Owner 和深命令容器；赏赐必须经过
新 Owner → PlanningHold → owned replay。世界业务效果仍是明确的测试替身，
不是两个真实游戏，也没有菜单/UI刷新证据。没有接触游戏、Steam或当前存档。

## 实际流程

1. 通过现有证书指纹固定的 TLS 房间认证 A/B，按 A选、B选、A确认、B确认锁定势力。
2. 可信本地适配器提供世界摘要契约、加载实例及独立 B 报告验签密钥。创建新目录、
   新规划 epoch、A/B日志；已有文件拒绝覆盖。B先独立观察并报告初始状态。
3. 两方只提交军团和人物 ID；势力由认证席位推导。网络线程持久化请求，
   不调用执行端。A本地命令与B远程命令共用同一队列。
4. 可信执行线程 `pump_one()` 重读 A 状态并预检，先落盘 DISPATCHING/INTENT，
   再调用本地端口。A执行成功后暂留 AWAITING_B，下一条不能超车。
5. B通过同一 TLS 连接取得权威意图，在自己的日志按序消费。日记保存同一意图，
   但 B 的 native command 必须重新取得本地 `context_sha256`，不能复制 A 视角 token。
6. B独立观察命令后的状态并签回执；A核验席位、实例、作用域、序号、摘要及签名，
   相等才标 PAIRED。重复消费不再调用原生函数；旧已确认回执也不能确认下一条。
7. A先准备后仍允许B继续赏赐；准备者不能新增自己的请求。双方准备、队列排空、
   两日志前缀相等才得到 `PROTOCOL_INPUTS_SEALED`。**它没有设置原生ReadyFence，
   不允许直接推进游戏。** 最终实际输入限制仍须整体原生 owner 接入。

这个后继只处理单个规划边界；尚未连跨旬重新装载、重新绑定及运行时代次管理。
普通菜单提交前接管、远端挂起时真正限制玩家操作、瞬时刷新和最终准备封口未做。

## 可信边界和失败处理

- `Replica` 的本地 port 提供 `attachment_id / observe() / context(force) / execute(command)`。
  回放结果必须实际验证 `native_returned / args_released / owned_slot_cleared`；
  观察只覆盖 `state_contract` 声明的字段，不能冒充全世界。
- B报告密钥与玩家登录凭据分开，只通过测试的本地 stdio supervisor 通道建立。
  TLS `scope/status` 不返回它；普通已登录客户端即使照抄 A 的正确摘要也不能报告已执行。
  HMAC绑定完整report（含scope、epoch对应摘要、加载实例、序号、状态和前缀）。
  **真实游戏的可信密钥引导通道还未实现**；不宣称抵御已被篡改的本机adapter或OS。
- 密钥只在内存中，未写入测试日志/摘要/仓库。签名生产者只从实际本地 journal/port
  重新观察结果。生产集成不能提供“给客户端任意JSON签名”的接口。
- 资格/归属/资源不足在未预留原生调用前终态 REJECTED，不占执行序号。
  加载实例变化、观察漂移、上下文损坏、原生执行后异常、持久化未知、断线均 HOLD，
  清准备状态，不自动重试或重开旧日志。原生调用与 SQLite 不能组成原子事务。
- 当前仅允许 loopback。测试涉及真实 TLS 和独立进程，仍不是两台异地电脑的验证。
- 两端业务若含不同随机结果，会在摘要比较时停止；固定+4的替身不能证明真实赏赐确定性。

`PeriodCoordinator` 与 `ExecutionJournal` 的初始前缀种子不同：0条命令时独立核对
两个真实journal，保留coordinator自己的初值；第1条及以后直接使用已核验的journal前缀。
没有修改冻结旧模块或伪造初始journal记录。

## 测试与复跑

仅Python业务替身（仍使用实际loopback TLS和独立B进程）：

```powershell
py -3 work/mod_research/reward_room_flow_test.py
```

原生组合先按 [Owner交接](a_reward_save_owner_handoff.md) 编译并通过测试，再使用
**本机新生成且来源摘要全部匹配**的fixture：

```powershell
py -3 work/mod_research/reward_room_flow_test.py --native-fixture '<new owner run>/fixture.exe'
```

原生端口会核对结果schema、PASS、EXE/两DLL及51份源码摘要，之后只启动该自建程序。
不同视角的世界样本归一化仅删除fixture的viewer差异；日期、两势力资金/行动力及
所有5名fixture人物忠诚度都进入摘要。fixture刘备君主500只是模型值，真实基线为952。
原生进程有256条IPC请求上限，只适用于本轮短验证。

最终结果：

- `reward_room_flow_runs/20261008-191629-910518/summary.json`：Python 21/21。
- `reward_room_flow_runs/20261008-191629-909494/summary.json`：原生组合13/13。
- 9份组合依赖源码在运行前后摘要一致；原生组合引用Owner结果
  `4d7521cecb369fde9b87dd11878f337080e03e5f7c3386d17dc00b87bd28282c`。

覆盖并发提交、先后顺序、不同视角、重复请求/执行后丢回执、单人Ready、无操作Ready、
越权/旧epoch/布尔ID/多余字段、签名/实例/摘要错误、已确认旧回执、断线与禁止重建日志。
另8个Python故障例覆盖写后异常、观察漂移、换实例及未知上下文故障，不能算原生异常实测。

交叉审查修复三处问题：裸客户端报告能伪造进度；宿主换实例被误当普通玩家命令拒绝；
迟到旧回执误中断下一条命令。均补反例后复跑。早期13/10、15/12项通过记录仍保留，
但缺这些最终反例，不作为当前最终证据；本模块没有失败测试运行。原生Owner的构建/断言
失败在其专属交接中保留，不能因此声称本轮所有实现一次通过。

## 下一步

1. 接真实游戏的可信actor/上下文采样与菜单提交前捕获；A本地操作必须也进入同一队列。
2. 让同一原生生命周期所有者提供B报告通道和最终ReadyFence，并跨world退役旧scope/key。
3. 用户方便后验证有限赏赐的真实双端数值及UI刷新；不把此次fixture结果当实机permit。
4. 保存/连续加载主线、规则换代、两机连接仍按 `docs/FIRST_TWO_PC_TEST.md` 验收。

本轮自建进程/监听均已退出，无新游戏补丁或调试器，无待用户操作。
