"""Publish this integration round from pinned evidence; no game or network access."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'outputs' / 'san14-link'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference(path):
    return dict(path=str(path.resolve()), sha256=sha(path))


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def checked_handoff(name, source_key):
    path = HERE / name
    record = read(path)
    for file, digest in record[source_key].items():
        assert sha(HERE / file) == digest, file
    return dict(handoff=reference(path), claims=record)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ready-handoff', type=Path, required=True)
    parser.add_argument('--native-run', type=Path)
    parser.add_argument('--economy-handoff', type=Path)
    args = parser.parse_args()
    task = checked_handoff('checkpoint_task_attribution_handoff.json', 'files')
    ai = checked_handoff('human_ai_runtime_handoff.json', 'source_sha256')
    task_result = Path(task['claims']['result']['path'])
    assert sha(task_result) == task['claims']['result']['sha256']
    ai_result = ROOT / ai['claims']['test_result']['path']
    assert sha(ai_result) == ai['claims']['test_result']['sha256']
    ready = read(args.ready_handoff)
    for file, digest in ready['files'].items():
        assert sha(ROOT / file) == digest, file
    assert sha(Path(ready['result']['path'])) == ready['result']['sha256']
    native = dict(attempted=False, task_chain_observed=False, scheduler_fence=False,
                  real_repeated_load=False)
    native_text = '新的读档收尾记录器已准备，尚无本轮完整实机记录。'
    if args.native_run:
        folder = args.native_run.resolve()
        native['attempted'] = True
        native['run_folder'] = str(folder)
        result_path = folder / 'result.json'
        if result_path.exists():
            result = read(result_path)
            native['result'] = reference(result_path)
            native['analysis'] = result['analysis']
            post = read(folder / 'post-debugger-check.json')
            assert post['result_sha256'] == sha(result_path)
            assert post['same_process'] is True and post['debugger_present'] is False
            native['postcheck'] = reference(folder / 'post-debugger-check.json')
            native['game_sample'] = post.get('game_sample')
            review_path = HERE / 'checkpoint_title_join_live_first_review.json'
            if review_path.exists():
                native['independent_live_review'] = reference(review_path)
            native['task_chain_observed'] = result['analysis']['task_chain_observed']
            native_text = ('本轮正常读取 34 号档，已配对 Load 工作线程及两条 Title 初始化线程的执行、返回和清理；调试器已退出。'
                           if native['task_chain_observed'] else
                           '本轮实机读档记录尚未凑齐所需链路；记录器已退出，调试器已脱离。')
        else:
            native['waiting_for_manual_load_or_cleanup'] = True
            native_text = '读档收尾记录器已启动，正等待一次手动读取 34 号档；尚不能把本次记录计作成功。'
    economy = dict(adapter_completed_this_round=False, installed_in_game=False)
    if args.economy_handoff:
        economy_claims = read(args.economy_handoff)
        for file, digest in economy_claims['source_sha256'].items():
            assert sha(HERE / file) == digest, file
        assert sha(ROOT / economy_claims['test_result']['path']) == economy_claims['test_result']['sha256']
        assert sha(ROOT / economy_claims['dll']['path']) == economy_claims['dll']['sha256']
        economy = dict(handoff=reference(args.economy_handoff), claims=economy_claims,
                       installed_in_game=False)
    report = dict(schema='san14.three-gate-integration.v1', updated=datetime.now().astimezone().isoformat(timespec='seconds'),
        task_attribution=task, ai_runtime=ai, ready_barrier=dict(handoff=reference(args.ready_handoff), claims=ready),
        economy=economy, manual_load_observation=native,
        all_three_gates_passed=False, two_real_periods=False, two_real_clients_playable=False,
        native_input_hold_installed=False, full_world_verified=False, ai_installed_in_game=False,
        remaining=['Connect real task creation/completion observations to repeatable native loader and safe generation switch.',
                   'Receive two genuinely different current-period saves and restore guest faction twice in the same process.',
                   'Install AI/economy adapters using reviewed native interception and a game-safe hold path.',
                   'Connect actual native input/replay-drain receipts to the room barrier.',
                   'Verify full loaded world against host, cover real reload, stop both games on uncertainty.',
                   'Test encrypted connection on the two remote PCs and run two empty-order periods.'])
    write(OUT / '三个门槛接入证据.json', report)
    economy_text = ('两处收入判断的专用适配器已完成本地验证，尚未接入游戏结算。'
                    if args.economy_handoff else '经济规则的两处专用收入判断仍在接线，不修改全局玩家身份。')
    text = f'''三个门槛接入进展（{report['updated']}）

这轮已接入新的任务归属核心、AI 四入口适配器和房间准备屏障。三项门槛尚未通过实机验收，当前仍不是可玩的双人版本。

一、同一进程连续两轮同步
新的 C++ 任务归属核心已接到现有六个转接入口：新一轮开始后，上一轮迟到的任务仍归上一轮，不能误改新一轮状态。16 项独立进程验证通过；创建/收尾记录仍由测试替身提供，实机观察入口和安全安装尚待接通。
{native_text}
还需要把这些真实任务记录接入常驻加载器，并使用两份真正不同的旬末存档，连续两次恢复到 B 的势力地图。已成功的一次自动加载不能替代这项验收。

二、双方势力不被 AI 接管，经济口径一致
四个 AI 决策入口的可加载 DLL 已完成，11 项独立进程验证通过。每次按游戏对象和军团列表重新确定势力归属，区分玩家主军团、委任军团及其他势力。
尚未安装到游戏：仍需四处代码拦截、原函数跳板和适合游戏线程的暂停方式。通用线程阻塞可能冻结画面，不能据此宣称已经解决。
{economy_text}

三、双方准备、等待、核验和失败停止
房间端现分两步确认：先锁住各自的本地输入，再等待双方命令都执行到同一位置并再次确认。
因此 A 先准备后，B 仍可继续下令，其命令可以同步给 A；双方都准备且同步完成后，才产生推进许可。
取消准备先撤销许可，再释放输入；断线、过期回执、超时和不确定结果使房间停止。网络包不能直接冒充游戏确认或启动时间推演。
本轮 {ready['result']['tests']} 项测试通过，包含真实本机 TLS 连接。但输入锁和世界确认仍使用明确标识的测试替身，真实游戏输入拦截尚未启用。房间停止也不等于已证明游戏线程停止。

当前可做的双机动作仍是网络预检。免 Python 便携包为 outputs/two_pc_preflight_portable.zip；两台异地电脑尚未实测。
下一次完整验收：保护双方势力 → 双方准备 → A 推进并生成新档 → B 接收、加载并恢复自己势力 → 核对世界 → 再重复一旬。
这将作为空命令双人原型的首轮测试；通过后再逐步加入持续的赏赐、出征等操作。
'''
    (OUT / '三个门槛接入进展.txt').write_text(text, encoding='utf-8')
    (OUT / '双机测试准备进展.txt').write_text(text, encoding='utf-8')
    (OUT / '开发剩余工作评估.txt').write_text(text, encoding='utf-8')
    resume_path = HERE / 'mainline_20261007_live_resume.json'
    resume = read(resume_path)
    resume.update(three_gate_integration_report=reference(OUT / '三个门槛接入证据.json'),
        task_attribution_latest=task['handoff'], ai_runtime_latest=ai['handoff'],
        ready_barrier_latest=reference(args.ready_handoff), title_join_observer_latest=native,
        next_concrete_integration=report['remaining'])
    if native.get('waiting_for_manual_load_or_cleanup'):
        resume['pending_user_action'] = 'Read slot 34 once normally, then return to map without commands/time advance.'
    elif native['attempted']:
        resume['pending_user_action'] = None
        resume['last_user_action'] = 'Normal manual slot 34 load while observing Load and both Title worker joins.'
        sample = native.get('game_sample')
        if sample:
            game = resume.setdefault('game_last_verified', {})
            game.update(pid=sample['pid'], date=[sample['date'][k] for k in ('year', 'month', 'day')],
                        force=sample['player']['force_id'], ruler=sample['player']['ruler_id'],
                        debugger_attached=False, last_sample=native['postcheck'])
    write(resume_path, resume)
    print(json.dumps(dict(report=str(OUT / '三个门槛接入进展.txt'), all_three_gates_passed=False), ensure_ascii=False))


if __name__ == '__main__':
    main()
