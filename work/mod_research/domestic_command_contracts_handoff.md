# 商人交易／武将移动的语义提案后继

2026-10-08。**76/76 离线检查通过。** 本轮新增严格提案和可信上下文预检，
没有新增可执行的游戏命令，也没有改赏赐、房间、执行日志或冻结读取器。
未访问游戏、Steam、当前存档、网络或 UI；无补丁、调试器、后台任务、待用户操作。

## 新能力及默认边界

- `outputs/san14-link/domestic_command_contracts.py` 是无进程／网络依赖的纯 Python 模块。
- 不可变 `CAPABILITIES` 仅登记现有 decoder 的 `merchant` 和 `officer_move`。
  字段元组、能力记录及映射不可通过常规赋值修改。两个类型均保持
  `native_execution_supported=False`、`room_routing_connected=False`。
- 从 `DomesticDecoder` 的 `command_preview` 复制纯语义 ID。版本、字段集合、
  数值范围、人物顺序和上下文摘要均明确；不携带进程指针或客户端授权。
- 完整可信证据最多得到不可变 `PRECHECK_ONLY`。缺少或过期的资格／报价记录
  得到 `NEEDS_EVIDENCE` 和精确缺项；已知越权、不合格、资源不足、上下文变动
  或格式错误抛出带 `code` 的 `ContractError`。
- 所有成功返回均为 `authorization_granted=False`、`applied_to_game=False`、
  `native_recheck_required=True`。它不是 native ticket、房间 Ready 或执行回执。

## API 与调用顺序

```python
from domestic_command_contracts import (
    CAPABILITIES, command_fingerprint, context_fingerprint,
    proposal_from_preview, validate_proposal, ContractError,
)

# preview 仅取 reader_result['command_preview']；不要传整个带状态的 reader 结果。
semantic_id = command_fingerprint(preview)
# 本机可信适配器独立取得 context，并按 semantic_id 关联实际观察／报价。
proposal = proposal_from_preview(preview, context, proposal_id=request_id)
result = validate_proposal(
    proposal, context,
    authorized_force_id=server_bound_force,
    now_tick=trusted_local_monotonic_tick,
)
# 即使 result.status == 'PRECHECK_ONLY'，仍不可调用游戏或声称另一端已应用。
```

`proposal_id` 是非零 32 位小写十六进制身份，不负责去重或分配网络顺序。
这些职责仍属于现有 room／execution_journal 后续组合。
`command_fingerprint` 保留武将顺序；不同数量、方向、目标、人物顺序都会改变摘要。
`context_fingerprint` 只是数据完整性绑定，**不认证上下文作者**。

`proposal_from_preview` 的输出是独立可序列化字典，不共享输入的列表／日期对象。
`validate_proposal` 会复制输入再检查，返回值只含不可变标量和元组。
调用方后改输入不会回写已取得的结果，也不会让旧 proposal 适用于新 context。
这里不声称复制数据能排除游戏线程或任意宿主线程并发写入。

## 可信上下文契约

schema 为 `san14.domestic-observations.v1`，字段集合严格为：

| 字段 | 内容 |
| --- | --- |
| `game_sha256` | 已支持版本固定摘要 |
| `context_id` | 本次本机上下文的非零 32 位小写 hex；宿主必须在换 world／房间绑定／规划快照后退休旧身份 |
| `phase`, `date` | `PLANNING`；日期只含 `year/month/day`，旬日为 1、11、21 |
| `captured_at_tick`, `expires_at_tick` | 同一本机单调时钟，观察至失效的半开区间 |
| `actor_force_id` | 独立于提案声明的行动势力；仍需与服务端 `authorized_force_id` 相等 |
| `districts` | 每项 `id, force_id, action_points` |
| `cities` | 每项 `id, force_id, district_id, gold, food` |
| `officers` | 每项 `id, force_id, district_id` |
| `eligibility_observations` | 按具体命令摘要绑定的资格观察列表，可为空 |
| `quotes` | 按具体命令摘要绑定的成本／时限记录，可为空 |

城市／武将的所属军团必须在上下文存在，且势力一致。命令的来源城市、目标城市
（移动）和全部人物须属于服务端授权势力。未知键、重复对象、重复人物、布尔 ID、
浮点数、越界 ID、循环结构、指针额外字段等拒绝。
源格目前只证明 `0..48399` 的布局范围；它与城市、路径的实际关系仍由可信资格
观察及后续原生检查负责，不能从这个 ID 范围校验推断路径合法。

每条资格／报价都要求 `context_id, command_sha256, observed_at_tick,
expires_at_tick, evidence_sha256`。证据时间范围必须包含在 context 内。
同类中同一命令只能有一条记录；重复／矛盾记录不由客户端择优。

- 资格观察另含 `officer_ids, decision`；人物顺序必须对应完整提案。
  `decision` 只能是可信观察给出的 `eligible`／`ineligible`。未核实就留空，
  不能以一个默认的 true 或 `eligible` 代替真实规则观察。
- 报价另含 `funding_city_id, charged_district_id, gold_debit, gold_credit,
  food_debit, food_credit, action_points, duration_days`，全部显式填写。
  资金城市／扣行动军团必须归行动势力所有；检查资金是否足够、资源字段溢出、
  行动力是否足够。记录通过完整命令摘要绑定到数量、方向和目标。
- **没有推导价格、数量换算、默认行动力、移动天数或人员可用性。**
  没有假定付款城必然等于来源城，也没有把移动包装层的行动扣除省掉。
  这些由后续已核验的原生观察器产生明确记录；本轮还没有该记录生产者。

可信边界必须由未来集成维持：context、报价和资格记录来自单独的本机适配器，
不能接收提案客户端自带的同名 JSON。`evidence_sha256` 是已有证据身份，解析器
不会访问它指向的原始证据，更不能凭 64 位字符串认证规则真实性。
宿主仍负责该证据的来源核验、生命周期、当前房间／世界绑定和执行前重验。

## 测试与冻结身份

```powershell
py -3 work/mod_research/test_domestic_command_contracts.py
```

不需要 `SAN14_PRIVATE_FIXTURE_ROOT`、Capstone、Frida、游戏或编译器。
74 项纯契约／反例检查，另 2 项直接组合现有 `DomesticDecoder` 与其 bytearray
自有内存 fixture，分别读取真实 decoder 的交易／移动 preview，再进入新契约。
这两项明确拦截并断言未调用 GameReader 构造、进程发现与 Memory 构造。
资格、成本、时限数据均为显式测试模型；不宣称游戏规则已完成验证。

覆盖身份／归属、输入复制、不可变结果、未知键、数值类型、旧 context、报价
过期／串命令、资格拒绝、扣费边界、资源溢出及默认不授权。所有 7 份依赖源码
在测试前后摘要一致。

- 最终：`domestic_command_contracts_runs/20261008-190724-819250/result.json`
- 结果 SHA-256：`893334d6fc10e1747a2029316f4dc94611123bf51aa830b5aad55d281a4b6095`
- 模块 SHA-256：`2e791b9fab2a9d49d008e467b05be90f67370fa4eeb329a57d4b57f423125818`
- 测试 SHA-256：`8235a297c79797448d73db2ed5066624ffa623d344d6d704c51137b8adc7bce4`
- 中间 `20261008-190520-346177` 的 74/74 记录保留。本轮没有失败运行。

## 下一步

1. 为交易／移动单独调查可信资格与成本记录的原生来源；移动须覆盖玩家包装
   层的行动扣除、任务创建和对象寿命。未知规则继续缺证据，不补测试常量。
2. 后继房间／日志只传此处的提案，服务端自行取绑定／context；执行端仍须有
   真正原生许可和执行后观察，不得将 `PRECHECK_ONLY` 转成已执行。
3. 之后才做有限菜单字段对照和真实执行；本轮不请求用户操作，不发原生许可。

本模块尚未接 TLS、room、journal、A唯一 Owner、B执行或UI刷新，没有双端即时
应用能力。原生保存／加载主线及现有赏赐协议均保持不变。
