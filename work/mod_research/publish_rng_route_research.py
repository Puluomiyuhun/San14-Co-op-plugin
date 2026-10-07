from datetime import datetime
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'outputs'/'san14-link'
def load(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
validation=load('rng-route-dll-validation-m.json')
audit=load('rng-route-site-audit-m.json')
live=load('rng-route-live-pristine-m.json')
boundary=load('lockstep-traces/boundary-after-route-dll-m.json')
previous=load('lockstep-traces/boundary-after-rng-fixture-l.json')
closeout=load('lockstep-traces/route-dll-m-closeout.json')
assert validation['result']=='PASS' and len(validation['cases'])==10
assert all(site['original'] for site in live['sites']) and not live['debugger_attached']
assert boundary['observations']==previous['observations']
assert closeout['save34_sha256']==closeout['backup_sha256']

report='''随机分流接入审计与独立DLL验证（第十二轮，2026-10-05）

结论
已完成一个由独立测试程序加载的DLL，验证候选包装层的调用和随机分流行为。10组测试通过；游戏未安装该DLL、未修改随机种子、未推进日期。这一步把上轮的算法原型推进到可跨DLL调用的包装层，还不能认定双客户端锁步成立。最早A轮首次漏算战斗的根因仍未查清。

一、把人物台词的包装范围缩小
原候选包住整段0x1AB630人物台词流程，但其中在生成文本之前调用显示对象、语音等步骤，之后也有界面处理。
新候选只包装0x1AB6F4调用0x1A1C10这一处，原函数依然执行一次，返回指针原样交回0x1AB6F9。表现上下文只覆盖这次同步调用，前后的界面处理不包含在内。
表达式里的两个随机入口是尾跳转：0x2D9243→0x3AA3F0（概率），0x2D9261→0x3AA7C0（范围）。只有处于上述同步上下文时才作为表现分流候选，未知来源继续执行原生函数。
语音变体使用独立候选点0x3B3774→0x3AA7C0；返回值仍用于选择后续语音分支，不能简单跳过调用。该点在独立原型中可分流，尚未实机启用。
原生全局0x18EB8B0继续保留给逻辑及只读种子消费者；表现使用私有状态，不交换或回滚全局种子。

二、用已有记录核对覆盖范围
近景144次随机写入：33次符合更窄的台词文本上下文，25次符合语音变体点（20次人物台词语音、5次战法语音）；85次其他消息路径仍走原生，另1次是保存过程同值写回。
远景146次已记主要写入：33次台词文本、28次语音、85次其他消息。远景另有3处已知随机序列缺口，缺失的写入不能凭该分类补认来源。
这些分类来自历史调用栈，不是已安装包装层的实时记录。范围参数小于2时不更新状态，写入日志也不会完整涵盖这类调用。尚未穷尽间接回调、异步任务及所有文本分支的副作用，因此上述位置仍是待实机审计的候选。

三、独立DLL做过的验证
测试程序只在自己的进程中加载rng_route_fixture.dll，用之前提取并重定位到私有内存的原生叶函数作为算法对照。DLL没有游戏进程查找、注入或补丁安装功能。
— 透传模式：嵌套文本调用、语音及未知表达式均保留原生结果和状态序列，原回调执行次数不变，64位返回指针完整保留。
— 分流模式：同步嵌套台词及语音使用私有状态，离开上下文后未知表达式恢复原生路径。
— 使用带展开信息的汇编CALL桥与叶函数尾JMP桥，验证相应调用形式；另外抽查RBX、RSI这两个非易失寄存器的保持。不是全部处理器状态的穷尽验证。
— 7个种子、119项范围/概率边界与原生函数相符；范围小于2不推进，概率阈值0、100仍消耗状态。
— 普通C++异常、显式Windows RaiseException，以及原随机回调抛出异常后，作用域深度和活动调用计数恢复，后续原生调用正常。这不代表能修复内存破坏或进程终止。
— 新线程不继承父线程台词上下文，未标记调用默认保持原生。正式接入遇到异步工作必须显式识别，不能依赖TLS自动传播。
— 两个表现线程共3000次抽取与单个逻辑线程2000次抽取并发，逻辑输出与原生参考逐项一致，私有最终状态也一致。未验证多个逻辑线程之间的确定顺序。
— 回调运行中拒绝替换配置，退出后允许替换；非法模式、空回调和错误结构大小被拒绝。没有实现游戏补丁卸载或并发卸载DLL。

四、与“为什么两次战场不同”的关系
共享随机状态存在跨流程影响，分流是排除这类影响的一条可行技术路径。独立测试只能证明包装层和算法行为，不能代替实机战场对照。
原A最初漏算与B出现差异时，已监测随机值仍一致，因此不能将原A直接归因于台词/语音随机。交战等待标志、隐藏队列、工作线程顺序仍需独立查证。
远景与近景虽然本次记录的交战片段和战法身份一致，但其起始随机状态及记录器不同，仍不是严格的单变量镜头实验。

五、下一步实机试验条件
先接入只记录来源、参数和返回结果的透传版本，核对包装范围、未分类调用以及新增包装对时序的影响；通过后再小范围开启私有状态，比较首次交战、逐段逻辑状态和演出事件。
实际指令替换、近地址跳转桥、线程协调和补丁撤销均未由本轮DLL实现。正式起点还须有阻止新逻辑输入、等待相关工作结束、快照及双方确认的同步边界；“队列看起来空了”不是完整屏障。

六、当前游戏与用户测试方法
只读核对：203年8月11日（中旬），抽查783条记录稳定；全局随机3510933083，与上轮核对值相同；已知人物台词队列为空、已知工作及特效待处理标志为0。四处候选指令仍为原始字节，调试器未附加，34号档与备份哈希相同。
当前随机值与早期A/B起点不同这一已知事实保留在证据中；本轮没有把它改回。原A/B首次军队差异早于首次已记录随机差异，收尾报告里的历史比较不是本轮新增分叉。
附带“随机分流独立验证包.zip”。如需自行复验，解压到任意独立目录，运行“运行独立验证.cmd”；看到10行PASS且退出码为0即与本轮一致。不需要启动游戏，不需要复制文件到游戏目录；该包不是联机插件，也不会操作游戏。这轮无需再次读档或推进。
'''
readme='''这是第十二轮研究的独立验证包，不是游戏联机插件。

用法：解压后运行“运行独立验证.cmd”。它只在自己的进程里加载同目录DLL，输出10组结果，全部PASS且退出码0代表验证成功。游戏不必启动。
请将整包放在独立目录，不需要放进Steam或游戏目录。
二进制使用本机Visual Studio 2022的x64运行时构建。若系统报告运行时DLL缺失，保留错误信息；这是运行环境问题，尚未执行验证。

包中包含DLL、测试程序、测试源码、原生算法对照代码、构建脚本、验证结果及SHA256清单。build_rng_route_fixture.cmd中的目录按本项目布局编写，复建时需保持work/mod_research目录层级，并使用相应编译器路径。
程序测试随机结果和包装层调用行为，不模拟三国志14战场，不安装或注入游戏，不证明双客户端锁步已完成。
'''
launcher='''@echo off
pushd "%~dp0"
if errorlevel 1 exit /b 1
rng_route_dll_fixture.exe "%~dp0rng_route_fixture.dll"
set "fixture_exit=%errorlevel%"
echo.
echo Fixture exit code: %fixture_exit%
pause
popd
exit /b %fixture_exit%
'''
package_files=[r['path'] for r in validation['files']]+['rng-route-dll-validation-m.json','native-rng-fixture-source.json']
package=OUT/'随机分流独立验证包.zip'
with zipfile.ZipFile(package,'x',compression=zipfile.ZIP_DEFLATED) as z:
    for filename in package_files:z.write(ROOT/filename,filename)
    z.writestr('说明.txt',readme.encode('utf-8-sig'))
    z.writestr('运行独立验证.cmd',launcher.replace('\n','\r\n').encode('ascii'))
    z.writestr('SHA256.json',json.dumps({name:sha(ROOT/name) for name in package_files},indent=2))
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None
    for name in package_files:assert hashlib.sha256(z.read(name)).hexdigest()==sha(ROOT/name)
manifest=package_files+['audit_rng_route_sites.py','rng-route-site-audit-m.json','check_rng_route_live_sites.py',
 'rng-route-live-pristine-m.json','rng-domain-classification-l.json','survey-1ab630.txt','survey-1a1c10.txt',
 'survey-2d91a0.txt','survey-3b36b0.txt','lockstep-traces/boundary-after-route-dll-m.json',
 'lockstep-traces/boundary-after-rng-fixture-l.json','lockstep-traces/route-dll-m-closeout.json','publish_rng_route_research.py']
evidence={'created':datetime.now().astimezone().isoformat(),
 'status':'DEDICATED_DLL_FIXTURE_PASS_GAME_HOOK_NOT_INSTALLED',
 'original_a_root_cause_proven':False,'two_real_clients_verified':False,'certified_sync_barrier':False,
 'validation':validation,'candidate_site_audit':audit,'read_only_live_site_check':live,
 'candidate_boundary_same_as_previous_turn':True,'candidate_boundary':boundary,'closeout':closeout,
 'package':{'file':package.name,'sha256':sha(package),'archive_integrity_verified':True},
 'manifest':[{'path':name,'sha256':sha(ROOT/name)} for name in dict.fromkeys(manifest)]}
for name,data in [('随机分流接入审计第十二轮.txt',report),('随机分流接入审计第十二轮证据.json',json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')]:
    with (OUT/name).open('x',encoding='utf-8') as f:f.write(data)
with (OUT/'双客户端实施路线.txt').open('a',encoding='utf-8') as f:
    f.write('\n锁步追查第十二轮：窄化台词上下文与独立DLL验证（2026-10-05）\n')
    f.write('候选台词范围缩到0x1AB6F4→0x1A1C10文本调用，另用两个表达式尾跳入口及一个语音变体点。历史近景记录对应33次台词文本、25次语音，其余85次消息保留原生，1次同值保存写回。独立DLL完成10组调用、返回值、嵌套、C++/SEH异常及并发分流测试。尚未安装到游戏，游戏候选指令及已知状态未改。最早A轮漏算根因仍未解，后续先做实机透传审计再考虑分流对照。详见“随机分流接入审计第十二轮.txt”。\n')
print(json.dumps({'published':True,'files':['随机分流接入审计第十二轮.txt','随机分流接入审计第十二轮证据.json',package.name],
                  'package_bytes':package.stat().st_size,'report_characters':len(report)},ensure_ascii=True))
