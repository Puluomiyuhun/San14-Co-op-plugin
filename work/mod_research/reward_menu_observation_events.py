"""Analyze read-only menu evidence and compose a NON-SENDABLE capture shadow.

This is an observation source contract, not a native interception owner. A
matched wrapper may already have executed locally; replaying it would duplicate
effects. Menu constructor/destructor/cancel and full input lifetime remain unknown.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'outputs'/'san14-link'))
from reward_menu_capture import CaptureSession, CaptureError

POINTS={'menu_update':0x67A930,'wrapper_call':0x67A993,'common_call':0x626275,'wrapper_return':0x67A998}
FIELDS={'seq','event','rva','thread','rsp','state','root','world','viewer','date','ui_event_code_raw',
        'eax','preview','counter','pid','birth','base','run_id','lost_events'}


def analyze(rows,metadata):
    result=dict(schema='san14.reward-menu-source-analysis.v1',classification='INCOMPLETE_CAPTURE',
                reasons=[],pairs=[],updates=[],native_suppression=False,native_execution_verified=False,
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
        latest={};spans={};last_counter=0;world=None
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
            if event=='menu_update':
                latest[key]=deepcopy(row)
                result['updates'].append(dict(seq=seq,raw_event=row['ui_event_code_raw'],preview=deepcopy(p),
                    meaning='observed_update_or_draft_change; not constructor/cancel'))
            elif event=='wrapper_call':
                need(key in latest and row['thread'] not in spans,'entry lacks Update or is nested')
                need(row['ui_event_code_raw']==2 and latest[key]['preview']==p,'entry draft differs from latest observed Update')
                spans[row['thread']]=dict(before=deepcopy(row),common=None)
            elif event=='common_call':
                span=spans.get(row['thread']);need(span is not None and span['common'] is None,'orphan/duplicate common')
                need(span['before']['state']==row['state'] and span['before']['rsp']==row['rsp']+0x890,'common frame/state mismatch')
                need(span['before']['preview']==p,'native ID args differ from UI draft');span['common']=deepcopy(row)
            elif event=='wrapper_return':
                span=spans.pop(row['thread'],None);need(span is not None,'orphan wrapper return')
                need(span['before']['state']==row['state'] and span['before']['rsp']==row['rsp'],'wrapper return frame mismatch')
                need(span['before']['preview']==p,'draft changed before wrapper returned')
                result['pairs'].append(dict(call_seq=span['before']['seq'],return_seq=seq,
                    common_seq=span['common']['seq'] if span['common'] else None,
                    preview=deepcopy(span['before']['preview']),viewer=row['viewer'],date=deepcopy(date),
                    wrapper_result=row['eax'],already_may_have_executed=True))
        need(not spans,'unreturned wrapper scope')
        result['classification']='MENU_CALL_SOURCE_MATCHED' if any(p['common_seq'] for p in result['pairs']) else 'INCONCLUSIVE'
        result['source_binding']={k:metadata[k] for k in ('pid','birth','base','run_id')}
    except (KeyError,TypeError,ValueError) as error:
        result['classification']='INCOMPLETE_CAPTURE';result['reasons'].append(str(error));result['pairs']=[]
    return result


def capture_shadow(analysis,trusted_context,*,now_tick):
    """Exercise existing CaptureSession from observed IDs, but return no packet.

    trusted_context is supplied independently by the caller. This does not turn
    observed state addresses into native lifetime/attachment evidence. Production
    must instead intercept before native effects and own that lifetime.
    """
    if analysis.get('classification')!='MENU_CALL_SOURCE_MATCHED' or not analysis.get('pairs'):
        raise ValueError('No matched source observation')
    pair=analysis['pairs'][0]
    if pair['viewer']!=trusted_context.get('viewer_force_id'):
        raise ValueError('Observation does not belong to trusted viewer')
    session=CaptureSession()
    capture_id=hashlib.sha256(json.dumps(analysis['source_binding'],sort_keys=True).encode()).hexdigest()[:32]
    session.capture(pair['preview'],trusted_context,capture_id=capture_id,now_tick=now_tick)
    pending=session.confirm(capture_id,pair['preview'],trusted_context,now_tick=now_tick)
    again=session.confirm(capture_id,pair['preview'],trusted_context,now_tick=now_tick)
    return dict(schema='san14.reward-menu-observation-shadow.v1',source_call_seq=pair['call_seq'],
        semantic_preview_sha256=pending.preview_sha256,officer_ids=list(pending.officer_ids),
        district_id=pending.district_id,duplicate_confirmation_same_object=pending is again,
        network_packet=None,network_submission_allowed=False,native_interception=False,
        native_suppression=False,native_execution=False,trusted_context_producer_implemented=False,
        reason='Read-only source may already have executed; never replay this observation')
