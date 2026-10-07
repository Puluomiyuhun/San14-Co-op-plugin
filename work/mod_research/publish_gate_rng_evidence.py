"""Publish bounded follow-up evidence, including the failed RNG restoration check."""
from datetime import datetime
import hashlib,json
from pathlib import Path
from analyze_combat_gates import next_rng
ROOT=Path(__file__).resolve().parent
TRACES=ROOT/'lockstep-traces'
OUT=ROOT.parents[1]/'outputs/san14-link'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
analysis=read(TRACES/'gate-rng-analysis.json')
end=read(TRACES/'sunjiao-and-end-results.json')
closeout=read(TRACES/'closeout-gate-rng.json')
assert not analysis['rng_chain_breaks'] and not analysis['rng_algorithm_mismatches']
assert len(analysis['rng_observations'])==89
assert len(analysis['c_d_gate_comparisons'])==19
assert all(not x['troop_differences'] and set(x['different_fields'])<={'global_rng'} for x in analysis['c_d_gate_comparisons'])
assert all(not x['sampled_record_changes_excluding_known_runtime_pointer'] and x['focused_state_equal'] and x['person_task_sample_equal'] for x in end['end_comparisons'].values())
assert closeout['result']=='SAMPLED_GAMEPLAY_RESTORED_RNG_DIFFERS'
assert closeout['debugger_attached'] is False and closeout['rng_state_rewritten'] is False
old=closeout['comparison']['random_inputs_a']['global_18eb8b0']
new=closeout['comparison']['random_inputs_b']['global_18eb8b0']
assert next_rng(old)==new
manifest=[]
paths=[TRACES/name/file for name in ('gate-run-c','rng-run-d') for file in ('trace.jsonl','before.json','metadata.json')]
paths += [ROOT/n for n in ('observe_combat_gate.cpp','observe_combat_gate.exe','observe_rng_gate.cpp','observe_rng_gate.exe',
    'combat-gate-fixtures.json','rng-gate-fixtures.json','rng-global-accesses.json','disasm-3aa7c0.txt',
    'survey-16c640.txt','survey-3b36b0.txt','survey-3b1e20.txt','survey-3b1d20.txt','survey-2da9a0.txt','survey-2d91a0.txt',
    'survey-2922b0.txt','survey-2a3ce0.txt')]
for p in paths:
    manifest.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
report={
    'schema':'san14.lockstep-followup.combat-gates-rng.v1','created':datetime.now().astimezone().isoformat(),
    'result':'ADDITIONAL_DIVERGENCE_PATHS_OBSERVED_ORIGINAL_A_CAUSE_UNRESOLVED',
    'comparison':analysis,'sunjiao_and_end_states':end,
    'restoration':{**closeout,'extra_rng_transition':{'baseline':old,'restored_observed':new,'matches_one_prng_step':True,
        'caller_known':False,'scope':'Match of values, not a trace of a specific post-load call. Read-time/state-reset boundaries were not instrumented.'}},
    'diagnostic_metadata':{n:read(TRACES/n/'metadata.json') for n in ('gate-run-c','rng-run-d')},
    'diagnostic_baselines':{n:read(TRACES/n/'before-diagnostics.json') for n in ('gate-run-c','rng-run-d')},
    'c_after_and_restore_diagnostics':{n:read(TRACES/'gate-run-c'/n) for n in ('after-diagnostics.json','restored-diagnostics.json')},
    'dry_attach_detach_logs':{n:[json.loads(x) for x in (TRACES/n/'trace.jsonl').read_text().splitlines()] for n in ('gate-dry-a','rng-dry-a')},
    'infrastructure_fixtures':{n:read(ROOT/n) for n in ('combat-gate-fixtures.json','rng-gate-fixtures.json')},
    'manifest':manifest,
    'conclusions_zh':[
        '原A首批伤害未执行的根因尚未抓到，不能把待处理标志残留直接定为原因。',
        '原B/C/D旬末抽查记录一致，而所监测全局随机状态不同；并非全部阶段/动画已验证。',
        'D轮首次与C对应采样不同的已观测随机消费，返回地址为0x2DA9C3；其上层脚本身份未知。',
        '0x3B3779路径也消耗同一随机状态，下游疑似空间语音/声音播放；该语义为静态推断，不能据此认定该全局状态仅供表现使用。',
        '孙皎起点已配置火矢，用户不确定过去是否发动；没有完整战法事件日志，不能认定战法分叉。',
        '最后一次读档的局面抽查恢复，但随机状态多一步对应值；严格校验未通过，未篡改游戏状态来使检查通过。'
    ],
    'next_steps_zh':[
        '记录完整读档至规划地图期间的随机消费，捕获上层脚本/调用者。',
        '为漏算复现增加交战记录身份、处理阶段与会影响计算的运行时对象字段。',
        '为战法增加发动者、目标、战法ID、逻辑日期子步和实际结算日志。',
        '分类确认后再决定逻辑与表现随机如何隔离；尚不全局替换随机函数或清零等待标志。'
    ],
    'limits':['Single game process, not two clients','Partial world and event coverage','Hardware debugger changes wall-clock scheduling',
              'C and D instrument different locations','No live game code/data writes, injected DLLs or game calls this follow-up']
}
p=OUT/'读档推演分叉追查第二轮证据.json'
p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert read(p)==report
print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'result':report['result'],'closeout':closeout['result'],
                  'save34_matches_backup':closeout['save34_sha256']==closeout['backup_sha256']},ensure_ascii=True))
