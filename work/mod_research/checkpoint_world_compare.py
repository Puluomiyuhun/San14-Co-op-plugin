"""Offline, scope-explicit comparison of captured SAN14 state.

The result is diagnostic evidence only. Equal observed fields never mean full
world equality and never authorize the existing GuestTransition to release.
No process, window, device or live-game reader is imported or opened.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from checkpoint_world_snapshot_reader import Snapshot, read_snapshot

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
SUPPORTED_BUILD = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def small(value, limit=180):
    text = canonical(value).decode('utf-8')
    return value if len(text) <= limit else {'preview': text[:limit], 'truncated': True,
                                           'sha256': digest(value)}


def source_build(snapshot):
    return snapshot.metadata.get('exe_sha256', snapshot.metadata.get('build_sha256'))


def display_byte(key, offset, enabled):
    # The only exception is the already audited army display object pointer.
    # No heuristic pointer detector, economic/RNG suppression, or city exception.
    return enabled and key.startswith('army:') and 0x148 <= offset < 0x150


def record_payload(key, segments, normalize):
    result = []
    previous = -1
    for segment in sorted(segments, key=lambda row: row.offset):
        if type(segment.offset) is not int or segment.offset < 0 or segment.offset < previous or not segment.data:
            raise ValueError('Overlapping, empty or invalid captured record segments')
        raw = bytes(0 if display_byte(key, segment.offset+i, normalize) else byte
                    for i, byte in enumerate(segment.data))
        result.append((segment.offset, raw))
        previous = segment.offset+len(segment.data)
    return result


def observed_hash(snapshot, normalize):
    hasher = hashlib.sha256()
    for key in sorted(snapshot.records):
        hasher.update(canonical(['record', key]))
        for offset, raw in record_payload(key, snapshot.records[key], normalize):
            hasher.update(canonical([offset, len(raw)]))
            hasher.update(raw)
    hasher.update(canonical(['fields', snapshot.fields]))
    return hasher.hexdigest()


def changed_fields(left, right, path=''):
    """Lists retain order. Missing members are differences, never intersections."""
    if type(left) is not type(right):
        yield path, left, right, 'type'
    elif isinstance(left, dict):
        for key in sorted(left.keys() | right.keys()):
            child = path+'/'+key.replace('~', '~0').replace('/', '~1')
            if key not in left:
                yield child, None, right[key], 'added'
            elif key not in right:
                yield child, left[key], None, 'missing'
            else:
                yield from changed_fields(left[key], right[key], child)
    elif isinstance(left, list):
        for index in range(max(len(left), len(right))):
            child = path+'/'+str(index)
            if index >= len(left):
                yield child, None, right[index], 'added'
            elif index >= len(right):
                yield child, left[index], None, 'missing'
            else:
                yield from changed_fields(left[index], right[index], child)
    elif canonical(left) != canonical(right):
        yield path, left, right, 'value'


def compare(left: Snapshot, right: Snapshot, *, max_examples=80):
    if type(max_examples) is not int or not 0 <= max_examples <= 1000:
        raise ValueError('max_examples must be between 0 and 1000')
    normalize = source_build(left) == source_build(right) == SUPPORTED_BUILD
    records_a = set(left.records)
    records_b = set(right.records)
    removed = sorted(records_a-records_b)
    added = sorted(records_b-records_a)
    result = dict(schema='san14.observed-world-comparison.v1', result='PENDING',
        full_world_verified=False, native_gameplay_enabled=False, authorize_release=False,
        game_accessed=False, sources=[dict(path=s.source_path, sha256=s.source_sha256,
            format=s.format, metadata=s.metadata, coverage=s.coverage) for s in (left, right)],
        exception_policy=dict(army_display_pointer_148_150=normalize,
            evidence='checkpoint-coverage-contract.txt / checkpoint-coverage-audit.py',
            no_other_record_bytes_excluded=True),
        diagnostics_excluded_from_observed_equality=dict(
            left_keys=sorted(left.diagnostic_fields), right_keys=sorted(right.diagnostic_fields),
            reason='Reader-classified local identity/capture/transcript evidence; separately compared below, not a full-world exemption.'),
        removed_records=dict(count=len(removed), examples=removed[:max_examples]),
        added_records=dict(count=len(added), examples=added[:max_examples]),
        record_layout_mismatches=[], byte_difference_examples=[], display_pointer_examples=[],
        field_difference_examples=[], diagnostic_difference_examples=[], metadata_difference_examples=[], counts={})
    counts = Counter(raw_changed_bytes=0, unresolved_changed_bytes=0, display_changed_bytes=0,
        changed_records=0, layout_mismatches=0, changed_fields=0, equal_sampled_bytes=0)
    domain_changes = Counter()
    for key in sorted(records_a & records_b):
        a = record_payload(key, left.records[key], False)
        b = record_payload(key, right.records[key], False)
        if [(o, len(v)) for o,v in a] != [(o, len(v)) for o,v in b]:
            counts['layout_mismatches'] += 1
            if len(result['record_layout_mismatches']) < max_examples:
                result['record_layout_mismatches'].append(key)
            continue
        changed = False
        for (offset, x), (_, y) in zip(a, b):
            for index, (before, after) in enumerate(zip(x, y)):
                if before == after:
                    counts['equal_sampled_bytes'] += 1
                    continue
                changed = True
                counts['raw_changed_bytes'] += 1
                absolute = offset+index
                row = dict(record=key, offset=absolute, before=before, after=after)
                if display_byte(key, absolute, normalize):
                    counts['display_changed_bytes'] += 1
                    examples = result['display_pointer_examples']
                else:
                    counts['unresolved_changed_bytes'] += 1
                    domain_changes[key.split(':', 1)[0]] += 1
                    row['classification'] = ('economy_rule_dependent_not_ignorable'
                        if key.startswith('city:') and 0xA0 <= absolute < 0xA8
                        else 'unresolved_shared_or_unknown')
                    examples = result['byte_difference_examples']
                if len(examples) < max_examples:
                    examples.append(row)
        counts['changed_records'] += int(changed)
    for path, before, after, change in changed_fields(left.fields, right.fields):
        counts['changed_fields'] += 1
        if len(result['field_difference_examples']) < max_examples:
            result['field_difference_examples'].append(dict(path=path, change=change,
                                                            before=small(before), after=small(after)))
    # Metadata are printed independently: timestamps, process addresses and local
    # viewer labels do not silently become shared state. Different build/date/
    # recorded boundary also blocks an equal-context diagnosis.
    diagnostic_count = 0
    for path, before, after, change in changed_fields(left.diagnostic_fields, right.diagnostic_fields):
        diagnostic_count += 1
        if len(result['diagnostic_difference_examples']) < max_examples:
            result['diagnostic_difference_examples'].append(dict(path=path, change=change,
                before=small(before), after=small(after)))
    result['local_diagnostic_difference_count'] = diagnostic_count
    context_keys = ('exe_sha256','build_sha256','date','state_stack','in_player_strategy','capture_stage','phase')
    context_differences = []
    for key in context_keys:
        a, b = left.metadata.get(key), right.metadata.get(key)
        if canonical(a) != canonical(b):
            context_differences.append(dict(field=key, before=a, after=b))
    result['metadata_difference_examples'] = context_differences
    result['recorded_context_equal'] = not context_differences
    result['same_native_phase_independently_verified'] = False
    result['counts'] = dict(counts)
    result['unresolved_bytes_by_domain'] = dict(domain_changes)
    result['observed_hashes'] = [observed_hash(s, normalize) for s in (left, right)]
    equal = not (removed or added or counts['layout_mismatches'] or counts['unresolved_changed_bytes']
                 or counts['changed_fields'] or context_differences)
    result['observed_fields_equal'] = equal
    result['result'] = 'MATCHED_OBSERVED_FIELDS_ONLY' if equal else 'OBSERVED_DIFFERENCES_OR_SCOPE_MISMATCH'
    result['examples_limited_to'] = max_examples
    result['limitation'] = ('Archived partial captures; matching hashes do not cover unsampled state, '
        'prove a stable same-phase native boundary, establish sidecar/rule equality or authorize loading/release.')
    return result


def write_report(report, path):
    path = Path(path)
    output = (path if path.is_absolute() else WORKSPACE/path).resolve()
    output.relative_to(WORKSPACE)
    for source in report['sources']:
        original = Path(source['path']).resolve()
        if output == original or (output.exists() and original.exists() and output.samefile(original)):
            raise ValueError('Comparison output cannot overwrite an input archive or file alias')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare(read_snapshot(args.before), read_snapshot(args.after))
    output = write_report(report, args.output)
    print(json.dumps(dict(result=report['result'], counts=report['counts'],
        full_world_verified=False, output=str(output)), ensure_ascii=False))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
