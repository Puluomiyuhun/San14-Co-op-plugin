"""Freeze current offline composition evidence and a usable remaining-work list."""
from pathlib import Path
from datetime import datetime
import hashlib,json,shutil
P=Path(__file__).resolve().parent
OUT=P.parents[1]/'outputs/san14-link'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf8'))
def record(p):return {'path':str(p.resolve()),'sha256':sha(p),'data':read(p)}
def main():
 result_path=sorted((P/'checkpoint_dynamic_complete_runs').glob('*/result.json'))[-1]
 result=record(result_path);r=result['data'];assert r['result']=='PASS' and r['sources_unchanged']
 for name,digest in r['source_sha256'].items():assert sha(P/name)==digest,name
 frozen=read(P/'checkpoint_complete_live_owner_v2_handoff.json')
 for name,digest in frozen['source_sha256'].items():assert sha(P/name)==digest,name
 assert sha(P/'checkpoint_complete_live_owner_v2.dll')==frozen['dll_sha256']
 refs=[P/'checkpoint_dynamic_files_handoff.json',P/'checkpoint_persistent_authorized_handoff.json',P/'checkpoint_persistent_planning_observer_handoff.json',P/'checkpoint_dynamic_session_independent_review_20261007-173914-380008.json']
 optional=P/'checkpoint_persistent_input_hwbp_handoff.json'
 if optional.exists():refs.append(optional)
 stamp=datetime.now().isoformat(timespec='seconds')
 handoff={'schema':'san14.dynamic-complete-offline-handoff.v1','updated':stamp,'result':result,
  'fixture_binary_sha256':sha(result_path.parent/'fixture.exe'),'component_handoffs':[record(p) for p in refs],
  'source_sha256':r['source_sha256'],'frozen_v2_unchanged':True,'game_access':False,
  'native_core_composition_verified_offline':True,'actual_hardware_prefetch_verified_offline':True,
  'dynamic_file_date_identity_and_planning_verified_offline':True,
  'native_scheduler_fence':False,'production_owner_installer':False,'actual_native_queue_adapter_integrated':False,
  'repeated_game_load_verified':False,'world_verified':False,'map_cover_in_game_verified':False,'two_clients_playable':False,
  'successor_files':['checkpoint_dynamic_file_profile','checkpoint_dynamic_load_request_commit','checkpoint_dynamic_cc_load_observer','checkpoint_dynamic_cc_load_lifecycle','checkpoint_dynamic_title_identity_adapter','checkpoint_dynamic_native_session','checkpoint_persistent_authorized_controller','checkpoint_persistent_planning_observer','checkpoint_persistent_input_hwbp'],
  'test_only_files':['checkpoint_dynamic_admission_fixture.inc','checkpoint_dynamic_planning_fixture_helpers.inc','checkpoint_dynamic_complete_fixture.cpp'],
  'integration_notes':[
    'One immutable six-slot bridge/router. A fresh dynamic Session, logical adapter, input Controller, HW Context and planning Observer for every generation; all retained.',
    'Dynamic Session has no installer and ActivateForOfflineExercise returns false in production. Controller production activation also false.',
    'User physical forwarding goes through once-configured CheckpointPersistentAuthorizedOriginal. Session userObservation Before/After/Finally routes to the generation Controller; Controller next callbacks route to planning.',
    'SessionPort status reports actual Session initialized/armed/error/stop, and bind_menu calls actual Session.BindQueuedMenu. Context and generation are retained independently.',
    'Old HW provider has a process-global one-shot installed pointer. Persistent HW successor registers one permanent handler and uses independent address-bound Contexts with TLS ownership; uncertain restore blocks that thread.',
    'Owned native queue/load/Title/new-User bodies remain doubles. Production queue adapter, owner ABI, IPC and callback-time dynamic guards must be wired separately.',
    'Do not hot-swap retained successful V2 hooks or clear once claims. Future live test needs a new separately reviewed owner and fresh attachment.',
    'Full-world observation, visible map cover/input hold and room READY never follow from these component receipts alone.']}
 (P/'checkpoint_dynamic_complete_handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'动态连续加载组合证据.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding='utf8')
 report='''动态连续加载组合进展

本轮已把输入检查、提交加载、实际文件校验、加载观察、势力转换和回到大地图的确认接在同一条原生核心测试链上。同一进程固定保留入口，每次加载使用新记录；连续两代可成功，20个组合场景通过。

直接完成的内容
1. 文件大小、摘要、日期、势力、君主和军团信息已进入C++核心；第二代使用不同字节、大小、日期和君主，不再固定依赖34号档数据。当前保留已验证的专用槽位63与对应文件名，上限16MiB。
2. 输入授权控制器按每次真实调用绑定本代会话。实际执行硬件输入观察、私有票据、授权后排队及会话绑定；不能用另一代的调用冒充本代。
3. 回图观察器直接核对本次提交、文件读取、工作线程返回、身份转换回执，再检查当前大地图的日期、势力、君主和军团。
4. 完整组合测试暴露并修复了旧输入检查器的“一进程只允许初始化一次”限制。新检查器只安装一次永久异常处理入口，但允许每次检查拥有独立记录；不重置旧记录。
5. 补测已有玩家操作、缺少输入观察、原生异常、错误摘要、错误军团、旧报告界面、地址复用等路径。前置拒绝不提交加载；异常后六个调试寄存器恢复；回图后不会重复排队。

证据边界
这些是独立测试进程中的真实C++核心、文件哈希、原子修改、硬件观察和线程调用。游戏的排队、世界反序列化、Title及界面重建用明确的测试替身；测试中的第二份内容也不是可导入游戏的正式存档。因此它证明核心接线能够循环，不证明真实游戏连续两旬已经成功。
本轮没有访问游戏、Steam存档或改动已实测成功的V2模块。

下一关
把新核心装入正式常驻运行模块，接回已验证的原生排队适配器、每代动态检查、进程内通信和下一次加载交接条件，然后做真实连续两次加载。现在还不能直接把测试程序当MOD启动器。
完整剩余清单见《开发剩余工作评估.txt》。
'''
 (OUT/'动态连续加载组合进展.txt').write_text(report,encoding='utf8')
 assessment=OUT/'开发剩余工作评估.txt'
 prior=P/'versions'/('remaining_work_before_dynamic_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));prior.mkdir(parents=True)
 if assessment.exists():shutil.copyfile(assessment,prior/assessment.name)
 assessment.write_text('''双客户端原型剩余工作
更新：'''+stamp+'''

当前位置
实机已证实：A专用保存、单次工具触发的B加载、改为刘备视角并回到可下令大地图。受控出征、赏赐及两势力基本操作也有实测。
本轮离线已证实：动态文件/日期/身份、输入授权、加载观察、身份转换、回图确认组成同进程两代完整核心链，20个场景通过。
尚未证实：同一真实游戏进程每旬反复同步；两个真实客户端完整可玩。原型目前仍不能直接交给两个人正常开局。

1. 每旬恢复的正式运行模块【当前主线】
已有：核心链离线连通；一次真实原生加载走通；房间检查点协议和进程通信有独立测试。
还缺：新常驻owner与ABI，动态参数接回原生队列适配器/运行检查/IPC，上一代真正结束的交接条件，以及连续两次真实加载。
验收：B已在自己的势力中，连续接收两份来自A的正式检查点，每次自动恢复到正确日期和B势力，并能继续下令。不能拿离线回调计数归零代替游戏任务已结束。

2. 完整世界一致与加载体验
已有：整份文件传输/完整读取校验；多个序列化表研究；外部等待画面助手的自有窗口测试。
还缺：新链下的完整世界核验、实际游戏地图遮罩与输入等待、加载异常的保留和恢复。当前身份与日期一致不等于所有军队/城市/任务都已核验。
验收：B最终世界与A一致（仅允许明确的本地视角字段差异），等待时保留地图画面，完成后再开放操作。先支持窗口/无边框。

3. 两个人类势力与玩家指令
已有：出征/赏赐受控执行，命令解析和去重记账，AI/经济适配研究。
还缺：捕获正常菜单操作，A确定执行次序，两端各执行一次，避免远程命令再次上报；持续接入两个人类势力的AI/经济控制。
验收：先用赏赐+出征白名单，两人各玩自己的势力，主机AI不代替任何玩家下令，扣钱/忠诚/兵力不重复计算。其他内政、人才和外交按命令族扩展，暂不宣称全支持。

4. 准备、时间和选择事件
已有：双方准备和事件归属/答复的协议层。
还缺：准备后真正停止下令，双方完成同步才推进；招募等选择事件由正确玩家处理，另一端实际等待；B临时推演的结果不能独立成为正式决策。
验收：第5天A事件、第7天B事件等情况按主机顺序处理一次，不能依赖两端弹出完全相同的窗口。

5. 双机联调、恢复和交付
已有：房间通信、文件传输、重传与断线等待的离线测试。
还缺：两个真实游戏客户端连续多旬联调，一端慢/断线/加载失败时的恢复，助手窗口创建/加入/选势力与安装打包。
验收：两台机器跑完“下令→准备→推演→A保存→B同步→继续下令”；异常停在明确状态，不重复操作。默认仍是额外联机助手窗口配合原生游戏菜单。

接下来按验收节点推进
先完成同一游戏进程连续两次加载；再完成两客户端无命令一旬；然后加入赏赐和出征的受限试玩。顺滑画面、更多命令和长期恢复继续扩展。以上节点尚未完成，暂不按源码/测试数量推算百分比或剩余天数。
''',encoding='utf8')
 resume=P/'mainline_20261007_live_resume.json';state=read(resume)
 state['dynamic_complete_offline']={'updated':stamp,'handoff':str((P/'checkpoint_dynamic_complete_handoff.json').resolve()),'result':str(result_path.resolve()),'cases':len(r['cases']),'actual_hardware_prefetch':True,'game_access':False,'native_second_load':False}
 state['next_concrete_integration']=[
  'Preserve current successful V2 hooks/once claim. Do not reload the one-shot installer or hot-swap its six game slots.',
  'Implement a successor production owner/ABI using the dynamic Session, per-generation authorized Controller, persistent hardware provider and planning observer. Reuse real native queue adapter, not fixture double.',
  'Bind dynamic callback-time runtime guards and local transaction paths/storage/IPC; no arbitrary remote addresses or profile booleans authorize native calls.',
  'Establish native previous-generation handoff before enabling production generation publication. Counts alone are insufficient.',
  'Then test two genuine checkpoints in one game process, followed by full-world verification, window/borderless map cover/input hold and two-client empty-order period loop.',
  'Add actual dual-human AI/economy control, continuous reward/sortie command whitelist and event waiting before calling the prototype playable.']
 resume.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({'published':True,'cases':len(r['cases']),'checked_sources':len(r['source_sha256']),'frozen_v2_unchanged':True,'game_access':False}))
if __name__=='__main__':main()
