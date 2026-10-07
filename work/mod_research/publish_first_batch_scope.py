"""Preserve the narrowed hypotheses and validation without claiming A's root cause."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
from lockstep_baseline import sample, BattleObserver

ROOT = Path(__file__).resolve().parent
TRACES = ROOT/'lockstep-traces'
OUT = ROOT.parents[1]/'outputs/san14-link'
load = lambda p: json.loads(p.read_text(encoding='utf-8'))
rows = lambda p: [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

native = rows(ROOT/'combat-filter-fixture-expanded-results.jsonl')
assert native[-1]['result'] == 'PASS' and native[-1]['recorded_pairs_allowed'] == 17
assert native[-1]['minimum_pairs_allowed_any_player'] == 15
source = load(ROOT/'combat-filter-fixture-source.json')
fixtures = load(ROOT/'first-batch-fixtures.json')
payload = load(ROOT/'first-batch-payload-validation.json')
assert len(fixtures) == 3 and all(x['result']=='PASS' for x in fixtures)
assert payload['result']=='PASS' and len(payload['checks'])==13
assert all(sha(ROOT/x['name'])==x['sha256'] for x in payload['artifacts'])
idle = rows(TRACES/'first-batch-idle-p/trace.jsonl')
assert [r['event'] for r in idle] == ['attached','armed','detached']
assert idle[-1] == {'event':'detached','captured':False,'registers_restored':True}
assert not (TRACES/'first-batch-idle-p/stderr.log').read_text()
closeout = load(TRACES/'first-batch-idle-p-closeout.json')
assert not closeout['debugger_attached'] and closeout['original_strategy_update_restored']
assert not closeout['comparison']['sampled_record_changes_excluding_known_runtime_pointer']
proposal_before = load(TRACES/'proposal-durability-restored-o.json')
proposal_after = load(TRACES/'proposal-durability-restored-p.json')
assert proposal_before == proposal_after and proposal_after['random_global_18eb8b0']==1138287528
reader = BattleObserver()
try:
    current = sample(reader)
    assert current == load(TRACES/'first-batch-idle-p/before.json')
    image = (ROOT/'game-runtime-image.bin').read_bytes()
    points = (0x3F9344,0x3F935F,0x16C640,0x16C685,0x16AC60,0x15C045)
    assert all(reader.memory.read(reader.memory.base+rva,32)==image[rva:rva+32] for rva in points)
finally:
    reader.close()

f = rows(TRACES/'branch-run-f/trace.jsonl')
pairs = next(r['pairs'] for r in f if r['event']=='pairs_ready')
def side(raw):
    b=bytes.fromhex(raw)
    return int.from_bytes(b[4:8],'little'),int.from_bytes(b[:2],'little')
pair_ids = {(side(p['a']),side(p['b'])) for p in pairs}
historical={}
for name in ('run-a','run-b'):
    trace=rows(TRACES/name/'trace.jsonl')
    stages=[r for r in trace if r['event']=='stage']
    assert len(stages)==3720 and stages[167]['stage']==12 and stages[168]['stage']==13
    a,b=stages[167]['seq'],stages[168]['seq']
    first=[r for r in trace if r['event']=='casualty_request' and a<r['seq']<b]
    assert len(first)==(0 if name=='run-a' else 16)
    assert all(((r['source_kind'],r['source_id']),(r['target_kind'],r['target_id'])) in pair_ids for r in first)
    historical[name]={'first_stage12_casualty_requests':len(first),
                      'known_rng_before':stages[167]['global_rng'],
                      'known_rng_after':stages[168]['global_rng'],
                      'F_pair_list_contains_all_first_damage_pairs':all(((r['source_kind'],r['source_id']),(r['target_kind'],r['target_id'])) in pair_ids for r in first)}
assert historical['run-a']['known_rng_before']==historical['run-b']['known_rng_before']==413016057

report='''首批交战过滤与记录补缺（第十五轮，2026-10-05）

本轮结论
原A首批没有伤害请求、原B有16次，这个差异仍然成立；原因尚未查清。本轮排除了两个有条件的单因素解释，并验证了旧状态取样存在能影响交战资格的盲区。不能再把“783条样本相同”说成“完整推演状态相同”。

1. 额外过滤器不能单独解释同一批名单全部消失
从游戏映像提取0x43F160额外过滤、0x2110B0玩家判断、0x2F21E0当前势力读取、0x29A000关系判断四段原生代码，在独立进程的合成对象上执行。重定位有明确清单；对象有效性和虚函数势力ID读取使用测试替身。没有在游戏进程执行这些函数，也不是完整战斗模拟。
使用正常F轮首批17条真实交战记录，张鲁玩家上下文下17条均通过额外过滤。把玩家编号遍历0..51，共884次判断，任一编号下至少15条通过。原B首批16次伤害涉及的攻击方/目标组合均包含在这17条中。
过滤器对部队目标直接放行；对当前玩家攻击据点的情况才有特定筛选。7个正反控制验证确实能拒绝部分关隘和城市目标，测试并非恒真替身。
因此：如果异常轮生成的名单与正常轮相同，仅切换这个过滤开关或玩家编号不足以解释整批零伤害。原A未记录实际名单，故这个条件不能追溯确证；其他资格判断及原A名单不同的可能性仍保留。

2. 世界开关有前提，旧样本又漏了关系字段
0x29A000读取world+0x165C，但其对应拒绝分支还要求交战双方force+0x12的0x02位都置位。原A的规划起点，52个势力该字节均为0。在其余合成关系字段固定的测试中，遍历52×52=2704对势力，世界开关0/1不改变返回值；另3个控制覆盖双方置位和仅一方置位。
这只排除“双方旗标保持0，却仅因该世界开关变化而被拒绝”的说法。旧记录没有首次交战当刻的完整势力状态，不能证明规划起点旗标一定保持到那时。
更关键的是：攻击方force+0xEA[目标势力]以及双方force+0x194会直接参与关系判断。3个独立反例只改这些字段，即可从允许交战变成拒绝，而旧版取样force+0x10..0x40完全相同。这证明旧状态一致性检查覆盖不足，但不证明原A当时这些字段确实不同；也不凭偏移猜测界面业务名称。

3. 新记录器只覆盖首次交战的决策链
改用四个自适应硬件执行断点：时段门槛→阶段13边界；战斗管理器入口；名单生成返回→伤害请求；逐对资格判断。它同时记录子时段、等待/效果队列、实际交战名单、列表成员顺序、特殊过滤状态及上述势力关系字段。
首批阶段12完成、进入阶段13时自动退出记录器。游戏仍会正常继续推演，不会替用户暂停，也不注入DLL、不改写游戏代码或逻辑数据。硬件调试仍会改变执行时序，不能称为完全无扰动。
按已知正常路径估算约42个记录点，相较此前3720个阶段入口减少重复中断；真实命中次数尚待本次实机推演。重建或等待次数不同会改变这个数字。
诊断器要求完整门槛、结束边界和正常退出；缺失事件、超时或错误不会被当成“战斗被跳过”的证据。输出区分门槛关闭、等待路径未重建、生成返回0、名单为空、全部前置资格不符、观察到伤害、以及有名单但尚不能解释的无伤害。

4. 验证及当前状态
独立进程三种硬件记录器退出测试通过（正常、超时、取消），原函数仍正确执行。合成内存覆盖7次调用、6类事件及两次断点配置切换，另拒绝3种损坏列表；诊断器13项正常与反例检查通过。合成调用验证不能替代真实线程上的动态断点切换或完整战斗验证。
当前游戏做了两秒待机挂接：106个线程挂接后正常退出，无战斗事件。前后783条取样记录及已发现随机状态完全一致；提案/耐久新增覆盖也与上一轮相同，仍为9个非空提案。当前日期203年8月11日，玩家张鲁，全局随机值1138287528。
该随机值与最早A/B规划起点不同，未经修改；下一次是分支定位观察，不宣称同随机起点的锁步复测。调试器已退出，6处候选代码指纹及原CUserStrategy更新函数保持原样，34号存档与备份哈希一致。

下一步
从当前恢复的34号档记录首批交战，先验证新覆盖能否把正常链条完整串起来；若再出现首批漏算，就可依据同一份记录缩小到实际分支。若本次仍正常，也不会据此宣布异常已修复或双客户端锁步成立。要定位最早那一次，仍需能复现异常或取得相应历史字段；旧日志缺失的信息不能事后补造。
'''
paths=[ROOT/n for n in ('combat_filter_fixture.cpp','combat_filter_fixture_code.h','combat_filter_fixture.exe','combat-filter-fixture-source.json','combat-filter-fixture-expanded-results.jsonl','first_batch_observe.inc','observe_first_batch.cpp','observe_first_batch.exe','make_first_batch_observer.py','analyze_first_batch.py','first-batch-payload-validation.json','first-batch-fixtures.json','start_first_batch_observer.py')]
paths += [TRACES/'first-batch-idle-p/trace.jsonl',TRACES/'first-batch-idle-p-closeout.json',TRACES/'proposal-durability-restored-p.json']
evidence={'created':datetime.now().astimezone().isoformat(),'historical_comparison':historical,
          'native_predicate_scope':source,'native_predicate_results':native,
          'infrastructure_tests':fixtures,'synthetic_validation':payload,'idle_trace':idle,
          'idle_sample_exactly_equal':True,'proposal_coverage_exactly_equal':True,'six_code_points_unchanged':True,
          'current_global_rng':1138287528,'closeout':closeout,
          'new_live_combat_capture_completed':False,'original_run_a_root_cause_proven':False,
          'artifacts':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]}
with (OUT/'首批交战过滤与记录补缺第十五轮.txt').open('x',encoding='utf-8') as f:f.write(report)
with (OUT/'首批交战过滤与记录补缺第十五轮证据.json').open('x',encoding='utf-8') as f:json.dump(evidence,f,ensure_ascii=False,indent=2)
with (OUT/'双客户端实施路线.txt').open('a',encoding='utf-8') as f:
    f.write('\n\n锁步追查第十五轮：首批交战过滤与记录补缺（2026-10-05）\n原生隔离判断表明：同一正常17条名单中，额外过滤在所有玩家编号下至少放行15条，不能单独解释整批零伤害。世界+165C分支还要求双方势力+12的0x02位；规划起点这些位为0不等于首次交战时也为0。关系+EA、+194三个反例证明旧势力样本相同仍可交战资格不同，原A相关历史字段缺失，不能追溯归因。\n新增首次阶段12决策链记录器，四个自适应硬件断点至阶段13自行退出，补齐门槛、等待、名单及资格。独立退出3项、合成诊断13项、游戏两秒待机挂接均通过；未进行新实机交战，真实动态切换仍待验证。当前783条样本和新提案/耐久覆盖未变，随机1138287528未改，调试器已退出、存档保持。原A根因及锁步仍未证明，详见“首批交战过滤与记录补缺第十五轮.txt”。\n')
print(json.dumps({'published':True,'historical':historical,'native_summary':native[-1],
                  'idle_sample_exactly_equal':True,'proposal_coverage_exactly_equal':True},ensure_ascii=False))
