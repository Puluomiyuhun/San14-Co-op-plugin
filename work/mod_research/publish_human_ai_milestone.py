"""Publish tested candidate routing, with unimplemented live behavior explicit."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs' / 'san14-link'
load = lambda p: json.loads(p.read_text(encoding='utf-8'))
preview = load(OUT / '双人控制范围预览.json')
tests = load(ROOT / 'human-ai-fixture-results.json')
source = load(ROOT / 'human-ai-fixture-source.json')
closeout = load(ROOT / 'human-ai-closeout.json')
assert tests['result'] == closeout['result'] == 'PASS'
assert not preview['applied_to_game'] and not closeout['human_ai_policy_installed']
assert tests['live_preview_sha256'] == hashlib.sha256((OUT / '双人控制范围预览.json').read_bytes()).hexdigest()
contract = {
    'status': 'CANDIDATE_OFFLINE_VALIDATED_NOT_INSTALLED',
    'game_sha256': preview['game_sha256'],
    'wrappers': [
        {'route': 'force', 'entry_rva': '0xc6660', 'native_identity_call': '0x2110b0', 'body_rva': '0xa9160',
         'protect': 'force_id belongs to a verified human session'},
        {'route': 'district', 'entry_rva': '0xc65f0', 'native_identity_call': '0x20b580', 'body_rva': '0xa8e50',
         'protect': 'district_id is the native main district of a human force'},
        {'route': 'army', 'entry_rva': '0xc6580', 'native_identity_call': '0x209ab0', 'body_rva': '0xa8cf0',
         'protect': 'leader person +0x118 resolves to a human main district'},
        {'route': 'army_group', 'entry_rva': '0xc66a0', 'native_identity_call': '0x209c80', 'body_rva': '0xa9220',
         'protect': 'first native group member resolves to a human main district; live resolver still required'},
    ],
    'known_callers': ['0x3eb560', '0x3ebcb0'],
    'unit_wrapper_following_calls': ['0x3eba08 -> 0xc64c0', '0x3ec711 -> 0xc64c0'],
    'unit_queue_writes_outside_wrapper': ['0x3ebadc', '0x3ec7c5'],
    'shared_player_getters_to_leave_unchanged': ['0x2f21a0', '0x2f21e0', '0x2110b0'],
    'per_force_ai_map_to_leave_unchanged': 'CAIManager+0x60',
    'required_before_live_install': [
        'Revalidate executable and exact native bytes, planning boundary and original callbacks',
        'Resolve both authenticated human forces and their native ordered-list main districts',
        'Check actual viewer belongs to the session; never trust packet force claims',
        'Resolve and validate current subject identity/ownership on callback; invalidate mappings on load or ownership change',
        'Complete live group lookup, preserve context setup/cleanup and code outside the wrapper',
        'Implement reversible hook transport and native pause for HOLD; no silent lost work',
        'Refuse activation when world+16A8 bit8 is set until its mode is understood',
        'Test actual dispatch, AI choices, unit movement and battle during one controlled turn',
    ],
    'scope_limit': 'Four known direct wrapper routes, not complete AI-command coverage. No global player replacement. Outside-wrapper queue evidence is static, not a runtime movement guarantee.',
}
paths = [OUT / 'human_ai_policy.h', OUT / 'human_control_reader.py', OUT / '双人控制范围预览.json',
         ROOT / 'human_ai_fixture.cpp', ROOT / 'human_ai_fixture_code.h', ROOT / 'human-ai-fixture-source.json',
         ROOT / 'human-ai-fixture-results.json', ROOT / 'human-ai-closeout.json']
evidence = {'schema': 'san14.human-ai-routing-milestone.v1', 'created': datetime.now().astimezone().isoformat(),
            'status': contract['status'], 'contract': contract, 'tests': tests, 'native_sources': source,
            'live_read_only_preview': preview, 'closeout': closeout,
            'provenance': [{'path': str(p.relative_to(ROOT.parents[1])), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
(OUT / '双人势力AI控制验证证据.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
report = '''双人势力AI控制：原生分支与候选规则验证（2026-10-05）

本轮完成
已找到原生“玩家免于AI决策”的四个外层入口，并完成可供后续适配器使用的双玩家分流规则。隔离验证通过，当前存档的控制范围也已只读解析。规则尚未挂接到真实游戏，当前游戏AI行为没有改变。

为什么需要这一步
上轮已证明：主机仍显示张鲁，也能按网络请求为刘备执行赏赐。接下来必须防止游戏把刘备继续当作普通AI，自行产生与第二玩家冲突的命令。同时要保留玩家已下令部队的后续执行，以及用户主动委任军团的原有行为。

原生边界与候选设计
0xC6660：势力级入口。原生按当前玩家势力排除AI；候选规则按房间内两个人类势力排除。
0xC65F0：军团级入口。原生保护当前玩家主军团；候选规则同时保护双方主军团。
0xC6580：部队级入口。原生通过主将所属军团进行判断；候选规则用该归属匹配双方主军团。
0xC66A0：编组级入口。原生按首个有效枚举成员的军团判断；隔离测试中该归属由受控桩提供，真实编组读取仍需完成。
主军团由游戏原生军团名单顺序、君主和军团类型决定，不能简单假设“势力编号就是军团编号”。其他势力、委任军团继续进入原生路径。

这套规则只适用于上述外层AI入口。不会将所有地方调用的“是否当前玩家”都改成双玩家判断，否则菜单、可见信息、提案和事件归属可能一起改变。也不通过关闭按势力AI总开关来实现。
外层调用者在部队AI入口返回后，还会执行上下文清理和部队队列处理；候选方案保留这些代码。它们位于入口之外是静态证据，尚未证明挂接之后真实部队移动、攻击和动画一定正常，必须单独实测。

当前34号档的只读预览
张鲁：势力12，主军团11；4支主军团部队保持原有保护。另有委任军团9及6支部队，保留原生AI委任行为。
刘备：势力2，主军团2；新增保护4支部队：14关羽、15刘备、20关平、28轲比能。
名单包含18个军团所属势力条目、21个有效军团和56支现存部队。特殊势力51没有君主编号，但有原生主军团；预览保留其原生处理，不将其提升为玩家可选势力。
这里的“保护”均是候选规则的计算结果，游戏中尚未生效。编组没有纳入本次真实数据预览。

如何验证
将四个原生入口和六段访问/判断函数复制到独立测试进程，仅重定位其数据和调用依赖。实际AI函数体改为计数桩，主军团名单查询、人员有效性、编组归属和势力编号虚函数部分使用受控依赖；不打开游戏、不注入、不执行游戏AI。
816组原生分支检查通过，覆盖两种本机势力、相关模式位的两种状态及四类入口。
408组单玩家兼容检查通过，候选分流与原生行为相符。
408组双玩家分流检查通过，同时保护两个主军团并保留其他路径。
13项异常上下文检查通过，包括未知身份、越界、重复主军团、无效配置和未适配的模式位。
95个真实存档条目的语义编号复制到隔离进程，原生入口结果与只读预览相符，C++候选规则与预览结果相符。
合计1740项检查。这些是入口分流检查，不是1740场战斗测试，也没有验证完整AI命令覆盖率。

交付代码与查看方法
human_ai_policy.h：供后续原生适配器使用的纯决策函数，返回沿用原生、跳过人类决策、或暂停待处理三种结果。当前没有安装器。
human_control_reader.py：只读解析当前存档，输出上述控制范围和预期分流。
停在可下令的大地图后，可双击同目录“查看双人控制范围.cmd”，结果保存到“双人控制范围预览.json”。它不会关闭AI、切换玩家、推进日期或创建房间。

恢复与收尾
已检测到用户原生读回34号档。上轮赏赐造成的资源、忠诚和标志变化已恢复；571名武将、108条任务、56支部队及783条抽查记录通过恢复核对，仅允许经类型与回指验证的部队运行时指针重建。
全局随机值从赏赐前3900088880变为读档后3823646826，未改写；不能据此宣称完整隐藏状态恢复。该值在本轮收尾检查时保持3823646826。
10段原生代码指纹保持一致，原更新回调已还原，无调试器附加；AI总开关为1，按势力表为空，34号存档文件和备份哈希不变。本轮没有新增游戏写入或DLL注入。

下一步验收目标
先完成编组归属读取、可还原的外层入口挂接，以及身份不明时真正暂停推进的处理；随后用一次受控推进验证双方不会被AI改派新命令、已有部队仍正常移动和交战、委任军团继续工作。仅有分流函数返回“暂停”不等于游戏已经会暂停。
此后继续第二个真实客户端的独立菜单和即时状态回传。此次尚未实现第二游戏接入，也没有解决此前原A首批交战漏算，确定性锁步仍未验证通过。
'''
(OUT / '双人势力AI控制验证.txt').write_text(report, encoding='utf-8')
roadmap = OUT / '双客户端实施路线.txt'
text = roadmap.read_text(encoding='utf-8')
marker = '最新主线进展：双人AI控制边界与规则（2026-10-05）'
if marker not in text:
    text += ('\n\n' + marker + '\n'
             '确认四个外层AI入口按当前玩家势力/主军团排除；候选方案将范围扩展为两个会话势力及其各自主军团，保留委任军团。'
             '十段原生代码的隔离验证、双玩家候选规则及95个真实存档条目对照通过，共1740项入口分流检查。'
             '当前张鲁4支主军团部队已属原生排除范围，新增刘备4支；张鲁委任军团9的6支部队仍走原生AI。\n'
             '没有挂接实际AI入口，也未推进；编组真实读取、可还原挂接、真正暂停和正常移动/交战仍待验收。'
             '新增“查看双人控制范围.cmd”。34号档局面抽查已恢复，随机值3823646826与赏赐前不同，未改写；'
             '详见“双人势力AI控制验证.txt”及对应证据JSON。\n')
    roadmap.write_text(text, encoding='utf-8')
print(json.dumps({'result': 'PUBLISHED', 'status': contract['status'], 'checks': tests['total'], 'restored_sample': closeout['restored_sampled_records_unchanged']}))
