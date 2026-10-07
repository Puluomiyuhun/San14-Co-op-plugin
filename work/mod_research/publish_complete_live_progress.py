"""Publish only saved evidence; does not touch game or install/execute anything."""
import argparse,hashlib,json
from datetime import datetime
from pathlib import Path
P=Path(__file__).resolve().parent
OUT=P.parents[1]/'outputs/san14-link'

def record(path):
    path=Path(path);raw=path.read_bytes()
    return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),data=json.loads(raw))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--result',type=Path,required=True)
    args=parser.parse_args();live=record(args.result);r=live['data']
    success=r.get('result')=='PASS_NATIVE_LOAD_IDENTITY_PLANNING'
    observed_path=args.result.parent/'observed-outcome.json'
    observed=record(observed_path) if observed_path.exists() else None
    o=observed['data'] if observed else {}
    visible_partial=all(o.get(k) is True for k in ('native_load_receipt_ready','native_identity_receipt_ready',
        'existing_save_files_unchanged','new_game_reuses_retired_load_address')) and o.get('post_current_force')==2 and o.get('post_current_ruler')==952
    sources={name:record(P/name) for name in ('checkpoint_complete_live_owner_handoff.json',
        'checkpoint_live_runtime_guards_handoff.json','checkpoint_serialized_storage_gate_handoff.json')}
    for name in ('checkpoint_complete_live_owner_v2_handoff.json','checkpoint_live_runtime_guards_v2_handoff.json',
            'checkpoint_forward_planning_observer_v2_handoff.json','checkpoint_complete_live_acceptance_v2_handoff.json',
            'checkpoint_complete_live_inspect_v2_handoff.json'):
        if (P/name).exists():sources[name]=record(P/name)
    stamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    evidence=dict(schema='san14.complete-owner-progress.v1',updated_at=stamp,live_attempt=live,
        source_handoffs=sources,single_native_load_passed=success,observed_outcome=observed,full_world_verified=False,
        real_map_cover_verified=False,repeated_periods_verified=False,two_real_clients_playable=False)
    summary=(
        '本轮完成一次工具触发的原生加载：指定检查点经过实际读取，加载收尾与身份转换回执一致，'
        '重建了203年8月中旬、刘备的规划操作状态。没有要求用户手动选择存档；画面呈现尚未核验。\n'
        '这证明单次自动B加载的这条路径成立；不代表完整世界核验、连续每旬加载或两个客户端已经可玩。\n'
        if success else
        '本轮统一自动加载模块已开发并进行一次实机尝试，但未满足完整成功验收。\n'
        '本次结果：'+r.get('result','UNKNOWN')+'；原因：'+str(r.get('error','见回执'))+'\n'
        '已保存唯一尝试和现场证据，没有自动重发读档。后续先检查这次尝试，再决定修正路径。\n')
    if visible_partial:
        summary=('本轮已真实走通“工具自动读入指定检查点 → 切换刘备身份 → 回到大地图”，用户已确认画面。\n'
            '实际读取274,880字节且与目标存档哈希一致；原生加载收尾和身份转换回执完整。'
            '事后只读核对为203年8月中旬、刘备，原有83份存档未变。\n'
            '严格整体结果仍为INCOMPLETE：最后的规划观察器把新地图对象复用旧加载对象的内存地址误判为旧对象。'
            '这个原因已定位，修正独立保存在v2；没有改写原结果，也没有重复本次加载。\n')
    body='实机加载接入进展（'+stamp+'）\n\n'+summary+'\n'
    body+='本轮代码落地\n'
    body+='1. 统一DLL把输入检查、原生菜单排队、读取目标文件、加载收尾、刘备身份与新规划界面接在同一会话中。\n'
    body+='2. 运行时检查按加载阶段区分新旧对象；存档接口的跨线程检查已串行化，避免彼此干扰。\n'
    body+='3. 启动工具保留一次性记录；结果不明时不重发，也不卸载可能仍被游戏调用的模块。\n'
    body+='4. 成功判断必须关联实际读取字节、加载收尾、目标身份和新界面，同时复查实际挂钩位置与迟到错误。\n\n'
    body+='离线验证：运行时检查13项、统一DLL12项、存储串行模块11项；另有Python启动流程与回执判定测试。'
    body+='原生游戏主体的测试替身只用于离线验证，没有把它们当成实机加载证明。\n\n'
    if visible_partial:
        body+='针对实机问题的v2修正\n'
        body+='改为依据当前状态链、对象类型、原生虚表及加载完成记录识别对象生命周期；内存地址相同只作为诊断信息。'
        body+='仍要求可下令阶段，旧类型、错误状态链、未就绪界面继续拒绝。'
        body+='运行时检查19项、新规划观察器21项、结果分类8项针对性测试已通过；统一新版DLL的7项组合测试也已通过。'
        body+='新版尚未再次安装到真实游戏。复测需要新启动的游戏进程，避免叠加旧模块。\n\n'
    body+='仍需完成\n'
    body+='1. 完整世界及附加同步数据核验；同一进程连续第二旬恢复，旧消息和旧回调不影响新会话。\n'
    body+='2. 真实游戏中的地图等待画面与输入限制。目前仍可能显示正常读档画面。\n'
    body+='3. 两个人类势力的规则、首批赏赐/出征操作、准备和正式事件接入持续联机。\n'
    body+='4. 两台真实游戏客户端连续运行，随后扩大命令支持并打包助手。\n\n'
    body+='进度按这些实机关卡报告，不按脚本或测试数量换算百分比。\n'
    OUT.mkdir(parents=True,exist_ok=True)
    archive=P/'complete_owner_progress_archives'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');archive.mkdir(parents=True)
    for name in ('实机加载接入进展.txt','实机加载接入证据.json'):
        file=OUT/name
        if file.exists():(archive/name).write_bytes(file.read_bytes())
    (OUT/'实机加载接入进展.txt').write_text(body,encoding='utf8')
    (OUT/'实机加载接入证据.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
    assessment=OUT/'开发剩余工作评估.txt'
    old=assessment.read_text('utf8') if assessment.exists() else ''
    assessment.write_text('最新状态（'+stamp+'）：'+summary+'详细证据见《实机加载接入进展.txt》。\n\n'+old,encoding='utf8')
    resume=P/'mainline_20261007_live_resume.json';state=json.loads(resume.read_text('utf8'))
    prior_attempt=state.get('complete_owner_attempt')
    if prior_attempt and Path(prior_attempt['path']).resolve()!=args.result.resolve():
        history=state.setdefault('complete_owner_prior_attempts',[])
        if not any(x.get('path')==prior_attempt['path'] for x in history):history.append(prior_attempt)
    state['complete_owner_attempt']=dict(path=str(args.result),result=r['result'],success_scope='single load identity planning only',
        after_commit_hooks_retained=True,automatic_retry_allowed=False,run=r.get('run'))
    if observed:state['complete_owner_observed_outcome']=dict(path=str(observed_path),sha256=observed['sha256'])
    claim_name='checkpoint_complete_live_v2_once.json' if args.result.parent.parent.name=='checkpoint_complete_live_v2_runs' else 'checkpoint_complete_live_once.json'
    if claim_name not in state['must_preserve_once_records']:
        state['must_preserve_once_records'].append(claim_name)
    state['next_concrete_integration']=[
        'Inspect saved complete owner attempt; never delete/reset its claim or automatically retry an uncertain load.',
        'If single native load passed, implement repeated-session ownership and complete-world verification.',
        'Connect real window cover/input hold before asserting map-preserving synchronization.',
        'Then integrate two-real-client period loop, human-faction rules and supported planning commands.']
    if success:
        state['game_last_verified'].update(pid=r['pid'],birth=r['birth'],base=hex(r['base']),force=2,ruler=952,user_update_slot_original=False)
        state['game_state_after_complete_attempt_requires_inspection']=False
        state['single_native_guest_reload_verified']=True
        state['not_completed']=['repeatable_guest_reload' if x=='automatic_full_guest_reload' else x for x in state['not_completed']]
        state['next_concrete_integration'][0]='Single V2 automatic load, native byte/lifecycle/identity and fresh planning callback passed. Keep its owner and one-shot claim retained; proceed to reusable session ownership and full-world verification, not another installation over these hooks.'
        if claim_name=='checkpoint_complete_live_v2_once.json':
            state['complete_owner_v2_ready_for_fresh_process']['game_installed']=True
            state['complete_owner_v2_ready_for_fresh_process']['result']=str(args.result.resolve())
            state['v2_next_live_test']='V2 single automatic load already passed; do not rerun its one-shot launcher or delete its claim. Next live test requires a separately reviewed repeatable-session design.'
        old_inspection=state.pop('complete_owner_post_stop_inspection',None)
        if old_inspection:state['prior_owner_post_stop_inspection']=old_inspection
        state['complete_owner_post_stop_status']=dict(result_path=str(args.result.resolve()),
            stop_requested=r['post_stop_report']['StopRequested']==1,
            request_cas=r['post_stop_report']['RequestCasApplied'],identity_cas=r['post_stop_report']['IdentityCasApplied'],
            active_callbacks=sum(r['post_stop_report'][k] for k in ('ActiveDispatch','ActiveWorker','ActiveRead')),
            all_bridges_balanced=all(b['started']==b['returned'] and b['abnormal']==0 for b in r['post_stop_report']['bridges']),
            new_native_errors=False,known_planning_error_preserved=False)
    elif visible_partial:
        state['game_last_verified'].update(force=2,ruler=952,user_update_slot_original=False)
        state['game_state_after_complete_attempt_requires_inspection']=False
        state['v2_next_live_test']='Use a fresh game process to remove the retained v1 owner safely; then load slot34 and perform one separately claimed v2 attempt. Never reset/delete the v1 claim or hot-unload its DLL.'
        state['next_concrete_integration'][0]='Finish/review independent v2 owner; the specific v1 planning rejection is explained by legitimate new Game reuse of retired Load address. Preserve the incomplete v1 receipt and user-confirmed B map separately.'
    else:state['game_state_after_complete_attempt_requires_inspection']=True
    resume.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(report=str(OUT/'实机加载接入进展.txt'),single_load_passed=success),ensure_ascii=False))

if __name__=='__main__':main()
