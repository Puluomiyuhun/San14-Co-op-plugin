# A 本机采样及真实空队列兼容

2026-10-09。本轮实际读取当前游戏，不调用保存、加载或推演。完整地址、Steam模块绑定和代码采样只保存在仓库外私有结果；公开证据见本轮 `docs/evidence`。

## 确认的实际问题

原电脑当前张鲁、203年8月中旬、五层大地图状态下，manager 的队列地址、容量和数量都是零。它是正常未分配的空 vector。A 原先链接的 `checkpoint_native_input_pending_adapter.cpp` 要求至少16字节队列 span、非零容量，因此这种真实状态会被 `Bind` 拒绝。此前 A 组合 fixture 都事先分配队列，未覆盖这个情况。B 已有不同 ABI 的 bound resolver 实现，不应为了迁移一个 A 只读检查器而混用其加载授权配置。

新增同 ABI 后继 `checkpoint_native_input_pending_empty_queue.cpp`，链接时**替换**冻结旧实现，不同时链接两个实现。只允许地址/容量/数量全零；部分零、数量超过容量、漂移地址等仍拒绝。旧空绑定不能跟随后来分配的地址；必须重新采样并构造新的检查器。空绑定的 `BeginAuthorizedLoadPush` 明确拒绝，没有给 A 检查增加自动加载权限。原分配队列的路径保持，并补数量上界检查。

## 可用于实际 Owner/Gate 的采样端口

`a_save_local_binding::Sampler` 提供 `Sample(void*, pending::Config&)`，供 Owner 的 `sample_input` 和 Gate 的 `sample` 使用。初始化保存该局 base、root、world、cache、五个 state 及 attachment binding，初始化后不可重绑。每次调用现读 stack、queue、toolbar、panel 地址，检查内存页与容量，并用 volatile 读复核指针及元数据；输出实际原生地址的 span，不伪造队列或写游戏字段。换 world、cache 或五个 state 时拒绝。

当前支持 stack capacity 至少6（原电脑实际16），与原检查器48字节最小范围保持一致。采样端口只检查来源及可读范围，**不自行判定空闲**：例如非空待执行队列仍返回实际数据，由后续 Inspector 判断为 `UnownedStateQueue`。采样结果必须在已验证的原生调用作用域中立即使用，不能跨帧缓存。重复读取不是锁，也不是原子快照或完整输入暂停。

`a_save_local_binding.py --capture --pid <当前PID>` 只用只读进程句柄，复用已审 planning/storage 捕获，核当前 EXE、进程出生、五层状态和缓存的 Steam v014 接口。它既不加载 DLL，也不替代安装许可或调用原生存储函数。无参数只显示帮助。

## 验证与真实边界

```powershell
py -3 work/mod_research/checkpoint_native_input_pending_empty_queue_test.py
py -3 work/mod_research/a_save_local_binding_test.py
```

前者先用冻结实现复现正常空队列的拒绝，再用后继验证合法空队列、错误结构、分配漂移及加载授权拒绝。后者在自有内存中直接组合真正 Sampler 和后继 Inspector，覆盖空→已分配队列、待处理命令、换 world/state 和不可读页面。均不打开游戏；原始结果及编译产物留在仓库外。新父 Adapter 的实际 Host/管道两例也已链接该后继，验证原已分配队列路径没有被破坏。

原电脑已执行 Python 真实只读 capture 并通过，确认当前 empty vector 以及 planning/storage 身份；这与 C++ Sampler 的自有内存组合测试分别记证据，**未向游戏注入 Sampler 或调用自动保存**。

下一步：本机 Runtime 使用同一个 Sampler、Owner/Gate、Controller/Host/ParentAdapter，完成真正来源发布与一次新文件保存；不用再重复同类只读空队列采样。完整加载/双机闭环仍未完成。
