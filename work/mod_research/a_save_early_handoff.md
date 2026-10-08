# A 保存前 User 早段报告写入审计与拒绝检查

2026-10-08。本轮仅使用私有归档和自有进程；没有访问游戏进程、Steam、游戏目录或 UI，没有安装游戏补丁。相关 fixture 已退出。

## 发现与范围

旧 `a_save_action_gate_handoff.md` 对 `2A1EC0` 的“选择清理”概括不充分。归档实际路径是：

1. User `3F9BA8` 检查 `User+660`；非零时 `3F9BB0 -> 2A1EC0`。
2. `2A1EC0` 遍历全局 `base+1FC98B0` 报告树。符合当前所有者的记录经 `2A236F -> 835800` 写入 Root 持有的报告记录。
3. `835C2C` 实际写 `World+165A` 报告索引。本轮证明的是内存数据写入，未独立证明这些字段的磁盘序列化范围。
4. `2A24B7 -> 240310` 清空节点向量、复位哨兵链接和 `base+1FC98B8` 数量；返回后 `3F9BB5` 清零 `User+660`。

此路径全部在现有 `3F9DAF` 动作切点之前，不能仅靠现有尾段拦截排除。冻结 FreshSave Driver 的 planning 检查也没有覆盖 `User+660` 和报告树。

所有者判断的精确定义：读取对象 `+118` 字节作为 `Root+DE40` 数组索引，将所得指针与 `2F21A0` 返回值比较。另见 `2F21A0` 从玩家势力字段取值，经 `Root+DCA0`、`20C110` 转换。本轮不把 `Root+DE40` 的完整对象类型武断认定为势力；反例名为 `report-other-owner`。

## 可复跑归档执行

`a_save_early_audit.py` 只读环境变量 `SAN14_PRIVATE_FIXTURE_ROOT` 下的 `game-runtime-image.bin`，校验完整 SHA-256 及 11 段固定代码哈希。代码仅复制到模拟器内存，未输出归档机器码到仓库。

User 从真实入口 `3F9B00` 执行到现有动作切点 `3F9DAF`；报告遍历、插入、清空函数内部不人为改跳转。外部文本、音频、对象查询、分配和 UI 调用采用结果中逐调用点列出的模型，其中间接调用也明确标为模型。合成 TLS、对象布局与文本输入不是实际游戏状态；模型内部可能产生的额外副作用没有被认证为无害。遇到未列明直接外部调用会失败，不会默认跳过。

最终 8/8 通过：

| 用例 | 真实归档路径产生的结果 |
| --- | --- |
| idle | 空报告、空渲染列表，零非栈写入 |
| updater-active-empty | 另一更新分支但列表仍空，零非栈写入 |
| report-empty | flag=1、空树，5 次非栈写入；复位哨兵和 flag |
| report-one | flag=1、队列=1、所有者匹配；18 次非栈写入，其中 11 次报告记录写入，World+165A 从 0 到 1，队列与 flag 清零 |
| report-other-owner | 初始 flag=1、队列=1、所有者不匹配；实际执行 `2A1EC0`/`240310`，未进入 `835800`，6 次清理写入，无世界或报告记录写入 |
| flag-zero-queued | flag=0、队列=1；User 跳过报告处理，队列仍为 1，零非栈写入 |
| selection-pick | 实际 `3FB9B0` 写入 3 个 User 选中指针；下游 UI 重建是模型 |
| selection-clear | 实际 `3E8EF0` 产生 45 次 User 写入，清空选择字段和相关结构 |

`report-other-owner` 除检查终态，还显式断言初始状态、原生 flush/clear 入口到达、原生 insert 入口未到达以及写入归属，避免用例名字变更后退化为 idle 仍通过。

**为什么 flag=0 也要检查队列：** `flag-zero-queued` 表明 `User+660=0` 只说明本次 User 不处理报告，不能说明报告渠道已经排空。已有记录会留在树中，之后 flag 变化仍可能触发这条真实写入路径。因此必须同时拒绝 flag 非零和队列非空；不能只看 `User+660`，也不能主动清空它们让检查通过。

最终记录：`a_save_early_audit_runs/20261008-103538-646117/result.json`。

- result SHA-256：`e62f5257e2f37c1af718312befcf14a61950f725ae3b5f29fdf19ba1af7eb155`
- script SHA-256：`90738e6ae318ffbb4252d1629a6f819ea86f72cb2e6de1162844bdda1636adb4`
- 完整私有归档 SHA-256：`5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`

复跑（在仓库根，私有归档路径按接手机器调整）：

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机私有研究输入目录>'
py -3 work/mod_research/a_save_early_audit.py
```

## 新只读拒绝检查

`a_save_early_guard.{h,cpp}` 是绑定一次、不可复制的本地组件。`Initialize` 接受既有 attempt/attachment/owner_generation、base/root/world/user；`Observe` 拒绝来源、身份、阶段、报告状态和两次采样漂移；`Retire` 后不再给出安静观察。

检查包括三个已确认指令短片段及整个片段所在内存范围的 RX、同 AllocationBase、生产 MEM_IMAGE 属性；Root/World/User 身份与 vtable；状态栈 count=5、无待办状态命令、栈顶为绑定 User、phase=2；User flag；报告数量；空树哨兵三个链接及 nil 字节。短片段检查只认证已知边界，不是完整程序身份认证，未来外层仍须保留完整版本/原生所有者验证。

安静候选采样两遍并逐字段比较，之后复查 Retire 和源片段。**两次观察相同不等于原子排他锁，也不能排除 ABA 或随后发生的写入。** 组件不持有对象生命周期，不发现目标进程，不申请安装补丁，不写入对象或报告树。

所有结果的 `fullWriteExclusion`、`saveAuthorized`、`roomReady` 永远为 false。生产 permit、冻结 Driver、IPC 与 Room 均未修改。测试明确输出 `save_owner_composed=false`、`production_permit=false`。

未来可信本地 permit 可以组合调用：

1. 在既有绑定/对象生命周期和实际排他条件下调用 `guard.Observe(binding)`。
2. 结果不是 `QuietReportsObserved` 就拒绝本次保存许可。
3. 即便得到 `QuietReportsObserved`，仍须完成既有 Owner、世界、命令排空及完整写入排他检查；禁止直接把这个结果转换成 permit=true。
4. 让合法原生流程自行处理待办报告后再尝试；不清 flag、不丢队列、不强行调用 flush 作为“修复”。

## 原生自有进程验证

`a_save_early_guard_test.py` 同时构建生产库和 fixture 版本。fixture 用自有内存布局及固定短源片段检查观察器，不执行 SAN 原生保存，不冒充当前 SaveOwner 仍有效。

最终 14/14：quiet、flag、queue、shape、phase、world、user、source、writable、noaccess、binding、retired、drift、retire-during。包括实际页属性/不可读内存反例，两次观察之间改变状态或 Retire，以及检查不修改待办字段、quiet 也不授权保存。

最终记录：`a_save_early_guard_runs/20261008-103016-643583/result.json`。

- result SHA-256：`403abe641ba991f50739232d697d0c45ee728f618ccca501f439313d2f5ea106`
- 生产 lib SHA-256：`17b0e71b12cf0dc230a56a4d6f342ce3c5522693585eb8cc6c32b581039c1d39`
- fixture exe SHA-256：`fdcdf8159da0f24d93b3dee153212f930658befe9836326c95d66dd9c56bcc8d`

```powershell
py -3 work/mod_research/a_save_early_guard_test.py
```

## 保留的失败与修正

- audit `102300-852443`：报告用例遇到未列明 `F1BB40`，增加明确的有限 memset 模型。
- audit `102316-637523` / `102331-167889`：合成输入缺失预期文本指针；后者定位到 `8359BD`。补上 `base+18EB8B8` 所指的已映射空 UTF16 文本，没有放宽源哈希或指令路径。
- audit `102343-401820` 首次 8/8；`103240-105347` 为精确所有者名称版本；`103538-646117` 增加强起点和实际入口断言后最终 8/8。
- guard `102821-002608` 12/14：memcmp 整个 View 结构误比较 padding，造成 quiet/retire-during 假 Drift；改为比较命名字段。`102838-374112` 14/14；禁止 Guard 复制后 `103016-643583` 最终 14/14。

上述目录均保留，不把失败目录称为通过证据。

## 精确剩余与下一步

- `15FA20` 已确认是 TLS 守护的单例 getter；`16C5F0` 按模式分派 `163C80`、`16C6D0` 或 `16BEF0`。目前只证明前两者 `singleton+A0=0` 的空列表分支无非栈写入；非空列表的场景对象虚调用、模式 >3 的 `16BEF0` 尚未审计。
- `3FB9B0 -> 3EC960` 的 UI 重建、可选注册表投影，以及 `3E8EF0 -> 337BB0` 的非空图形对象释放仍未证明不会间接写世界/命令；本轮 selection 用例不能代替此证明。
- `User+660`/报告队列写入者和对象生命周期没有被此读检查锁住；要接生产 permit，必须由同一可信所有者提供排他范围并处理采样到原生保存之间的竞争。
- 全设备、窗口消息、键盘/鼠标消费与原生后台路径的完整排他，以及任意游戏进程的补丁安装/线程排空，仍须按既有 action gate 边界继续完成。本轮不增加 live 入口。
- 本轮减少了“早段是否只改 UI”的未知并增加一个可直接组合的拒绝条件；没有获得完整保存许可，也没有重跑真实 SAN 保存或双机联机。

新增文件范围冻结为本 handoff、audit.py、guard.h/cpp、guard_fixture.cpp、guard_test.py；冻结旧模块、根文档、tools、Git 均未修改。
