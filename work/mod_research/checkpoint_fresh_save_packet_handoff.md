# A 保存字节出口

2026-10-08。`checkpoint_fresh_save_packet.{h,cpp}` 把现有 `Owner::CopyArtifact` 的完整结果序列化；`checkpoint_fresh_save_packet.py` 严格解码。它没有读取游戏进程、调用 Steam 或执行加载的能力，也不是 IPC 身份认证器。

## 接线方法

在持有常驻 Owner 的本机代码中，先调用 `CopyArtifact(generation, artifact)`，成功后调用 `checkpoint_fresh_save_packet::Encode(artifact, packet)`。Encode 重新计算文件 SHA256，拒绝未完成、活动作用域未退出、阶段不全和虚构完整世界/Ready 权限的报告；失败时清空输出，防止继续使用上一次成功的字节。

Python 侧只从已绑定的本机生产者取得 packet，再调用 `decode_packet(raw)`。返回不可变请求、报告和文件 bytes。**能解码不等于来源可信**：任何人都能制造相同格式，不能将网络上传的 packet 或旧文件当作“当前 A 刚保存完成”。本机 IPC 的生产者身份、进程生命周期以及输入排除仍需外层接入。

后继 `checkpoint_fresh_save_binding.py` 在提交前保存完整协议边界，再核对该 packet 的请求、实际字节和保存后的世界观察，交给现有 Room 传输。原生 `room_epoch` 是两次保存保持不变的 Owner 会话标识；协议每旬变化的 epoch 必须另行关联。

## 格式 v1

全部整数显式小端编码，不使用 C++ 结构体内存布局。

| 字段组 | 字节数 | 内容 |
| --- | ---: | --- |
| 前缀 | 24 | `S14FSV01`、版本1、头长度284、文件字节数 |
| 请求 | 88 | generation、稳定room_epoch、period、cut、32字节room_id、日期/君主/势力、16字节文件名 |
| 完成报告 | 140 | 状态、生命周期计数、返回/FINALLY证据、三个范围标志 |
| 文件摘要 | 32 | 文件字节的SHA256 |
| 文件数据 | 1至64 MiB | CopyArtifact固定的原始字节 |

报告中 `entries == exits`，相关原生返回次数满足 `7 <= original_returned <= entries`；无关但正常退出的入口可以增加作用域计数，不应误判为保存失败。`stop_after_commit=1` 的已完成文件仍可被观察和记录，但房间发布层必须拒绝用它继续游戏。

包中无本地路径、凭据或可解引用的跨进程缓冲区。`save_state` 和 `executor_thread` 是诊断标识，不能拿到另一台电脑执行，也不证明生产者身份。游戏内容仍属于本机私有数据，不提交 packet。

## 已执行验证

```powershell
py -3 work/mod_research/checkpoint_fresh_save_packet_test.py
```

该命令不需要私有游戏 profile；需要 Windows、VS2022 C++ x64 工具链。它编译生产编码器，在自有子进程构造明确的格式测试数据，再由 Python 解码 C++ 产物。8 项 Python 测试覆盖大小/版本、截断和尾随数据、请求类型、未完成报告、错误权限、字节污染及不可变返回值；C++ 同时核对拒绝路径和失败输出清空。测试文件不是 SAN14 存档，没有任何原生游戏调用。

`a_save_user_owner_test.py` 另外把该编码器接在真正的自有 Owner `CopyArtifact(1/2)` 后，生成 `success/first.packet` 和 `success/second.packet`。这里实际经过 Owner/Driver/原生桥/文件保存和读取验证，但游戏保存业务仍是替身。它验证模块组合，不能称为两个真实客户端已经联机。

结果保留在 ignored `checkpoint_fresh_save_packet_runs/`。公开摘要与当前剩余接线见仓库 `docs/HANDOFF.md`。
