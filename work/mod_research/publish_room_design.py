"""Update user-facing usage around the reviewed design and verified room layer."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'outputs'/'san14-link'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
unit=read(ROOT/'room-session-tests.json')
wire=read(OUT/'房间连接与选势力验证.json')
binding=read(OUT/'房间绑定与赏赐预检对接.json')
assert unit['result']==wire['result']==binding['result']=='PASS'
paths=[OUT/name for name in ['room_session.py','room_transport.py','run_room_selftest.py','房间势力目录.json',
                            '房间连接与选势力验证.json','房间绑定与赏赐预检对接.json','双人联机交互与同步设计.txt']]
report={'schema':'san14.room-design-milestone.v1','created':datetime.now().astimezone().isoformat(),
        'result':'ROOM_BINDING_VALIDATED_NATIVE_ADAPTER_PENDING','unit_tests':unit,'tls_exchange':wire,
        'reward_preflight_integration':binding,'no_game_writes_this_milestone':True,
        'implemented':['Pinned TLS loopback room connection','Two authenticated seats','Distinct faction selection and confirmation',
                       'Locked binding epoch','Idempotent room requests','Live-process resume without faction takeover',
                       'Shared identity source for command authority, candidate AI config and event ownership'],
        'not_implemented':['Playable create/join UI','LAN/two-computer validation','Native local viewer switching',
                           'Game checkpoint transfer and loaded-state barrier','Command capture and immediate peer game replication',
                           'Native ready/advance/event pause hooks','Battle synchronization','Host restart recovery'],
        'provenance':[{'path':str(p.relative_to(ROOT.parents[1])),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
(OUT/'房间设计与开发验证证据.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
usage=OUT/'预期用法与双人操作流程.txt'
backup=ROOT/'usage-before-room-revision-20261006.txt'
if not backup.exists():backup.write_bytes(usage.read_bytes())
usage.write_text('''三国志14联机：预期用法与现在能运行的入口
更新时间：2026-10-06

目标使用流程
1. 两人各开自己的游戏和联机助手，版本、适配器、规则配置须匹配。
2. A创建房间并选择共同开局/检查点，B使用地址和邀请加入。首版目标为局域网或已有虚拟局域网，公网中继尚未实现。
3. A、B选不同势力，双方确认后锁定归属。改选会取消此前确认；对局中不临时交换。
4. 两边载入同一起点，再各自恢复本机势力界面，完成状态/身份核对后进入规划。房间选中势力本身不等于游戏已经切换。
5. 各自在原生菜单操作，最终确认时自动发送命令，不用手填JSON或每次运行脚本。主机验权并执行一次，立即效果和任务创建及时回传两端。
6. 自己的命令都处理完后点准备。另一人可以继续操作，准备方自动接收更新。双方准备后封存输入、核对最终状态版本，再共同推进。
7. 战场过程同步；第5日属于A的阻塞事件使双方在该节点等待A，第7日属于B的事件同理，处理后同步继续。只对齐旬末不满足要求。
8. 掉线目标是停止继续推进并保留归属，重连核对后继续；主机崩溃恢复另需持久检查点与日志。

各自视角
A、B各看自己的势力菜单、武将、提案和事件，镜头、菜单浏览、排序与未提交草稿独立。改变世界的确认操作、战法/自动行为设置、事件答复和推进控制需要同步。具体分类、并发规则、准备封存与原生接入顺序见“双人联机交互与同步设计.txt”。

当前新增可运行入口
双击“运行房间选势力自测.cmd”：会自动启动一个本机TLS房间服务进程、创建A/B两条客户端连接，使用已保存的势力目录选择张鲁/刘备，检查越权、去重、掉线与重连，然后退出监听。结果为“房间连接与选势力验证.json”。
这不是让两人手动加入游戏的启动器，也不会读取或修改SAN14。当前机器具备Python和cryptography依赖，尚未打包为朋友电脑可直接安装的程序。
房间协议支持确认与固定绑定，但真实状态仍停在等待原生适配器。没有假装开局、没有更改游戏视角、没有同步第二份游戏。不要将目录复制给朋友就当作成品联机。

原有只读入口
“查看双人控制范围.cmd”：需游戏停在可下令大地图，显示双方主军团、委任军团和部队的候选AI保护范围，不实际关闭AI。
“查看双方命令权限.cmd”：分别查看张鲁、刘备的赏赐名单和预计消耗，不执行赏赐。
“检查赏赐命令.cmd”“读取当前游戏.cmd”“读取出征草稿.cmd”“读取内政草稿.cmd”仍为只读研究工具。
“运行联机模拟测试.cmd”和“运行旬内事件模拟.cmd”属于历史模拟世界验证，和本轮真实TLS房间连接测试的范围不同，也不会使真实游戏联机。

已经实测与仍缺的内容
已验证固定出征自动执行、受控赏赐、主机张鲁视角下为刘备执行一次网络赏赐及去重；双玩家AI候选分流通过隔离测试。
本轮新增26项房间规则测试、17项本机TLS连接检查，并将房间赋予B的势力身份接到现有赏赐预检；没有再次执行赏赐。
真正可玩的下一步是：原生双人控制/AI保护、各自身份恢复、B菜单确认后主机执行并把即时效果更新到A/B两份真实游戏，再推进战场过程和事件暂停。
这些关键环节通过前，不承诺完整内政、无感同步、确定性锁步或连续多旬稳定性。
''',encoding='utf-8')
roadmap=OUT/'双客户端实施路线.txt';text=roadmap.read_text(encoding='utf-8')
marker='最新主线进展：连接与势力绑定设计落地（2026-10-06）'
if marker not in text:
    text+='\n\n'+marker+'\n重新明确连接、势力选择、本机界面、即时/延时操作、准备封存和事件归属。新增房间协议与证书指纹固定的TLS传输，26项规则测试与17项真实本机交互检查通过。使用当前游戏只读采集的12个普通势力条目，A/B锁定张鲁/刘备；房间身份对接赏赐预检，越权拒绝，无实际游戏命令执行。\n房间状态保持WAITING_NATIVE_ADAPTER。AI名单、事件归属和命令权限共用绑定；真实身份切换、两游戏即时复制和战场同步仍待接入。详见“双人联机交互与同步设计.txt”和“房间设计与开发验证证据.json”。\n'
    roadmap.write_text(text,encoding='utf-8')
print(json.dumps({'result':'PUBLISHED','rule_tests':unit['tests_run'],'tls_checks':wire['check_count'],'native_game_started':False}))
