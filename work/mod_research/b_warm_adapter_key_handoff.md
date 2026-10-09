# 本地独立 adapter key：准备、人工转交与加载

新增 `b_warm_adapter_key.py`；不修改 Room join token、TLS 服务、RemoteCompletionRoom 或 RemoteGuestCompletion。只创建本地密钥文件并返回公开 fingerprint。导入模块不会创建文件、打开进程或联网。

## 使用

先在仓库之外建好一个私人目录，例如 `%LOCALAPPDATA%\San14Coop\Private`。目录管理由本机用户完成；工具不修改已有目录或其他文件 ACL。

```powershell
py -3 work/mod_research/b_warm_adapter_key.py create --file "$env:LOCALAPPDATA\San14Coop\Private\adapter.key"
py -3 work/mod_research/b_warm_adapter_key.py status --file "$env:LOCALAPPDATA\San14Coop\Private\adapter.key"
```

A 只生成一次。为了给 B 准备明确的人工转交副本，可用 `export --source <A-private-file> --destination <new-local-transfer-file>`。该命令只创建另一份受当前 Windows 用户保护的本地文件，不发送、不上传、不发邮件，不输出密钥。两台电脑应使用可信私密渠道人工传文件，不使用普通房间 join 响应、聊天日志或 Git。

B 收到文件后显式执行 `import --source <received-file> --destination <new-B-private-file>`。它验证文件编码并新建接收方 SID 所有的私有文件；不会更改、删掉或尝试修复来源文件。随后双方运行 `status --file <private-file>`，通过另行可信方式核对 fingerprint。导入不能证明来源可信，也不能撤销传输或来源文件此前已经发生的泄漏；确认后由用户自行处理传输副本。

所有 CLI 只接受文件路径，不接受 key 文本。成功 JSON 包含 schema、operation、公开 fingerprint 和明确 false 的 secret_disclosed/native_permission；失败只有固定错误标签，不回显错误输入/文件内容/路径。Fingerprint 是独立 domain 下 key 的 SHA-256，不是 join token，也不授予 native 执行能力。

本地 launcher 的实际接点：

```python
from b_warm_adapter_key import load_key
key = load_key(private_file_path)  # 返回 bytes，只在本地内存使用
# A: existing_room.enroll_adapter(key, host_sampler=..., verify_held=...,
#      host_receipt_key=..., source_kind=...)
# B: RemoteGuestCompletion(existing_B_control_connection, key, verify_held=...)
```

这两个既有 API 的其他参数仍须来自同一实际 owner；本工具不伪造 boundary、不配置 native 模块，也不自动启动房间。完成回执的已有 HMAC 验证继续使用同一 32 字节 key；它认证已登记 adapter 的来源，不远程证明游戏已经执行。

## 文件范围与失败规则

- 新 key 用 `secrets.token_bytes(32)` 生成；固定 ASCII 版本头加 64 个小写十六进制字符和 LF。拒绝全零、BOM、CRLF、额外换行、大小写/长度错误。文件中不保存房间 join token。
- Windows `CreateFileW(CREATE_NEW)`，不共享句柄，在创建时传安全描述符：Owner 为当前进程 token 的用户 SID，protected DACL 恰有该 SID 的一条完整权限 ACE。写入前、flush 后都从实际句柄复核 ACL。不是先写宽权限明文再执行 icacls。
- 普通 `load_key/status/export` 要求该精确 owner/ACL；默认继承管理员/SYSTEM/其他主体的宽 ACL 文件也拒绝。`import` 是唯一显式允许读取已转交、可能宽 ACL 来源的路径，目标仍按上述私有规则创建。
- 拒覆盖已存在目标；短写/flush/ACL 异常保留失败目标，不自动删除后重试。该文件可能为空或部分写入，需人工判断；不会当作成功 key 使用。
- 只允许显式本地盘符路径和支持 persistent ACL 的卷。最终对象用 OPEN_REPARSE_POINT 检查，拒 directory、reparse、多个 hardlink、UNC、ADS、设备名称和模糊末尾点/空格。创建目标处于任何可见 `.git` 祖先（含 worktree `.git` 文件）时拒绝，避免正常用法把 key 纳入仓库。
- 这不是抵抗同用户恶意进程、管理员取得所有权、磁盘离线读取、父目录并发替换或之后人工改权限的沙箱；没有加密文件内容或保证 Python 内存清零。此范围依赖可信本机 launcher/用户与正常 Windows ACL，不声明自动密钥交换、密钥轮换或断线恢复。

## 验证

命令：`py -3 work/mod_research/b_warm_adapter_key_test.py`，只用仓库外自有临时文件和短命 CLI 子进程。

最终 6/6 通过：

1. 实际创建／ACL 验证／load／status／export，以及已有目标拒覆盖、原 bytes 不变。
2. 规范编码、精确长度和全零拒绝，非法 import 不创建目标。
3. 宽 ACL 来源不能普通 load，显式 import 后可按接收方私有 ACL load，来源不改变。
4. 实际 hardlink、目录、UNC、ADS、设备/模糊名称拒绝。
5. `.git` worktree 标志下目标拒绝，不生成 key。
6. 实际 CLI 创建、状态和拒覆盖输出检查，只公开 fingerprint，不含 key bytes/hex。测试断言也避免把秘密作为 assertEqual 的失败诊断输出。

最终私有记录：`work/mod_research/b_warm_adapter_key_runs/20261009-201345-022488/result.json`（此路径位于仓库外的父 work）。SHA-256：`d1758938c7df4e1e863532c26b47665b824e193fb5268eb551c8b91b55a8a551`。2 份源码 pins、1 份日志 artifact；inputs_unchanged=true。14 个测试秘密文件已删除，remaining_secret_files=0；不把 key 文件内容或 key 文件哈希存入 evidence。CLI 子进程全部正常返回，无游戏访问、网络调用、发布器、驻留模块或调试器。

本轮没有测试失败。`201247-216345` 为首轮 5 项通过，`201325-143131` 为增加 Git/路径边界后的 6 项通过；保留日志，测试秘密同样按既定清理删除。最终只为避免失败断言意外打印秘密修测试输出，再跑当前结果；没有重试实际 key 的一次性创建。

源码 SHA-256：

- `b_warm_adapter_key.py`：`5f74d46dd6b218929ab95faccb7efe318b140c887d3abb30ba9d5f43902a3b19`
- `b_warm_adapter_key_test.py`：`513371f9b3442b08103f24ac7866f1beb6e1c726ef3b56bac6c45b7bf52f8877`

当前集成与提交状态见 [主交接](../../docs/HANDOFF.md)。剩余工作是本机启动入口明确接受私有路径后调用 `load_key`，并由用户为两台机器人工转交同一 key；本工具不自动执行该外部步骤。
