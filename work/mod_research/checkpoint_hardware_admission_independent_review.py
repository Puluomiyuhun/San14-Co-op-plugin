"""Offline evidence review only: reads workspace source/reports, no native calls."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    checks = {}
    hp = P / 'checkpoint_native_input_hwbp_handoff.json'
    hw = json.loads(hp.read_text(encoding='utf8'))
    bp = P / 'checkpoint_bound_forward_session_handoff.json'
    bound = json.loads(bp.read_text(encoding='utf8'))
    for prefix, data in [('hardware', hw), ('bound_forward', bound)]:
        for name, digest in data['source_sha256'].items():
            checks[f'{prefix}:source:{name}'] = sha(P / name) == digest
    checks['hardware:report'] = sha(hw['report']) == hw['report_sha256']
    checks['hardware:production_object'] = sha(P / 'checkpoint_native_input_hwbp_core.obj') == hw['production_object_sha256']
    checks['hardware:fixture_exe'] = sha(P / 'checkpoint_native_input_hwbp_fixture.exe') == hw['fixture_exe_sha256']
    checks['hardware:notes'] = sha(P / 'checkpoint_native_input_hwbp_notes.txt') == hw['notes_sha256']
    checks['bound_forward:report'] = sha(bound['fixture_report']) == bound['fixture_report_sha256']
    for key in ['fixture_binary', 'production_controller_object', 'production_session_object']:
        checks[f'bound_forward:{key}'] = sha(P / bound[key]) == bound[key + '_sha256']
    checks['bound_forward:notes'] = sha(P / 'checkpoint_bound_forward_session_notes.txt') == bound['notes_sha256']
    hr = json.loads(Path(hw['report']).read_text(encoding='utf8'))
    br = json.loads(Path(bound['fixture_report']).read_text(encoding='utf8'))
    checks['hardware:cases'] = hr['result'] == 'PASS' and len(hr['cases']) == 18 and all(x['passed'] for x in hr['cases'])
    checks['bound_forward:cases'] = br['result'] == 'PASS' and len(br['cases']) == 36 and all(x['passed'] for x in br['cases'])
    checks['bound_forward:hardware_dependency'] = bound['dependencies']['hardware_provider_handoff_sha256'] == sha(hp)
    findings = [
        {'status': 'FIXED', 'item': 'VEH classification fault', 'evidence': 'handlerBody assigns claimed only after owned thread, exact RIP/address, DR0/DR7 and DR6 cause checks. Outer SEH returns SEARCH without claimed; only observer failure following owned claim is contained.'},
        {'status': 'REVIEWED', 'item': 'Original and debug-register lifetime', 'evidence': 'Actual original is forwarded once, original exceptions retain propagation, Finish runs on owner thread. Foreign debug controls are preserved on conflict; pinned State/VEH/module and retained route avoid stale observer calls when cleanup is uncertain.'},
        {'status': 'REVIEWED', 'item': 'Deadline semantics', 'evidence': 'Deadline is sticky refusal followed by indefinite cleanup join. It is not a hard completion deadline. An OS ResumeThread failure could leave owner suspended; external timeout cannot assert restoration or permit unloading.'},
        {'status': 'FIXED_IN_NEW_CONTROLLER', 'item': 'Published wrapper before accepted BEFORE', 'evidence': 'Bound-forward RunOriginal active==0 branch forwards without provider/queue or poisoning the later attempt. Session DispatchAfter ignores a callback without paired accepted BEFORE. Actual configured dispatcher pre-admission case passed.'},
        {'status': 'REVIEWED', 'item': 'Combined mode0 and empty queue', 'evidence': 'New controller uses bound pending adapter, mode0/zero-capacity initial queue, and real own-process hardware provider. Four-argument original scope wraps actual fetch. Hardware error/restore uncertainty denies queue even if pending fields look clean. Queue resolver is authorized only by the same one-use ticket after a native queue callback.'},
    ]
    output = {
        'schema': 'san14.hardware-admission-independent-review.v1',
        'result': 'NO_NEW_BLOCKER_IN_REVIEWED_OFFLINE_SCOPE' if all(checks.values()) else 'HASH_OR_EVIDENCE_MISMATCH',
        'reviewer': 'native_save_entry',
        'game_access': False, 'process_access': False, 'tests_rerun': False,
        'hardware_handoff': str(hp), 'hardware_handoff_sha256': sha(hp),
        'bound_forward_handoff': str(bp), 'bound_forward_handoff_sha256': sha(bp),
        'checks': checks, 'findings': findings,
        'limits': ['Not a review or approval of any live launcher/carrier.', 'No all-thread scheduler fence, complete input hold, full-world verification, or actual game load is demonstrated.', 'Pinned module/VEH/state are process-lifetime resources; same-process repeat attempt is unsupported.', 'Mixed or foreign single-step exceptions continue searching; tests do not prove every debugger interaction.', 'Hardware fixture executes the exact archive fetch block in an owned OS PE; surrounding game world and other native bodies remain synthetic.'],
    }
    dest = P / ('checkpoint_hardware_admission_independent_review_' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    dest.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'path': str(dest), 'sha256': sha(dest), 'checks': len(checks), 'failed': [k for k, v in checks.items() if not v], 'result': output['result']}))
    return int(not all(checks.values()))

if __name__ == '__main__':
    raise SystemExit(main())
