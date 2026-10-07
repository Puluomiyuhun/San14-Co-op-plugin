"""Publish bounded checkpoint evidence, keeping fixture and native claims apart."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1]/'outputs'/'san14-link'


def read(name, required=True):
    p = ROOT/name
    if not p.exists():
        if required:
            raise FileNotFoundError(p)
        return None
    return json.loads(p.read_text(encoding='utf-8'))


def main():
    journal = read('checkpoint-journal-tests.json')
    cycles = read('checkpoint-cycle-integration-results.json')
    reload_fixture = read('auto_reload_test_results.json')
    cache_fixture = read('auto_cache_test_results.json')
    cache_live = read('auto_cache_live_result.json', False)
    reload_live = read('auto_reload_live_result.json', False)
    reload_late = read('auto_reload_late_outcome.json', False)
    reload_diagnostic = read('auto_reload_live_diagnostic.json', False)
    save_fixture = read('save_checkpoint_fixture_results.json', False)
    explicit_name = read('save_checkpoint_explicit_name_shadow.json', False)
    before = read('checkpoint-cycle-live/before-auto-cache.json')
    comparisons = {}
    for name in ('before-auto-cache-vs-after-auto-cache', 'after-auto-cache-vs-after-auto-reload'):
        value = read('checkpoint-cycle-live/'+name+'.json', False)
        if value is not None:
            comparisons[name] = value
    cache_ok = bool(cache_live and cache_live.get('result') == 'PASS' and cache_live.get('execute'))
    reload_ok = bool(reload_live and reload_live.get('result') == 'PASS' and reload_live.get('execute'))
    ordinary = [f'svdexSC{i:02}.s14' for i in range(50)]
    occupied = sum(name in before['save_files'] for name in ordinary)
    report = {'schema': 'san14.checkpoint-cycle-progress.v1',
              'created': datetime.now().astimezone().isoformat(),
              'priority': 'complete functional lifecycle before latency optimization',
              'persistent_guest_journal_tests': journal,
              'synthetic_multi_period_integration': cycles,
              'auto_reload_isolated_tests': reload_fixture,
              'auto_cache_isolated_tests': cache_fixture,
              'auto_cache_live': cache_live,
              'auto_reload_live': reload_live,
              'auto_reload_late_readonly_outcome': reload_late,
              'auto_reload_diagnostic': reload_diagnostic,
              'auto_save_isolated_tests': save_fixture,
              'explicit_checkpoint_filename_offline_evidence': explicit_name,
              'live_partial_world_comparisons': comparisons,
              'ordinary_save_slots_occupied': occupied,
              'ordinary_save_slots_total': 50,
              'ordinary_save_overwrite_permitted': False,
              'native_multiplayer_cycle_complete': False,
              'full_world_coverage_verified': False,
              'native_gameplay_enabled': False}
    (OUT/'自动旬末同步接入证据.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    cache_text = '已在当前游戏完成原生存档目录扫描。' if cache_ok else '目录扫描试验器已通过隔离测试，真实游戏是否成功以附带证据为准。'
    load_text = '已由工具自动触发34号档重载，并观察到回到张鲁可下令状态；无需手动点读档。' if reload_ok else '自动重载试验器已通过隔离测试，真实游戏验证尚未完成。'
    if reload_late:
        assert reload_late['result'] == 'LATE_SAME_PLAYER_PLANNING_MAP_OBSERVED'
        load_text = ('工具实际提交了一次34号档原生读档请求，已录到请求被消费及目标文件被绑定；随后记录器读内存失败而退出。'
                     '事后只读核对观察到新的张鲁规划界面实例、原生待处理请求已清空、地图和对象业务样本相同。'
                     '这支持自动读回地图已发生，但中间阶段日志不完整，原尝试仍保留未完整通过状态；没有删除一次性记录或重复提交。'
                     '当前已恢复到203年8月中旬张鲁大地图，原有80份s14文件哈希均未改变；全局随机状态变化被如实记录，未忽略。')
    text = f'''自动旬末同步接入进展
更新：{report['created']}

本轮优先完成逻辑和执行顺序，暂不做加载速度优化。

一、约定的完整循环
A、B各操作自己的势力；规划命令经A确认并同步。双方准备、已接受命令齐全后开始推演。第一版允许双方本地战场演出存在差异，正式事件选择仍由A协调。
旬末先停止新命令，A在结算与事件完成的边界导出原生检查点；B收到并校验完整文件，将加载意图持久化，然后只提交一次原生加载。B恢复所选势力，重新观察当前世界、日期及会话实例；A在此期间保持边界。核对通过才能开放下一旬。
收到文件、原生请求排队、历史“成功”收据，都不能单独代表当前B已经完成世界恢复。

二、已经实现并验证的协议部分
checkpoint_journal.py 保存两份固定检查点载荷，校验哈希后事务落盘。加载意图必须先提交；工具退出或原生结果未知时，重启不会自动重放。相同回执幂等，错误势力、旧世界实例、A已推进或B又读过别的档均拒收。42项测试通过，包括独立进程竞争和落盘后强制退出。
本地固定证书TLS与协调器、分块接收、持久记录已经串联：连续两旬故意分叉B测试世界，完整替换后仍为B势力；第三旬模拟中断则持续锁定。17项集成检查通过。这里的世界和加载回调是合成数据，不是真实双客户端。

三、原生接入
{cache_text}
{load_text}
记录器已调整为在原生加载worker完成后再检查重建的人物/势力索引，并补充失败读地址和清理日志。新增隔离测试已通过，新版本未重复执行真实读档。旧日志缺少失败地址，“过早访问索引”是有静态依据的候选原因，尚未唯一证实。
找到的正常加载链先依赖游戏原生存档目录缓存，再由原生状态机卸载旧世界、反序列化和重建菜单。完成读档后缓存会清空，因此每次自动重载需要重新建立缓存；不能仅写入槽号。
缓存初始化和自动重载分别通过{len(cache_fixture['cases'])}项、{len(reload_fixture['cases'])}项隔离进程测试。前者用替身扫描回调；后者执行复制的原生请求消费分支，其后加载步骤为替身。隔离测试不能代替真实游戏验证，测试二进制与原真实尝试二进制分别保留哈希。
自动保存已找到“绑定新请求→排队CSaveState→原生worker保存→收尾”的路径。当前普通存档位占用{occupied}/50，本轮不会覆盖任何旧槽；独立mod检查点文件名仍需进一步验证。
独立文件名如mpcheck01.s14已有10项模拟器检查支持参数能够传至原生存储写入边界；部分外围调用为替身，没有真实写入。原生普通目录不会枚举这个名字，对应的自动加载入口还需单独接入。当前普通槽试验器没有据此放宽限制。

四、世界核对范围
已实际读取全部48,400个地图格原生序列化的5字节字段，共242,000字节，另保留783条人物、城市、军团、势力、部队样本。比较器只对已有证据的部队显示地址区别处理，城市经济值、随机状态和未知字段不会被静默忽略。
这些仍不是完整世界证明。人物物理槽、任务和编组引用对象、提案、部分动态登记表与World字段还需补齐；切换为B视角后的经济和AI规则也要接入共同人类势力集合。

五、距离真实双机闭环还剩什么
1. 把安全的原生导出接入A旬末边界，并使用不会占用/覆盖个人存档的专用检查点。
2. B收到新检查点后自动安装、原生加载、恢复所选势力；将旧的固定34号档实验推广到每个新旬。
3. 补全加载后业务状态核对，处理双人势力的AI和经济规则。
4. 把持续的命令捕获、事件归属、准备按钮、控制连接与检查点传输接到同一房间流程。
5. 用两台真实电脑连续多旬验收，含攻城、部队产生/消失、招募事件和断线。
完整原生联机仍未开启；目前不是可交付游玩的成品mod。第一版预计仍有原生加载等待，自动化加载和缩短等待时间是两件事。
'''
    (OUT/'自动旬末同步接入进展.txt').write_text(text, encoding='utf-8')
    print(json.dumps({'cache_live_pass': cache_ok, 'reload_live_pass': reload_ok,
                      'ordinary_slots_occupied': occupied, 'native_multiplayer_cycle_complete': False}))


if __name__ == '__main__':
    main()
