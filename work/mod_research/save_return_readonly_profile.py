"""Small read-only profile for a normal menu-return observation; never hooks."""
from pathlib import Path
from datetime import datetime
import json,struct,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'outputs'/'san14-link'))
from battle_observer import BattleObserver
from startup_identity_reader import capture_startup_context
from start_startup_switch import no_debugger


def capture(reader):
    no_debugger(reader)
    m=reader.memory; b=m.base
    q=lambda p:struct.unpack('<Q',m.read(p,8))[0]
    d=lambda p:struct.unpack('<I',m.read(p,4))[0]
    i=lambda p:struct.unpack('<i',m.read(p,4))[0]
    start=capture_startup_context(reader)
    assert start['snapshot']['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'],'Stable planning stack required'
    stack=q(b+0x19E7310+0x20);user=q(stack+32);game=q(stack+16)
    ui=q(user+0x478);panel=q(game+0x480)
    cache=q(b+0x2025318);special=q(b+0x201EC70)
    methods={name:hex(q(b+0x12CC4A8+offset)-b) for name,offset in
             [('resume',0x18),('pause',0x20),('update',0x28),('enter_event',0x58),('exit_event',0x60)]}
    assert methods=={'resume':'0x3f5530','pause':'0x3f5920','update':'0x3f9b00','enter_event':'0x3f7710','exit_event':'0x3f7a70'},'Original User methods required'
    assert q(b+0x12DC5F8+0x28)==b+0x4AA650,'Original Save update required'
    profile={'context':start,'base':hex(b),'user':hex(user),'game':hex(game),'methods':methods,
             'user_phase':d(user+0x470),'selected':[hex(q(user+o)) for o in (0x4a8,0x4b0,0x4b8)],
             'pending_menu':i(ui+0x88),'advance_game':d(game+0x47c),'advance_panel':d(panel+0x1b0),
             'pending_state_count':q(b+0x19E7310+0x30),
             'cache':{'mode':i(cache+8),'pending':i(cache+0x3ec),'count':q(cache+0x18)},
             'special_context':{'pointer':hex(special),'value':d(special) if special else None},
             'game_writes':0,'no_debugger':True,'native_gameplay_enabled':False}
    assert start==capture_startup_context(reader),'Changed during profile'
    assert profile['user_phase']==2 and profile['pending_menu']==-1
    assert profile['advance_game']==profile['advance_panel']==profile['pending_state_count']==0
    return profile


if __name__=='__main__':
    r=BattleObserver()
    try: result=capture(r)
    finally:r.close()
    path=ROOT/('save_return_readonly_profile_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with path.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'evidence':str(path),'date':result['context']['snapshot']['date'],
                      'selected':result['selected'],'special_context':result['special_context'],
                      'game_writes':0,'pending_menu':result['pending_menu']},ensure_ascii=False))
