"""Freeze the owned-process integration results. Reads local artifacts only."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'outputs/san14-link'
STAGE = HERE / 'human_rules_passthrough_stage_runs/20261007-213654-745897'
PINNED = {
    'os_publisher': ('human_rules_debug_publish_handoff.json', '7ecb72bd00fa66d491d20d6e2111b4d58af74943bd39f91d3f508be7ec9394b0'),
    'six_entry_combination': ('human_rules_stage_debug_rollback_handoff.json', '11d263cda73db596330015d723fb2d2f16954c19d4d4011a3702f15f8adbd359'),
    'load_cpu_ports': ('checkpoint_task_native_ports_handoff.json', 'cc1c098b1c29ea25b611f96c45a307f4cff2773f6641f69ba04e805e4554c5c2'),
    'reward_owned_replay': ('checkpoint_reward_owned_replay_handoff.json', 'decd8a37d9235370f7cda378b86d9fcefbd51efee10a1fc4ec9c5fcb82099a16'),
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path):
    return {'path': str(path.resolve()), 'sha256': sha(path)}


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def resolve(name):
    path = Path(name)
    if path.is_absolute():
        return path
    for base in (HERE, ROOT, OUT):
        if (base / path).exists():
            return base / path
    raise ValueError('Missing artifact: ' + name)


def check(path, digest):
    assert sha(path) == digest, str(path)


def verify_handoff(key, name, digest):
    path = HERE / name
    check(path, digest)
    data = read(path)
    checked = []
    # The final six-entry run owns its recursive source snapshot, including a
    # generated header absent from HERE. Never substitute the superseded target.
    source_root = resolve(data['archival_policy']['actual_sources']) if key == 'six_entry_combination' else HERE
    for field in ('source_sha256', 'tested_dependency_sha256', 'binary_sha256',
                  'artifacts', 'frozen_dependencies', 'raw_receipt_sha256'):
        for name, digest in data.get(field, {}).items():
            item = source_root / name if field == 'source_sha256' else resolve(name)
            check(item, digest)
            checked.append(ref(item))
    for path_field, hash_field in (
        ('result_file', 'result_sha256'), ('result', 'result_sha256'),
        ('fixture_binary', 'fixture_binary_sha256'),
        ('production_object', 'production_object_sha256')):
        if hash_field in data and path_field in data:
            # Some handoffs use a status string in result alongside result_file.
            if path_field == 'result' and 'result_file' in data:
                continue
            item = resolve(data[path_field])
            check(item, data[hash_field])
            checked.append(ref(item))
    return {'handoff': ref(path), 'claims': data, 'verified_artifacts': checked}


def freeze_stage(history):
    data = read(STAGE / 'result.json')
    assert data['result'] == 'PASS' and len(data['cases']) == 4
    assert all(c['result'] == 'PASS' for c in data['cases'])
    snapshot = history / 'stage'
    snapshot.mkdir()
    artifacts = []
    for name, digest in data['source_sha256'].items():
        check(HERE / name, digest)
        shutil.copy2(HERE / name, snapshot / name)
        artifacts.append(ref(snapshot / name))
    for name in ('result.json', 'build.cmd', 'stage.dll', 'stage_fixture.dll',
                 'stage_fixture.exe', 'owned_rules_image.dll',
                 'human_rules_stage_fixture_image_profile.h'):
        shutil.copy2(STAGE / name, snapshot / name)
        artifacts.append(ref(snapshot / name))
    check(snapshot / 'stage.dll', data['production_dll_sha256'])
    check(snapshot / 'stage_fixture.dll', data['fixture_dll_sha256'])
    review = HERE / 'human_rules_passthrough_stage_independent_review_v2.json'
    check(review, '8d765f8a6a7425a14db4eb83e1017acd856f683c4c348d6f6e3ab9b56776ed13')
    handoff = {
        'schema': 'san14.passthrough-stage.handoff.v1',
        'status': 'OWNED_PROCESS_PASS_NOT_GAME_INSTALLED',
        'result': ref(snapshot / 'result.json'), 'artifacts': artifacts,
        'production_dll': ref(snapshot / 'stage.dll'),
        'cases': data['cases'],
        'independent_review': ref(review),
        'review_scope': 'Closes descriptor Prepared publication and Snapshot error-read findings. Review predates the explicit owned MEM_IMAGE fixture extension; production main-image hash gate remains unchanged.',
        'interface': 'HumanRulesStagePrepare creates pinned trampolines/metadata and an immutable six-site descriptor. It never publishes source patches. Require exported preparation_state Prepared before/after reading, plus nonce, process birth and module binding.',
        'profiles': {'ai_prefix_sizes': [16, 15, 15, 15], 'economy_call_sizes': [5, 5]},
        'production_image_sha256': '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025',
        'production_gate': 'Exact current process main MEM_IMAGE, supported image hash, native source and unwind profiles. Explicit fixture DLL is separately compiled and marked fixture=1.',
        'game_access': False, 'policy_enabled': False,
        'production_publisher_connected': False,
        'limitations': [
            'Pass-through only. AI business functions in owned fixtures are declared doubles; actual archived entry wrappers execute on CPU.',
            'The debugger publisher controls only self-created children. Its terminate-on-uncertainty policy must not be transplanted to a game attach.',
            'No game initialization/injection/activation owner, no AI business drain, no complete input hold.',
            'Modules, trampolines and metadata are pinned; no hot unload or reset is supported.'],
    }
    path = HERE / 'human_rules_passthrough_stage_handoff.json'
    assert not path.exists(), 'Frozen stage handoff already exists; do not overwrite'
    write(path, handoff)
    return {'handoff': ref(path), 'claims': handoff}


def main():
    parts = {key: verify_handoff(key, *item) for key, item in PINNED.items()}
    history = HERE / 'three_gate_reports' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    history.mkdir(parents=True)
    parts['passthrough_stage'] = freeze_stage(history)
    previous = OUT / '三个门槛接入证据.json'
    shutil.copy2(previous, history / 'prior-evidence.json')
    report = read(previous)
    remaining = [
        'Implement target-specific initialization and pass-through publication ownership; the own-child debugger cannot be used as a game PID installer.',
        'Activate Load ports before runner 834D98 under a proven worker lifetime; add real parent/start/closure/join and both Title task source ports.',
        'Bind reward replay to genuine planning callback, original submit and world/pool lifetime; complete native local input hold and real Ready/drain acknowledgments.',
        'Enable two-human AI/economy rules at a verified game business boundary after pass-through validation.',
        'Export two distinct fresh host period checkpoints; load both in one guest process, restore its faction, and verify the complete world.',
        'Validate map cover during real reload and connect the two remote PCs; run two empty-order periods before expanding commands.',
    ]
    report.update(
        schema='san14.three-gate-integration.v3',
        updated=datetime.now().astimezone().isoformat(timespec='seconds'),
        previous_report=ref(history / 'prior-evidence.json'),
        native_ports_integration_round=parts,
        all_three_gates_passed=False, two_real_periods=False,
        two_real_clients_playable=False, native_input_hold_installed=False,
        full_world_verified=False, ai_installed_in_game=False,
        this_round_game_access=False, this_round_game_writes=0,
        this_round_game_calls=0, this_round_game_injection=False,
        this_round_user_action_required=False, remaining=remaining)
    write(previous, report)
    progress = f'''三个门槛接入进展（{report['updated']}）

本轮新增：六个入口的安装、执行、恢复组合；加载线程四个实际执行位置的捕获；赏赐命令的完整参数与生命周期管理。均已有可编译代码和通过的独立进程测试。本轮没有访问或改动游戏，也不需要用户操作。

目前仍未完成两个真实客户端连续两旬的运行，不能作为可玩双人版交付。独立进程测试与游戏实测分开记账，不把新增测试数量折算成完成百分比。

1. 两名玩家的 AI 与收入入口
新的组合已在自建 Windows 进程里，针对归档的四个 AI 入口、两个收入判断入口完成：准备转接模块 → 安装 → 执行 → 恢复原指令。正常执行涵盖 120 次 AI 入口转发和 180 次收入判断；另测原函数异常，以及六个位置分别安装失败后的恢复，共 8 项通过。
实际执行的是已归档的游戏入口机器指令；后面的 AI 业务函数是明确标注的测试替身。当前模块只保持原行为，尚未启用“两个人类势力免于 AI 接管”的规则。不能把这些结果写成真实 AI 决策或两方收入已经验证。
更底层的 Windows 安装机制另有 13 项测试；转接 DLL 本身有 4 项测试。它们相互衔接，不能当成三次独立的游戏成功。
剩下的是面向游戏本身的初始化和安装入口，以及启用规则的合适时机。当前测试程序只创建自己的子进程，不能直接拿来附加游戏。

2. 连续加载的真实记录来源
加载线程的四个执行位置，已经通过实际硬件断点取得 CPU 上下文，再送入现有任务归属和加载会话模块。5 项测试通过，验证两轮 Load 片段、异常传播、寄存器保持和断点恢复。
这次确实执行了归档的任务运行器；加载业务、系统同步对象仍有测试替身。记录范围仅到 Load 收尾，未宣称完成身份切换或返回大地图。
剩下的是在真正加载线程足够早的位置启用捕获，以及补齐父调度器和 Title 两个任务的来源。缺少它们时，不允许把“某段结束”当作“整轮加载完成”。

3. 赏赐命令
已补上完整武将名单的构造、势力与资金归属检查、命令内容检查，以及执行结束后的资源回收。24 项测试通过，包括等待时执行远程赏赐、过期、取消、参数被改动、内存池变化和原函数异常。
它解决了“网络命令如何形成游戏能用的参数、这些参数要保留多久”的问题。真实城市、武将、世界仍归游戏所有，外层还要保证执行期间不换世界、不释放相关对象，并在正确游戏线程调用。当前没有开启完整输入锁，也没有新做游戏赏赐实测。

离双人测试还剩的主线
第一步：完成真游戏中的安装和任务来源接线，先只转发原行为，核对没有破坏游戏。
第二步：接入双方势力保护、准备后的输入锁、真正的命令排空回执。
第三步：让 A 实际生成两份不同的新旬末档，B 在同一进程连续加载两次、恢复自身势力，并核对完整世界。
第四步：验证大地图遮罩，再接通异地两机，先跑两旬不下新命令的循环，之后加赏赐和出征。

此前已验证过单次自动加载并回到刘备大地图；这不等于常驻、连续两旬同步已完成。现有全世界核验、加载遮罩、最新旬末档自动导出和异地网络连接仍未通过完整实机验收。
'''
    for name in ('三个门槛接入进展.txt', '双机测试准备进展.txt', '开发剩余工作评估.txt'):
        (OUT / name).write_text(progress, encoding='utf-8')
    resume_path = HERE / 'mainline_20261007_live_resume.json'
    resume = read(resume_path)
    shutil.copy2(resume_path, history / 'prior-resume.json')
    resume.update(three_gate_integration_report=ref(previous),
                  native_ports_integration_round={key: part['handoff'] for key, part in parts.items()},
                  pending_user_action=None, next_concrete_integration=remaining,
                  latest_round_game_access=False)
    write(resume_path, resume)
    receipt = {
        'result': 'PUBLISHED_OWNED_PROCESS_PROGRESS_REAL_GAME_GATES_OPEN',
        'evidence': ref(previous),
        'progress': ref(OUT / '三个门槛接入进展.txt'),
        'handoff_count': len(parts),
        'verified_artifact_references': sum(len(part.get('verified_artifacts', [])) for part in parts.values()),
        'game_access': False, 'user_action_required': False,
    }
    write(history / 'publication.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
