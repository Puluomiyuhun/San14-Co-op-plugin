"""Publish weighted engineering estimates with exact evidence boundaries.

This only reads workspace artifacts. Percentages are human estimates of work,
not derived from test totals and never used to enable gameplay.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'outputs'/'san14-link'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def local(path):
    p=Path(path)
    p=(p if p.is_absolute() else ROOT/p).resolve()
    assert p.is_relative_to(ROOT), 'Evidence must stay in this workspace'
    assert p.is_file(),p
    return p

parser=argparse.ArgumentParser()
parser.add_argument('--planning-evidence',required=True)
parser.add_argument('--port-evidence',required=True)
args=parser.parse_args()
audit_path=HERE/'progress_audit_20261007.json'
audit=json.loads(audit_path.read_text(encoding='utf-8'))
assert not audit['game_process_access'] and not audit['steam_directory_access']
for value in audit['evidence_sources'].values():
    p=local(value['workspace_path'])
    assert sha(p)==value['sha256'],p
modules=audit['modules']
assert sum(m['weight'] for m in modules)==100
assert all(0<=m['estimate_low']<=m['estimate_high']<=100 for m in modules)
assert all(m['real_two_client_acceptance'] is False for m in modules)
low=sum(m['weight']*m['estimate_low']/100 for m in modules)
high=sum(m['weight']*m['estimate_high']/100 for m in modules)
rounded=[int(5*round(low/5)),int(5*round(high/5))]
assert rounded==audit['overall_range']

proofs={}
for label,path in (('planning_return_observer',args.planning_evidence),('native_port_composition',args.port_evidence)):
    p=local(path);r=json.loads(p.read_text(encoding='utf-8'))
    assert r['result']=='PASS',p
    sources=r.get('source_sha256',{})
    assert sources,'Source-bound evidence required'
    for name,expected in sources.items():
        src=Path(name)
        if not src.is_absolute():src=HERE/src
        assert sha(local(src))==expected,src
    for name,expected in r.get('frozen_unchanged',{}).items():
        assert sha(local(name))==expected,name
    assert r.get('game_access') is False,p
    proofs[label]={'path':str(p),'sha256':sha(p),'result':r['result'],
                   'source_sha256':sources,
                   'evidence_scope':r.get('scope',r.get('native_providers_and_wire')),
                   'real_game_access':False,
                   'tests_run':r.get('tests_run',len(r.get('cases',[])) if type(r.get('cases')) is list else r.get('cases'))}

stamp=datetime.now().astimezone().isoformat()
report={'schema':'san14.parallel-development-progress.v1','updated_at':stamp,
    'mvp_scope':audit['mvp_definition'],'modules':modules,
    'weight_total':100,'estimated_work_completion_range':rounded,
    'percentage_is':'Subjective integration-work estimate, not playability, runtime verification rate, or forecast of days',
    'full_common_command_version_percentage':None,
    'full_version_reason':'Command-family scope and reusable native execution/event coverage are not yet measured; no reliable denominator.',
    'estimate_confidence':'low-to-medium','playable_mvp_available':False,
    'two_real_clients_roundtrip_verified':False,'real_game_access_this_turn':False,
    'audit':{'path':str(audit_path),'sha256':sha(audit_path)},
    'parallel_component_evidence':proofs,
    'release_blockers':audit['release_blockers'],
    'new_offline_components_do_not_remove_live_release_blockers':True}
(OUT/'并行开发与进度评估.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['并行开发与进度评估',f'更新：{stamp}','',
       '首个受限双人原型：约四成，粗略区间35%—50%。这是开发与接入工作量的主观估计，不是可玩率，不按测试条数折算，也不代表剩余天数。',
       '计算范围：固定受支持版本/剧本和两势力，赏赐、出征白名单，保留其他势力AI；A权威、B允许战斗过程分歧，旬末必须完整恢复；包含必需事件处理、窗口/无边框等待画面和明确故障恢复。',
       '包含常用内政、人才和外交的完整版本尚无可信百分比。通用入口可能批量复用，但命令族与事件覆盖范围还未盘清，不能在试玩版进度上随意打折。','',
       '本轮并行成果',
       '1. 加载后的大地图回归观察器：核对新规划状态、当前B身份、待处理加载请求等，区分“身份初始化有记录”和“回到规划地图”。该观察不代替完整世界、输入锁或实际画面验证。',
       '2. NativePort组合适配器：将总控制器接向已有本地通信通道，绑定持久加载意图和已验证文件；实际输入、完整世界及文件发布/配置仍须可信原生实现提供。缺少这些能力时拒绝放行，不伪造成功。',
       '3. 独立审计：按8个功能包、总权重100评估，逐项区分源码、独立测试与实机证据；本报告重新核对证据文件哈希。',
       '本轮仍未访问真实游戏、Steam存档或真实游戏窗口。新增离线模块没有消除下列实机门槛。','',
       '分项进度（同样是粗估）']
for m in modules:
    lines.extend([f"{m['name']}：{m['estimate_low']}%—{m['estimate_high']}%（权重{m['weight']}）",
                  '已有：'+'；'.join(m['implemented']),
                  '仍缺：'+'；'.join(m['remaining']),''])
lines.extend(['判断能否试玩的硬门槛',
    '一、B真实自动加载专用检查点，恢复B身份，完整共享业务状态核验通过。',
    '二、两个人类势力的AI/经济规则真实生效，日常菜单命令在原生执行前受控。',
    '三、两个真实客户端完成命令→准备→推演→旬末校正→下一旬，至少连续两旬。',
    '四、正确处理自然触发事件和既存任务。禁用招募、外交按钮不能保证没有事件；未知强制事件只能明确暂停/恢复，不能默认点击。',
    '五、断线、加载中断、重复消息不造成重复效果，玩家无需每旬手动替工具清理。','',
    '接下来先接入真实输入控制、完整世界及新地图证据，再将房间开始/命令/检查点入口串通。优先证明真实循环，不因离线组件多就跳到扩展全部菜单。',
    '完整独立测试路径、源文件哈希与审计依据见同名JSON。'])
(OUT/'并行开发与进度评估.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'published':str(OUT/'并行开发与进度评估.txt'),
                  'estimated_range':rounded,'all_sources_rehashed':True,'playable_mvp_available':False},ensure_ascii=False))
