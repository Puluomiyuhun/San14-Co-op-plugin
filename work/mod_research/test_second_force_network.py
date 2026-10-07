"""Authentication/journal failure tests, synthetic executor only."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from second_force_reward_network import ROOT,Receiver,sign,SUPPORTED_SHA256

credentials={'A':{'key':'a'*64,'force_id':12},'B':{'key':'b'*64,'force_id':2}}
payload={'schema':'san14.second-force-pilot.v1','session':'session','client_id':'B','request_id':'1'*32,
         'command':{'schema':'san14.authority-reward-command.v1','game_sha256':SUPPORTED_SHA256,'context_sha256':'c'*64,
                    'date':{'year':203,'month':8,'day':11,'period':'中旬'},'force_id':2,'district_id':2,'funding_city_id':13,'officer_ids':[101,264,411]}}
checks=[]
with tempfile.TemporaryDirectory(dir=ROOT) as directory:
    folder=Path(directory);calls=[]
    def execute(c):calls.append(c);return {'synthetic':True,'officer_name':'郭女王'}
    r=Receiver(folder/'normal.jsonl','session',credentials,execute)
    def rejected(name,packet):
        before=len(calls);assert r.handle(packet)['status']=='REJECTED' and len(calls)==before,name
        checks.append(name)
    a=deepcopy(payload);a['client_id']='A';rejected('A cannot submit B command',sign(a,credentials['A']['key']))
    packet=sign(payload,credentials['B']['key']);packet['mac']='0'*64;rejected('bad MAC',packet)
    for field,value in [('session','other'),('schema','other'),('request_id',True),('client_id','unknown')]:
        a=deepcopy(payload);a[field]=value;rejected(field,sign(a,credentials['B']['key']))
    for field,value in [('force_id',True),('district_id',True),('funding_city_id',19),('officer_ids',[101,101,411]),('game_sha256','0'*64),('date',{})]:
        a=deepcopy(payload);a['command'][field]=value;rejected(field,sign(a,credentials['B']['key']))
    packet=sign(payload,credentials['B']['key']);first=r.handle(packet);assert first['status']=='COMPLETED' and len(calls)==1;checks.append('accepted once')
    assert r.handle(packet)=={**first,'duplicate':True} and len(calls)==1;checks.append('duplicate in process')
    r=Receiver(folder/'normal.jsonl','session',credentials,execute)
    assert r.handle(packet)=={**first,'duplicate':True} and len(calls)==1;checks.append('duplicate after restart')
    a=deepcopy(payload);a['command']['context_sha256']='d'*64;rejected('same id different content',sign(a,credentials['B']['key']))
    a=deepcopy(payload);a['request_id']='2'*32;rejected('second fixed pilot id',sign(a,credentials['B']['key']))
    def uncertain(c):calls.append(c);raise RuntimeError('Synthetic uncertain outcome')
    r=Receiver(folder/'unknown.jsonl','session',credentials,uncertain)
    assert r.handle(packet)['status']=='UNKNOWN_NO_AUTO_RETRY' and len(calls)==2;checks.append('uncertain outcome')
    r=Receiver(folder/'unknown.jsonl','session',credentials,execute)
    assert r.handle(packet)['status']=='UNKNOWN_NO_AUTO_RETRY' and len(calls)==2;checks.append('unknown does not retry after restart')
    pending=(folder/'unknown.jsonl').read_text().splitlines()[0]+'\n';(folder/'pending.jsonl').write_text(pending)
    r=Receiver(folder/'pending.jsonl','session',credentials,execute)
    assert r.handle(packet)['status']=='UNKNOWN_NO_AUTO_RETRY' and len(calls)==2;checks.append('in-progress does not retry after restart')
    (folder/'corrupt.jsonl').write_text('{')
    try:Receiver(folder/'corrupt.jsonl','session',credentials,execute)
    except ValueError:checks.append('corrupt journal fails closed')
    else:raise AssertionError('Corrupt journal accepted')
report={'result':'PASS','checks':checks,'count':len(checks),'scope':'Synthetic executor; no game access'}
(ROOT/'second-force-network-fixtures.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
