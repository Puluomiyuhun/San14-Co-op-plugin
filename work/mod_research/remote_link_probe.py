"""Independent two-path TLS network diagnostic; no Room or game integration.

Default help opens no network. serve creates fresh short-lived diagnostic
credentials; only its invite.json is transferred privately. Never give this
tool a real room invitation. check uses only Python's standard library.
serve additionally needs cryptography to create a short-lived certificate.
"""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
import argparse,ctypes as C,hashlib,hmac,ipaddress,json,secrets,socket,ssl,sys,threading,time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SCHEMA='san14.remote-link-probe-invite.v1';WIRE='san14.remote-link-probe-wire.v1'
CHANNELS=('control','download');MAX_PACKET=4096
FLAGS=dict(network_only=True,two_games=False,game_access=False,room_joined=False,native_installed=False,ready_sent=False)


def need(ok,message):
    if not ok:raise ValueError(message)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def _hex(value,size):return type(value) is str and len(value)==size and all(c in '0123456789abcdef' for c in value)
def _timeout(value):
    need(type(value) in (int,float) and .1<=value<=10,'Timeout must be 0.1..10 seconds');return float(value)
def _address(value,*,bind=False):
    need(type(value) is str,'Explicit IPv4 address required');ip=ipaddress.IPv4Address(value)
    need(not ip.is_multicast and (bind or not ip.is_unspecified),'Invalid diagnostic IPv4 address');return str(ip)
def _port(value,*,bind=False):
    need(type(value) is int and (0 if bind else 1)<=value<=65535,'Explicit TCP port required');return value
def _json(raw):
    def pairs(rows):
        value={}
        for key,item in rows:need(key not in value,'Duplicate JSON key');value[key]=item
        return value
    def invalid(_):raise ValueError('Nonfinite JSON value')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)


def invitation(value):
    fields={'schema','probe_id','host','ports','fingerprint','token','expires_at','network_only'}
    need(type(value) is dict and set(value)==fields and value['schema']==SCHEMA and value['network_only'] is True,
         'Independent diagnostic invitation required')
    need(_hex(value['probe_id'],32) and _hex(value['fingerprint'],64) and _hex(value['token'],64),'Malformed diagnostic identity')
    _address(value['host']);ports=value['ports']
    need(type(ports) is dict and set(ports)==set(CHANNELS),'Both diagnostic ports required')
    for port in ports.values():_port(port)
    need(ports['control']!=ports['download'],'Distinct diagnostic listeners required')
    need(type(value['expires_at']) is int and time.time()<value['expires_at']<=time.time()+605,'Diagnostic invitation expired or outside lifetime')
    return deepcopy(value)


def read_invitation(path):
    with Path(path).open('rb') as stream:raw=stream.read(MAX_PACKET+1)
    need(len(raw)<=MAX_PACKET,'Diagnostic invitation too large');return invitation(_json(raw.decode('utf-8-sig')))


def _private_bytes(path,raw):
    # Same current-token protected DACL and CREATE_NEW discipline as adapter
    # keys, but write bytes directly; diagnostic PEM/JSON are NOT adapter keys.
    from b_warm_adapter_key import Native,SA
    native=Native();name=native.path(path);resolved=Path(name).parent.resolve(strict=True)/Path(name).name
    need(not any((p/'.git').exists() for p in resolved.parents),'Diagnostic credentials must be outside a Git worktree')
    sd=C.c_void_p();native.check(native.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        'O:'+native.sid+'D:P(A;;FA;;;'+native.sid+')',1,C.byref(sd),None))
    attributes=SA(C.sizeof(SA),sd,False)
    try:handle=native.k.CreateFileW(name,0x40000000|0x20000,0,C.byref(attributes),1,0x80|0x200000|0x80000000,None)
    finally:native.k.LocalFree(sd)
    need(handle not in (None,C.c_void_p(-1).value),'Private diagnostic file already exists or cannot be created')
    try:
        native.file_check(handle);native.acl(handle);done=C.c_ulong();buffer=C.create_string_buffer(raw)
        native.check(native.k.WriteFile(handle,buffer,len(raw),C.byref(done),None));need(done.value==len(raw),'Incomplete private diagnostic write')
        native.check(native.k.FlushFileBuffers(handle));native.acl(handle)
    finally:native.k.CloseHandle(handle)


def _certificate(folder,lifetime):
    # Matches room_transport's TLS certificate SHA256 pin principle, with all
    # secret writes private from creation. No room/token implementation imported.
    # Match the standalone environment checker and relocated tools layout. This
    # runs only for explicit serve, never for import/help/the stdlib-only client.
    for path in (ROOT.parent/'deps',ROOT.parent/'mod_research/python_deps'):
        if path.is_dir() and str(path) not in sys.path:sys.path.append(str(path))
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'SAN14 independent network diagnostic')]);now=datetime.now(timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
        .not_valid_after(now+timedelta(seconds=lifetime+60)).sign(key,hashes.SHA256()))
    cert_path,key_path=folder/'probe-cert.pem',folder/'probe-key.pem'
    _private_bytes(key_path,key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    _private_bytes(cert_path,cert.public_bytes(serialization.Encoding.PEM))
    return cert_path,key_path,cert.fingerprint(hashes.SHA256()).hex()


def _proof(token,stage,payload):
    return hmac.new(bytes.fromhex(token),b'san14-independent-probe\0'+stage.encode()+b'\0'+canonical(payload),hashlib.sha256).hexdigest()
def _signed(token,stage,payload):return dict(payload,proof=_proof(token,stage,payload))
def _verify(token,stage,value,expected):
    need(type(value) is dict and set(value)==set(expected)|{'proof'} and
         all(value[k]==v and type(value[k]) is type(v) for k,v in expected.items()) and _hex(value['proof'],64),
         'Diagnostic channel or nonce differs')
    need(hmac.compare_digest(value['proof'],_proof(token,stage,expected)),'Diagnostic authentication failed')
def _send(sock,value):
    raw=canonical(value)+b'\n';need(len(raw)<=MAX_PACKET,'Diagnostic packet too large');sock.sendall(raw)
def _read(sock,timeout,closing=None):
    end=time.monotonic()+timeout;raw=b''
    while True:
        if closing is not None and closing.is_set():raise OSError('Diagnostic closed')
        remaining=end-time.monotonic()
        if remaining<=0:raise TimeoutError('Diagnostic read timeout')
        sock.settimeout(min(.2,remaining))
        try:part=sock.recv(min(1024,MAX_PACKET+1-len(raw)))
        except socket.timeout:continue
        if not part:raise EOFError('Diagnostic connection ended')
        raw+=part;need(len(raw)<=MAX_PACKET,'Diagnostic packet too large')
        if b'\n' in raw:
            need(raw.endswith(b'\n') and raw.count(b'\n')==1,'Unexpected diagnostic framing')
            return _json(raw)


class ProbeServer:
    def __init__(self,*,bind,advertise,control_port,download_port,output,lifetime=120,timeout=3):
        bind=_address(bind,bind=True);advertise=_address(advertise);_port(control_port,bind=True);_port(download_port,bind=True)
        need(control_port==0 or control_port!=download_port,'Distinct listener ports required')
        need(type(lifetime) is int and 1<=lifetime<=600,'Lifetime must be 1..600 seconds');self.timeout=_timeout(timeout)
        self.folder=Path(output).resolve();need(not self.folder.exists(),'Fresh diagnostic output required');self.folder.mkdir(parents=True)
        self.lock=threading.RLock();self.close_lock=threading.RLock();self.closing=threading.Event();self.closed=threading.Event()
        self.listeners={};self.clients=set();self.workers=[];self.threads=[];self.timer=None
        self.counts={c:dict(completed=0,errors=0) for c in CHANNELS};self.deadline=time.monotonic()+lifetime
        self.invitation=None
        try:
            cert,key,fingerprint=_certificate(self.folder,lifetime)
            self.context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);self.context.minimum_version=ssl.TLSVersion.TLSv1_2
            self.context.load_cert_chain(str(cert),str(key))
            for channel,port in zip(CHANNELS,(control_port,download_port)):
                listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM);self.listeners[channel]=listener
                listener.bind((bind,port));listener.listen(8);listener.settimeout(.2)
            self.invitation=dict(schema=SCHEMA,probe_id=secrets.token_hex(16),host=advertise,
                ports={c:s.getsockname()[1] for c,s in self.listeners.items()},fingerprint=fingerprint,
                token=secrets.token_hex(32),expires_at=int(time.time())+lifetime,network_only=True)
            _private_bytes(self.folder/'invite.json',canonical(self.invitation)+b'\n')
            for channel in CHANNELS:
                thread=threading.Thread(target=self._accept,args=(channel,),daemon=True,name='san14-probe-'+channel)
                self.threads.append(thread);thread.start()
            self.timer=threading.Timer(lifetime,self.close);self.timer.daemon=True;self.timer.start()
        except BaseException:self.close();raise

    def _accept(self,channel):
        listener=self.listeners[channel]
        while not self.closing.is_set():
            try:raw,_=listener.accept()
            except socket.timeout:continue
            except OSError:return
            with self.lock:
                if self.closing.is_set():raw.close();return
                self.clients.add(raw)
                worker=threading.Thread(target=self._handle,args=(channel,raw),daemon=True,name='san14-probe-client')
                self.workers.append(worker);worker.start()

    def _response(self,channel,request):
        need(time.monotonic()<self.deadline and not self.closing.is_set(),'Diagnostic lifetime ended')
        invite=self.invitation
        need(type(request) is dict and _hex(request.get('client_nonce'),64),'Client nonce required')
        base=dict(schema=WIRE,probe_id=invite['probe_id'],channel=channel,client_nonce=request['client_nonce'])
        _verify(invite['token'],'probe',request,base)
        base['server_nonce']=secrets.token_hex(32)
        return _signed(invite['token'],'challenge',base)

    def _handle(self,channel,raw):
        sock=None
        try:
            raw.settimeout(self.timeout);sock=self.context.wrap_socket(raw,server_side=True,do_handshake_on_connect=False)
            with self.lock:
                self.clients.discard(raw)
                if self.closing.is_set():sock.close();return
                self.clients.add(sock)
            sock.do_handshake();request=_read(sock,self.timeout,self.closing)
            response=self._response(channel,request);_send(sock,response)
            expected={k:v for k,v in response.items() if k!='proof'}
            _verify(self.invitation['token'],'ack',_read(sock,self.timeout,self.closing),expected)
            need(time.monotonic()<self.deadline and not self.closing.is_set(),'Diagnostic lifetime ended')
            _send(sock,_signed(self.invitation['token'],'done',expected))
            with self.lock:self.counts[channel]['completed']+=1
        except Exception:
            with self.lock:self.counts[channel]['errors']+=1
        finally:
            for connection in (sock,raw):
                if connection is not None:
                    try:connection.close()
                    except OSError:pass
                    with self.lock:self.clients.discard(connection)

    def report(self):
        with self.lock:
            return dict(result='NETWORK_DIAGNOSTIC_HOST',channels=deepcopy(self.counts),closed=self.closed.is_set(),
                active_connections=len(self.clients),listener_threads_alive=sum(t.is_alive() for t in self.threads),
                worker_threads_alive=sum(t.is_alive() for t in self.workers),**FLAGS)

    def close(self):
        with self.close_lock:
            if self.closed.is_set():return
            self.closing.set()
            if self.timer is not None:self.timer.cancel()
            with self.lock:sockets=[*self.listeners.values(),*self.clients]
            for sock in sockets:
                try:sock.shutdown(socket.SHUT_RDWR)
                except OSError:pass
                try:sock.close()
                except OSError:pass
            with self.lock:threads=[*self.threads,*self.workers]
            end=time.monotonic()+max(2,self.timeout+.5)
            for thread in threads:
                if thread is not threading.current_thread():thread.join(max(0,end-time.monotonic()))
            self.closed.set()
            row=self.report();row['cleanup_complete']=not row['active_connections'] and not row['listener_threads_alive'] and not row['worker_threads_alive']
            with (self.folder/'host-report.json').open('x',encoding='utf-8') as out:json.dump(row,out,indent=2)


def serve(**kwargs):return ProbeServer(**kwargs)


def _check_channel(invite,channel,timeout):
    started=time.monotonic();raw=None;sock=None;stage='connect'
    try:
        raw=socket.create_connection((invite['host'],invite['ports'][channel]),timeout=timeout)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.check_hostname=False;context.verify_mode=ssl.CERT_NONE
        stage='tls';sock=context.wrap_socket(raw,server_hostname=invite['host']);sock.settimeout(timeout)
        stage='fingerprint';actual=hashlib.sha256(sock.getpeercert(binary_form=True)).hexdigest()
        need(hmac.compare_digest(actual,invite['fingerprint']),'Diagnostic certificate fingerprint mismatch')
        base=dict(schema=WIRE,probe_id=invite['probe_id'],channel=channel,client_nonce=secrets.token_hex(32))
        stage='challenge';_send(sock,_signed(invite['token'],'probe',base));reply=_read(sock,timeout)
        need(type(reply) is dict and _hex(reply.get('server_nonce'),64),'Server nonce required')
        base['server_nonce']=reply['server_nonce'];_verify(invite['token'],'challenge',reply,base)
        stage='ack';_send(sock,_signed(invite['token'],'ack',base));_verify(invite['token'],'done',_read(sock,timeout),base)
        return dict(channel=channel,result='PASS',elapsed_ms=round((time.monotonic()-started)*1000),certificate_pinned=True,nonce_roundtrip=True)
    except Exception as exc:
        return dict(channel=channel,result='FAIL',stage=stage,error_type=type(exc).__name__,
                    elapsed_ms=round((time.monotonic()-started)*1000))
    finally:
        for connection in (sock,raw):
            if connection is not None:
                try:connection.close()
                except OSError:pass


def check(value,*,timeout=3):
    invite=invitation(value);timeout=_timeout(timeout)
    rows=[_check_channel(invite,channel,timeout) for channel in CHANNELS]
    return dict(result='PASS_NETWORK_BOTH_PATHS' if all(r['result']=='PASS' for r in rows) else 'FAIL_NETWORK_PATHS',
                channels=rows,diagnostic_only=True,**FLAGS)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode')
    host=sub.add_parser('serve');host.add_argument('--bind',required=True);host.add_argument('--advertise',required=True)
    host.add_argument('--control-port',type=int,required=True);host.add_argument('--download-port',type=int,required=True)
    host.add_argument('--output',type=Path,required=True);host.add_argument('--lifetime',type=int,default=120);host.add_argument('--timeout',type=float,default=3)
    guest=sub.add_parser('check');guest.add_argument('--invite',type=Path,required=True);guest.add_argument('--timeout',type=float,default=3)
    args=p.parse_args(argv)
    if args.mode is None:p.print_help();return 0
    owner=None
    try:
        if args.mode=='check':
            report=check(read_invitation(args.invite),timeout=args.timeout);print(json.dumps(report));return 0 if report['result'].startswith('PASS_') else 1
        owner=serve(bind=args.bind,advertise=args.advertise,control_port=args.control_port,download_port=args.download_port,
            output=args.output,lifetime=args.lifetime,timeout=args.timeout)
        print(json.dumps(dict(event='DIAGNOSTIC_LISTENING',invitation_path=str(owner.folder/'invite.json'),
            expires_at=owner.invitation['expires_at'],**FLAGS)),flush=True)
        owner.closed.wait();print(json.dumps(owner.report()));return 0
    except KeyboardInterrupt:return 130
    except Exception as exc:
        print(json.dumps(dict(result='DIAGNOSTIC_FAILED',error_type=type(exc).__name__,**FLAGS)));return 1
    finally:
        if owner is not None:owner.close()


if __name__=='__main__':raise SystemExit(main())
