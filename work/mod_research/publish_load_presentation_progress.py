"""Consolidate frozen offline evidence; no game access or native load."""
from pathlib import Path
from datetime import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent.parent / 'outputs' / 'san14-link'
EVIDENCE = {
    'actual_load_bytes_observer': 'checkpoint_cc_load_observer_fixtures/20261007-013536-907632/result.json',
    'load_lifecycle_receipt': 'checkpoint_cc_load_lifecycle_fixtures/20261007-015030-142930/result.json',
    'atomic_title_pair': 'checkpoint_identity_pair_commit_fixtures/20261007-013334-532962/result.json',
    'native_title_lifetime': 'checkpoint_title_worker_lifetime_shadow_20261007-013910-457023.json',
    'own_window_map_cover': 'checkpoint_map_cover_runs/20261007-014532-177786/result.json',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    now = datetime.now().astimezone().isoformat()
    evidence = {}
    for name, relative in EVIDENCE.items():
        path = ROOT / relative
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['result'] == 'PASS', name
        sources = data.get('source_sha256', {})
        if name == 'native_title_lifetime':
            sources = {'checkpoint_title_worker_lifetime_shadow.py': sources}
        for source, digest in sources.items():
            assert sha(ROOT / source) == digest, (name, source, 'changed since evidence')
        evidence[name] = {
            'path': relative, 'sha256': sha(path), 'result': data['result'],
            'case_count': len(data['cases']) if 'cases' in data else None,
            'scope': data.get('scope', data.get('native_result', {}).get('scope', 'Machine-code VM, no real game access')),
        }
    cover = json.loads((ROOT / EVIDENCE['own_window_map_cover']).read_text(encoding='utf-8'))['native_result']
    assert cover['capture_times']['unchanged'] > cover['capture_times']['background']
    assert cover['capture_times']['revealed'] > cover['capture_times']['failure']
    for key, cutoff in cover['minimum_frame_times'].items():
        assert cover['capture_times'][key] > cutoff
    contract = ROOT / 'checkpoint_load_integration_contract.json'
    report = {
        'schema': 'san14.immediate-sync-map-wait-progress.v1', 'updated_at': now,
        'result': 'OFFLINE_COMPONENTS_VERIFIED_INTEGRATION_PENDING',
        'evidence': evidence, 'current_source_hashes_verified': True,
        'integration_contract': {'path': contract.name, 'sha256': sha(contract)},
        'reward_target': 'Host commits once, sends complete ordered effects; client applies and refreshes immediately without waiting for the next period. Visible information follows native game rules.',
        'reward_continuous_two_client_sync_verified': False,
        'period_end_target': 'Full native checkpoint plus multiplayer metadata; B pauses world input, displays old map pixels during controlled load, restores B identity/camera, verifies new world/frame, then resumes.',
        'actual_game_cover_integrated': False,
        'game_load_started_this_turn': False,
        'two_client_roundtrip_verified': False,
        'b_load_latency_measured': False,
        'superseded_cover_timing_evidence': 'checkpoint_map_cover_runs/20261007-013821-202482/result.json had no strict frame-time gates. Preserved as historical; not used here.',
        'economic_note': 'The nine-city identity-dependent income-preview differences were already reproduced offline; the shared-human rule still awaits live integration. See 经济规则适配进展.txt.',
    }
    text = f'''即时同步与地图等待加载进展
更新：{now}

赏赐以后B什么时候看到
目标是A确认赏赐并成功执行后，就把这笔操作的完整结果发给B，不等下一旬。同步包括忠诚、金钱、行动力和本旬赏赐标记等相关变化，不能只同步一个属性；同一笔操作重发不会再次扣款。
B收到并应用后刷新相应界面。若原生规则允许B查看该武将忠诚，就显示新值；联机不额外开放原来不可见的情报。这里的“即时”包含网络、执行和界面刷新耗时，并非零延迟。
受控赏赐调用已经有实机证据，但正常菜单操作的持续捕获、真实两端的结果传播和界面刷新尚未连通。当前不能把目标流程称作已经可用。

旬末如何交接
A完成本旬结算后，给B发送完整原生检查点以及房间、势力、命令位置等联机附加信息。B加载A的世界，仍恢复成B自己的势力和菜单；镜头保留B自己的位置。
传输和校验可以后台执行。真正替换游戏世界时必须停住B的操作，旧地图对象会被销毁，所以等待期间保留的是旧地图画面。目标显示顺序是：原地图 → 原地图上显示“正在同步” → B的新地图，不让玩家反复看原生读档页面。
这不是继续操作旧世界同时悄悄替换数据。A也要等待B完成核对才共同进入下一旬。画面遮盖不会消除实际加载时间，目前没有B完整加载的可靠耗时数据。

本轮开发与验证
1. 实际加载字节观察核心：检查真正交给原生加载器的文件内容和对应工作线程，31项独立进程测试通过。不是只检查目录里的文件，也没有在本轮调用游戏读档。
2. 加载生命周期观察核心：在旧加载对象还活着时记录线程结束、请求清理与成功退出证据，30项独立进程测试通过；旧对象释放后仍可读取自身记录。测试中的原生阶段变化是模拟的，尚不是实机加载验收。
3. 势力/君主成对切换核心：一次性提交两个关联身份，19项独立进程测试通过；生产环境的原生身份入口校验和整条初始化接入仍待完成。
4. 原生机器码回放确认：身份线程可能在旧加载对象释放前或释放后开始，2种时序均已验证。后续接入不能重新读取旧对象，也不能强制只接受某一种栈层数。
5. Windows等待层原型：自建可见窗口、真实窗口捕获与像素核验通过。底层变成新画面以后，覆盖层仍保持旧图；失败状态不露出底层；确认新画面后再撤掉。严格核对了帧时间，避免把缓存旧帧当成成功。
等待层验证仅针对自建测试窗口，没有捕获或覆盖SAN14，也没有证明真实游戏加载页已被遮挡。原生输入暂停、镜头恢复、新地图就绪及真实窗口适配还需整合。

本轮没有实际读档、切换势力或推进日期，不需要用户恢复34号档。

紧接着的主线
把上述组件接成一个受控B加载入口，再验证“同一份A世界 → B身份与菜单 → B的新地图 → 下一旬仍可操作”。随后连接真实双客户端的赏赐即时同步与连续多旬循环。
此前9城的身份相关经济差异已完成离线复算，详见《经济规则适配进展.txt》；共同人类规则的实机安装与结算验证仍未完成。
'''
    (OUT / '即时同步与地图等待加载进展.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / '即时同步与地图等待加载进展.txt').write_text(text, encoding='utf-8')
    prefix = ('最新补充（2026-10-07）：实际加载字节、生命周期和成对身份切换的独立核心测试已通过；'
              '自建可见窗口的旧画面等待层验证通过。尚未接入真实游戏完整加载或游戏画面遮挡，B加载耗时未测。'
              '赏赐即时同步是目标，持续双客户端自动传播尚未连通。详见《即时同步与地图等待加载进展.txt》。\n\n')
    for filename in ('B端原生加载接入进展.txt', '开发剩余工作评估.txt'):
        target = OUT / filename
        old = target.read_text(encoding='utf-8')
        if not old.startswith(prefix):
            target.write_text(prefix + old, encoding='utf-8')
    print(json.dumps({'result': report['result'], 'source_hashes_verified': True,
                      'output': str(OUT / '即时同步与地图等待加载进展.txt'),
                      'cases': {k: v['case_count'] for k, v in evidence.items()}}, ensure_ascii=False))

if __name__ == '__main__':
    main()
