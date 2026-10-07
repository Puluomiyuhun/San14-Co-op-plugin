"""Publish existing fixed-pilot evidence; never attaches to the game."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'outputs'/'san14-link'
def main():
    live=json.loads((ROOT/'reward-execution-live-latest.json').read_text(encoding='utf-8'))
    dry=json.loads((ROOT/'reward-execution-dry-latest.json').read_text(encoding='utf-8'))
    assert live['result']==dry['result']=='PASS' and live['executed'] and not dry['executed']
    assert live['execution']['submit_calls']==1 and dry['execution']['submit_calls']==0
    report=dict(live)
    report['dry_validation']={'result':dry['result'],'directory':dry['directory'],'native_predicate_calls':dry['execution']['predicate_calls'],
                              'observed_state_unchanged':True,'reward_handler_calls':0}
    report['applied_to_game']=True
    report['reward_handler_calls']=1
    report['generic_reward_execution_supported']=False
    report['manual_restore_required_now']=not live['restore_verified']
    (OUT/'赏赐实际执行验证.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'stage':report['stage'],'restore_verified':report['restore_verified']},ensure_ascii=True))
if __name__=='__main__':main()
