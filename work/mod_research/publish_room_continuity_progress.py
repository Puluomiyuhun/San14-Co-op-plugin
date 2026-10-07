"""Consolidate this turn's offline integration and native input evidence."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'outputs'/'san14-link'
files=[HERE/name for name in ('checkpoint_host_export_handoff.json',
    'checkpoint_native_input_action_handoff.json','checkpoint_native_input_prefetch_handoff.json')]
for directory in ('checkpoint_connected_prototype_tests','checkpoint_room_lifecycle_tests','checkpoint_room_client_tests'):
    p=sorted((HERE/directory).glob('*/result.json'))[-1]
    assert json.loads(p.read_text(encoding='utf-8'))['result']=='PASS'
    files.append(p)
for name in ('checkpoint_native_input_action_fixture.json','checkpoint_native_input_prefetch_fixture.json'):
    p=HERE/name;data=json.loads(p.read_text(encoding='utf-8'))
    assert data.get('result')=='PASS' or data.get('failed')==0
    files.append(p)
evidence=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
report=dict(schema='san14.room-continuity-input-progress.v1',updated=datetime.now().isoformat(),
    result='OFFLINE_INTEGRATED_NOT_PLAYABLE',game_access=False,two_game_periods_verified=False,
    map_cover_in_game_verified=False,full_input_hold_verified=False,full_world_verified=False,
    tests=dict(room_lifecycle=15,room_keepalive=4,historical_export=10,connected_native_fixture=6,
               native_action=14,native_prefetch=8),evidence=evidence,
    source_sha256={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in
        ('checkpoint_room_lifecycle.py','checkpoint_room_client.py','checkpoint_host_export_reader.py',
         'checkpoint_connected_prototype.py')})
(OUT/'连续通信与输入接线进展.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
notes='''三国志14双客户端联机：连续通信与输入接线进展

这轮完成的连接
同一个房间里，A、B 分别通过自己的连接提交准备；只有双方操作已处理完毕才满足准备条件。
两个控制连接和下载服务能够保留到下一旬；上一旬的下载票、旧连接和旧存档编号不能读取新旬文件。
必须有前一旬完成回执才能发布下一旬；第一份检查点也必须对应开局绑定的日期、时期和游戏实例。
玩家掉线时协调器一起暂停。重连恢复房间席位，但不自动重试结果不明的游戏操作。
关闭联机流程会撤销已提交的准备和未使用的推进许可，防止关闭后仍开始下一步。
以上 15 项测试通过，包含同一 TLS 房间连接完成两次传输。两旬数据和完成回执是明确标注的模型，不是两次实机战斗。

内政思考时保持连接
原网络处理层有 30 秒空闲超时。新增控制连接包装器默认每 5 秒空闲发送一次状态心跳。
心跳与玩家请求共用串行收发，避免把一方回复当成另一方的回复。下载继续使用独立连接。
超时或丢回执后不自动重发；明确退出会停止心跳并清理连接，清理失败保留错误且允许再次显式关闭。
4 项真实本机 TLS 测试通过，含超过缩短后的服务器空闲时限仍在线、并发请求配对、丢回执不重发及关闭失败。

保存来源与加载已串接
新增历史 A 导出读取器，核验九份既有工作区证据，包括成功保存及返回、一次性记录、原文件和发布后完整读回。
返回真实历史存档字节及来源说明，已接进房间传输和 C++ 加载测试进程；完整链路 6 项测试继续通过。
这份档只对应 203 年 8 月中旬，接口会拒绝拿它代表其他日期。读取历史证据没有触发当前游戏保存。
来源模块本身 10 项测试通过。它保留“历史归档”标记，没有生成当前 A 世界的实时证明。

输入拦截补充
菜单读取前的中间调用桥：8 项自建 PE 测试通过。实际调用已有待处理检查，再执行原始菜单读取指令。
整数寄存器、标志、XMM 和 MXCSR 恢复经过测试；玩家原请求仍由原流程消费，不被检查器清除。
实际触发重放读取的访问异常后，Windows 能展开测试调用栈，未伪造正常返回。真实跳转安装、游戏现场排他，以及更宽 SIMD/x87 状态仍未验证。
动作查询旁路：14 项独立进程测试通过。执行原始动作查询和已初始化 TLS 快路径，未用替代函数冒充。
来源未初始化、动作或映射未知时拒绝；中和查询结果时保留物理按键状态。真实设备未访问，完整输入屏障尚未完成。

现在怎么试
“运行房间到加载诊断.cmd”：核验历史导出来源，创建 A/B 本机房间、下载、一次加载、检查刘备身份和下令阶段。
“运行连续两旬通信诊断.cmd”：检查两次通信的衔接、旧票作废、准备权限、掉线和关闭流程。
这两个入口都不需要操作游戏，仍依赖本工作区的程序，不能单独发给朋友作为 MOD 安装包。

下一段主线
把原生输入、加载和画面等待层接到真实游戏，并验证自动读入后身份、日期、镜头及操作恢复。
然后连接完整世界核验、正常菜单命令的持续捕获与远端执行，验证两台电脑连续两旬。
目前仍不能开始真实双人游戏；本轮完成的是通信连续性、来源核验接线和两条输入路径的独立验证。
'''
(OUT/'连续通信与输入接线进展.txt').write_text(notes,encoding='utf-8')
target=OUT/'开发剩余工作评估.txt'
prefix=('最新进展（2026-10-07，连续通信接线）：房间连续两旬通信、准备接口、旧票作废、断线暂停、'
        '5秒空闲保活和历史导出→加载链已通过离线测试；两条输入路径的独立机器码验证通过。'
        '连续旬次使用合成完成回执，未完成真实双机循环。当前进展见《连续通信与输入接线进展.txt》。\n\n')
old=target.read_text(encoding='utf-8')
if not old.startswith(prefix):target.write_text(prefix+old,encoding='utf-8')
print('Published room continuity and input evidence.')
