"""Publish completed live evidence, preserving the earlier preparation report."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
from lockstep_baseline import sample, BattleObserver
from battle_branch_inputs import capture_branch_inputs

ROOT=Path(__file__).resolve().parent
TRACES=ROOT/'lockstep-traces'
RUN=TRACES/'first-batch-live-p2'
OUT=ROOT.parents[1]/'outputs/san14-link'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
audit=load(RUN/'comparative-audit.json')
closeout=load(RUN/'closeout.json')
restored=load(TRACES/'first-batch-p2-restored-closeout.json')
proposal=load(TRACES/'proposal-durability-restored-p2.json')
prior_proposal=load(TRACES/'proposal-durability-restored-p.json')
assert audit['counts']['casualty_request']==16 and audit['counts']['pair_eligibility']==17
assert audit['historical_comparisons']['run-b']['ordered_damage_requests_equal']
assert not audit['historical_comparisons']['run-b']['before_army_record_differences']
assert not audit['historical_comparisons']['run-b']['after_army_record_differences']
assert audit['F_pair_comparison']['raw_side_records_equal'] and audit['F_pair_comparison']['eligibility_order_equal']
assert all(not v['sampled_record_changes_excluding_known_runtime_pointer'] and v['focused_state_equal'] and v['person_task_sample_equal'] for v in audit['end_comparisons'].values())
assert len(audit['troop_changes'])==10
assert restored['result']=='PASS' and restored['comparison']['random_inputs_equal']
assert not restored['debugger_attached'] and restored['original_strategy_update_restored']
assert proposal['nonempty_proposal_count']==9 and proposal['random_global_18eb8b0']==3900088880
assert proposal['hashes']==prior_proposal['hashes']
reader=BattleObserver()
try:
    state=sample(reader);branch=capture_branch_inputs(reader)
    assert state==sample(reader) and branch==capture_branch_inputs(reader)
    assert state['random_inputs']==restored['comparison']['random_inputs_b']
    before=load(RUN/'before-branch-inputs.json')
    # Preserve the raw restored pair contents separately; they may include unknown bytes.
    branch_summary={k:branch[k]==before[k] for k in branch if k!='pairs'}
    for filename,data in [('restored.json',state),('restored-branch-inputs.json',branch)]:
        with (RUN/filename).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
finally:reader.close()

report='''首次交战短记录实测结果（第十五轮实测补充，2026-10-05）

结论
P2轮完整记录到正常的首次交战流程，没有重现原A首批漏算。新记录器两次断点切换已在本次实际逻辑线程执行中生效，并在进入阶段13时退出。仍不能宣称已找到原A原因、修复异常或证明双客户端锁步。

实际过程
共42个观察点：6次时段门槛、1次战斗入口、1次名单生成返回、17次逐对资格判断、16次伤害请求、1次结束边界。
子时段0、2、4、6、8门槛关闭；子时段10门槛放行。战斗入口pending_94=0，生成返回1，名单有17条。逐对访问顺序与生成名单完全一致，16条资格通过；特殊过滤开关和世界+165C在各记录点均为0。没有观察到等待路径跳过重建。
本次伤害请求的攻击方、目标、数值、调用来源及顺序与原B首批16次记录逐条相同；首批开始与结束的部队采样字节也分别完全相同。对正常F轮，17条名单双方各24字节、排序及资格判断结果全部相同，本次比较没有需要排除的未知字节差异。

那一条未通过的交战
20号部队→9号部队的记录未通过前置资格判断。在它之前，9号部队→20号部队已发出11点伤害请求；20号部队首批开始恰有11兵，首批结束为0兵。结束时歼灭处理列表由0项变为1项，其中记录20号部队。
这个处理顺序与正常F轮相同，属于单对资格未通过的证据，不是原A整批16次伤害消失的重现。当前记录没有分别监测“对象有效性、排除名单、歼灭列表”等每个子判断，因此不把最终资格值夸大成已捕获确切拒绝指令。
本批共有10支部队的兵力/伤兵发生变化，详细前后数值保存在证据JSON。

补上的隐藏状态
规划起点、首批门槛、生成返回、首批结束四处，52个势力的+12、+194及+EA关系字节均一致。+12和+194均为0；关系数组有两处非零：势力2→9与9→2均为23。这里是势力编号，不能误当作同编号部队，也不猜测该值的界面名称。
首次生成前列表数量为：root+58部队62、root+68排除0、城市51、关隘10、歼灭0。完成首批后歼灭列表变为1，其余数量不变。记录同时保留了成员顺序，不能将相同数量当成完整相同。
这些是P2当时的实测状态；原A缺少对应历史记录，不能把它们倒填给原A。

旬末与随机状态
记录器只覆盖首次交战，后续一旬正常运行至203年8月21日。旬末785条局面样本、聚焦状态及人物任务样本，与正常B/F/N三轮一致，排除了已知部队显示对象指针地址差异。其余旬内过程没有在本轮连续记录，所以不据此证明整旬动画或每一步均相同。
本轮规划起点全局随机值1138287528，首批门槛为218062980；原A/B首批门槛为413016057。旬末全局随机值534843186，也与比较轮不同。它是分支定位观察，不是同随机起点对照。局部战斗结果相同既不能证明共用随机无影响，也不能证明完整世界相同。
新覆盖还保存了旬末31个提案槽中的11个非空项和52个城市表项的耐久关联；旧B/F未记录这些新增字段，不能补报历史一致性。

恢复检查
用户读回34号档后，日期恢复203年8月11日、玩家张鲁。783条原局面样本、人物任务和已发现随机状态均与原A规划起点一致，全局随机值此次恢复为3900088880；未对随机状态做人工写入。
提案恢复为9个非空项，提案与城市耐久覆盖哈希和本轮开始前相同。调试器已退出，6处观察代码与原策略更新函数核对正常，34号存档和备份SHA256仍一致。

当前判断与后续边界
本轮将低频记录器的完整链条验证通过，也再次确认正常首批的顺序与结果。原A依然是尚未重现的历史异常，不能因为增加一次正常样本就缩掉所有未捕获的候选原因。
下一步应依据具体候选研究加载后的调度/等待状态，或构造能区分原因的隔离验证；在没有新条件或明确对照方案前，单纯再推进同一局一旬的收益很低。本轮已收尾，无记录器运行，也不需要用户继续推演。
'''
artifacts=[RUN/n for n in ('metadata.json','before.json','before-branch-inputs.json','trace.jsonl','analysis.json','comparative-audit.json','end.json','end-branch-inputs.json','closeout.json','restored.json','restored-branch-inputs.json')]
artifacts += [TRACES/n for n in ('first-batch-p2-restored-closeout.json','proposal-durability-after-p2.json','proposal-durability-restored-p2.json')]
artifacts += [ROOT/n for n in ('close_first_batch_capture.py','audit_first_batch_live.py','publish_first_batch_live.py')]
evidence={'created':datetime.now().astimezone().isoformat(),'result':'NORMAL_FIRST_BATCH_CAPTURED_ORIGINAL_A_UNRESOLVED',
          'audit':audit,'end_closeout':closeout,'restoration':restored,
          'restored_nonpair_branch_fields_equal':branch_summary,
          'restored_proposal_durability_hashes':proposal['hashes'],
          'artifact_manifest':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in artifacts]}
dest=OUT/'首次交战短记录实测结果.txt'
evdest=OUT/'首次交战短记录实测证据.json'
with dest.open('x',encoding='utf-8') as f:f.write(report)
with evdest.open('x',encoding='utf-8') as f:json.dump(evidence,f,ensure_ascii=False,indent=2)
assert dest.read_text(encoding='utf-8')==report and load(evdest)==evidence
with (OUT/'双客户端实施路线.txt').open('a',encoding='utf-8') as f:
    f.write('\n\n第十五轮实测补充：首次交战短记录P2完成并恢复34号档。42个观察点完整捕获17条名单、16条资格通过和16次伤害请求；伤害数值与顺序、首批前后部队字节均同正常B，名单原始字节和资格同正常F。20→9未通过之前9→20已请求11伤害，20初始11兵、结束0兵，符合正常轮顺序。\n新增势力关系字段在规划/门槛/生成/结束四处一致，歼灭列表在首批内由0变1。旬末785条取样同B/F/N，随机状态不同，不是同起点锁步证明。恢复后783条及已发现随机状态与原A起点一致（3900088880），提案9项和耐久哈希恢复，无调试器、存档未变。原A仍未重现，暂不重复要求用户推进；下一步须有明确新候选或隔离验证。详见“首次交战短记录实测结果.txt”。\n')
print(json.dumps({'published':str(dest),'restored_rng':proposal['random_global_18eb8b0'],
                  'restored_branch_nonpair_equal':branch_summary,'debugger_attached':False,'root_cause_proven':False},ensure_ascii=True))
