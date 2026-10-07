"""Publish the bounded second-force experiment; never opens or mutates the game."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs' / 'san14-link'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    native = read(ROOT / 'second-force-reward-live-latest.json')
    network = read(ROOT / 'second-force-network-live-latest.json')
    dry = read(ROOT / 'second-force-reward-dry-latest.json')
    post = read(Path(network['directory']) / 'post-duplicate-check.json')
    authority_tests = read(ROOT / 'authority-reward-fixtures.json')
    native_tests = read(ROOT / 'second-force-reward-fixtures.json')
    network_tests = read(ROOT / 'second-force-network-fixtures.json')
    ai = read(ROOT / 'ai-dispatch-handoff' / 'index.json')
    assert all(r['result'] == 'PASS' for r in [native, network, dry, post, authority_tests, network_tests])
    assert len(native_tests) == 25 and all(r['passed'] for r in native_tests)
    assert authority_tests['tests_run'] == 34 and network_tests['count'] == 21
    assert network['native_submit_calls'] == native['execution']['submit_calls'] == 1
    assert native['viewer_force_id'] == 12 and native['command_force_id'] == 2
    assert post['duplicate_did_not_reapply'] and post['original_strategy_update_restored']
    restored = native.get('restore_verified', False)
    restoration = native.get('restoration') if restored else {'result': 'PENDING_USER_NATIVE_LOAD'}
    sources = [
        ROOT / 'second-force-reward-live-latest.json', ROOT / 'second-force-network-live-latest.json',
        ROOT / 'second-force-reward-dry-latest.json', Path(network['directory']) / 'post-duplicate-check.json',
        ROOT / 'authority-reward-fixtures.json', ROOT / 'second-force-reward-fixtures.json',
        ROOT / 'second-force-network-fixtures.json', ROOT / 'ai-dispatch-handoff' / 'index.json',
        ROOT / 'second_force_reward_network.py', ROOT / 'second_force_reward_pilot.cpp',
        ROOT / 'second_force_reward_guard.inc', ROOT / 'second_force_reward_pilot.h',
        ROOT / 'run_second_force_reward.py', OUT / 'authority_reward.py',
        OUT / '查看双方命令权限.cmd',
    ]
    evidence = {
        'schema': 'san14.second-force-command-milestone.v1',
        'created': datetime.now().astimezone().isoformat(),
        'result': 'EXECUTION_PASS_RESTORE_PASS' if restored else 'EXECUTION_PASS_RESTORE_PENDING',
        'scope': 'One actual game, two local TCP processes, one fixed reward command for non-viewer force 2.',
        'game_sha256': native['command']['game_sha256'],
        'current_viewer_force_id': 12, 'command_force_id': 2,
        'player_identity_switched': False, 'native_submit_calls': 1,
        'native_common_reward_handler_rva': '0x1d6da0',
        'game_thread_callback_used': True,
        'native_effects': native['effects'],
        'native_adapter': native['adapter'],
        'network': {k: network[k] for k in [
            'transport', 'sender_pid', 'receiver_pid', 'network_packets',
            'native_submit_calls', 'wrong_faction_rejected', 'duplicate_cached',
            'changed_id_content_rejected', 'two_real_games', 'other_client_state_replication']},
        'post_duplicate_live_check': post,
        'restore_verified': restored, 'restoration': restoration,
        'tests': {'authority_preflight': authority_tests, 'native_fixture': native_tests,
                  'network_synthetic_executor': network_tests},
        'ai_gate_offline_audit': ai,
        'unimplemented': ['Second real game client and own-faction UI',
                          'Human-faction AI decision exclusion',
                          'Authority state replication to remote game',
                          'General command queue and multi-command concurrency',
                          'General reward execution and complete UI feedback',
                          'Continuous battle synchronization and native event pause handling'],
        'limits': [
            native['record_scope'],
            'Known global/world RNG fields were unchanged; this is not exhaustive RNG coverage.',
            'Crash/restart duplicate tests used a synthetic executor, not a crashed live game process.',
            'No real LAN or second computer tested. No independent battle simulation proven.',
            'The original first-combat omission remains unresolved.',
            'Temporary callback was restored; the inert DLL stays loaded until game exit.',
            'The per-force AI gate also reaches a unit path; safe AI exclusion is not established.',
        ],
        'provenance': [{'path': str(p.relative_to(ROOT.parents[1])),
                        'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources],
    }
    (OUT / '第二势力命令接入实测证据.json').write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    rng_text = ('已发现随机状态也一致。' if restored and restoration['known_rng_equal'] else
                f"已发现全局随机值与赏赐前不同：{restoration.get('global_rng_before')} → {restoration.get('global_rng_restored')}，未改写；不宣称完整隐藏状态恢复。")
    restore_text = ('用户已原生读回34号档；局面抽查恢复通过，资源、人员、任务及783条抽查记录恢复，'
                    '仅允许经类型和所属部队回指验证的运行时部队指针重建。'
                    + rng_text) if restored else (
        '临时执行入口已经还原，34号存档文件与备份保持原哈希。当前游戏仍保留本次赏赐的效果，'
        '待用户原生读取34号档后核对恢复；不能把“存档文件未变”当作“内存局面已恢复”。')
    report = f'''第二势力命令接入实测（2026-10-05）

已完成的核心进展
游戏保持张鲁视角（势力12），主机收到绑定刘备（势力2）的网络命令后，在游戏线程调用原生共用赏赐处理入口，为刘备的三名武将实际完成赏赐。没有切换本机玩家编号。本轮证明了“主机可以按请求者所属势力执行受控命令”这条链路。

这是一次固定命令的真实游戏实验。发送端与接收端是两个独立进程，通信使用本机TCP；只有一个真实SAN14进程，没有第二台电脑，也没有将结果更新到另一个游戏客户端。

真实资源和人员变化
日期保持203年8月中旬，没有推进。
刘备庐江（城市13）金钱：20804 → 20504，扣300。
刘备军团2行动力：10 → 9，扣1。
郭女王（101）忠诚：93 → 97。
公孙康（264）忠诚：91 → 95。
小乔（411）忠诚：99 → 100。
三人的赏赐标志同时更新。张鲁的宛城资源、军团11行动力和玩家身份保持不变。
783条抽查记录中仅上述3名武将、1个城市、1个军团发生预期变化；已发现的全局随机状态及世界随机字段保持一致，全局值为3900088880。抽查不是完整世界内存验证，不覆盖全部UI提示及隐藏字段。

网络权限和重复请求
实际向接收进程发送4个TCP请求：
1. 使用A的凭据请求B的命令：拒绝，没有调用赏赐。
2. 使用B的凭据提交正确命令：接受，原生赏赐提交1次。
3. 再次发送同一个B请求：返回已保存回执，没有再次扣钱或提高忠诚。
4. 使用相同请求编号但改变内容：拒绝。
网络测试后再次采集真实游戏状态，与首次执行后的783条记录一致，确认重复请求没有追加效果。
接收端在调用前持久记录待执行状态，完成后保存回执。对执行结果未知的请求不自动重试。进程崩溃/重启场景仅做过合成执行器测试，尚未在真实游戏执行中强制崩溃，不能宣称所有故障下的恰好一次保证。

实现和验证范围
外部Python负责网络收发、请求身份绑定、版本和局面预检；受控DLL负责在游戏更新回调中构造名单、重新检查资格和归属、调用原生赏赐、核对效果并还原接入点。
预检现在将“界面当前显示的势力”和“本条命令被授权的势力”分开。网络传语义编号，由主机解析成自己的游戏对象，不传另一进程的内存指针。
34项权限/资源预检、25项原生执行夹具、21项网络认证/去重/异常记录测试通过。正式调用前同一DLL完成了真实游戏空跑，未调用赏赐；正式调用次数为1。新CLI也在真实游戏上只读运行通过。
上述都是限定版本、限定存档、限定命令的验收，不是通用多人模式验收。已有世界上下文哈希仍偏保守，双方连续多命令的排队、重验和过期处理还需实现。

当前恢复状态
{restore_text}
临时DLL已无活动回调，模块本身会留在进程内直到游戏退出。一次执行凭证保留，脚本不会自动重试本次实验。

现在可以运行的只读入口
保持游戏停在可下令的大地图，双击同目录“查看双方命令权限.cmd”。它分别读取张鲁、刘备的赏赐候选人及预计付款城市、行动力消耗，输出“双方赏赐预检.json”。它不执行赏赐、不切换玩家，也不创建联机房间。候选人数会随当前局面变化。
本轮赏赐后，张鲁仍有3名候选，刘备剩余2名；读取34号档后刘备应回到5名。本工具仅针对当前已核验的游戏版本；查看名单不代表获得该势力的网络控制权。

下一段核心主线
一、建立两个人类势力的控制归属，区分AI自行选择新命令与部队执行已有命令。
离线确认按势力AI查询0xB44D0的4处直接调用，分布于势力、军团及部队相关路径；部队路径还通往队列写入。直接将该势力的AI总结果改为0，可能影响已有命令的处理，尚未证实可以这样做。当前AI总开关为1，按势力表为空，本轮未改动AI控制。
二、让第二客户端保留自己的操作视角，将它的操作转成带所属势力和请求编号的命令，由主机验权、排队和执行。先沿用已经实测的赏赐，再扩展内政类别。
三、把主机确认的即时效果同步回两个真实客户端，验证双方画面、资源和可用操作一致。此阶段才解决“B即时看到A忠诚变化”的真实跨客户端问题。
四、接入统一推进、日内事件暂停和战场过程同步。此前原A首批战斗漏算仍未定位，确定性锁步不能算通过；继续保留过程校验和发现分叉时暂停的设计，不以旬末覆盖替代过程一致性。

主线结论
第二势力的受控命令已经能经网络进入主机并产生正确的原生效果。接下来优先解决双方控制权和第二个真实客户端的状态回传；目前还不能作为双人联机成品使用。
'''
    (OUT / '第二势力命令接入实测.txt').write_text(report, encoding='utf-8')
    roadmap = OUT / '双客户端实施路线.txt'
    marker = '最新主线进展：第二势力命令已实际执行（2026-10-05）'
    text = roadmap.read_text(encoding='utf-8')
    if marker not in text:
        text += ('\n\n' + marker + '\n'
                 '主机保持张鲁视角，经本机TCP接收绑定刘备的固定赏赐命令，实际调用原生共用处理1次。'
                 '庐江扣300金、军团2扣1行动，郭女王93→97、公孙康91→95、小乔99→100；'
                 '张鲁资源和玩家身份不变。A越权拒绝，B重复请求返回缓存，同编号改内容拒绝；'
                 '重复请求后的真实状态核对没有追加效果。34项预检、25项原生夹具、21项网络测试通过。\n'
                 '只有一个真实游戏和两个本机网络进程，尚未实现第二游戏的自有界面、AI排除或状态回传。'
                 '新增只读入口“查看双方命令权限.cmd”。下一阶段优先控制权、AI新命令范围和真实双客户端即时状态同步；'
                 '原A首批漏算仍未解，锁步未通过。恢复状态和证据以“第二势力命令接入实测.txt”及对应JSON为准。\n')
        roadmap.write_text(text, encoding='utf-8')
    print(json.dumps({'result': 'PUBLISHED', 'restore_verified': restored,
                      'files': ['第二势力命令接入实测.txt', '第二势力命令接入实测证据.json'],
                      'tests': [34, 25, 21]}, ensure_ascii=True))


if __name__ == '__main__':
    main()
