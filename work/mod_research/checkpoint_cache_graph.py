"""Read-only ownership witness for the native save directory cache.

The main list at +10 and four category lists at +400 are separate owners.
A category can retain nodes after the table has been reset; ownership does
not imply that every node is currently indexed. No heap-stride assumptions.
"""
import struct


def inspect_cache(read, cache):
    def get(address, size):
        if not 0x10000 <= address <= 0x00007FFFFFFFFFFF - size:
            raise ValueError('invalid_pointer')
        data = read(address, size)
        if len(data) != size:
            raise ValueError('short_read')
        return data

    raw = get(cache, 0x440)
    q = lambda offset: struct.unpack_from('<Q', raw, offset)[0]
    i = lambda offset: struct.unpack_from('<i', raw, offset)[0]
    lists = [(name, offset, q(offset), q(offset + 8)) for name, offset in
             [('main', 0x10)] + [('group' + str(n), 0x400 + n * 0x10) for n in range(4)]]
    heads = {head for _, _, head, _ in lists}
    if len(heads) != 5:
        raise ValueError('duplicate_head')
    spans = [(cache, cache + 0x440)]
    def reserve_span(address, size):
        end = address + size
        if not 0x10000 <= address <= 0x00007FFFFFFFFFFF - size:
            raise ValueError('invalid_pointer')
        if any(address < other_end and other_start < end for other_start, other_end in spans):
            raise ValueError('overlapping_owner_storage')
        spans.append((address, end))
    for head in heads:
        reserve_span(head, 16)
    owners, payloads, rows = {}, {}, []
    for name, offset, head, count in lists:
        if count > 120:
            raise ValueError('excessive_count')
        first, tail = struct.unpack('<QQ', get(head, 16))
        current, previous, nodes = first, head, []
        while current != head:
            if current in heads or current in owners:
                raise ValueError('cycle_or_shared_owner')
            if len(nodes) >= count:
                raise ValueError('count_mismatch')
            reserve_span(current, 0x160)
            blob = get(current, 0x160)
            successor, predecessor = struct.unpack_from('<QQ', blob)
            if predecessor != previous:
                raise ValueError('predecessor_mismatch')
            text_at = 0x10 + 0x128
            length, capacity = struct.unpack_from('<QQ', blob, text_at + 16)
            if length > capacity or length > 1024 or capacity > 32768 or (capacity < 16 and capacity != 15):
                raise ValueError('invalid_string_shape')
            if capacity < 16:
                text = blob[text_at:text_at + length + 1]
            else:
                text = get(struct.unpack_from('<Q', blob, text_at)[0], length + 1)
            if len(text) != length + 1 or text[-1] != 0 or b'\0' in text[:-1]:
                raise ValueError('invalid_string_terminator')
            filename = text[:-1].decode('ascii')
            owners[current] = name
            payloads[current + 0x10] = {'owner': name, 'node': hex(current), 'filename': filename}
            nodes.append({'node': hex(current), 'payload': hex(current + 0x10), 'filename': filename})
            previous, current = current, successor
        if len(nodes) != count or tail != previous:
            raise ValueError('count_or_tail_mismatch')
        rows.append({'name': name, 'offset': offset, 'head': hex(head), 'count': count, 'nodes': nodes})
    entries, seen = [], set()
    for slot, payload in enumerate(struct.unpack_from('<120Q', raw, 0x20)):
        if not payload:
            continue
        if payload not in payloads:
            raise ValueError('table_without_owner')
        if payload in seen:
            raise ValueError('duplicate_table_payload')
        seen.add(payload)
        entries.append({'slot': slot, 'payload': hex(payload), **payloads[payload]})
    if get(cache, 0x440) != raw:
        raise ValueError('cache_changed_during_sample')
    return {'cache': hex(cache), 'mode': i(8), 'secondary': i(0x3F0),
            'pending': i(0x3EC), 'lists': rows, 'table': entries,
            'owned_nodes': len(owners), 'indexed_nodes': len(entries),
            'unindexed_owned_nodes': len(owners) - len(entries), 'game_writes': 0}
