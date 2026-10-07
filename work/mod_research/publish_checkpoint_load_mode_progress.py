"""Publish a bounded native mode round trip without claiming a B load."""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs/san14-link'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def ref(path):
    return {'path': str(Path(path).resolve()), 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('result', type=Path)
    p.add_argument('--metadata-fixture', type=Path, required=True)
    p.add_argument('--launcher-fixture', type=Path, required=True)
    args = p.parse_args()
    result = load(args.result)
    assert result['schema'] == 'san14.checkpoint-load-mode-live.v1'
    assert result['result'] == 'PASS' and result['mode'] == 'execute' and result['load_mode_round_trip_verified']
    assert result['actual_hook_slots_and_pages_restored'] and result['existing_save_files_unchanged']
    assert result['known_coverage']['matched'] and not result['load_requested'] and not result['save_requested']
    metadata = load(args.metadata_fixture)
    launcher = load(args.launcher_fixture)
    assert metadata['result'] == launcher['result'] == 'PASS'
    after = result['after']
    graph = after['cache_graph']
    file_count = len(load(args.result.parent / 'known-after.json')['save_files'])
    assert graph['mode'] == 0 and graph['pending'] == -1 and after['pinned_user'] == result['before']['pinned_user']
    raw_proof = ROOT / 'checkpoint_load_byte_binding_shadow_20261006-213101-952726.json'
    buffer_proof = ROOT / 'checkpoint_target_metadata_buffer_shadow_20261006-214108-883620.json'
    dispatch_proof = ROOT / 'checkpoint_load_mode_dispatch_audit_20261006-214321-461404.json'
    for proof in (raw_proof, buffer_proof, dispatch_proof):
        assert load(proof)['result'] == 'PASS'
    progress = {'schema': 'san14.checkpoint-load-mode-progress.v1', 'updated': datetime.now().astimezone().isoformat(),
        'native_load_mode_round_trip': 'PASS_ONE_BOUNDED_REAL_ATTEMPT',
        'same_player_state_restored': True, 'date': after['context']['snapshot']['date'],
        'player': after['context']['snapshot']['player'], 'known_coverage': result['known_coverage'],
        'existing_save_files_unchanged': True, 'save_files_count': file_count, 'hook_slots_and_pages_restored': True,
        'cache_mode': 0, 'cache_pending_load': -1, 'normal_directory_indexed_count': len(graph['table']),
        'metadata_core_offline_only': True, 'metadata_production_adapter_completed': False,
        'B_load_completed': False, 'full_world_verified': False, 'real_game_cover_completed': False,
        'real_game_input_gate_completed': False, 'two_real_client_loop_completed': False,
        'native_gameplay_enabled': False,
        'evidence': [ref(x) for x in (args.result, args.result.parent / 'known-before.json',
             args.result.parent / 'known-after.json', args.metadata_fixture, args.launcher_fixture,
             raw_proof, buffer_proof, dispatch_proof)]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'B端原生加载接入进展.json').write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    text = f'''B端原生加载接入进展
更新：{progress['updated']}

本轮真实验证
在当前游戏进程执行一次原生读取菜单的进入与取消。游戏自己建立读取模式及存档列表，未选择任何槽位；正常执行一次无选择的界面更新后，发出一次原生取消，再回到同一个张鲁玩家操作层。
前后仍为203年8月中旬。已跟踪的783条对象记录、48,400地格序列化字段及随机状态核对一致，现有{file_count}份.s14文件均未改变。两个临时虚表入口及页保护均已恢复。没有加载文件、保存文件或推进时间。
当前原生读取模式为0，待加载槽位仍为-1；普通存档目录保留{len(graph['table'])}个有效索引。此次是在同一进程验证B将要使用的一个步骤，并没有接入第二个真实客户端。

实现中排除的风险
“取消菜单”只是排入一次退栈请求，同帧仍可能更新一次菜单。若先取消，再碰上原生取消输入，会重复退栈。新入口让原生更新先完成，再核对无槽位选择、无加载请求、无已有退出请求，最后取消；已有原生取消时不追加第二次。
普通存档的目录节点由四个分类链表持有，另有主链。专用检查点登记模块已改为识别这五条链，避免误删、误认普通存档节点，也不把暂未索引的原生节点当成错误。

已完成的离线接入代码
专用文件登记核心会持有经过完整读取验证的文件及字节，直接从同一buffer解析存档头，检查保留槽为空，然后转移新节点的所有权。解析成功、错误位、消费长度与头部内容都必须一致；仅头部相同不足以接受截断文件。
该核心已通过独立进程测试，但还没有生产适配器、真实串行边界及缓存代际跟踪，不会在游戏内登记或授权加载。
完整加载实际消耗的文件校验点，以及新世界中恢复刘备身份的时机，也已有真实机器码离线验证；仍需整段原生加载的实际测试。

当前链路和剩余顺序
A导出专用检查点：已真实通过。原生接口两遍完整读取同一文件：已真实通过。本次读取模式进出：已真实通过。
下一步是把新登记核心接到游戏内的受控边界，锁定专用文件及正数保留槽，随后执行一次原生加载，恢复B身份并核对新世界。
再接窗口/无边框下的旧地图等待画面及输入暂停，最后串成两个真实客户端的一旬循环。当前测试入口尚未隐藏原生菜单，不代表最终等待画面已经完成。
A端此前一次保存到返回约1.219秒；B完整加载及整轮同步延迟尚未测得。不能用菜单进出时间或文件读取时间代替B加载性能。
'''
    (OUT / 'B端原生加载接入进展.txt').write_text(text, encoding='utf8')
    marker = '本轮加载模式验证：'
    summary = (marker + '原生读取菜单进入、无选择更新、单次取消并返回同一张鲁操作层已真实通过。'
               f'已知游戏数据和{file_count}份存档未变，入口恢复。B专用文件的完整加载、身份恢复、等待画面及双机循环仍待接入。'
               '最新说明见《B端原生加载接入进展.txt》。\n\n')
    for name in ('开发剩余工作评估.txt', '地图等待层与独立检查点进展.txt', '保存返回与输入控制进展.txt'):
        path = OUT / name
        if path.exists():
            old = path.read_text(encoding='utf8')
            if not old.startswith(marker):
                path.write_text(summary + old, encoding='utf8')
    print(json.dumps({'result': 'PASS', 'report': str(OUT / 'B端原生加载接入进展.txt'), 'B_load_completed': False}))


if __name__ == '__main__':
    main()
