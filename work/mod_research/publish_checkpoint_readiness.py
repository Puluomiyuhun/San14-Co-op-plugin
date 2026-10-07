"""Publish current native checkpoint evidence and remaining-work assessment."""
from pathlib import Path
import hashlib, json
HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'outputs'/'san14-link'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
a=load(HERE/'native-checkpoint-audit.json')
i=load(HERE/'native-checkpoint-inventory.json')
w=load(HERE/'native-save-worker-shadow.json')
assert len(a['anchors'])==30 and len(a['arrays'])==39
assert i['representative_objects']==117 and i['status_only_array_samples']==17
assert i['same_pointer_tables_two_reads'] and not i['complete_world_verified']
assert w['result']=='PASS' and w['cases']==12 and not w['real_storage_tested']

report='''原生存档检查点接入进展
更新：2026-10-06

当前结论
已把旬末全量同步所需的原生保存入口、结束条件和主要存档分发结构具体定位出来。现有实测存档调用栈与当前游戏代码核对一致，因此可以继续沿“主机原生保存，客机受控重载”的路线实现。
这次没有调用真实游戏保存或加载，没有安装自动同步模块，也没有证明存档已覆盖联机所需的全部状态。自动导出、B自动重载、两个真实客户端持续联机仍未完成。

一、保存完成不能靠旧标志判断
两份历史实际记录均在CSaveState里经过同一条后台工作链：
508CA0 → 2EE740 → 2F7A10 → 2F7B50 → 2E7D30 → CWorldData序列化2F9610。
2EE740返回的是准备阶段的归档对象或空值，不代表文件已经交给存储层。
随后508CF8调用2FCE40，后者执行流的收尾、存储提交与清理，最后把状态返回。工作线程只将状态恰好为0判为成功，在508D1C写入结果标志，508D22处才能观察到本次发布的值。
这个全局标志在上述过程结束前可继续保留旧值。因此后续适配必须绑定本次保存请求、实际工作线程/调用次序和目标文件，不能把旧值1误判成本次保存完成。
机器码隔离执行覆盖12种情形，包括准备失败、存储失败、负/正状态、临时/复用归档、已有成功标志等。执行的是原生工作线程及收尾函数；底层存储、序列化、锁和析构均用明确的测试替身代替。12项通过不等于实际磁盘保存已成功。
特别是人为构造“无流对象但状态为0”时，原生工作线程也会报成功；这进一步说明还必须验证当前文件和本次任务关联。该构造不是实际游戏出现过的问题。
存储成功也不等于Steam云已上传或硬件断电持久性已验证。

二、存档覆盖有了可核对的清单
原生保存与加载都会进入2E7D30分发器。当前格式号为0x5C，满足已发现的四个版本条件。
静态代码中提取到39组固定指针数组，共60070个槽位。其中包括：
人物1651槽、部队CTroopsData 501槽、军队单位CArmyUnitData 501槽、地图格48400槽、城市52槽、势力52槽、军团52槽、区域CAreaData 501槽，以及提案、历史、日志、异民族等。
槽位含无效项、占位项及基础规则表，不能当成60070个活跃对象，也不能据此断言每个对象所有字段都写进存档。
只读核对当前真实游戏：39组指针表前后两读一致，每组首/中/尾各抽一个对象，共117个对象的RTTI和序列化虚函数已确认。城市/人物/部队/地图等对应各自的序列化入口。
其中17组的抽样对象使用同一个只检查流状态、不写对象载荷的方法。不能把“分发器遍历了这个表”误算为“表的所有内存都保存了”；这些表的规则来源与版本一致性仍须单独核对。
固定数组之外还有动态对象管理入口、额外管理器入口和CWorldData世界状态入口。动态管理结构并非在起始地址放普通RTTI虚表，本轮按原生代码处理为独立结构，没有猜读其类型。
这份清单是后续覆盖审计的起点，不是完整世界哈希，也不是全字段存取往返验证。

三、还要接通的实际链路
1. 在真正可下令的旬末边界锁定新命令；等待正式事件处理完，避免仍在工作线程/报告界面中保存。
2. 通过游戏支持的原生状态流程启动本次保存，使用专用同步文件或事先保护的槽位；不覆盖用户原档。
3. 跟踪本次保存工作线程完成、原生保存状态退出，核对日期、命令序号、文件大小和哈希，才向B发布。
4. B先退出自身临时推演到可重载边界，丢弃临时世界，按已实测的身份初始化路径加载A的世界并保留B势力。
5. 核对加载后的权威业务数据、共同规则和必要附加状态；更新加载实例与执行记账，拒绝旧命令、旧事件、旧回执。
6. 验证反复加载不会把旬初提案、任务或结算重复触发。当前身份切换曾验证过基本菜单，尚不能代替这个反复重载验收。
只有完整链路核对成功才能开放下一旬内政。需要附加哪些未保存的共享运行状态，仍以原生保存/加载覆盖实证为准。

本轮游戏收尾
游戏仍为203年8月中旬（原始日11）、张鲁，位于可下令状态。34号存档哈希未变。本工具仅以只读权限检查内存，未附加调试器、未调用原生游戏函数、未推进日期。
当前不需要用户再做一次出征、赏赐或推进测试。
'''
(OUT/'原生存档检查点接入进展.txt').write_text(report,encoding='utf-8')

assessment='''双人联机剩余工作评估
更新：2026-10-06；以A主机权威、B允许临时战斗分歧、旬末全量重载校正为基线。

阶段判断
已有多个关键点的可行性证据，但尚处于将原生链路接成完整循环的阶段，不是最后打包阶段。
已实际验证过“同档换成本地刘备身份并使用基本菜单”、受控出征、受控赏赐/第二势力赏赐；这些都是单机环境中的有界测试。
房间/TLS、命令执行记账和旬末检查点协议有独立测试，经济/AI适配有静态、离线或隔离执行证据；尚未在两个真实客户端上连成可玩的房间。
不再追求首版战斗过程完全锁步，消除了一个难以界定的前置研究关卡。但A最终世界完整替换B、即时操作不乱序重复、两个势力各自能操作，仍是必需项。
不以脚本数量或测试条数换算完成百分比；目前也缺少稳定原生闭环的数据，不能可靠报剩余天数。

剩余六类主要工作（按开发优先级）

1. 旬末原生检查点与B受控重载【最大原生关卡】
已有：存档文件传输；一次真实刘备身份进入；保存/加载入口与39组固定数据分发；保存完成条件的隔离执行验证。
还缺：自动原生保存、完成与文件关联、B安全退出临时战局并自动重载、字段覆盖/共享附加状态核对、反复加载不重复结算、加载实例与旧消息隔离。
验收：先不新增命令，让A推进一旬，B完整接收同一旬末世界且仍为B；下一旬可以继续。然后连续重复。

2. 两个人类势力的游戏规则与AI控制【必须在多人持续推演前接入】
已有：4条AI外层路线候选；两个人类势力的经济规则候选；9城收入/费用差异通过完整预览函数离线复算。
还缺：原生持续接入；AI不会擅自给A或B势力下令，玩家委任仍正常；双方经济规则一致并在真实结算验证；特殊模式/势力灭亡等处理。
验收：B视角变化不会改变权威经济或AI控制权；连续多旬中两个人类势力无额外AI决策。

3. 玩家操作的持续捕获与同步【范围最大的功能接入工作】
已有：出征、赏赐的受控真实执行，内政结构解析，权限预检，去重执行记账。
还缺：接入日常菜单操作；A裁定顺序，双方各执行一次；远程命令不循环上报；错误/过期状态处理；按命令族支持内政、任命、人才、军令、外交等，确保未适配命令不会造成隐藏分叉。
验收：先形成赏赐+出征白名单闭环，再按共享入口批量扩展。不会要求用户把每个按钮逐一重复演示；仅在无法离线确认或需要实际端到端验证的关键路径安排测试。
首个受限原型会明确限制可用操作，不能宣称完整内政支持。

4. 准备、实际暂停与正式事件【协议已有，原生接入不足】
已有：双方准备屏障、事件归属/答复、断线进入等待的协议检查。
还缺：准备状态真正拦住游戏继续下令/自行推进；A负责产生B的正式事件；招募、外交等带选择的结果由正确玩家处理，另一方实际等待；B临时推演产生的事件不能独立执行正式决定。
验收：例如第5天A事件、第7天B事件，主机日期和正式选择保持顺序，每个结果仅应用一次。B是否刚好出现同一个原生弹窗不能成为正确性前提。

5. 两台真实机器联调与恢复【尚未完成】
已有：本机两个网络客户端TLS、重传和连接恢复；原生命令独立记账；同一服务进程内的旬末检查点重连测试。
还缺：两个真实游戏进程连续多旬；一端慢、断线、重复消息、加载中断；检查点持久化、主机重启恢复和存档会话恢复。
验收：失联或不确定的执行结果进入等待/受控恢复，不能自动重复扣钱、下令、加载或进入下一旬。
已有命令记账的持久性不能替代整场房间和检查点流程的重启恢复。

6. 原生适配模块和联机助手交付【窗口未产品化】
已有：研究脚本、少量原生试验、模块接口设计。
还缺：可持续运行的游戏内适配模块；助手窗口、创建/加入房间、选势力、状态提示、错误恢复；连接方式、版本检查、安装/退出清理和打包。
默认目标仍是额外助手窗口配合原生游戏菜单。是否最终以持久DLL作为适配载体，要在原生循环稳定后落实；当前研究工具不等于可分发MOD安装包。
初期受限原型可以手动启动游戏和选择同步测试档；自动进图和顺滑每旬重载须经过验证后再开放。

接下来按四道验收推进
第一道：原生导出/重载往返，包括身份、日期、状态覆盖和无重复结算。
第二道：两个人类规则接入后，两个真实客户端完成无新增命令的一旬，并接上下一旬。
第三道：赏赐和出征贯穿真实内政—准备—推演—校正流程，并处理必须面对的正式事件；未支持功能明确拦截。
第四道：扩大命令族、连续多旬与掉线恢复，再完善助手和安装包。
第一道如果不能可靠成立，先修正检查点方案，不继续堆积菜单功能。严格战斗锁步留作后续体验改进，不作为上述首版验收门槛。

本轮新增成果及证据边界
30个保存/加载代码锚点核对；2份既有真实保存调用栈一致；39组指针表、117个代表对象只读检查；原生保存工作线程/收尾函数的12种隔离执行情形通过。
这些结果减少了原生存档接入的不确定性，但没有完成自动原生保存、自动B加载或完整双机试玩。
'''
(OUT/'开发剩余工作评估.txt').write_text(assessment,encoding='utf-8')
e={'schema':'san14.native-checkpoint-readiness.v1','date':'2026-10-06','audit':a,'live_inventory':i,'worker_shadow':w,
   'native_export':False,'native_guest_reload':False,'full_state_coverage':False,'two_real_clients':False,
   'remaining_work_groups':6,'first_priority':'Native authoritative checkpoint export/reload roundtrip',
   'manifest':[]}
for name in ['audit_native_checkpoint.py','verify_native_save_worker.py','native-checkpoint-audit.json',
             'native-checkpoint-inventory.json','native-save-worker-shadow.json','publish_checkpoint_readiness.py']:
    p=HERE/name;e['manifest'].append({'path':str(p.relative_to(HERE.parents[1])),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
write(OUT/'原生存档检查点接入证据.json',e)
profile={k:a[k] for k in ['schema','game_sha256','captured_image_sha256','format_version','anchors','arrays',
                         'save_observation_points','candidate_export_requirements','native_full_coverage_verified',
                         'automatic_export_implemented','automatic_guest_reload_implemented','limits']}
profile['schema']='san14.native-checkpoint-research-profile.v1'
profile['gameplay_enabled']=False
write(OUT/'checkpoint_native_profile.json',profile)
path=OUT/'主机权威旬末同步验证.json';current=load(path)
current['native_checkpoint_research_2026_10_06']={'code_anchors':30,'fixed_arrays':39,'rtti_samples':117,
    'save_worker_shadow_cases':12,'evidence':'原生存档检查点接入证据.json',
    'real_native_export_completed':False,'real_guest_reload_completed':False,'full_native_coverage_verified':False}
write(path,current)
path=OUT/'双人联机当前缺口与使用形态.txt';text=path.read_text(encoding='utf-8')
marker='\n本轮原生检查点补充（2026-10-06）\n'
if marker in text:text=text.split(marker)[0]
text+=marker+'保存工作链、完成条件与39组数据分发已定位，117个代表对象只读核对和12种原生控制流隔离执行通过；自动保存/重载、完整覆盖和真实双机循环仍未完成。详见《原生存档检查点接入进展.txt》和《开发剩余工作评估.txt》。剩余六类主要工作，下一步先过原生检查点往返验收。\n'
path.write_text(text,encoding='utf-8')
print(json.dumps({'reports_written':2,'evidence':True,'native_gameplay_enabled':False,'remaining_groups':6}))
