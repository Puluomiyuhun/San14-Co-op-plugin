"""External read-only snapshot for the independent load-mode round trip."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / 'python_deps'), str(ROOT.parents[1] / 'outputs/san14-link')]
from checkpoint_cache_graph import inspect_cache
from checkpoint_push_start import sample as old_sample, MemoryPage
import ctypes as C
from ctypes import wintypes as W


def pages(reader):
    k = reader.memory.k
    k.VirtualQueryEx.argtypes = [W.HANDLE, C.c_void_p, C.POINTER(MemoryPage), C.c_size_t]
    k.VirtualQueryEx.restype = C.c_size_t
    value = {}
    for name, rva in [('user', 0x12CC4A8 + 0x28), ('load_init', 0x12DB4C0 + 8),
                      ('load_update', 0x12DB4C0 + 0x28), ('save_update', 0x12DC5F8 + 0x28)]:
        page = MemoryPage()
        assert k.VirtualQueryEx(reader.memory.handle, reader.memory.base + rva, C.byref(page), C.sizeof(page)) == C.sizeof(page)
        value[name] = {'pointer': hex(struct.unpack('<Q', reader.memory.read(reader.memory.base + rva, 8))[0]),
                       'protect': page.Protect, 'allocation_protect': page.AllocationProtect,
                       'state': page.State, 'type': page.Type}
    return value


def snapshot(reader):
    # Keep the old pilot's evidence unchanged. Replace only its deliberately
    # limited directory-shape checks with the five native ownership graphs.
    before = old_sample(reader, allow_target=True)
    obsolete = {'cache_not_supported_empty_list_shape', 'cache_residue_stride_or_mode'}
    before['reasons'] = [r for r in before['reasons'] if r not in obsolete]
    base = reader.memory.base
    cache = struct.unpack('<Q', reader.memory.read(base + 0x2025318, 8))[0]
    graph = inspect_cache(reader.memory.read, cache)
    assert graph == inspect_cache(reader.memory.read, cache), 'Directory graph changed during sample'
    before['cache_graph'] = graph
    before['mode_hook_pages'] = pages(reader)
    originals = {'user': 0x3F9B00, 'load_init': 0x4A27A0, 'load_update': 0x4AA200, 'save_update': 0x4AA650}
    for name, rva in originals.items():
        if before['mode_hook_pages'][name]['pointer'] != hex(base + rva):
            before['reasons'].append(name + '_hook_present')
    before['result'] = 'PASS' if not before['reasons'] else 'BLOCKED_PRECONDITIONS'
    return before


if __name__ == '__main__':
    from battle_observer import BattleObserver
    with_reader = BattleObserver()
    try:
        data = snapshot(with_reader)
    finally:
        with_reader.close()
    path = ROOT / ('checkpoint_load_mode_snapshot_' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    with path.open('x', encoding='utf8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'path': str(path), 'result': data['result'], 'reasons': data['reasons'],
                      'cache_graph': data['cache_graph'], 'game_writes': 0}))
