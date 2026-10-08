# 赏赐菜单正常收尾来源与拒绝条件（2026-10-08）

本轮进一步执行了正常成功尾部的**真实入队、队列消费、Reward清理和状态栈
变更**，查清为什么不能收到权威回执就让 wrapper 返回1。没有新增可调用的
生产 close API，也没有修改或放开上一轮一次性捕获门禁。

全部离线。没有访问游戏、Steam、当前存档或 UI，没有运行 preflight/record、
安装、注入或调试器。根文档与 Git 由主 agent 处理。

## 已执行的真实路径

| 路径 | 本轮证据 |
| --- | --- |
| Reward.Update 非零返回尾 `67A99C→F690→67A9A9→10A60` | 在自建进程中以原Update栈形进入真实成功尾，未调用包装或公共赏赐；F690是明确的manager替身 |
| `10A60` | 实际追加16字节请求：u32类型1、末8字节object=0；中间4字节是padding。**请求不携带菜单身份** |
| `50A7BA…50A992` | 实际复制pending，调用分配器释放旧存储的替身入口，清零manager的pending指针/计数/容量 |
| `50A9C8 / 50A9E4` | 从消费时的正式栈顶重新取R12，type1转入pop分支；不会依据原来的赏赐菜单指针选择目标 |
| `50B1A5 / 50B1B5` | 调当前栈顶pause+20和finalize+10；Reward的实际+10为`667B10` |
| `667B10` | 原机器码驱动布局三个虚方法，写state+8并把state+478清零；虚方法是UI替身 |
| `50B1FB / 50B21C` | 实际减少正式栈计数，调用下层状态resume+18；下层User逻辑是替身 |
| `50B25C / 50B267` | 原机器码调用Reward的`6115A0→60B000`析构，再触达allocator释放入口；选择列表服务及allocator本体是替身 |

只执行dispatcher的有限区段，到`50B3B6`前接回测试桥；没有执行完整509FE0
返回、后续各状态Update、输入调度或世界推演。原生虚表角色来自固定归档。
对象、世界、UI、临时vector增长、分配器和下层生命周期是明确fixture。
**allocator_free_double只记录实际触达的释放入口，并未真正释放对象内存**；
分析输出`freed_objects`是这些释放目标的简写，不能理解成真实游戏堆free已证实。

成功分支由fixture明确选择，权威回执没有驱动这次原生关闭。我们没有让任意
返回值或手工析构冒充生产收尾，也没有将这组来源执行计为“赏赐回执自动关闭
游戏菜单成功”。原始代码和提取片段只留在ignored run目录。

## 已跑出的关键反例

| 自建原生场景 | 实际状态栈/调用结果 |
| --- | --- |
| 一个请求、栈顶仍Reward | Reward清理，计数6→5，同一User恢复；Reward为allocator释放目标 |
| 入队后再push DifferentMenu | 消费时清理DifferentMenu，计数7→6，Reward仍在栈顶且layout未清空 |
| 入队后把Reward栈位替换为DifferentMenu | 清理DifferentMenu，计数6→5，也回到同一User，但原Reward根本没清理；**只看回User仍会误判** |
| 两个关闭请求 | 原生循环依次pop Reward、User，计数6→4，落到Strategy |
| 第一次pop后再追加一次 | 同样把User继续pop掉，不能用重复回执重复入队 |
| 只入队不消费 | Reward仍在栈顶，没有完成关闭 |
| 空队列消费 | 不改变菜单栈 |

因此必须由同一个原生Owner持有“已绑定菜单→排队→消费→清理”的生命周期。
入队前/后各读一次相同指针不是锁，不能补齐这个缺口。本轮所有结果的
`can_queue_close` / `production_permit` 都为false。

## 新只读接口

`reward_menu_completion_analysis.py`：

- `read_authority_result(path, scope, attachment, player, request_id, preview, fresh_report)`
  以SQLite `mode=ro`读取已有本地执行日志，核APPLIED当前tip、无未决项、准确
  request/intent/seq、房间/期次/attachment及另行提供的新鲜本机report。
  force/district/funding_city/officers作严格canonical比对；日期也须和原生命令
  一致。只排队/接受还不算执行结果，旧请求在后续命令完成后也拒绝。
- 结果是不可变的`AuthorityEvidence`副本。这不是认证IPC；本地路径、scope、
  attachment、fresh_report必须来自可信宿主，不能直接接收网络客户JSON。
  就算有人自行构造此类实例，分析器也没有原生调用或放行能力。
- `analyze(trace, authority, context, source, now_tick=...)`只接受本轮明确的
  owned trace版本，核进程出生/base/root/world/thread/menu/User、既有
  CaptureSession的可信菜单上下文、期限/视角/期次和逐事件来源、序号。
  分类会区分正确目标的已观察清理、错菜单、多次pop、尚未关闭和证据不全。
  即使全部匹配，分类仍为`MATCHING_TEARDOWN_OBSERVED_WITHOUT_LIFETIME_LEASE`。

测试实际复用CaptureSession→localhost TLS→两个业务模型→当前APPLIED日志，
重复提交仍只有一条权威请求。随后只读关联native来源试验，**不是权威驱动
native close的跨进程组合**。菜单context与本机身份关联目前由fixture提供。
对生产采样需做明确的新版本，不能把owned trace标签换成live就使用。

## 最小后续只读观察

`reward_menu_completion_audit.py`的`POINTS`给出7个精确RVA、小锚点和寄存器
字段，不含启动游戏/安装函数。下一轮可分两组，各不超过4个硬件点：

1. 来源与归属：`67A993`确认前、`67A998`包装返回、`10AE4`入队完成、
   `50A9D2`消费选顶。保留同线程/RSP配对、准确menu实例、队列初末计数/
   存储、请求kind/object、消费时R12和正式栈。仅观察普通自然确认时原生
   已可能执行赏赐，该数据仍不能重发。
2. 清理与返回：`50B1B5`finalize调用前、`50B1FF`栈计数减少后、`50B21F`
   下层resume返回、`50B26A`allocator返回。最后一个点的R12可能已失效，
   只能比较此前保存的数值身份，不能再次解引用该对象。

必须复用现有已审查的DR租约/恢复方式，记录新run/pid/birth/base/线程、
连续事件序号与丢失/异常。源不同、漏样本、取消/其它请求混入都不充分。
真正的后继接线仍须找出可持有这个窗口的调度Owner；**本轮没有实现该锁，
也没有安排用户游戏操作**。

## 验证、指纹与失败

复跑（显式私有归档，只创建自有进程）：

```powershell
py -3 work/mod_research/reward_menu_completion_test.py --archive-root "<private-archive-folder>"
```

最终 **59/59 PASS**：24静态核对、7个真实CPU归档执行场景、28个只读日志/
TLS关联/拒绝检查。路径：
`reward_menu_completion_runs/20261008-214037-856396/result.json`。
31份源码前后摘要一致；image与pdata结束重新哈希一致。

| 文件/产物 | SHA-256 |
| --- | --- |
| result.json | `01080bf2c48ffe5fd429e09d3e57c2f4b86712c8374cd7f445d9d7ad94948516` |
| fixture.exe（不提交） | `c97069df57e517c9ea2ad1cc10da5b2d3b876198d98c78ec4c6fc78a2a824002` |
| completion_audit.py | `127d5925ee2cc0ac2143c9498fb41fa168c9b899aa9815dea940826fd5fb9eed` |
| completion_analysis.py | `7271748c4c7eab02022a4c7314b71e34790109880b11d2e25b94cf8365d938c9` |
| completion_test.py | `20c6a0eb6ef69143cb5a128e84b5eaa26dcb06bba93ae6ba9a9b60e20271480d` |
| completion_fixture.cpp | `5a76108e51d17717182a34ea30a3c78dcc5f8473ef068050d9c2a695c8a9e9c4` |
| completion_fixture.asm | `4eb99bd104fe5959896cd670daed2ff5af78c279a8024a30f76d87929075c144` |

私有image SHA仍为`5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`；
pdata为`74e018f15ec009af5fd0e0d91ce981b82d7d970150b3dce5861f17d11eea2e9f`。

失败保留：`213806-430821`先过23静态和3个CPU场景，换栈顶push时自建虚表
漏填Reward的resume+18槽而AV。补入归档已证的665CD0 leaf，并增加静态槽
核对后，`213838-212206`为57/57中间成功；资金城市与日期反例补齐后才是上列
59项最终版本。没有改冻结前驱或任何游戏内存。

自建进程与TLS已收尾；无活动补丁、调试器和待用户操作。
