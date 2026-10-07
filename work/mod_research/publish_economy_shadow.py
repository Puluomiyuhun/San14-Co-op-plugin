"""Publish the current bounded proof; preserve earlier stage evidence."""
import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parents[1]/'outputs'/'san14-link'
load=lambda name:json.loads((HERE/name).read_text(encoding='utf-8'))
r=load('economy-shadow-verification.json');close=load('economy-shadow-closeout.json')
extra_city=load('economy-extended-after-restoration.json')['cities']['20']['name']
assert r['result']=='PASS_EXACT_CITY_DELTAS_AND_SHARED_HUMAN_PREVIEW'
assert close['result']=='UNCHANGED_SAMPLED_BUSINESS_STATE'
evidence={'schema':'san14.economy-adaptation-progress.v2','current_stage':'Complete preview-formula shadow execution',
          'complete_preview_verification':r,'live_closeout':close,
          'earlier_isolated_selector_verification':load('economy-selector-test-results.json'),
          'basic_menu_observation':load('startup-switch-menu-result.json'),
          'live_adapter_installed':False,'full_world_equality_verified':False,'two_real_clients_verified':False,
          'implementation_sources_at_publication':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in
             ('economy_shadow.py','test_economy_shadow.py','validate_economy_shadow.py','close_economy_shadow.py')}}
(OUT/'经济规则适配证据.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rows='\n'.join(f"{c['name']}：原张鲁视角{c['observed_original_A']}；原刘备视角{c['observed_original_B']}；适配后双方{c['adapted_A_and_B']}" for c in r['cities'])
text=f'''经济规则适配进展
更新：2026-10-06

本轮结论
此前同一存档换成刘备后，9座城市的+A0/+A4字段出现18个整数差值。现在已经通过完整收益/支出预览函数复算，张鲁、刘备两种身份下的36个数值均与已保存的真实游戏样本一致，18个差值全部复现。
这些差值由已定位的两个区域收入入口按“该势力是否为本机玩家”选择不同倍率造成。在本次设置（设置键5的原生查询值为1）下，人类倍率150%，AI倍率100%。设置项在界面上的难度名称尚未核对。
倍率逐区域计算、取整后再汇总，不能对城市总额统一乘倍率。庐江两项区域收入原为2812、5892，成为本机人类后为4216、8835；若错误地把总额乘1.5，会得到4218、8838。
本次两种身份下支出和模式0收入一致。+A0/+A4按模式1收入减支出，再加两倍模式0收入减支出计算；它们不是当前库存金粮。仍不允许在世界一致性校验中忽略这些字段。

候选规则的完整计算验证
只对原生2110B0的两个已审计经济调用（返回位置28DE76、28DAAA）使用房间人类势力集合{{张鲁、刘备}}。其他本机身份判断保留原规则。
两种本机身份分别运行完整预览计算后，9座城市全部一致；80个区域的160项收入结果连同顺序也全部一致，且区域汇总与城市收入一致。
另选寿春（势力11）作为其他势力对照，原规则/候选规则、张鲁/刘备视角四种组合的完整结果相同：[-1002, -2633]。本轮没有遍历全部51城。

9城对照（每对数值依次为+A0、+A4）
{rows}

实际开发了什么
新增economy_shadow.py独立计算工具，使用Unicorn 2.1.4执行游戏原有x64指令。工具以只读权限复制必要游戏数据，所有身份初始化、链表操作和预览写入都发生在模拟器私有内存；没有让正在运行的游戏执行这些函数，也没有向游戏写入补丁或业务数据。
复制数据后，可完全脱离游戏进程重放。武将有效能力、装备/官职、个性、政策、区域遍历及收入支出计算沿用所走路径的原始代码，没有用固定数字替代这些经济查询。
明确建模的外围部分包括单线程锁、线程编号、临时内存分配/释放、已初始化设置对象的TLS入口、已提交栈的检查，以及两处等价的内存清零。经济修正规则仅限前述两个调用点。
缺失的数据页、未知外部调用、未初始化设置和异常释放会停止测试。12项离线工具检查通过；曾尝试追加{extra_city}对照，但冻结数据缺页，工具停止，该城市未计入验证。

如何核对采样
两个相关内存池各取得连续两份相同的完整复制，避免把游戏界面反复借还的节点拼成不一致的链表。计算后核对171422字节实际读取依赖，经济/代码依赖未出现变化。
195字节变化只被已审计的内存池分配函数在私有写入前读取，且位于已复制的池范围，单独记录为分配器状态；若同一字节也被业务代码读取，则不作此分类。相关拒绝条件已测试。
这是稳定读取检查，不是整个游戏进程的原子快照或完整世界哈希。

实际游戏当前状态
仍为张鲁、203年8月中旬，停在可下令大地图。前后区域、城市、相关武将、势力/军团及列表样本相同，34号存档SHA256不变，无调试器附着。没有推进日期，无须再读档或重复操作。

与双客户端主线的关系
“相同世界数据、各自本机势力”这个设计可以保留；共享经济规则需要使用房间内的两个人类势力集合，菜单继续使用各自本机势力。现在已证明这两个入口的完整预览计算能满足这一点。
输出目录中的human_economy_policy.h仍是候选规则，要求有效的房间绑定版本、人类势力集合、设置核对和游戏代码版本。头文件自身不安装拦截，也不自动暂停游戏。

仍需完成
1. 将候选规则接入真实模块和房间绑定/设置校验，在安全阶段做实际游戏预览对照；本轮尚未安装真实补丁。
2. 核对旬内真正结算及其余依赖本机身份的路径。此次执行的是完整预览入口，没有证明全部经济、AI、事件或战斗计算都已覆盖。
3. 继续整合双方开局、命令传递、人类势力AI保护和日期推进。两台真实客户端与完整战场锁步尚未验收。
'''
(OUT/'经济规则适配进展.txt').write_text(text,encoding='utf-8')
print('PUBLISHED_COMPLETE_PREVIEW_SHADOW_VERIFICATION')
