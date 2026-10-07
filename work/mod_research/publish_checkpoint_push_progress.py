"""Publish the passing bounded A export; do not enable native gameplay."""
from pathlib import Path
from datetime import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs/san14-link'
RUN = ROOT / 'checkpoint_push_runs/20261006-203111-687580'
ARCHIVE = ROOT / 'checkpoint_push_archives/20261006-204306-581930/result.json'


def load(p):
    return json.loads(p.read_text(encoding='utf8'))


def ref(p):
    return {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def main():
    result = load(RUN / 'result.json')
    archive = load(ARCHIVE)
    assert result['result'] == 'PASS' and result['native_save_complete']
    assert result['completion_evidence']['complete']
    assert archive['result'] == 'PASS' and archive['sha256'] == result['file']['sha256']
    adapter = result['adapter']
    duration = (adapter['returned_at'] - adapter['queued_at']) / 1000
    worker = (adapter['finalized_at'] - adapter['queued_at']) / 1000
    assert duration == 1.219 and worker == .954
    report = {
        'schema': 'san14.checkpoint-push-progress.v1',
        'updated': datetime.now().astimezone().isoformat(),
        'native_A_export': 'PASS_ONE_BOUNDED_REAL_ATTEMPT',
        'queue_to_same_User_seconds': duration,
        'queue_to_finalizer_seconds': worker,
        'B_load_latency_measured': False,
        'full_sync_latency_measured': False,
        'filename': 'mppush01.s14', 'file': result['file'],
        'parsed_date': archive['date'], 'ruler_name': archive['ruler_name'],
        'known_coverage': result['completion_evidence']['coverage'],
        'existing_saves_unchanged': result['completion_evidence']['ordinary_saves_unchanged'],
        'hook_slots_and_protection_restored': result['hooks_restored_from_memory'],
        'old_failed_export_remains_failed_and_retired': True,
        'native_full_file_identity_verified': False,
        'B_load_completed': False, 'full_world_verified': False,
        'real_game_cover_completed': False, 'real_game_input_gate_completed': False,
        'two_real_client_loop_completed': False,
        'native_gameplay_enabled': False,
        'evidence': [ref(p) for p in (
            RUN / 'result.json', RUN / 'trace.jsonl', RUN / 'known-before.json', RUN / 'known-after.json',
            ROOT / 'checkpoint_push_once.intent', ARCHIVE,
            ROOT / 'checkpoint_push_fixtures/20261006-202955-491965/result.json')],
    }
    receipt_path = ROOT / 'checkpoint_push_export_receipt_20261006-203111-687580.json'
    if receipt_path.exists():
        receipt = load(receipt_path)
        assert receipt['result'] == 'A_EXPORT_VERIFIED_GUEST_UNBOUND'
        report['A_export_receipt'] = ref(receipt_path)
        report['guest_bound'] = False
    read_path = ROOT / 'native_file_identity_runs/20261006-211040-957998/result.json'
    read_result = load(read_path)
    assert read_result['result'] == 'PASS' and read_result['mode'] == 'read'
    assert read_result['two_observed_native_reads_matched'] and read_result['actual_hook_slots_restored']
    assert read_result['existing_files_unchanged'] and read_result['known_coverage']['matched']
    reader = read_result['adapter']
    assert reader['readReturns'] == [274880, 274880] and reader['sizes'] == [274880] * 3
    assert reader['nativeSha256'] == [archive['sha256']] * 2 and reader['localPinReleased'] == 1
    trace = load(read_path.parent / 'trace.json')
    assert len(trace) >= 2 and trace[-2]['adapter'] == trace[-1]['adapter'] == reader
    report.update(native_full_file_identity_verified=True,
        native_file_identity_scope='Two observed reads through A process Storage interface; not a future B load or persistent lock.',
        native_read_result=ref(read_path), native_read_file_size=274880, native_read_count=2,
        native_read_known_coverage=read_result['known_coverage'], future_load_byte_identity_proven=False,
        native_read_once=ref(ROOT / 'native_file_identity_read_once.json'),
        metadata_mode_audit=ref(ROOT / 'private_checkpoint_metadata_mode_audit.json'))
    report['native_read_launcher_version_note'] = ref(ROOT / 'native_file_identity_review_version_note.json')
    report['native_read_launcher_offline_hardening'] = ref(ROOT / 'native_file_identity_launcher_hardening_test_20261006-212417-650399.json')
    report['post_review_native_probe_rerun'] = False
    (OUT / '原生检查点导出进展.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    text = f'''原生检查点导出进展
更新：{report['updated']}

已通过的真实步骤
新入口在保留原玩家操作层的情况下，提交一次原生保存，由游戏自己的保存线程完成，再返回同一个玩家操作层。实测仍为203年8月中旬、张鲁，没有意外推进。
生成独立文件mppush01.s14，共274,880字节，约268KiB。完整SHA256为{archive['sha256']}。原有81份.s14文件哈希保持不变；其中包含之前失败试验留下的取证文件。配置及附加存档文件也未变。
从提交保存到原生收尾约0.954秒，到同一玩家操作层恢复约1.219秒；外部工具另观察了约1秒的文件稳定期。这只是当前测试局的一次A端保存数据，不是B加载耗时，也不是网络或完整联机等待时间。

结果核对
前后已跟踪的783条对象记录全部字节一致，48,400个地格的已确认序列化字段一致，全局及已知世界随机状态一致，已知分配器计数一致。观察用的两个虚表槽及页保护均已恢复，模块保持无钩子的常驻状态直至游戏退出。
新文件已另行归档；在隔离环境执行游戏原有头部解析代码，确认日期为203年8月11日、张鲁。只替换了读取原始字节的流函数，没有执行完整世界加载。已知字段比较和头部成功不等于全部隐藏状态覆盖。

旧失败保持原判定
旧mpckpt01.s14试验使用替换玩家层的入口，曾意外推进一旬，仍为失败且执行器保持禁用。其文件、日志和一次性记录保留。本次mppush01来自不同的状态压入入口和新的一次性记录，不复用旧失败结果。
之前正常保存菜单取消的观察日志仍为INCOMPLETE；这次完整保存的PASS来自独立记录，并未修改旧记录。

接下来接入B
游戏自身读取已实际通过：先做不调用存储接口的空运行，再通过原生Storage接口读取两遍。每次返回274,880字节，三次长度查询一致，两次完整SHA和逐字节比较都与归档相同。经探针转发的原生更新调用恰好执行一次，原入口和页保护恢复，所有.s14文件及已跟踪783记录、48,400地格、随机状态在检查前后一致。文件读取句柄已释放；没有加载或推进。
上述是A进程这两次读取的事实，不能替代B加载时的文件绑定。B仍需在加载开始前绑定专用文件、正数保留槽和B身份，加载成功后验证新世界实例、日期及B身份，再允许操作。
不能先请求34号档再临时替换文件名。真实B进程、房间轮次、准备冻结等证据也不能从这次A单机测试补造。
历史读取校验通过不等于未来加载已消费相同字节；在真正加载时仍需保持文件身份和实例关联。

原生加载顺序的新证据
新增7项隔离执行检查确认：现有pending加载入口只在缓存处于读取模式时响应。当前保存结束留下的mode1并不满足此条件。
原生保存/读取列表的构造函数会先销毁旧缓存节点、清空槽位和pending，再设置新模式。因此必须先通过正常原生生命周期切到读取模式，之后再登记专用文件；如果先登记再切模式，刚登记的目标会被清掉。
这部分尚为离线代码证据，没有执行新的模式切换、登记或加载。旧metadata core仍绑定旧失败文件，不直接用于新文件。

尚未完成
1. B自动加载这份专用文件，恢复刘备身份并回到正确的新地图。
2. 真实地图画面覆盖、输入隔离和镜头恢复；当前仍不能保证不露出原生读档页。
3. 双人类势力规则、持续命令、正式事件，以及两个真实客户端连续多旬。
这些仍是原生接入和联调工作，当前不是可直接发给朋友安装的联机MOD。下一步优先完成导出—传输—B恢复的真实闭环，再优化耗时。
'''
    (OUT / '原生检查点导出进展.txt').write_text(text, encoding='utf8')
    # Keep earlier findings verbatim under a clearly dated history boundary.
    marker = '最新状态：新的A端专用导出已通过一次真实验证。'
    for name in ('保存返回与输入控制进展.txt', '地图等待层与独立检查点进展.txt', '开发剩余工作评估.txt'):
        path = OUT / name
        previous = path.read_text(encoding='utf8')
        if marker in previous:
            latest = '原生完整读取也已实测通过：A进程连续两次读取274,880字节并与归档逐字节一致，原入口恢复，已知游戏数据及存档未变。B原生加载仍待接入；模式切换必须先于专用文件登记。\n'
            if latest not in previous:
                path.write_text(latest + previous, encoding='utf8')
            continue
        path.write_text(marker + '\n203年8月中旬、张鲁，返回同一玩家操作层；已知对象/地格/随机状态及原有存档不变。提交到返回约1.219秒，仅为A保存耗时。B专用文件加载、真实等待画面和完整双机循环仍待完成。\n最新完整说明见同目录《原生检查点导出进展.txt》。\n\n以下为导出成功之前的阶段记录，其中“尚未完成新导出”只描述当时状态；旧失败及不完整日志的判定保持不变。\n\n' + previous, encoding='utf8')
    print(json.dumps({'result': 'PUBLISHED', 'export': str(OUT / '原生检查点导出进展.txt'), 'native_gameplay_enabled': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
