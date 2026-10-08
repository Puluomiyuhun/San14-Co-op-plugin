# 同一跨旬 Owner 接实际保存管道、TLS 和日志

2026-10-08。仅自建进程、诊断文件、回环 TLS；未发现或访问游戏/Steam/当前存档/UI，没有实机补丁、记录器或待用户操作。冻结前驱未修改。

## 这次合并了什么

旧 `a_save_ipc_flow_test.py` 的实际管道链使用最初 `a_save_user_owner.cpp`；新的正式跨旬生命周期此前只在另一个 fixture 中保存。现在同一进程只链接 `planning_period_owner.cpp`、`planning_period_interlock.cpp` 和 `planning_input_interlock_gate.cpp`，复用原 `a_save_ipc` Server/Client。不能再同时链接旧物理 Owner 实现。

真实顺序为房间预约 → 管道 Submit → User 回调/五阶段诊断 Save/返回 User → 原生存储双读 → 管道 Copy → TLS 分块接收 → SQLite STAGED/reopen。中间在同一引擎线程调用 Controller 实际 Game/User 观察、Period.Retire/Rebind，接续累计赏赐编号与 Ready revision；第二次没有重建物理 Owner/Gate 或清空历史。两份不同的诊断文件各32字节，绝不是合法游戏存档。

新 fixture 通过只读 `PERIOD_BOUNDARY` 事件报告真实本地生命周期结果；Python 测试等此事件才提交第二次。stdio 仅携带既有私有 bootstrap 与诊断事件，不携带 Submit/Copy。正式请求仍走已认证管道。原网络流程的 Room 连接保持不变。

## 验证与身份

- 构建：`a_save_period_ipc_build_runs/20261008-220409-281042/result.json`，SHA-256 `4c4d3cffeb158db86eb7e51ccadcdccf1469a480604b88a29ba60ad5c7bfca55`，生产和 fixture 分开编译，60份构建源码指纹。
- 最终运行：`a_save_period_ipc_flow_runs/20261008-220427-971453/result.json`，SHA-256 `3b490705cc023894b6c0e37fc3388356d23d8535b5e2291220ccbf635c8326db`，**8/8，0跳过**：6项冻结协议客户端反例、1项两旬原生管道/TLS/日志组合、1项换期后主动停止的真实管道组合。
- 正常组合：同一进程两次 Submit/Copy/完成、四次原生存储读取、两次赏赐、两个退休回执；首次历史逐字节不变。所有实际作用域为0，房间/管道/自建进程收尾。
- 停止组合：首档已复制、实际重绑下一期后 Stop；第二次保存和旧导出均被拒绝，房间关闭，只有一次保存。这里是主动停止，并未宣称复测所有原生 SEH 故障。
- Python 另记录15份实际导入依赖身份；运行前后核对构建源码、EXE、两个私有运行 DLL 及生产库。没有源码变化/测试失败。初版7/7运行 `20261008-220321-169074` 保留；最终增加了停止反例，不能继续引用旧构建作为最终证据。

复跑仅限自有诊断子进程；需本机既有私有 `checkpoint_push_profile.h`、`checkpoint_planning_hold.dll/.lib`，不从运行中游戏生成。

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机已有归档目录>'
py -3 work/mod_research/a_save_period_ipc_build.py
py -3 work/mod_research/a_save_period_ipc_flow_test.py --build-run '<刚输出的构建目录>'
```

## 不等于已完成的部分

- 日期变更、赏赐/保存业务函数仍为明确替身；TLS 世界快照及 B 的 loaded 回执为模型。未证明赏赐数据写进真实游戏存档，B 日志只到 STAGED。
- 原生 period binding 是 fixture 自己的本地绑定；虽实际调用正式 Period API，但尚未把 `planning_period_session` 的完整网络 scope 映射接入此管道。不得将这次写成 Session/TLS 全闭环。
- 交叉审查确认：`expectedPeriod=0` 只拒绝 fixture 新请求，父测试等边界事件是协作串行；Inspect(copies)到Retire/Rebind间没有覆盖整个转换的IPC全局锁。并发调用者、后台writer与不遵守该协作顺序的请求不在本次证明中。
- 上游 Gate 覆盖已知入口；`permit` 是诊断调度函数，生产仍必须接持续输入/writer排他与生命周期所有者。事件等待不是生产同步屏障，不发保存或推进许可。
- 实际常驻窗口、真实日期引擎、A合法新档、B换world/规则换代/地图核验仍未接入本次组合。`full_input_held/production_permit/actual_game_save_load` 均为false。

下一步根据正常保存父层协调与实机最小观察结果选择保存边界，再接可信宿主提供的生产 permit；不能因本次已能传输诊断文件而直接安装到游戏。
