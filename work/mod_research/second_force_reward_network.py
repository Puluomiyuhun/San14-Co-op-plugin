"""Bounded loopback test: authenticated B command executed on an A-view host.

Exactly one fixed reward command, one receiver, no LAN listener or game replica.
Pending/unknown outcomes never retry native execution automatically.
"""
import argparse
from datetime import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'outputs/san14-link'))
from game_reader import SUPPORTED_SHA256
from reward_preflight import canonical

def sign(payload,key):
    return {'payload':payload,'mac':hmac.new(key.encode(),canonical(payload),hashlib.sha256).hexdigest()}

class Receiver:
    def __init__(self,path,session,credentials,executor):
        self.path=Path(path);self.session=session;self.credentials=credentials;self.executor=executor
        self.state={};self.bound_request=None
        if self.path.exists():
            for line in self.path.read_text(encoding='utf-8').splitlines():
                row=json.loads(line)
                if row['state'] not in ('IN_PROGRESS','UNKNOWN','COMPLETED'):raise ValueError('Invalid journal state')
                self.state[row['request_id']]=row
                if self.bound_request not in (None,row['request_id']):raise ValueError('Multiple journal requests')
                self.bound_request=row['request_id']

    def append(self,row):
        with self.path.open('ab') as f:f.write(canonical(row)+b'\n');f.flush();os.fsync(f.fileno())
        self.state[row['request_id']]=row

    def authenticate(self,packet):
        if type(packet) is not dict or set(packet)!={'payload','mac'}:raise ValueError('Bad packet')
        p=packet['payload']
        if type(p) is not dict or set(p)!={'schema','session','client_id','request_id','command'}:raise ValueError('Bad payload')
        if type(p['client_id']) is not str or p['client_id'] not in self.credentials:raise ValueError('Unknown client')
        credential=self.credentials[p['client_id']]
        if type(packet['mac']) is not str or not hmac.compare_digest(packet['mac'],sign(p,credential['key'])['mac']):raise ValueError('Invalid authentication')
        if p['schema']!='san14.second-force-pilot.v1' or p['session']!=self.session:raise ValueError('Wrong session/schema')
        if type(p['request_id']) is not str or re.fullmatch('[0-9a-f]{32}',p['request_id']) is None:raise ValueError('Bad request id')
        c=p['command']
        keys={'schema','game_sha256','context_sha256','date','force_id','district_id','funding_city_id','officer_ids'}
        if type(c) is not dict or set(c)!=keys:raise ValueError('Bad command')
        if type(c['force_id']) is not int or c['force_id']!=credential['force_id']:raise ValueError('Session faction mismatch')
        if c['schema']!='san14.authority-reward-command.v1' or c['game_sha256']!=SUPPORTED_SHA256:raise ValueError('Wrong command/build')
        if c['force_id']!=2 or type(c['district_id']) is not int or c['district_id']!=2 or type(c['funding_city_id']) is not int or c['funding_city_id']!=13:
            raise ValueError('Only fixed Liu Bei reward is supported by this pilot')
        if type(c['officer_ids']) is not list or any(type(x) is not int for x in c['officer_ids']) or c['officer_ids']!=[101,264,411]:raise ValueError('Unsupported officers')
        if type(c['context_sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',c['context_sha256']):raise ValueError('Bad context digest')
        if c['date']!={'year':203,'month':8,'day':11,'period':'中旬'}:raise ValueError('Wrong turn')
        return p

    def handle(self,packet):
        try:p=self.authenticate(packet)
        except (ValueError,TypeError,KeyError) as e:return {'status':'REJECTED','applied_to_game':False,'error':str(e)}
        identity=p['request_id'];digest=hashlib.sha256(canonical(p)).hexdigest()
        old=self.state.get(identity)
        if old:
            if old['digest']!=digest:return {'status':'REJECTED','applied_to_game':False,'error':'Request id content changed'}
            if old['state']!='COMPLETED':return {'status':'UNKNOWN_NO_AUTO_RETRY','applied_to_game':None,'duplicate':True}
            return {**old['receipt'],'duplicate':True}
        if self.bound_request not in (None,identity):return {'status':'REJECTED','applied_to_game':False,'error':'Pilot already bound to another request'}
        self.bound_request=identity
        self.append({'request_id':identity,'digest':digest,'state':'IN_PROGRESS'})
        try:
            result=self.executor(p['command'])
            receipt={'status':'COMPLETED','request_id':identity,'applied_to_game':True,'duplicate':False,'effect':result}
        except Exception as e:
            self.append({'request_id':identity,'digest':digest,'state':'UNKNOWN','error':str(e)})
            return {'status':'UNKNOWN_NO_AUTO_RETRY','applied_to_game':None,'duplicate':False,'error':str(e)}
        self.append({'request_id':identity,'digest':digest,'state':'COMPLETED','receipt':receipt})
        return receipt

def receive(connection):
    data=bytearray()
    while len(data)<32768:
        chunk=connection.recv(min(4096,32768-len(data)))
        if not chunk:raise ValueError('Incomplete packet')
        data.extend(chunk)
        if b'\n' in data:
            line,rest=bytes(data).split(b'\n',1)
            if rest:raise ValueError('One packet per connection')
            return json.loads(line)
    raise ValueError('Packet exceeds bound')

def run_receiver(run):
    config=json.loads(os.environ['SAN14_SECOND_FORCE_SESSION'])
    def execute(command):
        path=run/'authorized-command.json'
        with path.open('x',encoding='utf-8') as f:json.dump(command,f,ensure_ascii=False,indent=2)
        child=subprocess.Popen([sys.executable,str(ROOT/'run_second_force_reward.py'),'--execute','--command-file',str(path)],
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        try:out,error=child.communicate(timeout=45)
        except subprocess.TimeoutExpired:raise RuntimeError('Adapter outcome unknown; process not terminated and no retry allowed')
        (run/'adapter.stdout.json').write_bytes(out);(run/'adapter.stderr.txt').write_bytes(error)
        if child.returncode:raise RuntimeError('Adapter failed; inspect preserved diagnostics')
        result=json.loads(out)
        if result['result']!='PASS' or not result['executed'] or result['execution']['submit_calls']!=1 or result['command']!=command:raise RuntimeError('Adapter response mismatch')
        return {'viewer_force_id':result['viewer_force_id'],'command_force_id':result['command_force_id'],
                'submit_calls':result['execution']['submit_calls'],'directory':result['directory'],'effects':result['effects']}
    receiver=Receiver(run/'journal.jsonl',config['session'],config['credentials'],execute)
    with socket.socket() as server:
        server.bind(('127.0.0.1',0));server.listen(4);server.settimeout(60)
        (run/'ready.tmp').write_text(json.dumps({'port':server.getsockname()[1],'pid':os.getpid()}))
        (run/'ready.tmp').replace(run/'ready.json')
        for _ in range(4):
            connection,_=server.accept()
            with connection:
                connection.settimeout(50)
                try:reply=receiver.handle(receive(connection))
                except (ValueError,TypeError,KeyError) as e:reply={'status':'REJECTED','applied_to_game':False,'error':str(e)}
                connection.sendall(canonical(reply)+b'\n')

def run_demo():
    tests=json.loads((ROOT/'second-force-network-fixtures.json').read_text());assert tests['result']=='PASS'
    dry=json.loads((ROOT/'second-force-reward-dry-latest.json').read_text(encoding='utf-8'))
    assert dry['result']=='PASS' and not dry['executed']
    assert not (ROOT/'second-force-reward-once.json').exists(),'Existing attempt; do not retry automatically'
    run=ROOT/'second-force-network-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    config={'session':secrets.token_hex(16),'credentials':{key:{'key':secrets.token_hex(32),'force_id':force} for key,force in [('A',12),('B',2)]}}
    payload={'schema':'san14.second-force-pilot.v1','session':config['session'],'client_id':'B','request_id':secrets.token_hex(16),'command':dry['command']}
    unauthorized={**payload,'client_id':'A'}
    changed={**payload,'command':{**payload['command'],'context_sha256':'0'*64}}
    packets=[sign(unauthorized,config['credentials']['A']['key']),sign(payload,config['credentials']['B']['key']),
             sign(payload,config['credentials']['B']['key']),sign(changed,config['credentials']['B']['key'])]
    env=os.environ.copy();env['SAN14_SECOND_FORCE_SESSION']=json.dumps(config)
    with (run/'receiver.log').open('wb') as log:
        child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--receiver',str(run)],env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        deadline=time.monotonic()+10
        while not (run/'ready.json').exists():
            if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Receiver did not become ready')
            time.sleep(.05)
        ready=json.loads((run/'ready.json').read_text());receipts=[]
        for packet in packets:
            with socket.create_connection(('127.0.0.1',ready['port']),timeout=5) as connection:
                connection.settimeout(55);connection.sendall(canonical(packet)+b'\n');receipts.append(receive(connection))
        child.wait(timeout=5)
    with (run/'receipts.json').open('x',encoding='utf-8') as f:json.dump(receipts,f,ensure_ascii=False,indent=2)
    assert child.returncode==0
    assert [r['status'] for r in receipts]==['REJECTED','COMPLETED','COMPLETED','REJECTED'],receipts
    assert receipts[2]=={**receipts[1],'duplicate':True}
    assert receipts[1]['effect']['submit_calls']==1
    result={'result':'PASS','directory':str(run),'transport':'TCP loopback','sender_pid':os.getpid(),'receiver_pid':ready['pid'],
            'network_packets':4,'native_submit_calls':1,'bound_force':2,'viewer_force':12,
            'wrong_faction_rejected':True,'duplicate_cached':True,'changed_id_content_rejected':True,
            'two_real_games':False,'other_client_state_replication':False,'restore_required':True,
            'effect':receipts[1]['effect']}
    with (run/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    (ROOT/'second-force-network-live-latest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--receiver',type=Path);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if a.receiver:run_receiver(a.receiver)
    elif a.execute:run_demo()
    else:p.error('Use --execute for the single fixed real-game experiment')
