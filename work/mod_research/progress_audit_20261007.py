"""Workspace-only, evidence-based progress audit. Never imports game tools."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'outputs' / 'san14-link'
PREFIX = HERE / 'progress_audit_20261007'

def ref(name, scope='outputs', anchor=None):
    path = (OUT if scope == 'outputs' else HERE) / name
    raw = path.read_bytes()
    result = {'workspace_path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest()}
    if anchor:
        lines = raw.decode('utf-8-sig').splitlines()
        hits = [i+1 for i, line in enumerate(lines) if anchor in line]
        if not hits:
            raise AssertionError((name, anchor))
        result.update(anchor=anchor, line=hits[0])
    return result

sources = {
    'status': ref('开发剩余工作评估.txt'),
    'ipc_progress': ref('原生通信接入进展.txt'),
    'baseline': ref('完整联机逻辑与验收基线.txt'),
    'room': ref('room_session.py', anchor='class Room:'),
    'room_actions': ref('room_session.py', anchor="Unsupported action; no native game start or execution adapter installed"),
    'transport': ref('room_transport.py'),
    'checkpoint': ref('authoritative_sync.py', anchor='class PeriodCoordinator:'),
    'event': ref('authoritative_sync.py', anchor='def host_event('),
    'timeline': ref('timeline_protocol.py', anchor='Synthetic event-barrier protocol'),
    'execution_journal': ref('execution_journal.py'),
    'checkpoint_journal': ref('checkpoint_journal.py'),
    'transfer': ref('checkpoint_transfer.py', anchor='Production Room currently has no artifact endpoint'),
    'human_ai': ref('human_ai_policy.h'),
    'human_economy': ref('human_economy_policy.h'),
    'ai_evidence': ref('双人势力AI控制验证证据.json'),
    'economic_evidence': ref('经济规则适配证据.json'),
    'identity_live': ref('刘备开局接入测试说明.txt'),
    'reward_live': ref('第二势力命令接入实测.txt'),
    'sortie_live': ref('网络命令自动执行验证.json'),
    'export_live': ref('原生检查点导出进展.txt'),
    'load_live': ref('B端原生加载接入进展.txt'),
    'load_chain': ref('B端加载串联进展.txt'),
    'offline_progress': ref('离线开发进展与明早验证.json'),
    'guest_transition': ref('checkpoint_guest_transition.py', 'work', 'class NativePort(Protocol):'),
    'guest_admission': ref('checkpoint_guest_transition.py', 'work', 'def require_local_planning('),
    'guest_session': ref('checkpoint_guest_native_session.h', 'work', 'class Session {'),
    'guest_report': ref('checkpoint_guest_native_session.h', 'work', 'fullWorldVerified=false'),
    'session_ipc': ref('checkpoint_session_ipc.h', 'work', 'enum class Opcode:'),
    'visual_client': ref('checkpoint_visual_client.py', 'work'),
    'input_contract': ref('transition_input_gate_contract.py'),
}

modules = [
    {
        'id':'startup', 'name':'连接、选势力、共同开局', 'weight':12, 'completion_range':[55,70],
        'implemented':['两席位认证、TLS 固定证书、独占势力/军团绑定、重连保留席位', '加载身份配对核心及统一 Session 的离线串联'],
        'real_game_evidence':['同一份34号档在一个真实游戏中换成刘备，用户确认君主和基本菜单'],
        'not_real_game_evidence':['Room 本身没有 start-game 入口', '新统一 Session 与命名管道使用合成游戏对象，未安装真实加载器'],
        'gaps':['绑定房间势力到真实版本/进程配置与加载实例', '真实共同起点覆盖、B首次自动加载与两个客户端同时可操作', '固定张鲁/刘备以外的选择范围必须如实限制'],
        'milestone_acceptance':'A/B 固定受支持势力，经房间握手和同档恢复进入各自原生菜单，完整业务起点与控制权通过核对。',
        'evidence':['room','room_actions','transport','identity_live','guest_session','session_ipc'],
    },
    {
        'id':'commands', 'name':'持续命令捕获与即时同步', 'weight':18, 'completion_range':[25,40],
        'implemented':['赏赐/出征语义预检、受控原生执行工具', '授权、全局顺序和持久执行意图/回执的组件', '两独立原生夹具的归一化样本一致性'],
        'real_game_evidence':['固定赏赐请求通过本机网络在真实A游戏为刘备执行一次，重复和越权拒绝', '受控出征命令曾实际执行后恢复'],
        'not_real_game_evidence':['持续正常菜单捕获、B应用与刷新不在已通过实测范围', '原房间 route_preview 只返回路由，不执行命令'],
        'gaps':['在本地原生执行前捕获/拦截，避免先扣款再重复广播', 'A排队裁决与A/B各执行一次、回环抑制、过期对象生命期', '白名单之外的所有改变业务输入必须实际拦截', '赏赐/出征真实双端连续回执和UI刷新'],
        'milestone_acceptance':'两个真实客户端从各自菜单反复完成赏赐/出征，A裁定一次且双方即时收敛；未适配命令不能偷跑。',
        'evidence':['reward_live','sortie_live','execution_journal','room_actions'],
    },
    {
        'id':'human_rules', 'name':'两个人类势力AI和经济规则', 'weight':12, 'completion_range':[30,45],
        'implemented':['4条原生AI外层路线的候选分流、主军团/委任区别', '两个经济调用的双人类集合候选规则', '9城、80区域经济预览的完整原生代码离线复算'],
        'real_game_evidence':['真实档只读归属样本', '换身份前后的9城差异样本为离线解释提供实机依据'],
        'not_real_game_evidence':['头文件是纯策略，不安装钩子', '离线预览一致不证明真实旬内全部结算一致'],
        'gaps':['持续安装与房间规则绑定', 'A不替B做新AI决定且B已有部队继续行军战斗', '委任、编组及模式位不被误伤', '真实收入/支出/提案等共享规则覆盖'],
        'milestone_acceptance':'连续多旬两个人类势力没有额外AI决策，本机视角不改变共享业务规则，其他AI和委任继续工作。',
        'evidence':['human_ai','human_economy','ai_evidence','economic_evidence'],
    },
    {
        'id':'ready_events', 'name':'准备封存、推进和正式事件', 'weight':12, 'completion_range':[20,35],
        'implemented':['双方准备、命令前缀/世界相等、单次推进许可的协议', 'A事件生成/归属答复/应用屏障', '5日/7日招募等独立演示协议'],
        'real_game_evidence':[],
        'not_real_game_evidence':['timeline_protocol 的任务时间和结果是合成定义', '协议 phase 变化不能实际暂停游戏'],
        'gaps':['原生准备/推进按钮和既有命令提交入口的真实控制', 'A生成B正式事件并等待正确答复', 'B投机弹窗的压制/转交及业务副作用识别', '未支持强制事件的明确中止/恢复流程'],
        'milestone_acceptance':'正式事件只在A按日期产生并一次应用，正确玩家答复，另一方真实等待；准备后不能通过原生输入绕开封存。',
        'evidence':['checkpoint','event','timeline','baseline'],
    },
    {
        'id':'period_checkpoint', 'name':'旬末全量导出、传输、B恢复', 'weight':24, 'completion_range':[45,60],
        'implemented':['原生专用导出、专用文件读取/发布组件', '限窗TLS分块校验、持久B检查点日志', '真实读取字节/生命周期/B身份同链Session与实际本机管道', '总控制器保留未知结果，不自动重复加载'],
        'real_game_evidence':['新A保存实测返回同一规划层约1.219秒，保存274880字节', '原生专用文件完整读取和发布后读回实测通过', '旧34号自动重载中段证据不完整，只能记录事后返回观察'],
        'not_real_game_evidence':['统一加载Session、文件核验和身份链是独立进程合成游戏对象', '未有新专用检查点完整B自动加载+完整世界核对', '1.219秒仅为A保存，不是B加载/全流程'],
        'gaps':['完整NativePort真实接入、正常取消/完成清理', '完整业务覆盖合同与实际世界摘要/必要sidecar', '每旬重复恢复不额外结算、提案或事件', '专用文件动态轮换和连续多旬Session生命期', '两个真实客户端无新增命令跨一旬再接下一旬'],
        'milestone_acceptance':'B全部共享世界按A替换（含对象增删与场外），身份仍为B，实际摘要一致且A未前进，连续至少多旬重新开放规划。',
        'evidence':['export_live','load_live','load_chain','checkpoint','checkpoint_journal','transfer','guest_session','session_ipc','guest_transition'],
    },
    {
        'id':'presentation_input', 'name':'旧图等待、输入屏障和新地图呈现', 'weight':8, 'completion_range':[35,50],
        'implemented':['独立Windows画面助手、旧图保留与新帧时间校验', '持续客户端/进程绑定/失败保持', '总控制器等画面与原生输入放行双确认才准接单', '中性输入与排空协议'],
        'real_game_evidence':[],
        'not_real_game_evidence':['自有双进程真实窗口测试不等于SAN14画面', '像素与身份记录不等于新规划地图/可操作证据'],
        'gaps':['真实游戏全生命周期输入屏障且不阻断加载所需更新', '真实窗口捕获/遮罩/镜头恢复', '新规划状态与帧属于同一加载实例的原生观察', 'LIVE后失联立即重新阻止原生输入'],
        'milestone_acceptance':'窗口/无边框模式下旧地图等待→B新地图，遮罩期不能操作后台，撤罩后物理输入排空并在确认后开放。',
        'evidence':['visual_client','guest_transition','guest_admission','guest_report','input_contract'],
    },
    {
        'id':'recovery', 'name':'断线、未知结果与多旬恢复', 'weight':8, 'completion_range':[30,45],
        'implemented':['命令执行与B检查点持久日志', '加载一次性意图、丢回执保留观察、管道重连查询', '旧epoch/attachment和冲突重复消息拒绝'],
        'real_game_evidence':['固定命令重复请求在单个真实游戏中无追加效果'],
        'not_real_game_evidence':['助手/管道重连不等于主机房间重启恢复', 'SQLite与游戏内存不是原子事务，未知效果保持暂停'],
        'gaps':['整场房间/检查点/命令基线重新绑定', '全房间与主机重启后的共同恢复', '加载中断、游戏崩溃和网络异常的真实恢复演练', '完成后持续健康监测与新一旬状态机复用'],
        'milestone_acceptance':'慢端/断线/丢回执/加载中断不产生重复效果或错误继续；可明确恢复到共同检查点。主机迁移可不做。',
        'evidence':['execution_journal','checkpoint_journal','session_ipc','checkpoint','guest_transition'],
    },
    {
        'id':'delivery', 'name':'助手、安装与受限试玩交付', 'weight':6, 'completion_range':[10,25],
        'implemented':['研究脚本/编译核心、使用设计和版本指纹', '房间选势力与合成演示入口'],
        'real_game_evidence':[],
        'not_real_game_evidence':['核心可编译不等于朋友可安装使用', '当前没有生产房间到完整适配器的启动入口'],
        'gaps':['真实启动/安装/退出生命周期、助手UI', '双方连接、版本/模式/势力限制与错误提示', '公网或既定组网方式联调', '最小安装包与双人测试步骤、恢复说明'],
        'milestone_acceptance':'两位玩家按一份步骤安装/连接，在明确受支持范围内完成连续多旬，出错有可理解的恢复入口。',
        'evidence':['status','room_actions','ipc_progress'],
    },
]
assert sum(m['weight'] for m in modules) == 100
for module in modules:
    module['estimate_low'], module['estimate_high'] = module['completion_range']
    module['implemented_evidence'] = [sources[key]['workspace_path'] for key in module['evidence']]
    module['remaining'] = module['gaps']
    module['real_two_client_acceptance'] = False
overall = [int(round(sum(m['weight'] * m['completion_range'][side] for m in modules) / 100 / 5) * 5)
           for side in (0, 1)]

issues = [
    {'id':'I1', 'severity':'blocking_integration_gap', 'title':'房间选择完成尚不通向实际游戏或命令执行',
     'evidence':['room_actions','transfer'],
     'detail':'Room.handle仅有选势力、确认和route_preview，transfer明确无生产artifact endpoint。协议/网络单项通过不能计为玩家连接后已能玩。',
     'resolution':'将统一验收/真实适配能力接到房间开始和命令/检查点端点；就绪前保持当前拒绝行为。'},
    {'id':'I2', 'severity':'blocking_scope_mismatch', 'title':'任意势力目录与固定单次加载配置尚不匹配',
     'evidence':['room','guest_session','ipc_progress'],
     'detail':'目录允许多个正常势力选择，而Session仍绑定固定档案与身份且单次使用。不能对用户开放尚未映射到受验证原生配置的选择或连续重载。',
     'resolution':'首个原型明确限制固定双方/固定场景；或补齐通用配置、动态文件与多旬实例编排后扩大范围。'},
    {'id':'I3', 'severity':'blocking_native_coverage', 'title':'文件SHA和B身份成功不能满足完整世界放行条件',
     'evidence':['guest_report','guest_transition','checkpoint','economic_evidence'],
     'detail':'生产Session能力仍fullWorldVerified=false，NativePort却必须提供真正完整覆盖后才能完成；现有抽样和文件哈希无法给这一条件提供真实证据。经济适配未安装时，B身份初始化本身已有业务派生差异的历史实证。',
     'resolution':'定义并实现语义覆盖/sidecar/派生状态规则，区分读取字节、身份和世界三个不同证据；不得靠把布尔字段置真完成接入。'},
    {'id':'I4', 'severity':'blocking_scope_mismatch', 'title':'命令白名单不能排除推演中自然发生的强制事件',
     'evidence':['baseline','event','timeline'],
     'detail':'只开放赏赐/出征仍可能推进既存任务、历史事件、灭亡、俘虏等需要处理的状态。遭遇即暂停可作为探索原型，但不能同时宣称普遍可连续多旬。',
     'resolution':'受限剧本需列明可运行边界；最低正式事件路由/无副作用提示分类必须接通，未知事件明确终止/恢复而不是默认点确定。'},
    {'id':'I5', 'severity':'blocking_native_input_gap', 'title':'同意联机命令不等于已阻止本地菜单偷偷执行',
     'evidence':['reward_live','guest_transition','input_contract','room_actions'],
     'detail':'赏赐受控调用有效，但通常玩家先在菜单确认的本地副作用如何截获尚未接通；必须先拦截再交A裁定，或实现有证据的来源执行规则。否则发送方会先执行后重复，或拒绝请求仍留下本地改变。',
     'resolution':'白名单捕获与所有非白名单业务输入的原生阻止要一起验收；高层按钮/网络拒绝不是替代。'},
    {'id':'I6', 'severity':'documentation_drift', 'title':'历史报告与最新主线的口径不一致',
     'evidence':['baseline','reward_live','status'],
     'detail':'旧第二势力实测尾部仍称不能以旬末覆盖替代过程一致性，最新基线已允许；总评估夹有多轮旧缺口。旧事实可以保留，但进度应使用明确当前摘要和历史段落，不能抽到旧句子就认为新主线反转。',
     'resolution':'当前交付说明集中引用最新能力清单，并将旧段标成历史；不改写原始失败证据。'},
]

report = {
    'schema':'san14.progress-audit.v1',
    'updated_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
    'audit_mode':'offline workspace files only; no executable imports or tests run',
    'game_process_access':False, 'steam_directory_access':False, 'real_window_access':False,
    'scope':'Fixed supported scenario/version and two forces; native own-force menus; reward/sortie whitelist; A authority, B speculative battle, full period replacement; minimum mandatory-event handling; window/borderless presentation; no host migration or strict battle lockstep.',
    'scope_limits':['Full domestic/talent/diplomacy command catalog is excluded from this MVP estimate.', 'Zero-stall reload, arbitrary scenarios/forces and a polished public installer are not baseline promises.', 'The first test may be exploratory and blocked by unsupported events; that is not the final playable MVP.'],
    'estimate_method':'Subjective work-completion ranges by integration deliverable, weighted to 100. No conversion of test counts/file counts to progress. Does not predict elapsed days, success probability or current playability. Native unknowns can expand scope.',
    'modules':modules,
    'milestone_weight_total':100,
    'weighted_completion_rounded_to_5pct':overall,
    'overall_range':overall,
    'estimate_confidence':'low-to-moderate until actual B full restore and two-client roundtrip',
    'playable_mvp_available':False,
    'release_gates':{
        'actual_full_guest_restore_and_full_world_verification':False,
        'two_human_rules_live_and_native_input_capture':False,
        'two_real_clients_reward_sortie_next_period_loop':False,
        'mandatory_native_event_owner_and_barrier':False,
        'continuous_multi_period_and_failure_recovery':False,
    },
    'mvp_definition':{
        'game_scope':'Fixed verified game version, scenario/checkpoint and two supported factions; all remaining factions AI.',
        'player_experience':'Two real clients, each own native menus/camera; extra assistant window; initial window/borderless mode only.',
        'commands':'Reward and sortie whitelist captured before native effects; other world mutations are actually blocked.',
        'authority':'A orders commands and owns formal outcomes/events; B may have speculative battle differences.',
        'periods':'A full authoritative world replaces B at each period end, with B identity, actual complete-world verification and continued next-period planning.',
        'events':'Minimum required native event ownership and pause/answer handling includes naturally triggered events and preexisting tasks, even if new recruitment/diplomacy commands are disabled.',
        'faults':'Detect divergence, disconnect and uncertain effects; keep physical input/advance held and provide explicit common-checkpoint recovery.',
        'excluded':['strict battle lockstep','host migration','all command types','arbitrary scenarios/factions','zero loading pause','polished public release'],
    },
    'release_blockers':[
        'No actual complete B automatic restore with B identity and full semantic-world verification yet.',
        'No native continuous input/command interception, two-human AI/economy installation or common rule settlement proof yet.',
        'No two-real-client reward/sortie -> ready -> battle -> authoritative period replacement -> next-period loop yet.',
        'Mandatory event routing includes natural events/preexisting tasks; command whitelist alone cannot remove this hard gate.',
        'No real multiple-period repetition and explicit interrupted-load/disconnection recovery yet.',
    ],
    'issues':issues,
    'recommended_sequence':['Complete the real B restore/semantic-world/input/presentation contract.', 'Install two-human rules before any two-client continuous advancement.', 'Prove no-new-command one-period and next-period loop.', 'Join reward/sortie native capture and A order/results; suppress all unsupported mutations.', 'Add mandatory event ownership and failure recovery, then broaden commands and distribution.'],
    'evidence_sources':sources,
    'concurrency_note':'This report freezes evidence hashes read by this agent; concurrent new Session/visual/controller work is excluded until its own results are published. No shared source or output file modified.',
}
PREFIX.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

lines = [
    '受限双人可玩原型：独立进度审计',
    '更新：'+report['updated_at'],
    '',
    '审计范围：只读工作区现有源码和证据。未访问真实游戏进程、窗口、Steam目录；未运行现有测试或导入可能访问游戏的模块。并行开发正在进行，本报告以列明的文件哈希为界，不替未完成新改动背书。',
    '',
    '总体判断',
    '按固定版本/剧本、固定两势力、赏赐+出征白名单的MVP工作包估算，约35%—50%的实现与接入工作已有成果。这个区间不是精确统计，不是可玩率，更不是剩余天数。即使某模块组件完成较多，任何强制放行关卡未通过都不能发成可玩MOD。当前真实双人可玩MVP仍未达到。',
    '本轮最大增量是统一C++加载Session、真实本地命名管道、持久画面助手和总控制器的独立链路。真实A导出已通过；新的完整B自动恢复+完整世界核对尚未通过。两者不能合并成“端到端加载成功”。',
    '不把测试条数、源码行数、脚本数或静态callsite数折算为完成率。下面的权重总和100，表示MVP工作包和验收贡献，允许按新证据调整。完整内政/人才/外交支持、严格战斗锁步、任意剧本和无停顿体验不在这个区间内。',
    '',
]
for m in modules:
    lines += [f"{m['name']}：权重{m['weight']}；工作完成粗估{m['completion_range'][0]}%—{m['completion_range'][1]}%",
              '已实现：'+'；'.join(m['implemented']),
              '实机证据：'+('；'.join(m['real_game_evidence']) if m['real_game_evidence'] else '暂无该模块端到端实机验收'),
              '证据边界：'+'；'.join(m['not_real_game_evidence']),
              '缺口：'+'；'.join(m['gaps']),
              '验收里程碑：'+m['milestone_acceptance'], '']
lines += ['具体矛盾/边界问题（多数为未接通合同，当前代码选择拒绝，未发现已放行的真实游戏漏洞）','']
for i in issues:
    lines += [i['id']+' '+i['title'], i['detail'], '建议：'+i['resolution'], '']
lines += ['不能跳过的上线门槛',
          '1. B真实加载专用检查点、恢复自己身份，完整语义世界核对通过。',
          '2. 两个人类势力规则真实安装，日常菜单业务输入在原生执行前受控。',
          '3. 两个真实客户端完成命令→准备→推演→全量校正→下一旬。',
          '4. 必须面对的事件按所有者处理、停止和继续不会重复生效。',
          '5. 连续多旬与明确故障恢复能运行，不依赖每旬人工替工具清场。',
          '',
          '建议先后：完整B恢复/输入/世界/呈现→双人规则→真实无命令跨旬→赏赐/出征持续闭环→事件与恢复→扩大命令和打包。',
          '这些不是五个小修补。尤其完整状态覆盖、真实输入拦截与正式事件仍可能暴露新的原生规则路径，故暂不估天数。',
          '',
          '证据文件和精确哈希见同名JSON。该报告未修改任何outputs或正在并行开发的源文件。']
PREFIX.with_suffix('.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(json.dumps({'weight_total':100,'rough_completion':overall, 'playable':False, 'modules':len(modules),'issues':len(issues),'sources':len(sources)},ensure_ascii=False))
