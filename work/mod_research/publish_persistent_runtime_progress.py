"""Publish verified offline progress; never touches a game process or game save."""
from pathlib import Path
from datetime import datetime
import hashlib,json,shutil
P=Path(__file__).resolve().parent;OUT=P.parents[1]/'outputs/san14-link'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf8'))
def record(p):return {'path':str(p.resolve()),'sha256':sha(p),'data':read(p)}
def verify_sources(mapping):
 for name,digest in mapping.items():assert sha(P/name)==digest,name
def latest(folder):
 path=sorted((P/folder).glob('*/result.json'))[-1];r=record(path)
 assert r['data']['result']=='PASS' and r['data']['sources_unchanged'],path
 verify_sources(r['data']['source_sha256']);return r
def main():
 runtime=latest('checkpoint_persistent_runtime_runs');physical=latest('checkpoint_persistent_physical_owner_runs')
 assert len(runtime['data']['cases'])==27 and len(physical['data']['cases'])==16
 queue=record(P/'checkpoint_dynamic_native_queue_handoff.json')
 guards=record(P/'checkpoint_dynamic_runtime_guards_handoff.json')
 research=record(P/'checkpoint_dispatch_handoff_research_handoff.json')
 review=record(P/'checkpoint_persistent_runtime_independent_review.json');verify_sources(review['data']['source_sha256'])
 verify_sources(guards['data']['sources']);verify_sources(research['data']['new_files'])
 # Independent component tests are separate evidence, not extra real-game wins.
 frozen=read(P/'checkpoint_complete_live_owner_v2_handoff.json');verify_sources(frozen['source_sha256'])
 assert sha(P/'checkpoint_complete_live_owner_v2.dll')==frozen['dll_sha256']
 stamp=datetime.now().isoformat(timespec='seconds')
 evidence={'schema':'san14.persistent-runtime-progress.v1','updated':stamp,
  'runtime_combination':runtime,'physical_owner':physical,'queue_component':queue,'guards_component':guards,
  'native_handoff_research':research,'independent_review':review,
  'fixture_binary_sha256':sha(Path(runtime['path']).parent/'fixture.exe'),
  'game_access':False,'frozen_v2_unchanged':True,'six_slot_owner_integrated_offline':True,
  'actual_queue_adapter_integrated_offline':True,'dynamic_guards_tested_separately':True,
  'dynamic_guards_integrated_into_full_runtime_chain':False,'production_generation_publication':False,
  'native_scheduler_handoff_verified':False,'live_handoff_recorder_installer_available':False,
  'real_repeated_load':False,'full_world_verified':False,'actual_map_cover_verified':False,'two_clients_playable':False,
  'important_limits':[
   'Native game queue/load/deserialization/Title/UI bodies are explicit own-process doubles. Full runtime fixture attachment/storage guards remain doubles; dynamic guards have separate real-bridge tests only.',
   'Bootstrap forwards native originals and has no Session observers. Only fixture publishes complete generations after initialization. No production activation API was added.',
   'Frozen Set::Publish may roll back the current failed slot. Permanent configurations/contexts remain; successful earlier slots are retained. Owner records attempted vs successful publication and uncertainty.',
   'Archive instructions exercised in Unicorn are offline game code, with explicit User/Windows API doubles. The tap decoder/sampler/analyzer is not a live recorder installer.',
   'Native parent detach and both Title worker joins still require correlated live observation and task-generation binding. Zero active counters or reaching a common dispatcher tail does not prove handoff.',
   'No successful V2 hooks, once records or game files were modified. Future game installation needs a fresh reviewed attachment; do not replace retained V2 slots.']}
 (P/'checkpoint_persistent_runtime_handoff.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'常驻加载接线证据.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'常驻加载接线进展.txt').write_text('''常驻加载接线进展
更新：'''+stamp+'''

本轮继续由三个agent并行，主agent负责整合与验证。重点仍是让同一游戏进程能够反复接收主机检查点。

实际完成
1. 接回真实加载队列适配器：授权、原生排队、返回菜单检查、队列解析、停止与异常处理均走现有核心；替代了上一轮测试中的布尔授权/直接插队列。独立组合11项通过。
2. 新常驻物理入口模块：一次配置和发布六个入口，记录原始转发目标与页面保护；每次同步不重装入口。启动先只转发原调用，Session准备好后才允许测试代进入，消除了半初始化对象暴露窗口。16项测试通过。
3. 将以上两块接入输入硬件观察、动态文件读取、身份转换、回图确认的两次连续加载流程。最终27个组合场景全部通过；旧Session和旧队列的有效报告字段在下一代后保持不变。
4. 动态运行检查模块独立完成30项测试：当前B的日期/身份与待载A的日期/身份分别检查；实际桥回调的线程、代次、阶段、调用编号以及同回调队列授权均核验。这一块尚未与完整owner/Session全链合并。
5. 找到真正原生收尾需要观察的位置。User返回之后还有callable返回、worker完成和父调度器解除关联；普通公共尾端也可能来自任务暂时让出执行。Title还有两个分别需要等待的worker。已交付离线采样/解码/分析工具，核对13个指令位置，运行两条归档机器码路径，12项测试通过。

审查修正
独立审查推动了bootstrap启动顺序修正；同时准确记录了旧槽发布器在失败时可能回滚当前槽的行为，所有已配置回调和对象仍保持常驻。测试中还定位到报告结构填充字节造成的比较误报，改为逐一比较全部命名字段，没有忽略实际状态。

边界
以上为独立测试进程或归档机器码模拟中的验证。游戏反序列化、原生菜单/界面重建仍有明确测试替身；两次真实游戏加载还没完成。动态检查模块的30项是独立组件测试，不能当作已接入完整运行链。记录工具还没有实机安装器。
本轮未触碰运行游戏、Steam存档、已成功V2模块或一次性记录。

下一步
先准备并验证原生任务收尾的实机只读记录，配对父调度器结束与Title两条任务；再把动态检查、存储绑定、进程通信和已证明的任务归属接成完整运行模块，开放连续两次实机加载。之后才是双客户端空命令一旬和赏赐/出征受限试玩。
''',encoding='utf8')
 assessment=OUT/'开发剩余工作评估.txt';backup=P/'versions'/('remaining_work_before_runtime_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir(parents=True)
 if assessment.exists():shutil.copyfile(assessment,backup/assessment.name)
 assessment.write_text('''双客户端原型剩余工作
更新：'''+stamp+'''

当前位置
实机：单次A保存、B自动加载并切换刘备、回到可下令大地图已有成功证据。赏赐/出征有受控执行测试。
离线：常驻六入口、实际输入观察和队列适配器、文件校验、身份转换、回图确认已组成两代流程，27个场景通过。动态运行检查另有30项组件测试。原生结束条件已定位到具体任务与指令路径。
仍未完成：真实同一进程连续加载；两个真实客户端完整可玩。现在不能把测试程序当成可分发联机MOD。

1. 连续加载正式接入【当前主线】
已补：常驻物理入口、纯转发bootstrap、真实队列接线、动态检查模块。
还缺：任务归属/收尾的真实配对记录；把动态检查、存储绑定、IPC/数据ABI、Session/Controller生产激活接成完整运行模块。必须防止迟到旧任务误入新代，不能用计数归零代替。
下次明确验收：同一真实游戏进程接收两份正式存档，每次自动回到正确日期和B势力并可操作。

2. 完整世界校验与等待画面
军队、城市、武将、任务及其他世界数据仍需完整核验；仅君主和日期正确不够。
窗口/无边框下保留地图画面、覆盖底层加载页面以及同步时停止操作，尚未在真实游戏验收。

3. 玩家正常操作与两个人类势力
把正常菜单操作自动捕获、交给A排序并在两端各执行一次，避免重复上报/扣款/下令；持续限制AI代替两个玩家决策。
首版先赏赐和出征白名单，其他内政、人才、外交按命令族扩展，尚未全支持。

4. 准备、时间推进和选择事件
准备后停止新增命令，双方命令执行完才推进；招募等事件由对应玩家处理，另一方等待；A确定正式结果，B不能把本地临时结果独立提交。

5. 双机联调与交付
两台机器连续多旬验证，慢客户端/断线/加载失败的恢复；最后接好额外助手窗口里的创建房间、加入、选势力与安装打包。

顺序：连续两次真实加载 → 两客户端无命令一旬 → 赏赐+出征受限试玩 → 扩充命令和优化体验。
不按测试数量推算完成百分比或剩余天数。当前仍不能直接双人正常开局。
''',encoding='utf8')
 resume_path=P/'mainline_20261007_live_resume.json';resume=read(resume_path)
 resume['persistent_runtime_offline']={'updated':stamp,'handoff':str(P/'checkpoint_persistent_runtime_handoff.json'),'runtime_result':runtime['path'],'runtime_cases':27,'physical_cases':16,'guards_component_cases':30,'actual_queue_adapter_integrated':True,'full_chain_dynamic_guards_integrated':False,'native_scheduler_handoff_verified':False,'game_access':False}
 resume['next_concrete_integration']=[
  'Preserve successful V2 hooks, frozen sources and once claims. Never hot-swap the retained six game slots.',
  'Use dispatch handoff research profile to build a reviewed read-only native recorder. Correlate fresh/resume task provenance, actual User worker parent detach and both Title worker joins.',
  'Integrate separately tested dynamic runtime guards, local storage Gate, IPC/data ABI and prepared Session/Controller behind the new physical owner bootstrap; never expose partially initialized generations.',
  'Implement production task-bound handoff and activation only after exact native ownership/termination evidence, not active-count checks. Production remains closed today.',
  'Then verify two genuine checkpoints in one game process, complete-world equality, window/borderless map cover/input hold, and two-client empty-order period.',
  'Wire dual-human AI/economy, continuous reward/sortie whitelist and event waiting before claiming a playable prototype.']
 resume_path.write_text(json.dumps(resume,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({'published':True,'runtime_cases':27,'physical_cases':16,'guard_component_cases':30,'frozen_v2_unchanged':True,'game_access':False}))
if __name__=='__main__':main()
