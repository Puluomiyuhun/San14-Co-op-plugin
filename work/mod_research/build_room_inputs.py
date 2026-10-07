"""Capture a current, read-only catalog and one legal authority preflight."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs' / 'san14-link'
sys.path.insert(0, str(OUT))
from human_control_reader import capture
from battle_observer import BattleObserver
from authority_reward import capture_context, eligible_ids, make_command, validate_reward
from room_session import PROTOCOL, Room, digest
save = Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14')
backup = ROOT.parent / 'mod_test/replay-checkpoint-34/svdexSC34.s14'
save_hash = hashlib.sha256(save.read_bytes()).hexdigest()
assert save_hash == hashlib.sha256(backup.read_bytes()).hexdigest()
reader = BattleObserver()
try:
    preview = capture(reader, [12, 2])
    context = capture_context(reader, 2)
    ids = eligible_ids(context, context['main_district_id'])[:3]
    assert ids
    command = make_command(context, context['main_district_id'], ids)
    preflight = validate_reward(command, context, 2)
finally:
    reader.close()
rules = {'players': 2, 'ownership': 'one_distinct_force_each', 'delegation': 'preserve_native',
         'phase': 'room_binding_only', 'native_start_enabled': False}
manifest = {'profile': {'protocol': PROTOCOL, 'game_sha256': preview['game_sha256'],
                        'adapter_contract': 'research-no-native-room-adapter.v1',
                        'checkpoint_sha256': save_hash, 'rules_sha256': digest(rules)},
            'forces': [{'id': f['force_id'], 'name': f['ruler_name'], 'main_district_id': f['main_district_id']}
                       for f in preview['forces'] if f['ruler_id'] > 0 and f['force_id'] < 46],
            'source': {'method': 'read-only live catalog', 'captured': datetime.now().astimezone().isoformat(),
                       'game_date': preview['date'], 'viewer_force_id': preview['viewer_force_id'],
                       'checkpoint_bytes_verified': True, 'live_world_equals_checkpoint_not_proven': True,
                       'selection_scope': 'Protocol catalog of ordinary active factions; actual local identity switching remains unverified'}}
Room(manifest)
(OUT / '房间势力目录.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(ROOT / 'room-integration-inputs.json').write_text(json.dumps({'context': context, 'command': command, 'preflight': preflight}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'result': 'PASS', 'catalog_forces': len(manifest['forces']), 'viewer_force': preview['viewer_force_id'],
                  'command_force': command['force_id'], 'preflight': preflight['result'], 'applied_to_game': False}))
