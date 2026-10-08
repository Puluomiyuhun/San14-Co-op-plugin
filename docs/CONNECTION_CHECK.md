# 两台电脑的连接检查入口

这是可以先交给另一台电脑运行的诊断工具：核对工具版本、可选的本机游戏EXE版本，建立真实TLS房间并传输诊断文件。它不连接原生游戏组件，也不会启动游戏、修改势力、读写存档或进入地图。通过后仍需完成 `HANDOFF.md` 中的实机加载与规则衔接门槛。

## 从干净仓库生成

在仓库根目录运行，输出路径必须尚不存在：

```powershell
py -3 tools/prepare_connection_check.py --output ".local/connection-package" --zip ".local/SAN14-Connection-Check.zip"
```

生成包只包含明确列出的六份Python源码、诊断目录、说明、启动脚本和文件摘要。无需原电脑的 `catalog.json`、游戏镜像、私有profile、历史运行目录或编译产物；不会打包本机配置、证书、私钥、邀请或存档。诊断目录的两个席位仅用于网络测试，不代表当前剧本势力列表。

两台电脑使用同一压缩包，解压到各自可写目录。需要 Python 3.10+ 与 `cryptography`。本工具不会自动安装依赖；缺失时检查会准确报错。本轮没有生成免Python运行时的EXE。

## 检查本机与游戏版本

在解压目录运行，或者双击 `Start.cmd` 使用中文选项：

```powershell
py -3 run.py check
py -3 run.py init --game-exe "C:\实际安装目录\SAN14PK_SC.exe"
py -3 run.py check
```

`init` 创建本机 `local-config.json`，不覆盖已有配置。配置相对路径以配置文件所在目录为基准，换电脑后可以各自填写自己的EXE路径。EXE只从磁盘计算SHA256，从不执行或打开游戏进程。支持版本为 `42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025`；明确配置了错误版本或不可读路径时，会在联网前拒绝。

没有配置游戏路径时显示 `NOT_CONFIGURED`，仍可做纯网络诊断。该结果不表示游戏版本或原生profile检查通过。

## 建立诊断连接

异地两台电脑需要先建立能互通的局域网/VPN。工具只接受明确的局域网/VPN IPv4，不自动配置网络、不改防火墙，也不监听通配地址。A 使用自己的可达地址：

```powershell
py -3 run.py host --bind 192.168.1.20
```

把A打印路径中的 **`invite.json` 单独私下交给B**，B运行：

```powershell
py -3 run.py guest --invite "D:\收到的文件\invite.json"
```

不要共享整个 `private-runs` 目录，里面含A的TLS私钥。邀请只属于当次诊断房间。默认端口41414；A可用 `--port` 指定其他端口，邀请自动携带实际端口。默认等候600秒，可通过 `--timeout` 设置10至900秒。

成功时两端显示 `NETWORK_BYTES_PASS_WAITING_NATIVE_BACKEND`，表示连接与诊断字节核对通过。B报告包含数据量和本次传输耗时，但本机回环耗时不能预测异地延迟，也不包含真实存档加载时间。双方结果留在各自的 `private-runs`。

## 已验证与未验证

```powershell
py -3 tools/test_connection_bundle.py
```

8项检查通过，包含两个独立进程、两个带空格的重新放置目录、隔离Python搜索路径、实际回环TLS、129 KiB完整字节、错误证书指纹、不同工具源码版本、错误EXE版本、包文件篡改、配置不覆盖，以及生成期间混入额外文件也不被打包等情形。测试没有私有profile依赖、游戏进程访问或网络配置修改。

包的文件摘要用于发现缺文件和混版，不认证恶意第三方分发者。两台真实异地电脑、用户实际VPN和原生游戏后端尚未测试。连接诊断通过不能放行游戏Ready。
