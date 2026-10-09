"""Data-only warm acceptance/start tests. No GameReader, process API or live invoke."""
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
import copy,ctypes as C,hashlib,json
import checkpoint_complete_live_acceptance_test as old
import b_warm_profile_contract as wire
import b_warm_start_acceptance as accept
import b_warm_start as start

P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
SEED=PRIVATE/'checkpoint_complete_live_owner_smoke/20261007-152554-825501/success-new/report.bin'
BUILD=PRIVATE/'b_warm_factory_runs/20261009-172050-464741/result.json'
BUILD_SHA='d08889ffb8cdbf517c141e8b3b2a8e05d38374008cd7833a041713fb48720499'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(v,why):
    if not v:raise AssertionError(why)
def refused(fn):
    try:fn()
    except (ValueError,FileNotFoundError):return
    raise AssertionError('unexpected acceptance')
def synthetic(variant=0):
    old.SEED=SEED;r,kw,_=old.synthetic()
    r.update(SessionState=13,HooksRestored=1,retained_hooks=False)
    for h in r['hooks']:h.update(observed=h['original'],dirty=0,published=0,restored=1,known=1,lastProtection=h['protection'])
    p=wire.Profile();p.file.name=b'svdexccSC03.s14';p.file.slot=63;p.file.size=r['bytes']['requested'];p.file.sha256[:]=bytes.fromhex(r['requestReadSha'])
    p.before=wire.Date(203,8,11);p.loaded=wire.Date(203,8,11);p.source=wire.Identity(666,12,11);p.target=wire.Identity(952,2,2);p.currentForce=12
    if variant:
        p.before=wire.Date(204,9,1);p.loaded=wire.Date(204,9,11);p.source=wire.Identity(111,7,6);p.target=wire.Identity(222,9,8);p.currentForce=2
        p.file.size+=32;p.file.sha256[:]=hashlib.sha256(b'explicit synthetic second profile').digest();r['requestReadSha']=bytes(p.file.sha256).hex()
        for b in (r['bytes'],r['lifecycle']['frozenBytes']):b.update(requested=p.file.size,returned=p.file.size,readRax=(b['readRax']&0xffffffff00000000)|p.file.size,sha256=r['requestReadSha'])
        r['identity']['worldForceAfter']=p.target.force
        for field in ('planningBeforeSample','planningAfterSample'):r[field]['uiForceContext']=p.target.force
        r['PlanningUiForceMatches']=1
        kw['planning']['context']['snapshot']['date'].update(year=p.before.year,month=p.before.month,day=p.before.day)
        kw['planning']['context']['snapshot']['player'].update(force_id=p.currentForce,ruler_id=952)
    # Pair fields remain actual seed *pointers*, never replace them with IDs.
    pr=wire.Report();pr.magic=wire.MAGIC;pr.size=C.sizeof(pr);pr.version=1;pr.configured=pr.ready=1;pr.profile=p
    rt=wire.RetireReport();rt.version=1;rt.size=C.sizeof(rt);rt.bound=rt.sealed=rt.restored=rt.completionSeen=1;rt.eligibleChecks=1
    rt.attempt=kw['attempt'];rt.userCall=r['planningUserCall'];rt.identityCall=r['planningIdentityCall'];rt.loadCall=r['planningCompletedCall'];rt.thread=r['hardware']['thread']
    kw['planning']['profileSha256']=hashlib.sha256(bytes(p)).hexdigest();kw.update(profile=p,profile_report=bytes(pr),retire_report=bytes(rt))
    old.sync_pods(r);return wire.old.decode_report(old.report_bytes(r)),kw
def normalize(r):old.sync_pods(r);return wire.old.decode_report(old.report_bytes(r))
def altered_retire(kw,field,value):
    rt=wire.RetireReport.from_buffer_copy(kw['retire_report']);setattr(rt,field,value);kw['retire_report']=bytes(rt)
def altered_profile(kw,field,value):
    p=wire.Report.from_buffer_copy(kw['profile_report']);setattr(p.profile,field,value);kw['profile_report']=bytes(p)
class Clock:
    def __init__(self):self.now=0.
    def monotonic(self):return self.now
    def sleep(self,n):self.now+=n
class Samples:
    def __init__(self,rows):self.rows=rows;self.calls=0
    def call(self,address,data=None,output_size=0):
        row,kw=self.rows[min(self.calls//3,len(self.rows)-1)];position=self.calls%3;self.calls+=1
        require(address==position+1,'report export order')
        raw=(old.report_bytes(row),kw['profile_report'],kw['retire_report'])[position];require(len(raw)==output_size,'exact report output size');return 0,raw
def complete(rows):
    kw=rows[0][1];cfg=wire.Config();cfg.profile=kw['profile'];cfg.owner.attempt=kw['attempt'];cfg.owner.epoch=kw['epoch'];cfg.owner.generation=kw['generation'];cfg.owner.attachment[:]=bytes.fromhex(kw['attachment_hex'])
    calls=Samples(rows);records=[];clock=Clock();addresses={n:i+1 for i,n in enumerate(('GetCheckpointCompleteLiveOwnerReport','GetBWarmProfileReport','GetBWarmRetireReport'))}
    with patch.object(start,'time',clock):
        got=start.completion(calls,addresses,profile=kw['profile'],planning=kw['planning'],storage=kw['storage'],description=kw['description'],config=cfg,deadline=1.,record=lambda samples,row:records.append(row))
    return got,records,calls.calls
def main():
    run=PRIVATE/'b_warm_start_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result={'result':'FAIL','synthetic_classifier_tests':True,'game_process_access':False,'native_calls':0,'cases':[],'source_pins':{}}
    names=['b_warm_start_test.py','b_warm_start.py','b_warm_start_support.py','b_warm_start_acceptance.py','b_warm_profile_contract.py','b_warm_profile_capture.py','checkpoint_complete_live_acceptance_test.py','checkpoint_complete_live_acceptance.py','checkpoint_complete_live_owner_contract.py','checkpoint_live_prefetch_contract.py']
    for n in names:result['source_pins'][str(P/n)]=sha(P/n)
    result['private_pins']={str(SEED):sha(SEED),str(BUILD):sha(BUILD)}
    def case(name,fn):fn();result['cases'].append({'case':name,'passed':True})
    try:
        r,kw=synthetic();expected=accept.validate_report(r,**kw);require(expected['result']==accept.CLASSIFICATION and not expected['ready_authorized'],'baseline result')
        case('synthetic_completed_profile_target2',lambda:accept.validate_report(r,**kw))
        r9,k9=synthetic(1);case('synthetic_dynamic_size_date_target9_pointer_pairs',lambda:accept.validate_report(r9,**k9))
        negatives={
          'profile_bytes_mismatch':lambda rr,kk:altered_profile(kk,'currentForce',13),
          'profile_hash_not_capture':lambda rr,kk:kk['planning'].__setitem__('profileSha256','00'*32),
          'retire_attempt':lambda rr,kk:altered_retire(kk,'attempt',kk['attempt']+1),
          'retire_user_call':lambda rr,kk:altered_retire(kk,'userCall',rr['planningUserCall']+1),
          'retire_identity_call':lambda rr,kk:altered_retire(kk,'identityCall',rr['planningIdentityCall']+1),
          'retire_load_call':lambda rr,kk:altered_retire(kk,'loadCall',rr['planningCompletedCall']+1),
          'retire_not_sealed':lambda rr,kk:altered_retire(kk,'sealed',0),
          'restored_slot_still_bridge':lambda rr,kk:rr['hooks'][0].__setitem__('observed',rr['hooks'][0]['hook']),
          'native_bytes_wrong_hash':lambda rr,kk:rr['bytes'].__setitem__('sha256','00'*32),
          'identity_target_force_wrong':lambda rr,kk:rr['identity'].__setitem__('worldForceAfter',3),
          'nested_load_completion_wrong':lambda rr,kk:rr['identity'].__setitem__('completionCall',rr['identity']['completionCall']+1),
          'source_guard_error':lambda rr,kk:rr.__setitem__('GuardError',3),
          'active_dispatch':lambda rr,kk:rr.__setitem__('ActiveDispatch',1),
          'bridge_unbalanced':lambda rr,kk:rr['bridges'][0].__setitem__('returned',rr['bridges'][0]['returned']-1),
        }
        for name,mutate in negatives.items():
            rr,kk=copy.deepcopy(r),copy.deepcopy(kw);mutate(rr,kk);rr=normalize(rr);case('reject_'+name,lambda rr=rr,kk=kk:refused(lambda:accept.validate_report(rr,**kk)))
        rr=copy.deepcopy(r);rr['identity']['worldForceAfter']=9
        case('reject_raw_pod_disagrees_decoded',lambda:refused(lambda:accept.validate_report(rr,**kw)))
        later=copy.deepcopy(r);later['sequence']+=1
        case('completion_two_fresh_samples',lambda:require(complete([(r,kw),(later,kw)])[2]==6,'two full samples'))
        case('completion_duplicate_sequence_rejected',lambda:refused(lambda:complete([(r,kw),(r,kw)])))
        back=copy.deepcopy(r);back['sequence']-=1
        case('completion_regressing_sequence_rejected',lambda:refused(lambda:complete([(r,kw),(back,kw)])))
        incomplete=copy.deepcopy(r);incomplete['HooksRestored']=0
        last=copy.deepcopy(later);last['sequence']+=1
        case('completion_incomplete_does_not_count',lambda:require(complete([(incomplete,kw),(later,kw),(last,kw)])[2]==9,'requires two complete samples after incomplete'))
        changed=copy.deepcopy(kw);altered_retire(changed,'thread',wire.RetireReport.from_buffer_copy(changed['retire_report']).thread+1)
        case('completion_changed_frozen_key_requires_two_new',lambda:require(complete([(r,kw),(later,changed),(last,changed)])[2]==9,'stable frozen key samples'))
        err=copy.deepcopy(r);err['GuardError']=3
        case('completion_native_error_terminal',lambda:refused(lambda:complete([(err,kw)])))
        for name,attrs,want in [('unknown',{},True),('not_started',{'may_have_started':False,'completed':False},False),('started_incomplete',{'may_have_started':True,'completed':False},True),('started_completed',{'may_have_started':True,'completed':True},False)]:
            def check_calls(attrs=attrs,want=want):
                exc=RuntimeError('owned fake invoke');[setattr(exc,k,v) for k,v in attrs.items()]
                def invoke(*a):raise exc
                c=start.Calls(None,invoke)
                try:c.call(1)
                except RuntimeError:pass
                require(c.uncertain is want,'uncertainty classification');c.invoke=lambda *a:(0,None);c.call(2);require(c.uncertain is want,'uncertainty is sticky')
            case('Calls_'+name,check_calls)
        case('approved_actual_factory_manifest',lambda:require(start.approved_build(BUILD,BUILD_SHA)[1]==json.loads(BUILD.read_text())['production_dll']['sha256'],'approved actual production DLL'))
        assets=run/'approval';assets.mkdir();files={}
        for n in ('source.cpp','private.bin','generated.cpp','production.dll'):
            q=assets/n;q.write_bytes(n.encode());files[n]=q
        manifest={'family':'san14.b-warm-factory.v1','result':'PASS','factory_complete_passed':True,'inputs_unchanged':True,'sources':{str(files['source.cpp']):sha(files['source.cpp'])},'private':{str(files['private.bin']):sha(files['private.bin'])},'generated':{str(files['generated.cpp']):sha(files['generated.cpp'])},'binaries':{str(files['production.dll']):sha(files['production.dll'])},'production_dll':{'path':str(files['production.dll']),'sha256':sha(files['production.dll'])}}
        def approve_model(m):q=assets/'result.json';q.write_text(json.dumps(m));return start.approved_build(q,sha(q))
        # These fake files test parsing/closure only, never native readiness.
        case('approval_schema_model',lambda:approve_model(manifest))
        for field,value in [('family','old-family'),('inputs_unchanged',False),('factory_complete_passed',False),('sources',{})]:
            m=copy.deepcopy(manifest);m[field]=value;case('approval_reject_'+field,lambda m=m:refused(lambda:approve_model(m)))
        files['source.cpp'].write_bytes(b'drift');case('approval_source_pin_drift',lambda:refused(lambda:approve_model(manifest)))
        require(all(sha(n)==h for section in ('source_pins','private_pins') for n,h in result[section].items()),'inputs changed while testing');result['inputs_unchanged']=True;result['result']='PASS'
    except Exception as exc:result['error']=repr(exc)
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(run/'result.json'),'cases':len(result['cases'])}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
