"""Exact business call/return pairing; raw return is not success or full effect proof.
No native invocation, suppression, result application, network send or Ready permission.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

POINTS={'common_return':0x62627A,'wrapper_call':0x67A993,'common_call':0x626275,'wrapper_return':0x67A998}
FIELDS={'seq','event','rva','thread','rsp','state','root','world','viewer','date','ui_event_code_raw',
        'eax','preview','counter','pid','birth','base','run_id','lost_events'}


def analyze(rows,metadata):
    result=dict(schema='san14.reward-result-source-analysis.v1',classification='INCOMPLETE_CAPTURE',
                reasons=[],pairs=[],native_suppression=False,native_execution_verified=False,native_return_success_verified=False,
                full_reward_effects_verified=False,room_ready_permission=False,
                menu_lifetime_verified=False,cancellation_mapping_verified=False,
                production_permit=False,network_submission_allowed=False)
    def need(ok,why):
        if not ok:raise ValueError(why)
    def integer(v,low=0,high=2**64-1):return type(v) is int and low<=v<=high
    try:
        need(type(rows) is list and len(rows)<=256,'invalid bounded event rows')
        need(type(metadata) is dict,'missing metadata')
        need(metadata.get('capture_complete') is True,'capture not clean and complete')
        need(type(metadata.get('capture_errors')) is list and not metadata['capture_errors'],'capture errors or invalid error collection')
        for key in ('pid','birth','base'):need(integer(metadata.get(key),1),'invalid process binding')
        need(type(metadata.get('run_id')) is str and 1<=len(metadata['run_id'])<=63,'missing run identity')
        spans={};last_counter=0;world=None
        for seq,row in enumerate(rows,1):
            need(type(row) is dict and set(row)==FIELDS,'unknown/missing event fields')
            need(type(row['seq']) is int and row['seq']==seq and type(row['lost_events']) is int and row['lost_events']==0,'event loss or sequence gap')
            need(row['event'] in POINTS and type(row['rva']) is int and row['rva']==POINTS[row['event']],'unknown source point')
            need(all(row[k]==metadata[k] and type(row[k]) is type(metadata[k]) for k in ('pid','birth','base','run_id')),'mixed process/run binding')
            for key in ('thread','rsp','state','root','world','counter'):need(integer(row[key],1),'invalid native event identity')
            need(row['counter']>=last_counter,'non-monotonic sampling clock');last_counter=row['counter']
            need(integer(row['viewer'],1,51) and integer(row['ui_event_code_raw'],0,2**32-1) and integer(row['eax'],0,2**32-1),'invalid viewer/event/result')
            date=row['date'];need(type(date) is list and len(date)==3 and integer(date[0],1,9999) and integer(date[1],1,12) and integer(date[2],1,30),'invalid date')
            current=(row['root'],row['world'],row['viewer'],tuple(date))
            if world is None:world=current
            need(world==current,'world/viewer/date changed during capture')
            p=row['preview'];need(type(p) is dict and set(p)=={'kind','force_id','district_id','funding_city_id','officer_ids'},'invalid preview fields')
            need(p['kind']=='reward' and all(integer(p[k],1,51) for k in ('force_id','district_id','funding_city_id')) and p['force_id']==row['viewer'],'preview/viewer differs')
            ids=p['officer_ids'];need(type(ids) is list and len(ids)<=64 and all(integer(i,1,5999) for i in ids) and len(set(ids))==len(ids),'invalid officer list')
            key=(row['thread'],row['state']);event=row['event']
            if event=='wrapper_call':
                need(row['thread'] not in spans,'nested wrapper')
                need(row['ui_event_code_raw']==2,'entry not confirmation event')
                spans[row['thread']]=dict(before=deepcopy(row),common=None,returned=None)
            elif event=='common_call':
                span=spans.get(row['thread']);need(span is not None and span['common'] is None,'orphan/duplicate common')
                need(span['before']['state']==row['state'] and span['before']['rsp']==row['rsp']+0x890,'common frame/state mismatch')
                need(span['before']['preview']==p,'native ID args differ from UI draft');span['common']=deepcopy(row)
            elif event=='common_return':
                span=spans.get(row['thread']);need(span is not None and span['common'] is not None and span['returned'] is None,'orphan/duplicate business return')
                need(span['common']['state']==row['state'] and span['common']['rsp']==row['rsp'],'business return frame mismatch')
                need(span['common']['preview']==p,'business return draft changed')
                span['returned']=deepcopy(row)
            elif event=='wrapper_return':
                span=spans.pop(row['thread'],None);need(span is not None,'orphan wrapper return')
                need(span['before']['state']==row['state'] and span['before']['rsp']==row['rsp'],'wrapper return frame mismatch')
                need(span['before']['preview']==p,'draft changed before wrapper returned')
                need((span['common'] is None)==(span['returned'] is None),'missing business return')
                result['pairs'].append(dict(call_seq=span['before']['seq'],return_seq=seq,
                    common_seq=span['common']['seq'] if span['common'] else None,
                    preview=deepcopy(span['before']['preview']),viewer=row['viewer'],date=deepcopy(date),
                    common_return_seq=span['returned']['seq'] if span['returned'] else None,
                    native_return_raw=span['returned']['eax'] if span['returned'] else None,
                    native_return_success_verified=False,thread=row['thread'],state=row['state'],
                    root=row['root'],world=row['world'],common_rsp=span['common']['rsp'] if span['common'] else None,
                    wrapper_result_raw=row['eax'],already_may_have_executed=True))
        need(not spans,'unreturned wrapper scope')
        result['classification']='NATIVE_BUSINESS_RETURN_PAIRED' if any(p['common_seq'] for p in result['pairs']) else 'INCONCLUSIVE'
        result['source_binding']={k:metadata[k] for k in ('pid','birth','base','run_id')}
    except (KeyError,TypeError,ValueError) as error:
        result['classification']='INCOMPLETE_CAPTURE';result['reasons'].append(str(error));result['pairs']=[]
    return result

