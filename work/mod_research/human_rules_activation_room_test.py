"""Actual existing TLS/Room protocol, with explicit synthetic native fields.
Feeds the real room-derived Config into the independently allocated native CPU
fixture; never connects to a game process or presents this as two-PC acceptance.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import secrets
import struct
import subprocess
import sys
import tempfile
import threading
import time
P = Path(__file__).resolve().parent
sys.path[:0] = [str(P/'python_deps'), str(P.parents[1]/'outputs/san14-link')]
from human_rules_activation_room import Config, GAME_SHA, export_config, require_current, rules
from room_session import Room, RoomError, PROTOCOL, digest
from room_transport import Client, Server, make_certificate


def main(native_run):
    run = P/'human_rules_activation_room_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    settings = rules(1, 0)
    manifest = {'profile': {'protocol': PROTOCOL, 'game_sha256': GAME_SHA,
        'adapter_contract': 'research-no-native-room-adapter.v1', 'checkpoint_sha256': '1'*64,
        'rules_sha256': digest(settings)}, 'forces': [{'id': 12, 'name': 'A', 'main_district_id': 11},
        {'id': 2, 'name': 'B', 'main_district_id': 2}], 'source': {'test': 'owned memory only'}}
    room = Room(manifest)
    with tempfile.TemporaryDirectory(dir=run) as private:
        cert, key, fingerprint = make_certificate(private)
        with Server(('127.0.0.1', 0), room, cert, key) as server:
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
            thread.start()
            a = Client('127.0.0.1', server.server_address[1], fingerprint,
                       {'method': 'host', 'credential': room.host_token, 'profile': manifest['profile']})
            b = Client('127.0.0.1', server.server_address[1], fingerprint,
                       {'method': 'join', 'credential': room.invite, 'profile': manifest['profile']})
            try:
                for client, action, extra in [(a, 'select_force', {'force_id': 12}),
                        (b, 'select_force', {'force_id': 2}), (a, 'confirm_force', {}), (b, 'confirm_force', {})]:
                    v = client.request({'action': 'status'})
                    assert client.request({'action': action, 'request_id': secrets.token_hex(16),
                                           'expected_revision': v['state']['revision'], **extra})['ok']
                native = {0x11FCA1E0: struct.pack('<Q', 0x20000000),
                          0x20085130: struct.pack('<Q', 0x71000000),
                          0x11FD0C5C: struct.pack('<i', 1), 0x118EB628: struct.pack('<I', 1),
                          0x7100003A: b'\x0c', 0x71000034: struct.pack('<H', 203),
                          0x71000036: b'\x08', 0x71000037: b'\x0b', 0x710016A8: b'\0'*4}
                read = lambda address, length: native[address][:length]
                c = export_config(room, settings, 'A', image=0x10000000, root=0x20000000,
                                  world=0x71000000, read=read)
                require_current(room, settings, c)
                config_path = run/'room-native-config.bin'
                config_path.write_bytes(bytes(c))
                native_run = Path(native_run)
                r = subprocess.run([str(native_run/'fixture.exe'), 'routes', str(native_run/'fixture.dll'),
                     str(P/'game-runtime-image.bin'), str(config_path)], capture_output=True, timeout=20)
                (run/'native.stdout.txt').write_bytes(r.stdout+r.stderr)
                assert r.returncode == 0, r.stdout+r.stderr
                # No remote action or arbitrary settings digest activates native rules.
                assert not a.request({'action': 'seal_rules', 'request_id': secrets.token_hex(16)})['ok']
                bad = Config.from_buffer_copy(bytes(c)); bad.epoch[0] ^= 1
                try: require_current(room, settings, bad)
                except RoomError: pass
                else: raise AssertionError('stale export accepted')
                native[0x118EB628] = struct.pack('<I', 2)
                try: export_config(room, settings, 'A', image=0x10000000, root=0x20000000, world=0x71000000, read=read)
                except RoomError: pass
                else: raise AssertionError('native settings mismatch accepted')
                b.close()
                for _ in range(100):
                    with room.lock:
                        if room.players['B']['connection'] is None: break
                    time.sleep(.01)
                try: require_current(room, settings, c)
                except RoomError: pass
                else: raise AssertionError('disconnected binding accepted')
            finally:
                a.close(); b.close(); server.shutdown(); thread.join(2)
    result = {'result': 'PASS', 'real_loopback_tls_room': True, 'independent_native_process': True,
              'two_computers': False, 'game_access': False, 'native_sample_source': 'explicit fixture fields',
              'native_rules_calls': 'actual allocated source CALLs with real frozen resolver',
              'native_run': str(native_run), 'rules': settings,
              'checks': ['room A/B authenticated and bound', 'actual room export consumed by native Prepare/Seal',
                         'both humans and delegated native routes', 'remote seal unsupported',
                         'stale export rejected', 'native setting mismatch rejected', 'disconnect export rejected'],
              'source_sha256': {f: hashlib.sha256((P/f).read_bytes()).hexdigest() for f in
                               ['human_rules_activation_room.py', 'human_rules_activation_room_test.py']}}
    (run/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'result': 'PASS', 'path': str(run/'result.json')}))


if __name__ == '__main__': main(sys.argv[1])
