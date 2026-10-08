"""Offline native producer audit + counterexample tests for observation pairing.

No process discovery, game attachment, save, network or debugger APIs.
"""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import sys
import a_save_native_coordination_events as events
import a_save_writer_scope_audit as prior

P=Path(__file__).resolve().parent
EXTRA={'producer':(0x8D3D0,0x8D442),'inline_producer':(0x3F7B60,0x3F7E3B),
       'destructive_join':(0x16C160,0x16C19F),'updater_reset':(0x16C060,0x16C154)}


class VM(prior.VM):
    def step(self,m,address,size,unused):
        if address not in self.handlers and address not in self.stops and address!=prior.STOP:
            rva=address-prior.BASE
            if any(a<=rva<z for a,z in EXTRA.values()):self.visits.append(rva);return
        super().step(m,address,size,unused)


def producer_case(raw,locked,inline=False,allocation=True):
    v=VM(raw);b=prior.BASE;m=v.unit_manager;log=[];index=prior.ARENA+0x156000
    v.put(m+0x18,index);v.put(index,3,4);v.put(b+0x201D370,int(locked),4)
    for slot,label in ((0x123C328,'enter'),(0x123C0D8,'leave')):
        p=b+0x2210600+slot%0x100;v.put(b+slot,p)
        def lock(label=label):
            prior.need(v.reg('RCX')==b+0x201D378,'native producer uses list-registry critical section')
            log.append(label);v.ret()
        v.handlers[p]=(label+' registry lock service double',lock)
    def allocate():
        prior.need(v.reg('RCX')==b+0x201D3A0 and v.reg('RDX')==3 and v.reg('R8')&255==1,'native queue append arguments')
        log.append('allocate');v.ret(v.node if allocation else 0)
    v.model(0x172D0,'registry node allocator double',allocate)
    if inline:
        v.model(0xB11E0,'initialized army singleton double',value=m)
        v.model(0x299460,'inline producer eligibility double',value=0)
        input_node=prior.ARENA+0x158000;v.put(input_node,v.unit);v.put(v.unit+0x48,25,2)
        def setup():v.set('RBX',input_node);v.set('R14',0xBD10)
        v.run(0x3F7C10,setup=setup,stop=0x3F7C86)
        prior.need(v.get(v.unit+0x48,2)==0xBD10,'actual Game initializer writes serialized army field before enqueue')
    else:v.run(0x8D3D0,(m,v.unit))
    prior.need(log==(['enter'] if locked else [])+['allocate']+(['leave'] if locked else []),'native producer lock/append/store order')
    prior.need(v.get(v.node)==(v.unit if allocation else 0),'actual producer stores army pointer only for allocated node')
    return v.row('inline-'*inline+'producer-'+str(int(locked))+'-'+str(int(allocation)),lock_order=log,
        native_queue_store_executed=allocation,native_army_field_store_executed=inline,
        real_mutex_executed=False,save_coordination_proved=False)


def destructive_join_case(raw):
    v=VM(raw);b=prior.BASE;m=v.unit_manager;updater=b+0x1A38840;seen=[]
    v.m.mem_write(updater,bytes(0x200))  # Empty owned updater, not archived heap pointers.
    v.put(m+0x90,1,4)
    for a,result in ((0x15FA20,updater),(0x15FAA0,v.effects),(0x15FB70,prior.ARENA+0x15A000)):
        v.model(a,'singleton lookup double',value=result)
    for a in (0x16B750,0x16B690,0x16B840):
        v.model(a,'updater nested container cleanup double',lambda a=a:(seen.append(hex(a)),v.ret())[1])
    v.model(0x834BC0,'OS join service double',lambda:(seen.append('join'),v.ret())[1])
    def clear():seen.append('queue-clear-'+hex(v.reg('RCX')-m));v.ret()
    v.model(0x1FEAC0,'registry list clear double',clear)
    v.run(0x16C160,(m,))
    prior.need(seen==['0x16b750','0x16b690','0x16b840','join','queue-clear-0x10','queue-clear-0x0'],'destructive cleanup must not be misclassified as pure drain')
    prior.need(v.get(m+0x90,4)==0 and 0x16C060 in v.visits,'actual native cleanup/active clear')
    return v.row('destructive-join-is-not-normal-save-drain',ordered_calls=seen,production_entry_usable=False)


def static_case(raw):
    import capstone as cs
    d=cs.Cs(cs.CS_ARCH_X86,cs.CS_MODE_64)
    # Bounded direct layers only. Missing a direct call is not absence of a
    # transitive lock; save UI and pause descendants remain explicitly unknown.
    callback_ranges={'save_initialize':(0x4A29D0,0x4A2A3E),'user_pause':(0x3F5920,0x3F5A2C),
        'user_exit':(0x3F7A70,0x3F7B5D),'save_to_world':(0x2F7B50,0x2F7C70)}
    callbacks={}
    for label,(a,z) in callback_ranges.items():
        calls=[dict(rva=hex(i.address),target=i.op_str) for i in d.disasm(raw[a:z],a) if i.mnemonic=='call']
        prior.need(not any(c['target'] in ('0x16c160','0x834bc0') for c in calls),'new direct drain changes scope')
        callbacks[label]=dict(start=hex(a),end=hex(z),sha256=hashlib.sha256(raw[a:z]).hexdigest(),calls=calls)
    tail=list(d.disasm(raw[0x16C2A8:0x16C2B8],0x16C2A8))
    prior.need([(i.address,i.mnemonic,i.op_str) for i in tail][-3:]==[
        (0x16C2B2,'add','rsp, 0x20'),(0x16C2B6,'pop','rsi'),(0x16C2B7,'ret','')],'army return observation must use balanced RSP')
    return dict(case='native-callback-direct-layer-and-return-stack',result='PASS',callbacks=callbacks,
        return_stack_proof='Entry push rsi/sub rsp20 balanced by add rsp20/pop rsi before sole ret16C2B7.',
        coordination_proved=False,transitive_lock_absence_proved=False)


def pairing_cases():
    base=0x140000000;meta=dict(pid=71,birth=222,base=base,run_id='owned-parser-fixture',capture_complete=True)
    spec={e['event']:e for e in events.EVENTS}
    def row(name,seq,thread=None,**changes):
        army=name.startswith('army');r=dict(seq=seq,event=name,rva=spec[name]['rva'],thread=thread or (72 if army else 71),rsp=0x65001008 if army else 0x66002000)
        if name=='save_scope_enter':r.update(archive=0x50001000,stream=0x50002000,archive_stream=0x50002000)
        elif name=='save_scope_return':r.update(rbx=0x50001000)
        elif name=='army_worker_enter':r.update(manager=base+events.ARMY_MANAGER_RVA,return_pc=base+0x83A9DF)
        else:r.update(return_pc=base+0x83A9DF)
        r.update(changes);return r
    se,sr,ae,ar='save_scope_enter','save_scope_return','army_worker_enter','army_worker_return'
    cases=[]
    def test(name,rows,want,metadata=None,extra=None):
        original=deepcopy(rows);result=events.analyze(rows,metadata or meta)
        prior.need(result['classification']==want,name+' classified as '+result['classification'])
        prior.need(rows==original and result['production_permit'] is False and result['full_writer_exclusion'] is False,name+' must preserve inputs and deny authorization')
        if extra:prior.need(extra(result),name+' additional paired-scope check')
        cases.append(dict(case=name,result='PASS',synthetic=True,classification=result['classification'],issues=result.get('issues',[])))
    clean=[row(se,1),row(sr,2)]
    overlap=[row(se,1),row(ae,2),row(ar,3),row(sr,4)]
    test('empty capture',[],'INCONCLUSIVE')
    test('one save',clean,'NO_WORKER_SCOPE_OVERLAP_OBSERVED')
    test('worker before save',[row(ae,1),row(ar,2),row(se,3),row(sr,4)],'NO_WORKER_SCOPE_OVERLAP_OBSERVED')
    test('worker inside save',overlap,'WORKER_SCOPE_OVERLAP_OBSERVED',extra=lambda r:len(r['overlaps'])==1 and r['overlaps'][0]['different_threads'])
    test('save inside worker',[row(ae,1),row(se,2),row(sr,3),row(ar,4)],'WORKER_SCOPE_OVERLAP_OBSERVED')
    test('worker spanning save entry',[row(ae,1),row(se,2),row(ar,3),row(sr,4)],'WORKER_SCOPE_OVERLAP_OBSERVED')
    test('same thread is not concurrency',[row(se,1),row(ae,2,thread=71),row(ar,3,thread=71),row(sr,4)],'WORKER_SCOPE_OVERLAP_OBSERVED',extra=lambda r:not r['overlaps'][0]['different_threads'])
    test('two separate saves',[row(se,1),row(sr,2),row(se,3),row(ae,4),row(ar,5),row(sr,6)],'WORKER_SCOPE_OVERLAP_OBSERVED',extra=lambda r:len(r['save_scopes'])==2 and len(r['overlaps'])==1)
    broken='INCOMPLETE_OR_INCONSISTENT_CAPTURE'
    for field,val in (('rsp',0x66002008),('rbx',0x50003000),('rva',0x2F7C2E),('run_id','wrong'),('seq',1)):
        rows=deepcopy(clean);rows[-1][field]=val;test('wrong Save '+field,rows,broken)
    for field,val in (('rsp',0x65001010),('return_pc',base+0x83A9E0)):
        rows=deepcopy(overlap);rows[2][field]=val;test('wrong army '+field,rows,broken)
    for field,val in (('manager',base+events.ARMY_MANAGER_RVA+8),('rsp',True),('thread',1.5)):
        rows=deepcopy(overlap);rows[1][field]=val;test('wrong army entry '+field,rows,broken)
    rows=deepcopy(overlap);del rows[1]['manager'];test('missing manager field',rows,broken)
    rows=deepcopy(overlap);rows[1]['snapshot_error']='read failed';test('snapshot failure',rows,broken)
    test('missing army return',[row(se,1),row(ae,2),row(sr,3)],broken)
    test('missing Save return',[row(se,1)],broken)
    test('orphan army return',[row(ar,1),row(se,2),row(sr,3)],broken)
    test('observer incomplete',clean,broken,dict(meta,capture_complete=False))
    test('observer error',clean,broken,dict(meta,capture_errors=['thread lost']))
    test('sequence must begin at one',[row(se,2),row(sr,3)],broken)
    test('zero sequence',[row(se,0),row(sr,1)],broken)
    test('missing whole worker pair leaves sequence gap',[row(se,1),row(sr,4)],broken)
    for lost in (1,-1,True,1.5,'invalid'):
        rows=deepcopy(clean);rows[-1]['lost_events']=lost
        test('declared lost events '+repr(lost),rows,broken)
    rows=deepcopy(clean)
    for item in rows:item['lost_events']=0
    test('explicit zero lost events',rows,'NO_WORKER_SCOPE_OVERLAP_OBSERVED')
    for value in (None,'error',{},7):
        test('invalid capture_errors '+repr(value),clean,'INVALID_CAPTURE',dict(meta,capture_errors=value))
    test('profile mismatch',clean,'INVALID_CAPTURE',dict(meta,profile_id='wrong'))
    test('repeated same-thread save',[row(se,1),row(se,2),row(sr,3)],broken)
    test('unknown event',[dict(row(se,1),event='invented'),row(sr,2)],broken)
    return cases


def main():
    private=Path(os.environ['SAN14_PRIVATE_FIXTURE_ROOT']).resolve();sys.path.insert(0,str(private/'python_deps'))
    run=P/'a_save_native_coordination_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    sources={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in (Path(__file__).name,'a_save_native_coordination_events.py','a_save_writer_scope_audit.py')}
    result=dict(schema='san14.a-save-native-coordination.test.v1',result='FAIL',cases=[],sources=sources,game_access=False,production_permit=False)
    try:
        raw=(private/'game-runtime-image.bin').read_bytes();profile=events.validate_archive(raw)
        (run/'observation_profile.json').write_text(json.dumps(profile,indent=2)+'\n',encoding='utf-8')
        result['cases']+=pairing_cases()
        for locked in (False,True):
            for allocation in (False,True):result['cases'].append(producer_case(raw,locked,allocation=allocation))
        result['cases'].append(producer_case(raw,True,inline=True))
        result['cases'].append(destructive_join_case(raw))
        result['cases'].append(static_case(raw))
        result['native_ranges']={n:dict(start=hex(a),end=hex(z),sha256=hashlib.sha256(raw[a:z]).hexdigest()) for n,(a,z) in EXTRA.items()}
        prior.need(all(hashlib.sha256((P/n).read_bytes()).hexdigest()==h for n,h in sources.items()),'source drift')
        prior.need(hashlib.sha256((private/'game-runtime-image.bin').read_bytes()).hexdigest()==events.ARCHIVE_SHA256,'private archive drift')
        result.update(result='PASS',sources_unchanged=True,archive_unchanged=True,profile_id=events.PROFILE_ID)
    except Exception as exc:result['error']=repr(exc);raise
    finally:
        (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(result=result['result'],cases=len(result['cases']),path=str(run/'result.json'))))


if __name__=='__main__':main()
