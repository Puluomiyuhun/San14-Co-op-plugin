"""Publish measured transfer costs, native restore evidence and UX targets."""
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;OUT=HERE.parents[1]/'outputs/san14-link'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
perf=load(HERE/'checkpoint-transfer-performance.json')
tests=load(HERE/'checkpoint-transfer-tests.json')
reload=load(HERE/'reload-latency-analysis.json')
inplace=load(HERE/'inplace-checkpoint-feasibility.json')
assert perf['result']=='PASS' and perf['sample_count']==18 and perf['listeners_stopped']
assert tests['result']=='PASS' and tests['tests']==15
assert inplace['anchors_verified']==46
rows=[]
for x in perf['summary']:
    name='本机回环，无额外延迟/限速' if not x['synthetic_rtt_ms'] else f"模拟 RTT {x['synthetic_rtt_ms']} ms，双向各{x['synthetic_mbps_per_direction']} Mbps"
    rows.append(f"{name}：逐块请求 {x['median_seconds_by_window']['1']:.3f} 秒；每批4块 {x['median_seconds_by_window']['4']:.3f} 秒。")
table='\n'.join(rows)
report=f'''旬末同步延迟与B端体验
2026-10-06

结论
按当前首版路线，B底层需要一次近似读档的世界恢复，确实可能产生可见等待。目标是由工具自动完成，玩家不必每旬开菜单选档；自动恢复本身尚未接通，不能承诺无加载画面或无停顿。
当前测试档只有274920字节，网络传输已有可测和可优化的空间。更应重点测量的是原生清理、关系与显示重建、身份和菜单初始化以及最终核对。尚未获得真实双机端到端等待时间。

一、本轮实际开发：减少逐块往返等待
新增checkpoint_transfer.py，按最多8块、默认4块的小窗口请求检查点，逐块检查房间检查点标识与坐标，最终核对文件哈希。现有样本共10块，从10次逐块请求等待变为3个请求窗口；每个网络包仍受原64 KiB限制。
15项边界测试通过：正常/乱序、正确部分数据重试、重复或越界响应、旧检查点、内容损坏、半包断线、取消及进度回调异常等。
本轮交叉审查发现并补齐了取消时清理、损坏后接收器重建、额外尾包污染后续请求的问题。候选接收函数采用一次性传输连接，在成功和失败时均关闭；内容损坏后须用相同受信任清单重建接收器，不能盲目复用缓存。
这不是已接入的生产房间下载功能。测试使用研究Room子类，正式房间仍未开放原生游戏。后续保持房间常驻控制连接、独立建立检查点传输通道的会话整合仍要实现，不应把常驻控制连接直接交给这个一次性函数。

二、网络数据（每条件3次，报告中位数）
{table}
使用真实34号存档274920字节及58字节测试附加文件，JSON/Base64响应合计368095字节。所有18次传输最终重建字节一致。
这是本机TLS经字节流延迟/带宽模拟器的结果，不是真实跨公网测试。计时包含请求、文件接收、哈希校验和本地传输连接关闭；不包含连接认证、清单接收、A保存、B读档和游戏状态核对。
模拟器没有覆盖真实丢包、拥塞、弱网波动。附加文件只是明确标为未验证的测试数据，完整联机附加状态及长局存档的体积仍需测量。
原始存档离线zlib可压到{perf['zlib_level6_bytes']}字节，但本次网络测试没有使用这项压缩。压缩或差量传输只减少网络字节，不会自动消除B的恢复工作。

三、历史加载记录能说明什么
两次成功实机记录中，“反序列化已返回→首次本地玩家策略更新”的部分区间分别为6.063秒（张鲁）和5.687秒（切换刘备）。
这些区间不含等待用户发起操作，但包含调试停顿、多线程重设断点和日志开销；此前读取文件/反序列化、之后真正可交互首帧以及完整世界校验也没有全覆盖。不能当正式版本的预期耗时、上限或下限，更不能把它们直接加到上述模拟网络时间上当总延迟。
内部经过CTitleState/CLoadState，不能仅凭类名断言屏幕一定显示过主菜单。当前工具依赖用户先触发正常读档，尚无自动房间重载接口，也没有证实可以在现有地图内无缝刷新。

四、为何暂时不能用简单内存覆盖消除读档
新增46个静态字节锚点核对。读入前原生流程会析构/释放并重建动态注册表；读取动态对象时调用工厂创建对象；读入后重建人物ID索引和活动列表，再创建部队显示对象。
旧部队的显示指针Army+148会清空并重新建立。人物、部队、任务的增删以及显示关系需要一起处理；传A的指针、复用B旧对象指针或只修改兵力坐标均不足以保证完整结果。
加载失败还可能发生在部分对象已被写入之后，因此恢复不是天然原子事务。失败时继续留在同步等待，不能带着半恢复世界开放下一旬。
这些是静态关系和既有实际记录支持的限制，尚未证明完整世界覆盖，也未证明热替换绝对不可能。

五、预期体验和优化顺序
第一层：先实现正确的自动原生恢复。旬末显示“正在同步本旬结果”；后台接收与校验；B到达可安全恢复的原生边界后自动替换世界并恢复B身份；最后核对成功，双方同时开放内政。B不必每旬手动点读档。
第二层：保存B镜头位置、缩放等本地偏好，恢复后按数值还原；选中对象按稳定ID重新查找，已消失的部队则取消选择。不能跨恢复保留旧内存指针。该界面恢复尚未实现。
第三层：在A已生成不可变的权威检查点后，可让文件接收/校验与B尚未结束的展示部分重叠。真正替换对象必须等待安全边界；A也不能在B确认之前进入下一旬下令。不能把仍未处理的正式事件藏在动画播放后面。
第四层：用低开销计时确定瓶颈后，研究减少纯界面往返、重复静态资源加载。保留必要的清理、对象重建和业务初始化，不凭函数名字跳过整段postload。
进一步的完整业务差量原地同步另列后续路线，原生恢复保留为故障恢复手段。
同步提示只解释正在发生什么，不会凭空减少底层耗时。若每旬实测等待明显影响操作节奏，应先优化恢复路径，再扩大功能范围。

下一次原生闭环的计时要求
分别记录A安全边界/保存开始与结束、B收到首字节与末字节、重载开始/反序列化结束/身份建立/首个可交互画面、最终业务核对通过。
双方分别使用本机单调时钟统计各段耗时，不能直接相减两台机器的单调时钟。单独测B可见等待窗口，区分网络时间、游戏重建时间、用户操作和测试工具开销。
当前尚未进行这个低开销真实测量；本轮无需用户再重复读档或推进。

执行边界
两个子agent分别完成历史时延和原地恢复依赖审计；主agent实现并测试传输优化，再做交叉审查和修复。
未向游戏注入新代码、未调用游戏保存/重载、未推进日期；34号原档哈希未变。测试网络监听均已关闭。
'''
(OUT/'旬末同步延迟与体验方案.txt').write_text(report,encoding='utf-8')
e={'schema':'san14.sync-latency-progress.v1','date':'2026-10-06',
   'transfer_performance':perf,'transfer_tests':tests,'historical_load_timings':reload,
   'native_restore_dependencies':inplace,'automatic_native_reload_implemented':False,
   'seamless_in_place_restore_verified':False,'real_total_wait_seconds':None,
   'persistent_control_and_artifact_channel_integration':False,'manifest':[]}
for p in [OUT/'checkpoint_transfer.py',HERE/'test_checkpoint_transfer.py',HERE/'benchmark_checkpoint_transfer.py',
          HERE/'analyze_reload_latency.py',HERE/'reload-latency-analysis.json',HERE/'audit_inplace_checkpoint.py',
          HERE/'inplace-checkpoint-feasibility.json',HERE/'checkpoint-transfer-performance.json',HERE/'checkpoint-transfer-tests.json']:
    e['manifest'].append({'path':str(p.relative_to(HERE.parents[1])),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
write(OUT/'旬末同步延迟评估.json',e)
addition='''
旬末等待体验补充（2026-10-06）
首版目标由工具自动完成B的原生恢复，不要求玩家每旬手动选档；当前自动重载尚未接通，底层仍近似读档，不能承诺无停顿/无黑屏。原生动态对象、索引与显示重建有明确依赖，不能用简单内存覆盖替代。
已增加4块窗口传输候选并通过15项边界检查及18次真实存档的TLS传输；模拟80ms RTT/10Mbps下接收校验约0.58秒，模拟150ms RTT/2Mbps下约2秒。这些不是公网或全流程等待时间。常驻控制连接与独立传输通道整合仍待接入。
后续同步状态提示、B身份与镜头恢复、减少界面往返均需实现。应先测自动原生恢复的可见等待，再决定资源复用优化。完整证据见《旬末同步延迟与体验方案.txt》和《旬末同步延迟评估.json》。
'''
for name in ['主机权威与旬末同步方案.txt','双人联机当前缺口与使用形态.txt','开发剩余工作评估.txt']:
    path=OUT/name;text=path.read_text(encoding='utf-8');marker='\n旬末等待体验补充（2026-10-06）\n'
    if marker in text:text=text.split(marker)[0]
    path.write_text(text+addition,encoding='utf-8')
path=OUT/'主机权威旬末同步验证.json';v=load(path)
v['latency_research']={'evidence':'旬末同步延迟评估.json','transfer_tests':15,'transfer_benchmark_samples':18,
    'automatic_native_reload_implemented':False,'real_total_wait_seconds':None,
    'native_gameplay_enabled':False}
write(path,v)
print(json.dumps({'published':True,'native_reload':False,'tests':15,'benchmark_samples':18}))
