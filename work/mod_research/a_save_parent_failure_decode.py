"""Decode cached Controller read/clean evidence from an existing RPM archive.

No process constructor, native call or live read occurs here. A cached hook
publication observation cannot replace the later immediate *slot==hook read.
"""
from datetime import datetime
import argparse
import json
from pathlib import Path
import a_save_parent_failure_read as base

DETAIL = base.PRIVATE/'a_save_parent_failure_detail_runs/20261009-222855-390752/layout.json'
DETAIL_SHA = '33713769e2a294b9f5d4879584455d2c86fd06e040f51b011d0c483bc0d36ea3'


def decode(raw, schema, detail):
    result=base.decode_runtime(raw,schema)
    controller=schema['Runtime']['controller_']['offset']+schema['Controller']['r_']['offset']
    for role,name,count in (('owner','OwnerReport',2),('gate','GateReport',3)):
        start=controller+schema['ControllerReport'][role]['offset']
        report=raw[start:start+schema[name]['_size']]
        offset=detail[name]['hooks']['offset'];hooks=report[offset:offset+detail['Hooks']['_size']]
        values=base.scalar_fields(hooks,detail['Hooks']);entries=[]
        for i in range(2):
            start=detail['Hooks']['entries']['offset']+i*detail['Entry']['_size']
            entry=hooks[start:start+detail['Entry']['_size']]
            row=base.scalar_fields(entry,detail['Entry']);row['binding']=base.scalar_fields(entry,detail['Binding']);entries.append(row)
        values['entries']=entries;result[role+'_hooks_cached']=values
        bridges=[]
        for i in range(count):
            start=detail[name]['bridges']['offset']+i*detail['Stats']['_size']
            bridges.append(base.scalar_fields(report[start:start+detail['Stats']['_size']],detail['Stats']))
        result[role+'_bridges_cached']=bridges
    r=result['reward_cached'];u=result['owner_cached'];g=result['gate_cached']
    predicates={
        'reward.bound':bool(r['bound']),'reward.error==None':r['error']==0,'!reward.uncertain':not r['uncertain'],
        '!reward.active':not r['active'],'!reward.queued':not r['queued'],
        'owner.armed':bool(u['armed']),'!owner.stopped':not u['stopped'],'owner.error==None':u['error']==0,
        '!owner.save_lane':not u['save_lane'],'!owner.user_hold_requested':not u['user_hold_requested'],
        '!owner.active_scopes':not u['active_scopes'],'gate.armed':bool(g['armed']),'!gate.stopped':not g['stopped'],
        'gate.error==None':g['error']==0,'!gate.active':not g['active']}
    hook_shapes={}
    for role in ('owner','gate'):
        for i,b in enumerate(result[role+'_bridges_cached']):predicates[f'!{role}.bridges[{i}].active']=not b['active']
        h=result[role+'_hooks_cached']
        hook_shapes[role]=bool(h['initialized'] and h['count']==2 and h['exceptionCode']==0 and all(
            e['known'] and e['published'] and not e['error'] and e['binding']['slot'] and e['binding']['hook'] for e in h['entries']))
    result['clean_predicates']=predicates
    result['clean_on_retained_report']=all(predicates.values())
    result['read_hook_cached_shape_valid']=hook_shapes
    result['read_immediate_pointer_check']='NOT_OBSERVED: cached Entry.observed is from publication, not the later Controller.read dereference'
    result['conclusion']='Controller.Initialize failed; clean is true on its retained complete report. Remaining alternatives are read tail immediate pointer check/exception, or ClaimController. Exact Claim/fresh rejection is not recorded.'
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive',type=Path)
    args=parser.parse_args()
    if args.archive is None:parser.print_help();return 0
    run=base.PRIVATE/'a_save_parent_failure_decode_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result=dict(result='FAIL',live_reads=0,native_calls=0)
    try:
        evidence=base.read_json(args.archive)
        base.require(evidence['result']=='PASS_READ_ONLY_PARENT_FAILURE_OBSERVATION' and evidence['dll_sha256']==base.DLL_SHA and
            evidence['layout_sha256']==base.LAYOUT_SHA,'Unexpected RPM evidence identity')
        base.require(base.digest(DETAIL)==DETAIL_SHA,'Exact compiled detail layout required')
        base.require(evidence['source_sha256']==base.digest(Path(base.__file__)) and evidence['native_calls']==0 and evidence['writes']==0,
                     'Original read-only observation/source differs')
        schema=base.layout();detail=base.read_json(DETAIL);raw=bytes.fromhex(evidence['raw_runtime'])
        decoded=decode(raw,schema,detail)
        base.require(decoded['controller']['error']==1 and not decoded['controller']['initialized'],'Different parent failure')
        # Two direct negative checks prove the decoder does not ignore the fields.
        bad=bytearray(raw);position=12456+136+schema['ControllerReport']['gate']['offset']+detail['GateReport']['bridges']['offset']+detail['Stats']['active']['offset'];bad[position]=1
        base.require(not decode(bad,schema,detail)['clean_on_retained_report'],'Active bridge escaped clean decoder')
        bad=bytearray(raw);position=12456+136+schema['ControllerReport']['owner']['offset']+detail['OwnerReport']['hooks']['offset']+detail['Hooks']['entries']['offset']+detail['Entry']['published']['offset'];bad[position]=0
        base.require(not decode(bad,schema,detail)['read_hook_cached_shape_valid']['owner'],'Missing publication escaped decoder')
        pins={str(p.resolve()):base.digest(p) for p in (args.archive,DETAIL,base.LAYOUT,Path(__file__),Path(base.__file__),base.P/'a_save_parent_failure_layout.cpp',base.P/'a_save_parent_failure_detail.cpp',base.P/'planning_period_interlock.cpp',base.P/'planning_checkpoint_save_lifecycle.inc')}
        for p in DETAIL.parent.iterdir():
            if p.is_file():pins[str(p.resolve())]=base.digest(p)
        result.update(result='PASS_OFFLINE_CACHED_INITIALIZATION_AUDIT',decoded=decoded,pins=pins,
                      negative_checks=['bridge_active_rejected','missing_publication_rejected'],restore_permission=False,retry_permission=False)
    except Exception as error:result['error']=repr(error)
    path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=result['result'],path=str(path),sha256=base.digest(path))))
    return 0 if result['result'].startswith('PASS_') else 1


if __name__=='__main__':raise SystemExit(main())
