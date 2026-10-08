# 扩展输入观察接入双端赏赐 Ready

2026-10-08。复用冻结 `reward_ready_flow`、房间、双端日志与测试套件，新增
`reward_interlock_native_port.py` 和 `reward_interlock_flow_test.py`。本轮没有游戏、
Steam、UI 或当前存档访问；仅启动明确指定、通过指纹核对的自建测试程序。

## 已接线与实际证据

两个持续原生测试端都使用 [planning_input_interlock](planning_input_interlock_handoff.md)
后继；沿用同一 User/Save Owner，新增 Game/global UI/panel 的本轮观察。赏赐仍有
显式业务替身，但 User/Game 桥、局部抑制和 FINALLY 通过已发布入口实际执行。

沿用的 11 项流程测试全部通过：两命令后准备、菜单语义去重、零命令、丢回执、
仅一人准备、未排空、封口后输入、普通玩家伪回执、旧 challenge、退休及换实例。
另 2 项结构测试拒绝缺少任一消费者证据、把 setter 当观察以及提升局部权限。
两类合计 **13/13**，不能把结构反例写成额外原生异常实验。

实际链路为 TLS → 独立 B Python 消费者 → A/B 两个原生子进程 → 局部输入观察。
最终从每端 IPC 日志独立检查其扩展观察，不以只有 setter 回复来满足组合。

## 扩展端口如何避免夸大范围

- 必须匹配独立 `san14.planning-input-interlock-owned.v1` 的成功结果、54 个输入
  源文件和 EXE/赏赐 DLL/PlanningHold DLL 三份产物摘要。旧 Ready worker 不冒充新后继。
- 同一 Ready revision 固定 Gate revision；新 Ready revision 必须对应更大的 Gate
  revision。每次实际 observation 的序号递增，观察线程保持相同，IPC 严格串行。
- setter 的 coverage 和新增 Game/UI/panel delta 必须都是 0。实际 sample 才能是
  `coverage=7`、三个 delta 各为 1；缺口 mask 始终是 31。
- 全输入、保存、房间 Ready、原生推进能力保持 false。五组未覆盖路径见原生交接。
- **原有签名 wire 仍只陈述 User/赏赐/保存接纳范围**，新证据在本地严格核验并保留
  原始 IPC；未改变旧 HMAC schema 来暗示整个引擎已经暂停。

测试在自身 Python 进程内显式替换旧套件的端口与 B 测试消费者入口；没有改写冻结
源文件、补填成功字段或放宽旧 Ready 验证。此端口不是生产游戏 IPC 引导实现。

## 复跑

先按原生交接生成本机新的 PASS 产物，再运行：

```powershell
py -3 work/mod_research/reward_interlock_flow_test.py --native-fixture '<本机 interlock run>/fixture.exe'
```

最终：`reward_interlock_flow_runs/20261008-201637-285628-99cbf1/summary.json`，13/13。
原生结果：`planning_input_interlock_runs/20261008-201256-271268/result.json`，18/18，
SHA256 `93b429181400491be4922741c66fe762f9140253f0996e43afd03b35e584c9d1`。
前一版 `201424-898523-4fa0b4` 同为13/13；交叉审查后收紧 setter 的零证据及新
Gate revision 递增要求，完整重跑形成以上最终结果。该组合没有失败运行。

## 下一期与真实闭环仍缺什么

原生 Controller 固定一个规划期的日期/viewer；赏赐 Owner 的绑定也不可原地换期。
**下一旬不能重置旧模块或复用旧 fence/key/回执。** 正式退役、保留必要等待、
新期绑定及命令日志谱系的跨旬接线仍需实现，当前没有运行自动跨旬脚本。

加载线程启动接入与两代完整队列已在另一个组合通过，见
[B 连续加载交接](b_reload_lifecycle_queue_handoff.md)。它与本 Ready 组合仍是
两条不同证据，不能相加为 A 保存→B 加载→新期解锁的完整游戏闭环。
真实菜单拦截和安全收尾、A 保存写入边界、两份合法新档、规则换世界以及真正持续
输入/执行排他仍是下一步。用户暂不方便操作；没有待用户的动作请求。
