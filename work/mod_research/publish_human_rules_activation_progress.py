"""Publish current controlled-test state without promoting fixtures to live proof."""
from pathlib import Path
from datetime import datetime
import hashlib,json

P=Path(__file__).resolve().parent
O=P.parents[1]/'outputs/san14-link'
def ref(path):
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def read(path):return json.loads(path.read_text(encoding='utf8'))

def main():
    claim=P/'human_rules_activation_live_v4_2904_134358355367489493_once.json'
    c=read(claim);run=Path(c['run'])
    events=[json.loads(s)for s in (run/'events.jsonl').read_text(encoding='utf8').splitlines()]
    kinds={e['kind']for e in events}
    installed='install_complete'in kinds and 'restore_complete'not in kinds
    restored='restore_complete'in kinds
    captured='round_captured'in kinds
    closed='closed_with_sources_original'in kinds
    uncertain=any(e['kind']in ('OWNER_ERROR','RECOVERY_REQUIRED_OWNER_RETAINED','NATIVE_FAULTED_RESTART_ONLY')for e in events)
    assert not uncertain,'Do not publish optimistic progress for an uncertain owner'
    names=['human_rules_activation_v2_handoff.json','human_rules_activation_v2_independent_review.json',
        'human_rules_activation_publish_v2_handoff.json','human_rules_activation_publish_v2_independent_review.json',
        'human_rules_activation_live_session_v4_independent_review.json',
        'checkpoint_fresh_save_handoff.json','checkpoint_fresh_save_independent_review.json',
        'checkpoint_ready_input_handoff.json','checkpoint_task_completion_handoff.json']
    proof={n:ref(P/n)for n in names}
    for name in ('human_rules_activation_live_round_handoff.json','human_rules_activation_live_round_independent_review.json',
                 'human_rules_income_count_offline_analysis.json'):
        if(P/name).is_file():proof[name]=ref(P/name)
    closeout=read(run/'closeout.json')if(run/'closeout.json').is_file()else None
    proof['live_claim']=ref(claim)
    for n in ('prepared.json','prepared-report.json','install-publisher-result.json','install-report.json',
              'round-report.json','round-state.json','restore-publisher-result.json','restore-report.json'):
        if(run/n).is_file():proof[n]=ref(run/n)
    stamp=datetime.now().astimezone().isoformat(timespec='seconds')
    state={'created':stamp,'pid':c['pid'],'birth':c['birth'],'run':str(run),'six_sources_installed':installed,
           'six_sources_restored':restored,'native_round_captured':captured,'room_closed':closed,
           'real_game_processes':1,'diagnostic_loopback_tls_seats':2,'real_guest_game':False,
           'full_world_verified':False,'user_restored34_verified':closeout is not None,'evidence':proof,
           'next':'Await user advance one period from current slot34; no save/load while installed'if installed and not captured else
                  'Inspect real round and restore sources before any manual load'if installed else
                  'Rules sources restored; verify manual restore34 separately'if restored else'Preparation only; installation pending'}
    if closeout:
        state['next']='No user action pending. Real single-game rules period completed and slot34 restored. Continue economic-call attribution and remaining checkpoint/input integration.'
        state['real_round_summary']={k:closeout[k]for k in ('actual_ai_calls','ai_bypassed','ai_original','income_predicate_calls','final_date','final_player','period_save_files_changed')}
    archive=P/'human_rules_activation_progress_publications'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    archive.mkdir(parents=True)
    (archive/'evidence.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    live=('双人规则已经安装到当前真实游戏，正在等待用户推进一旬。尚未取得规则启用后的整旬结果。'if installed and not captured else
          '已采集规则启用后的真实整旬日志，结果需要结合本轮计数核验。'if captured else
          '规则模块已完成准备；尚未安装六个入口。')
    if restored:live+=' 六个入口已撤回。'
    if closed:live+=' 本地诊断房间已关闭，模块保留到游戏退出。'
    if closeout:
        live='真实游戏中的双人规则已完成一旬测试：120次AI入口调用，8次按玩家势力规则跳过，112次继续执行原生逻辑；1044次收入归属判断全部返回。活动调用、挂起、异常均为0。六处入口已撤回，调试器与诊断房间已退出。用户恢复34号档后，783条抽查记录仅53个部队显示对象地址重建，其余已覆盖记录、任务字段、48400格序列字段和随机状态恢复一致。并非完整世界证明。'
    content=f'''双人规则与旬末同步接入进展（{stamp}）

当前实机阶段
{live}
这是一个真实游戏进程连接两个本机诊断席位，尚非两台电脑各运行一份游戏。测试绑定张鲁与刘备，目标是双方主军团不受AI代替决策，委任军团和其他势力仍走原逻辑，两处收入判断统一按双方人类势力处理。入口次数不等于具体命令数量，收入判断次数不等于发钱笔数。

本轮排除的问题
房间要求先完成双方选势力，再分别确认。已修正顺序。游戏中的world+165D是官爵派生的数组数量，张鲁为2、刘备为1；旧规则错误地要求恒为1。根据原生生成、消费路径删除了这项错误的空闲条件，未修改游戏中的该字段。此前的失败尝试均保留，未复用旧执行记录或重试已拒绝模块。
修正后的规则模块18项独立进程测试通过，安装/撤回模块16项通过。修复了启动日志参数名冲突并逐项检查11处事件调用后，本轮实机完成了规则启用测试。上一轮816次调用是纯转发证据，本轮启用规则后实际记录到1164次入口调用，两者分开保留。

收入调用次数待进一步归因
本轮1044次中524次判断为人类势力、520次判断为AI势力。比上一轮纯转发696次多348次，原码两条分支本身不会直接重入判断点；上层预测、结算调度或AI工作量变化仍需逐来源、势力及阶段记录区分。不能由次数推断重复发钱，也尚未证明经济数值完全一致。原34号档哈希未变；正常推进更新了autosdexSC08.s14。

其他开发进展
1. A端生成本轮新存档：完成同一组件连续处理两次独立请求、原生保存入口和收尾观察、文件占用保护及双重读取核对，26项组件测试通过。测试使用替身业务和诊断文件；还没有通过这套新组件实际生成两份SAN14旬末档。
2. B端连续加载：新增三个实际线程收尾位置的捕获和Title入口观察，6项独立进程用例均覆盖两代。仍需把父任务收尾、Title创建与启动接进生产安装流程，并实际连续加载两份不同存档。
3. 准备后等待：已补上主规划回调以外的两个菜单消费入口，12项原生桥测试、2项归档机器码验证、3项房间拒绝测试通过。仍未覆盖全部输入路径，因此尚不允许据此放行完整Ready。

双人原型尚需通过
本轮已完成双方势力保护入口的真实整旬测试。剩余重点是收入调用归因及数值对照；完整准备/命令排空与输入等待；A每旬新档导出；B同一进程连续两次加载并保留自身势力及核对世界；最后连接异地两台电脑，验证等待画面并逐项加入赏赐、出征等操作。
目前尚未形成完整可玩的双人循环，不能把组件测试数量换算为可信完成百分比。
当前已恢复34号档，不需要用户继续手动操作。
'''
    for name in ('双人规则实机接入进展.txt','三个门槛接入进展.txt','双机测试准备进展.txt','开发剩余工作评估.txt'):
        dest=O/name
        if dest.exists():(archive/name).write_bytes(dest.read_bytes())
        dest.write_text(content,encoding='utf8')
    (O/'双人规则实机接入证据.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    resume=P/'mainline_20261007_live_resume.json';r=read(resume);r['human_rules_activation_live']=state
    temp=resume.with_suffix('.tmp');temp.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(resume)
    print(json.dumps({'result':'PUBLISHED','live_installed':installed,'round_captured':captured,'restored':restored,'path':str(O/'双人规则实机接入进展.txt')},ensure_ascii=True))

if __name__=='__main__':main()
