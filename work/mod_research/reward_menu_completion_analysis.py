"""Read-only correlation, never a close/return-1/queue-pop authorization API.

The native queue is untagged. Even matching before/after samples cannot hold its
menu lifetime. The concrete missing producer/consumer lease is always reported.
"""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'outputs'/'san14-link'))
import execution_journal as journal
from reward_menu_capture import CaptureSession


def need(ok,why):
    if not ok:raise ValueError(why)


def integer(value,low=0,high=2**64-1):
    return type(value) is int and low<=value<=high


@dataclass(frozen=True)
class AuthorityEvidence:
    """Detached immutable evidence read from a trusted local journal snapshot.

    This is not authenticated IPC. Callers must supply the already-owned local
    path/scope/attachment and a fresh trusted adapter report, never client JSON.
    Even fabricated instances cannot grant a native close permission here.
    """
    canonical: str

    def value(self):
        return json.loads(self.canonical)


def read_authority_result(path,scope,attachment,player,request_id,preview,fresh_report):
    """Open existing SQLite mode=ro, match its exact applied current tip.

    No process, network or game observation occurs. The fresh report must come
    from the trusted local replica; this reader does not manufacture one.
    """
    scope=deepcopy(scope);preview=deepcopy(preview);fresh_report=deepcopy(fresh_report)
    journal.validate_scope(scope)
    need(player in ('A','B') and type(player) is str,'invalid local player')
    need(journal.hex_id(request_id,32) and journal.hex_id(attachment,32),'invalid request/attachment')
    need(type(preview) is dict and set(preview)=={'kind','force_id','district_id','funding_city_id','officer_ids'},'preview fields')
    need(preview['kind']=='reward' and all(integer(preview[k],1,51) for k in ('force_id','district_id','funding_city_id')),'preview IDs')
    ids=preview['officer_ids'];need(type(ids) is list and 1<=len(ids)<=16 and all(integer(v,1,5999) for v in ids) and len(set(ids))==len(ids),'officer IDs')
    need(scope['bindings'][player]=={'force_id':preview['force_id'],'main_district_id':preview['district_id']},'foreign preview')
    report_keys={'schema','scope_sha256','local_player','attachment_id','sequence','state_sha256','prefix_sha256','state_contract'}
    need(type(fresh_report) is dict and set(fresh_report)==report_keys,'fresh report fields')
    need(fresh_report['schema']=='san14.applied-prefix.v1' and fresh_report['scope_sha256']==journal.digest(scope)
        and fresh_report['local_player']==player and fresh_report['attachment_id']==attachment
        and fresh_report['state_contract']==scope['state_contract'],'fresh report identity')
    need(integer(fresh_report['sequence'],1,2**31-1) and all(journal.hex_id(fresh_report[k]) for k in ('state_sha256','prefix_sha256')),'fresh report values')
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=5,isolation_level=None)
    db.row_factory=sqlite3.Row
    try:
        db.execute('BEGIN')
        need(db.execute('PRAGMA user_version').fetchone()[0]==1,'journal version')
        need(db.execute('PRAGMA quick_check').fetchone()[0]=='ok','journal integrity')
        meta=db.execute('SELECT identity,halt FROM metadata WHERE id=1').fetchone()
        need(meta is not None and meta['halt'] is None,'journal missing or held')
        identity=json.loads(meta['identity'])
        need(identity=={'scope':scope,'local_player':player,'attachment_id':attachment},'journal identity differs')
        need(db.execute("SELECT COUNT(*) FROM entries WHERE status!='APPLIED'").fetchone()[0]==0,'unresolved journal entry')
        row=db.execute('SELECT * FROM entries WHERE player=? AND request_id=?',(player,request_id)).fetchone()
        need(row is not None and row['status']=='APPLIED','requested command not applied')
        need(row['sequence']==db.execute('SELECT MAX(sequence) FROM entries').fetchone()[0]==fresh_report['sequence'],'receipt is not current tip')
        intent=json.loads(row['intent']);receipt=json.loads(row['receipt']);journal.validate_intent(scope,intent)
        need(journal.digest(intent)==row['fingerprint']==receipt['intent_sha256'],'intent digest differs')
        need(type(receipt['sequence']) is int and intent['sequence']==receipt['sequence']==row['sequence'] and intent['request_id']==receipt['request_id']==request_id
            and intent['player_id']==receipt['player_id']==player and receipt['status']=='APPLIED_LOCAL','receipt identity differs')
        command=intent['command']
        fields=('force_id','district_id','funding_city_id','officer_ids')
        need(journal.canonical({k:command[k] for k in fields})==journal.canonical({k:preview[k] for k in fields}),'authority command differs from captured proposal')
        date=command['date'];need(type(date) is dict and all(type(date.get(k)) is int for k in ('year','month','day')),'authority date invalid')
        need(receipt['post_state_sha256']==fresh_report['state_sha256'] and receipt['prefix_sha256']==fresh_report['prefix_sha256'],'fresh report no longer matches receipt')
        native=receipt['native_result']
        need(type(native) is dict and all(native.get(k) is True for k in ('native_returned','args_released','owned_slot_cleared')),'local execution cleanup unresolved')
        evidence=dict(scope_sha256=journal.digest(scope),room_id=scope['room_id'],binding_epoch=scope['binding_epoch'],
            epoch=scope['timeline_epoch'],attachment_id=attachment,player_id=player,request_id=request_id,
            sequence=row['sequence'],intent_sha256=row['fingerprint'],state_sha256=fresh_report['state_sha256'],
            prefix_sha256=fresh_report['prefix_sha256'],preview=preview,date=[date[k] for k in ('year','month','day')],
            evidence_origin='existing local APPLIED journal plus separately supplied fresh local adapter report')
        return AuthorityEvidence(journal.canonical(evidence))
    finally:
        db.close()


CALLERS={
    'manager_getter_double':{0x67A9A1},'layout_before_double':{0x667B36},
    'layout_context_double':{0x667B46},'layout_destroy_double':{0x667B5C},
    'selection_destroy_double':{0x60B032},'other_pause_double':{0x50B1A8},
    'other_finalize_double':{0x50B1B8},'parent_resume_double':{0x50B21F},
    'other_destructor_double':{0x50B25E},'allocator_free_double':{0x50A982,0x50B26A}}


def analyze(trace,authority,context,source,*,now_tick):
    """Diagnostic owned traces only; refuses missing identities and stale scopes.

    context is the existing CaptureSession trusted context, and source is the
    separately retained native process/menu binding. They currently have only
    fixture producers. No successful output is permission to invoke the tail.
    """
    result=dict(schema='san14.reward-menu-completion-analysis.v1',classification='INCOMPLETE_EVIDENCE',reasons=[],
        can_queue_close=False,production_permit=False,menu_lifetime_verified=False,
        required_missing_source='exclusive lifetime from matching menu enqueue through native request consumption',
        authority_drove_native_close=False)
    try:
        need(type(authority) is AuthorityEvidence,'no trusted local authority evidence')
        a=authority.value();context=deepcopy(context);source=deepcopy(source)
        need(type(trace) is dict and trace.get('schema')=='san14.reward-menu-completion-owned-trace.v1','unsupported native trace')
        need(trace.get('passed') is True and trace.get('success_branch_selected_by_fixture') is True
            and trace.get('authority_did_not_drive_native_close') is True and trace.get('full_dispatcher_executed') is False
            and trace.get('menu_lifetime_lock') is False and trace.get('production_permit') is False,'trace evidence boundary changed')
        keys={'pid','birth','base','thread','menu','user','root','world'}
        need(type(source) is dict and set(source)==keys and all(integer(source[k],1) and type(trace.get(k)) is int and trace[k]==source[k] for k in keys),'native attachment/menu source differs')
        for k in ('room_id','binding_epoch','epoch','attachment_id','player_id'):
            need(context.get(k)==a[k],'stale room/epoch/attachment')
        session=CaptureSession();session.capture(a['preview'],context,capture_id=a['request_id'],now_tick=now_tick)
        need(context['phase']=='PLANNING','not planning')
        need(type(trace.get('viewer')) is int and trace['viewer']==context['viewer_force_id'],'native viewer changed')
        need(type(trace.get('date')) is list and len(trace['date'])==3 and all(type(v) is int for v in trace['date']) and trace['date']==a['date'],'native date differs from applied command')
        events=trace['events'];need(type(events) is list and len(events)<=128,'event bound')
        fieldset={'seq','event','caller_rva','thread','object','top','count','queue','layout_nonzero'}
        frees=[]
        for index,row in enumerate(events,1):
            need(type(row) is dict and set(row)==fieldset and type(row['seq']) is int and row['seq']==index,'event fields/loss')
            need(row['event'] in CALLERS and type(row['caller_rva']) is int and row['caller_rva'] in CALLERS[row['event']],'unexpected native return point')
            need(type(row['thread']) is int and row['thread']==source['thread'],'event thread changed')
            need(all(integer(row[k],0,64) for k in ('count','queue')) and type(row['layout_nonzero']) is bool,'invalid state sample')
            if row['event']=='allocator_free_double' and row['caller_rva']==0x50B26A:frees.append(row['object'])
        result['authority_sequence']=a['sequence'];result['request_id']=a['request_id'];result['freed_objects']=frees
        if len(frees)>1:
            result['classification']='MULTIPLE_POP_OBSERVED'
        elif frees and frees!=['Reward']:
            result['classification']='WRONG_MENU_TORN_DOWN'
        elif not frees:
            result['classification']='QUEUED_NOT_CLOSED' if trace['queued_before_consume'] else 'NO_COMPLETION_OBSERVED'
        else:
            wanted=['layout_before_double','layout_context_double','layout_destroy_double','parent_resume_double','selection_destroy_double','allocator_free_double']
            actual=[r['event'] for r in events if r['event']!='manager_getter_double' and not (r['event']=='allocator_free_double' and r['caller_rva']==0x50A982)]
            need(actual==wanted,'native teardown sequence incomplete')
            need(trace['queued_before_consume']==1 and trace['top_before_consume']=='Reward' and trace['remaining']==5
                and trace['reward_layout_cleared'] is True and trace['final_top']=='User','teardown target or resulting stack differs')
            result['classification']='MATCHING_TEARDOWN_OBSERVED_WITHOUT_LIFETIME_LEASE'
    except (ValueError,KeyError,TypeError) as error:
        result['classification']='INCOMPLETE_EVIDENCE';result['reasons'].append(str(error))
    return result
