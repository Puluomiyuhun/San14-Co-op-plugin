"""Loopback proof: separate sender -> authenticated receiver -> native update.

One fixed game command only. Durable request journal refuses automatic replay
after uncertain execution. This is not a LAN room or a second game client.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from pilot_request import canonical,authenticate,sign,validate_payload,WORDS,BASELINE_SHA,GAME_SHA

ROOT=Path(__file__).resolve().parent


def receive(connection):
    data=bytearray()
    while len(data)<8192:
        chunk=connection.recv(min(4096,8192-len(data)))
        if not chunk:raise ValueError('Incomplete frame')
        data.extend(chunk)
        if b'\n' in data:
            line,rest=bytes(data).split(b'\n',1)
            if rest:raise ValueError('One frame per connection is required')
            return json.loads(line)
    raise ValueError('Frame too large')


class Journal:
    def __init__(self,path):
        self.path=Path(path);self.states={}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                row=json.loads(line);self.states[row['request_id']]=row

    def append(self,row):
        with self.path.open('ab') as stream:
            stream.write(canonical(row)+b'\n');stream.flush();os.fsync(stream.fileno())
        self.states[row['request_id']]=row

    def execute(self,payload,executor):
        validate_payload(payload)
        identity=payload['request_id'];digest=hashlib.sha256(canonical(payload)).hexdigest()
        old=self.states.get(identity)
        if old:
            if old['payload_sha256']!=digest:raise ValueError('Request id was reused for different content')
            if old['state']!='COMPLETED':
                return {'request_id':identity,'status':'UNKNOWN_NO_AUTO_RETRY','applied_to_game':None,'duplicate':True}
            return {**old['receipt'],'duplicate':True}
        # Durably record intent before any game API is entered.
        self.append({'request_id':identity,'payload_sha256':digest,'state':'IN_PROGRESS'})
        try:
            execution=executor(payload)
            receipt={'request_id':identity,'payload_sha256':digest,'status':'COMPLETED',
                     'applied_to_game':True,'execution_count':1,'duplicate':False,'effect':execution}
        except Exception as error:
            self.append({'request_id':identity,'payload_sha256':digest,'state':'UNKNOWN','error':str(error)})
            return {'request_id':identity,'status':'UNKNOWN_NO_AUTO_RETRY','applied_to_game':None,'duplicate':False,'error':str(error)}
        self.append({'request_id':identity,'payload_sha256':digest,'state':'COMPLETED','receipt':receipt})
        return receipt


def run_receiver(run,key):
    journal=Journal(run/'requests.jsonl')
    bound_request=None
    def execute(payload):
        command=run/'received-command.json'
        command.write_bytes(canonical(payload))
        process=subprocess.Popen([sys.executable,str(ROOT/'run_autonomous_pilot.py'),'--execute','--command-file',str(command)],
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            out,error=process.communicate(timeout=50)
        except subprocess.TimeoutExpired:
            # No termination of an adapter that may still have a game callback.
            raise RuntimeError('Adapter outcome is uncertain; no automatic resend is permitted')
        (run/'adapter.stdout.json').write_bytes(out);(run/'adapter.stderr.txt').write_bytes(error)
        if process.returncode:raise RuntimeError(f'Adapter returned {process.returncode}; inspect its saved diagnostics')
        result=json.loads(out)
        if result['result']!='PASS' or result['request_id']!=payload['request_id'] or result['adapter']['submit_calls']!=1:
            raise RuntimeError('Adapter acknowledgement mismatch')
        return {'soldiers':result['effects']['new_unit']['soldiers'],
                'garrison_spent':result['effects']['garrison_spent'],'actions_spent':result['effects']['actions_spent'],
                'game_submit_calls':result['adapter']['submit_calls'],
                'manual_confirmation_required':False,'adapter_result_directory':result['directory']}
    with socket.socket() as server:
        server.bind(('127.0.0.1',0));server.listen(2);server.settimeout(60)
        ready_temp=run/'ready.tmp'
        ready_temp.write_text(json.dumps({'port':server.getsockname()[1],'pid':os.getpid()}))
        ready_temp.replace(run/'ready.json')
        for _ in range(2):
            connection,_=server.accept()
            with connection:
                connection.settimeout(10)
                try:
                    payload=authenticate(receive(connection),key)
                    if bound_request is None:bound_request=payload['request_id']
                    if payload['request_id']!=bound_request:raise ValueError('This pilot session permits one request id only')
                    response=journal.execute(payload,execute)
                except (ValueError,TypeError,KeyError) as error:
                    response={'status':'REJECTED','applied_to_game':False,'error':str(error)}
                connection.sendall(canonical(response)+b'\n')


def run_demo():
    run=ROOT/'network-submit-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True,exist_ok=False)
    key=secrets.token_hex(32)
    env=os.environ.copy();env['SAN14_PILOT_SESSION_KEY']=key
    # Packet values are the previously captured game command, never game pointers.
    payload={'schema':'san14.pilot-submit.v1','request_id':secrets.token_hex(16),'game_sha256':GAME_SHA,
             'baseline_sha256':BASELINE_SHA,'force_id':12,'source_city_id':19,'command_words':WORDS.copy()}
    packet=sign(payload,key.encode())
    with (run/'receiver.log').open('w') as log:
        child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--receiver',str(run)],
                               env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        ready=run/'ready.json';deadline=time.monotonic()+10
        while not ready.exists():
            if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Receiver did not become ready')
            time.sleep(.05)
        endpoint=json.loads(ready.read_text());receipts=[]
        for _ in range(2):
            with socket.create_connection(('127.0.0.1',endpoint['port']),timeout=10) as connection:
                connection.settimeout(60);connection.sendall(canonical(packet)+b'\n')
                receipts.append(receive(connection))
        child.wait(timeout=5)
    (run/'receipts.json').write_text(json.dumps(receipts,indent=2))
    first,duplicate=receipts
    assert child.returncode==0 and first.get('status')=='COMPLETED',receipts
    assert first.get('applied_to_game') is True and first.get('execution_count')==1,receipts
    assert duplicate=={**first,'duplicate':True},receipts
    states=Journal(run/'requests.jsonl').states
    assert len(states)==1 and next(iter(states.values()))['state']=='COMPLETED'
    result={'result':'PASS','transport':'TCP 127.0.0.1','sender_pid':os.getpid(),'receiver_pid':endpoint['pid'],
            'separate_processes':os.getpid()!=endpoint['pid'],'request_id':payload['request_id'],
            'network_deliveries':2,'game_executions':1,'duplicate_request_returned_cached_receipt':True,
            'receipt':first,'two_game_clients':False,'two_computers':False,'post_test_restore':'REQUIRED',
            'directory':str(run)}
    output=ROOT.parents[1]/'outputs'/'san14-link'/'网络命令自动执行验证.json'
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (run/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receiver',type=Path)
    args=parser.parse_args()
    if args.receiver:run_receiver(args.receiver,os.environ['SAN14_PILOT_SESSION_KEY'].encode())
    else:run_demo()
