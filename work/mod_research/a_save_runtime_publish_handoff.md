# A Runtime 外部发布与撤回

2026-10-09。这里记录新 `a_save_runtime_publish*` 后继；不修改冻结桥、Gate、Owner 或 Parent 前驱。本模块开发和测试只访问本次自己启动的进程，没有发现或访问游戏、Steam、UI、当前存档。真实执行由主线程另行记录。

## 安装顺序及证据

运行中的目标先调用 typed Prepare、ArmOwner，保持原三处 call；Owner 的 User/Save vtable 此时可透明转发。外部 publisher 持有初始 CREATE_PROCESS 调试事件后验证所有线程和来源，一次发布三个 call，detach 后才调用 ArmPublishedSources。后者先 Gate 后 Parent，自然父帧负责初始化 Host。暂停窗口里绝不远程调用、加载 DLL 或等待目标执行函数。

ArmOwner 已发布部分 vtable 但后续 Bind 失败仍需 Stop 和撤回；不能重复旧 once claim。恢复允许三个 call/四个 vtable 各自恰为已知原值或本次 hook，以覆盖 Owner-only 部分发布。未知值零写拒绝。

新 evidence 包装 TU include 原桥源码，仅公开其真实 bank 的 started/active 地址和值：User 2、Gate 3、Parent 2（Parent 第二槽未用，仍核验）。`a_save_runtime_publish_parent.cpp` 是显式 Parent 后继，在原 finally 中、active 递减前采集真实 Host Snapshot，奇偶序列保护 packed 24-byte HostCache。生产构建需用这四个新 TU 替代旧同名功能 TU，不能重复链接。

外部停住全部线程后读这七组真实计数，要求 active 全零，并检查 RIP 不在本 DLL、三个 call 或 relay 区间。不能只凭 RIP 判断桥已退出，也不要求早先远程 Snapshot 的 started 与 attach 时相等。实时透明回调会自然增加 started；暂停前预检不以 active 非零拒绝，held 窗口才要求为空。

恢复另外要求 typed Snapshot 证明 Stop/OwnerStop/mailboxStop、saveLane 和各层 active 为空、父 before/after/finally 配对、Driver 为 Idle、无绑定/排队的 Cancelled(8)，或经过原返回/worker join/文件核验的 Complete(5)。held 窗口双读真实 HostCache，序列相同且偶数、lease/frame 均零；已初始化 Host 必须 valid。Stop 永久关闭新 admission，旧已绑定任务仍须保留原桥排空。早停 Cancelled 但 saveLane 尚存时严格拒绝，不把它伪装成干净撤回。

## CLI 与返回

```
publisher.exe <inspect|install|restore> <pid> <birth> <base> <module> <dll_path> <dll_sha256> <plans.bin> <snapshot.bin>
```

Plans/Snapshot 由本次可信 typed 导出生成，nonce/进程出生时间/主 PE/DLL 身份匹配；传入 DLL 文件固定 SHA，production publisher 另要求支持的游戏 EXE SHA。relay 必须是本次私有 RX 内存，间接目标必须属于该 DLL 的 RX image。三 call、四 slot 的固定地址、原值、保护和实际分配类型逐项验证。

- `PASS_READ_ONLY`、`INSTALLED`、`RESTORED`：退出 0。
- `REJECTED_PREFLIGHT`：退出 2，无写入、无 attach。
- `REJECTED_HELD_NO_WRITES`：退出 3，无写入并已 detach。
- `CLEAN_ROLLBACK`：退出 4，已写项逆序恢复至事务前精确字节并恢复保护，已 detach。
- `RECOVERY_REQUIRED_EVENT_RETAINED`：保持自有进程和调试事件，不自动退出。不得强杀；需按该事务实际身份处理。

JSON 提供 attached/detached/uncertain、written_mask/rolled_mask、线程核验数和 OS error。写入后逐项核验内容/保护。只在 rollback 可以识别精确已知字节时恢复；写入未知或 detach 失败保留事件。不会卸载 DLL 或释放 relay。

## 最终验证

运行 `python -X utf8 work/mod_research/a_save_runtime_publish_test.py`。最终私有结果：

`work/mod_research/a_save_runtime_publish_runs/20261009-123624-806483/result.json`（仓库外）

SHA256 `0f47db9abe80109cd09b0e7bc3333bd739b9eb7d435ebfc8aced0c083a0fcaf8`。

5/5：真实外部 debugger 安装三个 call 后恢复七项；仅 Owner 两槽发布的恢复；第二项写入后注入失败，written/rolled mask 都是 3；真实非零 counter 在 held 窗口零写拒绝；真实 Host lease 非零零写拒绝。每例由自有目标核验安装/恢复/原始字节，目标正常退出；结果中存活自有 PID 为空。生产二进制在每个自有目标上均拒绝 EXE 身份不符。

4 个来源、8 个 exe/dll/obj、1 个生成 build.cmd 均固定哈希；生产 publisher SHA256 `c1b74c0d1bf76dc67bf50da6662dca61e2ada02dce13c991804fe71f49552990`。构建 `/W4 /WX`。fixture 只用 `A_SAVE_RUNTIME_PUBLISH_FIXTURE` 取消支持游戏 EXE 哈希限制和开启 `rollback-1` 注入，实际 attach、线程上下文、读写、保护、rollback、detach 代码同生产；自有 Stage 的 hook/counter/HostCache 是模型，未执行游戏业务。

实际 shim 的动态组合由 `a_save_runtime_exports_scope_runs/20261009-123231-127883` 另验证：真实 FINALLY 读取真实 Host、lease 从 1 到 0、Stop 后再次父帧、7 个实际桥 bank；84 来源/41 产物/6 生成已独立核验全同。该组合仍为一个 scoped 周期和原生业务替身，不证明全游戏 writer 排他。

失败保留：`123535-473162` 编译成功，但 Python 默认 GBK 写编译日志遇无法编码字符，结果 FAIL，未创建自有目标；`123557-907633` 为早一版 5/5 成功，最终增加 counter 地址互斥检查和分别固定四个 obj 后重跑。所有目录保留。

## 精确限制

本工具依赖可信协调器提供与固定 DLL 一致的 typed Plans/Snapshot，而非允许任意第三方 descriptor。七个 bank 只覆盖这些已安装桥；没有证明所有游戏 writer，也未证明用户此时完全不能输入。不能把一次本地新档试验授权当正式联机许可。发布/撤回期间 DLL 常驻；Inspect 不等同可安全卸载。真实新档结果与当前游戏清理状态以主线程的新运行记录为准。
