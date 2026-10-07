"""Record completed offline adapter integration without upgrading live-load claims."""
from datetime import datetime
import json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;OUT=P.parents[1]/'outputs/san14-link'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def entry(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def main():
    names=['checkpoint_live_storage_binding_handoff.json',
        'checkpoint_native_queue_adapter_handoff.json',
        'checkpoint_authorized_forward_admission_handoff.json',
        'checkpoint_live_runtime_guard_plan.json',
        'checkpoint_live_storage_binding_review_20261007-145047-633260.json',
        'checkpoint_queue_authorized_independent_review_20261007-150032-008360.json']
    paths=[P/n for n in names]
    handoffs=[read(p) for p in paths[:3]]
    for h in handoffs:
        if h['schema']=='san14.native-queue-adapter-handoff.v1':
            rp=Path(h['own_process_tests']['path']);expected=h['own_process_tests']['sha256']
        else:rp=Path(h['fixture_report']);expected=h['fixture_report_sha256']
        rp=rp if rp.is_absolute() else P/rp
        assert hashlib.sha256(rp.read_bytes()).hexdigest()==expected
        r=read(rp)
        if r['schema']=='san14.native-queue-adapter-fixtures.v1':
            assert r['passed'] is True and r['production_compiled'] is True
        else:assert r['result']=='PASS'
        assert all(c['passed'] for c in r['cases'])
        for name,digest in h['source_sha256'].items():
            assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest,name
    marker='本轮离线接线收尾：原生排队与存档接口'
    note=f'''{marker}

已实现原生加载菜单的单次排队适配器，并在隔离测试中接入输入检查产生的授权。它只接受同一调用、同一线程、同一控制器的请求；设计上会在原生代码返回后核对新建的菜单和队列，再继续加载会话。存档接口适配器核对缓存代际、模块归属及实际读取函数；只在初始化时核验模块文件，不在每次存档读取时重复扫描大型DLL。

这两项和授权控制器已完成独立进程验证；组合测试使用实际适配器，原生游戏函数主体仍由明确的测试替身承担，没有执行新的真实游戏加载。取消后的未消费授权须由上层同时撤销，停止控制器本身不等于整个会话已结束。

完整自动加载的剩余接线已细化到各个实际回调：加载前检查当前地图，加载中核验本次文件及活对象，加载后识别新玩家与新界面。生产环境的这些阶段校验及统一安装入口仍未完成。下一验收仍是：自动载入指定检查点、恢复刘备身份、回到可下令大地图；随后才做第二次连续加载和等待画面。
'''
    report=OUT/'实机加载接入进展.txt';text=report.read_text(encoding='utf-8-sig')
    if marker not in text:report.write_text(text+'\n'+note,encoding='utf-8-sig')
    evidence=OUT/'实机加载接入证据.json';record=read(evidence)
    record['updated']=datetime.now().astimezone().isoformat()
    record['offline_native_queue_adapter_verified']=True
    record['offline_cached_storage_binding_verified']=True
    record['offline_private_ticket_queue_handoff_verified']=True
    record['runtime_phase_guards_implemented']=False
    record['complete_session_installed']=False
    record['automatic_guest_reload_proven']=False
    seen={x['path'] for x in record['evidence']};record['evidence'] +=[entry(p) for p in paths if str(p) not in seen]
    evidence.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    resume=P/'mainline_20261007_live_resume.json';state=read(resume)
    state['offline_production_bindings']={n:entry(P/n) for n in names[:3]}
    state['runtime_guard_plan']=entry(P/names[3])
    state['production_owner_stop_requirement']='Retire/abort must stop queue adapter as well as admission controller; a minted-but-unconsumed queue capability otherwise remains. Never stop post-CAS byte/identity/lifecycle recovery just because admission is closed.'
    state['next_concrete_integration']=[
        'Use authorized-forward Controller + native queue Adapter + bound pending + hardware provider with frozen forward Session; preserve old frozen reports and all once claims.',
        'Implement the phase-specific validators from checkpoint_live_runtime_guard_plan.json and assemble one retained production owner/DLL. No always-true validators; storage callback graph must be acyclic.',
        'Acquire fresh supported attachment/config/module bindings and expected RNG immediately before Initialize; snapshots/historical successful observations are not current authorization.',
        'Run one real CC03 automatic load with exact buffer hash, lifecycle, Title identity pair 12/666 to 2/952, and rebuilt planning boundary. Retain all observers after possible CAS.',
        'Then solve repeated Session ownership, true map cover/input hold and full-world/room READY requirements. One successful load will not prove repeated periods or playable two-client synchronization.'
    ]
    resume.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'result':'PUBLISHED_OFFLINE_BINDINGS_ONLY','report':str(report)},ensure_ascii=False))
if __name__=='__main__':main()
