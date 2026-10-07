"""Fixed workspace evidence and own-copy faults only; no live/native access."""
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import checkpoint_host_export_reader as h

RUN = h.HERE / 'checkpoint_host_export_tests' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')


class HostExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        RUN.mkdir(parents=True, exist_ok=False)
        cls.blobs = {key: (h.HERE / row[0]).read_bytes() for key, row in h.SOURCES.items()}
        cls.export = h.load_reviewed_host_export()

    def test_reviewed_bytes_and_provenance_stay_historical(self):
        e = self.export
        self.assertEqual(e.archive_sha256, h.ARCHIVE_SHA)
        self.assertEqual(e.archive_size, 274880)
        self.assertEqual(e.parts_for_archive_replay(h.NODE)['world.s14'], self.blobs['archive'])
        r = e.receipt
        self.assertEqual(r['provenance'], 'HISTORICAL_REVIEWED_ARCHIVE')
        self.assertEqual(r['historical_attachment']['pid'], 53908)
        self.assertEqual(r['historical_native_full_reads'], 2)
        for key in ('current_A_world_verified', 'current_attachment_verified', 'full_world_verified',
                    'native_load_authorized', 'native_gameplay_enabled', 'native_save_called_this_read',
                    'game_access', 'old_entry_reenabled'):
            self.assertIs(r[key], False)

    def test_wrong_date_phase_unknown_fields_and_boolean_are_rejected(self):
        for node in ({**h.NODE, 'day': 21}, {**h.NODE, 'day': 1}, {**h.NODE, 'year': True},
                     {**h.NODE, 'phase': 'RUNNING'}, {**h.NODE, 'epoch': '0' * 32},
                     {k: v for k, v in h.NODE.items() if k != 'phase'}):
            with self.subTest(node=node), self.assertRaises(h.HostExportError):
                self.export.parts_for_archive_replay(node)

    def test_each_changed_receipt_archive_and_intent_rejects_before_semantics(self):
        for key in h.SOURCES:
            with self.subTest(key=key):
                blobs = dict(self.blobs)
                raw = bytearray(blobs[key]); raw[-1] ^= 1; blobs[key] = bytes(raw)
                with self.assertRaisesRegex(h.HostExportError, 'unapproved_source_' + key):
                    h._validated_bundle(blobs)

    def test_missing_source_bundle_and_truncated_archive_rejected(self):
        blobs = dict(self.blobs); del blobs['publish_intent']
        with self.assertRaisesRegex(h.HostExportError, 'incomplete_source_bundle'):
            h._validated_bundle(blobs)
        blobs = dict(self.blobs); blobs['archive'] = blobs['archive'][:-1]
        with self.assertRaises(h.HostExportError): h._validated_bundle(blobs)

    def test_once_and_uncertain_receipts_cannot_semantically_pass(self):
        # Deliberately exercise internal schema checks after bypassing digest
        # checking in this test only; public reader always requires pinned SHA.
        mutations = [
            ('save_receipt', ('adapter', 'queue_calls'), 2),
            ('save_receipt', ('adapter', 'intent_flushed'), 0),
            ('save_receipt', ('adapter', 'active_callbacks'), 1),
            ('save_receipt', ('adapter', 'return_matched'), 0),
            ('save_receipt', ('old_pilot_reenabled',), True),
            ('save_receipt', ('after', 'pinned_user'), '0x11111'),
            ('publish_receipt', ('adapter', 'publish', 'writeAttempts'), 2),
            ('publish_receipt', ('adapter', 'publish', 'intentDurable'), 0),
            ('publish_receipt', ('adapter', 'readReturns'), [274880, 274879]),
            ('publish_receipt', ('adapter', 'nativeSha256'), [h.ARCHIVE_SHA, '0' * 64]),
            ('publish_receipt', ('adapter', 'callbackActive'), 1),
            ('publish_receipt', ('B_load_authorized',), True),
        ]
        for name, route, value in mutations:
            with self.subTest(name=name, route=route):
                blobs = dict(self.blobs); row = json.loads(blobs[name]); target = row
                for key in route[:-1]: target = target[key]
                target[route[-1]] = value; blobs[name] = h.canonical(row)
                # Preserve the dependent old archive hash for focused save
                # semantic validation; this cannot bypass the public pin gate.
                if name == 'save_receipt':
                    ar = json.loads(blobs['archive_receipt'])
                    ar['export_result_sha256'] = h.sha(blobs[name])
                    blobs['archive_receipt'] = h.canonical(ar)
                with self.assertRaises(h.HostExportError): h._validate_semantics(blobs)

    def test_source_file_changes_rejected_and_immutable_snapshot_preserved(self):
        path = RUN / 'owned-archive-copy.s14'
        path.write_bytes(self.blobs['archive'])
        self.assertEqual(h._read_workspace_file(path, h.ARCHIVE_SIZE, h.ARCHIVE_SHA), self.blobs['archive'])
        raw = bytearray(path.read_bytes()); raw[1000] ^= 1; path.write_bytes(raw)
        with self.assertRaisesRegex(h.HostExportError, 'source_sha256_changed'):
            h._read_workspace_file(path, h.ARCHIVE_SIZE, h.ARCHIVE_SHA)
        # The already verified object returns its retained original bytes,
        # never silently rereads a changed source during package construction.
        self.assertEqual(h.sha(self.export.parts_for_archive_replay(h.NODE)['world.s14']), h.ARCHIVE_SHA)

    def test_workspace_boundary_rejected_before_any_file_open(self):
        with self.assertRaisesRegex(h.HostExportError, 'outside_workspace'):
            h._read_workspace_file(Path('C:/outside-evidence-do-not-open/no-file'), 1, '0' * 64)
        with self.assertRaisesRegex(h.HostExportError, 'relative_parent_not_allowed'):
            h._read_workspace_file(h.HERE / '../not-an-approved-source', 1, '0' * 64)

    def test_receipt_copy_and_parts_mapping_cannot_mutate_source(self):
        r = self.export.receipt; r['archive']['node']['day'] = 21
        r['full_world_verified'] = True
        parts = self.export.parts_for_archive_replay(h.NODE); parts['world.s14'] = b'not-a-save'
        again = self.export.receipt
        self.assertEqual(again['archive']['node']['day'], 11)
        self.assertIs(again['full_world_verified'], False)
        self.assertEqual(h.sha(self.export.parts_for_archive_replay(h.NODE)['world.s14']), h.ARCHIVE_SHA)

    def test_public_loader_missing_file_fail_closed_and_reads_only_fixed_workspace(self):
        seen = []
        read = h._read_workspace_file
        def record(path, size, digest):
            seen.append(Path(path)); return read(path, size, digest)
        with patch.object(h, '_read_workspace_file', record):
            h.load_reviewed_host_export()
        self.assertEqual(set(seen), {h.HERE / r[0] for r in h.SOURCES.values()})
        with patch.object(h, '_read_workspace_file', side_effect=FileNotFoundError('fixture')):
            with self.assertRaisesRegex(h.HostExportError, 'workspace_evidence_unavailable'):
                h.load_reviewed_host_export()

    def test_real_checkpoint_package_transports_bytes_and_scope_without_world_authority(self):
        sys.path.insert(0, str(h.WORKSPACE / 'outputs' / 'san14-link'))
        from authoritative_sync import CheckpointPackage, CheckpointReceiver, POLICY
        scope = {'schema': 'san14.authoritative-sync-scope.v1', 'room_id': '1' * 32,
            'binding_epoch': '2' * 32, 'authority': 'A', 'policy': POLICY,
            'bindings': {'A': {'force_id': 12, 'main_district_id': 11}, 'B': {'force_id': 2, 'main_district_id': 2}},
            'profile': {'protocol': 'san14.room.v1', 'game_sha256': h.GAME_SHA,
                'adapter_contract': 'research-no-native-room-adapter.v1',
                'checkpoint_sha256': h.ARCHIVE_SHA, 'rules_sha256': '3' * 64}}
        cut = {'sequence': 0, 'prefix_sha256': '4' * 64}
        package = CheckpointPackage(scope, '5' * 32, 1, cut, h.NODE,
            'offline-archive-replay-not-current-world.v1', '6' * 64,
            self.export.parts_for_archive_replay(h.NODE), source_player='A')
        receiver = CheckpointReceiver(package.manifest, package.checkpoint_id, scope, '5' * 32, 1, cut)
        for chunk in reversed(list(package.chunks())): receiver.accept(chunk)
        parts = receiver.verified_parts()
        self.assertEqual(parts, self.export.parts_for_archive_replay(h.NODE))
        self.assertFalse(package.manifest['native_coverage_verified'])
        self.assertFalse(json.loads(parts['adapter.json'])['current_A_world_verified'])


def main():
    output = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(HostExportTests)
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    source_names = ('checkpoint_host_export_reader.py', 'checkpoint_host_export_test.py', 'checkpoint_host_export_notes.txt')
    report = {'schema': 'san14.host-export-reader-fixtures.v1', 'result': 'PASS' if result.wasSuccessful() else 'FAIL',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'scope': 'Fixed historical workspace evidence + own-copy faults; no game/Steam/process/window access',
        'game_access': False, 'native_save_called': False, 'full_world_verified': False,
        'current_A_world_verified': False, 'source_sha256': {n: h.sha((h.HERE / n).read_bytes()) for n in source_names},
        'pinned_evidence': deepcopy(h.SOURCES), 'test_output': output.getvalue()}
    path = RUN / 'result.json'; path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output.getvalue()); print(path)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
