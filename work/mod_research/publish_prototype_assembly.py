"""Publish the reviewed offline integration boundary, without altering old evidence."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT/'outputs'/'san14-link'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify_sources(value):
    for name, expected in value['source_sha256'].items():
        assert Path(name).name == name and sha(HERE/name) == expected, name


planning_path = HERE/'checkpoint_planning_return_observer_session_summary.json'
bootstrap_path = HERE/'checkpoint_test_bootstrap_handoff.json'
input_path = HERE/'checkpoint_native_input_handoff.json'
boot_final_path = HERE/'checkpoint_test_bootstrap_runs/20261007-091300-295479/result.json'
faults_path = HERE/'checkpoint_offline_prototype_fault_runs/20261007-091259-615579/result.json'
diagnostic_path = HERE/'checkpoint_offline_prototype_runs/20261007-091332-273840/result.json'
planning, bootstrap, input_core, boot_final, faults, diagnostic = map(read,
    (planning_path, bootstrap_path, input_path, boot_final_path, faults_path, diagnostic_path))
assert planning['result'] == boot_final['result'] == faults['result'] == 'PASS'
assert diagnostic['result'] == 'PASS_EXPECTED_HOLD' and all(diagnostic['checks'].values())
assert input_core['test']['failed'] == 0 and input_core['source_check']['all_source_and_build_script_sha_unchanged']
for evidence in (planning, bootstrap, boot_final, faults, diagnostic):
    verify_sources(evidence)
for artifact in input_core['artifacts']:
    assert sha(ROOT/artifact['path']) == artifact['sha256'], artifact['path']
for name in ('fixture_report','regression_report'):
    assert sha(Path(bootstrap[name])) == bootstrap[name+'_sha256']
assert sha(HERE/'checkpoint_session_ipc_fixture.exe') == bootstrap['fixture_binary_sha256']
assert diagnostic['controller']['phase'] == 'HELD' and diagnostic['journal_status'] == 'INTENT'
assert not diagnostic['controller']['accept_planning_intents'] and not diagnostic['playable_mod']
assert diagnostic['bootstrap_cleanup']['closed'] and not diagnostic['bootstrap_cleanup']['close_errors']
assert diagnostic['bootstrap_cleanup']['exit_code'] is not None

evidence_paths = (planning_path, bootstrap_path, input_path, boot_final_path, faults_path,
                  diagnostic_path, OUT/'离线原型组件清单.json', OUT/'运行离线装配诊断.cmd')
report = dict(schema='san14.prototype-assembly-progress.v1', updated=datetime.now().astimezone().isoformat(),
    result='OFFLINE_INTEGRATION_PASSED_EXPECTED_HOLD', agents=3, root_integration=True,
    game_accessed=False, playable_mod=False,
    restricted_mvp_effort_estimate=dict(approx_percent=40, range=[35,50],
        basis='Same restricted MVP scope as preceding audit; subjective remaining implementation effort, not test/pass ratio.'),
    modules=[
        dict(name='Session 到新 User 的大地图回归观察', status='隔离链路通过',
             cases=planning['integration_cases'], regressions=29, live_verified=False),
        dict(name='工作区存档 staging 与双阶段子进程启动', status='真实管道与控制器装配通过',
             cases=boot_final['tests_run'], ipc_regressions=11, live_verified=False),
        dict(name='输入缓存中和与消息过滤', status='局部 C++ 实现通过',
             cases=input_core['test']['passed'], full_input_hold=False, live_verified=False),
        dict(name='一键离线诊断入口', status='CMD 入口实际运行通过',
             result=diagnostic['result'], faults_tested=faults['cases'], live_verified=False)],
    remaining=['完整原生输入保护、排空与恢复接线', '完整共享世界摘要及 sidecar 覆盖',
        'B 实机自动加载、势力/规划/画面恢复一体化验证',
        '赏赐/出征执行前捕获与两个人类势力 AI/经济规则安装',
        '双客户端事件、断线及连续两旬循环验证'],
    evidence=[dict(path=str(p),sha256=sha(p)) for p in evidence_paths])
(OUT/'原型装配进展.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
text = '''本轮三个 agent 并行开发，我负责装配和独立检查。没有操作游戏。

已经交付一个可双击运行的“离线装配诊断”入口。
它真正启动自有 C++ 测试进程，通过 Windows 管道连接控制器，读取并核对工作区的存档副本，沿 Session 生成加载和势力身份收据。由于没有完整游戏世界证明，它正确保持等待；不会因为“刘备身份已恢复”就开放操作。
它不是可玩的联机 MOD。测试中的游戏函数和初始输入/视觉证据仍是明确的替身；测试耗时不能当作 B 真实读档耗时。

本轮完成的接线
一、加载后返回地图：新 User 状态现在通过同一 Session 桥接受核验，实际使用上游字节、生命周期和身份收据。11 项整链测试和 29 项旧回归通过。
二、存档启动器：先确定自有子进程身份，再在持久加载意图生成后写入并验证文件，最后绑定同一次请求。10 项测试和 11 项实际管道回归通过。
三、输入控制：已写出 C++ 缓存中和、原始键盘中性查询副本和精确消息过滤，11 项测试通过。保留原设备的按住状态，防止清缓存被误认为已经松手；真实设备与消费入口还没有接齐。
四、统一入口：实际 CMD 启动通过；另验证组件哈希不符拒绝启动、保持画面失败不能假报成功、子进程在请求后退出不重复加载，3 项故障测试通过。

如何测试
双击“运行离线装配诊断.cmd”。正常显示 PASS_EXPECTED_HOLD；这表示诊断按预期停在等待状态。具体边界见“离线原型测试说明.txt”。这个入口依赖当前工作区，暂不作为发给朋友的安装包。

离可玩原型还有什么
最近的里程碑是 B 在真实游戏中自动加载一次，保留 B 的势力、回到规划地图，并正确核验完整世界与恢复输入。
随后将已有赏赐/出征接入执行前拦截、两人 AI/经济规则和房间准备流程，跑通两客户端的一整旬，再连续验证两旬与中断恢复。
窗口等待层仍需与这条真实链一起验证；目前不能承诺游戏中已经完全不闪加载页面。

进度仍保守估计约 40%，区间 35%—50%，范围与上一份受限 MVP 评估相同。
本轮减少了装配缺口，但实机核心门槛尚未通过，不按测试数量给进度加分。常用内政、人才、外交全覆盖版本仍不适合报精确百分比。
当前不用你手动操作游戏。下一次实测会从固定测试档的单次自动加载开始。
'''
(OUT/'原型装配进展.txt').write_text(text, encoding='utf-8')
print('Published verified offline prototype progress; playable_mod remains false.')
