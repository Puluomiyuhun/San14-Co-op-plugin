# A 上游写入边界与原生门禁后继

2026-10-08。只读指定SHA的历史归档/profile，运行Unicorn及自有原生fixture。未访问游戏进程、Steam、UI、游戏安装目录或当前存档目录。无待用户操作，无新增游戏补丁/调试器；自有测试进程已退出。冻结前驱未修改，Git及根文档由主agent整合。

## 本轮实际消除的缺口

上一版3F9BA8切点之前还有User直接调用15FA20和16C5F0。现在同一Gate的User补丁前移到**3F9B16**，在可信保存代和同一个实际User调用内，在这两个函数之前选择原**3FA0AE短收尾**。仍只有两处归本组件所有的补丁（另一处是Game panel 3F8606），旧3F9BA8报告块和3F9DAF动作块均保持原指令。

这不是简单把旧返回地址改小：3F9B16时原函数只建立了RSI/0x40栈帧，RBX/RBP/R14/R15尚未保存。原3FA09F长收尾此时不合法；本后继改用只恢复RSI/栈的3FA0AE。归档原prolog/short epilogue执行与自有PE桥测试分别验证了这层区别。

普通路径在桥内恢复原输入寄存器、XMM和flags，再以规范尾跳进入原15FA20。原User调用产生的返回地址3F9B1B仍留在栈上，原生15FA20返回的RAX自然交给后续`mov rcx,rax; call 16C5F0`。没有另造一个wrapper的返回充当原生User成功，也没有填写Driver成功字段。

**本轮堵住这两个callee经该User来源进入的路径**；其他caller、后台生产者、输入消息及更早的509640仍未全部隔离，不能宣称全局写入排他。

## 上游归档证据：7项

`a_save_upstream_audit.py` 校验完整历史归档SHA及所有已列函数范围摘要，在Unicorn执行有界路径。它包含明确外部模型，不是完整游戏执行。

- 15FA20已构造单例快路真实只读；冷路到159CB0构造器和CRT生命周期入口。构造器/CRT在本审计中为模型，没有证明其内部没有写入。
- 16C5F0真实按模式选择163C80、16C6D0、16BEF0。
- 163C80非空路径：外部坐标、距离和场景更新是模型；归档指令最终确实将updater模式写1。
- 16C6D0非空失效对象路径：161E20资格判断为false模型；原指令清对象+70标志并将node+28指针清零，337BB0生命周期callee仍未展开。
- 16BEF0两条非空路径：真实调用归档337200；空关联对象分支重置多个对象字段，忙对象分支置+70的0x10标志；16BEF0最终清updater模式。同步API为模型。
- 原User在3F9B16分流到原3FA0AE后，实际prolog/epilogue恢复RBX/RBP/RSI/R14/R15与调用者栈。此项的分流决策与509640结果是模型；实际PE桥另由29项组合覆盖。

这里只能把内存准确归为updater、节点和关联对象，**没有证明这些直接写的是持久world字段，也没有证明所有callee都只操作显示**。结论是这些来源包含真实对象/模式/生命周期副作用，不能凭“渲染”命名视为无写入。

## 实现和构建替换

- `a_save_upstream_gate.cpp/.h`替代`a_save_early_gate.cpp/.h`，命名空间`a_save_upstream_gate`。
- `a_save_upstream_bridge.asm`替代`a_save_early_gate_bridge.asm`，继续复用冻结`a_save_action_gate_bridge.cpp/.h`的固定桥bank；不要同时链接两份ASM。
- **`a_save_upstream_owner.cpp`替代`a_save_report_owner.cpp`**，维持原`a_save_user_owner::Owner`和`a_save_report_owner::Snapshot` ABI。业务、存储、report sidecar、状态机沿用前驱，只更改User原生前缀来源比较。
- 使用冻结原版`a_save_early_guard.cpp`，因为19字节report块不再改变。不要同时链接上一版early_gate_guard后继。
- User/Save桥、Driver、native storage、binder/gate和输入检查器继续使用现有实现。最多两个保存请求仍不放宽。

3F9B16落在原Owner固定32字节前缀内，不能跳过旧校验。新Owner只接受初始化时的原前缀，或本Gate已Arm后的**精确5字节call计划**；其余27字节与RX跳板、固定桥目标必须匹配。未归本组件所有的前缀/报告后缀改动继续拒绝，不会自动恢复竞争来源。

不可变计划通过Interlocked发布，prefix检查不取Gate锁；保留Gate → Save Snapshot顺序而不引入反向锁。主agent已独立审查源差异、栈位置、透明尾跳和前缀归属，未发现本轮阻断问题。

硬件shadow stack/CET开启仍拒绝初始化，因为held路径选择原返回地址；未关闭系统保护。生产发布器与全局持续Owner仍未接入。

## 原生组合：29/29

最终`a_save_upstream_runs/20261008-165201-451263/result.json`，**29/29 PASS**；生产库无fixture宏编译，源码/私有profile前后摘要一致。

- 同一实际Owner两份不同32字节诊断文件：binder2、queue2、native readback4；User native return4、Save native return10。四次upstream抑制，singleton/updater/report/selection/action业务double均0。
- `updater-write`确实将会写报告的业务放在被拦的16C5F0替身内，两保存均不执行它；`release-updater`释放后实际singleton返回流入下一updater，updater写入、报告消费和selection各执行一次。这使本轮验证直接覆盖“保存时跳过上游，正常操作恢复上游”的组合。
- `upstream-exception`在透明尾跳到singleton替身后产生真实SEH；User native_started=1、native_returned=0、finally=1、abnormal=1。没有伪造AFTER。原report compare AV场景继续覆盖下游异常。
- held和forward两条恢复区均逐控制PC做`RtlVirtualUnwind`；包括flags临时push/pop、pop RBP、RET与规范间接尾跳。unwind场景共427项内部检查通过。
- 原25项中报告晚到、提交/入口拒绝、storage/copy变化、owner争用、源码漂移/部分安装等继续通过；新增prefix-drift拒绝。
- `external-aba`、`early-bypass`的PASS仍意为复现外部/切点前的剩余写入风险，不是排他已解决。晚到报告保留与Owner撤权不依赖清掉待办。

原生fixture使用明确的singleton/updater、User/Game/Save业务与存储替身；原生19字节报告块和实际call来源执行于自有snippet。**不是完整归档User原生执行，也不是两个真实SAN存档**。完整归档路径审计的模型边界不因这29项而消失。

## 失败和最终指纹

所有中间目录保留，没有删除失败或重置claim：

1. audit `20261008-164500-715888`：冷单例fixture错误设置TLS epoch，未到构造器，被断言拒绝。
2. audit `20261008-164514-466855`：用例命名前缀错误选中mode4，未执行预期163C80，被断言拒绝。修fixture选择，未改归档指令。
3. audit `20261008-164525-024283`：7/7；最终加入源摘要冻结复核后`165215-790922`仍7/7。
4. native `20261008-164905-272541`：生产构建已过，fixture构建因/WX拒绝局部变量遮蔽成员；终端打印又遇GBK编码异常，build.log仍完整保留。修变量名及输出容错，没有放宽/WX。
5. native `20261008-164933-199803`：29/29；独立review与接口注释修正后最终`165201-451263`仍29/29。

最终native结果SHA256：`330b085443cd8d3f59210a0d519e1697b36396ecf53ab98193dd14c9fdf5e840`

最终production lib SHA256：`8f81756684e091f848504c81803b0b921393e8119191d9ccab6ed0c60437e5c7`

最终fixture EXE SHA256：`6acd03b3793c42ee7c603e656d4a50cb3f215037e954139fd885242d30c4aabd`

最终audit结果SHA256：`6f8339d38db9f905562ac5e9f14afe6ab7ff1d5625e9e07ebbf4672e55ae748b`

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机私有研究输入目录>'
py -3 work/mod_research/a_save_upstream_audit.py
py -3 work/mod_research/a_save_upstream_test.py
```

需要MSVC/MASM、私有checkpoint_push_profile.h、固定SHA历史game-runtime-image.bin，以及私有python_deps中的Unicorn/Capstone。缺失输入明确失败，不访问当前游戏。

## 下一步

保持`fullInputHold / reportWriteExclusion / saveAuthorized / roomReady / production_permit=false`。本轮已移除同一User调用里的两个已知updater旁路，但不是所有世界写入者全集。

下一步应围绕统一运行Owner补持续生命周期与生产者排空：先定位/约束其他report来源和后台写入、验证509640及其manager单例在目标阶段的合法状态，再接生产发布器、IPC导出与两真实新档。原生保存本身可以写自己的保存缓存，不应以任意全线程停止破坏所需保存调度。不要把无新命令的测试承诺或本轮29+7项数量换算成生产permit。
