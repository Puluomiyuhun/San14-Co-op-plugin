"""Independent offline review manifest; reads source and historical fixtures only."""
from pathlib import Path
from datetime import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / 'checkpoint_target_metadata_fixtures/20261006-214543-951745/result.json'


def main():
    names = ('checkpoint_target_metadata_core.cpp', 'checkpoint_target_metadata_core.h',
             'checkpoint_target_metadata_fixture.cpp', 'checkpoint_target_metadata_build.cmd',
             'native_storage_read_core.cpp', 'native_storage_read_core.h')
    content = {name: (ROOT / name).read_bytes() for name in names}
    hashes = {name: hashlib.sha256(value).hexdigest() for name, value in content.items()}
    fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
    assert fixture['result'] == 'PASS' and len(fixture['cases']) == 49
    assert all(hashes[name] == fixture['source_sha256'][name] for name in names)
    source = content[names[0]].decode('utf-8')
    anchors = {
        'all_five_owner_lists': 'for(unsigned owner=0;owner<5;++owner)',
        'require_exclusive_adapter_boundary': 'native_serial_boundary_not_proven',
        'non_atomic_commit_flag': 'commitStarted=true;',
        'count_store': 'put(m+0x18,initial.count+1)',
        'head_tail_store': 'put(initial.head+8,p)',
        'old_tail_next_store': 'put(initial.tail,p)',
        'index_store': 'put(m+0x20+c.slot*8,p+0x10)',
        'no_private_free_after_commit': 'if(allocation.pointer&&!commitStarted)',
        'same_adapter_required': 'sameAdapter(a,adapter_)',
        'same_lease_required': '&t==target_',
        'whole_graph_invalidation': 'g.digest==graphDigest_',
    }
    for key, value in anchors.items():
        assert value in source, key
    report = {
        'schema': 'san14.checkpoint-target-metadata-independent-review.v1',
        'result': 'OFFLINE_CORE_CONSISTENT_PRODUCTION_BOUNDARY_UNPROVEN',
        'reviewed_source_sha256': hashes,
        'fixture_result': str(FIXTURE), 'fixture_result_sha256': hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        'recorded_fixture_cases': 49, 'fixtures_rerun_by_review': False,
        'source_anchors': anchors,
        'supported_findings': [
            'The graph scan checks the main owner plus four category owners before publication, including overlapping heads/nodes and duplicate indexed pointers. Nonindexed category-owned nodes are retained as native-valid shape.',
            'The four stores implement main-list count, head tail, previous-tail next, and selected table payload pointer. Private node links and normalized header are checked before publication.',
            'commitStarted is set before the first store. Any subsequently caught exception is Uncertain and the cleanup path does not release the possibly transferred node. This is not atomic rollback.',
            'Durable intent precedes parser/allocation/publication. Existing intent rejects retry; a second call on the same Registration object returns Rejected instead of stale success.',
            'The local file handle and matching full bytes remain owned by VerifiedTarget. Parser receipt must reference these bytes, consume 294 bytes, and report zero new native file opens. Post-parser and precommit SHA checks detect mutation.',
            'Validate binds the same target object, same adapter callbacks/context, same boundary tokens and full five-list graph digest. Invalidation is sticky. loadAuthorized remains false.',
        ],
        'integration_risks': [
            {'id': 'partial_commit_not_fault_injected', 'status': 'UNVERIFIED_FAILURE_PATH',
             'evidence': 'Fixture explicitly asserts registrationStores==0 || registrationStores==4. No tests interrupt each of the four stores.',
             'impact': 'One/two/three completed stores can leave a count/link/index discrepancy. Uncertain/no-free is conservative, but half-publication diagnostics and recovery have not been exercised.',
             'minimum_test': 'In an isolated fixture copy, inject a caught failure after each store. Require Uncertain, consumed intent, no native/private node free or automatic rollback, and inspect the exact remaining graph. Do not run such fault injection in SAN14.'},
            {'id': 'partial_allocation_diagnostics', 'status': 'EVIDENCE_GAP',
             'evidence': 'report_.node is only set after all four stores; allocation ticket is local and not reported.',
             'impact': 'A half-commit result can be Uncertain with no direct retained allocation pointer/ticket in its report.',
             'minimum_change': 'Before production, retain an explicit diagnostic private-node address/ticket before the first publication store; keep this separate from nodeTransferred.'},
            {'id': 'boundary_tokens_are_not_a_lock', 'status': 'PRODUCTION_BLOCKER_ALREADY_DOCUMENTED',
             'evidence': 'guard only checks thread and calls Adapter::boundary; all attachment/generation/fence values are supplied by the caller.',
             'impact': 'Polling/digests detect sampled drift but cannot establish exclusive native access or detect clear/rebuild ABA with the same pointer/bytes and an unchanged caller-maintained generation.',
             'minimum_proof': 'A reviewed production adapter must own a real serial boundary through graph inspection, native presence calls, private allocation, four-store publication and readback; native clear/rescan must invalidate its generation. Synthetic token changes are not that proof.'},
            {'id': 'private_cleanup_ownership_contract', 'status': 'ADAPTER_OBLIGATION',
             'evidence': 'Once knownPrivate is true, later cleanup can call releaseNode without a fresh ownsNode check; nonalias uses the initial graph snapshot.',
             'impact': 'Safety depends on copyNode never publishing its allocation and subsequent boundary/presence callbacks not transferring it; stale true ownership alone would not suffice if that contract were violated.',
             'minimum_proof': 'Define ownsNode as exclusively private ownership, not only allocation provenance; verify native copy family does not link the node. Keep native-query callbacks side-effect-free with respect to ownership under the same fence.'},
            {'id': 'borrowed_bytes_lifetime', 'status': 'CALLER_LIFETIME_OBLIGATION',
             'evidence': 'Registration keeps a raw pointer to VerifiedTarget and no owning reference; Header and source bytes are borrowed during callbacks.',
             'impact': 'The caller must keep VerifiedTarget alive and immobile until validation/use is complete. A production parser must not retain/free the buffer or leave asynchronous readers after returning.',
             'minimum_proof': 'Use one explicit owner for registration+lease+adapter context through the controlled attempt; preserve node native ownership after transfer. No cleanup should free transferred nodes based on a stale receipt.'},
            {'id': 'future_load_identity_not_covered', 'status': 'EXPECTED_LIMIT',
             'evidence': 'Acquire verifies two native reads now; Validate later tests presence and pinned local bytes, not the future loader stream.',
             'impact': 'Registered metadata does not prove the next load consumes matching bytes.',
             'minimum_proof': 'Keep the planned 3A9227 actual native load-buffer count/SHA and per-worker binding before issuing any loaded receipt.'},
        ],
        'build_exception_scope': 'Reviewed fixture builds /EHa; a future adapter must retain appropriate SEH containment. VirtualQuery span checks are not a replacement for stable ownership during reads/writes.',
        'production_adapter_present': False, 'game_access': False, 'native_game_calls': False,
        'shared_files_modified': False, 'load_authorized': False,
    }
    path = ROOT / ('checkpoint_target_metadata_review_' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    with path.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'result': report['result'], 'cases_reviewed': 49, 'path': str(path), 'game_access': False}))


if __name__ == '__main__':
    main()
