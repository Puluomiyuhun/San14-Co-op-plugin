"""Publish preparation/arming status, never a fabricated successful B start."""
from datetime import datetime
from pathlib import Path
from start_startup_switch import ROOT,load,save,sha
OUT=ROOT.parents[1]/'outputs'/'san14-link'
fixture=load(ROOT/'startup-switch-fixture-tests.json')
infra=load(ROOT/'startup-switch-lifecycle-tests.json')
parser=load(ROOT/'startup-switch-analysis-tests.json')
idle=load(ROOT/'startup-switch-idle-check.json')
binary=ROOT/'startup_identity_switch.exe'
assert fixture['result']==parser['result']==idle['result']=='PASS'
assert fixture['binary_sha256']==idle['binary_sha256']==sha(binary)
active=load(ROOT/'startup-switch-active.json') if (ROOT/'startup-switch-active.json').exists() else None
baseline=load(ROOT/'startup-load-boundary-baseline.json')
baseline_tests=load(ROOT/'load-boundary-baseline-tests.json')
assert baseline_tests['result']=='PASS' and not baseline['new_excluded_fields']
assert len(fixture['cases'])==18
assert active is None or active['binary_sha256']==sha(binary),'Active run belongs to an older binary'
report={'schema':'san14.startup-switch-preparation.v1','created':datetime.now().astimezone().isoformat(),
        'result':active['result'] if active else 'PREPARED_NOT_ARMED',
        'purpose':'Load the unchanged shared checkpoint and hand the native initialization a Liu Bei local selection.',
        'isolated_tests':fixture,'lifecycle_tests':infra,'trace_analysis_tests':parser,
        'real_idle_check':idle,'active_run':active,'profile':load(ROOT/'startup-switch-profile.json'),
        'load_boundary_baseline':{**{k:v for k,v in baseline.items() if k!='records'},
                                 'record_count':len(baseline['records']),'sha256':sha(ROOT/'startup-load-boundary-baseline.json')},
        'load_boundary_baseline_tests':baseline_tests,
        'real_identity_switch_success_not_yet_verified':True,'b_visual_menu_verified':False,
        'two_client_multiplayer_verified':False,'native_gameplay_enabled':False,
        'sources_sha256':{p.name:sha(p) for p in (binary,ROOT/'startup_identity_switch.inc',ROOT/'startup_switch_profile.h',
             ROOT/'start_startup_switch.py',ROOT/'analyze_startup_switch.py',ROOT/'startup_switch_fixture.cpp',
             ROOT/'prepare_load_boundary_baseline.py',ROOT/'test_load_boundary_baseline.py')}}
rejection_path=ROOT/'startup-switch-rejection-latest.json'
if rejection_path.exists():
    report['first_live_attempt']=load(rejection_path)
live_path=ROOT/'startup-switch-live-result.json'
live=load(live_path) if live_path.exists() else None
if live and active and live['directory']==active['directory']:
    report['result']=live['result']
    report['real_identity_switch_success_not_yet_verified']=False
    report['real_native_identity_switch_verified']=True
    report['real_load_result']=live
    report['user_ruler_observation']=load(Path(live['directory'])/'user-ruler-observation.json')
    report['city_identity_effects']=load(ROOT/'city-identity-effects-audit.json')
    report['scope']='One real Liu Bei entry from the unchanged Zhang Lu checkpoint. Menu permissions still pending; identity-dependent economic fields require adaptation.'
    menu_path=Path(live['directory'])/'user-menu-observation.json'
    if menu_path.exists():
        report['basic_menu_check']=load(menu_path)
        report['b_basic_menu_checks_user_reported_ok']=True
        report['scope']='One real Liu Bei entry and user-reported basic menu checks. All menus/events remain unaudited; economic fields require adaptation.'
    recovery_path=Path(live['directory'])/'recovery.json'
    if recovery_path.exists():
        report['recovery']=load(recovery_path)
        report['current_state']='RESTORED_ZHANG_LU_CHECKPOINT_SAMPLE'
save(OUT/'刘备开局接入测试证据.json',report)
text='''刘备开局接入：本轮测试说明
更新：2026-10-06

本轮要验证什么
读取原来的34号张鲁存档，在原生程序建立策略和菜单之前，把启动选择交给刘备。世界中的城市、武将和部队继续来自同一份存档；本机操作身份预期变为刘备。
这轮只使用当前一个游戏进程检验B端的进入方式。还未接入第二台电脑、全命令同步或双人推演。

具体实现
在原生读取CTitleState选中君主之前，核对版本、载入成功顺序、启动状态、原君主、目标势力/君主关系，以及783条既有数据样本。
核对通过后，仅一次修改启动选择中的势力和君主两个对象引用，共16字节。随后的读取参数、身份初始化、官爵派生字段更新和界面建立由原生程序继续完成。
没有直接修改世界玩家编号，没有改写游戏代码，没有另开线程调用原生身份函数；观察工具会正常退出。
抽样核对只排除已知部队显示对象指针，不能充当完整世界一致性证明。

首轮未切换的原因与修正
首轮在任何身份写入之前被样本检查拦截，因此仍显示张鲁。只读补充记录证明：原基准来自大地图初始化之后，实际检查点却在初始化之前，二者有107条城市/部队记录、916个字节不同；进入大地图后这些字节全部回到原基准值。
现已用实际捕获的同一加载阶段数据重建检查基准，保留原有字段核对，不新增忽略字段。新增检查也验证了把大地图阶段的值放回加载基准会被拒绝。这只解决本次误拦截，尚不代表真实刘备身份或菜单通过。

已经通过的检查
18项隔离检查，包括合法写入、只读演练、错误日期/君主/军团/阶段/代码/存档样本、只读内存和重复执行拒绝。两个隔离案例实际运行了复制的原生身份初始化函数，结果为刘备势力2、官爵派生字段1。
12项加载阶段基准重建检查，覆盖记录不全、错误阶段、非法偏移、重复对象和未恢复的字段等情况。
3项真实独立进程的记录、超时、取消退出检查。
22项合成日志分析检查及2项已保存样本比较检查。
当前真实游戏的2秒只读待机挂接与退出检查；游戏数据样本及34号文件未改。
这些准备检查不代表真实刘备菜单已经通过。

用户操作
在告知测试已开启后，读取34号存档。进入大地图后，告诉我画面显示的君主。
本轮停在大地图，不下令、不推进日期、不再次读档，便于保存切换后的证据。
若仍显示张鲁或出现提示，直接描述即可。工具检查不通过时可能已退出，此时不要反复读档尝试触发。
核对完成后，再通过游戏正常读取34号档恢复张鲁。原存档文件不会被本工具覆盖。

执行约束
真正写入前会保存一次性尝试记录，已保留执行意图的情况不自动重试。超时但未触发写入的情况，可以先核对日志和当前状态，再重新开启。
目前没有安装双人AI决策保护，因此本测试不推进日期。进入刘备界面后仍需验证城市/武将可操作性和事件归属，之后才能接共同开局就绪流程。
'''
if active and not active['execute']:
    start=text.index('\n用户操作\n');end=text.index('\n执行约束\n',start)
    text=text[:start]+'''
首轮结果与本次补充
首轮已到达正确身份入口，日期、原君主、目标势力/君主、载入阶段检查通过，但783条样本的比较未通过。工具在任何写入和执行意图记录之前退出；当前仍是张鲁，存档未改。
进入大地图后的抽样业务状态与基准一致，加载边界的具体差异尚未确定。原日志只记录了不匹配，未记录字段；现已补充全部差异明细，包含对象、字段、预期值和实际值。
当前开启的是只读补充记录，不做刘备切换，也不放宽原检查。

用户操作
在告知只读记录已开启后，再读取34号存档。进入大地图后停住，不下令、不推进日期、不再次读档，回复“差异记录完成”。君主继续显示张鲁是本轮预期。
''' +text[end:]
(OUT/'刘备开局接入测试说明.txt').write_text(text,encoding='utf-8')
if live and active and live['directory']==active['directory']:
    start=text.index('\n用户操作\n');end=text.index('\n执行约束\n',start)
    text=text[:start]+'''
本次真实结果
这一次实际载入已成功：同一份34号张鲁存档，经原生身份初始化与菜单创建后，本机玩家保持刘备；用户也确认画面显示刘备。
加载边界的783条样本检查全部通过。工具只写启动选择的16字节，原生程序自行设置势力2、君主952及官爵派生字段1，然后建立策略和用户界面。记录器恢复调试寄存器并正常退出，34号存档文件未变。
地图阶段抽样的部队业务状态、任务字段，以及51座城市的现存金钱、粮食、驻军均一致。但9座城市的+A0/+A4整数发生变化，恰好属于张鲁与刘备；其上游原生计算存在根据本机玩家势力分流、使用不同百分比的路径。
目前只追到静态依赖与实测范围相符，尚未逐项复算全部18个整数差值，不把这些字段列为可忽略的界面数据。已知随机值和运行时容器也仍有变化。完整世界一致性与双客户端推演仍未通过。

当前用户核对
只看菜单：庐江能否进入赏赐武将选择页、取消后宛城是否只可查看而不能下内政命令。本轮不确认命令、不推进日期。菜单结果尚待反馈。
此次一次性工具已退出，不会再次触发；执行意图记录保留，禁止自动重试。界面证据收齐后，再正常读取34号档恢复张鲁，不覆盖存档。
''' +text[end:]
    text=text.replace('这轮只使用当前一个游戏进程检验B端的进入方式。','这轮只使用当前一个游戏进程检验B端的进入方式，真实身份初始化已经通过。')
    if report.get('b_basic_menu_checks_user_reported_ok'):
        text=text.replace('菜单结果尚待反馈。','用户反馈“试了下，基本都没问题”。核对后的783条抽样记录与刘备载入后样本一致，部队业务与任务字段一致。本次只验了指定基本菜单，没有逐项验收全部权限、命令和事件。')
        text=text.replace('界面证据收齐后，再正常读取34号档恢复张鲁，不覆盖存档。','界面证据已收齐，现请正常读取34号档恢复张鲁，不覆盖存档。后续经济规则研究在独立进程中进行。')
    if report.get('recovery'):
        text=text.replace('界面证据已收齐，现请正常读取34号档恢复张鲁，不覆盖存档。后续经济规则研究在独立进程中进行。','已经正常读取34号档恢复张鲁：日期为203年8月中旬，抽样记录、部队业务和任务字段与切换前一致，存档文件未变，记录器已退出。一次性执行记录继续保留。本轮无须再操作。')
    (OUT/'刘备开局接入测试说明.txt').write_text(text,encoding='utf-8')
print(report['result'])
