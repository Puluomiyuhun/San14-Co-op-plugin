"""Combine static-route, offline-fixture and live-read evidence without game access."""
from pathlib import Path
import json
import struct

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parents[1] / 'outputs' / 'san14-link'


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


types = {**read('domestic-types.json'), **read('domestic-extra-types.json')}
fixtures = read('domestic-decoder-fixture-results.json')
live = read('domestic-live-check.json')
if fixtures['result'] != 'PASS' or fixtures['tests_run'] != 16 or live['result'] != 'PASS':
    raise RuntimeError('Required read-only validation is incomplete')
if live['applied_to_game'] or live['positive_domestic_ui_correlation_verified']:
    raise RuntimeError('Unexpected execution/positive UI claim in read-only evidence')
if live['current_screen']['draft_available']:
    raise RuntimeError('This report expects the verified plain-map negative capture')


def branch(source, target):
    evidence = read(f'full-{source:x}.json')
    matches = [row for row in evidence['direct_references'] if int(row['target_rva'], 16) == target]
    if not matches:
        raise RuntimeError(f'Missing static branch {source:#x} -> {target:#x}')
    return matches


image = (ROOT / 'game-runtime-image.bin').read_bytes()
routes = []
for kind, ui, ai, update, wrapper, ai_method, native, cost, layer in [
    ('reward', 'CStrategyRewardState', 'CCommandExecutionPrizeNode',
     0x67A930, 0x626050, 0x2A440, 0x1D6DA0, 0x18ECF30, 'common_native_handler'),
    ('merchant', 'CStrategyMerchantState', 'CCommandExecutionMerchantNode',
     0x678D30, 0x625B40, 0x299F0, 0x1D5650, 0x18ECF28, 'common_native_handler'),
    ('officer_move', 'CStrategyMoveState', 'CCommandExecutionMoveNode',
     0x678DB0, 0x625FA0, 0x2A280, 0x1D58A0, 0x18ECF80, 'player_wrapper_after_native_handler'),
]:
    if types[ui]['methods'][0][5] != update or types[ai]['methods'][0][16] != ai_method:
        raise RuntimeError('Class method correspondence changed')
    routes.append({
        'kind': kind, 'ui_class': ui, 'ai_class': ai,
        'update_to_player_wrapper': branch(update, wrapper),
        'player_wrapper_to_common_handler': branch(wrapper, native),
        'ai_method_to_common_handler': branch(ai_method, native),
        'common_handler_rva': hex(native),
        'action_cost_layer': layer, 'action_cost_rva': hex(cost),
        'action_cost_in_captured_image': struct.unpack_from('<i', image, cost)[0],
        'positive_ui_draft_tested': False, 'native_execution_tested': False,
    })

report = {
    'stage_result': 'READ_ONLY_FOUNDATION_PASS',
    'exe_sha256': live['current_screen']['exe_sha256'],
    'statically_correlated_routes': routes,
    'offline_fixture_validation': fixtures,
    'live_read_validation': live,
    'domestic_network_execution_enabled': False,
    'requires_manual_action_now': False,
    'remaining': [
        'Real domestic UI parameter correlation',
        'Native container construction, lifetime, and complete legality guards',
        'Game-thread execution, exact resource effects and restoration',
        'Second-faction context, AI exclusion, and cross-client turn synchronization',
    ],
}
container_path = OUTPUT / '赏赐名单容器验证.json'
if container_path.exists():
    container = json.loads(container_path.read_text(encoding='utf-8'))
    if (container['result'] != 'PASS' or container['reward_handler_calls'] != 0
            or not container['reward_state_unchanged'] or container['domestic_network_execution_enabled']):
        raise RuntimeError('Unexpected reward-container evidence')
    report['stage_result'] = 'READ_AND_REWARD_CONTAINER_PASS'
    report['native_reward_container_validation'] = container
    report['remaining'][1] = 'Reward full legality checks; other domestic containers require separate native lifecycle validation'
    report['remaining'][2] = 'Actual domestic command execution, exact resource effects and restoration'
eligibility_path = OUTPUT / '赏赐资格对照验证.json'
if eligibility_path.exists():
    eligibility = json.loads(eligibility_path.read_text(encoding='utf-8'))
    if (eligibility['result'] != 'PASS' or eligibility['mismatches'] != 0
            or eligibility['reward_handler_calls'] != 0 or not eligibility['native_predicate_correlated']):
        raise RuntimeError('Unexpected reward-person eligibility evidence')
    report['stage_result'] = 'READ_CONTAINER_AND_REWARD_PREDICATE_PASS'
    report['native_reward_person_eligibility_validation'] = eligibility
    report['remaining'][1] = 'Reward UI scope/funding/phase/permission checks; other domestic native container lifecycles'
preflight_path = OUTPUT / '赏赐命令预检验证.json'
if preflight_path.exists():
    preflight = json.loads(preflight_path.read_text(encoding='utf-8'))
    if (preflight['result'] != 'PASS' or preflight['game_orders_executed'] != 0
            or not preflight['context_stable'] or preflight['new_dll_loaded']):
        raise RuntimeError('Unexpected read-only reward preflight evidence')
    report['stage_result'] = 'REWARD_PREFLIGHT_PASS_EXECUTION_PENDING'
    report['read_only_reward_command_preflight'] = preflight
    report['remaining'][1] = 'Recheck reward scope/funding/phase/permissions inside native execution; other domestic native container lifecycles'
execution_path = OUTPUT / '赏赐实际执行验证.json'
if execution_path.exists():
    execution = json.loads(execution_path.read_text(encoding='utf-8'))
    if (execution['result'] != 'PASS' or execution['reward_handler_calls'] != 1
            or not execution['executed'] or execution['domestic_network_execution_enabled']):
        raise RuntimeError('Unexpected native reward execution evidence')
    report['stage_result'] = execution['stage']
    report['native_reward_execution_validation'] = execution
    report['requires_manual_action_now'] = not execution['restore_verified']
    routes[0]['native_execution_tested'] = True
    routes[0]['native_execution_scope'] = 'Fixed checkpoint34, current force12, main district11, officers97/759/904 only'
    report['remaining'] = [
        'Generic command capture/replay, normal UI refresh and authenticated network reward execution',
        'Other domestic native containers, eligibility and execution lifecycles',
        'Second-faction control, AI exclusion, automatic save/load and cross-client turn synchronization',
    ]
    if not execution['restore_verified']:
        report['remaining'].insert(0, 'User native load34 and sampled state restoration verification')
path = OUTPUT / '内政解析验证.json'
path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'stage_result': report['stage_result'], 'routes': len(routes),
                  'offline_tests': fixtures['tests_run'],
                  'live_person_records_checked': sum(row['count'] for row in live['sampled_person_lists']),
                  'domestic_command_executions': 1 if execution_path.exists() else 0,
                  'read_only_foundation_state_unchanged': live['focused_before_after_state_matches']}, indent=2))
