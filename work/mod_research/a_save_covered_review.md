# 下一次新进程 A 保存：离线独立审查

2026-10-09。只读仓库、固定归档和自有运行证据；没有访问游戏、Steam、UI 或当前存档。未修改冻结源。下面不是下一次实机成功保证。

## 具体风险

1. 尚需处理五栈/queue1 的 User。a_save_covered_gate.cpp 的 layout 已接受精确本代排队 Save，但 a_save_covered_owner.cpp:229 的普通 User Entry 和284附近 After仍调用只接受五栈且queue0的 rp::observe。新 coveredShape 仅六栈（158..162）。此前组合手工 queuedGame 后立即apply六栈，未执行 pending User。故只要调度进入该窗口，仍会拒绝。这不是修改报告字段guard的理由。

   原归档确有相关路径：scheduler 50A03B先判pending，50A150按type处理事件；但50A7A6会遍历调用状态虚表+30，返回非零时50A7AB跳50B41B，绕过50A7BA开始的pending复制/清理/apply，然后50B441进入Update walk。队列count未变时50B63B/63F允许下一state。因此有明确的暂缓apply控制流；尚未枚举每个虚调用的真实业务条件，也未证明上次现场命中它。正常enqueue令count0→1时50B63F会结束本次walk，不能简单假设任意帧都有pending Game/User。后继必须针对精确同代队列，而不是接受所有pending。

2. a_save_runtime_start.py:86..97 期待 exports 内层结果具有 production、abi_executed、own_sources、schema.json。a_save_covered_runtime_build.py:39..70 是外层包装，实际这层位于 execution/abi目录。新启动后继必须验证外层来源，再明确取内层abi结果；直接把covered外层目录传给冻结start会在加载前KeyError，不应绕过验证。

3. 失败的来源撤回有意严格。runtime_start.py:213..230先Stop、等待IPC线程退出，再等restoreReady，publisher读取真实桥计数和Host cache。Driver Uncertain/Error54、SaveLane1、Hostlease1不能被active全零替代；旧ABI没有abort retirement，无法恢复就须保留DLL/来源，正常退出旧游戏。新增abort后继应是独立已认证drain，不伪造Complete/Copy。

4. Prepare成功但Plans失败时 start:221会因为plans_file为空保留模块；ArmOwner部分发布失败则只要Plans已取得，publisher已支持Owner-only两槽恢复。ArmPublishedSources部分成功也支持七来源任意已知subset。不能重试旧once claim或卸载DLL。

5. Snapshot或publisher未决不能当成干净失败。start:67..74记录publisher仍可能持有调试事件，未强杀；remote未知的主体路径设置uncertain并跳过cleanup。cleanup内部call若未知会只进入cleanup_error，后续不再调目标但诊断应保留RemoteCallUnknown.record，避免仅repr丢失待处理远程线程信息。这是最小记录改进，不是允许重复调用。

## 成功后七来源能否恢复

静态成功链自洽：Driver完成实际Save/User原返回、worker join、文件读回一致→Complete；Owner Finally清saveLane及report pinned；Host Copy/Complete邮箱后在同宿主TID释放producer锁；父Finally更新真实Host cache。channel.stop/close后Runtime.Stop阻止新admission，父仍可运行收尾；typed Snapshot及publisher都要求无活动与无lease/frame。publisher在held调试事件内逐个还原3call/4vtable，核字节/保护、干净detach，再由只读preflight核验。DLL/relay不卸载。

已有离线5/5组合证明上述成功及负例路径，但未曾证明新covered源码真实游戏保存成功后撤回七处；下一次必须记录实际原档哈希、产物hash、来源恢复和调试器退出。没有发现需要因“成功保存”而放宽restore条件的依据。

## Guard与诊断边界

新Gate的自有pending许可建立在Inspector返回UnownedStateQueue之后，继承的是该queue判定之前的全部检查；不是完整QuiescentObserved之后全部谓词。例如原Inspector在queue早返后才检查load_cache+8==1，不能文档宣称这个分支也经该检查。该许可是独立的精确Save过渡，未凭此放行一般菜单。

ASaveCoveredGateFirstFailure只记录第一次Game-before拒绝，能够区分frame/caller、source、claim与layout；snapshot不保证哪个具体layout子谓词，应保留原字段一起分析。Owner单独诊断covered计数；firstfailure与错误时间先后不得用后来的report撤权倒推。

后续最小工作：先完成pending User的精确同代后继/有界复现，再与独立abort retirement合成新生产DLL；新启动器接typed构建证据与first-failure只读采样。仍不要求或许可对已失败旧进程换模块重试。

## 本轮后继核对

pending User 已在新 a_save_pending_user_owner.cpp 窄化处理，前驱错误真实复现、后继6/6通过，详见 a_save_pending_user_handoff.md；这关闭上述具体离线缺口，未把CFG许可升级为旧实机根因证明。

独立静态检查根新 a_save_failure_diagnostic.py 与 a_save_diagnostic_start.py：未发现本次范围阻断。诊断只持 query/read/wait 句柄，精确PID/birth/EXE/DLL磁盘hash与内存header在两次DATA读取前后核验；只允许原header或仅ImageBase精确重定位header。stage最后发布且不重置的契约下，双读完全相同的非零stage才给出first failure，零stage报告NOT_PUBLISHED，不等于没有失败。DATA结果不授予恢复许可、不接受存档。新启动器cleanup已单独保留 RemoteCallUnknown.record；RPM诊断失败不会跳过原收尾。这是只读诊断审查，不是对真实保存或abort整体成功的认证。

最终诊断证据以 `a_save_failure_diagnostic_test_runs/20261009-135136-315886` 为准：root已为cleanup未知调用记录的修改重跑10/10，并核5源匹配。135009-489811是保留的中间记录，不能拿它覆盖修改后的启动器。
