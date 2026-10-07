# A 端 fresh Save 常驻组合交接

2026-10-08。状态：**生产组件可编译；13 项自有进程组合测试通过；尚未在 SAN14 实机运行。**

## 已实现

`checkpoint_fresh_save_session::Owner` 将冻结的 `checkpoint_fresh_save::Driver`、真实 `live_storage_binding::Context`／串行 `Gate`、独立两槽 PE 汇编桥和 `checkpoint_load_hook_set::Set` 接在一起。不是另一个模拟保存状态机。

- 原函数固定为支持版本的 `base+3F9B00`（User）和 `base+4AA650`（Save），配置不接受任意原函数。初始化要求两个 vtable 槽仍指向原函数，经 Driver 的映像／指令 profile 检查后再保留入口字节；Arm 和存储校验拒绝后加的入口替换。
- `Arm()` 先发布 Save 槽、后发布 User 槽，使用真实 CAS 和原页保护恢复。发布完成前不会准入请求，部分发布仍透明调用原函数。它不是全部线程的执行屏障。
- 只有实际汇编桥调用原生 User 并正常返回，Driver 才得到 AFTER，进而调用 `2FC750` binder 和 `2DF990` type0 Save 队列。规划拦截器自行返回不会构成这条证据，也不能作为原函数配置进来。
- Save 阶段、原生返回、FINALLY、文件固定和两次完整 native readback 由冻结 Driver 处理。同一 Owner／桥配置支持 **最多两个**不同代次和文件名的请求，未重置旧请求或模块静态计数器。
- `Stop()` 撤销新准入。已越过 binder 的保存继续观察；不调用 Gate.Stop、不恢复 vtable、不卸载模块。Owner 和桥上下文必须保留到进程退出。

## 接口和下一步接线

包含 `checkpoint_fresh_save_session.h`，以 `new Owner` 创建一个进程生命周期对象。依次调用 `Initialize(Config)`、`Arm()`、`Submit(Request)`；控制线程读取 `Snapshot()`、成功后用 `CopyArtifact(generation, artifact)`取得固定字节；退出准入用 `Stop()`。不得删除 Owner。独立桥 bank 一进程只配置一次，不能新建第二个 Owner 借此无限扩充请求额度。

Config 需要真实 base、已有绝对保存目录和意图目录、不可变 room ID／epoch，以及**当前进程验证过的** `live_storage_binding::Config`。Context 仍校验 PID／birth、映像、批准模块、方法地址／字节、缓存代次和 storage 对象；无默认返回 true 的生产验证器。storage 的 attachment generation 是常驻绑定代次，与每个 Save Request 的 generation 分开。调用者提供的 attachment 验证器必须只读、不可重入，不得反向调用 Owner／Driver 的方法。

还缺三个具体整合点：

1. A 端生产 owner／安装入口采集真实 Config 并负责常驻生命周期；本组件没有远程发现或安装器。已有六桥或规划 wrapper 占有 User 槽时本组件拒绝安装，不能直接叠挂。需要明确唯一槽所有者，或另做经过验证的共同分发版本。
2. 在提交到保存返回之间排除实际玩家输入及其他业务写入。这里的规划结构检查和两次读取不能替代全输入锁、全局静止或完整世界一致性证明。
3. 将 `CopyArtifact` 的实际字节送入 A 的 checkpoint 发布／Room 流程；Room 仍需自己的状态、连接、epoch 和提交条件。诊断 Report 的 `room_ready`、`full_world`、`all_input_held` 始终为 false，不能据此解锁或发布 Ready。

## 验证边界

`checkpoint_fresh_save_session_test.py` 实际编译生产 `.lib`，另在独立子进程执行同一 Owner 工厂、两槽 publication、PE 汇编调用、完整 RAX／XMM0 保留、SEH 展开、Context／Gate 验证、CREATE_NEW 意图和文件固定。fixture 只将游戏映像位置与可信模块路径适配为自有内存／PE；ContextInit 执行已归档的初始化快路径。**User／Save／binder／queue 业务本体、Steam 文件方法是明确的测试替身；生成文件不是 SAN14 存档。** 未访问游戏、Steam 或真实存档目录。

13 个场景覆盖：同 Owner 两次导出、禁止 wrapper 原函数、被抑制 User 没有返回证据、入口后来改变、Arm 前 Stop、binder 前 Stop、binder 内 Stop、readback 内 Stop、User／Save 原异常、存储 generation 改变、实际读取字节不同、Save 阶段跳跃。成功例两次 binder、两次 queue、两份不同日期／摘要文件；每份均两次 native API 全量读取。

构建要求 Windows、VS 2022 x64、Python 3，以及私有生成文件 `checkpoint_push_profile.h`：

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT = 'C:\san14-private\mod_research'
py -3 work/mod_research/checkpoint_fresh_save_session_test.py
```

缺私有输入直接退出，不假称通过。通过 `/I` 只读引用，不复制 profile 到公开源码目录；产物位于 ignored 的 `checkpoint_fresh_save_session_runs/`。

最终证据：

- 结果：`checkpoint_fresh_save_session_runs/20261008-004241-058678/result.json`，13/13 PASS；源码和私有输入在编译／测试期间未变。
- 结果 SHA256：`0080873221b2a5121d63727bd11cf4431ec12a1811fe46bca67ecd4b26c297f7`
- 生产库 SHA256：`a44550af4e0cc0653eaf0dcac68dbdfedc6207062201f449f1bdaebb06580f3d`
- 自有 fixture SHA256：`5bedae1a9a1b747d0cded063c9b37a5b8909c2f816e9765b37cade48158ab736`
- 私有 profile SHA256：`8b221226843ed047fe24b3599c9141219c48bbe101191e7c0c4dc1f01a2497ed`
- 独立只读审查：`checkpoint_fresh_save_session_independent_review.json`，SHA256 `9ad91dd84baffb93e2a9870ee40698bd0a1c71e8e934a71cffbe051a4579dee3`；无新增实质阻断，未重跑测试／访问游戏。原始审查 JSON 留在本机研究档案，不作为公开运行数据提交。

所有旧核心、旧 fixture、旧一次性记录均保持不变。
