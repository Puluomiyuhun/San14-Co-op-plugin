"""Inspect recorded movement fields and RNG chain without accessing the game."""
import json
from pathlib import Path
from analyze_lockstep import rows, baseline_difference
from analyze_combat_gates import next_rng

ROOT = Path(__file__).resolve().parent
TRACES = ROOT / 'lockstep-traces'
RUN = TRACES / 'stage-path-run-i2'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))

nearby = {}
for name in ('run-a', 'run-b', 'stage-path-run-i2'):
    stages = [r for r in rows(TRACES / name / 'trace.jsonl') if r['event'] == 'stage']
    records = []
    for index in range(165, 187):
        r = stages[index]
        data = bytes.fromhex(dict(r['armies'])[17])
        word = lambda offset: int.from_bytes(data[offset-0x10:offset-0x10+2], 'little')
        records.append({'index': index, 'stage': r['stage'], 'leader': word(0x12),
            'soldiers': word(0x16), 'actual_cell_2a': word(0x2a), 'next_cell_48': word(0x48),
            'status_37': data[0x37-0x10], 'target_kind_38': data[0x38-0x10], 'target_3a': word(0x3a),
            'date': r['date'], 'observed_subday': r.get('subday')})
    nearby[name] = records

seed = 4136155758
chain = [seed]
for _ in range(32): chain.append(next_rng(chain[-1]))
targets = {str(n): [i for i, state in enumerate(chain) if state == n]
           for n in (3900088880, 1138287528, 3823646826)}
before = read(RUN / 'before.json')
restored = read(TRACES / 'restored-stage-path-i2.json')
report = {'army_17_nearby': nearby, 'rng_chain_from_previously_observed_save_seed': chain,
    'rng_target_indices': targets,
    'restored_vs_i2_before': baseline_difference(before, restored),
    'limits': ['Only observations at stage entries, no watchpoint on army+48 in I2.',
              'RNG chain indices are arithmetic consistency, not captured call counts for the I2 restore.',
              'Original A/B did not record actual subday; index alignment assumes repeated stage sequence.',
              'Different I2 and B starting global RNG; this is not a fully synchronized determinism test.']}
(RUN / 'next-cell-analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'rng_target_indices': targets, 'comparison': report['restored_vs_i2_before'],
    'nearby': {k: [r for r in v if 176 <= r['index'] <= 181] for k,v in nearby.items()}}, ensure_ascii=True))
