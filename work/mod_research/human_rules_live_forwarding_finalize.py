"""Pin completed real-game pass-through evidence, without game access."""
import hashlib
import json
from pathlib import Path
from datetime import datetime

P=Path(__file__).resolve().parent
RUN=P/'human_rules_stage_live_runs/20261007-222556-471691'
CYCLE=RUN/'native-forwarding'


def read(path):return json.loads(path.read_text(encoding='utf8'))
def ref(path):return {'path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    install=read(CYCLE/'install-closeout.json');restore=read(CYCLE/'restore-closeout.json')
    inspection=read(RUN/'inspection-223937-475490.json');restored34=read(CYCLE/'restored34-closeout.json')
    before=read(CYCLE/'install-before.json');end=read(CYCLE/'restore-before.json')
    assert install['result']=='PASS_REAL_GAME_INSTALLED_PASSTHROUGH'
    assert restore['result']=='PASS_REAL_GAME_RESTORED' and restore['known_data_equal']
    for receipt in (install,restore):
        assert receipt['publisher']['written_mask']==63 and receipt['publisher']['detached']
        assert not receipt['publisher']['uncertain'] and receipt['publisher']['threads_checked']==102
        assert receipt['debugger_present'] is False and receipt['policy_enabled'] is False
    expected=[11,14,50,45,348,348]
    for counters in (inspection['counters'],restore['counters'],restored34['counters']):
        assert counters['entered']==counters['exited']==expected
        assert counters['state']==2
        assert all(counters[k]==0 for k in ('error','active','abnormal','unexpected_income_caller'))
    assert before['context']['snapshot']['date']['day']==11 and end['context']['snapshot']['date']['day']==21
    assert end['context']['snapshot']['state_stack']==before['context']['snapshot']['state_stack']
    assert restored34['result']=='PASS_USER_RESTORED34_AND_SIX_NATIVE_SOURCES'
    files_before=before['save_files'];files_after=end['save_files']
    assert files_before.keys()==files_after.keys()
    changed=[name for name in files_before if files_before[name]!=files_after[name]]
    assert changed==['autosdexSC07.s14']
    assert files_before['svdexSC34.s14']==files_after['svdexSC34.s14']
    references={name:ref(path) for name,path in {
        'preparation':RUN/'preparation-closeout.json',
        'idle_install':RUN/'install-closeout.json','idle_restore':RUN/'restore-closeout.json',
        'native_install':CYCLE/'install-closeout.json','native_restore':CYCLE/'restore-closeout.json',
        'native_calls_before_restore':RUN/'inspection-223937-475490.json',
        'start_world_sample':CYCLE/'install-before.json','end_world_sample':CYCLE/'restore-before.json',
        'restored34':CYCLE/'restored34-closeout.json','restored34_world_sample':CYCLE/'restored34-state.json',
        'controller_handoff':P/'human_rules_bound_publish_handoff.json',
        'independent_review':P/'human_rules_bound_publish_independent_review.json',
        'initializer_source':P/'human_rules_stage_live_start.py',
        'publication_coordinator_source':P/'human_rules_stage_live_publish.py',
        'finalizer_source':Path(__file__),
    }.items()}
    result=dict(schema='san14.real-game-six-entry-forwarding.v1',
        result='PASS_REAL_GAME_NATIVE_PERIOD_AND_RESTORE34',
        updated=datetime.now().astimezone().isoformat(timespec='seconds'),
        pid=2904,birth=134358355367489493,
        executable_sha256='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025',
        entry_counts=dict(force=11,district=14,army=50,group=45,income_site_28de71=348,income_site_28daa5=348),
        ai_entry_calls=120,income_predicate_calls=696,total_entry_calls=816,
        every_enter_matched_return=True,abnormal=0,active=0,unexpected_income_caller=0,
        native_business_functions_are_test_doubles=False,
        mode='pure pass-through; human AI/economy rules disabled',
        user_action='Normal native one-period advance with no new orders; ordinary reports closed; slot34 restored afterwards.',
        period_before=before['context']['snapshot']['date'],period_after=end['context']['snapshot']['date'],
        final_date=restored34['snapshot']['date'],final_player=restored34['snapshot']['player'],
        final_source_patches_present=False,final_debugger_present=False,
        final_modules_retained=True,original_slot34_unchanged=True,
        automatic_save_changed=changed,automatic_save_change_phase='during user-driven native period, outside install/restore operations',
        restored_sample_nonpointer_changes=0,restored_sample_runtime_pointer_changes=53,
        restored_sample_tiles_equal=True,full_world_verified=False,
        two_human_rules_live=False,two_real_clients_playable=False,two_real_periods_synchronized=False,
        references=references,
        not_proven=['The actual two-human policy bypass or income values under that policy.',
                    'Deterministic equality of this period to an uninstrumented run.',
                    'Complete world equality, full UI hold, remote command synchronization, repeated guest reload.'])
    out=P/'human_rules_live_forwarding_handoff.json'
    with out.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    resume=P/'mainline_20261007_live_resume.json';r=read(resume)
    r['human_rules_live_prepared'].update(six_sources_published=False,actual_native_hook_calls_observed=816,
        native_forwarding_handoff=ref(out),debugger_attached=False,active_cycle=None,
        next='Game restored34, original six sources restored. No more user action pending. Continue policy admission and repeated-load source wiring.')
    r['pending_user_action']=None
    resume.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'result':result['result'],'handoff':ref(out)},ensure_ascii=True))


if __name__=='__main__':main()
