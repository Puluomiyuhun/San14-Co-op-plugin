"""Build an allowlisted portable Python connection checker from public sources.

No game files, native profiles, historical catalog, keys, config or run logs
are copied. Output must be a new directory. Python and cryptography are needed
on each computer; this is not a bundled runtime or gameplay launcher.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'run.py': 'tools/connection_check_entry.py',
    'two_pc_preflight.py': 'outputs/two_pc_preflight/two_pc_preflight.py',
    **{n + '.py': 'outputs/san14-link/' + n + '.py' for n in
       ('room_session', 'room_transport', 'authoritative_sync', 'checkpoint_transfer')},
}
GAME = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
README = '''SAN14 连接诊断（Python 源码便携包）

用途：检查两台电脑的工具版本、可选游戏EXE摘要、TLS连接和诊断文件传输。
不启动游戏、不注入DLL、不读取存档、不自动进入地图；不代表双游戏已联机。

两台电脑解压同一包，需 Python 3.10+ 和 cryptography。
运行 py -3 -m pip install cryptography 可安装所需Python依赖（本工具不会自动安装）。
双击 Start.cmd，或打开终端运行 py -3 run.py check。

可选配置：py -3 run.py init --game-exe "C:\\实际目录\\SAN14PK_SC.exe"
配置仅在本机使用，不应传给朋友。已有配置不会被覆盖。
未配置EXE时版本明确显示 NOT_CONFIGURED，但仍可做纯网络诊断。

A：py -3 run.py host --bind <A的局域网/VPN IPv4>
B：py -3 run.py guest --invite "收到的invite.json"
异地双方需先建立能互通的局域网/VPN；工具不会修改路由、防火墙或开放公网端口。
只把A打印路径中的 invite.json 私下交给B，不传 private-runs 整个目录或私钥。
两个诊断席位不是游戏中的真实势力选择，不修改当前游戏。

成功显示 NETWORK_BYTES_PASS_WAITING_NATIVE_BACKEND；这是连接和字节校验通过。
报告在 private-runs，包含本机诊断；不要提交Git。结束后房间关闭。
更改/缺少包内源码会拒绝启动。摘要检查用于发现混版，不能认证第三方分发者。
'''


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = {name: sha(ROOT / source) for name, source in SOURCES.items()}
    for name, source in SOURCES.items():
        shutil.copyfile(ROOT / source, output / name)
    rules = hashlib.sha256(canonical(before)).hexdigest()
    catalog = dict(profile=dict(protocol='san14.room.v1', game_sha256=GAME,
        adapter_contract='research-no-native-room-adapter.v1',
        checkpoint_sha256=hashlib.sha256(b'san14.diagnostic-bytes-only.v1').hexdigest(), rules_sha256=rules),
        forces=[dict(id=12, name='Diagnostic seat A', main_district_id=11),
                dict(id=2, name='Diagnostic seat B', main_district_id=2)],
        source=dict(diagnostic_only=True, game_state_observed=False))
    (output / 'catalog.json').write_bytes(canonical(catalog) + b'\n')
    (output / 'README.txt').write_text(README, encoding='utf-8')
    (output / 'Start.cmd').write_bytes(b'@echo off\r\nsetlocal\r\npushd "%~dp0"\r\npy -3 run.py\r\npopd\r\npause\r\n')
    files = {name: sha(output / name) for name in (*SOURCES, 'catalog.json', 'Start.cmd', 'README.txt')}
    assert all(sha(ROOT / source) == before[name] for name, source in SOURCES.items()), 'Source changed during packaging'
    manifest = dict(schema='san14.connection-bundle.v1', files=files,
                    build_id=hashlib.sha256(canonical(files)).hexdigest(), diagnostic_only=True)
    (output / 'bundle.json').write_bytes(canonical(manifest) + b'\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New destination directory')
    parser.add_argument('--zip', type=Path, help='Optional new zip; contains only this build allowlist')
    args = parser.parse_args()
    if args.output.exists() or (args.zip and args.zip.exists()):
        parser.error('Output directory/zip already exists; nothing overwritten')
    value = prepare(args.output)
    if args.zip:
        args.zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.zip, 'x', zipfile.ZIP_DEFLATED) as archive:
            for name in sorted((*value['files'], 'bundle.json')):
                archive.write(args.output / name, 'SAN14-Connection-Check/' + name)
    print(json.dumps(dict(result='BUNDLE_CREATED', output=str(args.output.resolve()),
        zip=str(args.zip.resolve()) if args.zip else None, bundle_id=value['build_id'],
        files=len(value['files']) + 1, game_access=False, native_backend_connected=False)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
