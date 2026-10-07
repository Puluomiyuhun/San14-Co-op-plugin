"""Publish the reviewed offline integration and its bounded remaining work."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'outputs'/'san14-link'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import checkpoint_admitted_connected_prototype as connected
    connected.check_sources()
    test_path=sorted((HERE/'checkpoint_admitted_connected_prototype_tests').glob('*/result.json'))[-1]
    test=json.loads(test_path.read_text(encoding='utf-8'))
    if test['result']!='PASS' or test['tests_run']!=9:raise RuntimeError('Integration has not passed')
    for name,expected in test['source_sha256'].items():
        if sha(HERE/name)!=expected:raise RuntimeError('Tested source changed: '+name)
    for row in test['runs']:
        if sha(Path(row['path']))!=row['report_sha256']:raise RuntimeError('Run receipt changed')
    success=next(row for row in test['runs'] if row['case']=='success')
    (OUT/'输入检查接入诊断结果.json').write_bytes(Path(success['path']).read_bytes())
    runtime_path=HERE/'checkpoint_admitted_runtime_handoff.json'
    runtime=json.loads(runtime_path.read_text(encoding='utf-8'))
    review_path=HERE/'checkpoint_admitted_independent_review.json'
    review=json.loads(review_path.read_text(encoding='utf-8'))
    if review['result']!='PASS_BOUNDED_OFFLINE_REVIEW':raise RuntimeError('Independent review pending')
    for name,expected in review['reviewed_source_sha256'].items():
        if sha(HERE/name)!=expected:raise RuntimeError('Reviewed source changed: '+name)
    generation_path=HERE/'checkpoint_session_generation_runs/20261007-131711-064041/result.json'
    generation=json.loads(generation_path.read_text(encoding='utf-8'))
    if generation['result']!='PASS' or len(generation['cases'])!=8:
        raise RuntimeError('Generation isolation verification pending')
    for field in ('source_and_binary_sha256','frozen_dependency_sha256'):
        for name,expected in generation[field].items():
            if sha(HERE/name)!=expected:raise RuntimeError('Generation evidence changed: '+name)
    generation_handoff_path=HERE/'checkpoint_session_generation_handoff.json'
    generation_handoff=json.loads(generation_handoff_path.read_text(encoding='utf-8'))
    if generation_handoff['evidence_sha256']!=sha(generation_path):
        raise RuntimeError('Generation handoff differs')
    for name,expected in generation_handoff['source_and_artifact_sha256'].items():
        if sha(HERE/name)!=expected:raise RuntimeError('Generation handoff source changed: '+name)
    world_path=HERE/'checkpoint_world_next_table_handoff.json'
    world=json.loads(world_path.read_text(encoding='utf-8'))
    for name,expected in world['source_sha256'].items():
        if sha(HERE/name)!=expected:raise RuntimeError('World schema source changed: '+name)
    for key in ('fixture_report','native_report'):
        if sha(Path(world[key]))!=world[key+'_sha256']:raise RuntimeError('World evidence changed')
        if json.loads(Path(world[key]).read_text(encoding='utf-8'))['result']!='PASS':
            raise RuntimeError('World checks have not passed')
    world_review_path=HERE/'checkpoint_world_next_table_review.json'
    world_review=json.loads(world_review_path.read_text(encoding='utf-8'))
    if world_review['verdict']!='ACCEPT_WITH_DOCUMENTED_SCOPE_LIMITS' or \
            world_review['blocking_findings'] or world_review['target_handoff']['sha256']!=sha(world_path):
        raise RuntimeError('World review does not match final handoff')

    entry='''@echo off
chcp 65001 >nul
setlocal
set "PYTHONUTF8=1"
title 三国志14联机 - 输入检查接入离线诊断
set "SAN14_ADMITTED_SCRIPT=%~dp0..\\..\\work\\mod_research\\checkpoint_admitted_connected_prototype.py"
if not exist "%SAN14_ADMITTED_SCRIPT%" goto missing
where py >nul 2>nul
if errorlevel 1 goto fallback
py -3 "%SAN14_ADMITTED_SCRIPT%"
set "SAN14_ADMITTED_EXIT=%errorlevel%"
goto finished
:fallback
where python >nul 2>nul
if errorlevel 1 goto missing_python
python "%SAN14_ADMITTED_SCRIPT%"
set "SAN14_ADMITTED_EXIT=%errorlevel%"
goto finished
:missing
echo 找不到本工作区程序，请不要单独移动此入口。
set "SAN14_ADMITTED_EXIT=2"
goto finished
:missing_python
echo 没找到 Python 3，请保留错误信息。
set "SAN14_ADMITTED_EXIT=2"
:finished
echo.
echo 本程序只运行本机房间和自建测试进程，不连接游戏，不修改游戏存档。
echo 成功后仍等待完整世界与真实游戏接入，不是可玩的联机版。
pause >nul
exit /b %SAN14_ADMITTED_EXIT%
'''
    entry_path=OUT/'运行输入检查接入诊断.cmd'
    entry_path.write_bytes(entry.replace('\n','\r\n').encode('utf-8'))
    notes='''本轮房间与加载主线进展（2026-10-07）

已接通的新一段
A/B 的真实本机 TLS 房间连接 → 历史存档传输与校验 → 持久的一次性加载意图 → 新 C++ 加载控制器 → 玩家操作检查 → Session 加载/身份/下令界面观察 → 向 A 回报等待状态。
收到的存档字节实际交给新程序；新程序缺少暂存文件时会拒绝，不再回退到另一份固定文件。
新加载程序 17 项测试通过，网络组合 9 项测试通过。
9 项覆盖成功路径、传输损坏、三种时机断线、报告未关闭、进度回复丢失，以及操作在检查前存在/检查过程中出现。
最后两种情况实际启动了检查，但创建加载队列和发布加载请求的次数都是 0。玩家操作由原来的游戏逻辑替身处理，工具不直接擦掉操作。
另用真实子进程回执的 22 种字段变更验证：错误势力、错误存档、重复执行计数、旧绑定、缺少检查等不能误报为完成。

世界数据核验新增
完成 CForceData 势力表 52 个槽位的原生读写验证：每槽 378 字节，共 19,656 字节，保留全部实际序列化字段。
实际归档机器码验证 11 项、结构核验 8 项通过；这是使用自建数据验证读取结构，尚未采集当前游戏的完整势力表。
发现版本 91 和 92 的表长度相同，但版本 91 会转换两个字段，往返后不能原样恢复。因此新接口明确要求版本 92，不按长度猜版本。
另一项流转换开关也由调用方显式提供并检查为关闭；不能仅凭版本和数据长度判断读取方式。
加上此前地图、对象表等结果，世界覆盖继续扩大；仍不能把其中任一表相同称为整个世界一致。

连续多旬的会话隔离
已用同一自建进程里的两个独立模块验证旧、新会话隔离，8 个场景通过。
旧模块保留原来的会话；迟到或重复的旧回调不会使用新会话的一次性执行记录。
已经提交过加载请求、还有活动调用、菜单未完成或发生异常时，会拒绝交接。
这是两套固定会话的最小隔离验证，不是连续两次完整加载，也不是无限增加模块的最终方案。
真实游戏中加载完成后的交接、旧观察器收尾、主循环协调和长期复用仍未解决；尚未与新加载控制器接在一起。

如何运行
双击“运行输入检查接入诊断.cmd”。不需要手动操作游戏；程序不访问游戏或 Steam。
看到 PASS_EXPECTED_WAIT_FOR_GAME_PROVIDERS 表示这条离线链通过。
“输入检查接入诊断结果.json”记录本次结果；旧入口和旧证据保留，便于比较。
本入口依赖完整工作区，不能单独发送给朋友当安装包使用。

证据边界
网络连接、文件传输、持久日志、父子进程通信、原生 Session 和输入检查组件实际运行。
游戏的队列/加载/重建主体仍使用自建测试替身；部分已归档机器码在自建进程中执行。
不是在正在运行的游戏中注入，也不是两台电脑实机联调。
输入准入检查只决定是否可以开始同步，还不等于整个同步期间都隔离了键鼠操作。
成功路径仍停在等待完整世界核验，不开放下一旬，不证明遮罩画面、完整输入隔离或同进程重复加载。

距离能简单试玩还差什么
估计受限原型约完成 40%～50%，只是工程判断，不按测试数量换算。当前仍有约一半工作，并非只剩安装包。
1. 真实保存—B自动加载—B身份恢复连续循环；同一游戏进程能够第二次、第三次同步。
2. 同步期间的实际输入隔离、旧地图画面保留、新地图确认后恢复操作。
3. 完整世界核验：势力/武将/城市/部队/任务/事件及共享附加状态，不能只看日期与君主。
4. 两个人类势力的 AI 和规则接入；赏赐、出征先形成持续双端同步白名单，再扩大内政。正式事件归属和等待也须接入。
5. 两台电脑连续至少两旬，验证断线/加载失败不重做命令，然后整理助手窗口和安装步骤。

下一次实机验证目标
先验收一个完整的 A 导出、B 自动加载和身份恢复循环；随后验证同一进程下一旬再次同步。
在这些步骤通过之前，不用堆更多菜单功能来掩盖原生加载主线的缺口。
首版不要求战斗动画完全锁步，但仍要求旬末由 A 的完整状态统一校正 B。
'''
    (OUT/'输入检查接入与剩余工作.txt').write_text(notes,encoding='utf-8')
    evidence=dict(schema='san14.admitted-connected-progress.v1',updated=datetime.now().isoformat(),
        result='OFFLINE_INTEGRATION_PASS_NOT_PLAYABLE',game_access=False,full_world_verified=False,
        same_process_repeat_load_proven=False,real_two_client_test=False,
        estimate=dict(restricted_mvp_percent=[40,50],basis='ENGINEERING_JUDGMENT_NOT_TEST_COUNTS'),
        tests=dict(runtime=17,network_integration=9,receipt_mutation_subcases=22,generation_isolation=8,
                   force_table_native=11,force_table_schema=8),
        runtime_approved_sha256=connected.APPROVED_EXE,
        evidence=[dict(path=str(p),sha256=sha(p)) for p in
                  (runtime_path,test_path,review_path,world_path,world_review_path,
                   generation_path,generation_handoff_path)],
        entry=dict(path=str(entry_path),sha256=sha(entry_path)))
    (OUT/'输入检查接入与剩余工作.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    history=OUT/'开发剩余工作评估.txt'
    marker='最新进展（2026-10-07，准入网络接线）'
    old=history.read_text(encoding='utf-8')
    if not old.startswith(marker):
        history.write_text(marker+'：新加载控制器已接到房间实际传输链；网络9场景通过，'
            '新增势力表完整序列化字段核验和两代会话隔离验证。仍未完成真实游戏连续多旬，'
            '受限原型估计40%～50%。最新入口与缺口见《输入检查接入与剩余工作.txt》。\n\n'+old,encoding='utf-8')
    print('Published reviewed admitted runtime integration.')


if __name__=='__main__':main()
