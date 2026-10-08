"""Portable connection diagnostic entry. No native backend or game access.

An explicitly supplied game executable can be hashed from disk, never run.
Source hashes detect mismatched/incomplete bundles, not a malicious distributor.
"""
import argparse
import hashlib
import importlib.metadata
import ipaddress
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
FILES = ('run.py', 'two_pc_preflight.py', 'room_session.py', 'room_transport.py',
         'authoritative_sync.py', 'checkpoint_transfer.py', 'catalog.json', 'Start.cmd', 'README.txt')
CODE = FILES[:6]
GAME = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
FLAGS = dict(game_process_access=False, native_backend_connected=False,
             native_gameplay_enabled=False, two_computers_proven=False)
PRIVATE = tuple(ipaddress.ip_network(n) for n in
                ('127.0.0.0/8', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '100.64.0.0/10'))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def read_json(path, maximum=262144):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON field')
            result[key] = value
        return result
    def bad_constant(_):
        raise ValueError('Nonfinite JSON value')
    with path.open('rb') as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, 'JSON exceeds size limit')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=bad_constant)


def verify_bundle():
    value = read_json(HERE / 'bundle.json')
    require(type(value) is dict and set(value) == {'schema', 'files', 'build_id', 'diagnostic_only'} and
            value['schema'] == 'san14.connection-bundle.v1' and value['diagnostic_only'] is True,
            'Not a connection diagnostic bundle')
    require(type(value['files']) is dict and set(value['files']) == set(FILES), 'Incomplete bundle file list')
    for name in FILES:
        path = HERE / name
        require(path.is_file() and not path.is_symlink() and sha(path) == value['files'][name],
                'Bundle file missing or changed: ' + name)
    require(value['build_id'] == hashlib.sha256(canonical(value['files'])).hexdigest(), 'Bundle identity differs')
    catalog = read_json(HERE / 'catalog.json')
    profile = catalog.get('profile', {})
    require(profile.get('game_sha256') == GAME and
            profile.get('rules_sha256') == hashlib.sha256(canonical({n: value['files'][n] for n in CODE})).hexdigest() and
            catalog.get('source') == {'diagnostic_only': True, 'game_state_observed': False},
            'Diagnostic catalog differs from bundle sources')
    return value, profile


def config(path):
    if not path.exists():
        return dict(schema='san14.connection-local.v1', game_exe=None, output_directory='private-runs')
    value = read_json(path)
    require(type(value) is dict and set(value) == {'schema', 'game_exe', 'output_directory'} and
            value['schema'] == 'san14.connection-local.v1', 'Unsupported local configuration')
    require(value['game_exe'] is None or type(value['game_exe']) is str and value['game_exe'], 'Invalid game path')
    require(type(value['output_directory']) is str and value['output_directory'], 'Invalid output directory')
    return value


def anchored(path, value):
    item = Path(value).expanduser()
    return (item if item.is_absolute() else path.parent / item).resolve()


def address(value):
    ip = ipaddress.ip_address(value)
    require(ip.version == 4 and any(ip in n for n in PRIVATE), 'Use explicit LAN/VPN IPv4; wildcard/public addresses are refused')
    return str(ip)


def check_local(path, value, bundle):
    errors = []
    game = dict(status='NOT_CONFIGURED', disk_read=False)
    if value['game_exe']:
        target = anchored(path, value['game_exe'])
        try:
            digest = sha(target)
            game = dict(status='MATCH' if digest == GAME else 'MISMATCH', disk_read=True,
                        actual_sha256=digest, expected_sha256=GAME)
            if digest != GAME:
                errors.append('Game executable version differs; connection refused')
        except OSError:
            game = dict(status='UNREADABLE', disk_read=False)
            errors.append('Configured game executable is unreadable')
    try:
        import cryptography.x509  # Required by the frozen TLS certificate producer.
        crypto = dict(status='AVAILABLE', version=importlib.metadata.version('cryptography'))
    except (ImportError, importlib.metadata.PackageNotFoundError):
        crypto = dict(status='MISSING')
        errors.append('Install Python cryptography in this Python environment')
    return dict(result='LOCAL_DIAGNOSTIC_CONFIG_PASS' if not errors else 'LOCAL_DIAGNOSTIC_CONFIG_FAILED',
                bundle_id=bundle['build_id'], game_version=game, cryptography=crypto,
                errors=errors, native_profiles='NOT_ASSESSED', **FLAGS)


def invitation(path, profile):
    invite = read_json(path)
    require(type(invite) is dict and set(invite) == {'schema', 'host', 'port', 'fingerprint', 'invite', 'profile', 'diagnostic_only'},
            'Invalid invitation fields')
    require(invite['schema'] == 'san14.two-pc-preflight-invite.v1' and invite['diagnostic_only'] is True,
            'Not a diagnostic invitation')
    address(invite['host'])
    require(type(invite['port']) is int and 1 <= invite['port'] <= 65535, 'Invalid invitation port')
    require(type(invite['fingerprint']) is str and len(invite['fingerprint']) == 64 and
            all(c in '0123456789abcdef' for c in invite['fingerprint']), 'Invalid certificate fingerprint')
    require(type(invite['invite']) is str and 1 <= len(invite['invite']) <= 256 and invite['profile'] == profile,
            'Invitation belongs to a different tool build or profile')


def interactive():
    print('这是连接诊断工具，不会启动游戏或进入联机地图。')
    choice = input('1 检查本机；2 创建诊断房间；3 加入诊断房间：').strip()
    if choice == '1':
        return ['check']
    if choice == '2':
        return ['host', '--bind', input('输入本机局域网/VPN IPv4：').strip()]
    if choice == '3':
        return ['guest', '--invite', input('输入收到的 invite.json 路径：').strip().strip('"')]
    raise ValueError('请选择 1、2 或 3')


def main(argv=None):
    bundle, profile = verify_bundle()  # Before any protocol import or listener.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=HERE / 'local-config.json')
    sub = parser.add_subparsers(dest='mode', required=True)
    init = sub.add_parser('init')
    init.add_argument('--game-exe', type=Path)
    sub.add_parser('check')
    for name in ('host', 'guest'):
        command = sub.add_parser(name)
        command.add_argument('--timeout', type=int, default=600)
        if name == 'host':
            command.add_argument('--bind', required=True)
            command.add_argument('--port', type=int, default=41414)
            command.add_argument('--sample-kib', type=int, default=1024)
        else:
            command.add_argument('--invite', type=Path, required=True)
    if argv is None:
        argv = sys.argv[1:] or interactive()
    args = parser.parse_args(argv)
    path = args.config.resolve()
    if args.mode == 'init':
        require(path.parent.is_dir(), 'Local configuration directory does not exist')
        value = dict(schema='san14.connection-local.v1',
                     game_exe=str(args.game_exe.resolve()) if args.game_exe else None,
                     output_directory='private-runs')
        # Never overwrite an existing configuration, bundle file, or invitation.
        with path.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        print(json.dumps(dict(result='CONFIG_CREATED', config=str(path), **FLAGS)))
        return 0
    value = config(path)
    local = check_local(path, value, bundle)
    print(json.dumps(local, ensure_ascii=False), flush=True)
    if args.mode == 'check' or local['errors']:
        return int(bool(local['errors']))
    require(10 <= args.timeout <= 900, 'Timeout must be 10..900 seconds')
    if args.mode == 'host':
        args.bind = address(args.bind)
        require(0 <= args.port <= 65535 and 1 <= args.sample_kib <= 8192, 'Invalid port/sample size')
        args.force = 12  # Diagnostic seat, never a claimed in-game faction.
    else:
        invitation(args.invite, profile)
        args.force = 2
    args.output = anchored(path, value['output_directory'])
    args.game_exe = anchored(path, value['game_exe']) if value['game_exe'] else None
    sys.path.insert(0, str(HERE))
    import two_pc_preflight as core
    # The frozen module's real TLS/Room transfer remains unchanged.
    core.HERE = HERE
    if args.mode == 'host':
        core.host(args)
    else:
        core.guest(args)
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('诊断已取消；未连接原生游戏组件。')
        raise SystemExit(130)
    except (OSError, ValueError, KeyError, TimeoutError, ImportError, EOFError) as exc:
        print(json.dumps(dict(result='CONNECTION_DIAGNOSTIC_FAILED', error=type(exc).__name__,
                             message=str(exc), **FLAGS), ensure_ascii=False), flush=True)
        raise SystemExit(1)
