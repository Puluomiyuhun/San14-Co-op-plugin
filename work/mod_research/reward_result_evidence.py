"""Correlate passive native returns with bounded read-only before/after samples.

Caller retains the process reader and debugger capture lifetime. No process is
opened here. A paired return plus a projected change is not complete business
success, writer exclusion, or permission to apply a result to another game.
"""
from copy import deepcopy
import ctypes

import reward_result_watch as watch
import reward_counter_policy as counters
import reward_result_observation_events as events

SCHEMA='san14.reward-result-timed-sample.v1'
FLAGS=dict(network_submission_allowed=False,replica_applied=False,
           full_reward_effects_verified=False,native_return_success_verified=False,
           exclusive_business_attribution=False,production_permit=False,
           room_ready_permission=False)

def need(ok,why):
    if not ok:raise ValueError(why)

def clock():
    """Same Windows QPC domain used by the native observer, not wall time."""
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    frequency=ctypes.c_longlong();counter=ctypes.c_longlong()
    if not api.QueryPerformanceFrequency(ctypes.byref(frequency)) or not api.QueryPerformanceCounter(ctypes.byref(counter)):
        raise ctypes.WinError(ctypes.get_last_error())
    return dict(counter=counter.value,frequency=frequency.value)

def _clock(value):
    need(type(value) is dict and set(value)=={'counter','frequency'} and
         all(type(v) is int and 0<v<2**63 for v in value.values()),'Exact positive Windows QPC sample required')
    return value

def capture(reader,forces,*,actor,read_birth=None,read_clock=None):
    read_clock=read_clock or clock
    begin=_clock(read_clock())
    sample=watch.capture(reader,forces,actor=actor,read_birth=read_birth)
    extra=counters.capture(reader.memory.read,world=sample['identity']['world'])
    # Correct signed-byte auxiliary observation belongs to this sample only;
    # predecessor's i32 raw bytes are retained but never used as a native gate.
    repeated=watch.capture(reader,forces,actor=actor,read_birth=read_birth)
    need(all(sample[k]==repeated[k] for k in sample if k!='captured_at'), 'Shared snapshot changed around counter reads')
    need(extra==counters.capture(reader.memory.read,world=sample['identity']['world']), 'Counter snapshot changed')
    end=_clock(read_clock())
    need(begin['frequency']==end['frequency'] and begin['counter']<=end['counter'],'Sampling clock changed')
    return dict(schema=SCHEMA,sample=sample,counters=extra,begin=begin,end=end,game_writes=0,native_calls=0)

def validate(value):
    need(type(value) is dict and set(value)=={'schema','sample','counters','begin','end','game_writes','native_calls'} and
         value['schema']==SCHEMA and type(value['game_writes']) is int and value['game_writes']==0 and
         type(value['native_calls']) is int and value['native_calls']==0,'Timed read-only sample required')
    watch.validate_sample(value['sample']);_clock(value['begin']);_clock(value['end'])
    need(value['begin']['frequency']==value['end']['frequency'] and value['begin']['counter']<=value['end']['counter'],'Invalid sample interval')
    counters.shared_delta_exclusion(value['counters'],value['counters'])
    need(value['counters']['world']==value['sample']['identity']['world'],'Counter world differs')
    return value

def correlate(before,after,rows,metadata):
    validate(before);validate(after)
    analysis=events.analyze(rows,metadata)
    need(analysis['classification']=='NATIVE_BUSINESS_RETURN_PAIRED' and len(analysis['pairs'])==1,
         'Exactly one clean native business return required')
    pair=analysis['pairs'][0];need(pair['common_return_seq'] is not None,'No business return')
    b,a=before['sample'],after['sample'];identity=b['identity']
    need(all(identity[k]==metadata[k] for k in ('pid','birth','base')),'Trace process differs from samples')
    need(all(identity[k]==pair[k] for k in ('root','world')) and pair['viewer']==b['actor'],
         'Trace world/viewer differs from samples')
    date=identity['date']
    need(pair['date']==[date['year'],date['month'],date['day']],'Trace date differs from samples')
    need(before['end']['frequency']==after['begin']['frequency'] and
         before['end']['counter']<rows[0]['counter']<=rows[-1]['counter']<after['begin']['counter'],
         'Snapshots do not enclose the complete native trace')
    result=watch.compare_samples(b,a);delta=result['delta'];preview=pair['preview']
    need(preview['force_id']==delta['actor']['force_id'] and preview['district_id']==delta['actor']['district_id'] and
         preview['officer_ids']==delta['command']['officer_ids'], 'Observed native command differs from projected result')
    changed_cities={c['id'] for c in delta['changes'] if c['fieldtable']=='cities'}
    need(changed_cities=={preview['funding_city_id']},'Native funding city differs from projected result')
    aux={k:dict(before=v,after=after['counters']['fields'][k]) for k,v in before['counters']['fields'].items()
         if v!=after['counters']['fields'][k]}
    return dict(schema='san14.reward-result-correlated-evidence.v1',result='RETURN_AND_PROJECTED_CHANGE_CORRELATED',
        source_binding=deepcopy(analysis['source_binding']),native_return_raw=pair['native_return_raw'],
        wrapper_result_raw=pair['wrapper_result_raw'],business_return_paired=True,samples_enclose_trace=True,
        delta=delta,auxiliary_changes=aux,auxiliary_semantics_verified=False,
        evidence_sha256=watch.journal.digest(dict(before=before,after=after,rows=rows,metadata=metadata)),**FLAGS)
