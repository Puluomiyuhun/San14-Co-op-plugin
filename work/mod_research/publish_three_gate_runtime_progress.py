"""Pin this round's results and publish honest stage boundaries; no game access."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'outputs/san14-link'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path):
    return dict(path=str(path.resolve()), sha256=sha(path))


def resolve(name):
    path = Path(name)
    if path.is_absolute():
        return path
    for base in (HERE, ROOT, OUT):
        if (base / path).is_file():
            return base / path
    raise ValueError('Missing pinned artifact: ' + name)


def verify_refs(value):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
            assert sha(resolve(value['path'])) == value['sha256'], value['path']
        for child in value.values():
            verify_refs(child)
    elif isinstance(value, list):
        for child in value:
            verify_refs(child)


def evidence(name):
    path = HERE / name
    data = read(path)
    verify_refs(data)
    for key in ('files', 'source_sha256', 'wrapper_source', 'frozen_source_dependencies'):
        if key in data and isinstance(data[key], dict):
            for file, digest in data[key].items():
                if isinstance(digest, str) and len(digest) == 64:
                    assert sha(resolve(file)) == digest, file
    return dict(handoff=ref(path), claims=data)


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parts = {key:evidence(name) for key, name in (
        ('native_task_provider', 'checkpoint_native_task_provider_handoff.json'),
        ('human_rules_transport', 'human_rules_hook_handoff.json'),
        ('planning_hold_subset', 'checkpoint_planning_hold_handoff.json'),
        ('real_ai_identity_sample', 'human_rules_readonly_probe_handoff.json'),
        ('real_object_table_sample', 'checkpoint_world_object_capture_handoff.json'))}
    previous = OUT / '三个门槛接入证据.json'
    history = HERE / 'three_gate_reports' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    history.mkdir(parents=True)
    saved = history / 'prior-evidence.json'
    saved.write_bytes(previous.read_bytes())
    report = read(previous)
    report.update(schema='san14.three-gate-integration.v2',
        updated=datetime.now().astimezone().isoformat(timespec='seconds'),
        previous_report=ref(saved), runtime_integration_round=parts,
        all_three_gates_passed=False, two_real_periods=False, two_real_clients_playable=False,
        native_input_hold_installed=False, full_world_verified=False, ai_installed_in_game=False,
        this_round_game_writes=0, this_round_game_calls=0, this_round_game_injection=False,
        this_round_user_action_required=False,
        remaining=[
            'Install actual native task observation ports and bind repeatable session ownership without reusing old one-shot claims.',
            'Provide game-thread publication and game-safe AI Hold; then install the four AI and two economy interceptions.',
            'Capture and consume full remote command content with owned lifetimes; cover all native planning input paths and thread migration.',
            'Connect genuine input/drain acknowledgments to ReadyBarrierRoom; never upgrade the current subset receipt to full input hold.',
            'Produce two different fresh host checkpoints, verify loaded world beyond sampled tables, and restore guest faction twice in one process.',
            'Validate map cover during real reload and remote-PC connection, then run two empty-order periods before expanding commands.'])
    write(previous, report)
    text = f'''三个门槛接入进展（{report['updated']}）

本轮完成了三条并行开发支线，并补了两项真实游戏只读采样。当前仍未通过连续两旬的实机验收，不能作为可玩双人版交付。

1. 连续两次加载的任务归属
新的任务来源适配器已经连接到现有常驻转接、动态存档会话、队列、内存检查和返回大地图的观察模块。10 项组合测试通过，包括两轮复用相同地址、迟到的上一轮任务、缺失收尾步骤时拒绝完成。
这些测试在独立进程执行；原生事件与游戏业务函数仍由明确标注的测试替身提供。实际游戏内的来源观察入口尚未安装。候选实现保留两轮记录，不是无限轮常驻会话。

2. 防止双方被 AI 接管，统一经济判断
四个 AI 入口和两处收入判断的原函数跳板、转接与异常展开已经完成，13 项独立进程测试通过，覆盖部分安装失败后的恢复。当前安装函数明确拒绝修改真实游戏模块，真实线程停止进入这些入口的方案仍需接入。
另外，实际从当前 34 号局读取了 51 个势力槽位、21 个有效军团、56 支部队和 45 个非空编组。真实 C++ 归属解析器全部解析成功；张鲁主军团为 11，刘备主军团为 2。这里的 51 是表槽位数，不是 51 个在场势力。
这是归属判断的实机数据验证，尚未启用 AI 规则，也未验证两方实际收入结算。

3. 准备、等待与远程命令
新增原生适配器已经串起赏赐、出征入口、鼠标读取和规划边界。独立进程验证覆盖本地下令关闭后远端执行、取消、断线、过期票据、间接参数被改动、线程错误与异常退出。
远程执行必须绑定完整命令内容及其有效期；缺少真实游戏的内容采集模块时拒绝执行。单纯核对一个命令指针或参数外壳不能放行。
目前仍只覆盖有限入口。直接拦截出征提交会留下菜单事务风险，提前阻止规划界面处理输入的方案仅在测试中验证；尚未启用完整游戏输入锁。因此房间适配器拒绝把这份局部回执当作“双方可以推进”的凭据。

4. 旬末世界校验
补齐了真实地图物件表的采集：3001 个物理槽位，包含 0 号及未启用槽位，共 24008 字节存档字段。按真实指针表读取，不假设对象连续排列；两遍读取一致，保存字节的离线解析也通过。
这只是其中一张表；不是完整世界快照，也不是原子采样，更不能单凭它宣布 A、B 全世界一致。24008 字节也不是整份联机存档大小。

本轮对游戏只读，没有注入新模块、执行游戏函数、推进日期或改动存档，不需要额外手动操作。

下一项实机验收仍是：接入真实常驻入口 → 保护双方势力 → 双方准备 → A 生成新旬末档 → B 同步加载并回到自己的势力 → 世界核验 → 使用另一份新档再重复一旬。
首次双人原型先完成这个空命令循环，再逐步加入连续赏赐、出征等操作。真实输入锁、全世界核验、加载画面遮罩和异地两机连接仍未验收。
'''
    for name in ('三个门槛接入进展.txt', '双机测试准备进展.txt', '开发剩余工作评估.txt'):
        (OUT / name).write_text(text, encoding='utf-8')
    resume_path = HERE / 'mainline_20261007_live_resume.json'
    resume = read(resume_path)
    resume.update(three_gate_integration_report=ref(previous),
        runtime_integration_round={key:value['handoff'] for key,value in parts.items()},
        pending_user_action=None, next_concrete_integration=report['remaining'])
    write(resume_path, resume)
    print(json.dumps(dict(result='PUBLISHED_WITH_GATES_STILL_OPEN', report=str(OUT / '三个门槛接入进展.txt'),
        evidence_sha256=sha(previous)), ensure_ascii=False))


if __name__ == '__main__':
    main()
