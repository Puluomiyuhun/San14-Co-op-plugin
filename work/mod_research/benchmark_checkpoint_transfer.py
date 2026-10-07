"""Real save over localhost TLS with an explicit synthetic stream shaper.

Measures artifact fetch/hash/local channel close, after auth/manifest receipt.
Not a WAN measurement or native save/reload benchmark. No game process access.
"""
from pathlib import Path
import sys,json,socket,socketserver,threading,queue,time,tempfile,secrets,statistics,zlib
HERE=Path(__file__).resolve().parent;OUT=HERE.parents[1]/'outputs/san14-link'
sys.path[:0]=[str(OUT),str(HERE/'python_deps'),str(HERE)]
from test_checkpoint_tls import TestRoom
from room_transport import Server,Client,make_certificate
from authoritative_sync import CheckpointPackage,CheckpointReceiver,scope_from_room,digest,sha
from checkpoint_transfer import receive_checkpoint


class Bridge(socketserver.BaseRequestHandler):
    def handle(self):
        upstream=socket.create_connection(self.server.target,timeout=5)
        incoming=self.request
        for sock in (upstream,incoming):
            sock.settimeout(.5);sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        done=threading.Event();errors=[]
        def direction(src,dst):
            packets=queue.Queue(maxsize=128)
            def read():
                due=0
                try:
                    while not done.is_set():
                        try:data=src.recv(65536)
                        except socket.timeout:continue
                        if not data:break
                        delay=self.server.rtt_ms/2000
                        serial=len(data)*8/(self.server.mbps*1_000_000) if self.server.mbps else 0
                        due=max(time.perf_counter()+delay,due)+serial
                        packets.put((due,data),timeout=5)
                except (OSError,queue.Full) as e:
                    if not done.is_set():errors.append(str(e))
                finally:
                    try:packets.put(None,timeout=5)
                    except queue.Full:done.set()
            reader=threading.Thread(target=read,daemon=True);reader.start()
            try:
                while not done.is_set():
                    try:item=packets.get(timeout=.5)
                    except queue.Empty:continue
                    if item is None:break
                    due,data=item
                    if done.wait(max(0,due-time.perf_counter())):break
                    dst.sendall(data)
            except OSError as e:
                if not done.is_set():errors.append(str(e))
            finally:
                try:dst.shutdown(socket.SHUT_WR)
                except OSError:pass
                reader.join(timeout=6)
        threads=[threading.Thread(target=direction,args=p,daemon=True) for p in ((incoming,upstream),(upstream,incoming))]
        for t in threads:t.start()
        for t in threads:t.join(timeout=30)
        done.set()
        upstream.close()
        self.server.completed+=1
        self.server.errors.extend(errors)


class Shaper(socketserver.ThreadingTCPServer):
    daemon_threads=True
    def __init__(self,target,rtt_ms,mbps):
        self.target=target;self.rtt_ms=rtt_ms;self.mbps=mbps;self.completed=0;self.errors=[]
        super().__init__(('127.0.0.1',0),Bridge)


def main():
    slot=Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14')
    raw=slot.read_bytes();before=sha(raw)
    assert before=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
    manifest=json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8'));room=TestRoom(manifest)
    scratch=HERE/'checkpoint-transfer-bench';scratch.mkdir(exist_ok=True)
    records=[];a=b=None
    with tempfile.TemporaryDirectory(prefix='case-',dir=scratch) as tmp:
        assert Path(tmp).resolve().is_relative_to(scratch.resolve())
        cert,key,pin=make_certificate(tmp)
        with Server(('127.0.0.1',0),room,cert,key) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def connect(addr,method,credential):
                return Client(*addr,pin,{'method':method,'credential':credential,'profile':manifest['profile']})
            def offline():
                deadline=time.monotonic()+4
                while a.request({'action':'status'})['state']['players']['B']['connected']:
                    assert time.monotonic()<deadline;time.sleep(.01)
            try:
                a=connect(server.server_address,'host',room.host_token);b=connect(server.server_address,'join',room.invite)
                for client,force in [(a,12),(b,2)]:
                    s=client.request({'action':'status'})['state']
                    assert client.request({'action':'select_force','request_id':secrets.token_hex(16),'expected_revision':s['revision'],'force_id':force})['ok']
                for client in (a,b):
                    s=client.request({'action':'status'})['state']
                    assert client.request({'action':'confirm_force','request_id':secrets.token_hex(16),'expected_revision':s['revision']})['ok']
                scope=scope_from_room(room);epoch=secrets.token_hex(16);cut={'sequence':0,'prefix_sha256':digest(scope)}
                sidecar=b'{"fixture":"transfer-only","native_coverage":"UNVERIFIED"}'
                room.package=CheckpointPackage(scope,epoch,1,cut,{'year':203,'month':8,'day':21,'phase':'PLANNING_BOUNDARY'},
                    'transfer-performance-fixture.v1','0'*64,{'world.s14':raw,'adapter.json':sidecar},source_player='A')
                token=b.resume_token;b.close();b=None;offline()
                for rtt,mbps in [(0,0),(80,10),(150,2)]:
                    with Shaper(server.server_address,rtt,mbps) as proxy:
                        pt=threading.Thread(target=proxy.serve_forever,daemon=True);pt.start()
                        try:
                            # Alternate windows to limit ordering/cache effects;
                            # three repetitions are only exploratory samples.
                            for repetition,window in [(n,w) for n in range(3) for w in (1,4)]:
                                b=connect(proxy.server_address,'resume',token);token=b.resume_token
                                assert b.state['phase']=='WAITING_NATIVE_ADAPTER' and not b.state['native_gameplay_enabled']
                                offer=b.request({'action':'test_checkpoint_manifest'});assert offer['ok']
                                receiver=CheckpointReceiver(offer['manifest'],offer['checkpoint_id'],scope,epoch,1,cut)
                                start=time.perf_counter()
                                got=receive_checkpoint(b,receiver,action='test_checkpoint_chunk',window=window)
                                elapsed=time.perf_counter()-start
                                assert got['parts']=={'world.s14':raw,'adapter.json':sidecar} and not got['native_loaded']
                                records.append({'synthetic_rtt_ms':rtt,'synthetic_mbps_per_direction':mbps or None,
                                    'window':window,'repetition':repetition,'fetch_and_hash_seconds':elapsed,
                                    'chunks':got['chunks'],'request_windows':got['request_windows']})
                                print(json.dumps(records[-1]),flush=True)
                                b.close();b=None;offline()
                        finally:
                            if b:b.close();b=None
                            proxy.shutdown();pt.join(timeout=5);assert not pt.is_alive()
                        deadline=time.monotonic()+5
                        while proxy.completed<6 and time.monotonic()<deadline:time.sleep(.02)
                        assert proxy.completed==6,('Proxy handlers not finished',proxy.completed)
                end_state=a.request({'action':'status'})['state']
                assert end_state['phase']=='BOUND_PEER_OFFLINE' and not end_state['native_gameplay_enabled']
            finally:
                if a:a.close()
                if b:b.close()
                server.shutdown();thread.join(timeout=5);assert not thread.is_alive()
    assert sha(slot.read_bytes())==before
    summary=[]
    for rtt,mbps in [(0,0),(80,10),(150,2)]:
        summary.append({'synthetic_rtt_ms':rtt,'synthetic_mbps_per_direction':mbps or None,
            'median_seconds_by_window':{str(w):statistics.median(x['fetch_and_hash_seconds'] for x in records
                 if x['synthetic_rtt_ms']==rtt and x['window']==w) for w in (1,4)}})
    wire=sum(len(json.dumps({'ok':True,'chunk':ch},sort_keys=True,separators=(',',':')).encode())+1 for ch in room.package.chunks())
    report={'schema':'san14.checkpoint-transfer-performance.v1','result':'PASS','source_save_bytes':len(raw),
        'source_save_sha256':before,'zlib_level6_bytes':len(zlib.compress(raw,6)),'response_json_bytes':wire,
        'fixture_sidecar_bytes':len(sidecar),'summary':summary,'samples':records,'sample_count':len(records),
        'listeners_stopped':True,'game_processes_opened':0,'real_WAN_measured':False,'real_load_measured':False,
        'native_gameplay_enabled':False,
        'limits':['Local TCP byte-stream delay/bandwidth simulation, not real WAN packet loss/congestion.',
            'No TLS connection/authentication/manifest time included; timed fetch, integrity verification and local channel close.',
            'Helper consumes one transfer channel. Persistent control plus separate artifact-channel integration is not implemented.',
            'Uses one existing 274920-byte save and an unverified fixture sidecar; future checkpoints may be larger.',
            'Native save/load and synchronization barrier costs are unmeasured here.',
            'Artifact endpoint is a test Room subclass only; production room remains gameplay disabled.']}
    (HERE/'checkpoint-transfer-performance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':'PASS','summary':summary,'bytes':wire}),flush=True)


if __name__=='__main__':main()
