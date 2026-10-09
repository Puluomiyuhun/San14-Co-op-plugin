# Warm 启动验收独立离线测试

2026-10-09。本agent仅新增`b_warm_start_test.py`和本记录；未修改root维护的start、support、acceptance三份实现。没有调用GameReader、ProcessAPI、live invoke、游戏/Steam/UI或实际远程控制函数。

测试以旧真实自有fixture的4032字节Owner report作为POD形状，随后**明确合成**生产安装事实、模块地址、游戏caller与退休回执。动态target9的文件SHA/size/date也为合成分类器数据，保留真实seed中的Pair对象指针语义；不是第二份合法存档，也不是实机完成证据。

## 审查中定位并由root修复

- approved_build最初读source_pins/private_pins，但真正factory manifest是sources/private，导致正确构建必被拒绝。最终严格family下读取实际四个closure字段，真实factory manifest正例已通过。
- completion最初只比较两个accepted字典；重复相同Owner sequence也可通过。最终每个Owner样本要求sequence严格递增，重复或回退拒绝。
- source/target Pair一度被比较为Profile数字ID，这是错误的：Pair.force/person是对象指针。已撤回该比较，依靠原生profile guard关系校验、完整profile报告、规划指针对应及实机后读的日期/君主ID。测试特意保留指针值，防止此错误回归。
- root另外调整失败收尾，在已知完成的Stop请求后才关闭本地文件lease，并明确Stop不能证明native drain或准许重新staging。本测试只固定此版源码身份，没有执行整个execute异常恢复流程。

## 34项测试范围

动态profile target2与不同size/hash/date/target9正例；profile报告不匹配、retire attempt/User/Identity/Load call错配、未sealed、恢复槽仍是bridge、实际bytes SHA错误、目标force错误、嵌套完成call错误、raw POD与解析字典冲突、guard错误、活动dispatch、bridge计数不平衡均拒绝。

completion使用纯内存假调用器返回真实POD格式：两份新鲜完成样本通过；重复/倒退sequence拒绝；未完成样本不计入稳定次数；冻结key改变后须再取得两份一致样本；原生错误终止。

Calls使用显式假异常覆盖未知状态、未开始、已开始未完成、已完成四类，以及uncertainty保持不被后续正常返回清除。没有测试或许可在真实不确定控制调用之后继续发调用；后续假成功仅验证标记不被清除。

approved_build实际读取最终factory成功manifest并逐项检查其构建闭包；另外使用自有临时文本文件与明确合成manifest检查family、factory_complete_passed、inputs_unchanged、缺少closure、source pin漂移拒绝。这些临时文件不是真DLL、不代表本测试批准任何实际安装。

## 最终记录

最终private `b_warm_start_test_runs/20261009-173141-716883/result.json`，SHA256 `e73d08fc80590472abfb7ff0e9702f955441197c222d9c88a7935c47ecfa77c3`。34/34 PASS，10源码和2私有输入pins重新核对一致，inputs_unchanged=true。没有生成或执行新native二进制。

最终review版本：

- start.py：`53ba7ce7df012f52cdfaa4fe79e169a60a94be6bff95b47078a71c5272bf1379`
- support.py：`413c453f9fc17b9e900c1e4340f8659ddf8ba6d22725d6d9aa1aa64b95dc6ecb`
- acceptance.py：`2fb3d8ae131228f6635dc161f3417282a3a609d591ee6ed611c8b05f445c8bb0`
- test.py：`0b98f44a81bb3bcd5a77ef64651c349a533af5aa300ae297b28e0c5401d74df5`

173028-484322保留为root最终lease收尾调整前的34项成功记录；没有沿用该记录证明调整后源码。当前测试和EOF/尾空白检查已冻结。入口：`python work/mod_research/b_warm_start_test.py`。
