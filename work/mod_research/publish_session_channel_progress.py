"""Publish source-bound IPC evidence, using workspace files only."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'outputs'/'san14-link'
def checked(directory):
    p=sorted((HERE/directory).glob('*/result.json'))[-1]
    r=json.loads(p.read_text(encoding='utf-8'))
    assert r['result']=='PASS'
    for name,expected in r['source_sha256'].items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==expected,name
    return p,r

unit_path,unit=checked('checkpoint_session_channel_runs')
native_path,native=checked('checkpoint_session_channel_native_runs')
session_path,session=checked('checkpoint_guest_native_session_fixtures')
assert not unit['game_access'] and not native['game_access'] and not session['game_access']
stamp=datetime.now().astimezone().isoformat()
report={'schema':'san14.session-channel-progress.v1','updated_at':stamp,
    'local_control_channel_implemented':True,'actual_cross_process_transport_verified':True,
    'production_session_core_used':True,'native_game_bodies':'synthetic fixtures',
    'full_native_port_implemented':False,'live_loader_installed':False,'real_game_access':False,
    'steam_save_directory_access':False,'game_window_access':False,
    'test_counts':{'client_protocol_and_cancellation':unit['tests_run'],
                   'actual_cross_process':native['tests_run']},
    'evidence':{'client':str(unit_path),'cross_process':str(native_path),'session':str(session_path)},
    'source_sha256':{**session['source_sha256'],**unit['source_sha256'],**native['source_sha256']},
    'remaining':['native input barrier and fresh neutral release',
                 'full semantic shared-world/planning/camera evidence providers',
                 'game profile installation, normal menu cancel and post-load cleanup',
                 'repeatable multi-period binding and actual two-client loop'],
    'deadline_limit':'Python quarantines unconfirmed cancelled I/O without buffer release or reconnect. C++ server drains own cancelled pipe I/O before freeing stack memory; cleanup may exceed the transfer deadline.',
    'secrets_logged':False,'native_gameplay_enabled':False}
(OUT/'原生通信接入进展.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
text=f'''原生通信接入进展
更新：{stamp}

本轮补通了外部Python控制端与C++加载会话之间的本地通信，不访问真实游戏、游戏窗口或Steam存档目录。

实际新增内容

现在控制端可以通过Windows本地命名管道，向已经配置好的原生会话发送三类请求：查询状态、启动一次、停止新动作并保留观察。服务端直接调用已有统一Session，没有再造一个假的加载状态机。四个更新入口、加载/文件工作线程、身份恢复仍由之前的共用核心处理。
协议绑定本次会话、加载意图、连接进程及消息编号。只允许本机指定控制进程；客户端先核对服务进程身份，再发送会话凭据。不会通过消息传入任意地址、函数、存档路径或势力参数。
启动在发送前和接收执行前分别被标记为已使用。回执丢失、断线或超时后，可以显式重连继续查询，但不能再次启动同一次加载。停止并不撤掉正在进行的加载观察，也不冒充已经恢复到地图。
读取被中断时，客户端先取消并确认操作结束，再释放缓冲；无法确认的连接保留相关内存和句柄，不自动重用。C++服务端同样先完成取消收尾再释放栈内存，因此其取消清理可能比通信期限更长，尚不承诺严格墙钟退出上限。

本轮验证

{unit['tests_run']}项客户端协议和异常取消测试通过。
{native['tests_run']}项真实跨进程测试通过：Python通过实际Windows管道驱动自有C++进程中的Session，经过合成User/Menu/Game/Load/Title调用，取得实际核心产生的文件读取、加载结束和身份记录。还验证了丢回执重连、重复启动、旧消息重放、错误加载意图、进程身份不符、半包断线、空闲超时，以及真正挂起读取后的取消。
这里的管道、进程、核心回调、文件哈希、一次性记录和原子身份提交是真实执行；游戏对象、世界反序列化和原生初始化体仍是测试替身。能力标记持续明确：身份记录不等于完整世界已验证，也不等于可以恢复操作。

还没有完成什么

这是完整NativePort所需的控制与观察通道，尚未把NativePort整体实现完。还需要真实输入暂停及放行、共享世界完整核对、新规划状态/镜头证据，并把真实游戏配置与安装、正常菜单取消、加载后收尾接入。
目前仍面向固定测试档与单次会话。连续多旬复用、两个实际游戏客户端、两个人类势力规则、持续操作同步和正式事件处理仍需后续开发。
因此本轮消除了“控制器怎样和原生会话说话”这一缺口，没有把“真实联机循环已经完成”写成结论，也没有新的B加载耗时数据。

接下来的优先级

先把原生输入控制与加载终态观察接到这条通道和总控制器上，再安排一次真实B加载与地图恢复。真实游戏测试仍等你方便操作时集中进行，本轮不需要你读档、推进或演示菜单。
完整证据与源文件哈希见同名JSON。凭据没有写入结果文件；独立测试进程已结束。
'''
(OUT/'原生通信接入进展.txt').write_text(text,encoding='utf-8')
prefix='最新进展（本地通信，2026-10-07）：控制器到统一C++加载会话的实际命名管道已实现，客户端协议/取消测试与独立进程通信测试通过。本轮不访问游戏；完整NativePort、原生输入屏障、世界/地图观察和真实双客户端循环仍未完成。详见《原生通信接入进展.txt》。\n\n'
for name in ('开发剩余工作评估.txt','B端加载串联进展.txt'):
    p=OUT/name;old=p.read_text(encoding='utf-8')
    if not old.startswith(prefix):p.write_text(prefix+old,encoding='utf-8')
contract_path=HERE/'checkpoint_load_integration_contract.json'
contract=json.loads(contract_path.read_text(encoding='utf-8'))
contract['offline_integration']['local_session_control_channel_implemented']=True
contract['offline_integration']['actual_cross_process_session_control_verified']=True
contract['offline_integration']['live_native_port_implemented']=False
contract['latest_evidence_report']=str(OUT/'原生通信接入进展.json')
contract_path.write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'published':str(OUT/'原生通信接入进展.txt'),'unit':unit['tests_run'],
                  'cross_process':native['tests_run'],'sources_rehashed':True},ensure_ascii=False))
