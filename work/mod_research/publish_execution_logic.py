"""Publish the current design baseline and narrowly scoped execution evidence."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs' / 'san14-link'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
unit = read(ROOT/'execution-journal-tests.json')
native = read(ROOT/'journal-native-pair-results.json')
room = read(ROOT/'room-session-tests.json')
assert unit['result'] == native['result'] == room['result'] == 'PASS'
assert unit['tests_run'] == 32 and room['tests_run'] == 26
assert native['successful_pair_calls'] == {'A': 1, 'B': 1}
assert native['duplicate_attempts_suppressed'] == 6
assert native['actual_game_command_calls'] == native['game_processes_opened'] == 0
assert not native['native_gameplay_enabled'] and native['room_phase'] == 'WAITING_NATIVE_ADAPTER'
for filename, expected in native['source_sha256'].items():
    assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == expected, filename

note = '''统一逻辑与执行记账补充（2026-10-06）
完整玩法、命令生命周期、准备封存、战场表现、事件与恢复，以同目录“完整联机逻辑与验收基线.txt”为当前基线。两边固定自己的身份，所有玩法输入归入一个权威时间线；不能用旬末覆盖代替战场过程一致。
新增execution_journal.py，对接房间固定绑定与既有赏赐预检，在原生代码隔离副本中验证每端执行记录。32项异常/并发测试、26项房间回归通过；成对副本各执行一次，六次重传未再次调用；未应用、执行结果未知和读档回退均不能误当同步完成。
本轮没有连接游戏进程，没有新增真实赏赐，也未开启实际开局或推进。日志只提供适配器内部的防重和有界采样对照；完整世界、实际加载检测、真实菜单、持续AI保护与战场同步仍需接入。详见“执行记账与成对原生验证证据.json”。
下一验收关仍是真实B势力菜单/上下文，随后是两份真实游戏的一条赏赐闭环和共同推演；执行记录不能代替这些原生可行性验证。
'''
start = '[CURRENT_EXECUTION_LOGIC_BEGIN]\n'
end = '[CURRENT_EXECUTION_LOGIC_END]\n'
for name in ('双人联机交互与同步设计.txt', '预期用法与双人操作流程.txt',
             '双客户端实施路线.txt', '双人联机当前缺口与使用形态.txt'):
    path = OUT/name
    text = path.read_text(encoding='utf-8')
    if start in text:
        first, rest = text.split(start, 1)
        _, last = rest.split(end, 1)
        text = first + last
    title, rest = text.split('\n', 1)
    path.write_text(title+'\n\n'+start+note+end+'\n'+rest.lstrip('\n'), encoding='utf-8')

evidence = {'schema': 'san14.execution-logic-milestone.v1',
            'created': datetime.now().astimezone().isoformat(), 'result': 'PASS_WITH_NATIVE_ADAPTER_GATES_PENDING',
            'design': '完整联机逻辑与验收基线.txt', 'execution_journal_tests': unit,
            'room_regression': room, 'isolated_native_integration': native,
            'game_access_this_milestone': False, 'two_real_clients_verified': False,
            'ready_barrier_connected_to_game': False, 'game_crash_recovery_implemented': False,
            'next_native_gate': 'Own-faction native menu/context plus dual-human AI protection, then real two-client reward replication.',
            'design_sha256': hashlib.sha256((OUT/'完整联机逻辑与验收基线.txt').read_bytes()).hexdigest()}
(OUT/'执行记账与成对原生验证证据.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'result': evidence['result'], 'journal_tests': unit['tests_run'],
                  'room_tests': room['tests_run'], 'fixture_calls_per_pair': native['successful_pair_calls'],
                  'duplicate_attempts_suppressed': native['duplicate_attempts_suppressed'],
                  'game_access': False}, ensure_ascii=True))
