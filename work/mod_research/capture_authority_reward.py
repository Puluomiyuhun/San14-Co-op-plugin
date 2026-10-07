"""Capture both faction contexts, keeping the actual local player unchanged."""
from datetime import datetime
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'outputs/san14-link'))
from game_reader import GameReader
from authority_reward import capture_context,make_command,validate_reward,eligible_ids
run=ROOT/'authority-reward-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
run.mkdir(parents=True)
r=GameReader()
try:
    initial=r.snapshot();results=[]
    for force,ids in [(12,[97,759,904]),(2,[101,264,411])]:
        context=capture_context(r,force)
        command=make_command(context,context['main_district_id'],ids)
        result=validate_reward(command,context,force)
        assert context==capture_context(r,force)
        for suffix,data in [('context',context),('command',command),('preflight',result)]:
            with (run/f'force-{force}-{suffix}.json').open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
        results.append({'force':force,'viewer':context['viewer_force_id'],'ruler_id':context['ruler_id'],
                        'selected_officers':result['selected_officers'],'eligible_ids':eligible_ids(context,context['main_district_id']),
                        'costs':result['expected_costs']})
    assert r.snapshot()==initial
finally:r.close()
report={'result':'PASS','directory':str(run),'applied_to_game':False,'contexts':results}
with (ROOT/'authority-reward-current.json').open('w',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps(report,ensure_ascii=True))
