# B 每代加载前的本机采样

2026-10-09。`b_warm_profile_capture.py` 是 `checkpoint_complete_live_capture.py::planning_bindings` 的显式后继准备工具；冻结旧工具仍固定张鲁/203年8月中旬，不能用于 B 第二代。新工具仅读取，不安装 DLL、不执行加载、不暂存文件。未在游戏进程运行。

## 已实现

- 从明确指定 PID 重新读取当前五态对象、root/world/cache、UI、原生队列、随机状态、五个游戏入口原指针。日期/currentForce 来自本代不可变 profile，当前君主另行显式指定，不假定 B 此时仍是张鲁。
- 完整采两遍并核进程出生时间；管理器 current、各状态 task 和 pending 字段也参与比较。状态对象重建后使用新地址，不沿用上期地址。
- 当前生产 Owner 仅支持 mode0、指针/容量/数量全零的队列，所以这里同样拒绝已分配空队列和菜单/推进待处理状态；这不是自动寻找引擎安全点，瞬态不一致直接拒绝，不循环等待掩盖变化。
- JSON profile 严格检查字段、数值类型和范围后再转 ctypes，避免整数截断。仅槽63/`svdexccSC03.s14`，大小上限16MiB。profile中的存档日期/身份只是预期，实际仍要由 Bytes/Load/Identity/Planning 链验证。
- `wrap_owner_config` 将已构造的旧 typed Owner 配置与新 profile 组合为新 ABI；要求进程/地址/日期预期的 profile 摘要与本次采样相符。它不验证存储模块、不产生安装许可，也不以一段 JSON 冒认旧代已退休。

## 运行与验证

无参数只显示帮助，不发现游戏。离线测试：

```powershell
py -3 work/mod_research/b_warm_profile_capture_test.py
py -3 work/mod_research/b_warm_profile_capture.py
```

最终私有记录 `b_warm_profile_capture_test_runs/20261009-165305-305980/result.json`，SHA256 `f1a3deacdc7479a524657215659f30da87c9cf15d8aacd4fdaf14f9fc0920f36`。6项通过：初次与B换期换址采样；错日期/当前势力/君主；current/task/进程出生时间漂移；旧钩子/队列/待推进拒绝；profile/PID溢出与别名拒绝；typed组合拒绝旧地址和错profile。全部是内存读取替身，不是游戏运行结果。交叉审查发现并修复显式PID可能在OpenProcess的DWORD参数处截断的问题；CLI在打开进程之前检查，API亦拒绝超界。早期通过记录`164957-128827`保留。

未来明确需要本机只读采样时，使用 `--capture --pid <当前PID> --profile <私有预期JSON> --expected-ruler <当前君主ID>`。GameReader 仅获取 query/read 权限，原始地址与记录写仓库外 `b_warm_profile_capture_runs`；当前轮未执行这条命令。

## 尚缺的启动接线

此模块只负责 planning 侧。第六个 Steam Read 槽、缓存 storage 接口、已加载新 DLL 的模块身份/桥、实际文件及旧代退休仍由对应原生/存储层核验。旧 `storage_bindings` 有本机固定 Steam 路径；尚未完成第二台电脑路径配置或完整warm启动器。

两次相同读取不能证明原子快照或对象未曾销毁重用。采样之后仍可能发生变化，安装时必须重新由进程内 guard 核验。输出不授予输入排他、读档、自动覆盖槽63或下一代接管权限。
