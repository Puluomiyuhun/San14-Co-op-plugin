"""Publish milestone 14 from validated offline audit and read-only coverage."""
from datetime import datetime
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs' / 'san14-link'
load = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
audit = load(ROOT / 'proposal-scope-audit.json')
snapshot = load(ROOT / 'lockstep-traces' / 'proposal-durability-restored-o.json')
closeout = load(ROOT / 'lockstep-traces' / 'proposal-o-closeout.json')
validation = load(ROOT / 'proposal-coverage-validation.json')
assert sum(audit['proposal_draw_counts'].values()) == 319
assert len(audit['handlers']) == 25 and len(audit['durability_calls']) == 5
assert validation['result'] == 'PASS' and len(validation['checks']) == 10
assert snapshot['nonempty_proposal_count'] == 9 and len(snapshot['proposals']) == 31
assert snapshot['random_global_18eb8b0'] == 1138287528
assert not closeout['debugger_attached'] and closeout['original_strategy_update_restored']
assert not closeout['comparison']['sampled_record_changes_excluding_known_runtime_pointer']
assert closeout['save34_sha256'] == closeout['backup_sha256']

report = '''提案生成与耐久结算追查（第十四轮，2026-10-05）

本轮结论
第十三轮尚未命名的319次随机评分/换序调用，全部来自武将提案生成流程；生成候选会读取当前玩家势力。临时种子期间的5次随机调用则定位到据点耐久恢复计算。两者均有业务意义，不能整体划为表现随机。
这些发现补足联机状态与随机同步的必要条件，尚未解释原A首次漏算战斗。原A的部队差异早于已发现的全局随机值差异，不能把新的旬末发现当作它的既定根因。
本轮只分析已保存程序映像、原生调用日志并读取当前游戏内存；未推进日期、附加调试器、加载DLL、调用游戏函数或改写游戏状态。

1. 319次随机调用属于哪个系统
原生调用栈逐条核验：100次随机评分、50次16字节元素换序、60次整数条目换序、109次指针条目换序，全部经过0x3D1420→0x3CB950，外层为CStrategyState准备路径。
0x3D1420构造对象的RTTI确认为CProposalFunc。0x3CB950先收集人物候选，评分、排序并尝试生成提案。0x3D0000随机排列候选类别与处理器，再调用处理器虚函数+0x18尝试生成。
解出全局处理器表的25项：1个None，加24种具名提案，包括DevelopmentUp、Conscription、RepairEndurance、BuyFood、RecomendPerson、CurePerson、BurnEnemy等。英文名称来自游戏RTTI，不假设与界面中文逐字对应。完整方法地址及参数索引字段保存在证据JSON。
提案本身不是纯显示项：例如Conscription处理器的+0x48函数0x3C53F0中，0x3C5764确实写入城市+0x3C兵力。这里是静态执行路径证据，本轮没有实际接受或执行提案；不能因此宣称24类提案全部可远程操作。

2. 为什么两位玩家不能直接各自消耗同一条随机流
生成候选路径为0x3D1450→0x2F21A0；后者读取world+0x3A当前玩家势力编号，取CForceData，再经0x20C110取得其统辖军团。后续0x211F80构建CDistrictPersonIterator收集人物候选。因而该流程明确依赖当前玩家身份，而非只依赖共同地图数据。
由此推断：A、B分别控制不同势力，即使共同战局和随机起点一致，本地提案候选、分支和随机消费次数也可能不同。319次只是本次张鲁流程的观测次数，不是每个势力的固定次数。
原生生成器使用root+0x7EF08..0x7F000的31个CProposalData槽；0x3CC530会清理这组槽，0x3CCE70寻找空槽。本入口观察到的是一组全局槽位。未穷尽是否另有备份或存档结构，不能宣称程序所有地方都没有势力维度。
联机设计应把共同世界与按玩家呈现的业务数据分开：提案由主机按势力生成并保存，将所属势力、旬/世界版本和提案标识一起发送；客户端接受提案时提交引用，主机核验人物、目标、费用和当前条件，再按统一顺序执行并同步共同世界变化。
这是待实现方案。原生代码隐式读取当前玩家，不能只改一个势力字节就假定可以安全轮流生成。还需审计生成/执行的其他写入、玩家上下文、恢复和重复提交。提案随机也不能未经验证就整块分流；需要定义业务随机域与固定调度顺序，并核对生成及接受的实际效果。

3. 临时种子的5次抽取用于耐久恢复
第十三轮call_id 140..144的真实栈均为：0x3AA7C0→0x285550→0x2B4FA0→0x2CE910→0x3DD840→0x3DBF80。恢复的非易失寄存器表明5次都处于调度阶段索引39，使用同一个阶段对象。
0x2B4FA0检查当前值与上限，在条件通过后调用0x285550计算恢复量；当前值经城市+0x4E查root+0x6D808的CObjectData，读取其+0x14。计算值相加并限幅后，0x1D8230写回该对象+0x14。
业务名称另由CProposalHandler_RepairEndurance交叉确认：其效果路径也调用0x285550及同一读取函数0x20A330，并经0x21D430→0x1D8230更新同一字段。结合具名处理器、读写字段和限幅数据流，将该旬末路径识别为据点耐久恢复。
本次5次随机结果为3、41、12、20、41，参数为20、46、20、34、44。它们是计算中的随机项，不是最终增加的耐久值。旧日志没有捕获关联对象+0x14的前后值，因此不能补报本次各城最终恢复量，也不能把现在读到的内存当作当时数据。

4. 临时种子的范围大于单个函数调用
0x3DBF80使用66项阶段表；阶段索引1调用0x3D9790保存旧种子到阶段对象+0x14，并设置日期计算值加world+0x45C的临时种子。阶段39进行上述耐久处理；CTurnState收尾经+0x470对象调用0x3D4F60，才按“保存值非0”条件恢复旧种子并释放对象。
因此不能把这个机制理解成某个随机函数内部短暂换种子，或认为所有剧本都只有这5次调用。阶段可以分次推进，实测设置与恢复也跨了线程。同步若允许在旬末中间恢复，必须覆盖当前阶段及保存的旧种子；仅比较阶段外最终全局种子会漏掉中间业务结算。更简单的候选方案是只允许在已证明完整完成的逻辑边界建立起点，但现有空闲抽查仍不是已证明的同步屏障。

5. 已补充的只读工具与验证
新增proposal_state_reader.py：锁定当前EXE指纹，验证RTTI、字段范围与对象编号，记录31个提案槽的原始字节和已解字段，以及52个城市表项（含0号占位）关联的地图对象耐久。提案摘要带当前观察到的玩家和日期上下文；公共耐久单独摘要。
提案+0x10..0x30中的未知字节仍保留。摘要是诊断工具，不能直接当作跨进程同步协议；遇到差异仍需区分有效字段、未知数据和填充。当前玩家标签表示采集上下文，并非从每个提案记录里读出了独立势力归属。
当前恢复34号档：203年8月11日、张鲁，31槽中9个非空；宛的关联对象编号19，耐久字段3000。两次连续读取一致，稍后再次读取也与保存快照一致，随机值始终为1138287528。
10项离线反例检查通过，覆盖参数变化、未知字节、玩家身份、槽位顺序、独立耐久变化、截断记录、非法类型/人物/槽位及前后读取不一致的拒绝。测试证明新增校验覆盖与拒绝行为，不等同于游戏业务或双客户端同步通过。
旧的783/785条抽样没有包含提案槽和关联CObjectData耐久字段，故此前“抽样一致”不能升级为这两类数据也一致。现已补上后续采集能力，不能追溯补齐缺失的历史观测。

6. 收尾与下一步
游戏仍停在34号档原状态；783条原有局面抽样恢复核对通过，已知等待/工作/效果字段为空，调试器未附加，原更新函数未改，34号档与备份哈希相同。全局随机值1138287528与最早A轮基准不同，原样记录，没有修正。
后续接入规则必须分别处理共同世界业务随机、按势力生成的提案业务、已确认的纯表现随机，并覆盖旬末临时种子的生命周期。执行提案与即时操作仍应由主机排序核验，客户端世界按同一业务日志推进。
原A缺失首批战斗的问题继续单列：需要针对最早缺失的战斗入口、调度/队列前置条件取证，不能用更多正常旬末样本替代异常现场。当前尚未完成实际DLL透传接入、严格共同起点下的差异实验或双客户端锁步验证。本轮无需用户再手动推演。
'''

dest_report = OUT / '提案生成与耐久结算第十四轮.txt'
dest_evidence = OUT / '提案生成与耐久结算第十四轮证据.json'
for p in (dest_report, dest_evidence):
    if p.exists():
        raise RuntimeError(f'Refusing to overwrite {p}')
files = [ROOT / 'audit_proposal_scope.py', ROOT / 'proposal-scope-audit.json',
         ROOT / 'validate_proposal_coverage.py', ROOT / 'proposal-coverage-validation.json',
         ROOT / 'lockstep-traces' / 'proposal-durability-restored-o.json',
         ROOT / 'lockstep-traces' / 'proposal-o-closeout.json', OUT / 'proposal_state_reader.py']
evidence = {'created': datetime.now().astimezone().isoformat(),
            'static_and_historical_trace_audit': audit, 'current_restored_snapshot': snapshot,
            'negative_controls': validation, 'closeout': closeout,
            'game_mutated_this_round': False, 'original_run_a_root_cause_proven': False,
            'two_client_lockstep_proven': False,
            'artifacts': [{'path': str(p.relative_to(ROOT.parents[1])), 'sha256': sha(p),
                           'bytes': p.stat().st_size} for p in files]}
with dest_report.open('x', encoding='utf-8') as f:
    f.write(report)
with dest_evidence.open('x', encoding='utf-8') as f:
    json.dump(evidence, f, ensure_ascii=False, indent=2)
with (OUT / '双客户端实施路线.txt').open('a', encoding='utf-8') as f:
    f.write('''

锁步追查第十四轮：玩家提案与耐久恢复（2026-10-05）
已用RTTI、40处指令锚点和真实调用栈，将319次随机评分/换序归到CProposalFunc提案生成，识别24种有效处理器。候选生成读取当前玩家势力，故双客户端分属不同势力时不能假定其提案及随机消费相同。原生使用一组31槽，后续需主机按势力保存提案并验证接受操作；生成/执行的上下文和其他写入仍需审计，不能仅改玩家字节后直接调用。
临时种子内5次抽取定位到阶段39的据点耐久恢复；关联CObjectData+14此前未入快照。临时种子在66阶段流程索引1设置，CTurnState收尾按非零旧值恢复，可跨线程；它不是一个短函数内的局部种子。
新增只读提案/耐久采集及10项反例检查。当前34号档31提案槽中9个非空，52个城市表项的耐久关联已采集，前后稳定；旧783条样本也核对通过，随机值1138287528未改，调试器未附加，存档未变。旧轮缺失的提案/耐久历史数据不可事后补证。原A根因、完整世界同步和双客户端锁步仍未证明。详见“提案生成与耐久结算第十四轮.txt”及证据JSON。
''')
print(json.dumps({'report': str(dest_report), 'evidence': str(dest_evidence)}, ensure_ascii=True))
