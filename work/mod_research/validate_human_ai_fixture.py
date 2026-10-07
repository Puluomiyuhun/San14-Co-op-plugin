"""Check native gates and candidate policy against a saved read-only preview."""
import hashlib
import json
from pathlib import Path
import subprocess
import argparse
ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs' / 'san14-link'
parser = argparse.ArgumentParser()
parser.add_argument('--preview', type=Path, default=OUT / '双人控制范围预览.json')
parser.add_argument('--output', type=Path, default=ROOT / 'human-ai-fixture-results.json')
args = parser.parse_args()
preview_path = args.preview
data = json.loads(preview_path.read_text(encoding='utf-8'))
assert data['sample_stable'] and not data['applied_to_game']
a, b = data['human_forces']
main = {row['force_id']: row['main_district_id'] for row in data['forces']}
lines = [f"{data['viewer_force_id']} {a} {main[a]} {b} {main[b]} {int(data['world_16a8_bit8'])}"]
decisions = {'NATIVE': 0, 'BYPASS_HUMAN_DECISION': 1, 'HOLD': 2}
labels = ['forces', 'districts', 'armies'] + (['army_groups'] if data.get('army_groups_decoded') else [])
for route, label in enumerate(labels):
    for row in data[label]:
        district = 0 if route == 0 else row['id'] if route == 1 else row['district_id']
        lines.append(f"{route} {row['force_id']} {district} {int(row['native_outer_dispatch'])} {decisions[row['candidate_policy']]}")
cases = ROOT / 'human-ai-live-cases.txt'
cases.write_text('\n'.join(lines) + '\n', encoding='ascii')
run = subprocess.run([str(ROOT / 'human_ai_fixture.exe'), str(cases)], capture_output=True, text=True, timeout=15)
assert run.returncode == 0, (run.returncode, run.stderr)
result = json.loads(run.stdout)
assert result['result'] == 'PASS' and result['copied_live_subjects'] == len(lines) - 1
result['live_preview_sha256'] = hashlib.sha256(preview_path.read_bytes()).hexdigest()
result['fixture_source_sha256'] = hashlib.sha256((ROOT / 'human_ai_fixture.cpp').read_bytes()).hexdigest()
result['candidate_header_sha256'] = hashlib.sha256((OUT / 'human_ai_policy.h').read_bytes()).hexdigest()
result['scope'] = 'Copied native wrappers/accessors with controlled external stubs; live subjects are copied semantic IDs. No live AI hooks, movement or battle.'
args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
