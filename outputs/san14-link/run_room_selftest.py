"""Real local TLS room exchange; never opens SAN14 or calls its adapter."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from room_transport import Client
from room_session import RoomError, digest

HERE = Path(__file__).resolve().parent
SCRATCH = HERE.parents[1] / 'work' / 'room_protocol_tests'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=HERE / '房间势力目录.json')
    parser.add_argument('--command-input', type=Path)
    parser.add_argument('--output', type=Path, default=HERE / '房间连接与选势力验证.json')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    known = {f['id'] for f in manifest['forces']}
    assert {12,2} <= known, 'This bounded demo selects Zhang Lu / Liu Bei'
    command = (json.loads(args.command_input.read_text(encoding='utf-8'))['command'] if args.command_input else
               {'schema':'san14.authority-reward-command.v1','force_id':2,'game_sha256':manifest['profile']['game_sha256']})
    assert command['force_id'] == 2 and command['game_sha256'] == manifest['profile']['game_sha256']
    checks = []
    SCRATCH.mkdir(parents=True, exist_ok=True)
    a = b = None
    process = None
    with tempfile.TemporaryDirectory(prefix='tls-room-', dir=SCRATCH) as temporary:
        private = Path(temporary).resolve()
        # Verify the exact recursive-cleanup target is inside this task scratch.
        assert private.is_relative_to(SCRATCH.resolve()) and private != SCRATCH.resolve()
        log = (private / 'server.log').open('wb')
        try:
            process = subprocess.Popen([sys.executable, str(HERE / 'room_transport.py'), '--manifest', str(args.manifest.resolve()),
                                        '--private-state', str(private), '--lifetime', '60'],
                                       stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            deadline = time.monotonic() + 10
            while not (private / 'connection.json').exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('Room server did not start: '+(private/'server.log').read_text(encoding='utf-8',errors='replace'))
                time.sleep(.025)
            config = json.loads((private / 'connection.json').read_text(encoding='utf-8'))
            def connect(method, credential, profile=None, pin=None):
                return Client(config['host'], config['port'], pin or config['fingerprint'],
                              {'method': method, 'credential': credential, 'profile': profile or config['profile']})
            def rejected_connect(label, **kwargs):
                try:
                    c = connect(**kwargs)
                except RoomError:
                    checks.append(label)
                else:
                    c.close();raise AssertionError(label)
            rejected_connect('wrong certificate pin rejected before credentials', method='host', credential=config['host_token'], pin='0'*64)
            bad = deepcopy(config['profile']);bad['adapter_contract'] = 'unsupported'
            rejected_connect('version/profile mismatch rejected', method='join', credential=config['invite'], profile=bad)
            a = connect('host', config['host_token'])
            b = connect('join', config['invite'])
            checks.append('two distinct authenticated players over TLS')
            def request(client, action, **fields):
                return client.request({'action':action,'request_id':secrets.token_hex(16),**fields})
            def select(client, force):
                s = client.request({'action':'status'})['state']
                return request(client,'select_force',force_id=force,expected_revision=s['revision'])
            def confirm(client):
                s = client.request({'action':'status'})['state']
                return request(client,'confirm_force',expected_revision=s['revision'])
            assert select(a,12)['ok']
            assert not select(b,12)['ok'];checks.append('duplicate faction rejected')
            assert select(b,2)['ok'] and confirm(a)['ok']
            assert a.state['binding_epoch'] is None;checks.append('one confirmation cannot lock room')
            assert confirm(b)['ok'];state = b.state
            assert state['phase']=='WAITING_NATIVE_ADAPTER' and state['bindings']=={'A':{'force_id':12,'main_district_id':11},'B':{'force_id':2,'main_district_id':2}}
            checks.append('both confirmations lock distinct force/main-district bindings')
            assert not select(a,2)['ok'];checks.append('mid-match faction change rejected')
            envelope={'room_id':state['room_id'],'binding_epoch':state['binding_epoch'],'command':command}
            assert not request(a,'route_preview',envelope=envelope)['ok'];checks.append('A cannot claim B authority')
            q={'action':'route_preview','request_id':secrets.token_hex(16),'envelope':envelope}
            result=b.request(q);assert result['ok'] and result['receipt']['authorized_force_id']==2 and not result['receipt']['applied_to_game']
            authority=result['receipt'];checks.append('B command resolved to server-bound force 2 without execution')
            duplicate=b.request(q);assert duplicate['duplicate'] and duplicate['receipt']==authority;checks.append('request retry uses same receipt')
            modified=deepcopy(q);modified['envelope']['command']['force_id']=12
            assert not b.request(modified)['ok'];checks.append('same request id with changed content rejected')
            old=deepcopy(envelope);old['binding_epoch']='old'
            assert not request(b,'route_preview',envelope=old)['ok'];checks.append('stale binding rejected')
            assert not request(a,'start_game')['ok'];checks.append('native start remains disabled')
            token=b.resume_token;b.close();b=None
            deadline=time.monotonic()+3
            while True:
                paused=a.request({'action':'status'})['state']
                if paused['phase']=='BOUND_PEER_OFFLINE':break
                assert time.monotonic()<deadline, 'Disconnect not observed'
                time.sleep(.025)
            assert paused['bindings']==state['bindings'];checks.append('disconnect reserves faction and marks offline')
            rejected_connect('invitation cannot steal disconnected guest seat',method='join',credential=config['invite'])
            b=connect('resume',token)
            assert b.player_id=='B' and b.state['your_force']==2 and b.state['binding_epoch']==state['binding_epoch'];checks.append('resume restores same identity and binding')
            assert not b.state['world_synchronized'] and not b.state['client_viewer_switched'];checks.append('room does not claim game synchronization or viewer switching')
            report={'result':'PASS','transport':'TCP with pinned TLS certificate; 127.0.0.1 only',
                    'server_pid':process.pid,'client_process_pid':os.getpid(),'client_connections':2,
                    'catalog_source':manifest['source'],'checks':checks,'check_count':len(checks),
                    'bindings':state['bindings'],'command_authority':authority,'command_sha256':digest(command),
                    'real_game_processes_connected':0,'game_commands_executed':0,
                    'native_game_started':False,'two_computers_tested':False,'host_restart_tested':False}
        finally:
            if a:a.close()
            if b:b.close()
            if process is not None and process.poll() is None:
                # This child is solely the bounded lobby test server, never SAN14.
                process.terminate()
                process.wait(timeout=5)
            log.close()
    report['test_listener_stopped']=True
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    print(f"房间协议检查通过：{len(checks)}项。A绑定张鲁，B绑定刘备；测试监听已退出。")
    print('仅验证连接、选势力和命令归属，没有启动真实联机或执行游戏操作。')
    print(str(args.output.resolve()))


if __name__=='__main__':
    main()
