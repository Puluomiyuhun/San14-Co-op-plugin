"""Publish bounded evidence for this turn. No game/process/network operations."""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'outputs' / 'san14-link'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def evidence(path):
    return {'path': str(path), 'sha256': digest(path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-result', type=Path)
    parser.add_argument('--native-review', type=Path)
    args = parser.parse_args()
    guarded_path = HERE / 'checkpoint_guarded_runtime_handoff.json'
    network_path = HERE / 'two_pc_preflight_portable_handoff.json'
    guarded, network = read(guarded_path), read(network_path)
    guarded_result = HERE / guarded['result']['path']
    assert digest(guarded_result) == guarded['result']['sha256']
    assert guarded['status'] == 'PASS_OFFLINE_COMPOSITION'
    assert all(digest(HERE / name) == value for name, value in guarded['all_source_sha256'].items())
    assert network['result'] == 'PASS'
    assert digest(Path(network['package_path'])) == network['package_sha256']
    assert digest(Path(network['result_path'])) == network['result_sha256']
    assert network['two_computers_tested'] is False and network['native_backend_connected'] is False
    native = {'attempted_this_turn': False, 'task_chain_observed': False,
              'native_scheduler_fence': False, 'real_game_repeated_load_proven': False}
    native_text = '实机只读任务记录器正在单独审查；尚未以本轮新记录证明任务交接。'
    if args.native_result:
        result = read(args.native_result)
        native.update(evidence=evidence(args.native_result.resolve()), result=result)
        native['attempted_this_turn'] = True
        post_path = args.native_result.parent / 'post-debugger-check.json'
        post = read(post_path)
        assert post['result_sha256'] == digest(args.native_result)
        assert post['same_process'] is True and post['debugger_present'] is False
        assert post['process_birth'] == result['after']['birth']
        native['independent_debugger_postcheck'] = evidence(post_path.resolve())
        native['debugger_present_after'] = False
        native['task_chain_observed'] = bool(result.get('recorder_exit') == 0 and
            result.get('before_after_equal') is True and result.get('analysis', {}).get('task_chain_observed') is True)
        native_text = ('本轮在真实游戏中记录到一个空闲大地图任务的完整返回和父任务清理过程，'
                       '记录前后所核对的地图/身份/状态指针未改变，调试寄存器已恢复。'
                       '这只是一次任务交接观察，未证明连续读档。') if native['task_chain_observed'] else \
                      '本轮已尝试实机只读任务记录，但证据尚未形成完整任务交接；详情见证据文件。'
    if args.native_review:
        native['independent_review'] = evidence(args.native_review.resolve())
    audit_path = HERE / 'two_player_first_smoke_audit.json'
    audit = evidence(audit_path) if audit_path.exists() else None
    first_review_path = HERE / 'checkpoint_dispatch_handoff_live_first_review.json'
    if first_review_path.exists():
        native['first_live_run_independent_review'] = evidence(first_review_path)
    group_path = HERE / 'human_ai_group_resolver_handoff.json'
    group = read(group_path)
    assert group['result'] == 'PASS_OFFLINE_RESOLVER_ONLY'
    assert all(digest(HERE / name) == value for name, value in group['files'].items())
    group_result = ROOT / group['test_result']['path']
    assert digest(group_result) == group['test_result']['sha256']
    group_record = {'handoff': evidence(group_path), 'result': evidence(group_result),
                    'archived_scenarios': group['test_result']['scenario_count'],
                    'installed_in_game': False, 'atomic_snapshot': False,
                    'scope': 'C++ read-callback resolver for future army-group AI wrapper; offline only.'}
    now = datetime.now().astimezone().isoformat(timespec='seconds')
    report = {
        'schema': 'san14.two-pc-readiness-progress.v1', 'updated': now,
        'network': {'handoff': evidence(network_path), 'portable_zip': evidence(Path(network['package_path'])),
                    'loopback_two_independent_exe_processes': True, 'transferred_diagnostic_bytes': 129 * 1024,
                    'two_real_computers': False, 'vpn_configured_by_agent': False,
                    'native_backend_connected': False},
        'persistent_runtime': {'handoff': evidence(guarded_path), 'result': evidence(guarded_result),
                               'offline_cases': guarded['result']['cases'],
                               'full_chain_dynamic_guards_integrated': True,
                               'native_game_bodies_are_fixture': True,
                               'steam_storage_gate_integrated': False,
                               'production_generation_publication': False},
        'native_handoff': native, 'first_smoke_audit': audit,
        'army_group_identity_resolver': group_record,
        'single_real_guest_identity_reload_previously_verified': True,
        'playable_two_clients': False, 'two_native_periods': False,
        'full_world_verified': False, 'map_cover_in_real_load_verified': False,
        'remaining': ['real task attribution and both Title worker join receipts',
                      'production repeatable save/load owner and current-period artifact binding',
                      'dual-human AI and economy rules in the real host game',
                      'two clients ready/input waiting and failure hold',
                      'end-to-end two genuine periods and recipient/world comparison',
                      'continuous supported command capture and replay',
                      'map cover during actual native reload'],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / '双机测试准备证据.json', report)
    text = f'''双机测试准备进展（{now}）

现在可以开始：异地网络预检。
免 Python 的 EXE 便携包已完成。最终 EXE 复制到新目录、在空 PATH 环境下，用两个独立进程完成了加密连接、不同势力席位绑定和 129 KiB 随机文件收发/落盘校验。
两台异地电脑还没有实测，用户尚未配置虚拟网络。预检成功只说明连接与诊断文件通过，不代表可以开局。
安装包：outputs/two_pc_preflight_portable.zip
准备说明：outputs/异地双机连接准备.txt

本轮游戏后端进展
常驻加载的请求、文件字节、生命周期、身份、规划状态及入队检查现已连入同一条测试链；13 项组合验证通过。
其中连续两轮采用不同文件、日期和身份，旧轮次状态保持不变。游戏原生加载/界面/队列函数及 Steam 存储认证仍有测试替身；生产环境的连续加载开关尚未开放。
{native_text}
新增供 C++ AI 入口使用的部队编组归属读取接口，41 个既有场景与原生历史对照/已有纯算法一致。它可区分人类主军团和委任军团，但尚未挂接到实际 AI，也不等于 AI 保护已经生效。
先前已成功做过一次真实自动加载并回到刘备大地图；“一次成功”不能等同于本轮和下一轮都能连续成功。

第一次双人测试分三个阶段
1. 网络预检：现在可做，无需启动游戏。异地实测通过后记录连接结果。
2. 双游戏同步演示：两机分别进入同一世界的不同势力，再做一次 A 结果传给 B 的核对。仍需整合真实开局/文件/加载入口；人工存读档可以辅助诊断，但不算完整自动闭环。
3. 空命令连续两旬：双人准备、A 推进/保存、B 加载并恢复自己势力、世界核对、失败停止，再完整重复一旬。这个阶段尚未通过。

首测可以暂不让 B 自行推演战斗，B 在大地图等待 A 的结果；赏赐、出征等连续操作也可在空命令测试之后接入。
但 A 不能把 B 势力交给 AI 代管，玩家/AI经济规则也要统一。这两项是空命令推进的必要条件，不能因“没人下令”而省略。

当前主要缺口
真实游戏任务的归属/收尾和两条 Title 工作线程的结束确认；常驻保存/加载接入本轮动态文件；双玩家 AI 与经济适配；双端准备/输入等待/异常停止；连续两旬与世界内容核验。
随后接入持续的赏赐/出征命令，并验证原生读档时的地图遮罩。
尚不能承诺读档完全不闪加载画面，也不能把“日期和君主正确”当作全世界一致。

下一次关键验收是“同一个游戏进程接收两份真正不同的旬末文件，并两次恢复到可操作的 B 势力地图”。
完整双人原型的交付日期尚不能确定，需以上述实机验收判断。
'''
    (OUT / '双机测试准备进展.txt').write_text(text, encoding='utf-8')
    (OUT / '开发剩余工作评估.txt').write_text(text, encoding='utf-8')
    resume_path = HERE / 'mainline_20261007_live_resume.json'
    resume = read(resume_path)
    resume['user_network_context'] = 'Two Windows PCs in different locations; no connectivity configured yet.'
    resume['guarded_persistent_runtime_offline'] = report['persistent_runtime']
    resume['two_pc_network_preflight'] = report['network']
    resume['native_dispatch_handoff_latest'] = native
    resume['army_group_identity_resolver'] = group_record
    resume['first_smoke_audit'] = audit
    resume['published_two_pc_readiness'] = str(OUT / '双机测试准备进展.txt')
    resume['next_concrete_integration'] = report['remaining']
    write(resume_path, resume)
    print(json.dumps({'report': str(OUT / '双机测试准备进展.txt'),
                      'native_task_chain_observed': native['task_chain_observed'],
                      'playable_two_clients': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
