"""Read-only closeout of the user's basic Liu Bei menu check."""
from datetime import datetime
from pathlib import Path
from run_second_force_reward import BattleObserver,capture
from startup_identity_reader import capture_startup_context
from start_startup_switch import ROOT,load,save,sha,no_debugger,CHECKPOINT,CHECKPOINT_SHA
from analyze_startup_switch import compare_records

def main():
    meta=load(ROOT/'startup-switch-active.json');folder=Path(meta['directory'])
    reader=BattleObserver()
    try:
        no_debugger(reader);after=capture(reader);ctx=capture_startup_context(reader)
        assert after==capture(reader) and ctx==capture_startup_context(reader),'Read-only sample changed during capture'
        assert ctx['snapshot']['player']['force_id']==2 and ctx['snapshot']['player']['ruler_id']==952
        assert ctx['snapshot']['date']=={'year':203,'month':8,'day':11,'period':'中旬'}
        assert sha(CHECKPOINT)==CHECKPOINT_SHA
        comparison=compare_records(load(folder/'after.json'),after)
        save(folder/'after-menu.json',after);save(folder/'context-after-menu.json',ctx)
        observation={'schema':'san14.startup-menu-observation.v1','created':datetime.now().astimezone().isoformat(),
                     'directory':str(folder),'source':'user_message','user_text':'试了下，基本都没问题',
                     'requested_checks':['庐江进入赏赐武将选择页后取消','宛城不能下本势力内政命令'],
                     'result':'USER_REPORTED_BASIC_MENU_CHECKS_OK','native_player':ctx['snapshot']['player'],
                     'all_menus_verified':False,'events_verified':False,'command_execution_verified_by_this_check':False,
                     'comparison_since_post_load':comparison,'checkpoint34_unchanged':True,'debugger_attached':False,
                     'scope':'User reports the requested basic menu checks were generally fine, without item-by-item details. Does not certify all permissions, commands or event ownership.'}
        save(folder/'user-menu-observation.json',observation);save(ROOT/'startup-switch-menu-result.json',observation)
        print({'result':observation['result'],'sample_changes_since_post_load':comparison['other_record_changes'],
               'army_semantics_equal':comparison['active_army_semantics_equal'],'task_fields_equal':comparison['task_fields_equal'],
               'current_player':ctx['snapshot']['player'],'debugger_attached':False})
    finally:reader.close()

if __name__=='__main__':main()
