"""Exact-build code anchors for a native load-menu round trip, offline only."""
from pathlib import Path
from bisect import bisect_right
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent
saved_args = sys.argv
sys.argv = [__file__]
try:
    import disasm_chained as d
finally:
    sys.argv = saved_args

IMAGE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
EXE_SHA = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
assert hashlib.sha256(d.image).hexdigest() == IMAGE_SHA
FUNCTIONS = [0x411980, 0x426320, 0x426220, 0x4A27A0, 0x4AA200, 0x4D4AA0,
             0x10A60, 0xF690, 0x835DD0, 0x836DF0, 0x837E80, 0x837480,
             0x496580, 0x496F50, 0x509FE0, 0x50B6B0, 0x50B730,
             0x3F5530, 0x3F5920, 0x3F7710, 0x3F7A70, 0x3F9B00,
             0x509640, 0x3A29E0, 0x3A2700, 0x76ECB0]
anchors = []
seen = set()
for address in FUNCTIONS:
    index = bisect_right(d.starts, address) - 1
    assert index >= 0 and address < d.entries[index][1]
    root = d.primary(d.entries[index])
    for start, end, _ in sorted(set(d.groups[root] + [root])):
        if (start, end) in seen:
            continue
        seen.add((start, end))
        anchors.append({'rva': start, 'bytes': d.image[start:end].hex(), 'function': hex(root[0])})
anchors.append({'rva': 0x12DD6E0, 'bytes': b'CSaveLoadState\0'.hex(), 'function': 'native state name'})
assert d.image[0x12DD6E0:0x12DD6E0 + 15] == b'CSaveLoadState\0'
rows = ['#pragma once', '#include <cstdint>', '#include <cstddef>',
        'struct LoadModeAnchor{uintptr_t rva;const unsigned char* bytes;size_t size;};',
        'static const unsigned char LOAD_MODE_EXE_SHA[32]={' + ','.join(hex(x) for x in bytes.fromhex(EXE_SHA)) + '};']
for n, anchor in enumerate(anchors):
    rows.append('static const unsigned char LOAD_MODE_BYTES_' + str(n) + '[]={' +
                ','.join(hex(x) for x in bytes.fromhex(anchor['bytes'])) + '};')
rows.append('static const LoadModeAnchor LOAD_MODE_ANCHORS[]={')
rows.extend('{' + hex(anchor['rva']) + ',LOAD_MODE_BYTES_' + str(n) + ',sizeof(LOAD_MODE_BYTES_' + str(n) + ')},'
            for n, anchor in enumerate(anchors))
rows.append('};')
(ROOT / 'checkpoint_load_mode_profile.h').write_text('\n'.join(rows) + '\n')
(ROOT / 'checkpoint_load_mode_profile.json').write_text(json.dumps({
    'schema': 'san14.checkpoint-load-mode-profile.v1', 'exe_sha256': EXE_SHA, 'image_sha256': IMAGE_SHA,
    'anchors': anchors, 'game_access': False, 'load_or_save_requested': False}, indent=2) + '\n')
print(json.dumps({'result': 'PASS', 'anchors': len(anchors), 'bytes': sum(len(a['bytes']) // 2 for a in anchors), 'game_access': False}))
