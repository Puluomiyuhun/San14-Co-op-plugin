"""Publish evidence with separate native, emulator, fixture and UX boundaries."""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1]/'outputs'/'san14-link'


def evidence(path):
    path = Path(path)
    data = path.read_bytes()
    return {'source': str(path.resolve()), 'sha256': hashlib.sha256(data).hexdigest(),
            'data': json.loads(data)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--save-result', type=Path, required=True)
    parser.add_argument('--world-comparison', type=Path)
    parser.add_argument('--comparison-after-recovery', action='store_true')
    parser.add_argument('--save-regression', type=Path)
    args = parser.parse_args()
    save = evidence(args.save_result)
    comparison = evidence(args.world_comparison) if args.world_comparison else None
    assert save['data']['mode'] == 'execute'
    fixtures = evidence(ROOT / save['data']['fixture_evidence']) if not Path(save['data']['fixture_evidence']).exists() else evidence(save['data']['fixture_evidence'])
    sources = {
        'native_private_export': save,
        'export_fixture_tests': fixtures,
        'readonly_world_comparison': comparison,
        'world_comparison_after_manual_recovery': args.comparison_after_recovery,
        'map_wait_gate_tests': evidence(ROOT/'checkpoint-presentation-tests.json'),
        'surface_contract_tests': evidence(ROOT/'transition_visual_surface_test_results.json'),
        'presentation_journal_integration': evidence(ROOT/'transition_visual_integration_results.json'),
        'native_win32_offscreen_fixture': evidence(ROOT/'transition_visual_win32_results.json'),
        'native_load_metadata_emulation': evidence(ROOT/'private_checkpoint_metadata_shadow.json'),
    }
    for name in ('private_checkpoint_metadata_fixture_results.json', 'private_checkpoint_metadata_preparation.json', 'private_checkpoint_metadata_new_file.json', 'transition_input_gate_audit.json', 'private_checkpoint_save_unexpected_advance.json', 'private_checkpoint_save_RETIRED.json', 'private_checkpoint_save_state_transition_shadow.json'):
        if (ROOT/name).exists():
            sources[name.removesuffix('.json')] = evidence(ROOT/name)
    if args.save_regression:
        sources['native_save_state_apply_regression'] = evidence(args.save_regression)
    actual = save['data']
    passed = actual['result'] == 'PASS' and actual['native_save_complete'] is True
    if passed:
        assert actual['sampled_business_unchanged'] and actual['existing_files_unchanged']
        assert comparison and not comparison['data']['existing_save_files_changed']
    native = actual['adapter']
    duration = ((native['finalized_at']-native['queued_at'])/1000
                if native.get('finalized_at') and native.get('queued_at') else None)
    report = {
        'schema': 'san14.map-wait-private-checkpoint-progress.v1',
        'created': datetime.now().astimezone().isoformat(),
        'accepted_first_release_window_modes': ['windowed', 'borderless'],
        'game_video_settings_changed': False,
        'ux_target': 'retain old map pixels with sync cover during native B world rebuild',
        'sources': sources,
        'native_private_export_complete': passed,
        'observed_save_queue_to_finalizer_seconds': duration,
        'duration_is_not_load_or_multiplayer_latency': True,
        'native_map_cover_visible_proven': False,
        'native_input_gate_installed': False,
        'native_custom_checkpoint_loaded': False,
        'full_world_equality_proven': False,
        'two_real_client_cycle_complete': False,
        'native_gameplay_enabled': False,
    }
    (OUT/'地图等待层与独立检查点证据.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    incident = sources.get('private_checkpoint_save_unexpected_advance', {}).get('data')
    state = '实际导出成功' if passed else '未通过，不能作为可用的导出入口，也不会自动重试'
    size = actual.get('file', {}).get('size', '待确认')
    detail = ''
    file_detail = ''
    if incident:
        size = incident['save_files']['mpckpt01.s14']['size']
        detail = ('工具实际只提交了一次请求，但选择了替换当前状态的原生入口。CUserStrategyState被CSaveState替换，'
                  '结束后推进到203年8月下旬的报告界面。观察器拒绝了错误状态栈，恢复了两个钩子；原生已排队的流程仍完成并推进。'
                  '这不是合格的A旬末保存行为，也不能用生成文件或离线测试通过掩盖。原结果、once日志和文件均保留，不删除记录重试。')
        file_detail = f"事后只读盘点：原有{len(incident['save_files'])-len(incident['added_files'])}份存档改变列表为{incident['old_files_changed']}；新增{incident['added_files']}。"
    world_detail = '因未通过保存生命周期，未取得正常保存前后的完整稳定边界对照。'
    if comparison:
        comp = comparison['data']
        boundary = '测试前与人工读回34号档后' if args.comparison_after_recovery else '保存前后'
        world_detail = (f"{boundary}对照：48,400个地格的已确认序列化字段一致={comp['all_48400_hex_serialized_fields_equal']}；"
                        f"已跟踪全局随机一致={comp['sampled_global_rng_equal']}；World随机字段一致={comp['sampled_world_rng_fields_equal']}。"
                        '另保留783条对象记录的详细差异。这不是完整世界覆盖证明。')
        if args.comparison_after_recovery:
            world_detail += '恢复后的对照不能用于把失败的保存尝试改成成功。'
    elapsed_text = f'{duration}秒' if duration is not None else '未取得完整收尾记录'
    text = f'''地图等待层与独立检查点进展
更新：{report['created']}

约定的首版体验
用户已接受窗口或无边框模式。B在自己的地图画面上显示“正在同步”，A、B此时均停止新操作；后台恢复A的正式世界，重新建立B身份和菜单、恢复B镜头，新地图可见后继续下一旬。
原生加载仍有实际耗时。旧地图对象会被游戏销毁，等待期间保留的是旧地图像素画面。目标是遮住原生页面切换，不是让旧地图继续可交互。目前尚未在游戏中实现真实覆盖，不能承诺已经看不到读档页面；未改游戏视频设置。

本轮真实游戏结果
A端专用检查点：{state}。目标为mpckpt01.s14，实际文件大小{size}字节，通过游戏原生保存线程生成。
{detail}
原生队列到收尾记录：{elapsed_text}。这不是B读档耗时，也不是双机同步延迟。
{world_detail}
{file_detail}
本次范围仅为一个已知测试起点的A端导出试验；实际判定以以上通过/失败结果为准，不能推广为任意旬末、B专用文件加载或双机循环成功。

保存问题的离线修正依据
旧412520入口发出type2替换命令：实际队列消费代码删除User状态，CSave结束又弹出保存状态，所以没有返回原玩家操作层。旧入口现已禁用。
新候选2DF990发出type0压入命令。复制的原生队列消费与保存清理代码离线执行显示5层→6层→5层，原User对象保留；旧入口的失败结构也在同一测试中复现。
这个对照仍替换了分配和界面生命周期等外围调用。User暂停/恢复及选择状态副作用、实际worker、合法保存边界尚未验收；不据此重新开放原生执行。

画面与控制逻辑
checkpoint_presentation.py 已串接现有旬末协调器与持久检查点日志。流程必须依次获得旧图覆盖确认、单次加载许可、实际世界/B身份恢复、同一视角的新地图帧、撤罩确认。协调器切换到规划状态后，画面门尚未开放时仍不能接受玩家新命令。
画面接口与上述控制器/SQLite日志的集成验证通过；中断、旧回执或错误世界不能自动开放输入。这里的加载和呈现回执是合成的。
首版控制器只接受windowed/borderless画面回执，未知模式或独占全屏不能获得加载许可；中途切换模式会要求重新核对画面表面。
独立Win32样机使用自己的隐藏窗口和私有像素缓冲，验证后台换图时旧图保持、失败提示及自身消息拦截。结果明确为离屏绘制；未捕获、覆盖或拦截三国志14，也不证明真实可见遮罩已完成。
输入静态追踪还确认了DirectInput键盘、鼠标、控制器路径，不能只吞窗口消息。已找到Root状态中的输入转换段候选；原生清缓存仍遗漏raw键盘与部分锁存请求，完整输入门尚未安装。

B端接入准备
游戏普通目录不会自动枚举mod专用文件。现已离线验证显式文件名传递、原生头部解析、元数据节点创建/登记/释放路径，正在将文件身份核对与原生目录接入串联。
载入目标必须在原生开始加载前就绑定到正确文件，不能先请求34号档、再寄希望于后续拦截成功才换文件。当前没有执行新专用文件的真实B载入。
本地文件SHA、原生元数据头、加载后的世界摘要分别证明不同事情；彼此不能替代。现有受限实验只针对203年8月中旬的张鲁测试起点。

仍需完成的关键接入
1. 专用检查点的原生加载与B身份恢复，关联真实新文件和新世界实例。
2. 游戏输入门、真实地图取帧/可见遮罩、本机镜头恢复；不能仅靠外部窗口抢焦点，也不能暂停加载所需的主循环。
3. 加载后完整业务状态核对、双方人类势力AI与经济规则、持续命令和正式事件接入。
4. 两个真实客户端连续多旬验收，再测实际等待时间与优化。

当前仍为研究原型，房间未开放原生联机。本次异常后已请求玩家读回34号档；恢复后仅进行只读核验，不再执行新的游戏写入。
'''
    (OUT/'地图等待层与独立检查点进展.txt').write_text(text, encoding='utf-8')
    print(json.dumps({'native_private_export_complete': passed, 'observed_save_seconds': duration,
                      'native_gameplay_enabled': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
