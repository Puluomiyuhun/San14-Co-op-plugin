# A 带 AI 保护的网络启动入口

`observed_protected_host.py` 是 `observed_host_start.py` 的明确后继。默认/help 不访问进程；`--check` 只核本机配置、测试来源和构建文件；`--execute --no-new-commands` 才读取显式 PID、创建真实 TLS 房间并调用 `a_protected_start.execute`。

本轮用户要求延后实测；本入口尚未运行在游戏中。根测试实际创建 TLS、选势力、等待/交换收尾通知、断开并关闭服务；原生生命周期和两条完成标记是显式替身，不能算实机完成证据。规则与保存共存的独立 owned 验证见 [保护入口](a_protected_start_handoff.md)。

## 配置

沿用 [前驱手册](observed_start_handoff.md) 的完整 A 配置，作以下明确变更：

- `schema` 改为 `san14.a-protected-host.v1`。
- 新增 `rules_build`，仅含 `stage`、`publisher` 两个批准生产文件的绝对路径。SHA/可执行文件/计数器绑定由生产 `RulesBuild` 固定，配置不能切换为 fixture 或自填替代 SHA。
- `native.entry_test_run` 指向本轮通过的 `a_protected_start_test.py` 结果目录，要求同时绑定新旧入口来源及 `protected_integration_executed=true`。
- 新增 `network_entry_test_run`，指向本轮通过的 `observed_protected_host_test.py` 结果目录；启动检查重新核对当前所有已测试来源，不拿旧 CLI 测试冒充新入口覆盖。

B 仍用当前 `b_observed_start.py`。没有顺带开启独立赏赐服务或窗口输入 Owner。新字段以外的任意配置字段拒绝；范围仍是34号张鲁起点、刘备客机、两份快照、无新命令。

仅离线验证命令：

```powershell
py -3 -X utf8 work/mod_research/observed_protected_host_test.py
py -3 -X utf8 work/mod_research/observed_protected_host.py --help
```

内部显式入口（本轮未执行）：

```powershell
py -3 -X utf8 work/mod_research/observed_protected_host.py --check --config C:\private\a-protected.json
py -3 -X utf8 work/mod_research/observed_protected_host.py --execute --no-new-commands --config C:\private\a-protected.json
```

占位路径不是可直接运行的配置。真实执行仍须 fresh 游戏进程、本机构建/来源和原入口检查，不能复用旧机器 PID、claim 或一次性模块。与旧入口一样，A 自然自动档变化不被静默忽略，B 旧 CC03 须正常退出后恢复。

## 结果和收尾

A 的原生入口负责安装与恢复证据；CLI 不因“配置了规则”就填安装成功。只有新入口返回0、规则报告 `installed_once=true / restore_verified=true / retained_or_unknown=false`、B报告本地原生清理完成，并且网络关闭成功，才报 `PASS_PROTECTED_TWO_SNAPSHOT_NETWORK_ENTRY`。网络不独立证明 B 的原生清理。

A 返回后发布 host-finished；B报告完成后仍等该标志再断线；A等实际断线才关房间。原生失败不重放，网络关闭不表示残留规则或 DLL 已撤回。`two_real_clients_proven`、`reward_flow_enabled`、`complete_input_fence_proven` 不会因此被置真。

测试历史保留首轮013513三个失败：fixture把 `applied_receipts` 字典当列表使用，且未等待客机查询完上下文就制造原生异常。修正测试替身的集合类型和先后顺序；未修改生产网络规则来放行。最终结果位置与SHA以 HANDOFF/公开证据为准。
