# B收齐存档到A确认的跨进程接线

2026-10-08。新增 `checkpoint_delivery_control.py`、测试及本交接。没有操作游戏、Steam或游戏存档目录；使用自有诊断字节、SQLite、两个TLS通道和独立B Python进程。无待用户操作。冻结前驱未修改。

## 实际接通的部分

过去网络只把文件交给B，`PeriodCoordinator.received()` 仍由旧原型在同一个Python进程直接调用。现在B通过真实控制连接返回其已落盘的两个文件，A的独立 `CheckpointReceiver` 收齐并校验后，调用原有 `received('B', epoch, receiver)`。

这证明A实际收回与权威文件相同的字节。它不证明远端磁盘物理fsync、不证明游戏暂停或加载完成。B客户端自身会重新打开SQLite并重新读取校验，A的回复始终 `remote_durable_stage_verified=false`。

首版采用完整字节回传，多一次存档大小的传输。这里先接通明确的字节证据；之后再优化带宽。没有用网络 `verified=true` 或公开manifest哈希冒充完整接收，也没有将传输完成当成原生加载许可。

## 接线方式

控制监听器使用 `DeliveryControlEndpoint(room)` 包裹**同一个精确类型的** `RulesContextRoom`；房间/规则生命周期仍持原始room对象，下载监听器仍使用 `room.download_endpoint`。组合避免修改旧context的类型白名单，不创建第二份A协调器。

新增三个控制消息：

- `checkpoint_delivery_begin`：固定已明确取得的context摘要、检查点和请求编号，分配一次事务；相同请求可返回同一事务，不允许更换编号丢弃旧receiver。
- `checkpoint_delivery_chunk`：按原有32768字节分块格式回传；重复块须内容完全相同。每块重新核对B控制连接、scope、manifest、旬epoch、附件身份及generation。
- `checkpoint_delivery_finish`：实际两文件哈希通过后设置 `bytes_received`。同事务重复确认不重复调用 `received`；未知来源的旧 `bytes_received=true` 不能补做一张成功回执。

本地锁顺序为Room→coordinator→receiver。只保留一份receiver及上一代紧凑摘要，下一代必须先有原Room认可的独立加载完成谱系。错误token不关闭其他事务；已认领事务遇到数据/绑定错误则终态HELD、撤销下载。撤权失败单独报告，不宣称原生暂停。

B侧使用 `GuestDelivery(connection, expected_profile, journal).run()`。connection必须是本机真实B `RoomConnection`，profile须使用建立TLS连接时固定的兼容性资料，journal为已STAGED的真实 `CheckpointJournal`。helper从此connection内部建立自己的 `remote_context`，不能传入另一房间的context。它重新打开SQLite、校验两个parts，传输前后检查STAGED与内容，确认后仍保持STAGED，不创建INTENT。

helper错误保留日志并请求协议撤权；连接丢失时撤权未获确认就如实报告。对象不能重复run，不自动重连/补发；控制连接成功后由外层继续持有，不能在正常下载完成时关掉它。

## 验证

```powershell
py -3 work/mod_research/checkpoint_delivery_control_test.py
```

不需要私有运行时镜像或存档；需要现有Python/cryptography环境。最终运行 `checkpoint_delivery_control_runs/20261008-113927-254734/result.json`：19项，0失败、0错误、0跳过；12个源码指纹前后相同。

- 独立B进程实际TLS下载81959字节、SQLite落盘并重开、经控制TLS返回全部字节；A真正进入 `bytes_received=true`，B日志保持STAGED，控制连接保持在线。B没有取得A的Room/协调器对象。
- 五个独立B场景：成功、空SQLite、SQLite内容损坏、错误profile、确认后真正丢失TLS回复。丢回复时A已确认字节但房间退出可用状态，B保持HELD/STAGED且不虚称撤权ACK；重复run不发送请求。
- 并发确认仅一次 `received`；错误角色/token/新请求替换被拒；缺adapter、坏字节、冲突块、附件变化、断线、外部已存在INTENT、确认成功后异常均拒绝或终态撤权。
- 第二代测试的旧世界加载回执由测试MODEL建立，仅验证已有合法谱系后可换代；生产模块没有 `loaded` 调用。原生Ready消息不能绕过旧门槛。

保留失败：`113702-420501` 15/18通过，测试错误假设旧协调器进入推演后清空ready集合；改成核对未新增Ready、仍处RECONCILING。`113743-817548` 16/18通过，两个失败场景又错误预期关闭后仍RECONCILING，真实ReadyBarrier会进入HELD；按真实关闭语义校验后 `113828-315809` 18/18通过。新增真实EOF反例后为最终19/19。

独立审阅修复一处实际接口问题：原helper接收任意ContextSource，错接X连接与Y上下文会在X请求失败后关闭Y。现由constructor从本连接建立context，构造失败不触发其他房间撤权。审阅者另独立验证并发确认与 `received` 成功后异常的撤权路径。

## 剩余边界

本模块从未调用 `begin_guest_load`、`reserve_load`、`loaded` 或原生加载器。还需A真实边界/持续等待、B旧规则恢复与原生安全状态、单次许可跨机交接、B原生加载和完整世界核验，以及两端Ready释放。不能把此19项通过写成真实双人整旬闭环。游戏运行状态仍以重新核验为准。
