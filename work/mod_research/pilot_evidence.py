"""Evidence gates for the one-command development pilot; no process writes."""
import hashlib
import json
from pathlib import Path

GAME_SHA = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
CHECKPOINT_SHA = 'afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def check_checkpoint(path):
    data = Path(path).read_bytes()
    require(hashlib.sha256(data).hexdigest() == CHECKPOINT_SHA,
            'Slot 34 checkpoint does not match the backed-up test save')


def checked_state(snapshot):
    require(snapshot['schema'] == 'san14.focused-state.v1', 'Unsupported observation format')
    require(snapshot['exe_sha256'] == GAME_SHA, 'Observation is from a different game version')
    state = snapshot['critical_state']
    encoded = json.dumps(state, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    require(hashlib.sha256(encoded).hexdigest() == snapshot['critical_state_sha256'],
            'Observation content and digest disagree')
    require(state['date'] == {'year': 203, 'month': 8, 'day': 11, 'period': '中旬'}, 'Unexpected date')
    require(state['player']['force_id'] == 12 and state['player']['ruler_id'] == 666,
            'Unexpected controlled faction')
    require(state['city']['id'] == 19 and state['officer']['id'] == 666,
            'Unexpected source city or actor')
    units = snapshot['all_active_units']
    require(len({u['id'] for u in units}) == len(units), 'Duplicate army ids')
    require(state['officer_units'] == [u for u in units if u['officer_id'] == 666],
            'Actor army records disagree')
    return state


def check_native_trace(rows):
    entries = [r for r in rows if r['event'] == 'submit_entry']
    require(len(entries) == 1, 'Exactly one native submission capture is required')
    require(not any(r['event'] in ('error', 'error_cleanup', 'recorded_command_substituted') for r in rows),
            'Expected a successful observation of an unmodified native submission')
    require(rows[-1] == {'event': 'detached', 'captured': True, 'registers_restored': True},
            'Capture did not detach cleanly')
    entry = entries[0]
    require(entry['caller_rva'] == 0x7149D9 and entry['flags'] == 1,
            'Capture is not from the expected player submission path')
    words = entry['words']
    require(len(words) == 26 and all(type(v) is int and 0 <= v <= 0xffffffff for v in words),
            'Invalid native command payload')
    require(words[0] == 666 and words[2] == 1300 and words[14:16] == [5, 20],
            'Capture does not match the Zhang Lu 1300 / Chang an pilot')
    return words


def check_native_effect(before, after, words):
    b, a = checked_state(before), checked_state(after)
    require(not b['officer_units'], 'Actor already has an army at the baseline')
    require(b['date'] == a['date'] and b['player'] == a['player'], 'Date or faction changed')
    require(b['city']['garrison'] - a['city']['garrison'] == words[2], 'Incorrect garrison deduction')
    require(b['district']['id'] == a['district']['id'] and
            b['district']['action_points'] - a['district']['action_points'] == 1,
            'Incorrect district action deduction')
    old = {u['id']: u for u in before['all_active_units']}
    new = {u['id']: u for u in after['all_active_units']}
    require(all(new.get(key) == value for key, value in old.items()), 'An existing army changed')
    added = [value for key, value in new.items() if key not in old]
    require(len(added) == 1 and a['officer_units'] == added, 'Expected exactly one new actor army')
    unit = added[0]
    expected = {'officer_id': words[0], 'soldiers': words[2], 'formation_id': words[3],
                'naval_formation_id': words[4], 'tactic_ids': words[5:8],
                'order_code': words[13], 'destination_type': words[14], 'destination_id': words[15]}
    require(all(unit[key] == value for key, value in expected.items()),
            'Created army differs from the captured command')
    return {'result': 'PASS', 'garrison_spent': words[2], 'actions_spent': 1, 'new_unit': unit,
            'scope': 'Focused city/officer/district plus semantic active-army records; not complete world equivalence'}


def check_restored(before, restored):
    checked_state(before)
    checked_state(restored)
    require(before['critical_state'] == restored['critical_state'],
            'Focused state did not return to the checkpoint baseline')
    require(before['all_active_units'] == restored['all_active_units'],
            'Active army records did not return to the baseline')
    return {'result': 'PASS', 'focused_state_and_active_armies_match': True,
            'scope': 'Does not prove complete world or RNG restoration'}
