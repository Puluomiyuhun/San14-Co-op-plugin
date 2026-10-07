"""Record offline continuation work without accessing or installing in SAN14."""
import hashlib,json
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent
OUT=P.parents[1]/'outputs/san14-link'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rec(p):return dict(path=str(p.resolve()),sha256=sha(p),data=json.loads(p.read_text('utf8')))
def main():
    bridge_result=P/'checkpoint_persistent_bridge_runs/20261007-164806-742669/result.json'
    bridge=rec(bridge_result);route=rec(P/'checkpoint_persistent_route_handoff.json');profile=rec(P/'checkpoint_repeat_load_profile_handoff.json')
    assert bridge['data']['passed'] and route['data']['offline_passed']
    checked={}
    for mapping in (bridge['data']['source_sha256'],route['data']['source_sha256'],route['data']['objects'],profile['data']['files']):
        for name,expected in mapping.items():
            assert sha(P/name)==expected,name
            checked[name]=expected
    for row in route['data']['evidence']:assert sha(Path(row['path']))==row['sha256']
    native=json.loads((P/'checkpoint_complete_live_owner_v2_handoff.json').read_text('utf8'))
    assert all(sha(P/name)==expected for name,expected in native['source_sha256'].items())
    assert sha(P/'checkpoint_complete_live_owner_v2.dll')==native['dll_sha256']
    stamp=datetime.now().isoformat(timespec='seconds')
    evidence=dict(schema='san14.persistent-loading-offline-progress.v1',updated=stamp,game_access=False,
        bridge=bridge,route=route,profile=profile,current_source_hashes=checked,
        frozen_successful_owner_unchanged=True,second_native_load_executed=False,
        session_integrated=False,native_scheduler_fence=False,production_generation_switch=False,
        arbitrary_checkpoint_native_support=False,two_clients_playable=False)
    (OUT/'连续加载改造证据.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
    text='''连续加载改造进展

已完成单次自动加载；这轮开发的是连续每旬恢复所需的底层改造，尚未在游戏里执行第二次加载。

本轮实际代码
1. 新建六个常驻回调入口。正常返回、原生异常和观察回调异常都有收尾，保留原始返回值与异常，不需要每旬重新替换入口。
2. 新建旬次归属路由。进入回调时确定本次属于哪一旬；开始、结束和异常收尾使用同一份不可变上下文。旧调用进行中切换到新旬，不会把旧调用的结束记录写进新旬。嵌套调用沿用外层归属，独立新入口则读取当时的旬次。
3. 新建重复加载参数校验。严格区分“客户端当前是刘备”“收到的主机存档带张鲁身份”“恢复后仍应是刘备”。日期、文件内容、房间编号和本地执行编号分别绑定，避免将本地身份当成存档原始身份。

验证结果
六入口原生调用与异常测试29个场景通过；旬次路由和真实六入口组合20个场景通过，含四线程并发12,000次调用。参数校验11个测试方法、36类拒绝情形通过；审计定位25处需要参数化的源码锚点。
上述均在自有测试进程或纯数据中执行，没有操作游戏、Steam存档或当前已通过实测的DLL。

还缺的直接接线
1. 把已验证的完整加载会话迁到常驻入口：旧实现的槽位编号、线程内所有权接口和每会话计数需要明确适配，不能直接替换指针就使用。
2. 将档案大小、摘要、日期、势力及剧本相关字段贯通到每一轮的原生检查。新参数校验目前只生成准备信息，没有生成可执行原生配置。
3. 在实际游戏调度边界确认上一旬任务已结束，再开放下一次加载。回调计数暂时为零不等于不会再有迟到任务；本轮路由只证明已进入调用的归属，不证明该交接条件。
4. 然后完成同一游戏进程的连续两次加载，再接完整世界核验、地图等待画面和双客户端循环。

边界
当前路由最多保留32份旬次上下文，不回收已引用上下文，也不是无限轮次成品。旬次切换接口目前只用于明确标记的离线试验，未开放生产加载授权。本轮无需用户再次读档、推进或重启。
'''
    (OUT/'连续加载改造进展.txt').write_text(text,encoding='utf8')
    resume=P/'mainline_20261007_live_resume.json';state=json.loads(resume.read_text('utf8'))
    state['persistent_loading_offline']=dict(evidence=str((OUT/'连续加载改造证据.json').resolve()),
        report=str((OUT/'连续加载改造进展.txt').resolve()),bridge_cases=29,route_cases=20,
        native_second_load=False,game_access=False)
    state['next_concrete_integration']=[
        'Keep the passed V2 owner/claim retained and unchanged; do not hot-swap its six live hooks.',
        'Adapt complete loading Session to permanent six-entry bridge, per-entry generation lease and explicit physical/logical slot plus Claim/TLS binding.',
        'Propagate repeat-load profile across request/bytes/lifecycle/identity/guards/planning, distinguishing current B, incoming A and restored B.',
        'Prove the native transition boundary before production generation switching; offline route isolation alone is insufficient.',
        'Then exercise two consecutive native loads in one process, followed by full-world checks, visible input-held cover and two-client period loop.']
    resume.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
    assessment=OUT/'开发剩余工作评估.txt'
    existing=assessment.read_text('utf8')
    assessment.write_text('最新离线进展（'+stamp+'）：六个常驻入口、旬次回调归属和重复加载参数校验已实现并通过独立测试；尚未接入完整加载会话或执行真实连续两旬。详见《连续加载改造进展.txt》。\n\n'+existing,encoding='utf8')
    print(json.dumps(dict(published=True,checked_files=len(checked),game_access=False,second_native_load=False)))
if __name__=='__main__':main()
