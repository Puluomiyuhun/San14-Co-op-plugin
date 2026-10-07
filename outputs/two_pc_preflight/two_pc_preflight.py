"""Two-machine connectivity and byte-integrity preflight. No native backend imports."""
import argparse
from copy import deepcopy
import hashlib
import ipaddress
import json
from pathlib import Path
import secrets
import sys
import threading
import time
from room_session import Room, RoomError, canonical
from room_transport import Server, Client, make_certificate
from authoritative_sync import CheckpointPackage, CheckpointReceiver, scope_from_room, digest, sha, SyncError
from checkpoint_transfer import receive_checkpoint

HERE=Path(__file__).resolve().parent
PRIVATE=[ipaddress.ip_network(x) for x in ('127.0.0.0/8','10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','100.64.0.0/10')]
FLAGS=dict(native_backend_connected=False,native_gameplay_enabled=False,world_synchronized=False,native_loaded=False)

def require(ok,message):
    if not ok:raise RoomError(message)

def private_ip(value):
    addr=ipaddress.ip_address(value)
    require(addr.version==4 and any(addr in net for net in PRIVATE),'Use explicit LAN/VPN IPv4 (or loopback), never wildcard/public IP')
    return str(addr)

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def version_check(path,profile):
    if path is None:return dict(status='NOT_CHECKED',expected_sha256=profile['game_sha256'])
    actual=file_hash(path)
    require(actual==profile['game_sha256'],'Game executable SHA256 differs from supported room catalog; stop before connecting')
    return dict(status='EXACT_SHA256_MATCH',actual_sha256=actual,expected_sha256=profile['game_sha256'])

def write_json(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

class PreflightRoom(Room):
    """Diagnostic extension only. Never creates a PeriodCoordinator/native receipt."""
    def __init__(self,manifest,sample):
        super().__init__(manifest)
        require(type(sample) is bytes and 0<len(sample)<=8*1024*1024,'Diagnostic payload must be 1..8 MiB')
        self.sample=sample;self.package=None;self.scope=None;self.connections=None
        self.chunks={};self.delivered=set();self.ticket=None;self.channels={};self.done=None;self.issued=False
    def current(self):
        try:current=scope_from_room(self)
        except SyncError as exc:raise RoomError(str(exc)) from exc
        require(self.scope is not None and current==self.scope,'Room binding changed')
        require({p:r['connection'] for p,r in self.players.items()}==self.connections,'Control connection changed; restart preflight')
    def prepare(self):
        if self.package is not None:self.current();return
        self.scope=scope_from_room(self)
        self.connections={p:r['connection'] for p,r in self.players.items()}
        # These are explicitly diagnostic protocol placeholders, NOT observations
        # of a game date, command prefix or world. No load coordinator receives it.
        state=canonical(dict(schema='san14.preflight-payload.v1',diagnostic_only=True,**FLAGS))
        self.package=CheckpointPackage(self.scope,secrets.token_hex(16),1,{'sequence':0,'prefix_sha256':sha(b'preflight-no-commands')},
            {'year':1,'month':1,'day':1,'phase':'PLANNING_BOUNDARY'},'diagnostic-bytes-only-not-a-world',sha(self.sample),
            {'world.s14':self.sample,'adapter.json':state},source_player='A')
        self.chunks={(c['part'],c['index']):c for c in self.package.chunks()}
    def authenticate(self,request,connection):
        if type(request) is dict and request.get('method')=='preflight_download':
            with self.lock:
                self.current()
                require(set(request)=={'method','credential','profile'} and request['profile']==self.manifest['profile'],'Invalid download profile')
                require(self.ticket is not None and type(request['credential']) is str and secrets.compare_digest(request['credential'],self.ticket[0]) and time.monotonic()<self.ticket[1],'Expired/consumed diagnostic ticket')
                deadline=self.ticket[1];self.ticket=None;self.channels[connection]=deadline
                return dict(player_id='PREFLIGHT_DOWNLOAD',resume_token='',state=dict(phase='DIAGNOSTIC_TRANSFER_ONLY',**FLAGS))
        return super().authenticate(request,connection)
    def disconnect(self,player,connection):
        if player=='PREFLIGHT_DOWNLOAD':
            with self.lock:self.channels.pop(connection,None)
        else:super().disconnect(player,connection)
    def handle(self,player,connection,request):
        action=request.get('action') if type(request) is dict else None
        if action not in ('preflight_offer','preflight_chunk','preflight_received'):
            return super().handle(player,connection,request)
        try:
            with self.lock:
                if action=='preflight_offer':
                    require(set(request)=={'action'} and player=='B' and self.players['B']['connection']==connection,'Only bound guest control connection can offer')
                    self.prepare();require(not self.issued,'Diagnostic transfer already issued/in progress/completed');self.issued=True
                    token=secrets.token_urlsafe(32);self.ticket=(token,time.monotonic()+60)
                    return dict(ok=True,manifest=self.package.manifest,checkpoint_id=self.package.checkpoint_id,scope=deepcopy(self.scope),download_token=token,**FLAGS)
                self.current()
                if action=='preflight_chunk':
                    require(player=='PREFLIGHT_DOWNLOAD' and connection in self.channels and time.monotonic()<self.channels[connection],'Expired/unknown download channel')
                    require(set(request)=={'action','checkpoint_id','part','index'} and request['checkpoint_id']==self.package.checkpoint_id and type(request['part']) is str and type(request['index']) is int,'Invalid chunk request')
                    key=(request['part'],request['index']);require(key in self.chunks,'Unknown chunk');self.delivered.add(key)
                    return dict(ok=True,chunk=deepcopy(self.chunks[key]))
                require(player=='B' and connection==self.connections['B'] and set(request)=={'action','checkpoint_id','payload_sha256','version_check'},'Only original guest can report byte receipt')
                require(request['checkpoint_id']==self.package.checkpoint_id and request['payload_sha256']==sha(self.sample),'Diagnostic byte receipt mismatch')
                require(request['version_check'] in ('NOT_CHECKED','EXACT_SHA256_MATCH'),'Bad local version diagnostic')
                require(self.done is None and self.delivered==set(self.chunks),'Diagnostic already completed or transfer not fully served')
                self.done=dict(payload_sha256=request['payload_sha256'],guest_version_check=request['version_check'])
                return dict(ok=True,status='WAITING_NATIVE_BACKEND',**FLAGS)
        except (RoomError,SyncError,KeyError,TypeError) as exc:
            return dict(ok=False,error=str(exc),**FLAGS)

def request(client,packet):
    r=client.request(packet);require(r.get('ok') is True,r.get('error','Request failed'));return r

def bind(client,force,deadline):
    selected=False
    while time.monotonic()<deadline:
        s=request(client,{'action':'status'})['state']
        if s['bindings'] is not None:
            require(s['bindings'][client.player_id]['force_id']==force,'Unexpected own force binding')
            require(not s['native_gameplay_enabled'] and not s['world_synchronized'],'Unexpected native readiness')
            return s
        me=s['players'][client.player_id]
        action=None
        if not selected:action={'action':'select_force','force_id':force}
        elif len(s['players'])==2 and all(p['connected'] and p['force_id'] is not None for p in s['players'].values()) and not me['confirmed']:action={'action':'confirm_force'}
        if action:
            r=client.request(dict(action,request_id=secrets.token_hex(16),expected_revision=s['revision']))
            if not r.get('ok'):
                require(r.get('error')=='Stale room view; refresh selection',r.get('error','Selection failed'))
            elif action['action']=='select_force':selected=True
        time.sleep(.1)
    raise TimeoutError('Waiting for the other player/faction timed out')

def host(args):
    manifest=json.loads((HERE/'catalog.json').read_text(encoding='utf-8'))
    version=version_check(args.game_exe,manifest['profile']);address=private_ip(args.bind)
    run=args.output.resolve()/('host-'+secrets.token_hex(6));run.mkdir(parents=True)
    sample=secrets.token_bytes(args.sample_kib*1024)
    room=PreflightRoom(manifest,sample);cert,key,pin=make_certificate(run/'private-tls')
    with Server((address,args.port),room,cert,key) as server:
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.1},daemon=True);thread.start()
        connection=dict(schema='san14.two-pc-preflight-invite.v1',host=address,port=server.server_address[1],fingerprint=pin,invite=room.invite,profile=manifest['profile'],diagnostic_only=True)
        write_json(run/'invite.json',connection)
        print('Send ONLY invite.json to B:',run/'invite.json',flush=True)
        print('Listening for diagnostics only; native backend is disconnected.',flush=True)
        a=None
        try:
            a=Client(address,server.server_address[1],pin,dict(method='host',credential=room.host_token,profile=manifest['profile']))
            deadline=time.monotonic()+args.timeout;s=bind(a,args.force,deadline);done=None
            while time.monotonic()<deadline:
                request(a,{'action':'status'})
                with room.lock:done=deepcopy(room.done)
                if done:break
                time.sleep(.15)
            require(done is not None,'Guest diagnostic transfer timed out')
            report=dict(result='NETWORK_BYTES_PASS_WAITING_NATIVE_BACKEND',role='A',bindings=s['bindings'],version_check=version,guest_report=done,
                same_computer_loopback=ipaddress.ip_address(address).is_loopback,two_computers_proven=False,**FLAGS)
            write_json(run/'report.json',report);print(json.dumps(report,ensure_ascii=False),flush=True)
            return report
        finally:
            if a:a.close()
            server.shutdown();thread.join(5)

def guest(args):
    invite=json.loads(args.invite.read_text(encoding='utf-8'))
    require(invite.get('schema')=='san14.two-pc-preflight-invite.v1' and invite.get('diagnostic_only') is True,'Not a preflight invitation')
    host_ip=private_ip(invite['host'])
    manifest=json.loads((HERE/'catalog.json').read_text(encoding='utf-8'))
    require(invite['profile']==manifest['profile'],'Local tool/catalog profile differs from host')
    version=version_check(args.game_exe,manifest['profile'])
    run=args.output.resolve()/('guest-'+secrets.token_hex(6));run.mkdir(parents=True)
    b=Client(host_ip,invite['port'],invite['fingerprint'],dict(method='join',credential=invite['invite'],profile=manifest['profile']))
    try:
        state=bind(b,args.force,time.monotonic()+args.timeout)
        offer=request(b,{'action':'preflight_offer'});m=offer['manifest']
        require(offer['scope']['room_id']==state['room_id'] and offer['scope']['binding_epoch']==state['binding_epoch'] and offer['scope']['bindings']==state['bindings'],'Foreign room payload')
        require(m['state_contract']=='diagnostic-bytes-only-not-a-world','Unexpected diagnostic contract')
        receiver=CheckpointReceiver(m,offer['checkpoint_id'],offer['scope'],m['epoch'],m['period'],m['cut'])
        download=Client(host_ip,invite['port'],invite['fingerprint'],dict(method='preflight_download',credential=offer['download_token'],profile=manifest['profile']))
        started=time.monotonic();received=receive_checkpoint(download,receiver,action='preflight_chunk')
        payload=received['parts']['world.s14'];(run/'received-diagnostic.bin').write_bytes(payload)
        require(file_hash(run/'received-diagnostic.bin')==m['parts']['world.s14']['sha256'],'Written diagnostic bytes differ')
        request(b,dict(action='preflight_received',checkpoint_id=offer['checkpoint_id'],payload_sha256=sha(payload),version_check=version['status']))
        report=dict(result='NETWORK_BYTES_PASS_WAITING_NATIVE_BACKEND',role='B',bindings=state['bindings'],version_check=version,
            checkpoint_manifest_integrity_verified=True,payload_sha256=sha(payload),payload_bytes=len(payload),transfer_seconds=round(time.monotonic()-started,3),
            payload_is_game_save=False,same_computer_loopback=ipaddress.ip_address(host_ip).is_loopback,two_computers_proven=False,**FLAGS)
        write_json(run/'report.json',report);print(json.dumps(report,ensure_ascii=False),flush=True);return report
    finally:b.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='role',required=True)
    for name in ('host','guest'):
        p=sub.add_parser(name);p.add_argument('--force',type=int,default=12 if name=='host' else 2)
        p.add_argument('--game-exe',type=Path,help='Optional local executable for read-only SHA256 check; never launched')
        p.add_argument('--output',type=Path,default=HERE/'runs');p.add_argument('--timeout',type=int,default=600)
        if name=='host':p.add_argument('--bind',required=True);p.add_argument('--port',type=int,default=41414);p.add_argument('--sample-kib',type=int,default=1024)
        else:p.add_argument('--invite',type=Path,required=True)
    argv=None
    if len(sys.argv)==1:
        print('只检查连接与诊断文件传输；不启动游戏，不能开始联机。')
        role=input('A 主机输入 A，B 加入输入 B：').strip().upper()
        require(role in ('A','B'),'请输入 A 或 B')
        argv=['host','--bind',input('本机虚拟局域网 IPv4（本机自测用127.0.0.1）：').strip()] if role=='A' else ['guest','--invite',input('收到的 invite.json 完整路径：').strip().strip('"')]
        game=input('可选：游戏主程序 EXE 完整路径（只读摘要；直接回车将标为版本未检查）：').strip().strip('"')
        if game:argv+=['--game-exe',game]
    a=parser.parse_args(argv);require(10<=a.timeout<=900,'Timeout must be 10..900 seconds')
    if a.role=='host':require(0<=a.port<=65535 and 1<=a.sample_kib<=8192,'Invalid port/sample size')
    return host(a) if a.role=='host' else guest(a)

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    try:main()
    except (RoomError,SyncError,OSError,ValueError,KeyError,TimeoutError,ImportError) as e:
        print(json.dumps(dict(result='PREFLIGHT_FAILED',error=str(e),**FLAGS),ensure_ascii=False),flush=True);raise SystemExit(1)
