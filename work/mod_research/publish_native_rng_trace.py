"""Publish the complete native RNG trace, scoped reseeding and ordering evidence."""
from pathlib import Path
from datetime import datetime
from collections import Counter
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parents[1]/'outputs'/'san14-link'
TR=ROOT/'lockstep-traces';RUN=TR/'rng-pairs-live-n'
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
from analyze_rng_pairs import next_state
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
analysis=load(RUN/'paired-analysis.json');close=load(RUN/'closeout.json');meta=load(RUN/'metadata.json')
rows=[json.loads(line) for line in (RUN/'trace.jsonl').read_text(encoding='utf-8').splitlines()]
entry={r['call_id']:r for r in rows if r['event']=='rng_entry'}
ret={r['call_id']:r for r in rows if r['event']=='rng_return'}
byseq={r['seq']:r for r in rows if 'seq' in r};base=int(meta['base'],16)
assert analysis['entry_count']==analysis['return_count']==527 and analysis['write_count']==529
assert not analysis['helper_result_mismatch_call_ids'] and not analysis['unpaired_call_ids']
assert analysis['no_draw_calls']==1 and len(analysis['writes_outside_paired_helpers'])==3
assert analysis['candidate_route_counts']=={'native_or_unknown':472,'voice_candidate':23,'text_scope_candidate':32}
assert close['sample_unchanged_while_detaching'] and not close['debugger_attached'] and close['observer_detach']['abandoned_calls']==0

observed=next(r['value'] for r in rows if r['event']=='rng_watch_baseline');gaps=[]
for r in rows:
    if r['event']=='rng_write':
        if r['previous_observed']!=observed:gaps.append(r['seq'])
        reg='rcx' if r['rip'] in (base+0x3aa441,base+0x3aa3e6) else 'rax'
        assert (r['registers'][reg]&0xffffffff)==r['observed_after']
        observed=r['observed_after']
    elif r['event'] in ('rng_entry','rng_return') and r['rng_snapshot']!=observed:gaps.append(r['seq'])
assert not gaps and observed==2307227881==close['random_inputs']['global_18eb8b0']

seed_set=byseq[419];seed_restore=byseq[435]
assert seed_set['previous_observed']==seed_restore['observed_after']==1992406909
year,month,day=seed_set['date'];world45c=seed_set['world_inputs'][3]
date_value=(year*12+month)*30+day-31
assert date_value==73310 and world45c==56480 and seed_set['observed_after']==date_value+world45c==129790
scoped=[];current=129790
for identity in range(140,145):
    e=entry[identity];r=ret[identity];assert e['kind']=='range' and e['rng_snapshot']==current
    current=next_state(current);expected=(current&0x7fffffff)%e['argument']
    assert r['result']==expected and r['rng_snapshot']==current
    scoped.append({'call_id':identity,'argument':e['argument'],'result':r['result'],'new_state':current,'thread':e['thread']})
assert current==2323773429 and seed_restore['previous_observed']==current
assert seed_set['thread']!=seed_restore['thread']

direct=Counter(hex(entry[c['call_id']]['caller']-base) for c in analysis['calls'])
assert direct=={'0x2da9c3':179,'0x3b3779':23,'0x2855e1':5,'0x3cc0bc':100,'0x3c68e7':50,'0x3c685a':60,'0x3c6980':109,'0x3b350b':1}
ordering_calls=[c for c in analysis['calls'] if hex(entry[c['call_id']]['caller']-base) in ('0x3cc0bc','0x3c68e7','0x3c685a','0x3c6980')]
assert len(ordering_calls)==319 and all(entry[c['call_id']]['states'][-1]=='CStrategyState' for c in ordering_calls)
messages=Counter()
for c in analysis['calls']:
    for frame in c['unwind']['frames']:
        if frame['pc_rva']=='0x2d40a2':messages[hex(int(frame['nonvolatile']['rbx'],16)&0xffffffff)]+=1
comparisons=load(RUN/'end-comparisons.json')
assert all(not comparisons[k]['sampled_record_changes_excluding_known_runtime_pointer'] for k in ('after-run-b','after-camera-far-k','after-camera-near-k2'))
restored=load(TR/'rng-pairs-n-restored.json');boundary=load(TR/'boundary-restored-pairs-n.json')
assert not restored['debugger_attached'] and not restored['comparison']['sampled_record_changes_excluding_known_runtime_pointer']
assert boundary['stable_samples'] and boundary['observations'][-1]['random_inputs']['global_18eb8b0']==1138287528

image=(ROOT/'game-runtime-image.bin').read_bytes();md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
wanted={0x3d9799:'call 0x3aa390',0x3d979e:'mov dword ptr [rbx + 0x14], eax',0x3d97af:'call 0x2f0fc0',
        0x3d97c8:'call 0x2f0190',0x3d97d0:'call 0x3aa3e0',0x3d4f6d:'mov ecx, dword ptr [rcx + 0x14]',
        0x3d4f72:'je 0x3d4f7a',0x3d4f74:'call 0x3aa3e0',0x2f0fc0:'mov eax, dword ptr [rcx + 0x45c]',
        0x3c68e2:'call 0x3aa7c0',0x3c68fc:'movups xmmword ptr [rbx], xmm0',0x3c6855:'call 0x3aa7c0',
        0x3c6885:'mov dword ptr [rdi + 0x10], eax',0x3c697b:'call 0x3aa7c0',0x3c69a9:'mov qword ptr [rdi], rax',
        0x3cc0b7:'call 0x3aa7c0',0x3cc0bc:'lea ecx, [r14 + rax]',0x3b3506:'call 0x3aa7c0',0x3f7353:'call 0x3d1420'}
anchors=[]
for address,expected in wanted.items():
    ins=next(md.disasm(image[address:address+15],address));actual=f'{ins.mnemonic} {ins.op_str}';assert actual==expected,(hex(address),actual)
    anchors.append({'rva':hex(address),'instruction':actual,'bytes':ins.bytes.hex()})
last=ret[527];assert last['rng_snapshot']==2307227881 and entry[527]['rng_snapshot']==433855886
report='''原生随机调用与旬末结算追查（第十三轮，2026-10-05）

结论
完成一次真实游戏原生调用记录。527次范围/概率函数调用全部配对，参数与实际返回值验证通过；记录529次已知全局种子写入，未发现记录点之间未解释的种子跳变。本轮发现了游戏自身的“临时设置种子→结算→恢复旧种子”，以及进入下一轮准备阶段时的随机评分和列表换序。它们要求同步覆盖完整旬内流程及旬末收尾，不能只处理战场动画或常见语音点。
本轮没有加载上轮DLL，没有替换游戏指令或随机结果。采用硬件断点观察原函数入口、线程专属返回地址及全局种子写入，因此仍会改变调度时机；它不能证明未来DLL包装层对时序没有影响，也没有解决原A首次漏算战斗的根因。

1. 本次记录补齐了什么
上轮写入记录无法看见“不写种子就返回”的调用，也未保存函数真实参数及返回值。本轮为每个线程维护独立调用编号，记录入口参数、调用栈、返回寄存器和写入后的寄存器操作数。因而在存在其他线程写入时，不会把两个全局快照直接当作某次调用的独占状态转换。
独立测试先完成83次实际原生函数调用，涉及4个线程（其中2个并发），83个返回值与调用方收到的结果一致；覆盖4次不推进状态的范围调用、2次函数外写入、超时/取消清理。分析器额外用篡改返回值与删去返回记录作为反例，均正确识别。合成游戏上下文负载及未配对返回拒绝也通过。随后实机2秒静止挂接退出，抽查状态和种子不变，才开始本次推演。
游戏从203年8月11日、种子3510933083开始，记录到8月21日关闭报告并回到下令地图后结束。527次调用中，525次范围、2次概率；1次范围参数为1，返回0而不写种子，因此527次调用对应526次更新，再加3次直接设值，总计529次写入。
这些调用分布在15个线程编号。本轮断点记录里没有发现单次调用期间其他线程写入该种子的情况，但不能据此推断未挂调试器时也必然串行。

2. 旬末主动换种子，并在另一线程恢复
进入CTurnState时，0x3D9790先通过0x3AA390读取原种子1992406909，保存到小对象+0x14；随后将全局种子设为：
  ((年×12＋月)×30＋日－31)＋world[+0x45C]
本次日期203/8/21的日期计算值为73310，world[+0x45C]为56480，相加得到129790，与实际写入完全一致。这里仅确认字段偏移和计算式，未给world[+0x45C]额外命名。
接着0x285550路径做了5次范围抽取，参数依次为20、46、20、34、44，实际结果为3、41、12、20、41；私有计算重放与全部中间种子一致，最后临时状态为2323773429。
0x3D4F60随后从同类对象+0x14取回1992406909并恢复到全局。静态代码有“保存值非0才恢复”的条件，不能忽略这个边界。本次设置发生在线程42576，恢复发生在线程34120，说明该生命周期至少可以跨线程延续，不能用线程编号作为同步域身份。
0x285550的返回值继续参与0x2B4FA0中的数值计算和写回调用；其完整业务名称尚未确认。这是业务结算候选路径，不能归为表现随机。
意义：即使阶段前后的全局种子相同，中间也可能执行过有效结算。联机不仅要对齐最终种子，还要对齐临时种子的输入、作用范围、处理对象及顺序。

3. 日期已经到下旬，仍有内部随机排序
0x3F72C0→0x3D1420→0x3CB950的CStrategyState准备路径中，记录到319次范围调用：
— 100次在0x3CC0B7抽取0..49的数值，并与其他字段一起形成后续数值；
— 50次经0x3C68B0交换16字节元素；
— 60次经0x3C6810交换链表条目的32位数据；
— 109次经0x3C6930交换链表条目的指针数据，其中1次范围参数为1。
已确认后3类是随机选择后交换元素，会改变内部容器顺序。尚未完整确认这些容器各自对应哪类策略候选，也未将它们的全部内容纳入当前世界快照。
这些调用应继续保留在原生逻辑路径。仅比较武将、城市、军队的抽样记录，无法证明这些内部容器也完全一致；旬前共同起点必须覆盖准备阶段。

4. 表现候选也还有缺口
沿用第十二轮的窄化规则，本次32次调用属于人物台词文本候选，23次属于已知0x3B3774语音变体候选，472次保持原生或未知来源。
额外捕获到另一个语音相关入口0x3B3506，返回地址0x3B350B，本次出现1次；其返回值也参与选择后续语音分支。它不在原四处候选中，因此原方案不能宣称已经覆盖全部语音随机，尚未将这个新入口加入实际分流。
用户第一次报告完成时，游戏仍有CReportDisplayState，种子为433855886。关闭剩余报告后，台词路径又进行一次范围4抽取，结果1，种子变为2307227881。触发的精确UI时序还未穷尽，但已证明日期更新与可操作画面出现前后仍有收尾消耗；一到21日就停记录会漏掉它。

5. 与之前战场结果的比较及边界
本轮旬末785条抽样记录，排除既有军队显示对象指针后，与原正常B轮及近景/远景轮均无记录差异；与B轮、近景轮的焦点状态和任务抽样也一致。随机最终值不同。此次没有同步采集所有移动、伤害及演出事件，不能把旬末抽样相同升级为战场全过程相同。
本轮起始种子3510933083与旧轮不同，观测方法也不同，因此不是严格的种子或镜头单变量实验。原A首次战斗差异早于已知种子差异，仍不能归因于本轮发现的旬末流程。

6. 当前状态与后续方向
日志保存后，记录器恢复调试寄存器并正常退出；游戏候选位置及两个随机函数代码仍为原始内容。用户随后恢复34号档：203年8月11日张鲁，783条抽样记录恢复，调试器未附加，34号档哈希与备份相同。首次恢复检查读数尚不稳定而被拒绝，后续稳定检查通过；未保留第一次的具体字段差异，不据此推断原因。
恢复后的已知随机值为1138287528，与本轮推演起点3510933083不同；没有重写或修正。已知台词列表与工作标志为空，只作为候选空闲检查，仍不是已证明的同步屏障。
后续先把旬末临时种子生命周期、准备阶段的内部排序，以及新增语音入口纳入接入规则。逻辑顺序保持全局可核对，确认纯表现的调用再分流；随后再做实际DLL透传接入和严格起点对照。无需用户再重复本轮操作。
'''
manifest=['observe_rng_pairs.cpp','observe_rng_pairs.exe','make_rng_pair_observer.py','rng_pair_target_fixture.cpp','rng_pair_target_fixture.exe',
 'rng_pair_payload_fixture.cpp','rng_pair_native_fixture.h','build_rng_pair_observer.cmd','test_rng_pair_observer.py',
 'rng-pair-observer-validation.json','analyze_rng_pairs.py','test_rng_pair_analysis.py','rng-pair-analysis-validation.json',
 'start_rng_pair_trace.py','close_rng_pair_trace.py','survey-3d9790.txt','survey-3d4f60.txt','survey-3f5f50.txt',
 'disasm-2f0fc0.txt','disasm-2f0190.txt','survey-285550.txt','survey-2b4fa0.txt','survey-3c6810.txt','survey-3c68b0.txt',
 'survey-3c6930.txt','survey-3cb950.txt','survey-3d1420.txt','survey-3f72c0.txt','survey-3b3460.txt',
 'lockstep-traces/rng-pairs-idle-n/trace.jsonl','lockstep-traces/rng-pairs-live-n/metadata.json',
 'lockstep-traces/rng-pairs-live-n/trace.jsonl','lockstep-traces/rng-pairs-live-n/before.json',
 'lockstep-traces/rng-pairs-live-n/end.json','lockstep-traces/rng-pairs-live-n/paired-analysis.json',
 'lockstep-traces/rng-pairs-live-n/setter-unwind.json','lockstep-traces/rng-pairs-live-n/end-comparisons.json',
 'lockstep-traces/rng-pairs-live-n/closeout.json','lockstep-traces/rng-pairs-n-restored.json',
 'lockstep-traces/boundary-restored-pairs-n.json','publish_native_rng_trace.py']
evidence={'created':datetime.now().astimezone().isoformat(),'status':'NATIVE_TRACE_COMPLETE_NO_DLL_INSTALLED',
 'original_a_cause_proven':False,'two_client_determinism_proven':False,'complete_world_equality_proven':False,
 'observer_validation':{k:v for k,v in load(ROOT/'rng-pair-observer-validation.json').items() if k not in ('cases','payload_fixture')},
 'analysis_validation':load(ROOT/'rng-pair-analysis-validation.json'),
 'trace_summary':{k:v for k,v in analysis.items() if k not in ('calls','writes_outside_paired_helpers')},
 'state_sequence_unexplained_gaps':gaps,'direct_call_counts':dict(direct),
 'phase_counts':dict(Counter(e['states'][-1] for e in entry.values())),
 'thread_counts':dict(Counter(e['thread'] for e in entry.values())),
 'observed_interleaved_call_count':sum(bool(c.get('other_thread_write_sequences')) for c in analysis['calls']),
 'message_id_counts':dict(messages),'instruction_anchors':anchors,
 'temporary_seed_scope':{'saved_seed':1992406909,'calendar_value':date_value,'world_45c':world45c,'temporary_seed':129790,
                         'set_seq':419,'restore_seq':435,'set_thread':seed_set['thread'],'restore_thread':seed_restore['thread'],
                         'calls':scoped,'restore_value':1992406909,'nonzero_restore_guard':True},
 'setter_stacks':load(RUN/'setter-unwind.json'),'last_call':next(c for c in analysis['calls'] if c['call_id']==527),
 'new_voice_site_call':next(c for c in analysis['calls'] if entry[c['call_id']]['caller']==base+0x3b350b),
 'end_comparisons':comparisons,'closeout':close,'restore_check':restored,'restored_boundary':boundary,
 'manifest':[{'path':name,'sha256':sha(ROOT/name)} for name in manifest]}
for name,data in [('原生随机与旬末结算第十三轮.txt',report),('原生随机与旬末结算第十三轮证据.json',json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')]:
    with (OUT/name).open('x',encoding='utf-8') as f:f.write(data)
with (OUT/'双客户端实施路线.txt').open('a',encoding='utf-8') as f:
    f.write('\n锁步追查第十三轮：完整原生随机调用与旬末结算（2026-10-05）\n')
    f.write('真实推演527次原生调用全部配对，529次种子写入，无返回值不符或记录点间未解释跳变。发现CTurnState保存旧种子、按日期计算值加world+45C设临时种子、5次业务计算后跨线程恢复；下一轮CStrategyState准备阶段还有319次评分/容器随机换序调用，应保留逻辑域。另发现0x3B3506语音候选缺口及报告关闭后的额外台词抽取。785条旬末抽样记录与正常B轮一致，但隐藏排序、过程动画及原A首次漏算仍未证明。未安装DLL或改游戏随机，用户已恢复34号档，恢复后种子1138287528未改写。详见“原生随机与旬末结算第十三轮.txt”。\n')
print(json.dumps({'published':True,'calls':527,'writes':529,'ordering_calls':319,'temporary_seed':129790,'report_characters':len(report)}))
