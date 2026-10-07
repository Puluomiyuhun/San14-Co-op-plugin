"""Pure report and fixture gates. Never calls launcher main or opens game."""
from pathlib import Path
from datetime import datetime
import copy,json,hashlib
import checkpoint_cc_file_start as m
from checkpoint_cc_file_fixture_gate import validate_fixture
P=Path(__file__).resolve().parent
fixture=P/'checkpoint_cc_file_probe_fixtures/20261007-005047-180362/result.json'
proof=validate_fixture(fixture,m.DLL)
old=json.loads((P/'native_file_identity_runs/20261006-211040-957998/result.json').read_text(encoding='utf8'))
rows=[]
def check(name,value):
    assert value,name
    rows.append({'case':name,'passed':True})
r=copy.deepcopy(old['adapter']);before=old['before'];r['mode']=2
r.update(stage='native_absence_observed_twice',existsCalls=2,sizeCalls=2,sizes=[0,0,0],readReturns=[0,0],verifyAttempts=0,readCalls=0,identityMatched=0,verifiedSize=0,localPinReleased=0)
check('complete_absence_only',m.report_ok(r,2,before))
for key,value in [('sizeCalls',1),('existsCalls',1),('readCalls',1),('identityMatched',1),('state',8),('stopRequested',1),('slotRestored',0),('protectionRestored',0),('localPinReleased',1),('sizes',[1,0,0]),('stage','native_absence_rejected')]:
    candidate=copy.deepcopy(r);candidate[key]=value
    check('reject_'+key,not m.report_ok(candidate,2,before))
check('absence_not_read_success',not m.report_ok(r,1,before))
check('read_not_absence',not m.report_ok(old['adapter'],2,before))
check('read_report_compatible',m.report_ok(old['adapter'],1,before))
check('independent_magic',m.MAGIC==0x53414E1443434631)
check('actual_CC_filename',m.TARGET.name=='svdexccSC03.s14')
result={'schema':'san14.checkpoint-cc-launcher-predicate.v1','result':'PASS','cases':rows,'fixture':proof,'launcher_sha256':m.sha(P/'checkpoint_cc_file_start.py'),'game_access':False}
out=P/('checkpoint_cc_file_launcher_test_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
out.write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({'result':'PASS','cases':len(rows),'path':str(out)}))
