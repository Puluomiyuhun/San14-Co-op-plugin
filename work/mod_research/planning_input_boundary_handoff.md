# Planning input window boundary — 2026-10-08

本轮纯离线。未查找/打开游戏、Steam、现存窗口或存档，没有 preflight/record、注入或调试器。只创建自有进程中的隐藏 ANSI message-only HWND，结束后正常关闭。冻结前驱均未修改。

## 本轮新增

- `planning_input_boundary.h/.cpp`：使用现有 `planning_input_interlock::Controller` 的保留窗口消息边界；不叠第二套 User/Game Owner。
- `planning_input_boundary_fixture.cpp`、`planning_input_boundary_test.py`：真实独立 HWND 线程、原始归档 WndProc、自有队列消息测试。
- `planning_input_boundary_period_test.py`：同 fixture 显式替代链接冻结 `planning_period_owner.cpp` / `planning_period_interlock.cpp`，组合正式逻辑期退休/重绑定。

接口：`Boundary::Initialize(Config{controller,base,window})` 必须由 HWND 所属线程调用；`Request(held,revision,duplicate)`、`Retire(releasedRevision,duplicate)` 必须在既有 Controller 执行线程调用；`Snapshot` 只报告证据。Boundary、Controller、代码及 callback bank 必须驻留；8 个桥槽永不复用、不能卸载。槽用尽会拒绝。本轮没有生产 GUI 线程 bootstrap 或实时安装入口。

`Request(true)` 要求相同 revision 已获得真实 Game/User 的 7/31 局部观察；Setter 不能直接变成窗口 ACK。请求通过真实 PostMessage 投递，窗口回调处理后才形成 ACK；没有 Controller/Owner/Gate 锁在 WndProc 内嵌套。Controller/Owner Snapshot 发生在边界锁之外。实际收到并拦截审计范围内消息后才有 `auditedSuppressionObserved`。未知消息和 lifecycle 继续原过程，不凭 PostMessage 成功或过滤计数发 Ready/保存/推演许可。

## 真正覆盖与原生来源

复用冻结 `checkpoint_native_input::ClassifyMessage`，实测 SendMessage 的 Enter / mouse move，以及另一实际线程 PostMessage 的 Enter keyup 被拦在原 WndProc 业务调用前。审计范围包括 Enter/Backspace/Escape 的 keydown/up、mouse move/left/right down/up/leave；并非本轮逐条运行所有分类。真实 wheel 和自有未知消息原样转发，参数/返回值核对；WM_CLOSE/DESTROY 仍可退出。

生产身份要求同进程 ANSI HWND、指定窗口线程、原 class WndProc=base+5122F0、engine+18 指向该 HWND、窗口过程/handler 完整代码指纹及 RX MEM_IMAGE 身份。窗口过程 5122F0..512368 SHA-256：`ac9f1fc27b57c656e8a0cf5711e5a07f197168626d3823bf7f3f12b9f6a6e1d4`；handler 510BE0..511171：`81ecfc93cc2e7494d50cf5878b766e3796349a1e9d8516fde785c3f8cdfd6cd2`。

自有 fixture 执行归档 5122F0 的真实机器码，经正常 HWND/CallWindowProc 调用进入 510BE0 的显式 C++ 业务替身。该替身计数、转发 DefWindowProc，并明确模拟 Enter→PostMessage mouse 的后续；并未执行游戏完整 handler。fixture 宏仅放开 MEM_PRIVATE 和 handler 替身指纹，WndProc 原始 SHA 仍核验。私有 archive SHA：`5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268`。仅生成到运行目录的小段 WndProc profile，不提交原始字节/镜像。

## 必须保留的发布竞争限制

**Win32 SetWindowLongPtr 没有 CAS。本版生产使用前置为可信唯一 WndProc 发布者，且安装/退休在窗口线程串行；本版不能建立或证明这个发布排他。** 未知来源在写前已被看到时，操作拒绝且不覆盖。但检查与 Set 之间另一线程换来源时，Set 可能已经覆盖外来 WndProc，然后返回旧值才让本版发现冲突。

安装和退休各有一个确定性实跑反例：在 identity→Set 之间，自有另一线程真的 SetWindowLongPtr 到 foreign 过程；随后实际覆盖被断言。结果 `publicationConflict=true`、`foreignSourceMayHaveBeenReplaced=true`、`uncertain=true`，无正常 ACK/退休 ACK，也无完整 Ready。没有危险的猜测补偿恢复。不能把这两个 PASS 写成已阻止外来覆盖；它们证明该限制和失败报告真实存在。未知并发 publisher 仍是实机安装前置缺口。

正常退休要求 Controller 已明确 release、窗口 release ACK；窗口线程核当前过程仍属于自己的独立桥槽，恢复精确原 WndProc 后返回、FINALLY 排空才出现退休 ACK。旧对象驻留，缓存旧 callback 仍只透明调用旧 original；新 Boundary 使用不同桥槽。缓存 callback 测试是显式 fixture 调用，不冒称实际 Windows 投递了旧指针。

## 跨期组合及不能宣称的事项

组合确实使用同一物理 Owner/Gate，没有 reset 或第二套钩子：

1. 旧 Controller release → 窗口 release ACK → Retire ACK，恢复原 WndProc。
2. 旧 Controller 再 hold + 真实 Game/User 观察 → `planning_period_owner::Retire`。
3. fixture 仅改变同一 world 的日期，更新 period/epoch/digest，调用真实 `Rebind`。
4. 新 Controller claim 下一期，旧 Controller 与旧 reward binding 的 release 拒绝。
5. 新 Controller 显式 release → HWND 线程初始化新 Boundary → 新 revision hold + 真实观察 → 新 HWND ACK，并实际拦截输入。

这些 release 间隙不是连续全输入暂停。日期由 fixture 写入，不是真实旬末推演/存档加载。窗口二次 Initialize 由自有业务消息安排，不是已开发游戏 GUI bootstrap。新 Controller 和旧实例永久保留。业务赏赐/保存本轮不再运行，沿用对应独立证据；本轮只把实际窗口边界与正式逻辑期转换接在一起。

仍缺未分类窗口消息、Root conversion、设备缓存/直接轮询、其他消费者、后台 writer、物理按键释放与完整 OS 队列排空、生产窗口线程接线和发布排他。7/31 的前驱覆盖数不改，不借新增局部窗口证据消掉整个 WindowMessages 缺口。`fullWindowInputHeld/allInputHeld/physicalReleaseProven/osQueueDrained/roomReady/saveAuthorized/nativeGameplayEnabled` 恒 false。Snapshot/ACK 只是在调用时核对当前来源；不会阻止之后另一线程改来源或世界。没有测试原生异常跨归档 WndProc unwind，不能扩充为完整异常生命周期证据。

## 最终测试及指纹

- 窗口独立 **6/6 PASS**：`planning_input_boundary_runs/20261008-210909-886718/result.json`；59 个源码摘要再次核对一致。
  - result SHA `83ed9006709f934316d703aa9df6f4c4ed466a42a1f6007f17062369789e6f55`
  - fixture SHA `a61f3f484759e81cf98d62cb12145ded0f77747976e881f1925c4ce71747a4f1`
  - production library SHA `043d2de3f4c95d944a1b2cd757b0cc0ffc22253fa71e89b0bb93c00be5824c87`
- 替代链接正式 period 后继 **7/7 PASS**：`planning_input_boundary_period_runs/20261008-210927-252455/result.json`；59 个源码摘要再次核对一致。是六个窗口回归加一条组合，不是额外七种跨期流程。
  - result SHA `82d3cd545f93380d0df601143c2f73df1b1890d59f28c003654d96e30490b5b4`
  - fixture SHA `a56274850b9d2019adb0b5889cb73a4b190ffaea4e5911274b2f6a7274167389`
  - production library SHA `793d2b887f95a7bd8ccac4da4e4e9b424a9dbe1aaed67bb41df73668b4b9d4e4`

两套均编译生产无 fixture 宏对象及 library、fixture 可执行文件，VS2022 /W4 /WX。result 包含完整源码与产物 SHA、实际窗口线程、计数、固定 false 能力及剩余范围。没有网络 wire/HMAC 扩范围，也没有 IPC worker 后继；未来端口应单独绑定这些本地证据，不把旧 User receipt 当窗口覆盖。

## 保留失败

- `planning_input_boundary_runs/20261008-210036-816675`：测试生成器误把 Path 写成 tuple，编译前 AttributeError；保留 failure.txt，没有运行子进程。
- `210054-550279`：fixture 嵌套旧 main 宏冲突，/WX 拒绝；改为显式生成重命名 include，不改冻结文件。
- `210137-583696`、`210233-733964`：4 个场景都因 __try 中 return 引发 AbnormalTermination 误判而拒绝 ACK；后一轮保留诊断。修为显式 native returned 标志和 FINALLY 后 return。
- `210308-132419`：早期 4/4；`210722-327494`、`210810-645980`：6/6 中间通过。
- period `210556-342372`：早期5/5；`210739-659683`、`210827-826730`：7/7 中间通过。后续将下一期 Controller 从临时栈变量改为明确驻留，清理末空行后最终重跑。以最终两个路径为准。

## 复跑

仓库根目录执行，私有路径只用于 fixture 归档与已有规划 DLL，不访问游戏：

```powershell
$env:SAN14_PRIVATE_FIXTURE_ROOT='<本机私有归档目录>'
py -3 work/mod_research/planning_input_boundary_test.py
py -3 work/mod_research/planning_input_boundary_period_test.py
```

不等待用户操作。本轮无活动游戏补丁/调试器；自有窗口及子进程均正常结束。下一步先建立实际 GUI 线程来源与唯一 publisher 接线或设计驻留同桥换期，再补剩余设备/Root 消费者；不能用本版局部窗口计数授权生产保存/推演。
