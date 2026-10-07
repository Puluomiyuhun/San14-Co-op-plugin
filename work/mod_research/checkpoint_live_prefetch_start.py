"""One real User-call menu-prefetch observation. Default: read-only check.

No load/save/order action. Uses the approved one-thread hardware observer;
the User slot and debug state must be restored. DLL remains pinned in game.
Installation completion must be known before STOP is dispatched. A durable
single live claim prevents automatic retries, including uncertain outcomes.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import struct
import sys
import time

P=Path(__file__).resolve().parent
sys.path[:0]=[str(P),str(P/'python_deps'),str(P.parents[1]/'outputs'/'san14-link')]
APPROVED_DLL='3506c4fc18dd82a5adad6244eb992524ed8d8ae2bcd24c552f42e60d69980373'
APPROVED_HANDOFF='4fc7657b472820af3ccdc6a7a462be3c2bfcff7d551356924a104ed67b563799'
APPROVED_CONTRACT='ed3906765f76b6873f4a904531aa30c1c068916ab2a6af53b56713c926080791'
CLAIM=P/'checkpoint_live_prefetch_live_once.json'
EXPORTS=('InstallCheckpointLivePrefetchObserver','GetCheckpointLivePrefetchReport','StopCheckpointLivePrefetchObserver')


def require(ok,message):
    if not ok:raise RuntimeError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


class RemoteCallError(RuntimeError):
    def __init__(self,cause,*,completed,may_have_started,thread_id,cleanup_errors):
        super().__init__(str(cause))
        self.completed=completed
        self.may_have_started=may_have_started
        self.thread_id=thread_id
        self.cleanup_errors=cleanup_errors


def invoke(api,address,data=None,output_size=0):
    """Retain remote buffer after an uncertain thread; never terminate it."""
    require(not (data is not None and output_size),'Input/output modes are separate')
    allocation=thread=None;completed=False;create_attempted=False;creation_failed=False
    tid=W.DWORD();error=None;answer=None;cleanup_errors=[]
    try:
        size=len(data) if data is not None else output_size
        if size:
            allocation=api.k.VirtualAllocEx(api.handle,None,size,0x3000,4)
            require(allocation,'Cannot allocate observer buffer')
            if data is not None:
                buffer=C.create_string_buffer(data);written=C.c_size_t()
                require(api.k.WriteProcessMemory(api.handle,allocation,buffer,len(data),C.byref(written)) and
                        written.value==len(data),'Cannot publish observer config')
        # Mark the uncertain side of publication before entering the OS call:
        # Python interruption after native success may prevent assignment.
        create_attempted=True
        thread=api.k.CreateRemoteThread(api.handle,None,0,address,allocation,0,C.byref(tid))
        creation_failed=not thread
        require(thread,'Cannot create observer control thread')
        require(api.k.WaitForSingleObject(thread,10000)==0,
                'Observer call timed out; thread and argument lifetime remain uncertain')
        completed=True;code=W.DWORD()
        require(api.k.GetExitCodeThread(thread,C.byref(code)),'Cannot read observer control result')
        raw=api.reader.memory.read(allocation,output_size) if output_size and code.value==0 else None
        answer=(code.value,raw)
    except BaseException as exc:
        error=exc
    finally:
        if thread:
            try:
                if not api.k.CloseHandle(thread):cleanup_errors.append('CONTROL_THREAD_HANDLE_CLOSE_FAILED')
            except BaseException:cleanup_errors.append('CONTROL_THREAD_HANDLE_CLOSE_UNCERTAIN')
        if allocation and (completed or not create_attempted or creation_failed):
            try:
                if not api.k.VirtualFreeEx(api.handle,allocation,0,0x8000):cleanup_errors.append('BUFFER_RELEASE_FAILED')
            except BaseException:cleanup_errors.append('BUFFER_RELEASE_UNCERTAIN')
    if error or cleanup_errors:
        raise RemoteCallError(error or ';'.join(cleanup_errors),completed=completed,
            may_have_started=create_attempted and not creation_failed,thread_id=tid.value,
            cleanup_errors=cleanup_errors) from error
    return answer


def validate_prefetch_report(report,*,base,user,attempt,attachment_hex):
    require(all(report[k]==1 for k in ('admission_claimed','admission_started',
        'admission_finished','admission_closed','admission_begin_ok')),
        'First native-call observation is incomplete')
    require(all(report[k]==0 for k in ('admission_errors','admission_abnormal',
        'admission_bind_error','admission_close_error','admission_resolver_calls')),
        'Admission observer reports an error or unexpected allocation resolution')
    hardware=report['hardware']
    require(hardware['capture_kind']==1 and all(hardware[k]==1 for k in
        ('entered','captured','restored','finished','module_pinned','observer_calls')),
        'Missing actual hardware execution capture or restoration')
    require(all(hardware[k]==0 for k in ('error','os_error','exception_code',
        'helper_deadline_exceeded','restore_uncertain')),'Hardware capture was uncertain')
    require(hardware['site_rip']==base+0x3F9DAF and hardware['user']==user and
        hardware['call_id']==report['firstCall'] and hardware['thread']==report['ownerThread'] and
        hardware['gpr'][6]==user and hardware['gpr'][4]%16==0,
        'Hardware context does not belong to the observed first User call')
    require(hardware['binding']==dict(attempt_hex=attachment_hex[:32],
        attachment_hex=attachment_hex[32:],owner_generation=attempt),
        'Hardware binding differs from the exact supplied tokens')
    require(hardware['original_dr']==hardware['restored_dr'] and
        hardware['original_code_unchanged'] is True and hardware['queue_authorized'] is False and
        hardware['full_input_hold'] is False,'Hardware state not restored or unsupported authority claimed')
    for stage,pending in enumerate((report['pending_before'],hardware['pending'],report['pending_after']),1):
        require(pending['error']==0 and pending['decision']==1 and pending['stage']==stage and
            pending['call_id']==report['firstCall'] and pending['menu_command']==-1 and
            pending['user_phase']==2 and pending['stack_count']==5 and pending['queue_count']==0 and
            all(pending[k]==0 for k in ('game_transition','load_queued','advance','panel_advance')),
            'Entry, prefetch, or return was not a clean same-call observation')
        require(pending['read_only'] is True and pending['pending_admission_candidate'] is (stage!=1) and
            all(pending[k] is False for k in ('native_hook_installed','all_pending_sources_covered','full_input_hold')),
            'Pending observation contains an unsupported readiness claim')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--observe',action='store_true')
    args=parser.parse_args()
    from checkpoint_manual_reload_observe_start import precheck
    before=precheck()
    if not args.observe:
        print(json.dumps(before,ensure_ascii=False));return
    require(before['result']=='PASS','Game must be in the verified idle planning state')
    require(not CLAIM.exists(),'Live observation already claimed; no automatic retry')
    handoff=P/'checkpoint_live_prefetch_handoff.json'
    require(sha(handoff)==APPROVED_HANDOFF,'Observer handoff has not been independently approved')
    dll=P/'checkpoint_live_prefetch_core.dll'
    require(sha(dll)==APPROVED_DLL,'Observer DLL differs from the approved build')
    require(sha(P/'checkpoint_live_prefetch_contract.py')==APPROVED_CONTRACT,
            'Observer ABI contract differs from the reviewed source')
    from checkpoint_live_prefetch_contract import config_bytes,decode_report,Report
    from run_autonomous_pilot import ProcessAPI,pefile
    from battle_observer import BattleObserver
    from checkpoint_push_start import hook_pages,process_birth
    from checkpoint_live_capture import sample,comparison
    from checkpoint_live_force_capture import capture as force_capture,compare as force_compare
    folder=P/'checkpoint_live_prefetch_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    result=dict(schema='san14.live-prefetch-observation.v1',result='INCOMPLETE',
        load_requested=False,save_requested=False,game_order_submitted=False,
        full_world_verified=False,complete_session_installed=False,module_retained=True,
        dll_sha256=APPROVED_DLL,install_completed=False,stop_completed=False)
    reader=api=None;report_address=stop_address=None;installed_completed=False
    stopped=False
    try:
        reader=BattleObserver();base=reader.memory.base
        require(reader.pid==before['pid'] and process_birth(reader)==before['process_birth'] and
                hex(base)==before['base'],'Game attachment changed')
        known_before=sample();force_before=force_capture(reader);pages_before=hook_pages(reader)
        save(folder/'known-before.json',known_before);save(folder/'force-before.json',force_before)
        q=lambda address:struct.unpack('<Q',reader.memory.read(address,8))[0]
        states=[address for _,address in reader.state_objects()]
        manager=base+0x19E7310;cache=q(base+0x2025318)
        prefetch_before=reader.memory.read(base+0x3F9DAF,33)
        root=q(base+0x1FCA1E0);world=q(root+0x85130)
        attempt=secrets.randbits(64) or 1;binding_hex=secrets.token_hex(32)
        native_log=P/('checkpoint_live_prefetch_'+secrets.token_hex(16)+'.jsonl')
        config=config_bytes(pid=reader.pid,birth=before['process_birth'],base=base,attempt=attempt,
            attachment_hex=binding_hex,root=root,world=world,states=states,
            toolbar=q(states[4]+0x478),panel=q(states[2]+0x480),journal=str(native_log),expected_thread=0,
            cache=cache,stack=q(manager+0x20),stack_capacity=q(manager+0x18),
            queue=q(manager+0x40),queue_capacity=q(manager+0x38),
            expected_mode=struct.unpack('<I',reader.memory.read(cache+8,4))[0],
            helper_deadline_ms=1000,generation=attempt)
        copied=folder/dll.name;shutil.copyfile(dll,copied)
        require(sha(copied)==APPROVED_DLL,'Copied DLL differs')
        pe=pefile.PE(str(copied))
        exports={s.name.decode('ascii'):s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
        image_size=pe.OPTIONAL_HEADER.SizeOfImage;pe.close()
        require(all(name in exports for name in EXPORTS),'Missing observer export')
        save(CLAIM,dict(run=str(folder),pid=reader.pid,birth=before['process_birth'],attempt=attempt,
                       dll_sha256=APPROVED_DLL,load_requested=False,native_log=str(native_log)))
        result.update(before=before,attempt=attempt,binding_hex=binding_hex,native_log=str(native_log))
        api=ProcessAPI(reader)
        invoke(api,api.load_library_address(),str(copied).encode('utf-16le')+b'\0\0')
        modules=[address for address,path in api.modules() if str(path).lower()==str(copied).lower()]
        require(len(modules)==1,'Observer module binding differs')
        module=modules[0];report_address=module+exports[EXPORTS[1]];stop_address=module+exports[EXPORTS[2]]
        try:
            code,_=invoke(api,module+exports[EXPORTS[0]],config)
        except RemoteCallError as call_error:
            installed_completed=call_error.completed
            result.update(install_completed=call_error.completed,
                install_may_have_started=call_error.may_have_started,
                install_control_cleanup_errors=call_error.cleanup_errors)
            raise
        installed_completed=True;result.update(install_completed=True,install_exit=code)
        require(code==0,'Observer rejected installation')

        expected_hook=None
        def report():
            nonlocal expected_hook
            code,raw=invoke(api,report_address,output_size=C.sizeof(Report))
            require(code==0,'Observer report rejected')
            value=decode_report(raw)
            require(value['pid']==reader.pid and value['birth']==before['process_birth'] and
                    value['attempt']==attempt and value['base']==base and value['user']==states[4] and
                    value['slot']==base+0x12CC4A8+0x28 and value['original']==base+0x3F9B00 and
                    module<=value['hook']<module+image_size,'Observer report binding differs')
            if expected_hook is None:expected_hook=value['hook']
            require(value['hook']==expected_hook,'Observer hook identity changed')
            return value

        trace=[];deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            row=report();trace.append(row)
            if row['error']:break
            time.sleep(.15)
        code,_=invoke(api,stop_address);stopped=code==0
        result.update(stop_completed=stopped,stop_exit=code)
        require(stopped,'Observer did not restore owned slot')
        deadline=time.monotonic()+3;previous=None;stable=False
        while True:
            final=report();trace.append(final)
            drained=(final['active']==0 and final['pending_pairs']==0 and
                     all(t['pending']==0 for t in final['threads']))
            stable=drained and previous==final
            if stable or time.monotonic()>=deadline:break
            previous=final
            time.sleep(.05)
        save(folder/'trace.json',trace);result['observer']=final
        result['two_stable_stopped_reports']=stable
        result['scheduler_fence_proven']=False
        require(q(base+0x12CC4A8+0x28)==base+0x3F9B00 and hook_pages(reader)==pages_before,
                'Actual User slot or protection not restored')
        result['actual_slot_and_protection_restored']=True
        require(final['error']==0 and final['firstPair']==1 and final['contextVerified']==1 and
                final['active']==0 and final['bridgeAbnormal']==0 and
                final['bridgeStarted']==final['bridgeReturned'] and final['pair_errors']==0 and
                final['pair_overflow']==0 and final['thread_overflow']==0 and final['matched_pairs']>0 and
                final['thread_count']>0 and stable,'Observation did not finish cleanly')
        require(final['matchingBefore']==final['matchingAfter']==final['matched_pairs'] and
                sum(t['before'] for t in final['threads'])==final['matched_pairs'] and
                sum(t['after'] for t in final['threads'])==final['matched_pairs'] and
                all(t['before']==t['after'] and t['pending']==0 for t in final['threads']),
                'Stopped callback accounting differs')
        require(all(final[key]==1 for key in ('installed','stopped','modulePinned','slotRestored',
                'protectionRestored')) and final['firstArgs'][0]==states[4] and
                final['firstCaller']==base+0x50B785,'Observer terminal identity or restoration differs')
        require(all(final[key]==0 for key in ('queueCalls','requestCas','loadRequested','fullInputHold',
                'schedulerFenceProven','completeSessionInstalled')),'Unexpected native control claim')
        require(reader.memory.read(base+0x3F9DAF,33)==prefetch_before,'Native prefetch code changed')
        result['prefetch_code_unchanged']=True
        validate_prefetch_report(final,base=base,user=states[4],attempt=attempt,attachment_hex=binding_hex)
        known_after=sample();force_after=force_capture(reader)
        save(folder/'known-after.json',known_after);save(folder/'force-after.json',force_after)
        result['known_comparison']=comparison(known_before,known_after)
        result['force_comparison']=force_compare(force_before,force_after)
        require(known_before['save_files']==known_after['save_files'],'Existing save files changed')
        require(result['force_comparison']['observed_table_equal'] and
                not result['known_comparison']['objects']['other_record_changes'] and
                result['known_comparison']['all_48400_hex_serialized_fields_equal'] and
                result['known_comparison']['sampled_world_rng_fields_equal'] and
                all(known_before['context']['snapshot'][key]==known_after['context']['snapshot'][key]
                    for key in ('date','player','state_stack')),
                'Sampled business data changed during observation')
        result['global_rng_diagnostic_only']=True
        result['normal_observation_window_seconds']=5
        result['per_control_call_timeout_seconds']=10
        result.update(result='PASS_OBSERVATION_ONLY',existing_save_files_unchanged=True)
    except BaseException as exc:
        result['error']=repr(exc)
        # Never race STOP against an installation whose thread may still run.
        if api and stop_address and installed_completed and not stopped:
            try:
                code,_=invoke(api,stop_address);result['cleanup_stop_exit']=code
                result['stop_completed']=code==0
            except BaseException as cleanup:result['cleanup_error']=repr(cleanup)
    finally:
        if api:api.close()
        if reader:reader.close()
        save(folder/'result.json',result)
    print(json.dumps({'result':result['result'],'result_path':str(folder/'result.json'),
                     'stop_completed':result['stop_completed'],'error':result.get('error')},ensure_ascii=False))
    if result['result']!='PASS_OBSERVATION_ONLY':raise SystemExit(1)


if __name__=='__main__':main()
