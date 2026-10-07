"""Publish the completed real observation, retaining earlier milestone evidence."""
from datetime import datetime
import hashlib, json
from pathlib import Path
P=Path(__file__).resolve().parent
OUT=P.parents[1]/'outputs/san14-link'
LIVE=P/'checkpoint_live_prefetch_runs/20261007-143730-683769/result.json'

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def evidence(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def main():
    live=read(LIVE);o=live['observer'];h=o['hardware'];c=live['known_comparison']
    assert live['result']=='PASS_OBSERVATION_ONLY' and live['stop_completed']
    assert live['actual_slot_and_protection_restored'] and live['prefetch_code_unchanged']
    assert h['entered']==h['captured']==h['restored']==h['finished']==1
    assert h['original_dr']==h['restored_dr'] and o['admission_errors']==0
    assert o['admission_finished']==o['admission_closed']==1
    assert not live['load_requested'] and not live['game_order_submitted']
    assert not c['objects']['other_record_changes'] and c['all_48400_hex_serialized_fields_equal']
    assert live['existing_save_files_unchanged'] and live['force_comparison']['observed_table_equal']
    marker='本轮新增：真实菜单输入边界已通过（2026-10-07 14:37）'
    note=f'''{marker}

已在当前张鲁测试局里，连续记录同一次原生调用的进入、读取菜单命令前、返回后三个时点，确认该次没有待处理菜单命令或推进请求。只对这一次调用设置硬件执行断点；游戏原有指令的33字节没有改写，断点寄存器已恢复。

观察窗口共{o['matched_pairs']}次地图更新，全部正常配对返回；原更新入口与页面保护已恢复。为承接可能缓存的旧回调，模块继续保留，未卸载。没有下令、保存、读档或推进日期。日期仍为203年8月中旬、张鲁；783个采样对象、48,400个地格字段、52个势力字段及83份存档均未发现变化。这些核验不能替代完整世界一致性证明。

同时修正了两个真实起点差异：读档后缓存模式可以是0；命令队列可以尚未分配内存。适配器接受这类正常起点，但只有同次授权后由原生代码创建的队列才能被后续步骤认可。输入观察、队列适配与加载会话的组合已通过隔离进程验证；组合加载还未安装到真实游戏。

对主线的意义：已经能在真实游戏处理输入的正确位置做检查，并正常恢复。下一步是把该检查与原生加载请求、实际读取的目标存档、B身份恢复接成一次自动往返。此次观察没有执行这个往返，因此还不能称为自动B重载成功，也不能测出B的加载耗时或保证不出现加载画面。

当前无待处理的手动游戏操作。
'''
    report=OUT/'实机加载接入进展.txt'
    old=report.read_text(encoding='utf-8-sig')
    if marker not in old:report.write_text(note+'\n此前已验证的加载与线程观察\n\n'+old,encoding='utf-8-sig')
    path=OUT/'实机加载接入证据.json';record=read(path)
    record['updated']=datetime.now().astimezone().isoformat()
    record['real_single_call_prefetch_observed']=True
    record['real_single_call_debug_state_restored']=True
    record['prefetch_observed_matched_user_calls']=o['matched_pairs']
    record['automatic_guest_reload_proven']=False
    record['complete_session_installed']=False
    record['pending_user_action']=None
    paths=[LIVE,P/'checkpoint_live_prefetch_handoff.json',
        P/'checkpoint_live_prefetch_combination_review.json',
        P/'checkpoint_live_prefetch_start.py',
        P/'checkpoint_live_prefetch_launcher_tests/20261007-143711-862227/result.json',
        P/'checkpoint_bound_forward_session_handoff.json',
        P/'checkpoint_hardware_admission_independent_review_20261007-142850-838783.json',
        P/'checkpoint_storage_module_inventory_20261007-144148-212905.json']
    seen={x['path'] for x in record['evidence']}
    record['evidence'] += [evidence(p) for p in paths if str(p) not in seen]
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    progress=OUT/'开发剩余工作评估.txt';old=progress.read_text(encoding='utf-8-sig')
    heading='最新实机进展（2026-10-07 14:37，真实输入检查通过）：'
    if not old.startswith(heading):progress.write_text(heading+'已真实观察同次调用的菜单读取前后，恢复原入口和调试寄存器；155次更新正常返回，已核验数据与存档未变。自动B加载整体尚未实测；下一关仍是单次自动加载往返。详见《实机加载接入进展.txt》。\n\n'+old,encoding='utf-8-sig')
    resume=P/'mainline_20261007_live_resume.json';state=read(resume)
    state['real_prefetch_result']=str(LIVE.relative_to(P))
    state['real_prefetch_scope']='One actual original User call: BEFORE/prefetch/AFTER clean; six debug registers restored; original 33-byte code unchanged. Total 155 paired updates. No queue/CAS/load/save/order. Module retained.'
    state['runtime_configuration_snapshot']='checkpoint_session_binding_snapshot_20261007-141555-245678.json'
    state['storage_module_inventory']='checkpoint_storage_module_inventory_20261007-144148-212905.json'
    state['pending_user_action']=None
    state['game_last_verified']['global_rng_diagnostic']=live['before']['context']['global_rng']
    if 'checkpoint_live_prefetch_live_once.json' not in state['must_preserve_once_records']:
        state['must_preserve_once_records'].append('checkpoint_live_prefetch_live_once.json')
    state['next_concrete_integration']=[
        'Use bound-forward hardware admission and forward Session: original slot verification separated from wrapper forwarding. Owned 36 cases passed; first actual hardware observation also passed.',
        'Finish production queue action/resolver, cached v014 module-pinned binding and phase-specific validators. Use fresh expected RNG before Initialize, never the old manifest value.',
        'Assemble one real Session with exact target bytes, native load lifecycle, B identity and new planning observation. No gameplay-ready without required world/presentation/input checks.',
        'Only after a true one-load cycle, solve repeated-session ownership for the next period; frozen Session remains single-use.'
    ]
    resume.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(report),'evidence':str(path),'result':'PUBLISHED_REAL_OBSERVATION_ONLY'},ensure_ascii=False))

if __name__=='__main__':main()
