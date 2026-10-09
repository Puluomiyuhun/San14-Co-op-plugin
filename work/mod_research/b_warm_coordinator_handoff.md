# B 同进程两档诊断协调器

2026-10-09。新增 `b_warm_coordinator.py`、`b_warm_coordinator_native.h/.cpp`、`b_warm_coordinator_contract.py` 和 `b_warm_coordinator_build.py`。冻结的单代启动器、原生加载模块、暂存模块均未改。本轮没有访问游戏进程、Steam存档或UI，没有新增游戏补丁/调试器。

## 已经连接的流程

`Resident`持有同一个进程句柄、两个独立驻留bank和一个原生Handover所有者。第一份CC03必须事先已暂存；脚本核对两份profile来源/目标势力相同、第二before等于第一loaded、第二loaded恰为下一旬、文件SHA不同。这个诊断只加载两份已准备的文件，不替游戏推演，也不等于双方完整玩两旬。

第一bank使用当前本机五态/存储/模块/原入口绑定，实际typed Install后等待两份递增完成报告，再核实际六槽和页保护、地图日期/君主。退出只读文件租约后保留旧bank，不Stop成功模块。第二bank必须是不同的、尚未配置的实际DLL；原生typed Handover读取第一bank真实回执和源状态后才准许第二代接管。Python审计JSON不能替代这个判断。

Handover成功后，协调器核对目标仍为第一代实际读取的文件身份，生成本次一次性暂存事务，使用现有`b_warm_staging`备份并原子替换第二档。它持有第二文件只读租约，重新采样当前B规划对象，装第二bank并重复完整验收。失败不会回滚世界、重投或卸载旧模块；已知完成安装的Stop尝试发生在文件租约内，未知控制调用不重叠清理。Stop不证明排空，失败后的文件不得自动换回或重用。

同一PID/birth写入既有`b_warm_start_claims`，因此单代脚本和新协调器不能互相重试。两代使用同一个持久协调器内部的原生许可，不删除claim来运行第二次。`on_complete(index,result)`为本地完成回调，可由房间所有者连接`b_warm_room.report_warm_completion`；CLI本身尚未创建或加入网络房间。

## 构建与验证

原生wrapper只包装原有真实Handover，提供Prepare/Authorize/Observe/Describe四个typed导出，无安装业务钩子、文件写入、游戏推进或房间Ready功能。Prepare校PID/birth和nonce，合法形状的首次尝试失败也不重置。成功Prepare固定驻留模块；Authorize只允许精确独立第二bank，Observe报告实际完成状态。

- wrapper生产DLL/ABI：`b_warm_coordinator_build_runs/20261009-181031-457801/result.json`，SHA `4204df275c981b6c35c6bea01a25e040a0cea04be84e20ff2998079917e3b43a`。实际C++所有字段布局与Python一致，实际DLL描述、未准备调用和错误进程身份/once拒绝共6项通过。
- [两个完整factory组合](b_warm_factory_pair_handoff.md)在自有host中直接链接同源wrapper，执行真实typed Handover及两个完整Install/configure/guards。不是在该host加载wrapper生产DLL，也不是游戏代码业务执行。CLI要求helper所有native源与pair构建pins一致，并直接使用pair批准的生产bank DLL，不能拼接另一份单独通过但不匹配的bank。
- [协调文件检查](b_warm_coordinator_test_handoff.md)5项通过：真实Windows备份/原子替换/占用冲突/失败时租约；原生port明确替身。未运行整个`Resident`的远程模块加载和两档操作。
- root已核对helper与pair的全部native源匹配、实际产物闭包及默认help。私有日志、二进制和临时存档不提交Git。

## 实验入口

默认只显示help：

```powershell
py -3 work/mod_research/b_warm_coordinator.py
```

实际执行另需明确`--execute --pid <fresh-pid> --plan <local-plan.json> --helper-build <helper-result.json> --helper-sha256 <hash> --pair-build <pair-result.json> --pair-sha256 <hash>`。`--timeout`为每次加载等待秒数，默认180，范围30–1800。不要把旧失败进程用于新协调器。

plan严格包含`profiles`（两个`b_warm_profile_capture.py`定义的profile对象）、`target`（事先存在的CC03绝对路径）、`second_source`（已接收第二档的私有绝对路径）、`expected_ruler`（当前君主数字ID）、`steam_paths`（实际本机steam_api64.dll和steamclient64.dll路径字典）。目标槽的首次准备仍是独立步骤，不能拿此命令覆盖任何未核对的旧档。当前保存文件名映射仍只有槽63。

## 尚未证明与下一步

该入口仅为受控两档诊断；本轮未执行它的实机模式。native Handover核对已知加载链和六槽，不是覆盖所有外部写者的互斥锁；测试期间不能由玩家另下命令、保存、读档或推进。输入白名单、画面遮罩、两机推演和全世界一致核验没有被本轮测试替代。

房间侧已接实际TLS接收和诊断ACK，但ACK不调用旧`loaded()`，不把存档SHA冒充世界SHA。下一步在fresh游戏验证A两份真实新档和本协调器连续加载，再由同一房间所有者接收本地完成回调、实际世界观察、规则撤回/重装与下一旬许可。现有旧失败进程正常退出仍未确认，本轮无新增手动要求。
