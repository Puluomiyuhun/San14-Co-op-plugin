"""Publish preparation evidence without calling a pending recording complete."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'outputs'/'san14-link'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
audit=load(ROOT/'startup-identity-audit.json')
infra=load(ROOT/'startup-identity-observer-tests.json')
payload=load(ROOT/'startup-identity-payload-validation.json')
analysis=load(ROOT/'startup-identity-analysis-tests.json')
idle=load(ROOT/'startup-identity-idle-check.json')
assert all(t['result']=='PASS' for t in infra) and payload['result']==analysis['result']==idle['idle_result']=='PASS'
report={'schema':'san14.shared-startup-preparation.v1','created':datetime.now().astimezone().isoformat(),
        'result':'OBSERVER_PREPARED_REAL_LOAD_RECORDING_PENDING','static_audit':audit,
        'observer_lifecycle_tests':infra,'synthetic_payload':payload,'analysis_guards':analysis,
        'real_idle_attach_detach':idle,'before_recording_context':load(ROOT/'startup-current-context.json'),
        'native_identity_changes':0,'b_real_menu_verified':False,'automatic_game_loading_implemented':False,
        'sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (
            ROOT/'observe_startup_identity.exe',ROOT/'startup_identity_observe.inc',
            ROOT/'analyze_startup_identity.py',OUT/'startup_identity_reader.py')}}
(OUT/'共同开局初始化预研证据.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=OUT/'完整联机逻辑与验收基线.txt'
text=path.read_text(encoding='utf-8')
note='''
共同开局实施补充（2026-10-06）
采用A生成/选择共同起点，B接收同一世界，并在原生初始化边界建立B本机身份的方案。首次实现优先让双方共同重读检查点后核对，避免把A已经初始化的运行状态与B刚加载的状态直接当成一致。
身份建立必须覆盖策略状态与界面缓存；不是进入地图后只改玩家编号。具体用户流程与本轮原生路径见“共同开局与本机势力初始化.txt”。本轮新增只读上下文采样和载入顺序观察器，B真实菜单与自动开局尚未通过。
'''
if '共同开局实施补充（2026-10-06）' not in text:
    path.write_text(text+note,encoding='utf-8')
print(json.dumps({'result':report['result'],'anchors':len(audit['anchors']),
                  'lifecycle_tests':len(infra),'analysis_guard_cases':len(analysis['cases'])}))
