"""Read-only closeout: current restore sample, native code, hooks and save."""
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime
import hashlib
import json
from pathlib import Path
from run_second_force_reward import ROOT, CHECKPOINT, capture
from battle_observer import BattleObserver

load = lambda p: json.loads(p.read_text(encoding='utf-8'))
native = load(ROOT / 'second-force-reward-live-latest.json')
assert native['restore_verified']
restored = load(Path(native['directory']) / 'restored.json')
source = load(ROOT / 'human-ai-fixture-source.json')
reader = BattleObserver()
try:
    now = capture(reader)
    assert now == capture(reader), 'Current sample unstable'
    assert now['records'] == restored['records'], 'Sample changed after native restore verification'
    assert now['eligibility'] == restored['eligibility']
    assert now['focused'] == restored['focused']
    memory = reader.memory
    anchors = []
    for block in source['native_blocks']:
        a, z = int(block['rva'], 16), int(block['end'], 16)
        digest = hashlib.sha256(memory.read(memory.base + a, z-a)).hexdigest()
        assert digest == block['sha256'], f'Native block changed at {a:#x}'
        anchors.append({'rva': block['rva'], 'sha256': digest})
    manager = reader.pointer(memory.base + 0x1a1f6c0)
    reader.require_type(manager, 'CAIManager')
    ai = {'global_gate': int.from_bytes(memory.read(manager + 0x30, 4), 'little'),
          'per_force_entry_count': int.from_bytes(memory.read(manager + 0x68, 8), 'little')}
    assert ai == {'global_gate': 1, 'per_force_entry_count': 0}
    assert reader.pointer(memory.base + 0x12cc4a8 + 0x28) == memory.base + 0x3f9b00
    memory.k.CheckRemoteDebuggerPresent.argtypes = [W.HANDLE, C.POINTER(W.BOOL)]
    memory.k.CheckRemoteDebuggerPresent.restype = W.BOOL
    attached = W.BOOL()
    assert memory.k.CheckRemoteDebuggerPresent(memory.handle, C.byref(attached)) and not attached.value
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(CHECKPOINT) == sha(ROOT.parent / 'mod_test/replay-checkpoint-34/svdexSC34.s14') == 'afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
    result = {'result': 'PASS', 'created': datetime.now().astimezone().isoformat(),
              'restored_sampled_records_unchanged': len(now['records']),
              'persons_and_task_fields_unchanged': True, 'date': now['focused']['critical_state']['date'],
              'viewer': now['focused']['critical_state']['player'],
              'native_code_anchors_unchanged': anchors, 'ai_policy': ai,
              'original_strategy_update_restored': True, 'debugger_attached': False,
              'checkpoint34_unchanged': True,
              'global_rng_at_restore': restored['global_rng'], 'global_rng_now': now['global_rng'],
              'known_rng_equal_to_recent_restore': now['global_rng'] == restored['global_rng'] and now['world_rng_fields_hex'] == restored['world_rng_fields_hex'],
              'known_rng_equal_to_pre_reward_baseline': native['restoration']['known_rng_equal'],
              'rng_rewritten': False, 'human_ai_policy_installed': False,
              'scope': now['record_scope']}
    (ROOT / 'human-ai-closeout.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'native_code_anchors_unchanged'}, ensure_ascii=True))
finally:
    reader.close()
