"""Observe one player-strategy update call without changing game data."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'outputs' / 'san14-link'))
from battle_observer import BattleObserver
from pilot_evidence import check_restored

run = ROOT / 'update-traces' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
run.mkdir(parents=True, exist_ok=False)
reader = BattleObserver()
try:
    before = reader.capture()
    states = reader.state_objects()
    if states[-1][0] != 'CUserStrategyState':
        raise RuntimeError('Expected the plain player strategy map')
    reader.require_type(states[-1][1], 'CUserStrategyState')
    rva = 0x3F9B00
    image = (ROOT / 'game-runtime-image.bin').read_bytes()
    if reader.memory.read(reader.memory.base+rva,32) != image[rva:rva+32]:
        raise RuntimeError('Runtime function fingerprint mismatch')
    info = {'pid': reader.pid, 'base': hex(reader.memory.base), 'entry_rva': hex(rva),
            'state_address': states[-1][1], 'state_mode_470': int.from_bytes(reader.memory.read(states[-1][1]+0x470,4),'little'),
            'game_fingerprint': reader.sha256}
    (run/'metadata.json').write_text(json.dumps(info, indent=2))
    args = [str(ROOT/'observe_submit.exe'), str(reader.pid), hex(reader.memory.base), hex(rva), '15', str(run/'trace.jsonl')]
finally:
    reader.close()
completed = subprocess.run(args, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=35)
rows = [json.loads(line) for line in (run/'trace.jsonl').read_text().splitlines() if line]
reader = BattleObserver()
try:
    unchanged = check_restored(before, reader.capture())
finally:
    reader.close()
entries = [row for row in rows if row['event'] == 'submit_entry']
result = {'observed': bool(entries), 'exit_code': completed.returncode, 'directory': str(run),
          'state_mode': info['state_mode_470'], 'focused_game_state_unchanged': unchanged}
if entries:
    entry = entries[0]
    result.update({'caller_rva': hex(entry['caller_rva']), 'thread_id': entry['thread_id'],
                   'this_pointer_matches_player_state': entry['argument_pointer'] == info['state_address'],
                   'rdx': entry['flags']})
(run/'result.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
print(json.dumps(rows))
