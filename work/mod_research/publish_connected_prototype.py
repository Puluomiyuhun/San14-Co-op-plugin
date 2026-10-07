"""Publish the fixed, workspace-only diagnostic entry and evidence index."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1]/'outputs'/'san14-link'

entry = '''@echo off
chcp 65001 >nul
setlocal
set "PYTHONUTF8=1"
title 三国志14联机 - 房间到加载离线诊断
set "SAN14_CONNECTED_SCRIPT=%~dp0..\\..\\work\\mod_research\\checkpoint_connected_prototype.py"
if not exist "%SAN14_CONNECTED_SCRIPT%" goto missing
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%SAN14_CONNECTED_SCRIPT%"
set "SAN14_CONNECTED_EXIT=%errorlevel%"
goto finished
:python_fallback
where python >nul 2>nul
if errorlevel 1 goto missing_python
python "%SAN14_CONNECTED_SCRIPT%"
set "SAN14_CONNECTED_EXIT=%errorlevel%"
goto finished
:missing
echo 找不到本工作区程序。请不要单独移动这个入口文件。
set "SAN14_CONNECTED_EXIT=2"
goto finished
:missing_python
echo 没找到 Python 3，请保留窗口中的信息。
set "SAN14_CONNECTED_EXIT=2"
:finished
echo.
echo 只运行本机测试房间和测试进程，不连接游戏，不修改游戏存档。
echo 这不是可游玩的联机版。按任意键关闭窗口。
pause >nul
exit /b %SAN14_CONNECTED_EXIT%
'''
(OUT/'运行房间到加载诊断.cmd').write_bytes(entry.replace('\n','\r\n').encode('utf-8'))
multi_entry=entry.replace('房间到加载离线诊断','连续两旬通信诊断').replace(
    'checkpoint_connected_prototype.py','checkpoint_room_lifecycle_test.py')
(OUT/'运行连续两旬通信诊断.cmd').write_bytes(multi_entry.replace('\n','\r\n').encode('utf-8'))

notes = '''三国志14双客户端联机：本轮接线进展

最新：B 的同步进度已通过真实控制连接传回 A。A 能看到接收、文件就绪、加载请求、身份恢复和等待世界核验。
这些都是诊断消息，不授予继续游戏的权限；即使收到身份恢复提示，也不会据此进入下一旬。
已加入“进度已上报但回复丢失”的故障验证：保留一次性加载意图，不执行第二次加载；本轮该故障发生在原生 ARM 前，实际 ARM 次数为 0。

本次新增
同一组 A/B 房间连接和同一个下载入口，已经能完成连续两旬的通信；每旬的准备由各自认证连接提交。
上一旬下载票、旧连接、旧存档编号不能用于下一旬；前一旬未完成确认时不能发布下一旬。
房间初始规划阶段就绑定双方连接，断线会通知旬次协调器。重连只恢复房间席位，不自动继续不确定的游戏状态。
控制连接默认每 5 秒空闲保活，避免内政思考超过网络层 30 秒空闲限时而被断开。
保活和玩家请求串行收发，丢回执不自动重发。保活线程和连接退出均检查清理结果。
A 端来源检查已接进主诊断：核验九份既有保存/发布证据，传输实际历史存档及来源说明。
这份历史存档只准用于 203 年 8 月中旬的离线重放，不冒充当前 A 的新存档。

现在可以测试什么
双击同目录“运行房间到加载诊断.cmd”。不需要操作游戏；即使游戏开着，本入口也不访问它。
程序在本机创建两个真实 TLS 房间连接，分别选择张鲁、刘备；再另开下载连接传输工作区中的历史测试存档。
收到并完整校验后，先记录不可重复的加载意图，再把实际收到的字节交给本程序创建的 C++ 测试进程。
测试进程经过 Session 加载桥、势力身份检查、新 User 下令阶段检查。结束后，房间连接仍能收发消息。
测试创建的进程、监听端口和连接在结束时关闭，证书、临时档和记录只留在工作区。

如何判断结果
成功显示 PASS_EXPECTED_WAIT_FOR_GAME_PROVIDERS，并更新“房间到加载诊断结果.json”。
这个名字表示离线链路通过，但仍等待真实游戏接入；没有声称真实游戏完成同步。
另一个入口“运行连续两旬通信诊断.cmd”检查连续轮换、准备、旧票作废和掉线保持；当前 15 项通过。
连续两旬通信使用明确标注的合成世界与完成回执，不包含两次真实游戏推演或自动读档。
如果显示 FAIL，保留窗口和报告，不要把重复运行当作对真实游戏的恢复办法。
本诊断每次创建全新测试房间，不连接朋友的电脑；也不是可以单独发给朋友的 MOD 安装包。

新增的实际连接
1. 房间控制连接和存档下载连接已分开。关闭下载不会踢掉 B 的房间席位。
2. 下载权限绑定当前 A/B 连接、势力、旬次、存档；一次性下载票不能冒充房间重连凭证。
3. 下载来的字节真正进入 C++ 测试加载路径，没有在最后换成另一份固定测试内容。
4. 一个加载意图只能执行一次；即使重新打开本地记录，也不会再发第二次加载。
5. 存档读入、势力换好、回到下令阶段分开核验；还停在报告界面不能当作可继续游戏。

输入模块的并行进展
已完成键盘查询桥和已排队菜单检查，分别通过 14 项、11 项独立测试。
检查到玩家已有操作时拒绝进入同步，不直接清掉玩家的命令；能区分本次工具授权的加载菜单。
这些输入模块尚未安装到真实游戏，也未与本入口组成完整输入屏障。

证据与限制
房间下载模块 12 项测试，单次 runtime 10 项测试，完整接线 7 项测试通过；分类记录见“房间到加载开发记录.json”。
同步进度权限及顺序另有 8 项测试通过。
新增房间生命周期 15 项、连接保活及清理 4 项、历史保存导出来源 10 项测试通过。
完整接线包含成功路径、字节损坏、B 在传输前/下载后/加载绑定后断线、加载后仍停在报告界面。
加载前会复核已观察到的连接状态；这还不是对物理断网瞬间的持续游戏屏障。
原游戏函数在 C++ 测试进程中仍使用替身，开头的游戏空闲状态是明确标注的测试条件。
这轮没有自动读真实游戏存档、没有实际切换游戏画面，也没有双机对战或战斗速度测试。
即使文件传完、刘备身份和下令状态检查通过，仍保留等待状态；完整世界没有核验前不放行下一旬。
本机下载计时只反映回环网络，不能用于估计朋友联网时的总同步等待。

距离简单实机联机还缺什么
优先：真实游戏的自动保存/加载入口与这条链连接，实际输入隔离，保留地图的画面遮罩和恢复。
随后：旬末完整世界核验、实际 A/B 两端操作持续收集与执行、双人势力的 AI/权限和事件归属。
最终验收：两台电脑连续完成至少两旬，检查 B 势力、命令、战场结果、掉线等待和加载失败处理。
目前不能称为“已经能双人玩”。离线装配有了新的实跑证据；真实游戏闭环仍是主要缺口。
'''
(OUT/'房间到加载测试说明.txt').write_text(notes,encoding='utf-8')

sources = [HERE/'checkpoint_room_artifacts_runs/20261007-104915-814768/result.json',
           HERE/'checkpoint_guest_runtime_fixture_handoff.json',
           HERE/'checkpoint_native_input_keyboard_handoff.json',
           HERE/'checkpoint_native_input_pending_handoff.json',
           HERE/'checkpoint_host_export_handoff.json']
for directory in ('checkpoint_room_lifecycle_tests','checkpoint_room_client_tests','checkpoint_room_progress_tests'):
    sources.append(sorted((HERE/directory).glob('*/result.json'))[-1])
integration = sorted((HERE/'checkpoint_connected_prototype_tests').glob('*/result.json'))[-1]
sources.append(integration)
latest=json.loads(integration.read_text(encoding='utf-8'))
if latest['result']=='PASS':
    success=next(row for row in latest['runs'] if row['case']=='success')
    path=Path(success['path'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=success['report_sha256']:
        raise RuntimeError('Connected test receipt changed')
    (OUT/'房间到加载诊断结果.json').write_bytes(path.read_bytes())
files = [HERE/name for name in ('checkpoint_connected_prototype.py','checkpoint_connected_prototype_test.py',
    'checkpoint_room_artifacts.py','checkpoint_room_artifacts_test.py','checkpoint_guest_runtime_fixture_client.py',
    'checkpoint_room_lifecycle.py','checkpoint_room_client.py','checkpoint_host_export_reader.py','checkpoint_room_progress.py',
    'checkpoint_guest_runtime_fixture.exe')]
files.extend(OUT/name for name in ('room_transport.py','room_session.py','authoritative_sync.py',
                                  'checkpoint_transfer.py','checkpoint_journal.py','运行房间到加载诊断.cmd',
                                  '运行连续两旬通信诊断.cmd'))
data = dict(schema='san14.connected-prototype-progress.v1',updated=datetime.now().isoformat(),
    result='OFFLINE_INTEGRATED_NOT_PLAYABLE',game_access=False,real_two_client_test=False,
    full_world_verified=False,presentation_proven=False,input_hold_proven=False,
    evidence=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sources],
    components=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files],
    tests=dict(room_download=12,runtime=10,keyboard=14,pending_admission=11,connected_integration=7,room_progress=8,
               room_lifecycle=15,room_heartbeat=4,historical_host_export=10),
    estimate_note='No completion percentage inferred from test counts; real-game closed loop remains unverified.')
(OUT/'房间到加载开发记录.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('Published workspace diagnostic and evidence index.')
