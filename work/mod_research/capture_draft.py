import json
import struct
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path('outputs/san14-link').resolve()))
from game_reader import GameReader, DATA_POINTER_RVA, STATE_MANAGER_RVA

label = sys.argv[1]
reader = GameReader()
try:
    m = reader.memory
    snapshot = reader.snapshot()
    print(json.dumps(snapshot, ensure_ascii=False))
    manager = m.base + STATE_MANAGER_RVA
    count = struct.unpack('<Q', m.read(manager + 0x10, 8))[0]
    array = reader.pointer(manager + 0x20)
    addresses = struct.unpack('<' + 'Q' * count, m.read(array, count * 8))
    records = []
    for address, name in zip(addresses, snapshot['state_stack']):
        if name not in ('CStrategyUnitMakeState', 'CStrategyUnitTargetState'):
            continue
        reader.require_type(address, name)
        raw = m.read(address, 0x670 if name == 'CStrategyUnitTargetState' else 0x600)
        Path(f'work/mod_research/draft-{name}-{label}.bin').write_bytes(raw)
        record = {'name': name, 'address': address, 'tail': raw[0x470:].hex(), 'drafts': []}
        if name == 'CStrategyUnitMakeState':
            city = reader.pointer(address + 0x4b8)
            reader.require_type(city, 'CCityData')
            city_bytes = m.read(city, 0x168)
            print('CITY', struct.unpack_from('<H', city_bytes, 0x10)[0], city_bytes[0x12:0x1a].decode('utf-16le').split('\0')[0])
            start, end, cap = struct.unpack_from('<QQQ', raw, 0x4c0)
            assert start <= end <= cap and (end-start) % 8 == 0 and (end-start) <= 64 * 8
            for i, ptr in enumerate(struct.unpack('<' + 'Q' * ((end-start)//8), m.read(start, end-start))):
                data = m.read(ptr, 0x94)
                Path(f'work/mod_research/unit-draft-{i}-{label}.bin').write_bytes(data)
                record['drafts'].append({'address': ptr, 'bytes': data.hex()})
                old_file = Path(f'work/mod_research/unit-draft-{i}-1000.bin')
                old = old_file.read_bytes()
                changes = [(hex(j), struct.unpack_from('<I', old, j)[0], struct.unpack_from('<I', data, j)[0]) for j in range(0, 0x94, 4) if data[j:j+4] != old[j:j+4]]
                print('DRAFT', i, 'WORDS', struct.unpack('<37I', data), 'CHANGES', changes)
        else:
            start, end, cap = struct.unpack_from('<QQQ', raw, 0x540)
            print('TARGET_STATE_WORDS', [(hex(i),struct.unpack_from('<I',raw,i)[0]) for i in range(0x470,len(raw),4)])
            assert start <= end <= cap and (end-start) % 8 == 0 and end-start <= 64 * 8
            for i, ptr in enumerate(struct.unpack('<' + 'Q' * ((end-start)//8), m.read(start,end-start))):
                data = m.read(ptr,0x6c)
                Path(f'work/mod_research/target-draft-{i}-{label}.bin').write_bytes(data)
                record['drafts'].append({'address':ptr,'bytes':data.hex()})
                print('TARGET_DRAFT', i, 'WORDS', struct.unpack('<27I',data))
            root = reader.pointer(m.base + DATA_POINTER_RVA)
            for i in range(61):
                city = reader.pointer(root + 0xdaa8 + i*8)
                city_data = m.read(city, 0x80)
                name = city_data[0x12:0x1a].decode('utf-16le').split('\0')[0]
                if name in ('长安','長安','宛'):
                    Path(f'work/mod_research/city-{i}-{label}.bin').write_bytes(city_data)
                    print('CITY',i,name,city_data.hex())
        records.append(record)
    Path(f'work/mod_research/draft-{label}.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
finally:
    reader.close()
