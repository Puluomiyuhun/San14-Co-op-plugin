"""Read-only command preflight for city-funded reward in the locked build.

Passing this check is NOT execution support. The native caller must eventually
recheck on the game thread; UI refresh and recovery have not been validated.
No injection, writes, sockets or game function calls are used by this module.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from domestic_reader import DomesticDecoder
from game_reader import GameReader, SUPPORTED_SHA256
from reward_eligibility import capture_eligibility, pool_values

PLANNING_STACK=['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']

class PreflightError(ValueError):
    def __init__(self,code,message):super().__init__(message);self.code=code

def require(ok,code,message):
    if not ok:raise PreflightError(code,message)

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')

def context_hash(context):
    return hashlib.sha256(canonical({k:v for k,v in context.items() if k!='context_sha256'})).hexdigest()

def capture_context(reader):
    snapshot=reader.snapshot();eligibility=capture_eligibility(reader)
    d=DomesticDecoder(reader);base=d.memory.base
    district_table={d.ptr(d.root+0xDE40+i*8):i for i in range(1,52)}
    ordered=pool_values(d,d.root+0xC8,0x123F3F8,0x201D3A0,0x14000,51,8)
    districts={};main=0
    player=snapshot['player']['force_id'];ruler=snapshot['player']['ruler_id']
    for address in ordered:
        d.require_type(address,'CDistrictData')
        require(address in district_table,'district_identity','军团名单与对象表不符')
        identity=district_table[address];data=d.read(address+0x10,8)
        force=data[0];leader=int.from_bytes(data[2:4],'little')
        row={'id':identity,'force_id':force,'kind_raw':data[1],'leader_id':leader,
             'action_points':data[4],'valid':bool(force and data[1] and leader)}
        districts[identity]=row
        # 0x20C110 returns the first matching district in the native list order.
        if not main and force==player and (leader==ruler or data[1]==1):main=identity
    require(main!=0,'main_district','未找到当前势力的主军团')
    footholds=pool_values(d,d.root+0x78,0x123F3B8,0x201D3A0,0x14000,128,8)
    foothold_map={}
    for address in footholds:
        d.check_pointer(address);identity=d.uint(address+0x4E,2)
        require(identity not in foothold_map,'foothold_identity','据点编号重复')
        foothold_map[identity]=address
    people={p['id']:p for p in eligibility['persons']};funding={}
    for identity,row in districts.items():
        if row['force_id']!=player or not row['valid']:continue
        leader=people.get(row['leader_id'])
        require(leader is not None,'district_leader','军团长不在有效武将列表')
        address=foothold_map.get(leader['location_id'])
        if not address or d.uint(address,8)!=base+0x129FD10:
            funding[identity]={'supported':False,'reason':'付款据点不是当前支持的城市类型'}
            continue
        city=d.city_at(address);vt=d.uint(address,8)
        require(d.uint(vt+0x80,8)==base+0x209A00 and d.uint(vt+0x90,8)==base+0x20C2E0,
                'city_accessors','城市军团或资金读取函数不符')
        funding[identity]={'supported':True,'leader_id':leader['id'],'leader_force_id':leader['force_id'],
                           'leader_location_id':leader['location_id'],'city':city}
    top=reader.state_objects()[-1]
    mode=d.uint(top[1]+0x470) if top[0]=='CUserStrategyState' else None
    cost=d.uint(base+0x18ECF30)
    # Reconcile both samplers before accepting one context token.
    require(eligibility==capture_eligibility(reader),'sampling_changed','武将或任务在采样期间发生变化')
    d.verify_stable()
    require(snapshot==reader.snapshot(),'sampling_changed','日期、势力或界面在采样期间发生变化')
    context={'schema':'san14.reward-preflight-context.v1','game_sha256':reader.sha256,
             'date':snapshot['date'],'current_player_force_id':player,'ruler_id':ruler,
             'state_stack':snapshot['state_stack'],'strategy_mode':mode,'main_district_id':main,
             'districts':list(districts.values()),'funding':{str(k):v for k,v in funding.items()},
             'persons':eligibility['persons'],'native_action_cost':cost,
             'person_records_sha256':eligibility['person_records_sha256'],
             'task_fields_sha256':eligibility['task_fields_sha256']}
    context['context_sha256']=context_hash(context)
    return context

def eligible_ids(context,district_id):
    force=context['current_player_force_id']
    wide=district_id==context['main_district_id']
    return [p['id'] for p in context['persons'] if p['force_id']==force and 1<=p['rank_raw']<=4
            and (wide or p['district_id']==district_id) and p['predicate_eligible']]

def make_command(context,district_id,ids):
    funding=context['funding'].get(str(district_id),{})
    return {'schema':'san14.reward-preflight-command.v1','game_sha256':context['game_sha256'],
            'context_sha256':context['context_sha256'],'date':context['date'],
            'force_id':context['current_player_force_id'],'district_id':district_id,
            'funding_city_id':funding.get('city',{}).get('id',0),'officer_ids':list(ids)}

def validate_reward(command,context,authorized_force_id):
    keys={'schema','game_sha256','context_sha256','date','force_id','district_id','funding_city_id','officer_ids'}
    require(type(command) is dict and set(command)==keys,'command_shape','命令字段不符')
    require(command['schema']=='san14.reward-preflight-command.v1','schema','命令版本不符')
    require(command['game_sha256']==context['game_sha256']==SUPPORTED_SHA256,'game_version','游戏版本不符')
    require(type(authorized_force_id) is int and 1<=authorized_force_id<=51,'authorization','无效的授权势力')
    require(context['context_sha256']==context_hash(context),'context_integrity','预检状态摘要不符')
    require(type(command['context_sha256']) is str and re.fullmatch('[0-9a-f]{64}',command['context_sha256']) is not None
            and command['context_sha256']==context['context_sha256'],'stale_context','命令基于不同或过期状态')
    require(command['date']==context['date'],'wrong_turn','命令日期不符')
    require(context['state_stack']==PLANNING_STACK and context['strategy_mode']==2,'wrong_phase','请停在可下令的大地图')
    for key in ('force_id','district_id','funding_city_id'):
        require(type(command[key]) is int and 1<=command[key]<=51,'identity','势力、军团或城市编号无效')
    require(command['force_id']==authorized_force_id==context['current_player_force_id'],
            'authorization','本预检只支持当前本机玩家，不能由命令自行声明其他势力权限')
    districts={d['id']:d for d in context['districts']}
    district=districts.get(command['district_id'])
    require(district is not None and district['valid'] and district['force_id']==authorized_force_id,
            'district_owner','操作军团无效或不属于当前玩家')
    funding=context['funding'].get(str(district['id']))
    require(funding is not None and funding['supported'],'unsupported_funding','当前只支持由城市付款的赏赐')
    city=funding['city'];charged=districts.get(city['district_id'])
    require(funding['leader_id']==district['leader_id'] and funding['leader_force_id']==authorized_force_id
            and funding['leader_location_id']==city['foothold_id'],'funding_origin','付款位置与军团长上下文不符')
    require(command['funding_city_id']==city['id'],'funding_city','不能自行指定其他付款城市')
    require(city['force_id']==authorized_force_id and charged is not None and charged['valid']
            and charged['force_id']==authorized_force_id,'funding_owner','付款城市或扣行动军团归属不符')
    ids=command['officer_ids']
    require(type(ids) is list and 1<=len(ids)<=6000 and all(type(i) is int and 1<=i<6000 for i in ids),
            'officer_ids','需要非空且有效的武将编号列表')
    require(len(ids)==len(set(ids)),'duplicate_officer','同一条命令不能重复赏赐一名武将')
    people={p['id']:p for p in context['persons']}
    wide=district['id']==context['main_district_id']
    selected=[]
    for identity in ids:
        person=people.get(identity)
        require(person is not None and person['native_valid'],'officer_identity','武将无效或不在有效人员列表')
        require(person['force_id']==authorized_force_id,'officer_owner','不能赏赐其他势力的武将')
        require(1<=person['rank_raw']<=4 and (wide or person['district_id']==district['id']),
                'menu_scope','武将不属于该军团菜单的选择范围')
        require(person['predicate_eligible'],'officer_ineligible',f"{person['name']}未通过赏赐人员规则：{person['rejection_reason']}")
        selected.append(person)
    cost=context['native_action_cost']
    require(type(cost) is int and cost==1,'action_cost','行动力消耗与已核对版本不符')
    gold_cost=100*len(ids)
    require(city['gold']>=gold_cost,'insufficient_gold','付款城市金钱不足')
    require(charged['action_points']>=cost,'insufficient_actions','扣行动力的军团行动力不足')
    return {'result':'PRECHECK_PASS','mode':'read-only-no-execution','command':command,
            'selection_scope':'whole_current_player_force' if wide else 'context_district_only',
            'selected_officers':[{'id':p['id'],'name':p['name'],'loyalty_before':p['loyalty']} for p in selected],
            'expected_costs':{'funding_city_id':city['id'],'funding_city_name':city['name'],
                              'gold':gold_cost,'gold_before':city['gold'],'gold_if_executed':city['gold']-gold_cost,
                              'charged_district_id':charged['id'],'action_points':cost,
                              'actions_before':charged['action_points'],'actions_if_executed':charged['action_points']-cost},
            'applied_to_game':False,'replay_supported':False,'full_command_legality_verified':False,
            'execution_requirements_remaining':['Recheck identity, scope, eligibility and resources on native callback',
                                                'Validate native reward effects, UI refresh and native recovery',
                                                'Integrate authenticated session ownership and deduplicated execution']}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--district',type=int)
    parser.add_argument('--officers',type=int,nargs='+')
    parser.add_argument('--command-file',type=Path)
    parser.add_argument('--output',type=Path,default=Path(__file__).with_name('最近一次赏赐预检.json'))
    args=parser.parse_args();reader=None
    try:
        reader=GameReader();context=capture_context(reader)
        if args.command_file:
            require(args.command_file.stat().st_size<=65536,'command_shape','命令文件过大')
            command=json.loads(args.command_file.read_text(encoding='utf-8'))
        else:
            district=args.district if args.district is not None else context['main_district_id']
            command=make_command(context,district,args.officers if args.officers is not None else eligible_ids(context,district))
        result=validate_reward(command,context,context['current_player_force_id'])
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
        cost=result['expected_costs']
        print('只读预检通过；未执行赏赐。')
        print('候选：'+ '、'.join(p['name'] for p in result['selected_officers']))
        print(f"若执行：{cost['funding_city_name']}扣{cost['gold']}金，军团{cost['charged_district_id']}扣{cost['action_points']}行动。")
        print('结果：'+str(args.output.resolve()))
    except (PreflightError,RuntimeError,OSError,ValueError) as error:
        result={'result':'REJECTED','code':getattr(error,'code','capture_error'),'reason':str(error),
                'applied_to_game':False,'replay_supported':False}
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True));raise SystemExit(1)
    finally:
        if reader:reader.close()

if __name__=='__main__':main()
