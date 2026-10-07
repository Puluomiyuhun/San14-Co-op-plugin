"""Publish completed far-view evidence, explicitly separating the pending near test."""
import hashlib,json
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parents[1]/'outputs/san14-link'
TR=ROOT/'lockstep-traces';run=TR/'camera-route-far-k'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
a=load(run/'camera-route-analysis.json');audit=load(run/'gap-tactic-audit.json')
validation=load(ROOT/'camera-rng-watch-validation.json')
dry=load(TR/'camera-rng-watch-dry-k2/idle-comparison.json')
clean=load(TR/'camera-rng-watch-dry-k2-clean.json')
assert a['clean_detach'] and not a['errors'] and a['gate_coverage']['count']==120
assert len(a['tactic_dispatches'])==6 and not a['camera_decisions']
assert not any(r['armies'] for r in a['gate_comparisons']['run-b']['different_samples'])
assert a['end_comparison']['after-run-b']['different_records']==0
assert len(load(TR/'after-camera-far-k.json')['records'])==785
focused=load(run/'focused-differences.json')
assert len(focused)==1 and focused[0]['path']=='focused/state_stack'
assert len(audit['rng_gaps'])==3 and all(g['is_exactly_one_native_step'] for g in audit['rng_gaps'])
assert validation['result']=='PASS' and validation['observer_sha256']==hashlib.sha256((ROOT/'observe_camera_rng_watch.exe').read_bytes()).hexdigest()
assert all(dry[k] for k in ('random_inputs_equal','focused_state_equal','person_task_sample_equal'))
assert not dry['sampled_record_changes_excluding_known_runtime_pointer'] and not clean['debugger_attached']
text='''远景推演对照与随机写入补盲（第十轮，2026-10-05）

结论：本次远景推演未重现原A首批交战漏算；镜头导致战局分叉仍未证明，也未被排除。已找到本轮观测的两个限制，并完成对应记录器改进。尚未完成有效的近景／远景受控对照。

1. 远景真实推演结果
从34号档规划期开始，起点抽查及已发现随机状态与本轮参考一致，随机值为3823646826。用户推进一旬，不新增命令。
推进前镜头级别6；272条捕获事件中的镜头级别均为5，仍为远景。没有捕获6→5的具体写入，不能断言转换原因，也不能把采样当作连续完整镜头轨迹。
记录120个战斗入口（10天×12日内时段）、6次战法演出分发、146次主要随机写入。120个入口的部队抽查字节与原B对应阶段记录全部一致，旬末785条局面抽查记录与B/I2/J2一致。与B的聚焦状态只多了CReportDisplayState报告窗口；这不等于全部UI状态相同。原A旬末仍有25条抽查记录不同。
原B与本轮的记录指令位置、起点随机状态和记录器均不同，因此上述一致性是复核线索，不能当作只改变镜头的受控实验，也没有覆盖每一次中间伤害或动画。

2. 为什么没有记录到专门演出的镜头判定
6次分发均未命中0x15B12F（0x322030镜头资格调用的返回点）。前置0x210FF0谓词仅对战法ID 31..130、140..200返回真。
把历史战法指针与同一进程读档后的CTacticsData表核对后，对应为：火矢两次、象兵、大喝、突击、牵制各一次。它们的ID为5、135、11、2、10，都不满足前置条件，足以解释本轮为何未进入该镜头判定。历史事件没有直接保存表基址，所以名称/ID解释仍依赖该表在同进程读档后地址稳定；新记录器已在起点保存完整战法表来消除这一缺口。
孙皎所在部队本轮有一次火矢分发；早期实验没有对应战法事件记录，不能推断早期没有使用火矢。
普通战法依然可能受其他显示或声音分支影响；本次只是确认这条专门演出分支没有得到有效覆盖。

3. 随机记录确有缺口，不把缺口解释成不同算法
146次已捕获更新全部符合已识别的原生算法，其中118次来自表达式路径，28次来自声音变体路径。
事件107、113、166前各出现一处链条缺口；三处都恰好等于已识别算法再前进一步。只能说明数值相符，不能反推具体写入函数或线程。
上一版只观察0x3AA805主要写入点，另有已知写入点未覆盖。记录结束后到旬末截图之间的随机值也不同；原记录在日期到21日停止，报告阶段未必全部涵盖，不能把这段差异直接归为战斗期间漏记。

4. 新记录器及验证
保留战法分发、镜头资格和战斗入口三个执行观察点，把第四个槽改为监测已知全局随机状态0x18EB8B0的4字节写入。无论经由哪个函数写这个地址，都可触发写入观察，并记录写入后指令位置、调用栈、线程、镜头及推演阶段。未改游戏代码、逻辑数据或存档文件。
独立硬件测试通过7次写入，涵盖同值写入、字节/半字写入、重叠8字节写入和新建线程。超时及取消退出测试通过。11条合成事件验证通过，涵盖其他已知写入点及未知写入位置。游戏待机短测正常退出，783条抽查记录及已发现随机状态未变。
这并非“所有随机源”已被发现：它只覆盖这一已知地址；前次观察值也不是竞争线程下的原子写前值。调试器仍会改变时序，新旧记录器差异必须纳入对照限制。

5. 恢复及下一步
用户已恢复34号档，783条局面抽查、人员任务及规划期状态恢复。当前已知全局随机值1138287528，与远景轮起点3823646826不同，不能直接当作相同起点做近景实验。此次没有改写或强行归一随机值。
下一步先观察仅拉近镜头是否消耗该随机状态，不推进日期。正式对照仍须核对共同起点及任务边界，并对齐或明确控制随机初始化；要验证专门演出分支，还需能实际满足战法前置条件的测试样本。不能要求双方永久保持相同镜头来代替联网同步。
原A第一批交战缺失的原因仍未查清；完整世界同步、低干扰重复性以及两个真实客户端验证尚未完成。
'''
manifest_files=['analyze_camera_route.py','disasm-210ff0.txt','make_camera_rng_watch.py','observe_camera_rng_watch.cpp','observe_camera_rng_watch.exe',
 'prepare_camera_rng_watch_tests.py','test_camera_rng_watch.py','validate_camera_rng_watch.py','camera-rng-watch-validation.json',
 'start_camera_rng_watch.py','prepare_camera_rng_watch_start.py','lockstep-traces/camera-route-far-k/trace.jsonl',
 'lockstep-traces/camera-route-far-k/metadata.json','lockstep-traces/camera-route-far-k/before.json',
 'lockstep-traces/camera-route-far-k/camera-route-analysis.json','lockstep-traces/camera-route-far-k/gap-tactic-audit.json',
 'lockstep-traces/camera-route-far-k/focused-differences.json','lockstep-traces/after-camera-far-k.json',
 'lockstep-traces/restored-camera-far-k.json','lockstep-traces/camera-rng-watch-dry-k2/trace.jsonl',
 'lockstep-traces/camera-rng-watch-dry-k2/idle-comparison.json','lockstep-traces/camera-rng-watch-dry-k2-clean.json']
evidence={'created':datetime.now().astimezone().isoformat(),'run':'camera-route-far-k','conclusions':{'camera_causation_proven':False,'original_a_root_cause_proven':False,'near_far_controlled_test_complete':False},
 'far_summary':{k:a[k] for k in ('event_counts','observed_camera_states','tactic_dispatches','rng','end_comparison')},
 'tactic_and_gap_audit':audit,'focused_differences':focused,'recorder_validation':validation,'dry_run':dry,
 'next_step':'Camera adjustment observation only; battle advancement not requested yet. Do not silently normalize the mismatched RNG state.',
 'manifest':[{'path':n,'sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest()} for n in manifest_files]}
for name,data in [('远景推演与随机补盲第十轮.txt',text),('远景推演与随机补盲第十轮证据.json',json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')]:
    with (OUT/name).open('x',encoding='utf-8') as f:f.write(data)
roadmap=OUT/'双客户端实施路线.txt'
with roadmap.open('a',encoding='utf-8') as f:
    f.write('\n锁步追查第十轮：远景真实推演与随机写入补盲（2026-10-05）\n')
    f.write('远景轮120个战斗入口的部队抽查与B一致，旬末785条局面抽查一致，未重现原A。6次普通战法分发均未进入专门演出的镜头判定；须补充符合前置条件的样本才能测试该分支。主要随机写入记录发现3处各相当于一次原生更新的缺口，来源尚未记录。\n')
    f.write('已将新的记录器改为监测已知全局随机地址全部写入，保留镜头和战斗标记；独立硬件、合成事件、退出清理及游戏待机短测通过。原A根因及镜头因果均未证明。恢复后的随机起点与远景轮不同，未改写。下一步先只观察镜头调整，再处理正式对照起点。详见“远景推演与随机补盲第十轮.txt”。\n')
print(json.dumps({'published':True,'manifest_files':len(manifest_files),'report_chars':len(text)},ensure_ascii=True))
