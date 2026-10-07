"""Read-only game closeout and bounded evidence publication for investigation H."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
from analyze_lockstep import baseline_difference
from combat_list_inputs import capture_combat_lists
from lockstep_baseline import BattleObserver, sample

ROOT = Path(__file__).resolve().parent
TRACES = ROOT / 'lockstep-traces'
OUT = ROOT.parents[1] / 'outputs/san14-link'
load = lambda p: json.loads(p.read_text(encoding='utf-8'))

def save_new(path, value):
    with path.open('x', encoding='utf-8') as f:
        f.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

reader = BattleObserver()
try:
    current = sample(reader)
    lists = capture_combat_lists(reader)
    assert current == sample(reader) and lists == capture_combat_lists(reader)
finally:
    reader.close()
assert lists == load(TRACES / 'combat-list-baseline-h.json')
previous = load(TRACES / 'pending-run-g/restored.json')
comparison = baseline_difference(previous, current)
assert not comparison['sampled_record_changes_excluding_known_runtime_pointer']
assert all(comparison[k] for k in ('focused_state_equal', 'person_task_sample_equal', 'random_inputs_equal'))
assert previous['random_inputs'] == current['random_inputs']
assert current['random_inputs']['global_18eb8b0'] == 1138287528
save_new(TRACES / 'combat-inputs-final-h.json', current)
save_new(TRACES / 'combat-list-final-h.json', lists)

fixtures = [json.loads(s) for s in (ROOT / 'combat-inputs-fixture-results.jsonl').read_text().splitlines()]
assert len(fixtures) == 20 and all(x['result'] == 'PASS' for x in fixtures)
assert not (ROOT / 'combat-inputs-fixture-stderr.txt').read_bytes()
matrix, sort, tie = fixtures[-3:]
assert matrix['comparisons'] == 289 and matrix['distinct_symmetric_true_pairs'] == 0
assert sort['sort_runs'] == 19 and sort['distinct_input_orders'] == 18 and sort['same_output']
assert tie['both_directions_true'] and tie['input_0_1_output'] == [1, 0] and tie['input_1_0_output'] == [0, 1]
assert not tie['real_game_occurrence_proven']

image = (ROOT / 'game-runtime-image.bin').read_bytes()
dispatch = struct.unpack_from('<31I', image, 0x3f9610)
assert dispatch[12] == 0x3f9344 and dispatch[24] == 0x3f9535
def relative_target(at, opcode):
    assert image[at] == opcode
    return at + 5 + struct.unpack_from('<i', image, at + 1)[0]
assert relative_target(0x3f9535, 0xe8) == 0x3fbfc0
assert relative_target(0x3fc13c, 0xe9) == 0x2eb770
assert relative_target(0x2eb78f, 0xe9) == 0x2fd940
assert relative_target(0x2e5959, 0xe8) == 0x2fde60

close = load(TRACES / 'combat-inputs-h-closeout.json')
assert not close['debugger_attached'] and close['original_strategy_update_restored']
assert close['save34_sha256'] == close['backup_sha256'] == 'afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
assert {k: lists['pointer_lists'][k]['count'] for k in ('0x58', '0x68', '0x88', '0x98')} == {'0x58': 56, '0x68': 0, '0x88': 51, '0x98': 10}
assert lists['annihilate_list']['count'] == 0 and lists['active_list_matches_valid_records_as_set']

paths = [ROOT / n for n in (
    'combat_list_inputs.py', 'inspect_combat_lists.py', 'make_combat_inputs_fixture.py',
    'combat_inputs_fixture.cpp', 'combat_inputs_fixture_code.h', 'combat_inputs_fixture.exe',
    'build_combat_inputs_fixture.cmd', 'combat-inputs-fixture-source.json',
    'combat-inputs-fixture-results.jsonl', 'combat-inputs-fixture-stderr.txt',
    'survey-210d40.txt', 'survey-1622f0.txt', 'survey-159580.txt', 'survey-15abc0.txt',
    'survey-2e5830.txt', 'survey-3fbfc0.txt', 'disasm-2eb770.txt', 'survey-2fd940.txt',
    'survey-3f8e10.txt', 'publish_combat_inputs_evidence.py')]
paths += [TRACES / n for n in ('combat-list-inspection.json', 'combat-list-baseline-h.json',
    'combat-list-final-h.json', 'combat-inputs-final-h.json', 'combat-inputs-h-closeout.json',
    'pending-run-g/restored.json', 'branch-run-f/trace.jsonl')]
for path in paths:
    assert path.is_file(), path

report = {
    'schema': 'san14.lockstep.combat-inputs.v1',
    'created': datetime.now().astimezone().isoformat(),
    'result': 'ADDITIONAL_LOGIC_INPUTS_AND_SYNTHETIC_ORDER_SENSITIVITY_CONFIRMED_A_UNRESOLVED',
    'game_version': 'SAN14PK_SC.exe 1.0.11.0',
    'game_exe_sha256': '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025',
    'execution_scope': {
        'game_access': 'ReadProcessMemory only; no debugger, DLL load, code patch, game call, date advance or RNG write this investigation.',
        'native_fixture': 'Relocated native predicate, comparator and insertion sort execute in an independent process with locally allocated objects.',
        'stubbed_dependencies': ['object validity 0x2F2BB0', 'force lookup 0x20A810', 'pair-copy cleanup 0x15A3B0'],
        'unsupported_dependencies': 'Facility/presentation dependencies abort if reached. The real F data contains only kinds 5, 6 and 27.',
        'not_executed': 'Full battle simulation, RNG generation, actual army destruction, animation or two-client synchronization.'
    },
    'input_lists': lists,
    'reader_scope': 'Live inventory validated on current empty exclusion/annihilation lists and nonempty active/city/gate lists. Nonempty annihilation decoding is implemented but has not been validated against a real game event or a parser fixture; unknown object types remain UNRESOLVED.',
    'native_predicate': {
        'rva': '0x210D40',
        'observations': [
            'Membership in root+0x68 pointer list can exclude the same candidate without changing its object record.',
            'root+0x138 has native RTTI tlib::list<SAnnihilate>. A valid first member equal to the candidate excludes it independently.',
            'The third member can also exclude a candidate if the second and third members are valid, it equals the candidate, and its force is outside 46..51.'
        ],
        'complete_root68_lifecycle_known': False,
        'lists_absent_from_save_proven': False
    },
    'annihilate_lifecycle_static': {
        'append': '0x2E5830 checks duplicates and a 128-entry bound, allocates via 0x2FDE60 and copies 48 payload bytes.',
        'processing': 'Dispatcher stage 24 targets 0x3F9535, which calls 0x3FBFC0 to walk entries. Battle gate is stage 12.',
        'clear': '0x3FBFC0 tail-calls 0x2EB770 then 0x2FD940. The latter returns nodes to the pool and zeros head, tail and count.',
        'stage_table_rva': '0x3F9610',
        'verified_direct_branches': {'0x3F9535': '0x3FBFC0', '0x3FC13C': '0x2EB770', '0x2EB78F': '0x2FD940', '0x2E5959': '0x2FDE60'},
        'observed_nonempty_in_current_run': False
    },
    'fixtures': fixtures,
    'sort_interpretation': {
        'comparator': '0x15ABC0', 'native_sort': '0x159580',
        'real_control': '17 captured F pairs: original, reversed and 17 cyclic rotations produce the captured sorted order. 19 checks contain 18 distinct input permutations because a full rotation repeats the original.',
        'unmapped_bytes_scope': 'Changing side +2/+3/+9 did not change any of the 289 comparisons for this dataset. This does not prove the bytes are unused by all game logic.',
        'synthetic_tie': 'Same defending side; different army attacker IDs 101 and 102; attacker comparison byte +8 and word +0xA equal. Both comparator directions return true. Native insertion sort reverses the two-node input, so opposite inputs produce opposite outputs.',
        'conclusion': 'At least this valid comparator input shape has order-sensitive queue output; deterministic synchronization must preserve or deliberately canonicalize relevant construction order.',
        'real_f_tie_observed': False,
        'combat_damage_divergence_demonstrated_by_fixture': False,
        'no_std_sort_undefined_behavior_claim': True
    },
    'unchanged_vs_previous_restored_game': comparison,
    'input_lists_unchanged_this_investigation': True,
    'current_global_rng': current['random_inputs']['global_18eb8b0'],
    'rng_note': '1138287528 matches the previous restored game. Difference from the oldest A/B planning sample 3900088880 is pre-existing; no RNG repair was attempted.',
    'closeout': {k: close[k] for k in ('date', 'player', 'sampled_records', 'debugger_attached', 'original_strategy_update_restored', 'save34_sha256', 'backup_sha256', 'restored_diagnostics', 'rng_state_rewritten')},
    'next_discriminating_work': [
        'Audit original observer timing and stage-resume boundaries; A did not capture subday or cached battle gate.',
        'For a future targeted capture, collect semantic list membership/order before pair construction and after sorting, then per-pair eligibility reasons. Preserve raw unknown fields.',
        'Only design normalization after identifying a shared settled phase and proving that it does not duplicate, discard or reorder unresolved game work.'
    ],
    'original_a_cause_proven': False, 'deterministic_lockstep_proven': False,
    'complete_world_equality_proven': False, 'synchronization_patch_installed': False,
    'manifest': [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size,
                  'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
}
destination = OUT / '交战名单与排序追查第六轮证据.json'
save_new(destination, report)
assert load(destination) == report
print(json.dumps({'published': str(destination), 'native_fixture_cases': len(fixtures),
    'distinct_sort_inputs': sort['distinct_input_orders'], 'sampled_records': len(current['records']),
    'unchanged': True, 'rng': current['random_inputs']['global_18eb8b0'],
    'debugger_attached': close['debugger_attached']}, ensure_ascii=True))
