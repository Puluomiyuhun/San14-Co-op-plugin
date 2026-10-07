"""Read-only recovery witness; does not retry a request or certify full coverage."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from checkpoint_live_capture import sample, comparison
from run_second_force_reward import BattleObserver
from start_startup_switch import no_debugger

ROOT = Path(__file__).resolve().parent
load = lambda p: json.loads(p.read_text(encoding='utf-8'))


def main():
    attempt = load(ROOT/'auto_reload_live_result.json')
    assert attempt['execute'] and attempt['result'] == 'NOT_COMPLETED_NO_AUTO_RETRY'
    trace = attempt['trace']
    assert [r['event'] for r in trace] == ['attached', 'armed', 'reload_request_written',
        'native_request_consumed', 'native_target_bound', 'error', 'error_cleanup']
    assert trace[-1] == {'event': 'error_cleanup', 'registers_restored': True, 'detached': True}
    before = load(ROOT/'checkpoint-cycle-live/after-auto-cache.json')
    after = sample()
    compare = comparison(before, after)
    assert not compare['objects']['other_record_changes']
    assert compare['objects']['active_army_semantics_equal'] and compare['objects']['task_fields_equal']
    assert compare['all_48400_hex_serialized_fields_equal']
    assert not any(compare[k] for k in ('save_files_added', 'save_files_removed', 'existing_save_files_changed'))
    assert after['context']['snapshot']['date'] == before['context']['snapshot']['date']
    assert after['context']['snapshot']['player'] == before['context']['snapshot']['player']
    reader = BattleObserver()
    try:
        no_debugger(reader)
        states = reader.state_objects()
        old_user = load(ROOT/'auto_cache_live_result.json')['adapter']['state']
        new_user = states[-1][1]
        assert states[-1][0] == 'CUserStrategyState' and new_user != old_user
        manager = reader.pointer(reader.memory.base+0x2025318)
        pending = int.from_bytes(reader.memory.read(manager+0x3EC, 4), 'little', signed=True)
        assert pending == -1
        assert reader.pointer(reader.memory.base+0x12CC4A8+0x28) == reader.memory.base+0x3F9B00
    finally:
        reader.close()
    journal = ROOT/'auto_reload_live_once.json'
    result = {'schema': 'san14.auto-reload-late-outcome.v1',
              'created': datetime.now().astimezone().isoformat(),
              'result': 'LATE_SAME_PLAYER_PLANNING_MAP_OBSERVED',
              'request_submissions': 1, 'retry_issued': False,
              'observer_complete_trace': False, 'original_observer_error': trace[-2]['message'],
              'old_user_state': old_user, 'new_user_state': new_user,
              'native_pending_request_cleared': pending == -1,
              'current_context': after['context'], 'partial_comparison': compare,
              'persistent_once_journal_sha256': hashlib.sha256(journal.read_bytes()).hexdigest(),
              'journal_preserved': True, 'game_writes_by_verifier': 0,
              'native_gameplay_enabled': False, 'full_world_sync_proven': False,
              'meaning': 'The recorded request was bound to slot34 and a new matching idle map is now observed. Missing intermediate events are not reconstructed; original attempt remains unchanged. This is not a production loaded receipt.'}
    target = ROOT/'auto_reload_late_outcome.json'
    with target.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: result[k] for k in ('result', 'retry_issued', 'observer_complete_trace',
                                            'native_pending_request_cleared', 'full_world_sync_proven')}))


if __name__ == '__main__':
    main()
