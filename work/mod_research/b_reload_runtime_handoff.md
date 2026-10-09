# B 实际启动与连续加载：入口核对

2026-10-09。本轮没有启动或访问游戏进程、Steam存档、UI；未调用历史 live/start 脚本、未安装钩子、未消费任何运行 claim。按主agent明确授权，只读指定支持版本的游戏EXE磁盘文件及旧私有runtime归档。没有新增第三套队列模型或可绕过守卫的启动导出。

## 已落地的检查入口

新增 `b_reload_runtime_source_check.py` 仅接受显式磁盘EXE/runtime镜像路径，对总文件SHA、PE32+节映射、cold Bootstrap准确六段、磁盘重定位交叉进行只读比较。无进程/加载/写内存API；输出不含原代码字节。未用RVA直接当文件offset，且拒绝无磁盘数据的虚拟尾部、重叠节歧义和截断输入。输出JSON只新建，不覆盖旧证据。

本机执行证据在仓库外 `b_reload_runtime_source_runs/20261009-141734-550606/result.json`，SHA256 `b0e65a594aba2c2d4e90a0610ff040b780bbf5de756f828dbeb3ac13bd2f9746`。支持EXE总SHA `42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025`；runtime归档SHA `5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`。

| Bootstrap来源 | RVA | 长度 | 与runtime不同字节 |
| --- | --- | --- | --- |
| InitCall | 1447B6 | 5 | 5 |
| Init | 509580 | 185 | 185 |
| Runner | 834D10 | 357 | 356 |
| Thunk | 50B730 | 106 | 106 |
| Yield | 50B690 | 111 | 110 |
| ThreadEntry | 83A930 | 253 | 252 |

六段全部不同、所在节可执行，六段都没有交叉DIR64重定位。因此不能只根据磁盘EXE受支持就认定这些runtime来源已在进程PE入口准备好；本比较亦不能证明PE入口内存必然不同（例如TLS/加载器阶段仍可能改写）。旧文档的“79段不同”只作历史背景，本次直接核的是生产Bootstrap六段。

另用独立pefile解析同一文件，逐段比对映射offset、SHA与重定位交叉，6/6一致；`independent-mapping.json` SHA256 `db804770d857c982a252db42d2c61bdb00673e0925bbb76641277db3f10cf635`，含8份审查源pins。首次独立核验因错误依赖路径缺pefile而未执行比较；切到已有私有依赖路径后完成，未修改检查器。独立记录不是第二次游戏运行。

`b_reload_runtime_source_test.py` 3项纯文件解析测试通过：正确diskoffset、虚拟尾部/截断拒绝、重叠节拒绝。没有创建目标进程或执行PE。检查器SHA `b735e7e4e3938048b1002931db1db3d955cc8719ec5c7f28e022ef923e79c2eb`。

```powershell
python work/mod_research/b_reload_runtime_source_test.py
python work/mod_research/b_reload_runtime_source_check.py --disk-pe '<本机合法支持EXE>' --runtime-image '<已有私有runtime镜像>' --output '<全新JSON路径>'
```

## 尚不能直接接生产Bootstrap的原因

`b_reload_cold_bootstrap.cpp` 的 entry/threads/sources/empty 与 InitializeAndArm 共同要求：主线程实际RIP在PE入口、原有暂停数1、线程集恰为主线程和当前导出线程、六段runtime字节均匹配、原系统Leave IAT、四池对象槽全空。旧两代组合在自有PE里预先布置runtime字节；真实EXE不能这么做，也不能为了通过校验复制归档代码。

`b_reload_cold_registration::Policy` 还要求所有真实producer遵守同一SRW/taskStarts协议并给出确切原生线程start。最新组合的producer锁和统一start wrapper均是可信自有宿主。给新生产导出创建一把无人使用的锁、填零taskStarts，不构成真实排他。真实CRT更早启动上下文若未进入已审83A930前链仍会拒绝，不能把任意未知位置改成pending。

若六段只有在入口之后才完成准备，即便1447B6前池仍为空，旧Bootstrap也不能直接使用：其RIP与完整线程集前提已经改变。那时应建立明确的初始化调用前阶段后继，而非把old entry信息伪装成满足；来源检查、publication/retain、同Provider生命周期仍保留。

## 最短fresh启动观察（尚未执行）

仅需一次fresh进程的两个阶段，不需要先操作剧本或读档：

1. 在真实PE入口第一次停止，记录PID/birth/EXE及主PE基址、主线程RIP、完整线程集合；读取上述六段SHA/页保护/归属、Leave IAT身份、`base+1A24DA0+10+i*80`四槽。不要注入运行Bootstrap作为“探测”，避免消耗once或部分发布。该版本磁盘EntryRVA为 `21FE310`，以本次PE头复核值为准。
2. 若入口尚无runtime字节，放行到首次原生初始化call `base+1447B6` 执行前，用确切硬件执行点观察而不改其代码，重复同批读数；核caller正常路径、RCX实际pool与四槽仍空，以及新增线程来源。若该点不可可靠捕获、来源仍不同或pool已经暖，立即保留为阻断，不能恢复旧claim再试。

观测必须有界、只处理本次拥有的调试点，成对恢复新增暂停/调试寄存器并证明debugger退出；不在所有线程停住时remote-call。这里给的是最短观察方案，不是已完成的观察器或自动执行许可。

若第二阶段具备runtime来源与空池，下一步才审真实constructor返回后四线程初始wait、ThreadEntry前链与全部首次wake生产者。只有证明初始化调用期间没有旁路生产者，或建立真正覆盖它们的冻结入口，才能给cold registration传有效Policy。存在额外线程不自动等于它会生产任务，但也不能凭名字忽略。

## 从单次旧成功到连续两次的接点

历史私有 `checkpoint_complete_live_v2_runs/20261007-163447-239499/result.json` 确为 `PASS_NATIVE_LOAD_IDENTITY_PLANNING`；同记录明确 full_world_verified=false、ready_authorized=false、automatic_retry_allowed=false。旧成功是已暖游戏的一次性Owner/原生加载/身份/规划验收，不是新cold Runtime的启动证明，不能重复使用一次性Intent、旧DLL或旧回执完成第二次。

当前同PE/DLL/Provider两代组合已有真正 cold Prepare→原RegisterColdPool→Session/Input/queue→Gate换代，但仍差这些实际接点：

- 上述真实来源就绪阶段与其发布/回退或保留契约。
- 真实producer排他、真实线程start及早期CRT上下文范围。
- 将同Runtime的Provider、真实父/Load/Title来源与本机Session/Controller绑定，替换fixture中的引擎数据/诊断服务；生产不能登记后切SetEvent到fixture服务。
- 两份独立合法新档的实际存储绑定、B势力身份、菜单/输入恢复、旧规则退休/新world规则与世界完整核验。
- 真实第一代完成再进原Gate::RegisterAndOpen，保持旧报告与once；外部接口不能凭一个“加载成功”boolean发第二代。

本轮关闭了“磁盘文件究竟是否已经包含Bootstrap六段runtime代码”的事实不清；没有声称关闭cold可安装阶段或两合法存档连续加载。下一项需要上面的启动观察，继续堆外围队列fixture不能回答它。
