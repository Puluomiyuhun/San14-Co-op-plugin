# Read-only rules binding for a freshly loaded world

本轮新增 `b_warm_rules_capture.py` / `_test.py`；只读现有 GameReader 和本地 Room，不启动或访问游戏，不加载 DLL、不调用 Prepare/Seal、不发布规则，不改冻结前驱。

## 已有生产接点与真实缺口

1. `human_rules_activation_room.py:50 export_config()` 已有实际 root/world/date/viewer/settings 读取逻辑，但 `:39` 要求 `type(room) is Room`，现 WarmRoom/CheckpointRoom 不能直接传入。它将 Config.epoch 固定到 Room.binding_epoch；而 `human_rules_world_lifecycle.py:257 replace()` 要求新 Config.epoch 等于每次 NextWorldRequest.epoch。这两个身份需要区分，不能改 Room 身份来迎合 native 请求。
2. `human_rules_world_lifecycle.py:289` 明确要求旧新 viewer 相同；这是普通第二次校正的约束，不适用于初次张鲁→刘备。Root 的显式 BootstrapRulesBridge 后继负责第一次例外；本模块只读取其旧 A、新 B 配置，不提供切换权限。
3. `human_rules_world_lifecycle_test.py:185 current_config / :199 port / :270 prepare` 是自有进程的真实读内存/发布组合实现，但 `prepare()` 通过测试宿主命令生成模块，**不是生产 GameReader provider**。
4. `human_rules_activation_live_session_v4.py:131–155` 有生产 `LoadLibrary → HumanRulesActivationPrepare → Seal → 描述符/绑定核验`；它是固定诊断会话，不是目前 WarmRulesBridge 所需的可复用 `prepare_rules(observed) -> ResidentPort` 工厂。其 Room 出口仍为旧 exporter，正常 close/异常处理会走 Revoke，不能直接当跨 world 退休流程调用。
5. 原生规则 `human_rules_activation_v2.cpp` 的 bindingCurrent 绑定旧 root/world/settings，漂移会进入 fatal retention。必须在旧 world 尚有效且真实排他持有时恢复六个来源，再加载新档，之后用新独立规则模块 Prepare/Seal/install。Revoke 是终态，不应在正常 restore 前调用。

## 新捕获 API

```python
capture = RulesWorldCapture(
    reader, room, settings,
    pid=expected_pid, birth=expected_birth,
    read_birth=lambda: process_birth(reader),
    guard_check=trusted_native_fence_check)

observed = capture.capture_loaded(
    request, side='B', expected_ruler=952)
# observed 是 WorldGeneration，供 prepare_rules(observed) 使用。

# 给 ResidentPort(export_current=...) 的受信本地回调：
current_bytes = capture.export_current(observed, expected_ruler=952)
```

`process_birth` 来自已有 `checkpoint_complete_live_capture`；上例是装配说明，本测试没有构造实际 GameReader，也未调用进程 API。

- 接受真实 Room、CheckpointRoom、WarmRoom 这三种已知本地类，不接受网络描述字典代替 Room。
- 初始化固定 GameReader PID/birth/image/build、本地房间 scope、两玩家连接和设置摘要；每次采样前后重新验证。
- 从当前 memory/root/world、GameReader.snapshot、五个 planning 状态和类型重新采样，不使用预期新地址。读取实际 settings singleton、收入参数和 world option，与已认证规则摘要严格对照。
- `capture_loaded()` 按 request 精确日期、明确 A/B 侧和君主读取。可以读取旧 A 视角，也可以在已完成加载后读取 B 视角；调用者仍须持有加载完成和身份切换授权。
- Config.room、rules digest、force/main_district 取固定房间；**Config.epoch 取明确 request.epoch**。房间 binding_epoch 单独保持并核对，不能随规则模块换代而改写。
- `export_current()` 重新读取当前 native 日期，可用于旧 ResidentPort 的 `allow_date_advance` 检查；它不更新旧 Config、不允许旧模块跨 world 重用，最终与旧绑定的字节比较仍由 ResidentPort 执行。

捕获不等于完整 native idle/入口/AI main-district 证明。实际 `HumanRulesActivationPrepare/Seal` 仍须执行其完整生产守卫；本模块没有把这些守卫替换成 true。`guard_check` 必须为真实宿主的执行/输入排他检查，成功严格返回 None；重复 RPM 读取只能检查采样期间观察的一致性，不能独立证明调度排他。

## 离线验证

最终结果：`work/mod_research/b_warm_rules_capture_runs/20261009-185955-538998/result.json`

- SHA256：`768ceb15af7900dacebca7c043e3f6af6891977f096a1e00f6d0e4e0261a1dc4`
- 5/5 PASS；23 份来源执行前后相同，2 份产物哈希匹配。
- capture.py SHA：`92641c5e5dde826465e198cf21a84e12513791cc851a10318c2780e7459c6b94`
- test.py SHA：`79abf5b6d29318c760114e36dd15c21ae057d70be893de901411fe1fe69bd346`

真实 WarmRoom 经过原有身份选择和确认；GameReader 为明确 fake memory。正常例旧 viewer12→新 viewer2，root/world 地址改变，image/Room/rules/两势力军团保持，新 native epoch 变化且 Room.binding_epoch 不变。反例包括 native 设置不一致、未初始化 singleton、错日期/viewer、采样途中变化、PID/birth/玩家连接变更、失去 held 边界，以及观察日期前进不回写旧绑定。没有原生调用或真实游戏测试，不把这些结果称为规则已重装。

## 最短下一步

实际缺的不是另一个 Config 模型，而是保留式生产 `prepare_rules(observed) -> ResidentPort`：在当前受信 reader/Room/fence 内使用批准的新 DLL 独立副本，执行真实一次 Prepare/Seal，核 PID/birth/module/nonce/Config/描述符和来源，构造带实际 publisher 与新鲜 `export_current` 的 ResidentPort，随后由既有生命周期调用 install。失败保留驻留模块与未知状态，不重置旧 claim、不卸载、不自动 Revoke 一个尚待正常恢复的模块。

另一个独立缺口：第一次 B 仍为 A 势力时，冻结 Journal.reserve_load 的 pre-load guest viewer 要求 B 的目标势力。此轮 bootstrap 只能显式 STAGED 诊断路径；不能把 A-view 假写为 B-view 来取得正式 INTENT。若要首次加载同次完成协议 loaded，需要下一项明确的 bootstrap Journal/Projection 后继，成功回执仍严格要求真正 B 视角。该问题不由只读规则捕获绕过。
