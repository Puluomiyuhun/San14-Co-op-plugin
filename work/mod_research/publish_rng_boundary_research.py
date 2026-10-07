"""Publish native RNG isolation feasibility and limits of the observed idle boundary."""
import hashlib,json,struct,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parents[1]/'outputs/san14-link';TR=ROOT/'lockstep-traces'
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
b=(ROOT/'game-runtime-image.bin').read_bytes();md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
expected={0x1aca99:'call 0x1ac850',0x1acaa1:'call 0x1a1520',0x1acad3:'cmp dword ptr [rbp + 0x28], r15d',
 0x1acb21:'call 0x1ab630',0x1acb70:'inc dword ptr [rdi + 0x20]',0x1acc94:'call 0x16f30',
 0x1a1544:'mulss xmm0, dword ptr [rip + 0x10ef3d0]',0x1a1598:'mulss xmm2, dword ptr [rip + 0x109d488]',
 0x2d9243:'jmp 0x3aa3f0',0x2d9261:'jmp 0x3aa7c0',0x3b3774:'call 0x3aa7c0',
 0x3aa47d:'add eax, dword ptr [rip + 0x154142d]',0x2923ee:'call 0x3aa460',0x2a3e30:'call 0x3aa460',
 0x1da7b1:'or word ptr [rbp + 0x196], 1',0x1da8e7:'call 0x2c0ab0',0x1d7117:'call 0x1da730'}
anchors=[]
for addr,want in expected.items():
    ins=next(md.disasm(b[addr:addr+15],addr));actual=ins.mnemonic+' '+ins.op_str
    assert actual==want,(hex(addr),actual,want)
    anchors.append({'rva':hex(addr),'instruction':actual,'bytes':ins.bytes.hex()})
assert struct.unpack_from('<f',b,0x129091c)[0]==3 and struct.unpack_from('<f',b,0x123ea28)[0]==3.5
tests=load(ROOT/'native-rng-isolation-validation.json');assert tests['result']=='PASS' and len(tests['cases'])==10
assert tests['fixture_sha256']==hashlib.sha256((ROOT/'native_rng_isolation_fixture.exe').read_bytes()).hexdigest()
idle=load(TR/'boundary-idle-l.json');after=load(TR/'boundary-after-rng-fixture-l.json');close=load(TR/'boundary-rng-l-closeout.json')
assert idle['observations']==after['observations'] and idle['stable_samples'] and after['gameplay_sample_unchanged']
assert not close['debugger_attached'] and close['global_rng']==3510933083
domains=load(ROOT/'rng-domain-classification-l.json')
assert domains['camera-near-rng-k2']['counts']=={'save_same_value':1,'other_message_context':85,'person_line_subtree':53,'tactic_voice_subtree':5}
search=[r for r in domains['camera-near-rng-k2']['events'] if r['message_id'] in ('0x2c46','0x2c56')]
assert len(search)==80 and all('0x4ca57' in r['frames'] and '0x1da8ec' in r['frames'] for r in search)
contract={'status':'DESIGN_ONLY_NOT_INSTALLED','logic_state':'Keep native module+0x18EB8B0 as the logic state, including native read-only consumers.',
 'presentation_state':'Separate private state. Never temporarily swap or rewind the shared global seed.',
 'candidate_routes':[
  {'rva':'0x1AB630','role':'Synchronous person-line scope entry/exit; preserve all native work and return values. Requires final callback/exception audit.'},
  {'rva':'0x2D9243','role':'Tail jump to percentage helper: use private native-equivalent helper only in confirmed presentation scope; otherwise original.'},
  {'rva':'0x2D9261','role':'Tail jump to range helper with the same conservative routing policy.'},
  {'rva':'0x3B3774','role':'Candidate narrow voice-variation draw; preserve argument, ABI and result use. Audit all callers before enabling.'}],
 'default':'Unknown origins remain native/logic. Message interpreter membership alone is not a presentation whitelist.',
 'required_before_live_test':['Exact build and instruction fingerprints, backed-up checkpoint, log-only context classification first.',
   'Preserve native calling conventions, return values, recursion, tail jumps, exception cleanup and thread isolation.',
   'Tag asynchronous tasks explicitly if scope crosses threads; TLS does not automatically propagate.',
   'Freeze new logical command submission, drain/join relevant logical jobs, then snapshot/hash/ack before release. Idle polling alone is not this barrier.',
   'Retain first-divergence and read/write auditing. A mutex cannot make multiple logic-worker draw order deterministic.'],
 'not_solved':['Full-world snapshot coverage','Original A first-batch skip','Worker scheduling and movement barrier','Complete random-source inventory','Two real client validation']}
(ROOT/'rng-domain-hook-contract-l.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
text='''共同起点与随机分流预研（第十一轮，2026-10-05）

本轮已完成只读边界检查器和独立的原生随机分流原型。原型证明分离状态能抵抗表现调用次数及线程交错的差异；没有向游戏注入补丁，尚未解决原A首次交战漏算，也没有证明双客户端锁步成立。本轮无需用户推进游戏。

1. 共同起点不能只看“回到大地图”
CPersonLineManager拥有独立待处理列表。0x1ACA10遍历列表，通过0x1A1520按条目延迟计数+0x1C、阶段计数+0x20和配置阈值分阶段处理；+0x28阻挡字段会使部分步骤等待，成功后计数增加，完成后另行出队。阈值使用配置值乘3.0、3.5，尚未把该配置单位认定为秒或帧率。
现有动态记录证明台词在CProgressState期间仍会消费随机数，因此只等读档报告关闭、只在旬前对齐一次种子，并不能消除后续表现调用的影响。
新增capture_sync_boundary.py只读核对规划状态、已知台词队列、战斗工作/待处理标志与特效队列。当前3次连续采样一致，台词队列为空，已知工作及特效标志为空。该检查刻意返回certified_sync_barrier=false：串行抽查为空不等于没有正在执行或将要入队的任务。现存交战名单仍有17条，不能把所有容器一律清空作为修复。
正式同步还需要阻止新的逻辑输入、等相关工作任务结束，在可控制的引擎边界完成逻辑快照/哈希/双方确认，再一起释放推进；单纯等待固定毫秒数不够。

2. 找到“读取种子却不抽取”的概率函数
0x3AA460把输入值、world+0x454以及全局0x18EB8B0相加，再进行同族变换和概率比较；它读取全局种子但不回写。只监测写入会漏掉它的使用，已找到两处静态直接调用（0x2923EE、0x2A3E30）。这两处本轮未做动态触发验证，也未确认其完整业务含义。
将该原生函数搬入独立测试进程，224项输入关系及“不改种子”检查通过。固定其余输入时，仅额外做一次共用随机抽取，128个测试输入中有64个概率输出改变。这是函数依赖关系的试验，不是实战分叉率，也不能据此倒推原A的原因。
这要求后续方案保留原地址供逻辑计算和只读消费者使用，表现调用另用私有状态；不能只在常见随机函数外面数调用次数，也不能把全部随机统一变成各线程独立状态。

3. 真实调用分类有进展，但不能把所有“消息”都隔离
近景144次写入可按已验证调用栈分为：人物台词子路径53次，战法语音子路径5次，其他消息路径85次，保存过程同值写回1次。远景主要写入记录对应56、5、85次，另3处缺口来源仍未捕获。
85次其他消息中，80次消息0x2C46/0x2C56出现在CCommandExecutionSearchNode→0x1D7060→0x1DA730的搜索命令链。该外围函数同时写人员/命令记录，说明消息生成与业务流程交织；尚未证明这些消息随机的输出是否只影响文本。因此不得把整个CMessageManager或所有表达式随机一律划为表现。
已确定表达式通过0x2D9243、0x2D9261尾跳转进入概率/范围随机函数，尾跳转会让直接返回地址表现为共同解释器调用点。仅用一个返回地址识别来源不够，需要保留可信的上层执行上下文。未知来源继续使用原生逻辑路径。

4. 独立原型做了什么，验证到了哪里
从当前游戏运行映像提取6个原生叶函数：取种子、设种子、无界抽取、范围抽取、概率抽取、只读派生概率。只重定位10处数据引用到测试进程私有内存，保持函数指令及返回规则。代码页只读可执行，状态页可写；没有打开或调用游戏进程。
10组测试全部通过：
— 近景真实日志144个状态写入的原生重放（验证状态序列，不重建未捕获的概率参数或历史返回值）；
— 3500项连续更新、56项范围边界、63项概率边界；范围小于2不推进状态，而概率阈值0/100仍推进状态；
— 224项只读概率依赖及128项额外抽取反例；
— 两套合成调用顺序中表现抽取次数不同，600次逻辑结果与最终状态全部相同；使用共用状态的对照组则分叉；
— 嵌套上下文、C++异常退出及未知调用默认回逻辑域；
— 2个表现线程共8000次抽取，与1个逻辑线程4000次抽取并发，逻辑结果保持参考序列；
— “临时保存/写回全局种子”的交错反例，确认它会抹掉期间合法的逻辑状态更新，不能用于正式隔离。
这些是独立进程内的原生算法与分流测试，不是600场战斗，也不是两个游戏客户端已经联机。多逻辑线程之间的确定顺序、Windows结构化异常、异步任务上下文传播、实际钩子正确性均未被这些测试证明。

5. 下一步具体接入设计
优先候选是为已观察的同步人物台词调用树标记表现上下文，在两个表达式尾跳点按上下文选择私有随机函数；战法语音的变体抽取采用更窄的单点候选。保持原函数执行、参数和返回值，未知调用走原生路径。若产生跨线程任务，需要显式携带上下文，不能假设thread_local会自动传递。
接入前先做只记来源、不改结果的上下文分类，审计回调、返回值、递归、异常及构建指纹；再进行可撤销的小范围游戏试验。不会因独立原型通过就直接改整个游戏随机系统。
本轮前后游戏仍为203年8月中旬张鲁测试局，已读字段稳定，已知随机值3510933083未改变，当前调试器未附加。原A首次漏算发生时已监测随机状态仍相同，所以交战调度/隐藏状态这条线仍须独立调查。
'''
manifest=['capture_sync_boundary.py','make_native_rng_fixture.py','native_rng_isolation_fixture.cpp','native_rng_isolation_fixture.exe',
 'native_rng_fixture_code.h','observed_rng_states_fixture.h','native-rng-fixture-source.json','native-rng-isolation-validation.json',
 'validate_native_rng_fixture.py','rng-domain-classification-l.json','rng-domain-hook-contract-l.json',
 'survey-1aca10.txt','survey-1a1520.txt','survey-1a49e0.txt','survey-2d91a0.txt','survey-1da730.txt','survey-1d7060.txt',
 'survey-2922b0.txt','survey-2a3ce0.txt','calls-3aa460.json','domestic-route-survey.json','publish_rng_boundary_research.py',
 'lockstep-traces/boundary-idle-l.json','lockstep-traces/boundary-after-rng-fixture-l.json','lockstep-traces/boundary-rng-l-closeout.json']
e={'created':datetime.now().astimezone().isoformat(),'status':'OFFLINE_NATIVE_PROTOTYPE_PASS_LIVE_HOOK_NOT_INSTALLED',
 'original_a_root_cause_proven':False,'certified_sync_barrier':False,'two_real_clients_verified':False,
 'anchors':anchors,'fixture_validation':tests,'candidate_boundary':idle,'post_test_boundary':after,'current_read_only_closeout':close,
 'classification_counts':{k:v['counts'] for k,v in domains.items()},'search_command_context_draw_count':len(search),
 'hook_design':contract,'manifest':[{'path':n,'sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest()} for n in manifest]}
for name,data in [('共同起点与随机分流第十一轮.txt',text),('共同起点与随机分流第十一轮证据.json',json.dumps(e,ensure_ascii=False,indent=2)+'\n')]:
    with (OUT/name).open('x',encoding='utf-8') as f:f.write(data)
with (OUT/'双客户端实施路线.txt').open('a',encoding='utf-8') as f:
    f.write('\n锁步追查第十一轮：共同起点及原生随机分流原型（2026-10-05）\n')
    f.write('已解析人物台词分阶段队列，新增只读候选空闲检查，明确抽查空闲并非同步屏障。确认0x3AA460读取共用种子却不更新，不能只靠写入次数推断随机影响。其他消息随机中80次出现在搜索命令链，禁止整块隔离消息解释器。\n')
    f.write('独立进程重定位6个原生叶函数，10组测试通过，含真实144状态重放、分域后600次逻辑抽取一致、两个表现线程8000次抽取不扰动单逻辑线程。提出保留原地址作为逻辑状态、确认表现调用使用私有状态的候选接入；尚未安装补丁或完成实际钩子验证。原A根因仍未解，后续先做只记来源的上下文审计。游戏本轮未推进、已知数据未改动。详见“共同起点与随机分流第十一轮.txt”。\n')
print(json.dumps({'published':True,'native_cases':len(tests['cases']),'anchors':len(anchors),'manifest':len(manifest),'report_characters':len(text)}))
