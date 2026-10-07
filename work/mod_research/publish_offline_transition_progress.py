"""Publish audited offline progress. Never opens game/process/window/save paths."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'outputs'/'san14-link'

def latest_checked(directory):
    path=sorted((HERE/directory).glob('*/result.json'))[-1]
    r=json.loads(path.read_text(encoding='utf-8'))
    assert r['result']=='PASS',path
    for name,expected in r['source_sha256'].items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==expected,(path,name)
    return path,r

session_path,session=latest_checked('checkpoint_guest_native_session_fixtures')
visual_path,visual=latest_checked('checkpoint_visual_client_runs')
flow_path,flow=latest_checked('checkpoint_guest_transition_runs')
assert all(c['passed'] and not c['game_access'] for c in session['cases'])
assert visual['own_helper']['passed'] and not visual['game_access']
assert not flow['real_game_access']
stamp=datetime.now().astimezone().isoformat()
report={
    'schema':'san14.offline-transition-progress.v1','updated_at':stamp,
    'user_constraint':'No game interaction until user returns; this turn uses workspace archives and own fixtures only.',
    'real_game_access_this_turn':False,'steam_save_directory_access_this_turn':False,
    'game_window_capture_or_activation_this_turn':False,'live_loader_installed':False,
    'session_cases':len(session['cases']),'visual_tests':visual['tests_run'],
    'own_cross_process_visual_cycle':True,'controller_tests':flow['tests_run'],
    'evidence':{'session':str(session_path),'visual':str(visual_path),'controller':str(flow_path)},
    'verified_sources':{**session['source_sha256'],**visual['source_sha256'],**flow['source_sha256']},
    'missing_live_components':['NativePort IPC and target/profile installer',
        'native input barrier throughout teardown/rebuild and neutral release',
        'full semantic shared-world verifier and fresh planning/camera observation',
        'trusted actual-game presentation provider','normal menu cancellation and post-load hook lifecycle',
        'repeatable multi-period session ownership',
        'two real game clients completing period loop'],
    'b_load_latency_measured':False,'native_gameplay_enabled':False,
    'morning_action_required_now':False,
}
(OUT/'离线开发进展与明早验证.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
text=f'''离线开发进展与明早验证
更新：{stamp}

你不在家期间，本轮只使用工作区已有归档和我们自己创建的测试进程/窗口，没有访问正在运行的游戏、控制游戏窗口或读写Steam存档目录。今晚不需要你操作。

本轮实际完成

1. 原生加载会话模块
把加载请求、实际文件读取核验、加载结束观察、B身份恢复和六个函数入口登记接到了同一个C++会话中。现在由共用会话实现配置与分发，测试不再另外写一套分发逻辑。先安装观察入口，之后才能排队打开原生菜单并绑定本次菜单对象。
生产版本编译通过；{len(session['cases'])}个独立进程场景通过，包含正常早/晚身份恢复、文件不符、原生替身异常、请求前停止、请求已经提交后停止。提交后即使结果不明也保留观察，不自动重试或撤销身份。
这些是合成游戏对象上的真实指针安装、文件核验和原子提交；世界反序列化等游戏函数为替身。模块没有注入游戏，不能据此称真实读档已通过。

2. 等待画面助手的控制客户端
已实现持续收发、消息编号和进程身份核对、超时/断管处理、明确撤罩和退出操作。读取助手失败不会自动撤罩或放行游戏输入。
{visual['tests_run']}项协议与组合测试通过，并用我们自己的两个进程完成一次真实旧图保留、新图捕获、撤罩循环。截图只证明捕获到像素；游戏能否操作、是否真正回到地图，要另有原生观察依据。

3. 旬末同步总控制器
已经复用现有房间状态、持久日志、画面门和新画面客户端，把以下顺序串起来：
已验证的检查点 → 原生输入等待 → 保留旧地图 → 持久记录一次性加载意图 → 发起一次加载 → 观察完成 → 核对共享世界与B身份 → 准备新地图 → 再核对双方 → 撤罩 → 清空遗留输入并确认放行 → 接受下一轮命令。
{flow['tests_run']}项组合测试通过，覆盖重复启动、重启后旧加载意图、超时、迟到结果、断线、错误势力、只提供部分世界样本、等待期间世界变化，以及撤罩/输入放行时助手失联。
控制器不会仅凭房间显示“内政阶段”就接单：画面与输入确认都完成后，才允许准备和本地命令。异常时保留诊断，不自动再读一次档。

还缺的关键接口

Python总控制器与C++会话之间的真实通信、目标版本/进程绑定及安装器还未接通；输入拦截必须贯穿旧世界销毁和新世界创建，并在撤罩后等待新的中性输入周期，不能把一张旧地图盖在可操作的游戏上。
提交加载前取消时，恢复函数入口并不会自动关闭已打开的原生菜单，仍需接入正常取消和返回地图观察；提交加载后的最终钩子清理也要等真实终态核验后实现。
还缺完整共享世界的验证、新规划状态/镜头观察和真实游戏画面证据。文件SHA一致、B君主字段正确、已有783条对象或48400个地格抽查，都不能单独替代完整世界验证。
当前原生会话仍针对固定测试存档与身份配置，用于单次受控加载；连续多旬复用和多版本/多势力泛化尚未完成。后续仍需接上两个人类势力规则、持续命令捕获、正式事件等待和双机连续运行。
因此现在不是可分发联机MOD，也不能报告B完整加载耗时或保证不闪读档页面。

明早优先验证顺序

先只恢复窗口/无边框的大地图并确认起点。第一项安排真实游戏窗口的旧图保持与撤罩：不推进、不出征、不赏赐、不选存档槽。检查是否出现黑屏、遮罩位置是否正确、撤去后界面是否正常。
随后只有在上述真实接口与恢复条件接齐后，才进行一次受控“同步档加载 → B身份 → 新地图”测试，并分段记录传输、原生加载和画面恢复时间。准备期间无需你反复操作。
最后再安排真正双客户端的无新增命令一旬及下一旬；此前的独立测试不能代替这一关。
尽量把需要你观察的项目集中成一轮，但不预先承诺一轮就能验证所有未接通接口。今晚没有需要回复的测试口令，也没有后台等待你操作的游戏钩子由本轮启动。

本轮源文件与完整结果清单见同名JSON。各阶段失败/不完整的历史日志保留，未改写成成功。
'''
(OUT/'离线开发进展与明早验证.txt').write_text(text,encoding='utf-8')
prefix='最新进展（离线开发，2026-10-07）：用户离家，本轮不访问游戏或Steam存档目录。统一原生会话、画面助手客户端和旬末总控制器已通过独立测试；真实通信/输入屏障/完整世界与地图观察仍待接入。此前“等待恢复窗口”的请求暂不执行，明早再集中安排实机验证。最新说明见《离线开发进展与明早验证.txt》。\n\n以下是此前阶段记录，涉及当时的待办与实测结论，以各段时间为准。\n\n'
for name in ('开发剩余工作评估.txt','B端加载串联进展.txt'):
    p=OUT/name
    old=p.read_text(encoding='utf-8-sig')
    if not old.startswith(prefix):p.write_text(prefix+old,encoding='utf-8')
contract_path=HERE/'checkpoint_load_integration_contract.json'
contract=json.loads(contract_path.read_text(encoding='utf-8'))
contract['offline_integration']={
    'unified_native_session_implemented':True,'session_cases':len(session['cases']),
    'visual_client_and_bridge_implemented':True,'controller_implemented':True,
    'controller_tests':flow['tests_run'],'live_native_port_implemented':False,
    'live_input_barrier_implemented':False,'full_world_and_presentation_provider_implemented':False,
    'real_game_access_this_turn':False,'report':str(OUT/'离线开发进展与明早验证.json')}
contract['latest_evidence_report']=str(OUT/'离线开发进展与明早验证.json')
contract_path.write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'published':str(OUT/'离线开发进展与明早验证.txt'),
                  'session_cases':len(session['cases']),'visual_tests':visual['tests_run'],
                  'controller_tests':flow['tests_run'],'sources_rehashed':True},ensure_ascii=False))
