# Fresh Save 与房间检查点的关联

2026-10-08。生产 Python 适配代码已实现；验证是本机组件与真实 TLS 字节传输，**没有触碰 SAN14，也没有证明两份游戏已跑通连续两旬**。

## 为什么新增这一层

原有 `checkpoint_room_artifacts.py`、`checkpoint_room_lifecycle.py` 已支持独立 TLS 下载通道、当前控制连接绑定、连续旬次轮换、旧票据撤销与分块完整性检查。本轮复用它们，没有重造房间端点。

之前 `checkpoint_host_export_reader.py` 仅允许固定日期的历史导出档重放。新的 `checkpoint_fresh_save_binding.py` 接收受本机可信 owner 控制的 `CopyArtifact` 出口，把它与**本次提交之前**保留的完整房间上下文关联，再交给原有下载服务。

## API 与实际次序

1. 双席已选势力并确认，调用 `CheckpointRoom.bind_coordinator()`；在初始 PLANNING 创建一个 `FreshSaveBinding`。传入稳定的原生 `room_id: bytes32`、`room_epoch: uint64` 和受控的本机 `artifact_reader(generation)`。reader 只复制已完成产物并严格解码，不得发起保存，也不能接入网络 JSON、任意上传文件或历史重放档。
2. 双方完成协议准备、命令排空和推演，外部原生层真正维持玩家输入及其他业务写入排除。取得 A 的 `LocalWorldObservation`：当前 attachment、年月旬、势力/君主、覆盖契约、该契约下的世界摘要和已安全停留的观察。
3. `reserve(generation, filename, observation)` 在 room 与 coordinator 锁下保留完整 scope、128 位当旬 epoch、period、完整命令 cut（序号和 prefix hash）、seal、目标日期、两端 attachment、控制连接与世界观察；返回不可修改的原生 Request。此方法**不执行也不授权原生保存**。可信外层随后把该 Request 交给同一常驻 owner 的 `Submit()`。
4. native owner 完成保存后，`publish(generation, observe_world)` 从配置的 reader 取得 `DecodedArtifact`。逐字段检查原请求、完成状态、调用平衡、恰好一次 binder/queue、阶段与返回、完成代数，重新计算实际文件字节 SHA256；`stop_after_commit=1` 不发布。解码本身不是生产者身份认证。
5. 取得字节之后才调用 `observe_world()` 获取新观察。重新获取 room/coordinator 锁，对照原先保存的完整上下文与世界观察；不一致就锁定。构建带来源说明的 `adapter.json` 和 `CheckpointPackage`，调用既有 `offer_checkpoint()` 与 `install_offered_checkpoint()`。
6. 独立下载通道负责字节重试；B 的 journal、原生加载和完成回执仍由各自模块处理。本层不调用 `received()`、`begin_guest_load()`、`loaded()`、Ready 或游戏推进。

原生 `Request.room_epoch` 被常驻 Driver 要求两次保存相同；它是稳定 owner 会话标识。`PeriodCoordinator.epoch` 每旬变化。两者在本层明确分开，不能截断当旬 epoch 填进原生字段。完整每旬身份由 save generation 的不可变关联保留。

同一 binding 最多两个保留请求，和当前原生 Driver 容量一致。未决请求阻止第二次保留；文件名与 generation 不重用。断线、上下文变化、产物错误或发布不确定会进入 HELD，没有 reset、原生重发或自动恢复。所有 HELD 路径（包括显式 `hold()`）调用原有 `room.close_checkpoints()`，撤销已发票据与已认证的下载连接。若 `offer_checkpoint()` 或安装已完成后才发生异常，也不能继续供 B 下载；不回滚 coordinator 后伪装未发生。`publication_cleanup` 分别记录尝试、确认关闭和错误；关闭过程抛错时保持终态且 `closed=false`，不假称撤销成功。关闭房间协议不等于停止原生 owner、撤回已开始的 B 加载或阻止实际游戏输入。

`source_kind` 是可信本机外层的来源标签（`FIXTURE_ONLY` / `LOCAL_NATIVE_PROVIDER`），不是凭据或完成证明。所有产物的 `full_world_verified`、`native_gameplay_enabled`、`native_load_authorized`、`ready_authorized` 均保持 false。两次相同观察也不是完整输入锁或全世界证明；调用者仍必须在观察、保存、发布期间维持真实排除。

## 验证与运行

纯 Python 反例和 MODEL 字节 TLS 测试：

```powershell
py -3 work/mod_research/checkpoint_fresh_save_binding_test.py
```

此命令不编译、不打开游戏。20 个测试中，与自有原生产物有关的一个测试会明确 SKIP，其他测试运行。结果分别记录 `tests_run` 与 `skipped`，不把 SKIP 当作原生产物通过。

显式加入本轮自有 A owner 产物：

```powershell
py -3 work/mod_research/checkpoint_fresh_save_binding_test.py --owner-run work/mod_research/a_save_user_owner_runs/20261008-014011-202116
```

路径仅是本机示例；换电脑需先运行批准的 `a_save_user_owner_test.py` 生成自己的运行目录，然后传入该目录。工具核对该目录的 `result.json` schema、PASS、源稳定、未访问游戏标志、成功场景完成两次导出，以及 fixture EXE、生产库和当前对应源码 SHA256；来源清单只允许本研究目录内的简单文件名，不允许路径越界。核对结果 hash 写入本轮记录。这是本机诊断来源的一致性检查，不是对不可信文件的安全认证。

随后只读明确路径下的 `success/first.packet` 与 `success/second.packet`，固定并复核 packet 哈希；不扫描“最新结果”，不搜索游戏/存档，不导入历史 live 入口。缺少实际 owner 运行证据时不会把手工构造 packet 目录标成原生产物通过。

- 18 个 unittest 方法检查不可变关联、完整请求与报告反例、停止后拒绝、损坏/可变字节、JSON 冒充产物、观察缺失或变化、控制断线、读取时上下文变化、重复发布、两旬身份、两请求上限及 offer 后失败保留状态。包含真实安装完成、票据和下载连接都已发放后抛错，以及清理本身失败的反例。各方法内的字段反例用 subtest，不另凑测试数。
- 两个 TLS 测试各运行两旬：一个使用明确 MODEL 的大块字节；另一个使用自有进程实际 `Owner::CopyArtifact` 经生产 packet encoder 生成的不同产物。复用同两个控制席位与同一下载监听器，验证全文字节、旧旬请求拒绝和控制连接保留。
- B 侧实际执行 `CheckpointJournal.stage(receiver)`，重新打开 SQLite journal，核对 `STAGED` 状态及完整字节。测试没有提交 journal 原生加载意图。为了换到第二旬，coordinator 接收的是**明确 MODEL 的加载/世界回执**，不是 B 的原生完成证据。
- 两份自有原生 packet 在测试创建 Room/reserve **之前**已经由独立 fixture 产生。它们证明真实出口格式/产物到 TLS/journal 的连接；不证明生产中“动态 Room reserve → 同 owner Submit”的时序已经接通。报告明确 `native_exports_created_before_model_reservation=true`、`dynamic_native_submit_binding_validated=false`。
- `world.s14` 部分来自原生 fixture 的文件只有测试数据，业务函数是 TEST_DOUBLES，不是 SAN14 存档。世界观察始终为 MODEL_ONLY，TCP/TLS/哈希/SQLite 为实际执行。

结果写入 ignored 的 `checkpoint_fresh_save_binding_runs/<时间>/result.json`。stdout 最后一行为含 `result`、`path` 的 JSON，便于根目录的明确 allowlist 检查工具收集。本层测试需要 Python 与 cryptography，不依赖游戏或私有 profile；只有提供的自有原生产物在先前构建时使用了私有输入。

本轮独立复核曾发现：安装已经成功后再抛异常，只设置 binding HELD 会留下可用下载授权。已按上述统一撤销方式修复并加入反例。初次回归 `015148-490258` 的一个旧断言仍预期 RUNNING；新设计正确转为 HELD，修正断言后 `015230-869894` 达到 20/20 PASS。失败记录保留在本机，没有删除或用新结果覆盖。

## 仍缺的生产接线

1. 可信本机进程/owner 身份认证、原生 Submit 与 CopyArtifact 的实际 IPC 出口，且必须在 Submit 前调用 reserve。完成后再次 Stop/失效未必反映在已经冻结的旧 Artifact report；生产 provider 必须检查当前 owner 生命周期，并把停止/失效事件传给 binding 的 hold，不能只解码旧 packet。
2. 同一 A owner 与真实游戏槽所有者/输入排除协同，提供独立而且当时有效的世界观察；完整世界覆盖尚未完成。
3. B 同进程连续加载、世界/身份核对、双人规则重新绑定，以及双方继续操作的安全解除。
4. 真正两台电脑、两份 SAN14、两旬不同实档的受控测试；目前全链路仍未由本层证明。
