"""Reconstruct a stage-specific partial baseline from an observed full comparison.

Every compared byte was either equal to the reference or logged explicitly.
The pre-existing army+148 display-pointer exclusion remains; no new exclusion
is added. Unknown field semantics do not imply that the fields may be ignored.
"""
from copy import deepcopy
import json
from pathlib import Path
from start_startup_switch import ROOT,load,save,sha,JOURNAL,CHECKPOINT_SHA
TABLES={0x148:'person',0xDAA8:'city',0xDE40:'district',0xDCA0:'force',0x7DF60:'army'}
REFERENCE=ROOT/'startup-identity-traces/20261006-110512-181614/after.json'

def reconstruct(reference,comparison,planning):
    records=deepcopy(reference['records'])
    if comparison['stage']!='title_selection_boundary' or comparison['checked_records']!=len(records) or comparison['unreadable_records']!=0:
        raise ValueError('Incomplete or wrong-stage comparison')
    items=comparison['differences']
    if len(items)!=comparison['different_records']:
        raise ValueError('Wrong changed-record count')
    seen=set();changes=0
    for row in items:
        if row.get('read_error') or row['table_rva'] not in TABLES:
            raise ValueError('Invalid object table/read failure')
        kind=TABLES[row['table_rva']];key=f"{kind}:{row['id']}"
        if key not in records or key in seen:raise ValueError('Unknown/duplicate object')
        seen.add(key);body=bytearray.fromhex(records[key]);map_body=bytes.fromhex(planning['records'][key]);offsets=set()
        for delta in row['changes']:
            at=delta['object_offset']-0x10
            if at<0 or at>=len(body) or at in offsets:raise ValueError('Bad/duplicate byte offset')
            if kind=='army' and 0x138<=at<0x140:raise ValueError('Excluded pointer was not observed by the comparison')
            if body[at]!=delta['expected'] or map_body[at]!=delta['expected']:raise ValueError('Reference mismatch or field did not return on map')
            if type(delta['actual']) is not int or not 0<=delta['actual']<=255 or delta['actual']==delta['expected']:
                raise ValueError('Invalid byte difference')
            body[at]=delta['actual'];offsets.add(at);changes+=1
        records[key]=body.hex()
    if changes!=comparison['different_bytes']:raise ValueError('Wrong changed-byte count')
    # Do not represent copied process-specific display pointers as observed data.
    for key,value in records.items():
        if key.startswith('army:'):
            body=bytearray.fromhex(value);body[0x138:0x140]=bytes(8);records[key]=body.hex()
    return records

def main():
    report=load(ROOT/'startup-checkpoint-diagnostic-latest.json');folder=Path(report['directory'])
    meta=load(folder/'metadata.json');assert meta['execute'] is False and meta['checkpoint34_sha256']==CHECKPOINT_SHA
    assert sha(folder/'artifacts/startup_identity_switch.exe')==meta['binary_sha256']
    assert not JOURNAL.exists() and report['game_data_writes_by_adapter']==0 and not report['debugger_attached']
    trace=[json.loads(line) for line in (folder/'trace.jsonl').read_text().splitlines()]
    assert [r['event'] for r in trace]==['attached','armed','deserialize_return','load_worker_result','title_selection_boundary',
                                      'checkpoint_sample_comparison','error','error_cleanup']
    assert trace[3]['ebx']==1 and trace[4]['rva']==0x4DA3B2 and trace[4]['handoff_written'] is False
    assert trace[4]['states']==['CRootState','CMotorGameState','CTitleState'] and trace[4]['date']==[203,8,11]
    assert trace[4]['world_context']['force']==12 and trace[4]['world_context']['mode']==1
    assert trace[-1]=={'event':'error_cleanup','registers_restored':True,'detached':True}
    reference=load(REFERENCE);planning=load(folder/'after-diagnostic.json');comparison=report['boundary_comparison']
    restored=report['planning_sample_comparison']
    assert not restored['other_record_changes'] and restored['active_army_semantics_equal'] and restored['task_fields_equal']
    records=reconstruct(reference,comparison,planning)
    output={'schema':'san14.load-boundary-checkpoint.v1','stage':'title_selection_boundary','rva':0x4DA3B2,
            'checkpoint34_sha256':CHECKPOINT_SHA,'date':[203,8,11],'force':12,'records':records,
            'reconstructed_compared_bytes':True,'known_excluded_field':'army+0x148..0x150',
            'new_excluded_fields':[],'source_diagnostic_directory':str(folder),
            'source_artifacts_sha256':{str(p.relative_to(ROOT)):sha(p) for p in
                (REFERENCE,folder/'trace.jsonl',folder/'after-diagnostic.json',folder/'metadata.json',folder/'artifacts/startup_identity_switch.exe')},
            'stage_difference_records':comparison['different_records'],'stage_difference_bytes':comparison['different_bytes'],
            'scope':'783 partial records reconstructed from an actual read-only stage comparison. Same checkpoint/same stage fingerprint, not complete world equality, field-semantics proof or a cross-client save format.'}
    save(ROOT/'startup-load-boundary-baseline.json',output)
    print(json.dumps({'result':'STAGE_BASELINE_RECONSTRUCTED','records':len(records),'changed_from_planning':comparison['different_records'],
                      'bytes_changed':comparison['different_bytes'],'new_excluded_fields':[]}))

if __name__=='__main__':main()
