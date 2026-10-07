"""Use the new room's server-derived owner with the existing reward preflight."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'outputs'/'san14-link'
sys.path.insert(0,str(OUT))
from authority_reward import validate_reward, PreflightError
from room_session import digest
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
wire=read(OUT/'房间连接与选势力验证.json')
inputs=read(ROOT/'room-integration-inputs.json')
authority=wire['command_authority']
assert wire['result']=='PASS' and authority['status']=='BINDING_CHECK_ONLY' and not authority['applied_to_game']
assert wire['command_sha256']==digest(inputs['command'])
assert wire['bindings']['B']['force_id']==authority['authorized_force_id']==2
result=validate_reward(inputs['command'],inputs['context'],authority['authorized_force_id'])
assert result['result']=='PRECHECK_PASS' and not result['applied_to_game']
try:
    validate_reward(inputs['command'],inputs['context'],wire['bindings']['A']['force_id'])
except PreflightError:
    wrong_player_rejected=True
else:
    raise AssertionError('Host binding incorrectly authorized the guest reward')
report={'result':'PASS','source':'TLS room binding -> existing authority_reward.validate_reward',
        'viewer_force_id':inputs['context']['viewer_force_id'],
        'bound_player':authority['player_id'],'authorized_force_id':authority['authorized_force_id'],
        'main_district_id':authority['main_district_id'],'selected_officers':result['selected_officers'],
        'expected_costs':result['expected_costs'],'host_cannot_authorize_guest_reward':wrong_player_rejected,
        'context_source':'Read-only game sample captured at room-catalog preparation; replayed offline for this validation',
        'native_callback_recheck_required':True,'commands_executed':0,'two_game_clients_connected':False}
(OUT/'房间绑定与赏赐预检对接.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('selected_officers','expected_costs')},ensure_ascii=True))
