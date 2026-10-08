# 赏赐菜单捕获后继交接（2026-10-08）

本轮完成 **纯语义待提交捕获**，并把原生确认前候选缩到一个直接 call。
没有安装拦截、操作游戏、执行赏赐、发送网络请求或发放执行许可。
旧 decoder／赏赐协议／房间／日志保持不变。本模块不能单独用于实机联机。

## 原生来源与不能省略的边界

输入是原电脑已有 RVA 索引私有归档；未查找／打开游戏进程和 Steam，没有读取
当前存档。归档 SHA-256 为
`5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`，
对应历史 EXE SHA-256 为
`42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025`。
审计器只输出少量锚点／结论，不发布归档代码或完整反汇编。

| 层 | 可复核的实际来源 | 含义与限制 |
|---|---|---|
| UI Update `67A930` | `layout=[state+478]`，`[layout+170]==2` 后，`67A993 call626050` | 最短提交前候选在该 call；RCX/RBX 都是当前 reward state。此路径同步直达包装，不经过本项目权威队列。尚未证明所有 UI 输入来源均经过此分支。 |
| 包装 `626050` | 先取军团对应资金据点、检查余额能否覆盖 `count*100`；构造临时 ID list；`626275 call1D6DA0` | 候选应放在进入整个包装之前，避免已建立临时所有者和 UI 后处理。没有证明所有 helper 无其它副作用，也不把“已进入公共处理器”当作菜单接管。 |
| 公共处理器 `1D6DA0` | `1D6F8A` 写人物 flags；`1D6F91` 写忠诚；`1D6FD4` 形成 `count*(-100)`，`1D6FDC call15BD40`；`1D7001` 写军团行动力 | 实际权威赏赐结果／扣费路径在处理器内。现有固定赏赐实机 pilot 是该处理器验证，未验证这个菜单接管。 |
| 公共返回到包装 | `62627A` 取资金对象，`62627F call2F2BB0` 后才 `test EAX` | **公共处理器返回值未在这里检查**。直接令其返回 0 仍可能继续成功对话和 UI 后处理，不能据此取消／阻止重复。 |
| 包装返回到 UI | `67A998 test EAX`；非零调用 `F690` 后 tailjmp `10A60` | 这是包装自己的返回语义，余额不足路径也能返回 1，不能等同“赏赐执行成功”。`10A60` 将 `{1,0}` 追加状态控制请求队列，不在这个切点立即完成状态弹出。 |
| 零返回／重复输入 | 包装返回 0 时直接退出 Update；Update 自己不清除 event 2 | 归档 Update 的两个连续调用确实两次进入 wrapper double。因此只吞掉执行并返回 0 会留下重复触发风险，必须由未来原生 Owner 保持一次性捕获与正常 UI 收尾。 |
| 其它菜单／取消 | event 1 走 `67A9B6 tailjmp68F760`；后者有列表构造和 `layout+170=0` | 不能把 event 1 标为取消。event 0 还有输入门控／UI action／input reset 分支；**取消输入与安全关闭路径仍未确证**。新模块的 cancel 只取消本机语义草稿。 |

上述 wrapper／common 段是静态源码证据。执行证据只运行了真实归档的 **145 字节
UI Update**，所有外部 callee 均由显式服务替身替代；未运行完整包装、公共赏赐
或真实 UI 状态调度。6 个分支用例验证调用顺序、同 event 重入和栈／RBX 恢复，
不能声称原生取消、原生菜单状态或网络赏赐已成功。

## 新 API

`outputs/san14-link/reward_menu_capture.py` 没有进程、网络或原生执行依赖。
`CAPABILITIES` 不可变，原生拦截、原生取消、执行、网络提交、合法性验证均为 false。

```python
session = CaptureSession()
session.capture(decoder_result['command_preview'], trusted_context,
                capture_id=local_capture_id, now_tick=local_monotonic_tick)
pending = session.confirm(local_capture_id, fresh_preview, fresh_trusted_context,
                          now_tick=local_monotonic_tick)
proposal_packet = pending.packet()  # 仅构造数据，不发送、不执行
```

- 接收实际 `DomesticDecoder` 的 reward `command_preview`：只允许 kind、force、
  district、funding city 和最多16名有序 officer IDs。拒绝额外字段、指针数值、
  bool/float IDs、重复人物与未完成选择。
- `trusted_context` 必须由独立本机适配器提供，不能接 TLS 客户端自带 context。
  严格字段为 `room_id,binding_epoch,epoch,player_id,bound_force_id,
  main_district_id,viewer_force_id,attachment_id,menu_instance_id,
  world_revision,draft_revision,phase,observed_tick,expires_tick`。
  房间/期次/attachment/menu 是32位小写十六进制身份；revision/tick 是显式整数，
  tick 使用同一个本机单调时钟，生命周期/版本必须由未来真实观察器产生。
  本轮**没有**这些字段的可信生产者，字段通过不代表来源已认证。
- 绑定势力必须等于当前本机 viewer，preview 势力／军团须等于可信绑定。
  即便玩家 B，数据仍以其自己的 viewer／势力为准。
- 从 capture 到 confirm 必须保留房间、期次、viewer、attachment、menu、世界／
  草稿 revision。旧草稿自身期限不能被延长；确认前重新读 preview 必须完全相同。
  有效 context 身份或 preview 变化会终止旧 capture，不能改回旧数据再提交。
- 相同菜单实例最多产生一条待提交 request；重复／并发确认返回同一不可变对象
  和 request ID。每次 `packet()` 返回独立的纯 ID 字典，匹配现有
  `reward_room_flow` 的 `reward_submit` 形状，但本轮未接其发送路径。
  funding city 留作本机草稿比对，发送端不提供权威资金地址；服务端重新推导。
- cancel 在 confirm 前留下 tombstone；相同草稿 revision 不能用新 capture ID
  绕过取消。取消后修订选择须更大 draft revision。confirm 后 cancel 明确拒绝，
  不声称能够撤销已提交／原生已执行命令。
- 纯内存实例有容量上限，不自动丢弃 tombstone。重启对象不是去重恢复机制；
  生产接线须和原生 Owner／日志共同保持生命周期，不能重启后重新捕获未知旧命令。
- 此处从不根据 `ui_event_code_raw` 自动确认或自动取消。`confirm()` 是测试／
  未来可信捕获 Owner 传入的语义事件，**不能以此替代真实阻止本地先执行的证据**。
  这不是权限验证或排他锁；人物可用性、钱、行动力与执行后结果仍由原生适配器核验。

## 已运行与冻结身份

纯语义／自有内存测试，不需要私有归档：

```powershell
py -3 work/mod_research/reward_menu_capture_test.py
```

追加有界归档执行时显式指定私有输入目录（不会寻找游戏）：

```powershell
py -3 work/mod_research/reward_menu_capture_test.py --archive-root <private-archive-folder>
```

最终结果 `reward_menu_capture_runs/20261008-194247-415494/result.json`：
**53/53 单测 + 16/16 归档检查通过**，包括两项直接组合现有真实 decoder 的
bytearray fixture。源码及6项冻结依赖前后摘要相同，私有 image 结束重新哈希相同。

| 文件 | SHA-256 |
|---|---|
| `reward_menu_capture.py` | `0ddd235b2be1ba0f2f6f07213022c19802d1fbba39b361e2dbceb77cc93b6013` |
| `reward_menu_capture_test.py` | `0dcb62fc8b01638afdd4a96ea6ea9aa03167d75eb09dce9d180ffe8b1eafacd4` |
| `reward_menu_capture_audit.py` | `b031e020b0db465c8e5bee4578695939e2a5ed170bca1b4e6b012a3dcc5dbe30` |
| 最终 `result.json` | `a05e7969683a291a0e0aac21e6462b1be34d959fcccc28ac4f8792ff97cd297e` |

失败全部保留：`194207-227785` 的53项语义通过，但 emulator 测试映射漏掉
`76ECB0` callee 页，导致 fetch-unmapped；`194217-291704` 的53项语义通过、
归档11/12通过，原因是手抄 `626275` 五字节相对调用指纹一字节错误。扩大**自有
emulator**映射并按归档修正工具指纹后才有上列新完整成功记录。没有改游戏字节。

## 最小下一步（未安排用户操作）

1. 后继只读观察器复用已验证的 debugger/硬件断点租约和退出恢复；不能独占／
   覆盖其它 DR owner。四点可先用 audit 的 `ANCHORS`：`67A993`、`67A998`、
   `626275`、`67A9B6`。每事件记录新 run/进程出生身份/base/线程/序号／RSP；
   state 仅在本机用于配对，跨端输出只留 IDs。`67A993→67A998` 同线程、同 RSP
   配对；`626275` 参数对象必须在回调当场解码，不留栈指针给异步消费者。
2. 在未来用户方便时，先采样打开／改选／取消，确定取消真实来源与无提交；再
   单次正常确认，关联 UI code、纯 ID 草稿、wrapper 调用、common 进入和返回。
   有事件缺失、异步状态变化、未知路径就判不充分；不是四点命中就自动允许拦截。
   正常确认会产生原生赏赐效果，届时应有独立基线、收尾和恢复安排。
3. 只有这些证据完整后，才做新的原生捕获 Owner：在 call 前持有菜单 lifetime，
   阻止原生重复执行、正确取消／关闭 UI、将待提交送权威队列并显示等待结果。
   不能简单跳过 `1D6DA0`、伪造成功返回，或把 `confirm()` 当成这一步已经完成。

本轮无活动补丁、注入、调试器和游戏操作。根交接、提交和推送由主 agent 处理。
