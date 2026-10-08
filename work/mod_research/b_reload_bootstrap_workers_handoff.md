# B Bootstrap 实际接四 worker 与普通任务

2026-10-08。新后继文件族 `b_reload_bootstrap_workers*`；冻结 Bootstrap、loader、lifecycle、activation、Provider 前驱未改。仅自建主 PE/DLL 和既有归档输入；没有查找或操作游戏、Steam、当前存档、UI，没有待用户操作。

## 实际完成

同一个主 PE / MEM_IMAGE、同 DLL 静态 Runtime / Provider，实际执行：

1. 原 loader 把新建自有主线程停在真实 PE 入口；fixture export 在该线程仍暂停时准备受控区域。
2. 新生产 Runtime 调用冻结 `InitializeAndArm`。原生产源码核对来源、空池、线程集合，发布初始化调用点和 Leave IAT；只发生一次。
3. loader 恢复主线程，实际 wmain 调用已经发布的初始化调用点；归档初始化器实际执行四个构造调用。
4. 四个真实 Windows 线程实际执行归档 ThreadEntry，抵达原生冷等待。生产 `RegisterColdPool` 用实际线程 CONTEXT / 系统 unwind 验证，然后发布四个 worker 入口。
5. 第一个 worker 执行一项普通无票任务，真实归档 runner → thunk → fixture 业务，返回原生等待。Provider 不注册任务，不制造完成票。
6. 四 worker 正常停止，每个实际 outer FINALLY 一次、线程返回 0；保留唯一 Runtime，不重新初始化、不卸载 DLL、不清旧回执。

末端真实报告：4 cold workers、1 ordinary business、1 unowned task、0 registered tasks / gate entries / gate finishes、4 outer entries / FINALLY；lifecycle entered / returned / FINALLY / coldPools 均 1；activation/lifecycle error 与 uncertain 均 0。主 PE base、已发布 call/IAT 与归档来源未变，Enter IAT仍指真实系统函数。

## 解决的组合差异

- 旧私有映像 fixture 可用动态函数表；在主 PE 中 `RtlAddFunctionTable` 返回成功，`RtlLookupFunctionEntry` 却未选到它。本后继将五条受控归档范围的 unwind 条目编入自有 host 正式 `.pdata`；unwind 数据在 Bootstrap 前填到独立 fixture 区域，逐条检查系统查表。真实冷等待验证以及 runner 的实际 nativeCaller 路径随后再次使用系统 unwind。没有修改 CRT 入口、真实 PE 头或原有 unwind，也没有合成 CONTEXT 冒充原生栈。
- 五条表按实际归档 prologue 编码：caller sub40；initializer 保存 rbx/rbp/rsi、push rdi、sub112；thunk 保存 rbx/rbp/rsi、push rdi、sub32；runner 保存 rbx、push rdi、sub32；ThreadEntry push rbx/rsi/rdi、sub64。正常路径已执行，不宣称所有异常/epilogue 路径已覆盖。
- Enter/Leave 使用真实系统 IAT；thread manager、任务计数、四个 worker completion 临界区都预先 `InitializeCriticalSection`。没有使用 rootSync 空函数。线程结束后六个临界区的递归计数为 0 且可取得，任务计数归零；再销毁临界区、关闭自有句柄。
- MEM_IMAGE 的 demand-zero 页在首次触及前可能仍报告 WRITECOPY。fixture 在 Bootstrap 前显式构造四个空池槽并核其 RW；不靠诊断 printf 的读操作让页面就绪，也不放宽生产 page 检查。
- Runtime 的 Provider 私有且只构造一次。后续真实 Snapshot 直接读 lifecycle/activation；不使用 Bootstrap 封存快照假装 worker 已完成。

## 文件与构建

- `b_reload_bootstrap_workers.h/.cpp`：生产 retained Runtime / Provider 与启动、动态模块 Snapshot。
- `b_reload_bootstrap_workers_export.cpp`：生产 Bootstrap export；只有 OWNED 宏才包含人工准备与演练 export。
- `b_reload_bootstrap_workers_fixture.cpp/.inc`：自建 PE 区域、受控准备、真实线程和任务演练。
- `b_reload_bootstrap_workers_unwind.asm`：只链接自有 host 的静态 `.pdata`。
- `b_reload_bootstrap_workers_test.py`：生产 DLL、owned DLL/host、原 loader 构建与独立进程验收。所有 lifecycle/activation/Provider/Bootstrap 生产对象没有 fixture 宏；只有 owned export 编译有专用宏。activation 只链接 `b_reload_lifecycle_activation.cpp` 一份。

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机已有归档目录>'
py -3 work/mod_research/b_reload_bootstrap_workers_test.py
```

需要既有私有 archive/profile；没有则明确停止，不从游戏或当前存档自动取数据。产物及原始日志不提交。

最终记录 `b_reload_bootstrap_workers_runs/20261008-233403-352293/result.json`：**2/2 PASS，0 skips**。

- 结果 SHA256：`82af66efeecde4b16f1c3921175da52f7fdf154b4eaa6315e5178e6221d65c39`。
- 147 份源码身份结束时匹配，私有输入身份未变。
- 正向：实际 Bootstrap → 四 worker → 普通任务 → 正常结束。
- 反向：生产 DLL 遇未准备的自建主 PE，Bootstrap 阶段拒绝，未进入 wmain / worker；没有自动准备生产映像。

二进制身份（仅本地）：

- `loader.exe`：`63591aaf40a140734304d88bdb9672c67962c54affc7d96576a67866af628380`。
- `owned host.exe`：`a506d636c04261d46f442cd8eeaf686429dabf4565748fc1a019b90fe2b6226d`。
- `production_bootstrap.dll`：`8250c04c02f56938438487dd67f8e888eb8be2f0dc5a886ae93817d2c3317744`。
- `owned workers.dll`：`31d2519d803c199a8dee3fe3933336bee5188eeb97d1559fa1446ef6d95bd800`。
- `b_reload_bootstrap.obj`：`5d278e334f1867faa00e7b95cd5d6bfdd56ba9c49184b91c14219ba0f0b99162`。
- `b_reload_bootstrap_workers.obj`：`5f1d073735de28eb95b8889c47be22e1442f21f21e89d74e80b8c9c47573e955`。

## 保留的失败与中间运行

- `20261008-232659-904912`：构建失败，fixture alignas 导致 C4324 /WX。移除多余16字节对齐；所用临界区自然8字节对齐。
- `20261008-232745-551587`、`20261008-232842-302822`、`20261008-232926-959638`：正常分支在准备阶段拒绝，动态 unwind 表未被主 PE 系统查表选用。生产来源未就绪拒绝通过；未启动 worker。
- `20261008-233034-699244`：新增 MASM `.pdata` 构建语法失败，补 `option dotname`。
- `20261008-233126-915482`：正式 `.pdata` 查表通过；Bootstrap 的池 PAGE_READWRITE 检查拒绝。随后确认 demand-zero 页首次访问保护转换，不改生产校验。
- `20261008-233226-544103`：首次完整 2/2，通过时诊断打印读了空池页。此结果保留但不作为最终身份；最终版改显式预构造空池并加原始来源不变核验及关键断言立即终止自有子进程。
- `20261008-233403-352293`：最终 2/2；上述准备缺陷已修复。

失败只结束对应自有子进程。关键 require 不再累计后继续使用无效指针/句柄；若验收失败，直接结束当前自有 child，原 loader收尾。没有未知进程操作、活动调试器、存活自有 worker 或游戏补丁；生产驻留 DLL随自有进程自然结束，未调用卸载。

## 精确限制与下一步

这不是两次读档，更不是两个真实客户端联机。人工构造器仍主动等待初始窗口，真实游戏构造器的时序仍未知。状态对象、菜单/世界、业务 Update、线程构造、cookie 服务与线程退出 CRT服务是明确 fixture；Wait 服务观察事件后调用真实系统 Wait。真实 Enter/Leave 及已构造临界区没有替身。

目前 Runtime 只提供启动与真实 Snapshot，尚未把 queue 的两代 Session/Input/Provider 注册及 `RegisterAndOpen` 接入此所有者。下一步沿组合审查第4步，把它们放进这一个 Runtime；保持同主 PE、相同worker、同Provider，不能再分配另一映像或链接另一份全局模块。先真实两代正常/嵌套yield，再合并故障矩阵。

真实运行时来源就绪阶段仍未证明：历史79范围磁盘/运行时不一致，不能把人工准备PE当成真实游戏入口可安装证据。合法新档、持续全输入/后台writer保护、规则跨world、完整世界/地图核验、真实冷等待保证仍缺。本结果不授予 save/load/simulation permit 或 room Ready。
