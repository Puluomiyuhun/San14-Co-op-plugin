# 连续两次真实加载通过：稳定采样启动后继

2026-10-09。新 `b_warm_stable_refresh_coordinator.py` / `b_warm_stable_refresh_diagnostic.py` 只替换每bank安装前的规划采样接点。原始 `b_warm_refresh_*` 和已通过的原生DLL均未改。文件刷新/安装/加载/退休/Handover没有任何重试；仍用相同的完整守卫和报告验收。

## 采样与批准构建

每bank把 `b_warm_stable_capture` 的逐次结果保存为 `planning-sampling.json`，固定当前进程身份。仅精确双样本不一致错误可在0.75秒/最多3次内重新调用原双样本读取；日期、势力、birth、profile等其他失败立即拒绝，全部旧字段保留。该阶段没有FileWrite或Install。详见[采样交接](b_warm_stable_capture_handoff.md)。入口整体安装前原有两次前检仍保留，可能只读拒绝，不创建claim。

- 采样8项结果：私有 `b_warm_stable_capture_runs/20261009-220004-423346/result.json`，SHA `d6cb178390febdab93e9f0b9dc67735595e360607c7b51016825e2a88d6ccffd`。
- 新Python接线回归9项：`b_warm_stable_refresh_python_runs/20261009-220120-150754/result.json`，SHA `aa56f4e8200725096526c5f47b4013f2f597c75eced87256f896ab571a191fab`。
- `b_warm_stable_refresh_build.py`核验两者及原native pair后，复制相同DLL，固定三组来源；没有重新编译或伪称额外原生测试。新批准bundle：`b_warm_stable_refresh_build_runs/20261009-220219-504303/result.json`，SHA `66c42b886ee818da39fe987d79d296e2aab71eac4d7d8d0cff784abe2c69363a`。
- DLL在该bundle的 `production/checkpoint_complete_live_owner_v2.dll`，SHA仍为 `9c6c69e652466b0d392eb3e5e11cb91a2d334187cee84b4f7cf677846cf9df0e`。helper结果继续是 `b_warm_coordinator_build_runs/20261009-181031-457801/result.json`、SHA `4204df275c981b6c35c6bea01a25e040a0cea04be84e20ff2998079917e3b43a`。

这些都是原电脑私有相对路径，不是跨电脑安装许可。新机器须重新建立本机来源、编译、进程和存档身份记录；本次PID/claim不能复用。

## 实机经过与准确范围

首个新刷新试验 `b_warm_refresh_diagnostic_runs/20261009-215610-770741` 的第一bank成功，真实将旧原生274880字节更新到274920并加载刘备，锁释放且六槽恢复。第二bank获原生Handover后在安装前双采样拒绝，只有DLL而没有config/安装/刷新意图，整体INCOMPLETE。这不是刷新失败；具体哪一个采样字段变化未保留，不能猜成已定位。用户正常退出并重启，没有重投旧claim/模块。

最终 `b_warm_stable_refresh_diagnostic_runs/20261009-220403-678247/result.json` 返回 **PASS_TWO_WARM_REFRESH_LOADS**，SHA `3be79278e3ca829a8a0a96e1408cd41d7127c1b62b4acc0a3ab29a071deb6970`。新PID37636/birth134360279974184088：

1. 34源档加载并将张鲁改为刘备，203-08-11；刷新旧/新均274920字节。这一代重写相同字节，前一个进程的首载已经独立证明不同字节的原生刷新。
2. 上轮用户正常保存的新49源档加载，203-08-21，仍为刘备；原生档从274920变为274975字节。第二档日期至此通过实际加载证明。

两个bank都完成真实FileWrite一次、旧/新完整双读、原请求CAS、Load与Title生命周期、身份初始化、规划、封存和六槽恢复；目标锁在退休后释放。真实helper最终第二代完成。116/99轮只读观察验收，用户确认最终下旬刘备大地图。两bank稳定采样均一次通过，重采反例由离线测试证明，不能声称本次实机发生重采。

独立现场后验验证五态、日期/君主、六原槽、六处规则原入口、无调试器，且只有CC03与最初84档备份不同。用户正常退出后，在进程关闭状态恢复原CC03，最终84份大小/SHA全部与本轮最初备份一致；34未改、新49保留。清理记录在成功run的 `closed-restore-220828-370044/result.json`。成功/失败日志、once claim和临时新档全部保留，无活动进程钩子或调试器。

本次是一个真实B客户端、两份本地准备的真实档案。A第二档仍是用户手动保存，没有本轮联网、自动推演或地图遮罩测试。完整世界一致、全输入暂停和正式Room Ready都没有授权。

## 下一步

1. 在单独fresh生命周期验收已修复A自动保存；不要混用此次已消费的B生命周期。
2. 将新的原生刷新Resident接到远端收档owner，替换那里的旧物理暂存/跨load目标锁。已有远端TLS/ACK测试不代表这条新接线已自动完成。
3. 配置真实两机连接，先两期无新命令测试，再逐项增加玩法和界面体验。

本机诊断使用此新入口，plan格式仍与[刷新入口](b_warm_refresh_python_handoff.md)相同，必须传绝对plan路径、fresh PID和新bundle SHA。先`--check`，后`--execute --no-new-commands`。不要重跑本文成功或失败的旧进程/claim。
