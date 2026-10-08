# 检查点房间到本机规则配置的接线

2026-10-08。新增 `checkpoint_rules_context.py` / `_test.py`，冻结旧模块未修改。只操作自有测试内存、独立Python进程、回环TLS和SQLite，未访问游戏/Steam/存档或安装钩子；无待用户操作。

## 解决的实际接口差异

旧 `human_rules_activation_room.export_config` 要求 `type(room) is Room`，不能直接接检查点房间；旧联网原型又在同一Python进程直接持有协调器，不能照搬到远端B。新接口显式支持本机 `CheckpointRoom`、`ProgressRoom`、`ReadyBarrierRoom`、新 `RulesContextRoom`；远端只持自己的 `RoomConnection`，不构造假A房间。

规则 `Config.epoch` 与 `NextWorldRequest.epoch` 必须使用稳定的 `scope.binding_epoch`。`PeriodCoordinator.epoch` 每旬变化，只用于检查本次协议快照的时效。初始兼容性 `profile.checkpoint_sha256` 也不是每旬新存档摘要；不能强制二者相等。

`RulesContextRoom` 继承已有 `ReadyBarrierRoom`，网络准备请求仍只产生等待原生确认的动作，不能直接放行。新增两个网络动作：

- `rules_context`：返回当前已认证席位、完整scope、协议期次/阶段/旧世界attachment、当前检查点manifest与control绑定摘要。不含本机地址或凭据。首次明确取得快照时 `expected_context_sha256=null`；随后核验必须带原摘要，核验不会更换故障身份。
- `rules_context_fault`：当前席位以已发出的精确快照身份提出终态撤权；实际调用 `close_checkpoints`，核对下载关闭和已认证下载通道归零。始终 `native_pause_confirmed=false`。它只用于失败，普通规则恢复/切旬不调用此动作。

`remote_context(connection, expected_profile, checkpoint_id)` 的 profile 必须是本机建立TLS连接时固定的 greeting profile，不能从新返回的context里拿来给自己背书。整个context仍只是某一时刻的协议快照，**不是分布式锁或持续有效的加载许可**。连接失败后不会自动重连、换context或重发加载。

## 原生读取与生命周期回调

`NativeRulesBinding` 需要真实本机owner提供 `image/read/identity_check/guard_check/on_local_hold`。identity/guard/hold成功必须精确返回None，失败抛异常；False/True均拒绝。没有默认身份发现器或可用于实机的空guard。

- `export_current(world=None)` 从当前image重新读取root/world、viewer、日期与两项设置，前后复核指针和协议context；可作为 `ResidentPort.export_current`。返回136字节Config，由ResidentPort再与其不可变配置比较。
- `check_scope(world)` 核对规则的稳定房间/两人身份/设置绑定；可作为ResidentPort的scope回调。日期在实际读取/ResidentPort中核对，不能从网络标签推断本机世界。
- `next_world_request(local_generation, journal)` 要求本机真实SQLite日志已STAGED或INTENT，scope/manifest/旧attachments完全对应且字节校验通过；只生成逻辑目标，不创建或消费INTENT。原生generation来自本机owner，不能拿房间period冒充。
- `observe_loaded(request)` 从当前reader取得未知的新root/world，核对目标日期后返回WorldGeneration。**必须由上层在真实load完成后调用。若本机本来已经到了同一旬末日期，误提前调用也可能返回；它不是加载完成回执、世界一致证据或native attachment生成器。**

已安装旧ResidentPort的回调不能一直固定在最初PLANNING快照，否则旬末恢复时会被正常阶段变化误挡。`adopt_context` 只支持显式两步：同scope/control、同旬/同旧attachments的 PLANNING→RECONCILING；以及上层已有加载结果后，带当前WorldGeneration和新的B attachment，核对下一旬/新epoch/目标日期/A attachment不变，进入下一PLANNING。它只更换本机协议上下文引用，不改旧规则Config、不reset模块、不调用 `loaded`、不放行Ready或释放等待。不允许跳过阶段或自动重绑定；误传其他房间会拒绝，不关闭那个房间。

本机锁顺序是 **Room → NativeRulesBinding → ContextSource → coordinator**。本机source显式保存原Room锁，直接check/hold也先取Room锁，支持外层已经持有Room。若再包WorldLifecycle，外层也须先拥有Room再进入生命周期。远端没有A的Room锁，只在本机串行化操作；完整执行/输入排他必须由外层原生owner持续保留。

失败先请求本机保留等待，再尽力通知房间撤权。`local_hold_error`、`protocol_revocation_error` 和 `adoption_cleanup` 分别暴露失败，不把网络断线或ACK丢失写成已确认安全暂停。常驻DLL不由此模块卸载或重置。

## 验证与审查修正

```powershell
py -3 work/mod_research/checkpoint_rules_context_test.py
```

需要Windows、Python和cryptography，不需要私有game-runtime/profile。自有内存通过真正ReadProcessMemory读取；进程身份和执行排他回调明确是fixture模型。

最终运行 `checkpoint_rules_context_runs/20261008-103417-837814/result.json`，18/18 PASS，完整摘要见根 `docs/evidence`。覆盖：

- 本机三类检查点房间、稳定binding epoch与旬epoch误用拒绝、真实SQLite校验、加载后重新读取变化的自有world指针。
- 独立B Python进程，真实两个TLS通道下载147472字节，SQLite保持STAGED；B不接收A对象。错误本方viewer触发本机hold并经TLS实际关闭A下载。host `load_intent`仍None、`bytes_received`仍false。
- 错误profile、control断线、源码context漂移、旧故障凭据、错误viewer、读取期间指针改变、False回调、本机hold失败、远端撤权未确认、已有下载票/通道失效。
- 真实本机Room外层锁与并发source.check不死锁；初始准备意愿不能绕过原生Ready门槛。
- 明确的上下文阶段采用。下一PLANNING的完成回执仅在该测试里由MODEL填入旧协调器，用来验证谱系；不是实机加载或双客户端整旬证明。

保留的审查过程：首轮 `20261008-102519-552579` 13项通过仍缺正常阶段采用；独立审阅复现“核验新快照覆盖旧故障凭据”和本机Room/source锁倒序。新增expected摘要的非变更核验、显式adopt和Room外层锁后，`102920`为16项、`103106`为17项；`103417`再补真实EMPTY journal拒绝反例至18项。独立审阅者重新复现确认两项修复均有效。旧通过结果不涵盖后加的反例，所有记录保留。

## 仍未完成

真实原生identity/fence/本机hold端口、A保存准入、B父调度/Finalize整体加载器以及A/B原生对象的完整运行owner仍需连接。新模块没有网络 `received / begin_guest_load / loaded` endpoint，没有跨机原生Ready ACK，也不调用 `adopt_verified_planning_epoch`。完整世界核验、B菜单/地图帧恢复和释放等待仍由下一层负责。不能把本轮读取/传输成功当作实机双人游戏可开始。
