"""Summarize exact archived comparisons and the bounded native consumer work."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT/'outputs'/'san14-link'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('comparison_tests', type=Path)
    parser.add_argument('reader_tests', type=Path)
    args = parser.parse_args()
    paths = {
        'reader_tests': args.reader_tests,
        'compare_tests': args.comparison_tests,
        'native_consumer': HERE/'checkpoint_native_input_consumer_handoff.json',
        'serialization_audit': HERE/'checkpoint_world_serialization_audit.json',
        'faction_switch': OUT/'世界核验-历史势力切换.json',
        'save_before_after': OUT/'世界核验-原生保存前后.json',
    }
    reports = {name: load(path) for name, path in paths.items()}
    for name in ('reader_tests','compare_tests'):
        report = reports[name]
        assert report['result'] == 'PASS'
        for source, expected in report['source_sha256'].items():
            assert sha(HERE/source) == expected, source
    for source, expected in reports['serialization_audit']['source_sha256'].items():
        assert sha(HERE/source) == expected, source
    for artifact in reports['native_consumer']['artifacts']:
        assert sha(ROOT/artifact['path']) == artifact['sha256'], artifact['path']
    for name in ('faction_switch','save_before_after'):
        for source in reports[name]['sources']:
            assert sha(Path(source['path'])) == source['sha256']
        assert reports[name]['full_world_verified'] is False
        assert reports[name]['authorize_release'] is False
    saved = reports['save_before_after']
    switched = reports['faction_switch']
    assert saved['observed_fields_equal'] and saved['counts']['equal_sampled_bytes'] == 507352
    assert not switched['observed_fields_equal']
    assert switched['counts']['unresolved_changed_bytes'] == 39
    assert switched['counts']['display_changed_bytes'] == 138
    domain_counts = {name: d['count'] for name,d in saved['sources'][0]['coverage']['domains'].items()}
    assert domain_counts['hex'] == 48400
    result = dict(schema='san14.world-input-development-progress.v1',
        updated=datetime.now().astimezone().isoformat(), game_accessed=False,
        native_gameplay_enabled=False, full_world_verified=False,
        current_scope='Archived evidence comparison and a bounded mouse-consumer bridge; not a playable mod.',
        implementation=dict(reader_tests=reports['reader_tests']['tests_run'],
            comparison_tests=reports['compare_tests']['cases'], native_consumer_tests=10,
            compared_map_slots=48400, compared_saved_sample_bytes=507352,
            save_before_after_equal_within_observed_scope=True,
            faction_switch_unresolved_city_bytes=39, audited_display_pointer_bytes=138,
            world_direct_serialization_ranges=len(reports['serialization_audit']['world_direct_buffer_fields'])),
        input_blockers=['Pending menu is latched before the observed mouse calls',
            'A raw modifier path bypasses this mouse consumer',
            'Real hook lifetime, producer drain, controller and release fencing are still missing'],
        world_blockers=['Sequential partial archives are not a fresh atomic world capture',
            'Dynamic tasks, events, rule files and other tables remain incompletely covered',
            'The two-human economy policy still needs integration in the real load path'],
        evidence={name: dict(path=str(path.resolve()), sha256=sha(path)) for name,path in paths.items()})
    (OUT/'世界核验与输入接线进展.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    text = '''这轮完成了统一档案读器、差异比较器，以及一个可以接入原生鼠标读取位置的 C++ 适配模块。没有访问或操作真实游戏。

世界核验现在能做什么
旧的部分对象比较扩展到了全地图 48,400 格的已知存档字段，并一起核对对象名单、已采样任务及其顺序、随机状态、经济扩展记录和阶段信息。
原生保存前后那组历史档案的 49,184 条记录、507,352 个已采样字节一致。这包括每格已审计的 5 字节，并非地图格的全部运行时状态。
历史张鲁→刘备切换仍检出 9 城市的 39 个经济变化字节；另外 138 字节属于有独立依据的军队显示对象指针变化。随机状态等其他差异也保留，不以“本机视角不同”为理由忽略。
读器支持 12 份明确列出的历史档案；扩展经济的两份同内容样本都是张鲁视角，不冒充真实 A/B 对照。
输入格式校验、缺失对象、末尾地图格变动、任务顺序、随机状态和不同阶段等测试均通过。

新确认的存档特点
审计补出了 44 组 World 的直接序列化字段。存档包含本机势力等身份信息，头部也有生成时数据，因此两端文件 SHA 不同不等于业务世界一定不同。
反过来，文件传输 SHA 一致也不证明加载后的所有业务数据相同：原生初始化、共同规则、事件和未覆盖的外部状态仍要核验。

输入接线现在能做什么
已定位真实鼠标查询及调用点，用归档的实际 37 字节查询函数在自有进程中验证：先中和指定缓存，再执行原查询，保留参数、完整返回值与已测试的 C++ 异常清理。10 项隔离测试通过。
同时定位到两个具体缺口：菜单请求在这里之前已经被读入；后面还会通过另一条路径读取修饰键。因此这个适配器只保护指定鼠标查询，不能当作完整输入锁，也没有安装到游戏里。

下一步
优先把完整输入边界和已存在的菜单请求处理接好，再开展 B 的单次自动加载实验；用本轮比较器检查真实加载前后差异。
受限实验成功仍不等于双人整局通过。后续要接两个人类势力的经济/AI规则、执行前命令捕获和双客户端连续两旬循环。
当前没有开放完整世界成功标志或联机放行，也不需要你现在手动操作游戏。
'''
    (OUT/'世界核验与输入接线进展.txt').write_text(text, encoding='utf-8')
    print('Published bounded world/input evidence; no gameplay or full-world authorization.')


if __name__ == '__main__':
    main()
