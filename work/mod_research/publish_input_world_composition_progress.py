"""Publish verified evidence without upgrading independent fixtures to gameplay."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'outputs'/'san14-link'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def resolve(name):
    p=Path(name)
    if not p.is_absolute():p=(ROOT if p.parts[0]=='work' else HERE)/p
    p=p.resolve(strict=True)
    assert p.is_relative_to(ROOT.resolve())
    return p

names=('checkpoint_session_input_admission_handoff.json','checkpoint_native_input_router_handoff.json',
       'checkpoint_world_coverage_extension_handoff.json')
verified={};evidence=[]
for name in names:
    path=HERE/name;h=read(path)
    rows=[(r['path'],r['sha256']) for r in h.get('artifacts',[])]
    for key in ('source_sha256','source_and_artifact_sha256','frozen_dependencies_sha256'):
        rows.extend(h.get(key,{}).items())
    for source,digest in rows:
        p=resolve(source);assert sha(p)==digest,str(p)
        verified[str(p)]=digest
    for key in ('fixture_report','native_report'):
        if key in h:
            p=resolve(h[key]);assert sha(p)==h[key+'_sha256']
    evidence.append(dict(path=str(path),sha256=sha(path)))
for directory in ('checkpoint_room_progress_tests','checkpoint_connected_prototype_tests'):
    p=sorted((HERE/directory).glob('*/result.json'))[-1];r=read(p)
    assert r['result']=='PASS'
    for name,digest in r['source_sha256'].items():
        assert sha(HERE/name)==digest
        verified[str(HERE/name)]=digest
    evidence.append(dict(path=str(p),sha256=sha(p)))

report=dict(schema='san14.input-world-composition-progress.v1',updated=datetime.now().isoformat(),
    result='OFFLINE_COMPOSITION_VERIFIED',evidence=evidence,verified_artifacts=len(verified),
    tests=dict(session_input_admission=19,unified_input_router=14,world_native_replay=6,
               world_schema=7,room_progress=8,connected_pipeline=7),
    new_table=dict(class_name='CObjectData',physical_slots=3001,serialized_field_bytes=24008,
                   current_live_capture=False,all_field_semantics_known=False),
    new_session_controller_used_by_network_runtime=False,
    same_game_process_multiple_native_loads_verified=False,
    native_body_doubles_present_in_session_fixture=True,
    game_access=False,full_world_verified=False,full_input_hold_verified=False,
    native_gameplay_enabled=False,verified_sha256=verified)
(OUT/'输入加载串接与世界核验进展.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
text='''三国志14联机：输入、加载与世界核验的本轮进展

菜单检查已能决定是否发起加载
新增组合控制器把菜单检查与 Session 加载链实际串起：进入更新 → 原函数内菜单读取前检查 → 正常返回 → 授权压入加载菜单 → 核对新菜单 → 绑定并提交加载。
成功路径随后取得字节、加载生命周期、B 身份和新下令界面的检查结果；19 个自有进程场景通过。
玩家已有请求、更新中新增请求、遗漏检查点、错误菜单、异常、重入和停止等情况不会错误提交加载；原更新仍正常处理玩家请求。
这些测试复用了正式观察核心，但原游戏状态构造/更新仍包含测试替身，没有调用正在运行的游戏。

输入查询统一
鼠标、普通按键、修饰键和动作查询已由同一条路由调度，共用尝试身份、游戏实例、线程和递增序号，默认正常转发。
序号重复、来源布局变化、跨线程、未知参数和重入会拒绝；委派失败或原异常不会退还已占用序号。
14 项独立进程测试通过，底层归档查询代码真实执行。异常测试的注入包装器有明确标记。
尚无游戏安装器，也不因此声称所有输入来源都已隔离。统一输入路由与新的 Session 控制器仍是分别验证的组合件。

世界核验新增一类具体数据
CObjectData 全部 3001 个物理槽，每槽 +0x10 到 +0x17 的八字节序列化内容，共 24008 字节。
此前该类只抽查城市关联对象的耐久字段；本轮对这一整张表的原生读写路径做了机器码回放，6 个场景通过，严格结构校验 7 项通过。
新校验要求完整槽位、正确数量、精确长度和结束标记。实证表明，原生返回成功不一定表示完整读取：零记录和尾标记截断也可能被上层当作成功。
除已知耐久字段外，其余字段暂保留原始字节。当前还没有读取真实游戏的这张完整表，也未解码整份存档或证明全世界一致。

A 能看到 B 同步到哪一步
B 的接收、文件就绪、加载请求、身份恢复和等待核验提示，经房间控制连接传回；A 的状态查询和保活返回会包含该提示。
提示只作诊断，不会创建加载完成回执、允许准备或放行下一旬。8 项权限及顺序测试通过。
主网络→历史字节→一次加载诊断现为 7 项通过，新增了进度上报成功但回复丢失的场景：A 可以看到加载请求提示，实际 native ARM 仍为零，记录保留等待且不会重试。
正常诊断依旧等待完整世界核验，没有把“文件传完”或“身份恢复”当作全部完成。

可使用的入口
同目录“运行房间到加载诊断.cmd”已加入进度回传，正常报告可查看 host_progress_history。
它仍使用既有已验证的 runtime；本轮新的 19 场景 Session 组合尚未替换进去。
两个诊断入口均不访问游戏或 Steam，不需要用户操作游戏，也不是可分发的联机安装包。

接下来优先解决
1. 将新的加载准入控制器接入受控 runtime 协议，再与统一输入路由形成同一次加载的组合验证。
2. 实现真实游戏驻留接入、持续输入屏障和地图等待层，并做一次完整实机自动加载验证。
3. 解决同一个游戏进程内下一旬如何建立新会话。当前 Session 的一次性控制器和提交后的观察保留限制尚未解决，不能把网络两轮传输当作原生多旬加载已通。
4. 继续补全剩余世界表、动态状态和规则核验，再做真实双机连续多旬与命令同步。
'''
(OUT/'输入加载串接与世界核验进展.txt').write_text(text,encoding='utf-8')
master=OUT/'开发剩余工作评估.txt'
prefix=('最新进展（2026-10-07，输入加载组合）：菜单准入到单次 Session 加载链 19 场景、统一输入路由 14 场景通过；'
        '新增 CObjectData 3001 槽/24008 字节的原生读写结构核验。同步进度已回传 A，主离线链 7 场景通过。'
        '尚未替换网络 runtime 或证明同游戏进程多旬加载，详见《输入加载串接与世界核验进展.txt》。\n\n')
old=master.read_text(encoding='utf-8')
if not old.startswith(prefix):master.write_text(prefix+old,encoding='utf-8')
print(json.dumps({'result':report['result'],'verified_artifacts':len(verified),'game_access':False}))
