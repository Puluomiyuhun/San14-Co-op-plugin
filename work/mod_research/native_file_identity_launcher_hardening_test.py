"""Pure regression of the three post-run launcher changes; no main/process calls."""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import ast
import copy
import hashlib
import json
import struct

from checkpoint_push_contract import compare_known_coverage
from native_file_identity_launcher_audit import run as broad_audit

ROOT = Path(__file__).resolve().parent
CURRENT = ROOT / 'native_file_identity_start.py'
ARCHIVED = ROOT / 'native_file_identity_launcher_versions/20261006-211329-791841/native_file_identity_start.py'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main_node(path):
    return next(n for n in ast.parse(path.read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name == 'main')


def assigned(main, name):
    return next(n for n in ast.walk(main) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))


def exec_nodes(nodes, env):
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<exact-launcher-AST-offline>', 'exec'), env)


class FakePath:
    def __truediv__(self, key):
        return self

    def exists(self):
        return False


def run():
    current = main_node(CURRENT)
    archived = main_node(ARCHIVED)
    cases = []

    def check(name, condition):
        assert condition, name
        cases.append({'case': name, 'passed': True})

    # The broad audit executes definitions and fake-kernel tests only, never main().
    broad = broad_audit(CURRENT)
    old = broad_audit(ARCHIVED)
    check('23_existing_ABI_buffer_and_saved_run_checks', broad['case_count'] == 23 and old['case_count'] == 23)
    check('archived_version_hash_pinned', digest(ARCHIVED) == 'ce83851d8cfe31514c99b80d07cf382a345a3d5ac7084315a7056884707cb9e4')
    check('old_terminal_gap_and_current_fix', old['terminal_gate_edge']['can_accept_good_first_terminal_on_deadline']
          and not broad['terminal_gate_edge']['can_accept_good_first_terminal_on_deadline'])

    passed = assigned(current, 'passed').value
    for stable, expected in ((False, False), (True, True)):
        env = dict(installed=0, report_ok=lambda *a: True, value={}, args=SimpleNamespace(read=True), before={},
                   restored=True, after={'result': 'PASS'}, coverage={'matched': True}, files_equal=True, stable_terminal=stable)
        actual = bool(eval(compile(ast.Expression(passed), '<passed-expr>', 'eval'), env))
        check('current_pass_requires_stability_' + str(stable), actual == expected)
    for bad_key in ('restored', 'files_equal'):
        env[bad_key] = False
        check('stable_does_not_override_' + bad_key, not eval(compile(ast.Expression(passed), '<passed-expr>', 'eval'), env))
        env[bad_key] = True

    # Execute the exact source-comparison assignment, evidence save and assert.
    outer_try = next(n for n in current.body if isinstance(n, ast.Try))
    source_assign = assigned(current, 'source_coverage')
    start = outer_try.body.index(source_assign)
    source_nodes = outer_try.body[start:start + 3]
    assert isinstance(source_nodes[2], ast.Assert)
    intent = assigned(current, 'intent')
    check('source_gate_precedes_once_and_install', source_assign.lineno < intent.lineno < assigned(current, 'installed').lineno)
    source = load(ROOT / 'checkpoint_push_runs/20261006-203111-687580/known-after.json')
    original = load(ROOT / 'native_file_identity_runs/20261006-211028-162474/known-before.json')

    def source_case(name, mutate, expected):
        candidate = copy.deepcopy(original)
        mutate(candidate)
        saved = []
        env = dict(compare_known_coverage=compare_known_coverage, load=lambda _: copy.deepcopy(source),
                   SOURCE_RESULT=ROOT / 'unused/result.json', full_before=candidate, run=FakePath(),
                   save=lambda path, value: saved.append(copy.deepcopy(value)))
        failed = False
        try:
            exec_nodes(source_nodes, env)
        except AssertionError:
            failed = True
        check(name, (not failed) == expected and len(saved) == 1 and saved[0]['matched'] == expected)

    source_case('real_source_and_dry_capture_match', lambda _: None, True)
    source_case('source_record_change_rejected_and_saved', lambda c: c['objects']['records'].popitem(), False)
    source_case('source_context_date_change_rejected', lambda c: c['context']['snapshot']['date'].__setitem__('day', 21), False)
    source_case('source_rng_change_rejected', lambda c: c['objects'].__setitem__('global_rng', 123), False)
    source_case('source_tile_change_rejected', lambda c: c['tiles'].__setitem__('ordered_payload_hex', 'ff' + c['tiles']['ordered_payload_hex'][2:]), False)
    source_case('only_allocator_pool_change_permitted', lambda c: c['objects']['pools'].__setitem__('0x19e1c20', 987654), True)

    # Execute the exact exception handler without its final re-raise, using fake
    # Stop/GetReport/memory/page providers. It cannot create threads or open files.
    handler = outer_try.handlers[0]
    assert isinstance(handler.body[-1], ast.Raise)
    for label, stop_error, snapshot_error, memory_error, page_error, has_api in (
        ('all_cleanup_succeeds', False, False, False, False, True),
        ('stop_failure_keeps_snapshot_and_memory', True, False, False, False, True),
        ('snapshot_failure_keeps_stop_and_memory', False, True, False, False, True),
        ('both_remote_errors_still_read_memory', True, True, False, False, True),
        ('memory_error_is_retained', False, False, True, False, True),
        ('page_error_retains_completed_slots', False, False, False, True, True),
        ('no_api_no_cleanup_calls', False, False, False, False, False),
    ):
        calls = []
        saved = []
        def stop(*args):
            calls.append('stop')
            if stop_error: raise OSError('mock stop failure')
            return 0
        def snapshot(*args):
            calls.append('snapshot')
            if snapshot_error: raise OSError('mock snapshot failure')
            return {'state': 6, 'scope': 'mock only'}
        def read(*args):
            calls.append('memory')
            if memory_error: raise OSError('mock memory failure')
            return struct.pack('<Q', 0x1234)
        def pages(*args):
            calls.append('pages')
            if page_error: raise OSError('mock page failure')
            return {'mock': True}
        env = dict(api=SimpleNamespace(call_adapter=stop) if has_api else None, stop_address=77, report_address=78,
                   reader=SimpleNamespace(memory=SimpleNamespace(base=0x100000, read=read)), get_report=snapshot,
                   hook_pages=pages, run=FakePath(), save=lambda p, value: saved.append(copy.deepcopy(value)),
                   error=RuntimeError('original failure'), value=None, struct=struct)
        exec_nodes(handler.body[:-1], env)
        cleanup = saved[0]['cleanup']
        ok = len(saved) == 1 and saved[0]['result'] == 'ERROR_NO_AUTO_RETRY' and saved[0]['error'] == 'original failure'
        ok &= cleanup['attempted'] == has_api and saved[0]['two_observed_native_reads_matched'] is False
        if has_api:
            ok &= ('stop' in calls and 'snapshot' in calls and 'memory' in calls)
            ok &= bool(cleanup['stop_error']) == stop_error and bool(cleanup['snapshot_error']) == snapshot_error
            ok &= cleanup['snapshot_acquired'] == (not snapshot_error)
            ok &= ('memory_query_error' in cleanup) == (memory_error or page_error)
            ok &= (cleanup['actual_slots'] is not None) == (not memory_error)
            ok &= (cleanup['actual_pages'] is not None) == (not memory_error and not page_error)
        else:
            ok &= not calls and cleanup['actual_slots'] is None and cleanup['actual_pages'] is None
        check('cleanup_' + label, ok)

    return {
        'schema': 'san14.native-file-launcher-hardening-offline.v1', 'result': 'PASS',
        'current_launcher_sha256': digest(CURRENT), 'archived_executed_launcher_sha256': digest(ARCHIVED),
        'cases': cases, 'case_count': len(cases), 'inherited_broad_audit_cases': broad['case_count'],
        'actual_runs': broad['actual_runs'], 'A_export_to_dry_coverage': broad['A_export_to_dry_coverage'],
        'clarification_of_prior_audit': {
            'prior_report': 'native_file_identity_launcher_audit_20261006-211455-552025.json',
            'historical_findings_apply_to': str(ARCHIVED),
            'prior_current_hash_already_contains_three_fixes': True,
            'current_three_fixes': ['final_pass_requires_stable_terminal', 'A_known_source_compare_before_once',
                                   'independent_stop_snapshot_memory_cleanup_evidence'],
            'old_results_modified': False, 'actual_once_retried': False,
        },
        'limits': ['Tests execute exact AST portions with pure fake services, not a live/native lifecycle.',
                   'Original real dry/read PASS remains separate from these post-run launcher changes.',
                   'Python once uses exclusive file creation without fsync; crash durability is not proven.',
                   'Observed native file identity does not authorize B load or prove future load bytes/full world.'],
        'game_access': False, 'native_calls': False, 'launcher_modified': False,
    }


if __name__ == '__main__':
    report = run()
    output = ROOT / ('native_file_identity_launcher_hardening_test_' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'result': report['result'], 'cases': report['case_count'],
                      'broad_audit_cases': report['inherited_broad_audit_cases'], 'output': str(output), 'game_access': False}))
