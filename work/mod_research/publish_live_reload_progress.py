"""Publish verified milestones without treating fixture counts as completion %."""
from pathlib import Path
import argparse, hashlib, json
from datetime import datetime

P=Path(__file__).resolve().parent
OUT=P.parents[1]/'outputs'/'san14-link'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def evidence(path):
    return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('thread_result',type=Path)
    args=parser.parse_args()
    manual_path=P/'checkpoint_manual_reload_observe_runs/20261007-133644-956550/result.json'
    compare_path=P/'checkpoint-cycle-live/mainline-reload-final-before-20261007-1336-vs-mainline-reload-after-20261007-1338.json'
    force_path=P/'checkpoint-cycle-live/mainline-force-comparison-20261007-1338.json'
    manual,comparison,force,threads=map(read,(manual_path,compare_path,force_path,args.thread_result))
    assert manual['result']=='PASS' and manual['automatic_load_requests']==0
    assert not comparison['objects']['other_record_changes']
    assert comparison['all_48400_hex_serialized_fields_equal']
    assert not comparison['existing_save_files_changed']
    assert force['observed_table_equal'] and force['compared_physical_slots']==52
    assert threads['result']=='PASS_OBSERVATION_ONLY' and threads['stop_completed']
    assert threads['actual_slot_and_protection_restored'] and threads['two_stable_stopped_reports']
    assert threads['existing_save_files_unchanged'] and not threads['full_world_verified']
    observer=threads['observer'];n=observer['thread_count'];pairs=observer['matched_pairs']
    result=dict(schema='san14.live-reload-progress.v1',created=datetime.now().astimezone().isoformat(),
        manual_same_player_load_path_observed=True,automatic_guest_reload_proven=False,
        native_load_identity_transfer_proven=False,two_native_periods_proven=False,
        full_world_verified=False,game_map_cover_proven=False,playable_two_client_prototype=False,
        observed_user_thread_ids=n,observed_matched_user_calls=pairs,
        permanent_thread_affinity_proven=False,scheduler_fence_proven=False,
        evidence=[evidence(x) for x in (manual_path,compare_path,force_path,args.thread_result)])
    text=f'''实机加载接入进展（2026-10-07）

这轮完成了什么
用户手动读取34号档后，已完整观察到目标文件选择、世界读取完成、玩家身份初始化、战略界面初始化、回到可下令大地图。日期为203年8月中旬，君主仍为张鲁。观察工具已退出并恢复调试寄存器。

读档前后，783个已采样对象的业务字段、48,400个地格字段、52个势力的19,656字节字段投影一致；83份存档未被修改。显示对象地址随读档重建；全局随机状态有差异。这不是完整世界一致性证明，也不是B身份转换测试。

自动接入时找到的实际问题
观察器原先在安装时检查游戏“当前调度状态”指针。机器码证实该指针只在逐个更新状态期间设置，随后清空；这一检查应放在对应回调内。第一次安装因此拒绝，未发布更新钩子，事后核对游戏数据与存档未变。修正版保留其余上下文检查，并用独立进程测试覆盖这一差异。

修正后的短时真实观察完成：共{pairs}次地图更新完整配对，观察到{n}个线程ID。原更新函数、页面保护已恢复；模块保留以承接可能缓存的旧回调，没有执行读档、保存或游戏命令。这个短窗口不能证明未来线程归属固定，也不能替代原生调度屏障。

对主线的意义
手动读档的完整生命周期现在有实机证据；自动控制器不能依赖安装线程，也不能把临时调度指针当长期身份。后续必须在实际游戏回调中检查并提交一次加载，加载后重新识别新玩家界面。

仍未完成的试玩关卡
1. 将输入检查、原生加载请求、读取字节核验、B身份恢复接成一次真实自动往返。
2. 同一游戏进程连续完成第二次旬末同步，避免旧回调或旧消息影响新一旬。
3. 接上实际地图等待画面和输入限制，再进行两个真实客户端的连续一旬测试。
4. 把赏赐、出征等首批操作和两个人类势力规则接入上述循环。

当前仍不能称为可试玩的双客户端原型。不再用新增脚本或测试数量上调百分比，以这些实机验收关卡报告进度。
'''
    OUT.mkdir(exist_ok=True)
    (OUT/'实机加载接入进展.txt').write_text(text,encoding='utf-8-sig')
    (OUT/'实机加载接入证据.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    progress=OUT/'开发剩余工作评估.txt'
    old=progress.read_text(encoding='utf-8-sig')
    heading='最新实机进展（2026-10-07，完整手动加载与线程观察）：'
    if not old.startswith(heading):
        progress.write_text(heading+'手动34号档加载链已完整观察，修正了临时调度指针的安装期误判；线程观察结果见《实机加载接入进展.txt》。自动B重载、连续两旬及双客户端试玩仍待验收。下文百分比是旧阶段估计，本轮不按脚本数量更新。\n\n'+old,encoding='utf-8-sig')
    print(json.dumps({'report':str(OUT/'实机加载接入进展.txt'),'evidence':str(OUT/'实机加载接入证据.json')},ensure_ascii=False))

if __name__=='__main__':main()
