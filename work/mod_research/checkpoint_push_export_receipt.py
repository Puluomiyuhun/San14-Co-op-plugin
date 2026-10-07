"""Offline A-only receipt for the reviewed203111 export. No game/process access.

Consumes immutable workspace evidence and the archived file, never Steam paths.
Successful normalization is historical A evidence, not room or B authorization.
"""
from pathlib import Path, PureWindowsPath
from datetime import datetime
import argparse
import copy
import hashlib
import json
import math
import struct

import checkpoint_push_contract as export_contract
import checkpoint_push_to_guest_contract as guest_contract

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'checkpoint_push_runs/20261006-203111-687580'
ARCHIVE=ROOT/'checkpoint_push_archives/20261006-204306-581930'
FIXTURE=ROOT/'checkpoint_push_fixtures/20261006-202955-491965/result.json'
GAME_SHA='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
FILE_SHA='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
CONTRACT_SHA='eb9b8bbc93dce94d8381e0ab6a27ea62c31ac145a81abd14574826bb8a41ecbc'
PINNED={
 'result.json':'1653c91651f5d43b2173a185c72845a2631923173dd07b1c266641ce5cf2e0a4',
 'before.json':'a683f900362430616397000c2afcc2f8eb7459c39ccc9f11281696bdcf4de237',
 'after.json':'ebc7b303c2a06724306507fe5ddff94c8adcd2a54ebb1a5ad2ffc576534d44bc',
 'known-before.json':'60fe4c73746052ca5e019978c53649f3df795f535a8db8b0a8dd9c6630fd0044',
 'known-after.json':'2c4f42389f564f2122029920f2830a915acb9a6efd7cbc058591fa0808f478a9',
 'trace.jsonl':'289621220ff729abde842c9ac794f750d9b81c1aab1dc484163b8bb17467d1ca',
 'checkpoint_push_pilot.dll':'a27acc0645677f6a5690eb769ab92346d3930a8eec3fb32c5b7cba7f5c2f4403',
 'checkpoint_push_once.intent':'26720bd66884ed52565f91a095e861a03887448a5bea3c7aa9cf3d333c216a1f',
 'fixture.json':'a7ec9490724740b772abd5cccabaaea98c8a68cc07a3fdb195aba3d45292acd1',
 'archive.json':'b51a72a6c7bfc9b4e71ccc1f30d25a53d68169cc910d0c38ae7db4cf746e1cb7',
 'mppush01.s14':FILE_SHA,
}
EXPECTED={'pid':53908,'process_birth':134355726122897449,'base':0x7ff749440000,
          'file_sha256':FILE_SHA,'size':274880,'artifact_sha256':PINNED}
INTENT=struct.Struct('<Q9I16s4x')


class ReceiptError(ValueError):pass


def need(ok,reason):
    if not ok:raise ReceiptError(reason)


def sha(data):return hashlib.sha256(data).hexdigest()


def canonical_sha(value):
    return sha(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode())


def load_bundle():
    """Fixed reviewed workspace paths only; never follows paths inside JSON."""
    paths={name:RUN/name for name in ('result.json','before.json','after.json','known-before.json','known-after.json','trace.jsonl','checkpoint_push_pilot.dll')}
    paths.update({'checkpoint_push_once.intent':ROOT/'checkpoint_push_once.intent','fixture.json':FIXTURE,
                  'archive.json':ARCHIVE/'result.json','mppush01.s14':ARCHIVE/'mppush01.s14'})
    need(sha(Path(export_contract.__file__).read_bytes())==CONTRACT_SHA,'reviewed_export_contract_changed')
    return {name:path.read_bytes() for name,path in paths.items()}


def normalize(bundle,expected=EXPECTED):
    """Pure validation of bytes with separately pinned historical review inputs."""
    try:return _normalize(bundle,expected)
    except ReceiptError:raise
    except (KeyError,ValueError,TypeError,AttributeError,struct.error,UnicodeError) as error:
        raise ReceiptError('missing_or_malformed_evidence:'+str(error)) from error


def _normalize(bundle,expected):
    need(set(bundle)==set(PINNED),'missing_or_extra_artifact')
    hashes={name:sha(data) for name,data in bundle.items()}
    need(hashes==expected['artifact_sha256'],'artifact_hash_not_review_pinned')
    read=lambda name:json.loads(bundle[name])
    result=read('result.json');before=read('before.json');after=read('after.json')
    known_before=read('known-before.json');known_after=read('known-after.json')
    archive=read('archive.json');fixture=read('fixture.json');r=result['adapter']
    need(result['schema']=='san14.checkpoint-push-result.v2' and result['result']=='PASS' and result['mode']=='execute','not_passing_execute')
    need(result['before']==before and result['after']==after,'embedded_precheck_mismatch')
    need(result['install_exit']==0 and result['native_save_complete'] is True and result['capture_error'] is None,'export_incomplete')
    need(result['load_performed'] is False and result['native_worker_directly_called'] is False and result['old_pilot_reenabled'] is False,'unsupported_execution_scope')
    need(result['full_world_sync_proven'] is False,'unjustified_full_world_claim')
    need(export_contract.native_lifecycle_ok(r),'worker_return_or_lifecycle_not_complete')
    for label,sample in (('before',before),('after',after)):
        need(sample['result']=='PASS' and sample['reasons']==[],'precheck_not_passed_'+label)
        need(sample['pid']==expected['pid'] and sample['process_birth']==expected['process_birth'] and int(sample['base'],0)==expected['base'],
             'stale_process_attachment_'+label)
        snap=sample['context']['snapshot']
        need(snap['pid']==expected['pid'] and snap['exe_sha256']==GAME_SHA,'snapshot_attachment_'+label)
        need(PureWindowsPath(sample['target']).name=='mppush01.s14','forensic_or_wrong_target_'+label)
        need(sample['intent']==result['intent'] and PureWindowsPath(sample['intent']).name=='checkpoint_push_once.intent','wrong_once_scope_'+label)
        for key in ('pinned_user','pinned_game','pinned_world'):
            need(int(sample[key],0)==r[key],'wrong_'+key+'_'+label)
        need(sample['cache_mode']==r['cache_mode_before'] and sample['global_rng']==r['before_rng'],'precheck_rng_cache_'+label)
        need(sample['context']==(known_before if label=='before' else known_after)['context'],'known_capture_context_'+label)
    need(r['base']==expected['base'] and r['caller']==expected['base']+0x50B785,'wrong_native_caller')
    need(result['hooks_restored_from_memory'] is True and result['hook_pages_after']==before['hook_pages']==after['hook_pages'],'hook_page_cleanup_not_proven')
    need(result['hook_slots_after']=={'user':expected['base']+0x3F9B00,'save':expected['base']+0x4AA650},'wrong_restored_hook_slots')
    need(result['dll_sha256']==hashes['checkpoint_push_pilot.dll']==fixture['dll_sha256'],'dll_evidence_mismatch')
    need(result['fixture_evidence_sha256']==hashes['fixture.json'] and fixture['result']=='PASS'
         and fixture['source_fingerprints']['contract.py']==CONTRACT_SHA,'fixture_evidence_mismatch')

    intent=bundle['checkpoint_push_once.intent'];need(len(intent)==64,'wrong_once_size')
    fields=INTENT.unpack(intent)
    magic,version,pid,thread,slot,year,month,day,force,ruler,filename=fields
    need(magic==0x53414E1450534832 and version==2,'wrong_once_abi')
    need(pid==expected['pid'] and thread==r['executor_thread'],'wrong_once_attachment')
    need(slot==0xffffffff and (year,month,day,force,ruler)==(203,8,11,12,666),'wrong_once_state')
    need(filename==b'mppush01.s14\0\0\0\0','forensic_or_wrong_once_filename')

    rows=[json.loads(line) for line in bundle['trace.jsonl'].splitlines()]
    need(len(rows)>=6 and rows[-1]['adapter']==r,'trace_final_report_mismatch')
    prior_elapsed=-1.0;prior={}
    monotonic=('intent_created','intent_flushed','binder_calls','queue_calls','save_worker_started','save_worker_joined','save_finalizer_returned','return_matched')
    first_seen={}
    for i,row in enumerate(rows):
        elapsed=row['elapsed'];p=row['adapter']
        need(type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed>=prior_elapsed>=-1,'trace_time_order')
        prior_elapsed=elapsed
        need(export_contract.report_valid(p),'invalid_trace_report')
        need(all(p[k]==0 for k in ('error','exception_code','save_observation_error','stop_requested')),'trace_uncertainty')
        need(p['base']==expected['base'] and p['pinned_user']==r['pinned_user'],'trace_attachment')
        for key in monotonic:
            need(p[key]>=prior.get(key,0),'trace_flag_regression_'+key)
            if p[key] and key not in first_seen:first_seen[key]={'poll_index':i,'elapsed_seconds':elapsed}
        prior=p
    need(set(first_seen)==set(monotonic),'trace_missing_lifecycle_observation')
    # Several effects are first seen in the SAME poll. Do not invent distinct
    # event times or feed a fabricated strictly increasing sequence to B.
    order=[first_seen[k]['poll_index'] for k in monotonic]
    need(order==sorted(order),'trace_lifecycle_order')

    f=result['file']
    need(f['sha256']==expected['file_sha256']==hashes['mppush01.s14'] and f['size']==expected['size']==len(bundle['mppush01.s14']),'exported_file_hash_or_size')
    need(f['sha256']!=guest_contract.FORENSIC_SHA and f['first_seen_after_queue'] is True,'forensic_or_unassociated_file')
    details=export_contract.completion_evidence(r,after,f,known_before,known_after)
    need(details['complete'] and result['completion_evidence']==details,'coverage_or_completion_evidence_mismatch')
    need(archive['result']=='PASS' and archive['passing_bounded_A_export'] is True and archive['filename']=='mppush01.s14','archive_not_passing_export')
    need(archive['sha256']==f['sha256'] and archive['size']==f['size'] and archive['export_result_sha256']==hashes['result.json'],'archive_association')
    need(archive['native_parser_success'] is True and archive['file_format_version']==92 and archive['date']=={'year':203,'month':8,'day':11} and archive['ruler_name']=='张鲁','archive_header')
    parsed=bytes.fromhex(archive['parsed_header_hex'])
    need(len(parsed)==0x150 and sha(parsed)==archive['parsed_header_sha256'],'archive_parsed_header_digest')
    need(parsed[0x10:0x16]=='张鲁\0'.encode('utf-16le') and struct.unpack_from('<H',parsed,0xE2)[0]==203 and parsed[0xE4:0xE6]==bytes((8,11)),'archive_header_fields')
    need(sha(bundle['mppush01.s14'][:archive['header_bytes_consumed']])==archive['raw_header_prefix_sha256'],'archive_raw_header_digest')

    attachment={'pid':expected['pid'],'process_start_100ns':expected['process_birth'],'base':expected['base'],'game_sha256':GAME_SHA}
    def planning(sample):
        snap=sample['context']['snapshot']
        return {'stack':copy.deepcopy(snap['state_stack']),'phase':sample['context']['state_sample']['phase_raw'],
                'date':[snap['date'][k] for k in ('year','month','day')],'force_id':snap['player']['force_id'],
                'ruler_id':snap['player']['ruler_id'],'user_pointer':int(sample['pinned_user'],0),
                'pending_state_commands':sample['pending_vector']['count']}
    source_fields={'filename':'mppush01.s14','export_slot':-1,'evidence_origin':'reviewed_native_capture',
        'trace_sha256':hashes['trace.jsonl'],'attachment':attachment,'outcome':'NATIVE_PUSH_EXPORT_OBSERVED_RETURNED_USER',
        'forensic':False,'queue_type':0,'before':{'planning':planning(before)},'after':{'planning':planning(after)},
        'file':{'sha256':f['sha256'],'size':f['size'],'created_new':True,'local_absent_before':True,'native_absent_before':True},
        'lifecycle':{'request_associated':bool(r['save_association_ok']),'worker_success':bool(r['save_native_success']),
                     'finalizer_returned':bool(r['save_finalizer_returned']),'request_globals_cleared':bool(r['save_globals_cleared']),
                     'hooks_restored':True,'existing_saves_unchanged':details['ordinary_saves_unchanged'],
                     'binder_calls':r['binder_calls'],'queue_calls':r['queue_calls']}}
    rejected=False;reason=None
    try:
        guest_contract.prepare_guest_checkpoint(source=source_fields,current_source={},current_guest={},target_binding={},
                                                 expected={'schema':guest_contract.SCHEMA},staged_bytes=bundle['mppush01.s14'])
    except guest_contract.ContractError as error:rejected=True;reason=str(error)
    need(rejected,'A_only_evidence_unexpectedly_authorized_guest_preparation')
    return {'schema':'san14.checkpoint-push-A-export-receipt.v1','result':'A_EXPORT_VERIFIED_GUEST_UNBOUND',
            'run_id':RUN.name,'evidence_origin':'reviewed_native_capture','artifact_sha256':hashes,
            'source_fields_for_future_binding':source_fields,
            'attachment_scope':'Historical process lifetime at this export only; no live process was queried, no current attachment nonce exists.',
            'durable_intent':{'sha256':hashes['checkpoint_push_once.intent'],'raw_hex':intent.hex(),'magic':hex(magic),'version':version,
                              'pid':pid,'thread':thread,'slot':-1,'date':[year,month,day],'force_id':force,'ruler_id':ruler,
                              'filename':filename.split(b'\0')[0].decode(),'created_report':r['intent_created'],'flushed_report':r['intent_flushed']},
            'native_report':copy.deepcopy(r),'native_tick_observations':{k:r[k] for k in ('queued_at','finalized_at','returned_at')},
            'trace_first_seen':first_seen,'trace_order_scope':'Polling observations; intent/binder/queue share a poll. Not a strict event sequence.',
            'file_stability_summary':copy.deepcopy(f),'individual_file_stability_samples_recorded':False,
            'local_archived_file_sha256_verified':True,'native_full_file_identity_verified':False,
            'known_coverage_comparison':details['coverage'],'ordinary_saves':details['ordinary_saves'],'sidecars':details['sidecars'],
            'header_evidence':{k:archive[k] for k in ('file_format_version','date','ruler_name','header_bytes_consumed','parsed_header_sha256')},
            'guest_contract_refusal':{'rejected':rejected,'reason':reason},
            'unresolved_binding_prerequisites':[
                'No room_id/epoch/turn/last_command_seq or authority checkpoint ID was issued in this single-player experiment.',
                'No durable command freeze or current source attachment nonce was established; historical process birth is not a new live check.',
                'No strict per-event sequence or raw individual stable-file samples were retained; do not invent either.',
                'No B attachment, chosen B force proof, native metadata node/positive slot/cache-generation prebinding or B local staged-file observation exists.',
                'No complete native Steam file-byte identity or B worker/identity/returned-User observation exists.',
                'The exact existing guest contract expects additional lifecycle/schema facts. This receipt is deliberately partial and is refused by it.',
            ],
            'B_binding':None,'B_load_performed':False,'load_authorized':False,'formal_room_checkpoint_usable':False,
            'full_world_verified':False,'game_access_by_receipt_tool':False,
            'scope':'A-only bounded successful native export; not a multiplayer checkpoint or permission to reuse the once intent.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);args=p.parse_args()
    receipt=normalize(load_bundle())
    if args.output:
        dest=args.output.resolve();need(dest.parent==ROOT and dest.name.startswith('checkpoint_push_export_receipt_') and dest.suffix=='.json','output_must_be_new_receipt_in_work')
        with dest.open('x',encoding='utf-8') as file:json.dump(receipt,file,ensure_ascii=False,indent=2);file.write('\n')
    print(json.dumps({'result':receipt['result'],'file_sha256':FILE_SHA,'guest_contract_refused':receipt['guest_contract_refusal']['rejected'],
                      'load_authorized':False,'output':str(args.output) if args.output else None},ensure_ascii=False))


if __name__=='__main__':main()
