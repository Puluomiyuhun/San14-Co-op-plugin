"""Read-only real-period closeout after the user restores slot 34."""
from pathlib import Path
from datetime import datetime
import json,struct,hashlib,sys
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import human_rules_activation_live_session_v4 as live
from start_startup_switch import no_debugger
from analyze_startup_switch import compare_records

def ref(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def read(p):return json.loads(p.read_text(encoding='utf8'))
def main():
    claim=P/'human_rules_activation_live_v4_2904_134358355367489493_once.json'
    c=read(claim);run=Path(c['run']);prep=read(run/'prepared.json');round_report=read(run/'round-report.json')
    events=[json.loads(s)for s in (run/'events.jsonl').read_text(encoding='utf8').splitlines()]
    assert [e['kind']for e in events]==['starting','prepared','ready_for_install','install_complete','round_captured','restore_complete','closed_with_sources_original']
    assert events[-1]['revoke_exit']==0
    ai=round_report['ai'];income=round_report['income']
    assert round_report['state']==4 and round_report['error']==round_report['blocked']==0
    assert ai['active']==ai['abnormal_exits']==income['active']==income['abnormal']==income['held']==0
    assert ai['exits']==sum(ai['entered']) and income['entries']==income['exits']
    assert income['entries']==sum(income[k]for k in ('native','human','ai','held'))
    assert all(n==a+b+h for n,a,b,h in zip(ai['entered'],ai['native'],ai['bypassed'],ai['held'])) and sum(ai['held'])==0
    assert read(run/'restore-report.json')==round_report
    publication={}
    for op in ('install','restore'):
        result=read(run/(op+'-publisher-result.json'))
        assert result['exit']==0 and result['publisher']['detached'] and not result['publisher']['uncertain']
        assert result['publisher']['written_mask']==63 and result['publisher']['error']==0
        assert live.same_known_data(read(run/(op+'-before.json')),read(run/(op+'-after.json')))
        publication[op]=result
    assert live.same_known_data(read(run/'prepare-before.json'),read(run/'prepare-after.json'))
    before=read(run/'prepare-before.json');end=read(run/'round-state.json')
    assert end['context']['snapshot']['date']=={'year':203,'month':8,'day':21,'period':'下旬'}
    reader=live.BattleObserver()
    try:
        no_debugger(reader)
        assert reader.pid==c['pid'] and live.process_birth(reader)==c['birth']
        assert all(reader.memory.read(reader.memory.base+a,len(v))==v for a,_,v in live.profiles())
        assert struct.unpack('<i',reader.memory.read(prep['exports']['HumanRulesActivationState'],4))[0]==6
        after=live.known_snapshot(reader,expected_user_hook=before['expected_user_hook'])
        assert after['context']['snapshot']['date']==before['context']['snapshot']['date']
        assert after['context']['snapshot']['player']==before['context']['snapshot']['player']
        assert live.sha(live.SOURCE)==live.SOURCE_SHA
        comparison=compare_records(before['objects'],after['objects'])
        assert not comparison['other_record_changes'] and comparison['active_army_semantics_equal'] and comparison['task_fields_equal']
        assert before['tiles']['ordered_payload_hex']==after['tiles']['ordered_payload_hex']
        assert before['objects']['global_rng']==after['objects']['global_rng'] and before['objects']['world_rng_fields_hex']==after['objects']['world_rng_fields_hex']
        live.write(run/'user-restored34.json',after)
    finally:reader.close()
    files_before=before['save_files'];files_end=end['save_files']
    changed=sorted(k for k in files_before.keys()&files_end.keys()if files_before[k]!=files_end[k])
    out={'schema':'san14.real-human-rules-period.v1','result':'PASS_REAL_SINGLE_GAME_RULES_PERIOD_AND_RESTORE34',
         'updated':datetime.now().astimezone().isoformat(timespec='seconds'),'pid':c['pid'],'birth':c['birth'],
         'real_game_processes':1,'local_tls_diagnostic_peers':2,'human_factions':[12,2],'main_districts':[11,2],
         'actual_ai_calls':ai['exits'],'ai_bypassed':sum(ai['bypassed']),'ai_original':sum(ai['native']),
         'ai_by_route':{k:{'entered':ai['entered'][i],'native':ai['native'][i],'bypassed':ai['bypassed'][i]}for i,k in enumerate(('force','district','army','group'))},
         'income_predicate_calls':income['entries'],'income_classified_human':income['human'],'income_classified_ai':income['ai'],
         'income_count_is_not_transactions':True,'per_income_caller_breakdown_recorded':False,
         'active':0,'held':0,'abnormal':0,'native_errors':0,
         'before_date':before['context']['snapshot']['date'],'round_end_date':end['context']['snapshot']['date'],
         'final_date':after['context']['snapshot']['date'],'final_player':after['context']['snapshot']['player'],
         'six_sources_restored':True,'debugger_attached':False,'room_retired':True,'module_retained':True,
         'coordinator_exec_session':44057,'coordinator_exit_code_reported_by_root_tool':0,
         'slot34_unchanged':True,'period_save_files_changed':changed,'period_save_files_added':sorted(files_end.keys()-files_before.keys()),
         'restored_sample_comparison':comparison,'restored_hex_fields_equal':True,'restored_sample_rng_equal':True,
         'publication':publication,'source_claim':ref(claim),'run_directory':str(run),
         'scope':'Real native business and policy wrappers in one existing game process. Local Room seats are diagnostic, not two real game clients. Aggregate AI entries are not individual player orders. Income counters count predicates, not income transactions or values.',
         'not_proven':['two real clients','every AI path throughout a complete campaign','all gameplay unchanged except requested policy','numeric economy parity','full world equality','battle determinism','ready/input exclusion','repeatable checkpoint load loop']}
    live.write(run/'closeout.json',out)
    live.write(P/'human_rules_activation_live_round_handoff.json',out)
    print(json.dumps({'result':out['result'],'ai_calls':out['actual_ai_calls'],'bypassed':out['ai_bypassed'],'native':out['ai_original'],'income':out['income_predicate_calls'],'changed_save_files':changed,'runtime_pointer_changes':len(comparison['runtime_pointer_changes']),'game_writes':0,'native_calls':0}))

if __name__=='__main__':main()
