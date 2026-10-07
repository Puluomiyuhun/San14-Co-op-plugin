"""Publish bounded findings without turning an incomplete trace into success."""
from pathlib import Path
from datetime import datetime
import hashlib
import json

P = Path(__file__).resolve().parent
OUT = P.parents[1] / 'outputs' / 'san14-link'
RUN = P / 'save_return_observer_live' / '20261006-194514-137991'


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def evidence(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


analysis = load(RUN / 'analysis-v2.json')
comparison_path = P / 'checkpoint-cycle-live' / 'before-normal-menu-observation-20261006-vs-after-normal-menu-observation-20261006.json'
comparison = load(comparison_path)
delivery = load(OUT / '本地同步控制器验证.json')
exception_paths = sorted(P.glob('save_return_exception_static_*.json'))
exception_path = exception_paths[-1] if exception_paths else None
exception_static = load(exception_path) if exception_path else None
if exception_static:
    assert exception_static['trace_sha256'] == analysis['trace_sha256']
    assert exception_static['raise_exception_iat']['symbol'] == 'RaiseException'
assert analysis['result'] == 'INCOMPLETE'
assert analysis['ending']['registers_restored'] and analysis['all_four_callback_pairs_captured']
assert not comparison['objects']['other_record_changes'] and not comparison['objects']['runtime_pointer_changes']
assert comparison['all_48400_hex_serialized_fields_equal'] and comparison['sampled_global_rng_equal']
assert comparison['sampled_world_rng_fields_equal']
assert not any(comparison[key] for key in ('save_files_added', 'save_files_removed', 'existing_save_files_changed'))
assert delivery['result'] == 'PASS' and delivery['tests_run'] == 44
stamp = datetime.now().astimezone().isoformat()
report = {
    'schema': 'san14.save-return-input-progress.v1', 'updated': stamp,
    'normal_menu_trace_status': 'INCOMPLETE',
    'all_four_callback_pairs_captured': True,
    'normal_menu_stack_counts': [len(stack) for stack in analysis['state_sequences']],
    'same_user_object_retained': analysis['same_user_pointer_in_observations'],
    'date': {'year': 203, 'month': 8, 'day': 11, 'force': 12},
    'callback_thread_ids': analysis['callback_threads'],
    'observer_exceptions': analysis['errors'],
    'exception_static_classification': ({'evidence': evidence(exception_path),
        'same_code_thread_naming_emitters_found': True,
        'live_events_uniquely_attributed': False} if exception_static else None),
    'observer_detached_and_debug_registers_restored': True,
    'known_state_comparison': comparison,
    'save_file_count_before_and_after': 81,
    'delivered_local_transition_tests': delivery,
    'native_export_success': False, 'native_export_attempted_this_run': False,
    'old_export_pilots_remain_retired': True,
    'full_world_coverage': False, 'real_two_game_cycle_complete': False,
    'evidence': [evidence(path) for path in (
        RUN / 'trace.jsonl', RUN / 'analysis-v2.json', comparison_path,
        P / 'save_return_user_shadow_20261006-192905-382445.json',
        P / 'save_return_menu_regression_20261006-191752-777577.json',
        P / 'save_return_lifecycle_shadow.json',
        P / 'save_return_observer_fixtures' / '20261006-194343-853033' / 'result.json')],
}
(OUT / '保存返回与输入控制证据.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
text = f'''保存返回与输入控制进展
更新：{stamp}

目前结论
旧保存入口造成日期推进的原因已经定位；新的保留玩家操作层的结构通过了离线执行验证，并取得正常菜单的四个真实生命周期回调。尚未完成新入口的实际检查点导出，也未完成双客户端连续一旬。
本轮没有再次调用保存或加载，没有新增/覆盖存档；观察器已经退出。游戏仍为203年8月中旬、张鲁，当前无需读档恢复。

真实菜单观察
用户正常打开功能菜单、进入保存列表、不选择槽位并取消回地图。状态层数为5→6→7→6→5，同一个User对象始终保留。
退出事件(kind0)、暂停、恢复、进入事件(kind1)都捕获了入口、原生RET与返回调用者三点，栈和原始64位RAX配对。暂停时控制标记0→1、光标标记1→0、协调器标记0x27→0x26；恢复后各自还原。玩家阶段保持2，无推进请求。
前后783条已跟踪对象记录无变化，48,400地格的已确认序列化字段一致，已跟踪全局随机/World随机字段一致；81份.s14文件哈希均不变。此范围不能等同全部游戏隐藏状态。
观察器记录了两次first-chance 0x406D1388异常通知；当时没有采集异常地址/参数。离线在游戏中找到了使用相同代码、线程名和线程ID调用RaiseException的路径，支持线程命名通知这一解释，但无法逐条确认本轮两次通知的来源。原始整轮结果保留INCOMPLETE，不改为PASS。四个回调配对及前后字段比较是独立事实，不能替代完整无遗漏的执行记录。
工具使用硬件执行断点，会短暂影响执行时序；未写游戏代码、数据或虚表，未注入保存请求，结束时已恢复调试寄存器并脱离。

保存结构修正
旧412520发出type2，只有在替换保存选档层时才符合正常菜单上下文；直接从玩家层调用会删除玩家层。失败原件、取证文件和一次性日志继续保留，旧执行器保持禁用。
候选2DF990发出type0，实际队列消费代码会保留玩家层；保存结束type1返回原层。原生User四个生命周期回调、选择清理、回调重建与部分输入标记已加入复制机器码测试，8种受限情形通过；正常完整菜单控制流4种情形通过，保存生命周期另23种受限情形通过。
上述机器码测试仍替代了部分外围UI、调度、文件存储与完整序列化。正常菜单取消不等于新入口导出成功，因此本轮没有重新开放执行器。
审计还确认原生保存会尝试写configS_SC.s14和prdataN.s14，并会保存/回写随机状态。新入口必须在真正静止的规划边界执行，纳入这些副作用的观察，不能只核对新生成文件的头部。

已交付的本地同步控制器
checkpoint_local_transition.py组合了旬末协调器、SQLite持久日志、地图等待层、画面接口和输入合同。三个研究模块已整理到本目录；移植后的44项合成测试通过。
恢复世界并切回新地图以后，仍要等待新的输入排空周期、键鼠和手柄全部松开，才开放本地操作和准备。长按键、消息残留、旧画面/旧世界回执、连接中断都不能提前放行。
该控制器没有真实画面捕获、可见覆盖或设备拦截能力，也不调用原生加载。合成回执不能用于宣称已经遮住游戏读档画面。
本轮实际User回调分别在两个线程运行。这不证明Root输入消费也换线程，但证明不能把User回调线程当作永久主线程。当前合同固定线程检查会安全拒绝不匹配，未来需在已验证的串行输入边界交接，不能简单使用最新resume线程号放宽检查。

接下来开发顺序
1. 以新的独立候选实现一次保留原User的A端检查点导出，验证日期/阶段不变、文件确实完成、副作用受控；旧入口不复用。
2. 将正确的新文件绑定到B的受控重载，核对完整业务覆盖、B身份及新世界实例；先跑通一轮再谈速度。
3. 接入真实输入边界、旧地图可见覆盖与镜头恢复，验证不会穿透输入或露出原生切页。
4. 接双方人类规则、持续命令和事件，进行两个真实客户端的连续多旬验收。

这次解决的是保存返回结构和同步恢复放行条件，剩余最大缺口仍是原生导出—传输—B恢复的真实闭环；不能按离线测试数量估算完成百分比。
'''
(OUT / '保存返回与输入控制进展.txt').write_text(text, encoding='utf8')
marker = '\n保存返回与输入控制后续进展（2026-10-06）\n'
addition = '''本轮真实操作仅为打开保存列表后取消，5→6→7→6→5保留同一玩家对象，四个User生命周期调用都已配对。783条记录、48,400地格字段、已跟踪随机状态及81份存档前后一致。记录中两次未完整分类的异常通知使原始整轮仍为INCOMPLETE，未据此声称自动导出通过。
新的type0候选加入了真实User回调的离线测试，旧保存执行器继续禁用。本轮未实际保存/加载，不需要用户再恢复34。
新增本地同步组合控制器，移植后的44项合成测试通过；新地图呈现后仍等待物理输入全松手与排空才允许操作。真实可见画面覆盖和原生输入门尚未接入。User回调跨线程的实测提示输入线程所有权需要独立验证。
详细证据与下一步见《保存返回与输入控制进展.txt》《保存返回与输入控制证据.json》《本地同步控制器接口说明.txt》。
'''
for name in ('地图等待层与独立检查点进展.txt', '开发剩余工作评估.txt'):
    path = OUT / name
    old = path.read_text(encoding='utf-8-sig').split(marker)[0]
    path.write_text(old.rstrip() + '\n' + marker + addition, encoding='utf8')
print(json.dumps({'result': 'PUBLISHED', 'native_export_success': False,
                  'trace_status': analysis['result'], 'delivered_tests': 44}, ensure_ascii=False))
