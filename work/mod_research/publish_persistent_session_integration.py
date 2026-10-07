"""Publish scoped offline evidence; never access the game or its save directory."""
from pathlib import Path
from datetime import datetime
import hashlib,json
P=Path(__file__).resolve().parent
OUT=P.parents[1]/'outputs/san14-link'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf8'))
def latest(folder):return sorted((P/folder).glob('*/result.json'))[-1]
def record(path):return {'path':str(path.resolve()),'sha256':sha(path),'data':read(path)}
def main():
 session=record(latest('checkpoint_persistent_native_session_runs'))
 logical=record(latest('checkpoint_persistent_logical_adapter_runs'))
 parameters=record(P/'checkpoint_repeat_native_parameters_handoff.json')
 assert session['data']['result']=='PASS' and logical['data']['passed']
 for name,digest in parameters['data']['files'].items():assert sha(P/name)==digest,name
 for part in (session,logical):
  for name,digest in part['data']['source_sha256'].items():assert sha(P/name)==digest,name
 baseline=read(P/'checkpoint_complete_live_owner_v2_handoff.json')
 for name,digest in baseline['source_sha256'].items():assert sha(P/name)==digest,name
 assert sha(P/'checkpoint_complete_live_owner_v2.dll')==baseline['dll_sha256']
 run=Path(session['path']).parent
 handoff={'schema':'san14.persistent-native-session-handoff.v1','offline_passed':True,
  'evidence':{'path':session['path'],'sha256':session['sha256']},
  'fixture_binary':{'path':str(run/'fixture.exe'),'sha256':sha(run/'fixture.exe')},
  'production_object':{'path':str(run/'production.obj'),'sha256':sha(run/'production.obj')},
  'source_sha256':session['data']['source_sha256'],
  'core_symbol_binding':'Compile only frozen cc_load_observer.cpp and title_identity_adapter.cpp with CheckpointLoadWorkerClaim/CurrentOwner renamed to CheckpointPersistentObserverClaim/CurrentOwner; shims call new logical adapter. No old globals defined or reset.',
  'session_api':'Initialize fresh Session; activate only under explicit fixture macro. Physical bridge installation/configuration and generation handoff stay outside Session. DispatchFinally owns active decrement on normal/abnormal exit.',
  'review':'persistent_routing independently reviewed FINALLY and cross-generation records; no new blocker. Native Load exception may leave old lifecycle inFlight, but Session error keeps that generation failed.',
  'game_access':False,'production_activation':False,'planning_observer_integrated':False,'authorized_controller_integrated':False,
  'native_scheduler_fence':False,'full_world_verified':False,'frozen_v2_unchanged':True}
 (P/'checkpoint_persistent_native_session_handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding='utf8')
 stamp=datetime.now().isoformat(timespec='seconds')
 evidence={'schema':'san14.persistent-session-integration-progress.v1','updated':stamp,
  'session':session,'logical_adapter':logical,'native_parameters':parameters,
  'frozen_v2_sources_and_dll_unchanged':True,'game_access':False,
  'request_bytes_lifecycle_identity_cores_integrated_offline':True,
  'second_generation_starts_in_B_view_in_fixture':True,
  'authorized_controller_and_planning_observer_integrated':False,
  'arbitrary_checkpoint_native_support':False,'production_generation_switch':False,
  'native_scheduler_fence':False,'repeated_live_loads':False,'world_verified':False,'two_clients_playable':False}
 (OUT/'连续加载接线证据.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
 report='''连续加载接线进展

本轮推进：常驻入口已经接到实际加载核心，不再只是各自独立的底层测试。

已实现并验证
1. 新建每次加载独立的会话：入口固定保留，每次使用新的请求、文件校验、加载生命周期和势力转换记录，旧记录不重置。
2. 接通新入口与旧观察代码的槽位、线程归属转换。文件读取属于哪次加载，由当前实际调用链确认；复制出来的记录不能冒充有效调用。
3. 正常返回和异常退出均收尾。第一轮发生读取异常或回调异常，不会把计数和错误混入第二轮会话。
4. 同一个测试进程、同一套六个入口，连续执行两代会话。第二代从“客户端已是刘备”起步，模拟载入主机张鲁数据，再由实际势力转换核心改回刘备。真实执行了本地测试文件的完整哈希、独立意图文件和内存原子修改。
5. 新增重复加载参数候选转换：加载前读取当前客户端信息；读入新存档后，再依据本次加载证据获取新的君主、势力对象及剧本字段。旧地图的指针和固定数值不能直接带入新地图。

验证
加载核心组合的8个场景通过：连续成功、文件内容不符、加载异常、读取异常、势力初始化异常、界面回调异常、提交后停止、提交后验证拒绝。每个场景随后接一份新的成功会话，检查旧会话记录未变化。
槽位与线程归属适配另有独立原生组合测试；参数转换另有纯数据反例测试，详见同目录证据文件。
这些测试没有操作游戏，也没有改动当前已经实测成功的V2源码和DLL。

离可实机连续同步还缺什么
1. 将日期、存档大小和摘要、势力等动态参数真正传入C++请求、校验、转换和回到大地图的各层；目前原生核心仍使用已验证的固定测试存档。
2. 将输入控制和回到可下令大地图的观察器接到新会话，并合并路由、适配层和原生入口的错误检查。
3. 确认游戏任务真正结束的交接边界，防止上一轮尚未进入入口的迟到任务被归给下一轮。仅看当前回调数为零还不够。
4. 完成同一游戏进程连续两次加载实测，再接完整世界核验、保留地图的等待画面和双客户端每旬循环。

当前结论
本轮证明了“固定入口 + 独立加载会话”的核心接线可工作；没有证明游戏内连续两旬同步，也没有完成不露出加载页的画面遮罩。新会话的正式启用仍关闭，只能在独立测试程序中激活。无需用户读档、推进或重启。
'''
 (OUT/'连续加载接线进展.txt').write_text(report,encoding='utf8')
 resume=P/'mainline_20261007_live_resume.json';state=read(resume)
 state['persistent_session_integration']={'updated':stamp,'evidence':str((OUT/'连续加载接线证据.json').resolve()),'report':str((OUT/'连续加载接线进展.txt').resolve()),'offline_integration_cases':len(session['data']['cases']),'game_access':False,'native_second_load':False}
 state['next_concrete_integration']=[
  'Keep frozen passed V2 owner and once claim retained. Do not hot-swap current six game hooks.',
  'Propagate repeat-native candidate file/date/identity fields into successor C++ cores. Resolve new-world identity fields only at owned Title callback.',
  'Integrate generation-bound authorized admission Original wrapper and rebuilt planning observer with successor Session; include logical/route/physical fault receipts.',
  'Establish native scheduler handoff before enabling production generation publication. Zero active callbacks is insufficient.',
  'Run two native loads in one game process only after the above, then world verification, map-cover/input hold and real two-client loop.']
 resume.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
 assessment=OUT/'开发剩余工作评估.txt'
 text=assessment.read_text('utf8')
 if text.startswith('最新接线进展（'):text=text.split('\n\n',1)[1]
 assessment.write_text('最新接线进展（'+stamp+'）：常驻入口已接请求、文件校验、加载观察和势力转换核心；8个同进程双会话场景通过。输入控制、回到大地图观察、动态参数原生贯通和实机连续加载仍未完成。详见《连续加载接线进展.txt》。\n\n'+text,encoding='utf8')
 print(json.dumps({'published':True,'session_cases':len(session['data']['cases']),'logical_cases':len(logical['data']['cases']),'frozen_v2_unchanged':True,'game_access':False}))
if __name__=='__main__':main()
