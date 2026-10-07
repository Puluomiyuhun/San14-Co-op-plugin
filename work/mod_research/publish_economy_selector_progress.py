"""Publish the bounded arithmetic result, keeping real-world gaps explicit."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'outputs'/'san14-link'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
report=load(ROOT/'economy-selector-test-results.json')
assert report['result']=='PASS' and report['adapted_equal_pairs']==4896
evidence={'schema':'san14.economy-adaptation-progress.v1',
          'basic_menu_observation':load(ROOT/'startup-switch-menu-result.json'),
          'real_city_difference_audit':load(ROOT/'city-identity-effects-audit.json'),
          'isolated_selector_verification':report,
          'real_game_economy_fixed':False,'full_world_equality_verified':False,
          'live_adapter_installed':False,'two_real_clients_verified':False}
pipeline_path=ROOT/'economy-pipeline-audit.json'
if pipeline_path.exists():
    evidence['pipeline_audit']=load(pipeline_path)
    evidence['recovery']=load(ROOT/'startup-switch-recovery.json')
(OUT/'经济规则适配证据.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
text='''经济规则适配进展
更新：2026-10-06

已完成的真实开局检查
同一份34号张鲁存档经原生初始化进入刘备。用户随后按要求查看庐江赏赐选择页和宛城权限，反馈“试了下，基本都没问题”。检查后783条抽样记录、部队业务和任务字段与刘备载入后样本一致，没有抽查到菜单浏览造成的新业务变化。
这属于指定基本菜单的用户实测，不能扩展为全部命令、权限和事件已验收。

为什么还需要适配经济规则
张鲁与刘备两种本机身份下，9座相关城市的两个计算字段不同，现存金钱、粮食与驻军则一致。代码显示，两个上游计算入口使用“该势力是否等于本机玩家”的判断选择百分比。
若A只把张鲁视为玩家、B只把刘备视为玩家，同一城市便可能按不同规则计算。共享经济规则应把双方均视为人类，菜单权限继续只属于各自本机身份。

本轮开发内容
新增human_economy_policy.h，按两个已经审计的原生调用返回位置选择共同人类势力规则。仅处理这两个经济入口，其他调用保留原生本机判断；没有全局替换玩家查询。
候选规则要求两个人类势力、有效身份、相同绑定版本、已核对的设置和代码版本。上下文不符时返回Hold，未来接入器必须在计算前暂停；该头文件自身不会安装拦截或暂停游戏。
读取的游戏版本为SAN14PK_SC 1.0.11.0，对应可执行文件SHA256：
42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025

实际运行的离线对照
两个独立测试进程分别使用张鲁、刘备本机身份，运行复制的原生百分比选择及算术片段，并保留复制的原生本机玩家查询。设置对象读写和区域转势力的周边调用使用明确的测试替身，上游完整城市收益、支出、结算没有执行。
两边各跑4896组输入：原生规则中132组两端不同；采用共同人类势力规则后，4896组全部一致。
其中4704组非玩家势力计算与原生结果保持一致。102项原生本机身份判断仍只认各自势力。另有72项非法上下文拒绝与未分类调用保留原规则的检查通过。
测试包含两种计算片段、多个设置值、51个势力以及正数、负数和取整边界；它证明了这两个倍率选择入口的适配方向。

仍未完成的部分
尚未逐项复算真实9城的18个整数差值；不能把这些字段从世界校验中忽略。
尚未审计全部收入、支出、结算和其他依赖本机身份的共享逻辑；这两个入口不能代表全部经济规则。
候选规则尚未接到房间绑定/设置校验和真实游戏模块，没有向正在运行的游戏安装经济补丁，没有改变金粮或推进日期。
下一步追踪完整计算的输入与副作用，补齐具体调用点，再做受控的真实开局对照；数据核对、双人AI保护和日期推进同步仍是开放双人游戏前的必需项。

当前操作
刘备界面检查已结束，正常读取34号档即可恢复张鲁；停在大地图，不下令、不推进。一次性切换记录保留，不自动重复执行。
后续这部分验证优先使用保存的数据和独立程序，不需要用户逐项复现内政操作。
'''
if pipeline_path.exists():
    text=text.replace('刘备界面检查已结束，正常读取34号档即可恢复张鲁；停在大地图，不下令、不推进。一次性切换记录保留，不自动重复执行。','已读取34号档并核对恢复张鲁，203年8月中旬。抽样记录、部队业务和任务字段与切换前一致，原存档不变，没有调试器留在游戏中。本轮无须再操作。一次性切换记录保留，不自动重复执行。')
    text+='''
完整计算路径补充
已核对43处原生指令，区分收益预览和真正结算的入口。预览模式跳过所观察到的库存/人口提交区间，但仍会清空或写入区域+4A/+4C/+4E/+50等派生字段。因此不能在任意线程把这个函数当成无副作用的读取工具。
新增只读economy_reader.py，采集501个区域槽位及原生顺序中的343个有效区域、344个中心格记录、258个相关武将记录（含空对象），以及城市/势力资料。已补入旧样本缺少的武将+198和+1F8字段。
本次采样时有效区域的上述四项派生字段都是零；没有B端同阶段区域样本，不能声称已观察到区域差异。扩大采样是为后续完整对照保留证据。
真实稳定读取记录已保存，离线重放与错代码、错类型、越界、链表成员异常、采样中途变化等12项检查通过。
仍缺少完整有效能力查询涉及的装备、官职和上限解码，以及个性/政策查询、设置与日期相关输入。完整9城差值重放尚未完成，没有忽略差异，也没有在游戏内调用收益预览或安装新补丁。
'''
(OUT/'经济规则适配进展.txt').write_text(text,encoding='utf-8')
print('PUBLISHED_ISOLATED_ECONOMY_SELECTOR_PROGRESS')
if (ROOT/'economy-shadow-verification.json').exists():
    import runpy
    runpy.run_path(str(ROOT/'publish_economy_shadow.py'),run_name='__main__')
