"""Finish the existing tenth-round report with the completed close-view capture."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;TR=ROOT/'lockstep-traces';OUT=ROOT.parents[1]/'outputs/san14-link'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
folder=TR/'camera-near-rng-k2';a=load(folder/'analysis.json');audit=load(folder/'closeout-audit.json')
close=load(TR/'camera-near-k2-closeout.json');writes=load(folder/'rng-writes-unwound.json')
assert a['clean_detach'] and a['event_counts']['rng_write']==144
assert not a['rng']['continuity_gaps']
assert a['rng']['writers']=={'setter':1,'range_helper':142,'percentage_helper':1}
assert not a['far_gate_comparison']['changed_army_samples'] and a['far_gate_comparison']['shared_keys']==120
assert not a['far_end_comparison']['sampled_record_changes_excluding_known_runtime_pointer']
assert audit['six_tactic_dispatches_match_far']
assert not close['debugger_attached'] and close['original_strategy_update_restored'] and not close['rng_state_rewritten']
assert close['save34_sha256']==close['backup_sha256']=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
percent=next(r for r in writes if r['known_writer']=='percentage_helper')
frame=next(f for f in percent['unwind']['frames'] if f['pc_rva']=='0x2d40a2')
assert int(frame['nonvolatile']['rbx'],16)==0xc5f1
assert percent['previous_observed']==1793171794 and percent['observed_after']==4082451966
assert writes[0]['previous_observed']==writes[0]['observed_after']==1138287528 and 'CSaveState' in writes[0]['states']
text='''远近景推演与随机写入补盲（第十轮，2026-10-05）

本轮结论：远景和近景都没有重现原A首批交战缺失。两轮已记录的120个战斗时点部队数据、6次战法发动及旬末785条局面抽查一致。新增写入监测定位到人物台词中的概率判断会消耗已知共用随机状态。原A根因仍未查清，尚不能宣称镜头不影响战局或确定性锁步成立。

一、远景和近景的实际记录
远景启动前为6档，272条捕获事件均为5档；近景270条事件均为2档。记录器没有覆盖两个事件之间的连续镜头轨迹。
两轮均捕获10天×12时段的120个战斗入口，部分部队记录逐字节一致。6次战法的日期、日内时段、发动者类型/编号、战法指针一致，战法为火矢两次，象兵、大喝、突击、牵制各一次。旬末785条局面抽查及人员任务字段一致；聚焦状态的差异只在远景采样时报告窗口仍打开，不能称所有UI状态相同。
未记录完整战法目标列表，也未覆盖每次普通攻击、所有中间伤害和动画。因此目前没有证据出现“动画打的是另一队，最后强行套用结果”，但这轮数据还不足以排除所有此类问题。
远景起点已知随机值3823646826，近景1138287528，且两轮采用不同观察器；它们不是严格单变量镜头对照。不能把不同随机调用数量归因于镜头，也不能因局面抽查相同便认为随机状态无需同步。

二、仅调整镜头的独立观察
用户从6档拉近到2档、未推进的监测期间，已知全局随机地址未发生被捕获的写入，783条局面抽查和已发现随机状态均未变。这个结果只适用于规划期的本次调整，不代表推进中所有镜头处理都不会影响随机消费。

三、为什么没有进入专门战法演出的镜头分支
两轮6次分发均没有命中0x322030镜头资格判断的返回标记。该调用之前的0x210FF0谓词仅对战法ID 31..130、140..200返回真。本轮战法ID为5、135、11、2、10，全部不满足前置条件。
近景轮已在起点保存201条CTacticsData表，历史事件指针可直接映射；旧远景名称解释使用同进程读档后表，依赖表地址稳定。这说明该存档在这一旬没有有效测试到专门演出分支；不能因没有镜头判断事件就否定分支存在。
孙皎所在部队两轮均记录到火矢。更早实验没有相应事件流，不能判断更早是否也使用过。

四、新增随机写入来源
旧远景记录只观察主要写入指令0x3AA805，146次捕获更新均符合原算法，但有3处链条缺口，各恰好相当于再更新一次。没有当时调用栈，三处的来源仍未证明。
新记录器直接监测全局随机状态0x18EB8B0这4字节的写入，保留战法分发、镜头判断、战斗入口及调用栈。近景轮共144次写入：142次范围随机（表达式117次、声音变体25次），1次概率判断，1次保存状态中的同值写回。后者1138287528写回1138287528，不是新的随机抽取。
新增概率判断发生于8月12日日内子步16：状态1793171794→4082451966，写入指令0x3AA43B，停点0x3AA441。调用链从CPersonLineManager相关台词处理，进入消息0xC5F1的表达式求值，再通过间接调用抵达概率函数0x3AA3F0。栈中消息ID来自0x2D4040保存的EBX，单例类型也已核对。这里确认了人物台词处理会走主要范围随机函数以外的写入路径；没有恢复当时具体台词文本，不能把整个消息系统一概视为无关逻辑。
本轮记录区间的已观察状态链无缺口，143次非同值写入均符合原算法。日期到21日记录器自动结束，之后旬末报告期间的随机消费未完整覆盖，最后记录值666631366与旬末采样1535304145不同仍如实保留。
新记录器只监测一个已知随机地址，不等于所有随机源已发现；多线程下“上次观察值”也不是原子写前值。硬件调试会改变时序。

五、验证、恢复及后续方向
独立测试覆盖同值、字节、半字、重叠8字节及新线程写入，7次写入捕获通过；正常/超时/取消清理通过。11条合成事件及游戏待机短测通过。近景实际记录正常退出，无错误。
用户已读回34号档，最终783条局面抽查、人员任务和规划期状态恢复；调试器已退出、原更新函数已恢复，存档与备份哈希一致。首次恢复采样因两次读数变化被拒绝，随后稳定采样成功；拒绝时未保留变化字段，不能推断其具体原因。
恢复后的全局随机值3510933083仍与近景起点不同，本轮没有强行重写随机状态，没有安装游戏同步补丁。
接下来优先解决“读档后何时算共同起点”：报告和台词任务可以继续消耗共用随机状态，应在已确认初始化完成的边界再同步，并评估已证实表现路径的随机隔离。不能简单在任意调用前后保存并写回共用种子，也不能粗暴跳过整个消息系统。
镜头问题后续仍需相同起点、相同记录方式的重复对照，以及实际覆盖专门演出资格的样本。原A首次缺失发生在当时已监测随机状态尚相同时，仍需独立追查交战调度/待处理状态。当前不用再重复推进。
'''
(OUT/'远景推演与随机补盲第十轮.txt').write_text(text,encoding='utf-8')
path=OUT/'远景推演与随机补盲第十轮证据.json';e=load(path)
e['near_summary']={k:a[k] for k in ('run','event_counts','camera_states','rng','tactics','far_gate_comparison','far_start_comparison','far_end_comparison','limits')}
e['near_closeout']=audit
e['near_native_percentage_write']=percent
e['near_detach_and_checkpoint']={k:close[k] for k in ('debugger_attached','original_strategy_update_restored','save34_sha256','backup_sha256','rng_state_rewritten')}
e['next_step']='Offline common initialization boundary and scoped presentation RNG isolation research. No further game action requested. Camera causation and original A root cause remain unresolved.'
files=['analyze_camera_rng_watch.py','finish_camera_comparison_report.py','lockstep-traces/camera-near-rng-k2/metadata.json',
 'lockstep-traces/camera-near-rng-k2/trace.jsonl','lockstep-traces/camera-near-rng-k2/tactics-table.json',
 'lockstep-traces/camera-near-rng-k2/analysis.json','lockstep-traces/camera-near-rng-k2/rng-writes-unwound.json',
 'lockstep-traces/camera-near-rng-k2/closeout-audit.json','lockstep-traces/camera-near-rng-k2/focused-differences.json',
 'lockstep-traces/camera-setup-near-k2/trace.jsonl','lockstep-traces/camera-setup-near-k2/setup-comparison.json',
 'lockstep-traces/restored-camera-near-k2.json','lockstep-traces/camera-near-k2-closeout.json']
e['manifest'].extend({'path':n,'sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest()} for n in files)
path.write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (OUT/'双客户端实施路线.txt').open('a',encoding='utf-8') as f:
    f.write('\n第十轮补充：近景实测已完成并恢复34号档。近景2档与远景5档的120个战斗时点部队抽查、6次战法发动、旬末785条局面抽查一致；起点随机值和记录器不同，仍非单变量对照。144次全局随机写入中新增定位人物台词消息0xC5F1中的概率判断，经0x3AA43B写入；记录区间状态链无缺口。两轮均未进入专门战法演出的镜头资格分支。原A根因仍未明，下一优先项是共同初始化边界及已证实表现路径的随机隔离。当前无需再推进。\n')
print(json.dumps({'updated':True,'report_chars':len(text),'manifest_files':len(e['manifest'])}))
