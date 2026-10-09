# A 第二期保存：追加本地接口

2026-10-09。明确后继为 `a_save_repeat_exports.cpp`，前驱是冻结的 `a_save_abort_runtime_exports.cpp`。旧操作1–8及其数据布局原样保留；新增两个接口，不覆盖旧文件。

- `ASaveRuntimeRequestNext`（9）：152字节。只复制上一份文件的代号与SHA、下一期代号/房间逻辑期/输入摘要/日期；不接受回调地址、任意代码或“B已加载”的布尔值。成功返回只代表请求入队。真实上一份artifact匹配、退休和下一期绑定由Runtime在原父线程控制边界完成。
- `ASaveRuntimeRepeatSnapshot`（10）：224字节。输出当前切换阶段、错误、原宿主线程、退休记录、上一artifact与原生日期匹配结果，以及独立repeat租约/观察/待收尾状态。沿用原Prepare随机nonce和串行调用保护。调用方不能靠预填输出字段获得成功。
- 原Snapshot的`restoreReady`新增repeat租约/观察/待收尾均为空的条件。必须配套严格检查该条件的新发布器；不能与仅在部分终态检查它的旧发布器混用。

`a_save_repeat_contract.py`是纯数据编码和状态解释，不启动进程、不安装模块、不推动日期。`describe`拒绝缺少匹配记录的ReadySecond、未知状态、错误结果或本版本不支持的B/推演成功声明。即使第二期保存绑定就绪，也始终报告`two_player_ready=false`和`can_advance_game=false`。

## 实际边界

`RetiredWaitingDate`不是游戏会自动继续的承诺。当前上期ReadyFence/Gate仍持有，缺少原生日期推演接管接口，不能提示用户此时手动点击推进，也不能写日期字段制造成功。新接口只补保存Runtime的跨期衔接；尚未连接完整房间消息、B原生加载确认或所有writer排他。

现有 `planning_simulation_boundary::Execute` 只是可信宿主的同步回调边界；其测试回调写诊断日期，不是游戏跨帧推进器。下一步应把实际推演开始、运行中事件/报告、返回规划地图的三个阶段接到原宿主，并重新证明期间输入与world身份，不能把这个同步回调直接包装成“推进一旬”导出。

生产DLL的旧1–8 ABI测试由Runtime构建器执行。新增验证入口：

```powershell
python work/mod_research/a_save_repeat_exports_test.py --dll '<本次repeat生产构建的DLL绝对路径>'
```

它在自有新进程加载生产DLL，实际检查新增导出、错误包/nonce、真实Runtime拒绝非法Prepare、输出清零和Stop后拒绝；另编译C++字段布局逐项核对Python，并验证状态描述不会把等待或未收尾写成可推进。这不执行成功的原生保存/推演路径；正向Runtime组合验证由实现者的独立套件记录，存档业务与日期替身必须继续标明。

最终构建、实际结果和源码/产物身份见总交接的本轮证据。任何旧游戏进程、旧claim和旧已加载DLL均不适用这份新接口。
