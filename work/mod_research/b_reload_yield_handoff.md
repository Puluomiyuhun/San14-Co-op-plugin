# B 原生暂停与恢复后继

2026-10-08。只使用固定SHA历史归档和自有测试进程，未访问游戏、Steam、UI或当前存档目录。没有待用户操作，也没有新增游戏补丁或调试器。前驱冻结文件未改。

## 改动与证据

`b_reload_yield_parent.cpp`替代`b_reload_bound_parent_source.cpp`，沿用原ABI。不要同时链接。其余组件继续使用上一轮的nested四实现和worker Provider。

实际路径为：worker执行归档`50B690`，置yield并通过归档`834820`通知parent；parent结束本次调度，保留未完成worker；归档`509EF0`清yield并经`834640`重置同一事件，第二次归档调度命中`50B4AE`，随后唤醒原worker、继续原调用栈，最后走真实return/done/parent completion。

这里发现并修正了一个此前尚未实际触发的问题：resume之后必经`50B598`，旧来源会把这个位置再次交给Provider的fresh-creation路径，但没有fresh selection，因而拒绝。新来源只在**同一Scope已获Provider接受的resume**之后，固定state、vtable、formal slot、worker、callable，检查done/stop/yield状态，才消费一次`50B598`并标记`sample.skipped=3`。它不创建第二个ticket；错序、字段漂移及FINALLY时尚未消费都报错。没有放宽Provider代次验证，也没有直接写其成功字段。

## 最终测试

`b_reload_yield_runs/20261008-165445-303641/result.json`：**26/26 PASS**，139份源码及私有输入摘要前后不变，五份生产对象无fixture宏编译通过。

- 保留24个前驱检查，包括3个两代queue组合、直接Provider错代测试、独立Root和lease契约。
- `root-native-yield`：一个实际Root任务暂停、恢复一次，3个entry/return/done捕获、1个yield捕获，Provider仍只有原任务的6个计数事件。yield/resume另由实际捕获及状态检查证明，不挪用events数量。
- `nested-input-yield`：在实际User输入观察器尚处于armed状态时暂停，恢复后执行输入捕获并正常释放。两代各暂停一次；20个parent scopes、2个resume、16次fresh/create/complete、16个Root任务及48次Root三点捕获，8个Load任务。两次resume没有增加任务数；两次队列Finalize、三个Load/Title join及两代收尾继续通过。
- A agent独立审查resume来源，提出固定vtable建议，已纳入最终实现。

结果SHA256：`d0e1ee5789edc47a6517b3eafc2d58fea55e42007d208372a9e6d3700a1e6890`。

fixture EXE SHA256：`ab642570c112131ccb6e27f687efcf0fc399febfbecaa35bedc9b1589c2982f5`。

## 保留的失败

1. `20261008-165033-909780`：fixture定义位置早于输入观察类型，编译拒绝；只移动新fixture定义。
2. `20261008-165149-172465`：24/26，第二次parent调度没有重新准备fixture临时状态表，原生status调用AV。补齐测试环境，不改归档机器码。
3. `20261008-165306-629666`：25/26；实际嵌套暂停与两代流程均成功，但断言错误要求另一种planning User回调也必须yield。改为逐次Root业务明确调用数，并保持两代总数必须为2。此外该轮运行中接受vtable加固，源码摘要变化令整轮证据无效，保留FAIL。
4. 最终冻结后`20261008-165445-303641`：26/26，所有输入一致。没有删除失败运行或重置旧claim。

## 边界与下一步

本组的Root激活和业务/构造/存储仍由fixture提供；第二个文件仍是诊断变体，不能当作两份合法SAN存档。补充的三个归档函数原样执行，但同步对象与任务触发由自有fixture准备，不能据此宣称已接入实际游戏线程池。

继续组合独立的`b_reload_root_activation*`实际激活来源，并补嵌套异常、第三方DR漂移的实际执行覆盖；然后接统一Owner的规则撤下、持续排他、一次加载许可和世界/地图核验。没有授予fullWorld、Room Ready或生产加载许可。

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机私有研究输入目录>'
py -3 work/mod_research/b_reload_yield_test.py
```

需要MSVC/MASM及前驱固定SHA私有归档/profile；缺少输入明确失败，不去读取当前游戏。生成的完整profile、EXE/OBJ和原始运行日志留在本机。
