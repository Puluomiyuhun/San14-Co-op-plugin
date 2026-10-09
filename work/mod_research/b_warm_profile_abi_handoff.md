# Warm profile 的脚本 ABI 与独立模块检查

2026-10-09。`b_warm_profile_contract.py` 是数据类型和校验器，不访问进程、不安装模块，也不授权加载。它描述新 profile Config/Description/Report、嵌套旧 Owner Config，以及退休报告。文件映射仍严格限定槽63与 `svdexccSC03.s14`；仅文件内容、日期和身份可变。

`ready` 在 profile 报告里仅表示配置已不可变捕获。实际 Owner 安装失败时，该值也可能为1。因此 `status()` 明确保持 `load_completed_proven`、`can_install_next_bank`、`two_player_ready` 为false。完整加载回执、同进程身份、来源指针及当前世界的独立核验仍由未来启动器承担，不能拿配置报告代替。

## 本轮验证

从仓库根目录使用本轮经过审查的生产DLL及精确哈希运行：

```powershell
py -3 work/mod_research/b_warm_profile_abi_test.py --dll PATH_TO_REVIEWED_DLL --expected-sha256 EXACT_BUILD_SHA256
```

这只创建自己的测试子进程，不寻找游戏。两个DLL副本位于私有测试目录，加载到同一子进程后保留到进程退出；测试不给它们有效游戏绑定，不发布钩子或加载请求。

最终记录：私有 `b_warm_profile_abi_runs/20261009-154930-357815/result.json`，PASS。
输入生产DLL来自 `b_warm_profile_runs/20261009-154811-322893/composition/checkpoint_complete_live_owner_v2.dll`，SHA256 `0b3ec93697bf4361ba79c4164395315c52576159cac5fe2bf28607f19976d4e2`。文件名是历史builder别名，源码为本轮新后继，不能与旧同名DLL混用。

- 编译C++逐字段输出，核对Python八种结构的全部大小、字段偏移和字段大小。
- 实际两个DLL的module地址、物理bridge地址不同。第一模块失败的profile捕获不可重置，Stop不改变第二模块。
- 第二模块精确保存自己的文件/日期/身份配置；无效Owner仍被拒绝，没有arm或CAS。再次修改该配置失败，原配置不变。
- 实际描述/报告经Python解码；长度错误、非法状态、未知槽、零大小及无seal的恢复结果被拒绝。
- 子进程正常退出，无游戏访问。两个模块没有接管同六个槽，也未执行两个加载，不能用本结果代替连续加载验收。

此前 `20261009-154804-229667` 在中间DLL上也通过；随后生产安装意图文件增加新Config格式/哈希后，已换最终DLL完整重跑，不混用中间产物身份。

## 下一接点

先在可信启动器中捕获当前本机身份并构造完整 `Config`，配合准确文件配置；未来第二代仅在第一代真实完成、业务封存、六槽恢复及当前世界重新核验后使用独立模块。此次只验证了typed入口与配置隔离，尚未实现这个启动器或同六槽的两模块接续。
