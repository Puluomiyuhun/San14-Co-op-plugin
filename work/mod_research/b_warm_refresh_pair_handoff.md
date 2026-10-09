# 原生刷新与连续加载组合

2026-10-09。这是 `b_warm_factory_pair_test.py` 的显式后继；冻结旧来源未改。新生产组合使用 `b_warm_refresh_request.cpp`、`b_warm_refresh_retire_session.cpp`，并链接 `b_warm_refresh_owner.cpp` 与已有刷新core。新DLL没有fixture宏。

## 当前可复核候选

所有路径相对于原电脑私有 `../mod_research`，不在Git中；新电脑不得将这些路径或成功回执直接用于安装。

- 最终组合：`b_warm_refresh_pair_runs/20261009-215046-831686/result.json`；SHA `2af0e06f5f0823450f3195be5feeae796f36cefc230e0fafa52b6dde0ea88a2d`。
- 生产DLL：同目录 `composition/production/checkpoint_complete_live_owner_v2.dll`；SHA `9c6c69e652466b0d392eb3e5e11cb91a2d334187cee84b4f7cf677846cf9df0e`。
- 构建family `san14.b-warm-refresh-pair.v1`，`refresh_factory_pair_passed=true`；132来源、23私有输入、9生成文件、72编译产物、25运行产物全部独立复核。后者含持久refresh意图、原请求/身份/安装意图及真实目标/备份。
- 原helper继续使用 `b_warm_coordinator_build_runs/20261009-181031-457801/result.json`；SHA `4204df275c981b6c35c6bea01a25e040a0cea04be84e20ff2998079917e3b43a`。其25来源及产物重新校验，与新pair的全部相关C++/header来源相同。
- 新Python验证9项通过及生产ABI验证见各自[Python交接](b_warm_refresh_python_handoff.md)、[Owner交接](b_warm_refresh_owner_handoff.md)。根独立检查生产build无fixture宏、使用新request/retire，并解析PE确认三个新导出存在。

## 本轮实际跑了什么

同一个自有host创建初始701字节的私有CC03，两份新档为1025和1282字节。host的FileWrite真正写Windows文件并flush，然后更新自有存储缓存；FileRead从该缓存读取。两份独立bank使用同六槽、真实factory/guard/桥/Request/加载观察/身份/规划/退休/Handover实现。每一代在CAS之后实际尝试以写权限打开目标，证明分享锁拒绝；真实封存并恢复六槽之后再次尝试打开，证明租约已释放。第二代必须实际取得首代完成后的原生交接许可。

两代分别验证一次FileWrite、两次旧内容完整读取、两次新内容读取、持久意图、匹配报告和一次释放；第二代运行中调用首代六个旧物理入口，未进入第二代业务回调。另一个新host进程注入受控guard指纹差异，首代在请求前被拒、零FileWrite、第二代没有安装或交接。

fixture为构造自有世界先捕获Profile，再调用同一个Refresh Capture和实际原Owner安装；生产导出则先Refresh Capture，再经原Warm Profile安装。fixture不把游戏或Steam替身藏进生产DLL。生产导出布局/符号经过编译、ABI及PE核验，完整导出在真实游戏中的有效配置安装仍待实测。

fixture两代日期/势力故意不同，用来覆盖动态guard，不是两轮真实游戏推演。Python单独检查合法相邻profile，并以原生/RAM明确替身验证文件顺序和报告。不能将这两种测试拼成两真实客户端联机证据。

首次组合 `214757-003522` 因完整fixture片段插入位置错误、重复声明导致编译失败，修改builder为精确替换前驱片段后 `214827-917808` 通过。随后Python增加每轮失败报告、builder补来源和意图哈希，最终重建为上述 `215046-831686`；旧记录均保留。

## 实机下一步

已经通知用户正常启动并读34，等待回复；本轮尚未访问游戏或Steam存档。新plan保留旧CC03的完整Windows identity，两份独立source为34私有副本及上轮手工生成的新49私有副本；不能先用Python替换目标。新49已证明保存时RAM为203-08-21/张鲁，尚未读回，此次第二加载仍需验证其真正日期和B视角。

入口：`b_warm_refresh_diagnostic.py`。先`--check`，再执行`--execute --no-new-commands`；其余参数见Python交接。保持fresh进程、原规则来源、实际storage绑定和新claim检查。首载失败要读取新的RefreshReport；旧Request的Rejected不保证目标没被写。失败不自动回滚、重试、清claim或卸载固定模块，正常进程退出后的恢复另按实际记录处理。

这只推进本机B两档诊断。A自动保存修复后的实测、远端两游戏连接、完整输入暂停、菜单覆盖、事件等待和地图遮罩仍未完成。
