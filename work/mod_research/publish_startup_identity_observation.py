"""Publish real observation and separately label subsequent offline tooling."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'outputs'/'san14-link'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
observation=load(ROOT/'startup-identity-live-result.json')
closeout=load(ROOT/'startup-identity-closeout.json')
continuation=load(ROOT/'startup-continuation-audit.json')
folder=Path(observation['directory'])
archived=folder/'observer-artifacts'/'observe_startup_identity.exe'
assert sha(archived)==observation['observer_sha256']
assert observation['result']=='LOAD_ORDER_OBSERVED_NO_IDENTITY_CHANGE'
assert not observation['debugger_attached'] and observation['checkpoint34_unchanged']
assert closeout['raw_changed_records']==54 and not closeout['unexpected_sampled_record_changes']
infra=load(ROOT/'startup-identity-observer-tests.json')
payload=load(ROOT/'startup-identity-payload-validation.json')
analysis=load(ROOT/'startup-identity-analysis-tests.json')
assert all(r['result']=='PASS' for r in infra)
assert payload['result']==analysis['result']=='PASS'
paths=[folder/'trace.jsonl',folder/'before.json',folder/'after.json',folder/'analysis.json',
       folder/'closeout.json',archived,folder/'observer-artifacts'/'startup_identity_observe.inc',
       ROOT/'observe_startup_identity.exe',ROOT/'startup_identity_observe.inc',
       ROOT/'startup-continuation-audit.json',OUT/'startup_identity_reader.py']
report={
    'schema':'san14.shared-startup-live-evidence.v1',
    'created':datetime.now().astimezone().isoformat(),
    'result':'ORIGINAL_PLAYER_LOAD_ORDER_OBSERVED_B_STARTUP_NOT_YET_VERIFIED',
    'real_observation':observation,'sampled_closeout':closeout,
    'offline_continuation_audit':{k:v for k,v in continuation.items() if k not in
                                ('offset_4a0_4a8_candidates','undecoded_ranges')},
    'offline_scan_limits':{'unrelated_offset_candidates':len(continuation['offset_4a0_4a8_candidates']),
                          'undecoded_ranges':len(continuation['undecoded_ranges']),
                          'exhaustive_call_graph':False},
    'semantic_correction':{'rva':'0x1fca518','meaning':'Force context with several native UI writers; not a permanent player binding',
                           'legacy_cached_player_force_id_is_diagnostic_only':True},
    'subsequent_observer_enhancement':{'binary_sha256':sha(ROOT/'observe_startup_identity.exe'),
        'used_in_real_load_above':False, 'game_attached_by_new_version':False,
        'added_fields':['initializer_return_rva','native_handoff_context'],
        'lifecycle_tests':infra,'synthetic_payload':payload,'analysis_tests':analysis},
    'game_data_writes_this_round':0,'b_real_menu_verified':False,
    'two_client_startup_verified':False,'automatic_game_loading_implemented':False,
    'complete_world_equality_proven':False,'native_gameplay_enabled':False,
    'next_bounded_validation':'Use native load-time identity path for selected B faction; verify real menus, ownership and absence of later identity overrides before any turn advance.',
    'artifacts':[{'path':str(p.relative_to(ROOT.parents[1])),'sha256':sha(p)} for p in paths]}
(OUT/'共同开局真实载入证据.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=OUT/'完整联机逻辑与验收基线.txt'
text=path.read_text(encoding='utf-8')
note='''
共同开局真实记录补充（2026-10-06）
已在真实34号存档载入中观察到：载入成功后原生初始化张鲁身份，再创建策略和用户界面。此为建立B本机身份的候选阶段，B真实菜单尚未验证。
本轮还确认先前称为本机势力缓存的1FCA518有多个界面写入者；它是诊断用势力上下文，不能承担房间绑定、命令授权或单独的开局就绪判据。
抽样业务状态一致，显示对象指针重建；已知随机与部分运行时计数变化。共同存档载入后仍须核对/同步必要共享状态，不能宣布确定性锁步或自动开局已完成。详见“共同开局真实载入证据.json”和“共同开局与本机势力初始化.txt”。
'''
if '共同开局真实记录补充（2026-10-06）' not in text:
    path.write_text(text+note,encoding='utf-8')
print(json.dumps({'result':report['result'],'real_observation_events':6,'runtime_pointer_changes':54,
                  'new_payload_events':payload['events'],'new_negative_cases':payload['handoff_negative_cases'],
                  'lifecycle_tests':len(infra),'analysis_tests':len(analysis['cases'])}))
