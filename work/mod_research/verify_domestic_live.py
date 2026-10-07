"""Read-only checks of current screen and sample shared-pool person lists.

This is not a positive test of any open domestic UI or command execution.
"""
from pathlib import Path
import json
import hashlib
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'outputs' / 'san14-link'))
from domestic_reader import (DomesticReader, PERSON_POOL_ENABLED_RVA, PERSON_POOL_HEADS_RVA,
                             PERSON_POOL_COUNTS_RVA, PERSON_POOL_CAPACITY_RVA)
from battle_observer import BattleObserver
from sortie_reader import text_name

reader = BattleObserver()
try:
    before = reader.capture()
    current = DomesticReader.capture(reader)
    memory = reader.memory
    reads = []

    def read(address, size):
        data = memory.read(address, size)
        reads.append((address, data))
        return data

    def uint(address, size=8):
        return int.from_bytes(read(address, size), 'little')

    enabled = uint(memory.base + PERSON_POOL_ENABLED_RVA)
    heads = uint(memory.base + PERSON_POOL_HEADS_RVA)
    counts = uint(memory.base + PERSON_POOL_COUNTS_RVA)
    capacity = uint(memory.base + PERSON_POOL_CAPACITY_RVA, 4)
    if not enabled or not 0 < capacity <= 0x20000:
        raise RuntimeError('Unsupported live pointer pool')
    # A discovery scan only: candidates are individually reread and checked.
    sizes = struct.unpack('<' + 'Q' * capacity, memory.read(counts, capacity * 8))
    examples = []
    skipped_other_object_lists = 0
    for slot, discovered_size in enumerate(sizes[:0x14000]):
        if not 1 <= discovered_size <= 6000:
            continue
        head = int.from_bytes(memory.read(heads + slot * 8, 8), 'little')
        if not head:
            continue
        person = int.from_bytes(memory.read(head, 8), 'little')
        try:
            reader.require_type(person, 'CPersonData')
        except RuntimeError:
            skipped_other_object_lists += 1
            continue
        size = uint(counts + slot * 8)
        node = uint(heads + slot * 8)
        if not 1 <= size <= 6000:
            raise RuntimeError('Candidate list changed during sampling')
        people, visited = [], set()
        while node:
            if node in visited or len(visited) >= size:
                raise RuntimeError('Candidate pool cycle/count mismatch')
            visited.add(node)
            person, node = struct.unpack('<QQ', read(node, 16))
            reader.require_type(person, 'CPersonData')
            record = read(person, 0x36)
            people.append({'id': struct.unpack_from('<H', record, 0x10)[0],
                           'name': text_name(record[0x12:0x24]) + text_name(record[0x24:0x36])})
        if len(people) != size:
            raise RuntimeError('Candidate list is truncated')
        examples.append({'slot': slot, 'count': size, 'people_preview': people[:5],
                         'all_ids_sha256': hashlib.sha256(json.dumps([p['id'] for p in people]).encode()).hexdigest()})
        break
    if not examples:
        raise RuntimeError('No stable person-list example is available for this structural check')
    if any(memory.read(address, len(data)) != data for address, data in reads):
        raise RuntimeError('Sampled pool data changed during inspection')
    after = reader.capture()
    if before != after:
        raise RuntimeError('Focused game state changed during the read-only check')
    result = {
        'result': 'PASS', 'mode': 'read-only-live-structure-check',
        'current_screen': current, 'shared_pointer_pool_capacity': capacity,
        'sampled_person_lists': examples, 'skipped_other_object_lists': skipped_other_object_lists,
        'sampled_fields_stable': True, 'focused_before_after_state_matches': True,
        'focused_state_sha256': after['critical_state_sha256'],
        'active_armies': len(after['all_active_units']), 'applied_to_game': False,
        'positive_domestic_ui_correlation_verified': False,
        'scope': 'Current screen and one existing person pool list, selected city/officer/district and active armies; not whole world/RNG',
    }
    (ROOT / 'domestic-live-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
finally:
    reader.close()
