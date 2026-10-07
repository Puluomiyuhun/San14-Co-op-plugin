"""Read-only classification of the completed same-player load observation.

Preserve raw record differences; exclude only the previously identified army
display pointer after checking its current type, backlink and presence.
This is a sampled checkpoint comparison, not a complete-world equality proof.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
from run_second_force_reward import BattleObserver, capture, CHECKPOINT
from startup_identity_reader import capture_startup_context

ROOT = Path(__file__).resolve().parent
load = lambda p: json.loads(p.read_text(encoding='utf-8'))


def main():
    observed = load(ROOT/'startup-identity-live-result.json')
    folder = Path(observed['directory'])
    before, after = load(folder/'before.json'), load(folder/'after.json')
    if before['records'].keys() != after['records'].keys():
        raise RuntimeError('Sampled membership changed')
    raw, unexpected = [], []
    for key, hx in before['records'].items():
        left, right = bytes.fromhex(hx), bytes.fromhex(after['records'][key])
        if len(left) != len(right):
            raise RuntimeError('Record length changed')
        offsets = [i+0x10 for i,(a,b) in enumerate(zip(left,right)) if a != b]
        if not offsets:
            continue
        row = {'object': key, 'object_offsets': [hex(i) for i in offsets]}
        raw.append(row)
        if not (key.startswith('army:') and all(0x148 <= i < 0x150 for i in offsets)):
            unexpected.append(row)
    reader = BattleObserver()
    try:
        current = capture(reader)
        if current != after:
            raise RuntimeError('Current sample differs from captured load result')
        root = reader.pointer(reader.memory.base+0x1FCA1E0)
        links = []
        for unit in after['focused']['all_active_units']:
            key = f"army:{unit['id']}"
            address = reader.pointer(root+0x7DF60+unit['id']*8)
            old = int.from_bytes(bytes.fromhex(before['records'][key])[0x138:0x140], 'little')
            new = int.from_bytes(bytes.fromhex(after['records'][key])[0x138:0x140], 'little')
            actual = int.from_bytes(reader.memory.read(address+0x148,8), 'little')
            if actual != new or bool(old) != bool(new):
                raise RuntimeError('Display pointer presence/current value changed')
            if new:
                reader.require_type(new, 'CUnitArmy')
                if reader.pointer(new+0x40) != address:
                    raise RuntimeError('Display object backlink mismatch')
            links.append({'army_id': unit['id'], 'present': bool(new), 'rebuilt': old != new,
                          'current_rtti_and_backlink_checked': bool(new)})
        context = capture_startup_context(reader)
        if current != capture(reader):
            raise RuntimeError('Sample changed during verification')
    finally:
        reader.close()
    equality = {k: before[k] == after[k] for k in
                ('focused','eligibility','pools','world_rng_fields_hex')}
    checkpoint_unchanged = hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest() == (
        'afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95')
    if unexpected or not all(equality[k] for k in ('focused','eligibility','world_rng_fields_hex')) or not checkpoint_unchanged:
        raise RuntimeError(f'Unresolved sample changes: {unexpected}, {equality}')
    result = {
        'schema':'san14.startup-load-closeout.v1',
        'created':datetime.now().astimezone().isoformat(),
        'result':'SAMPLED_GAMEPLAY_MATCHES_RUNTIME_STATE_DIFFERS',
        'sampled_records':len(before['records']), 'raw_changed_records':len(raw),
        'raw_record_differences':raw, 'unexpected_sampled_record_changes':unexpected,
        'equal_sections':equality, 'display_pointer_field':'army+0x148',
        'display_backlink_field':'CUnitArmy+0x40', 'display_links':links,
        'known_rng_before':before['global_rng'], 'known_rng_after':after['global_rng'],
        'pool_samples_before':before['pools'], 'pool_samples_after':after['pools'],
        'pool_change_explanation':'Retained as runtime differences; cause and relevance not established by this trace.',
        'rng_rewritten':False, 'checkpoint34_unchanged':checkpoint_unchanged,
        'current_context':context, 'game_data_writes_by_adapter':0,
        'complete_world_equality_proven':False,
        'scope':before['record_scope']}
    for path in (folder/'closeout.json', ROOT/'startup-identity-closeout.json'):
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in
                     ('raw_record_differences','display_links','current_context')}, ensure_ascii=True,indent=2))


if __name__ == '__main__':
    main()
