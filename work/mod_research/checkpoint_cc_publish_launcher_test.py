"""Publisher report/ABI tests only; no game or launcher main invocation."""
from pathlib import Path
from datetime import datetime
import copy,ctypes as C,json
import checkpoint_cc_publish_start as m
P=Path(__file__).resolve().parent
old=m.load(P/'native_file_identity_runs/20261006-211040-957998/result.json')
r=copy.deepcopy(old['adapter']);before=old['before']
part=dict(state=5,osError=0,exceptionCode=0,existsCalls=3,sizeCalls=3,writeAttempts=1,writeReturned=1,nativeWriteReturn=1,
    intentCreated=1,intentDurable=1,localPinReleased=1,sourceMatched=1,matched=1,publishAttempts=1,writeMethod=0x12340000,
    sourceSha256=m.SHA,stage='published_and_observed_twice')
r['publish']=part;r['stage']='published_and_observed_twice'
rows=[]
def check(name,ok):
    assert ok,name
    rows.append({'case':name,'passed':True})
check('complete_publisher_report',m.report_ok(r,1,before))
for key,value in [('state',6),('writeAttempts',2),('writeReturned',0),('nativeWriteReturn',0),('intentCreated',0),('intentDurable',0),
    ('localPinReleased',0),('sourceMatched',0),('matched',0),('publishAttempts',2),('writeMethod',0),('sizeCalls',2),('existsCalls',2),
    ('sourceSha256','00'*32),('stage','native_file_write_once')]:
    candidate=copy.deepcopy(r);candidate['publish'][key]=value
    check('reject_publish_'+key,not m.report_ok(candidate,1,before))
for key,value in [('readCalls',1),('readReturns',[274880,1]),('identityMatched',0),('stopRequested',1),('slotRestored',0),('protectionRestored',0),('callbackActive',1)]:
    candidate=copy.deepcopy(r);candidate[key]=value
    check('reject_outer_'+key,not m.report_ok(candidate,1,before))
check('publish_does_not_satisfy_dry',not m.report_ok(r,0,before))
check('production_report_ABI',C.sizeof(m.Report)==680 and m.Report.publish.offset==520 and C.sizeof(m.PublishPart)==160)
raw=m.Report();raw.magic=m.MAGIC;raw.size=680;raw.version=1
raw.publish.state=5;raw.publish.writeMethod=0xFEDCBA9876543210;raw.publish.sourceSha256[:]=bytes.fromhex(m.SHA)
decoded=m.decode(bytes(raw))
check('decode_full_width_nested_pointer',decoded['publish']['writeMethod']==0xFEDCBA9876543210)
check('decode_full_source_hash',decoded['publish']['sourceSha256']==m.SHA)
check('fixed_target',m.TARGET.name=='svdexccSC03.s14')
result={'schema':'san14.cc-publisher-launcher-predicate.v1','result':'PASS','cases':rows,'launcher_sha256':m.sha(P/'checkpoint_cc_publish_start.py'),'game_access':False}
path=P/('checkpoint_cc_publish_launcher_test_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
m.save(path,result)
print(json.dumps({'result':'PASS','cases':len(rows),'path':str(path)}))
