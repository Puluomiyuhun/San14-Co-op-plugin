"""Actual slot34 bytes over two local pinned-TLS connections; no game access.

Only this bounded test subclass exposes read-only artifact fetch methods.
Production room_transport and Room.handle remain gameplay-disabled.
"""
from pathlib import Path
import sys,json,tempfile,threading,time,secrets
HERE=Path(__file__).resolve().parent;OUT=HERE.parents[1]/'outputs'/'san14-link'
sys.path[:0]=[str(OUT),str(HERE/'python_deps')]
from authoritative_sync import CheckpointPackage,CheckpointReceiver,scope_from_room,digest,sha
from room_session import Room
from room_transport import Server,Client,make_certificate,MAX_PACKET

class TestRoom(Room):
    package=None
    def handle(self,player,connection,request):
        if request.get('action') not in ('test_checkpoint_manifest','test_checkpoint_chunk'):
            return super().handle(player,connection,request)
        with self.lock:
            if player!='B' or self.players[player]['connection']!=connection or self.package is None:
                return {'ok':False,'error':'No authorized guest transfer'}
            if request=={'action':'test_checkpoint_manifest'}:
                return {'ok':True,'manifest':self.package.manifest,'checkpoint_id':self.package.checkpoint_id}
            if set(request)!={'action','checkpoint_id','part','index'} or request['checkpoint_id']!=self.package.checkpoint_id:
                return {'ok':False,'error':'Wrong checkpoint request'}
            for chunk in self.package.chunks():
                if chunk['part']==request['part'] and type(request['index']) is int and chunk['index']==request['index']:
                    return {'ok':True,'chunk':chunk}
            return {'ok':False,'error':'Unknown chunk'}

def main():
    slot=Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14')
    raw=slot.read_bytes();before=sha(raw)
    assert before=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
    manifest=json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8'));room=TestRoom(manifest)
    scratch=HERE/'checkpoint-tls';scratch.mkdir(exist_ok=True)
    a=b=None;checks=[]
    with tempfile.TemporaryDirectory(prefix='case-',dir=scratch) as temporary:
        folder=Path(temporary).resolve();assert folder.is_relative_to(scratch.resolve()) and folder!=scratch.resolve()
        cert,key,pin=make_certificate(folder)
        with Server(('127.0.0.1',0),room,cert,key) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def connect(method,credential):return Client('127.0.0.1',server.server_address[1],pin,{'method':method,'credential':credential,'profile':manifest['profile']})
            try:
                a=connect('host',room.host_token);b=connect('join',room.invite)
                for client,force in [(a,12),(b,2)]:
                    s=client.request({'action':'status'})['state']
                    assert client.request({'action':'select_force','request_id':secrets.token_hex(16),'expected_revision':s['revision'],'force_id':force})['ok']
                for client in (a,b):
                    s=client.request({'action':'status'})['state']
                    assert client.request({'action':'confirm_force','request_id':secrets.token_hex(16),'expected_revision':s['revision']})['ok']
                scope=scope_from_room(room);epoch=secrets.token_hex(16);cut={'sequence':0,'prefix_sha256':digest(scope)}
                # Only file transport is tested; this sidecar deliberately has
                # no claim to cover the native world or turn-end runtime.
                sidecar=json.dumps({'fixture':'file-transfer-only','native_state_coverage':'UNVERIFIED'}).encode()
                room.package=CheckpointPackage(scope,epoch,1,cut,{'year':203,'month':8,'day':21,'phase':'PLANNING_BOUNDARY'},
                      'file-integrity-test-not-native-world.v1','0'*64,{'world.s14':raw,'adapter.json':sidecar},source_player='A')
                response=b.request({'action':'test_checkpoint_manifest'});assert response['ok']
                receiver=CheckpointReceiver(response['manifest'],response['checkpoint_id'],scope,epoch,1,cut)
                checks.append('authenticated B receives room-bound manifest over pinned TLS')
                assert not a.request({'action':'test_checkpoint_manifest'})['ok'];checks.append('test fetch endpoint rejects the wrong seat')
                chunks=list(room.package.chunks());chunks.reverse();max_wire=0
                def fetch(chunk):
                    nonlocal max_wire
                    q={k:chunk[k] for k in ('checkpoint_id','part','index')};q['action']='test_checkpoint_chunk'
                    reply=b.request(q);assert reply['ok'];max_wire=max(max_wire,len(json.dumps(reply,separators=(',',':')).encode())+1)
                    return receiver.accept(reply['chunk'])
                for ch in chunks[:3]:fetch(ch)
                token=b.resume_token;b.close();b=None
                deadline=time.monotonic()+3
                while a.request({'action':'status'})['state']['players']['B']['connected']:
                    assert time.monotonic()<deadline;time.sleep(.01)
                b=connect('resume',token);assert b.state['binding_epoch']==scope['binding_epoch']
                checks.append('partial transfer resumes after B reconnects with the same binding')
                for ch in chunks[3:]:fetch(ch)
                assert fetch(chunks[0])['duplicate'];checks.append('out-of-order chunks and an exact retry accepted')
                received=receiver.verified_parts();assert received['world.s14']==raw and received['adapter.json']==sidecar
                checks.append('both reconstructed artifacts match bytes and SHA256')
                assert max_wire<=MAX_PACKET;checks.append('chunk packets fit the existing 64 KiB transport limit')
                status=b.request({'action':'status'})['state']
                assert status['phase']=='WAITING_NATIVE_ADAPTER' and not status['native_gameplay_enabled']
                checks.append('file receipt does not start/load the real game')
                assert sha(slot.read_bytes())==before;checks.append('original slot34 remains unchanged')
                report={'result':'PASS','checks':checks,'check_count':len(checks),'transport':'127.0.0.1 pinned TLS',
                    'client_connections':2,'B_reconnected':True,'source_save_size':len(raw),'save_sha256':before,
                    'chunk_count':len(chunks),'largest_packet_bytes':max_wire,'listener_stopped':False,
                    'real_game_processes_opened':0,'files_installed_into_game':0,'game_loaded':False,
                    'native_checkpoint_coverage_verified':False,'native_gameplay_enabled':False}
            finally:
                if a:a.close()
                if b:b.close()
                server.shutdown();thread.join(timeout=5);assert not thread.is_alive()
        report['listener_stopped']=True
    (HERE/'checkpoint-tls-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
