"""Publish this round's real-game result separately from owned-process work."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

P=Path(__file__).resolve().parent
OUT=P.parents[1]/'outputs/san14-link'
PARTS={
 'real_game_forwarding':('human_rules_live_forwarding_handoff.json','08c8ff13d3fe5f145da7695d0a49a9f7424404e4ffdd31fe9d38598a6a5cb9a2'),
 'bound_publisher':('human_rules_bound_publish_handoff.json','97ec1b89952b8c8dc9639903e04fdf3cee03d4a5c4744789e342cf9effa22eea'),
 'publisher_review':('human_rules_bound_publish_independent_review.json','6a2a98575e5eaf3df8d4e31cbf73855c502bd34c500ddb05b1250b0f2059824f'),
 'planning_dispatcher':('checkpoint_planning_dispatcher_handoff.json','95c65ec4cb3a94bba481ba93567bd0a6813e3262ab47a67f0a3dcc6a00279ff1'),
 'load_activation':('checkpoint_task_native_activation_handoff.json','14ddc626247afe1cc04174813bf66f79d3253cfff0dcb8196688db3de43e49b5'),
 'load_bind_start':('checkpoint_task_native_start_handoff.json','a0db49a0a3c6ac3689dbe06d4fc85d013fc64e77a835e513949c5fafc76c9a16'),
 'rules_stage':('human_rules_policy_stage_handoff.json','cb179fabfb2a67d458afc7fb242678817bf7ffff3157e10b3ceeb71b533cbf3f'),
}


def read(path):return json.loads(path.read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def ref(path):return {'path':str(path.resolve()),'sha256':sha(path)}
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def main():
    parts={}
    for key,(name,digest) in PARTS.items():
        path=P/name
        assert sha(path)==digest,name
        parts[key]={'handoff':ref(path),'claims':read(path)}
    live=parts['real_game_forwarding']['claims']
    for item in live['references'].values():
        assert sha(Path(item['path']))==item['sha256'],item['path']
    assert live['total_entry_calls']==816 and not live['final_source_patches_present']
    native_start=parts['load_bind_start']['claims']
    assert native_start['cases']==5 and not native_start['actual_game_publication']
    assert sha(P/native_start['result_path'])==native_start['result_sha256']
    start_result=read(P/native_start['result_path'])
    assert start_result['result']=='PASS' and len(start_result['cases'])==5
    assert all(case['passed'] and case['failures']==0 for case in start_result['cases'])
    for name,digest in native_start['files_sha256'].items():
        assert sha(P/name)==digest,name
    stamp=datetime.now().astimezone().isoformat(timespec='seconds')
    history=P/'three_gate_reports'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');history.mkdir(parents=True)
    report_path=OUT/'三个门槛接入证据.json'
    shutil.copy2(report_path,history/'prior-evidence.json')
    prior_user_report=OUT/'实机整旬转发验证.txt'
    if prior_user_report.exists():shutil.copy2(prior_user_report,history/'prior-user-report.txt')
    report=read(report_path)
    report.update(schema='san14.three-gate-integration.v4',updated=stamp,
        previous_report=ref(history/'prior-evidence.json'),real_native_round=parts,
        real_six_entry_publication_verified=True,real_six_entry_forwarding_verified=True,
        real_native_entry_calls=816,two_human_rules_live=False,
        all_three_gates_passed=False,two_real_periods=False,two_real_clients_playable=False,
        native_input_hold_installed=False,full_world_verified=False,ai_installed_in_game=False,
        final_six_sources_restored=True,final_debugger_attached=False,final_stage_module_retained=True,
        this_round_game_access=True,this_round_game_injection=True,
        this_round_source_patch_transactions=4,agent_requested_native_game_commands=0,
        user_advanced_native_periods=1,this_round_user_action_required=False,
        remaining=[
            'Connect verified room/shared-settings and a game-safe fault Hold to one-time pre-publication two-human rule activation; then validate actual bypass/income.',
            'Integrate the owned-process-verified native Load bind/start publisher with the actual resident owner; complete Title and parent join/closure ports and validate repeatable loading in game.',
            'Wire planning dispatcher to actual retained native callback and world lifetime; complete or explicitly constrain UI input coverage and real Ready/drain acknowledgments.',
            'Produce two different fresh host period checkpoints, synchronize both to the same guest process, restore its faction and verify the complete world.',
            'Validate map cover and remote-PC connectivity; first test two controlled empty-order periods, then add reward and sortie commands.'])
    # The earlier zero-write round fields do not describe this real installation.
    report.pop('this_round_game_writes',None);report.pop('this_round_game_calls',None)
    write(report_path,report)
    text=f'''实机接入与双人测试进展（{stamp}）

本轮关键进展：六个入口第一次在真实游戏中完成整旬转发验证，并已恢复原指令；用户也已读回34号档。

真实游戏验证
游戏从203年8月中旬推进到下旬，不新增命令。工具记录到势力入口11次、军团入口14次、部队入口50次、编组入口45次，两处收入判断各348次，共816次。所有进入均对应正常返回，活动调用、异常和意外收入调用来源均为0。
这次调用来自真正的游戏和真实业务函数。它验证了安装方式、函数转接和恢复流程；规则保持原行为，尚未启用两名人类势力保护，也不能据此声称同未插桩的一旬结果完全相同。
安装和恢复均检查了102个游戏线程，六处入口完整恢复，调试器已退出。诊断DLL与跳板保留在内存直到游戏退出，当前没有这六处活动补丁。
用户正常推进时更新了autosdexSC07.s14自动存档；34号档未变。恢复34后，已覆盖记录与地图格恢复一致，仅显示对象等运行期指针重建。不是完整世界核验。

同时完成的开发
1. 双人AI/收入规则组合：7项独立进程测试通过。双方主军团跳过AI决策，委任军团及其他势力保留原逻辑；两处收入判断对双方统一，其他菜单调用继续使用各自视角。已处理收入入口必须保留原调用位置的问题。生产启用尚需连接真实房间和设置检查、空闲阶段证明与故障暂停处理；没有用虚构凭据放行。
2. 加载线程接线：自动在原生运行器之前开启四点捕获，并在正常或异常返回时恢复；4项独立进程测试通过，每项两代。进一步完成首次加载的绑定、启动捕获与线程入口替换，另外5项独立进程测试通过。替换前会核对工作线程仍停在指定等待位置、任务身份和原入口；默认只观察，显式开启后才替换。代码尚未安装到真实游戏，父任务收尾与Title等来源仍需接通。
3. 规划与赏赐接线：18项六入口包装/收尾及实际DLL组合测试通过。每次在游戏回调对应线程中同步构造、执行并回收赏赐参数，允许不同工作线程接续处理。局部等待和排空来自实际回调收尾；主规划回调之外仍有菜单输入路径，不能宣称完整输入锁。

距离双人测试的实际门槛
一、让双方势力保护规则在真实游戏中启用，确认AI不会替玩家下令、收入判断一致。
二、把房间准备状态与真实输入/命令收尾接通，并完成常驻加载中父任务与Title的接线。
三、A产生本轮新档，B在同一进程连续接受两份不同的新旬末档、保留自己的势力，且完成世界比对。
四、接通异地两机并验证等待画面；先做两旬不下新命令的受控测试，再加入赏赐、出征等命令。

我们已经跨过“六入口只能在测试进程里运行”的门槛。完整双人循环仍未通过，不提供虚假的完成百分比，也尚不能交付可玩双人版。本轮游戏测试已收尾，暂不需要继续手动操作。
'''
    for name in ('三个门槛接入进展.txt','双机测试准备进展.txt','开发剩余工作评估.txt','实机整旬转发验证.txt'):
        (OUT/name).write_text(text,encoding='utf8')
    resume=P/'mainline_20261007_live_resume.json';state=read(resume)
    state.update(three_gate_integration_report=ref(report_path),
        real_native_round={key:item['handoff'] for key,item in parts.items()},
        pending_user_action=None,next_concrete_integration=report['remaining'])
    write(resume,state)
    receipt=dict(result='PUBLISHED_REAL_GAME_FORWARDING_PROGRESS',report=ref(report_path),
                 user_report=ref(OUT/'实机整旬转发验证.txt'),pending_user_action=None)
    write(history/'publication.json',receipt)
    print(json.dumps(receipt,ensure_ascii=True))


if __name__=='__main__':main()
