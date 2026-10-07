"""Publish the fixed-viewer design correction and bounded feasibility evidence."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'outputs'/'san14-link'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
r=load(ROOT/'identity-pair-results.json')
assert len(r['pairs'])==8 and r['isolated_fixture_processes']==16
assert len(r['source']['blocks'])==40 and r['game_memory_writes']==0
assert all(p['normalized_sample_equal'] for p in r['pairs'] if p['mode']=='normal')
assert all(p['different_offsets']==[0x165D] for p in r['pairs'] if p['mode']=='native_init')
closeout=load(ROOT/'human-ai-closeout.json')
assert closeout['result']=='PASS' and closeout['checkpoint34_unchanged'] and closeout['known_rng_equal_to_recent_restore']
report='''固定本机势力＋远程命令：可行性验证
更新：2026-10-06

设计收敛
采用用户提出的模型：A客户端一直以A势力为本机玩家，B客户端一直以B势力为本机玩家。两边各自使用原生菜单、镜头和查看界面。对方的操作以带明确势力归属的命令或权威效果进入本机世界。
“建立本机身份”发生在开局、读档或恢复时。正常收到一条远程命令时，不把A切成B再切回来，也不要求双方共用同一势力菜单。
主机仍负责共同命令顺序、授权、去重、事件和时间线。A可同时担任主机，B使用同一规则提交。
命令广播包含双方已经确认的输入；每端按执行记录处理一次。发送方已经执行的同一命令不能因为收到回执再扣钱。早期原型应在原生提交前截获，确认后再落地，避免不可逆的本地先行执行。
对于已证明跨本机身份结果一致的命令，可验证在双方分别执行同一语义命令；对未证明一致的命令，不能默认采用此方式。主机结果/过程复制与确定性锁步仍须按实际证据选择。

本轮做了什么
只读采集当前34号档的数据，建立两份独立进程的对象副本，分别固定张鲁12和刘备2。将40段原生代码及明确的查询依赖重定位到测试进程，实际执行其中的身份查询、初始化、赏赐和部分分支代码。
共8组成对场景、16个独立测试进程。它们不是两份SAN14游戏，不包含渲染、完整菜单或战场推演。真实游戏本轮没有执行赏赐、切换势力或推进日期。

通过的部分
1. 原生玩家/主军团查询：A副本返回张鲁、主军团11；B副本返回刘备、主军团2。自身势力判断相反且正确。这支持各自原生菜单采用各自身份，但不等于菜单的创建、缓存和刷新都已验证。
2. 当前普通模式下，B赏赐、A赏赐、A后B、B后A、B重复两次，五组成对运行均保持本机身份。扣钱、行动、忠诚、标志以及本次完整复制的采样对象结果一致。
3. 单次B赏赐：庐江金20804→20504，刘备主军团行动10→9；郭女王93→97、公孙康91→95、小乔99→100。A/B副本结果相同，张鲁本方金和行动不变。该结果也与先前真实张鲁客户端替刘备执行的实测数值相符。
4. 重复B命令会在原生函数内再次扣钱，证明插件必须在入口去重，不能指望游戏原生函数识别网络重复包。重复只在隔离副本执行。

原生身份初始化的新增证据
离线查到0x2FC850：从指定人物经军团获取势力，写world+0x3A；随后根据该势力的CRankData更新world+0x165D。已确认的一处直接调用来自0x4DA390，它通过CTitleState取得人物对象；这为开局身份设置提供候选入口，尚未验证任意大地图时刻调用它能正确刷新菜单。
在当前world+0x40=1的复制环境里，用张鲁666和刘备952分别调用这段原生入口。A世界字段保持原值；B改变两处字节：玩家12→2、由官爵数据派生的配置2→1。之后原生主军团查询正确，双方运行同一赏赐的资源/忠诚效果仍一致。
这两组保留了world+0x165D的差异，没有把它偷偷从完整采样比较中删掉。其读取路径0x3F72C0会据此将世界数组复制到CUserStrategyState；所有读取者和业务意义尚未穷尽，不能直接宣布它属于可任意忽略的纯显示数据。
另一种初始化模式world+0x40=4涉及额外上下文函数，本轮未适配，隔离测试会拒绝走该分支。

不能直接放行全量联机的原因
普通赏赐效果一致，不代表每段原生逻辑都无视本机玩家。
反例一：仅在复制环境将world+0xBC改成0，原生赏赐的附带路径会让world+0x80计数只在所属玩家副本增加。当前真实测试档该模式为-1，未触发此分支；不猜测该计数在界面中的业务名称。
反例二：0x43F160特殊交战过滤被调用时，同一个受控关隘目标会因攻击方是不是本机玩家而给出不同返回值。部队目标的控制例两边均通过。是否进入这个特殊过滤还取决于外层条件，不能把隔离反例说成当前实际战斗已经分叉，更不是最早异常A轮的根因。
已知提案生成也会读取本机势力并使用业务随机。因此后续要分别验证即时命令、玩家业务数据和连续推演，不能只同步命令与随机种子就宣布完成。

隔离测试的限制
命令容器由测试程序按已验证的布局重建，没有测试真实菜单最终确认的捕获。
资金上限路径的0x3CB260政策效果查询使用显式返回0的测试替身。其返回值在该调用处只参与第四个上限输出，不参与资金上限；资金上限、本次扣金、忠诚和行动写入使用原生代码。该查询原本的内部副作用没有被完整复现，不据此证明整个原生调用链全部无副作用。
未支持的部落城市分支和身份初始化模式4会触发隔离测试的失败路径，不伪造结果。
比较的是本次复制对象和字段，非完整世界。跨进程本地虚表地址已归一化；正常成对比较只额外忽略本机玩家编号，故能实际检出world+0x80和world+0x165D差异。
真实游戏前后783条已有记录、采样任务、已知随机及池计数一致；34号存档和原策略更新入口未改。无需用户重新读档。

下一阶段验收顺序
第一关：在真实游戏原生进入/重建策略界面的合适阶段建立B身份，验证默认菜单、可选武将和主军团都对应B，并验证读档恢复。不是只把玩家字节改成B就通过。
第二关：两份真实游戏各保持A/B身份，正常菜单确认一条赏赐，按主机顺序执行一次，两边结果与界面一致；未支持命令在原生执行前阻止。
第三关：两位人类势力的AI保护、共同推进和一场交战/事件的过程一致性。通过后再批量扩展内政、军事与多旬恢复。
本轮结论是“固定本机身份的方向得到有限原生代码证据支持”，不是完整联机已可玩。继续采用这一模型，不批量铺开尚未验证的命令类别。
'''
report_path=OUT/'固定本机势力与远程命令可行性验证.txt'
report_path.write_text(report,encoding='utf-8')
paths=[ROOT/'make_identity_pair_fixture.py',ROOT/'identity_pair_fixture.cpp',ROOT/'identity_pair_fixture_code.h',
       ROOT/'identity_pair_fixture.exe',ROOT/'validate_identity_pair_fixture.py',
       ROOT/'full-2fc850.txt',ROOT/'full-4da390.txt',ROOT/'full-2bbbc0.txt',report_path]
r['closeout']=closeout
r['scope']='Independent native-code fixtures from one captured game, with fixed local viewers. Five normal command pairs agree; one controlled context case exposes world+80 and two native-initializer cases expose world+165D. One policy query has an explicit boundary stub that affects only the fourth capacity output; its original internal side effects are not reproduced. No actual SAN14 menu creation, command execution or multiplayer simulation this turn.'
r['design']='Fixed local player per client; actor-bound ordered remote commands. Re-establish local identity only at session/load/recovery boundaries.'
r['provenance']=[{'path':str(p.relative_to(ROOT.parents[1])),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
(OUT/'固定本机势力与远程命令验证证据.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'report':str(report_path),'paired_scenarios':len(r['pairs']),'native_blocks':len(r['source']['blocks']),
                  'actual_game_command_calls':r['game_native_command_calls']},ensure_ascii=True))
