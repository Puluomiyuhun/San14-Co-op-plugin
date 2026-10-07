"""Build an explicitly actor-scoped preflight alongside the legacy local-player API."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'outputs/san14-link'
source=(OUT/'reward_preflight.py').read_text(encoding='utf-8')
source=source[:source.index('\ndef main():')]
source=source.replace('Read-only command preflight for city-funded reward in the locked build.',
'''Read-only authority-side reward preflight for an explicitly bound actor faction.
The viewer remains the actual local player. This module never changes it.
The caller supplies authority from a trusted session, never from packet claims.''')
source=source.replace('def capture_context(reader):','def capture_context(reader, actor_force_id):\n    require(type(actor_force_id) is int and 1<=actor_force_id<=51, "authorization", "命令势力编号无效")')
old="    player=snapshot['player']['force_id'];ruler=snapshot['player']['ruler_id']"
new="""    player=actor_force_id
    force_object=d.ptr(d.root+0xDCA0+player*8)
    d.require_type(force_object,'CForceData')
    ruler=d.uint(force_object+0x10,2)
    require(1<=ruler<6000,'actor_force','势力没有有效君主')"""
assert old in source;source=source.replace(old,new)
source=source.replace('current_player_force_id','command_force_id')
source=source.replace("'date':snapshot['date'],'command_force_id':player,'ruler_id':ruler,",
                      "'date':snapshot['date'],'command_force_id':player,'viewer_force_id':snapshot['player']['force_id'],'ruler_id':ruler,")
source=source.replace('san14.reward-preflight-context.v1','san14.authority-reward-context.v1').replace('san14.reward-preflight-command.v1','san14.authority-reward-command.v1')
source=source.replace("    require(type(command) is dict and set(command)==keys,'command_shape','命令字段不符')",
"""    require(type(command) is dict and set(command)==keys,'command_shape','命令字段不符')
    require(context.get('schema')=='san14.authority-reward-context.v1','context_schema','主机预检上下文版本不符')
    require(type(context.get('viewer_force_id')) is int and 1<=context['viewer_force_id']<=51,'viewer_context','本机观察势力无效')""")
source=source.replace('本预检只支持当前本机玩家，不能由命令自行声明其他势力权限','命令必须属于会话绑定的势力，不能由命令自行声明其他势力权限')
source=source.replace('未找到当前势力的主军团','未找到命令势力的主军团').replace('不属于当前玩家','不属于授权势力')
source=source.replace('whole_current_player_force','whole_authorized_force')
source=source.replace("'applied_to_game':False,'replay_supported':False,'full_command_legality_verified':False,",
                      "'viewer_force_id':context['viewer_force_id'],'authorized_force_id':authorized_force_id,\n            'applied_to_game':False,'replay_supported':False,'full_command_legality_verified':False,")
source+='''
def main():
    parser=argparse.ArgumentParser(description='读取各势力赏赐权限与预计消耗，不执行游戏命令。')
    parser.add_argument('--forces',type=int,nargs='+',default=[12,2])
    parser.add_argument('--output',type=Path,default=Path(__file__).with_name('双方赏赐预检.json'))
    args=parser.parse_args()
    require(len(args.forces)==len(set(args.forces)) and 1<=len(args.forces)<=51,'authorization','势力列表重复或过长')
    reader=GameReader()
    try:
        contexts=[capture_context(reader,force) for force in args.forces]
        assert contexts==[capture_context(reader,force) for force in args.forces], '采样期间状态变化'
        previews=[]
        for c in contexts:
            ids=eligible_ids(c,c['main_district_id'])
            command=make_command(c,c['main_district_id'],ids)
            if ids:
                try:preview=validate_reward(command,c,c['command_force_id'])
                except PreflightError as e:preview={'result':'REJECTED','code':e.code,'reason':str(e),'applied_to_game':False}
            else:preview={'result':'NO_ELIGIBLE_OFFICERS','applied_to_game':False}
            previews.append({'force_id':c['command_force_id'],'viewer_force_id':c['viewer_force_id'],
                             'main_district_id':c['main_district_id'],'eligible_officer_ids':ids,'preview':preview})
        result={'mode':'read-only-authority-preflight','contexts_are_atomic':False,'previews':previews,'applied_to_game':False}
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
        print('只读检查完成，未执行赏赐。游戏当前控制势力保持不变。')
        for row in previews:
            print('势力 '+str(row['force_id'])+'：候选 '+str(len(row['eligible_officer_ids']))+' 人；'+row['preview']['result'])
        print(str(args.output.resolve()))
    finally:reader.close()

if __name__=='__main__':main()
'''
(OUT/'authority_reward.py').write_text(source,encoding='utf-8')
test=(ROOT/'test_reward_preflight.py').read_text(encoding='utf-8').replace('from reward_preflight import','from authority_reward import').replace('current_player_force_id','command_force_id')
test=test.replace('san14.reward-preflight-context.v1','san14.authority-reward-context.v1')
test=test.replace("'command_force_id':12", "'viewer_force_id':12,'command_force_id':12")
test=test.replace("'reward-preflight-fixtures.json'","'authority-reward-fixtures.json'")
extra='''
    def test_foreign_actor_keeps_real_viewer(self):
        self.context['viewer_force_id']=2;self.refresh()
        result=validate_reward(self.command,self.context,12)
        self.assertEqual(result['viewer_force_id'],2)
        self.assertEqual(result['authorized_force_id'],12)
    def test_viewer_token_cannot_authorize_foreign_actor(self):
        self.context['viewer_force_id']=2;self.refresh();self.reject('authorization',authority=2)
    def test_legacy_context_is_not_actor_context(self):
        self.context['schema']='san14.reward-preflight-context.v1';self.refresh();self.reject('context_schema')
    def test_bad_viewer_rejected(self):
        self.context['viewer_force_id']=True;self.refresh();self.reject('viewer_context')
'''
test=test.replace("\nif __name__=='__main__':",extra+"\nif __name__=='__main__':")
(ROOT/'test_authority_reward.py').write_text(test,encoding='utf-8')
print('Generated separate actor-scoped preflight and 34 authorization/resource checks')
