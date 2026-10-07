# A 常驻 Owner 的本机 IPC 与动态旬次组合

2026-10-08。`a_save_ipc_client.py` 是正式本机命名管道客户端；`a_save_ipc_flow_test.py` 使用明确启动的自有进程验证组合。游戏业务仍是替身，世界观察及 B 完成回执仍是 MODEL，不能据此宣布 SAN14 双客户端已联机。

## 补齐的具体连接

上一轮先运行 fixture 生成两个 packet，再建立模型房间关联。本轮让 Python 在同一常驻自有 native Owner 尚未保存时先建立房间，按以下顺序运行两旬：

1. `FreshSaveBinding.reserve()` 固定完整 scope、当旬 epoch、命令 cut、attachment 和世界观察。
2. 将它返回的 `SaveReservation` 通过**真正的 Windows 本机命名管道**发给已初始化的 `a_save_user_owner::Owner::Submit()`。
3. 子进程中的原生 Owner 经真实槽位、桥与返回观察产生保存；Python 通过同一管道请求 `CopyArtifact`，严格解码和核对 request、SHA、当前 Owner 状态。
4. 再次观察 Owner 和模型世界，原房间发布检查点，经独立 TLS 下载到 B，再实际写入 SQLite journal、重开核对完整字节和 STAGED 状态。
5. 使用**明确模型**的 B 加载完成回执轮换旬次；相同两个控制连接、相同管道、相同 Owner 处理第二份不同保存。

Bootstrap 的私有 stdin 只传 secret、稳定原生 room ID/epoch 和 pipe nonce，**不传 Submit 或 Copy 命令**。正式 `a_save_ipc::Server` 绑定已经初始化的 Owner；未来游戏 DLL 中不依赖 stdin，只需可信安装器提供 Config 和生命周期。

原生服务的请求固定168字节；回复是56字节Header、60字节当前Owner Snapshot，Copy成功才追加旧编码器的packet。Config要求已经初始化/armed且未使用的Owner、预先指定的client PID、secret、稳定room ID/epoch和可信本地 `permit`。后者必须实际验证本轮world生命周期和完整写入排除，没有默认放行实现。服务不自驱Game回调，不替调用者安装来源；最多接受两个不同请求。`Run`只接一条连接，停止/断线后不重开；销毁Server前必须由调用者join其服务线程，不能卸载仍驻留的Owner桥。

## Python API

```python
endpoint = Endpoint(pipe, server_pid, server_birth, private_secret)
client = ASaveClient(endpoint, on_fault=binding.hold)
reservation = binding.reserve(generation, filename, trusted_before_observation)
client.submit(reservation)
# Binding 的 artifact_reader 绑定 client.wait_artifact。
package = binding.publish(generation, trusted_world_observer)
```

`Endpoint` 必须由可信本机 launcher 提供。客户端复用冻结 `checkpoint_session_channel.WinPipeTransport` 的 kernel PID/birth 检查与 OVERLAPPED I/O 取消、drain、未完成内存保活；新子类只换成 A 的变长 frame。旧 Guest Server/Session 格式没有被修改，也没有把固定旧档 reader 混进来。

每个请求在单一锁下递增 sequence。`Submit` 在开始 I/O 前就消费 generation；回复丢失、EOF、格式/身份/序号不匹配都会进入不可重放状态，关闭连接并通知房间 hold。没有自动重新连接。`Copy NotReady` 可以继续查询同一已提交 generation，不会重复 Submit。

`wait_artifact(timeout=N)` 在请求之间检查期限，已开始的一次 Copy 仍受客户端单请求超时限制，因此总等待上界为 N 加一次单请求超时；当前不承诺硬性的 N 秒总墙钟上限。

每个回复都附带当前 Owner 的 initialized/armed/stopped/error 和当前保存状态。仅有旧 Artifact 的 `stop_after_commit=0` 不足以发布：后来 Owner Stop 会让新的 Copy/观察被拒绝。显式 `stop()` 同样先通知房间撤下载授权，再发 native Stop；`close()` 通知 hold 并关闭管道。回调失败、I/O 取消未决分别记录，不能假称已经撤权或释放所有资源。

无原始地址、模块路径、任意文件路径或可执行命令从协议进入游戏；文件名来自已经保留的严格 `mpXXXXXXXX.s14` Request。客户端没有进程扫描、DLL 安装、游戏推进、Ready 或 B 加载接口。`on_fault` 只是可信调用者提供的本机回调，不能把一个未实现 hold 的回调当作已撤权证据。

## 运行检查

先用本机私有输入运行 `a_save_ipc_test_build.py`，得到一个明确的 `a_save_ipc_runs/<时间>`。然后：

```powershell
py -3 work/mod_research/a_save_ipc_flow_test.py --build-run work/mod_research/a_save_ipc_runs/<本次构建时间>
```

流程工具检查 build result schema、PASS、sources_unchanged、game_access=false、当前固定目录内源码指纹及 fixture EXE 摘要；启动前固定 EXE 只读句柄，核对其摘要，启动后核对真实 process handle 的 PID/birth。构建来源一致性检查不是对任意第三方报告的安全认证。

自有 fixture 没有窗口，仅操作明确的新运行目录。随机 secret 不放在命令行、stdout、报告或报错正文中。源码证明的通道约束还包括服务端限制本机连接、当前用户权限和预先指定的父进程。客户端身份核对失败会在发送任何 native 命令前拒绝。

不传 `--build-run` 时只运行六项客户端测试，六项原生组合会明确 SKIP。不能把这一结果称为实际管道或两旬原生组合通过。全部结果在 ignored 的 `a_save_ipc_flow_runs/`，stdout 末行提供 `result` 和 `path`。

## 最终离线证据

构建 `a_save_ipc_runs/20261008-021907-985240` 对应的最终检查为 `a_save_ipc_flow_runs/20261008-022410-279382/result.json`：12/12 PASS、0 skip、sources_unchanged=true、game_access=false。结果 SHA-256 为 `7775d8c1957469ac88399bff087c094749c19c3dadc1ec08c5e3d19508164018`；报告包含全部测试方法名称及执行前后的源码指纹。

- 动态主链使用一个进程、一个常驻 Owner，FINAL 为 submits=2、copies=2、completed=2；每代均先 reserve 再 Submit，两个实际 packet 未预先生成。两个不同的 32 字节替身保存均经 TLS 下载并重开 SQLite journal 核对 STAGED 和完整字节。
- 当前 Owner Stop 用例先完成一代保存，再 Stop；旧 complete packet 不能重新发布，房间关闭。FINAL 为 submits=1、copies=1、completed=1。
- permit 内触发 shutdown 的用例得到 FINAL submits=0、completed=0，确认准入回调返回后仍检查终止条件。
- 实际 Submit ACK 丢失用例只发一次 Submit，禁止重试并关闭房间；该轮 FINAL submits=1、completed=0。正常时序下保存可能已经完成，因此测试允许 completed 为 0 或 1，不把丢 ACK 解释为原生未执行。

上述 FINAL 均为 owner_stopped=1、ipc_closed=true、active=0、checks_failed=0，子进程正常退出且收尾无错误。其余测试覆盖真实 server PID/birth、secret、sequence 重放以及客户端分包、错误 generation、超时、NotReady 和撤权行为。

## 发现过的真实问题

首次实际组合 `20261008-021608-978703` 已处理动态保存和 TLS/journal，但显式 Stop 收尾失败：服务端把回复写入缓冲后立即 DisconnectNamedPipe，客户端读到 Header，尚未读取的 Snapshot 被丢弃。失败记录保留。现已修复为 native Owner 停止后保留有截止时间的只读 Snapshot/Stop 通道，等客户端 EOF/期限到达再断开；Copy/Submit 不再放行。没有使用无界 FlushFileBuffers。

同时补齐读取完整请求后、permit 回调返回后的 shutdown/父进程存活复核，避免准入过程中发生停止仍进入 Submit。最终检查包含该竞争条件的真实原生反例。

## 仍缺哪些实机端口

- 真实游戏中的 A Config/安装器、trusted permit 与完整输入/业务写入排除。当前 `a_save_user_owner` 的 User 子集 hold 会拒绝保存；不能为了保存偷偷解除等待后声称全部输入已锁。
- B 连续加载的父任务 fresh/resume/完成来源、Load Finalize `4CC690`、Title +520 创建/启动及每代自动激活。本轮另有 `b_reload_title590*` 补上+590来源与自动runner；它不等于连续加载已经成立。
- 换 world 之前撤回旧世界的双人势力规则、等全部调用退出，加载后重新绑定；真正 A/B 世界与身份观察、Ready 放行以及等待画面。
- 两台实际电脑上的版本/profile/安装和网络部署，以及两份游戏连续两旬的实机验证。

本机 IPC 的动态组合消除了“产物先生成再贴房间标签”的测试限制，但不将 fixture 的安全边界回调、模型世界摘要或模型 B 回执提升为生产证据。
