from pathlib import Path
import sys,json

before=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
after=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
b=before['critical_state'];a=after['critical_state']
new_ids=set(u['id'] for u in after['all_active_units'])-set(u['id'] for u in before['all_active_units'])
new_units=[u for u in after['all_active_units'] if u['id'] in new_ids]
report={'date_unchanged':b['date']==a['date'],
        'player_unchanged':b['player']==a['player'],
        'garrison_before':b['city']['garrison'],'garrison_after':a['city']['garrison'],
        'garrison_spent':b['city']['garrison']-a['city']['garrison'],
        'actions_before':b['district']['action_points'],'actions_after':a['district']['action_points'],
        'actions_spent':b['district']['action_points']-a['district']['action_points'],
        'new_units':new_units,
        'officer_units':a['officer_units'],
        'critical_state_matches':before['critical_state_sha256']==after['critical_state_sha256']}
if len(sys.argv)>3:Path(sys.argv[3]).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
