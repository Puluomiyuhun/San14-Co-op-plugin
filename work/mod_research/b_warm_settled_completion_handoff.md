# B 已推演到旬末后的校正日期合同

`b_warm_settled_completion.py` 是 `3acc907` 的 `RemoteCompletionRoom` 明确后继。由 A 的本地启动器选择 `SettledRemoteCompletionRoom`；房间请求不能自行切换策略。

## 改动

首代 bootstrap 仍从旧规划日期的 A 视角加载到目标日期和 B 视角。后续普通校正要求真实 `Profile.before == manifest.node` 且 `Profile.loaded == manifest.node`：B 已自行推演到旬末，再读取同一日期的 A 权威档。

旧 `RemoteCompletionRoom` 保留 B 在旧日期等待的受控诊断合同。新类不能自动同时接受旧日期、目标日期或任意日期，不能靠伪造旧日期绕过检查；只覆写 `_begin` 的日期政策，其他来源/文件/房间/身份、一次性预约、HMAC、重复回执和完整完成验证沿用原实现。B 的 `RemoteGuestCompletion` 与两种 Journal 无须修改。

这不是战斗推演器，不验证双方模拟过程相同，不建立原生输入暂停，不改变 Ready 权限。加载前日期由可信 B 原生所有者如实采集；服务器看到的签名配置本身不是现场证据。原生 warm profile 原本分别保存 before/loaded 日期，允许相等；真正游戏与规则的联合路径仍须实机验证。

## 入口与验证

```python
from b_warm_settled_completion import SettledRemoteCompletionRoom
room = SettledRemoteCompletionRoom(manifest)
# 后续绑定 Coordinator、enroll_adapter 和传档按原远端手册执行。
```

```powershell
py -3 work/mod_research/b_warm_settled_completion_test.py
```

测试复用原真实 TLS / 独立 B 子进程以及 SQLite Journal，保留 B 跨两期；仅改变明确本地选择的 authority class 和 B 第二期真实提交的 profile.before。原5项测试继续覆盖两期、错误密钥、错误完成身份、回复丢失和低可压缩摘要；新增普通旧日期拒绝、越期拒绝、bootstrap 错用目标日期拒绝。错误日期均在原生替身调用前拒绝。保存、加载、RAM 和暂停为显式替身；无游戏/Steam/UI访问。

最终8/8通过，私有结果 `../mod_research/b_warm_settled_completion_runs/20261009-201141-255559/result.json`，SHA-256 `42cd893fd285514dd5d07fbba04117fc2b12b93aafe929dd924b385f94879e51`。33份来源与92份产物哈希复核一致。见[本轮证据](../../docs/evidence/2026-10-09-warm-retained-owner-settled-key.json)。新电脑必须重建自己的进程、日期和原生证据，不能复制本机 JSON 放行。
