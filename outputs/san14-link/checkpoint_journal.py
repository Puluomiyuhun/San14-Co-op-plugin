"""Durable B-side checkpoint bytes and one load attempt, NOT a native adapter.

One explicit file belongs to one offered checkpoint and both old native load
attachments. Trusted adapter observations only: none of these methods is a
network endpoint. SQLite cannot transact with SAN14. An INTENT therefore never
becomes another native permission, even after restart or callback failure.
COMPLETED means a validated adapter receipt was saved, not that a running room
has consumed it. This does not recover the host/room or certify world coverage.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

from authoritative_sync import (CheckpointReceiver, PeriodCoordinator, PARTS,
    SyncError, canonical, hexid, integer, require, sha, validate_scope,
    validate_manifest, validate_cut)


class LoadHeld(SyncError):
    """A native attempt already exists; do not replay it."""


class CheckpointJournal:
    """Explicit creation/reopening; missing history is never silently recreated.

    Typical order: stage(receiver); coordinator.received(...);
    intent = coordinator.begin_guest_load(...); reserve_load(intent, ...);
    issue native load ONCE; complete(adapter_receipt); apply_to_coordinator(c,
    fresh_host_observation, fresh_guest_observation).
    A crash at any point after reservation holds further native attempts. A
    late, independently verified result may still complete the original intent.
    """
    def __init__(self, path, scope, manifest, checkpoint_id, epoch, period, cut,
                 attachments, *, create=False):
        validate_scope(scope); validate_manifest(manifest); validate_cut(cut)
        require(hexid(epoch, 32) and integer(period, 1), 'Bad expected checkpoint epoch/period')
        # Reuse transfer boundary checks, including canonical manifest pinning.
        CheckpointReceiver(manifest, checkpoint_id, scope, epoch, period, cut)
        require(type(attachments) is dict and set(attachments) == {'A', 'B'} and
                all(hexid(v, 32) for v in attachments.values()) and
                attachments['A'] != attachments['B'], 'Bad old attachments')
        identity = {'schema': 'san14.checkpoint-journal.v1', 'local_player': 'B',
                    'scope': scope, 'manifest': manifest,
                    'checkpoint_id': checkpoint_id, 'attachments': attachments}
        self._identity = canonical(identity)
        self.path = Path(path).resolve()
        if create:
            with self.path.open('xb'):
                pass
            with self._transaction() as db:
                db.execute('CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), '
                           'identity BLOB NOT NULL, status TEXT NOT NULL, '
                           'intent BLOB, receipt BLOB)')
                db.execute('CREATE TABLE parts (name TEXT PRIMARY KEY, data BLOB NOT NULL)')
                db.execute('INSERT INTO metadata VALUES (1,?,\'EMPTY\',NULL,NULL)',
                           (self._identity,))
                db.execute('PRAGMA user_version=1')
        with self._transaction() as db:
            require(db.execute('PRAGMA quick_check').fetchone()[0] == 'ok',
                    'Checkpoint journal integrity failure')
            require(db.execute('PRAGMA user_version').fetchone()[0] == 1,
                    'Unsupported checkpoint journal version')
            self._row(db)

    @property
    def identity(self):
        return json.loads(self._identity)

    @contextmanager
    def _transaction(self):
        db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True,
                             timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _row(self, db):
        row = db.execute('SELECT * FROM metadata WHERE id=1').fetchone()
        require(row is not None and row['identity'] == self._identity,
                'Journal checkpoint/scope/attachment mismatch')
        require(row['status'] in ('EMPTY', 'STAGED', 'INTENT', 'COMPLETED'),
                'Invalid journal status')
        require((row['intent'] is not None) == (row['status'] in ('INTENT', 'COMPLETED')) and
                (row['receipt'] is not None) == (row['status'] == 'COMPLETED'),
                'Inconsistent checkpoint journal lifecycle')
        return row

    def _validate_parts(self, parts):
        require(type(parts) is dict and set(parts) == PARTS,
                'Exactly world.s14 and adapter.json are required')
        manifest = self.identity['manifest']
        for name, raw in parts.items():
            require(type(raw) is bytes and len(raw) == manifest['parts'][name]['size'] and
                    sha(raw) == manifest['parts'][name]['sha256'],
                    'Checkpoint part size/hash mismatch')

    def _parts(self, db):
        parts = {r['name']: r['data'] for r in db.execute('SELECT name,data FROM parts')}
        self._validate_parts(parts)
        return parts

    def stage(self, receiver):
        require(type(receiver) is CheckpointReceiver, 'Verified receiver required')
        identity = self.identity
        with receiver.lock:
            require(receiver.checkpoint_id == identity['checkpoint_id'] and
                    canonical(receiver.manifest) == canonical(identity['manifest']),
                    'Receiver belongs to another checkpoint')
            return self.stage_parts(receiver.verified_parts())

    def stage_parts(self, parts):
        """Rehash and commit BOTH fixed parts atomically; does not install them."""
        parts = deepcopy(parts)
        self._validate_parts(parts)
        with self._transaction() as db:
            row = self._row(db)
            if row['status'] != 'EMPTY':
                require(self._parts(db) == parts, 'Conflicting staged checkpoint')
                return {'duplicate': True, 'status': row['status']}
            require(db.execute('SELECT COUNT(*) FROM parts').fetchone()[0] == 0,
                    'Unexpected incomplete staged content')
            db.executemany('INSERT INTO parts VALUES (?,?)', sorted(parts.items()))
            db.execute("UPDATE metadata SET status='STAGED' WHERE id=1")
        return {'duplicate': False, 'status': 'STAGED'}

    def verified_parts(self):
        with self._transaction() as db:
            require(self._row(db)['status'] != 'EMPTY', 'Checkpoint not staged')
            return self._parts(db)

    def _host(self):
        identity = self.identity
        return {'attachment': identity['attachments']['A'],
                'world_sha256': identity['manifest']['world_sha256'],
                'node': identity['manifest']['node']}

    def _check_host(self, observation):
        require(type(observation) is dict and
                canonical(observation) == canonical(self._host()),
                'A changed or its boundary observation is malformed')

    def _guest(self):
        identity = self.identity
        return {'attachment': identity['attachments']['B'],
                'viewer_force': identity['scope']['bindings']['B']['force_id'],
                'safe_boundary': True}

    def _intent(self, raw):
        intent = json.loads(raw)
        require(type(intent) is dict and set(intent) == {'schema', 'checkpoint_id',
                'coordinator_intent', 'host_observation', 'guest_observation'} and
                intent['schema'] == 'san14.checkpoint-load-intent.v1' and
                intent['checkpoint_id'] == self.identity['checkpoint_id'] and
                hexid(intent['coordinator_intent'], 32), 'Invalid stored load intent')
        self._check_host(intent['host_observation'])
        require(canonical(intent['guest_observation']) == canonical(self._guest()),
                'Stored intent guest binding changed')
        return intent

    def reserve_load(self, coordinator_intent, host_observation, guest_observation):
        """Commit INTENT before returning the only permission to issue a load.

        Guest safe_boundary is a trusted native-adapter observation, not a
        conclusion made here. Reopening/status calls cannot recover a permit.
        """
        require(hexid(coordinator_intent, 32), 'Bad coordinator load intent')
        identity = self.identity
        self._check_host(host_observation)
        expected_guest = self._guest()
        require(type(guest_observation) is dict and guest_observation == expected_guest and
                type(guest_observation['viewer_force']) is int and
                guest_observation['safe_boundary'] is True,
                'B changed identity/attachment or is unsafe to load')
        intent = {'schema': 'san14.checkpoint-load-intent.v1',
                  'checkpoint_id': identity['checkpoint_id'],
                  'coordinator_intent': coordinator_intent,
                  'host_observation': deepcopy(host_observation),
                  'guest_observation': deepcopy(guest_observation)}
        with self._transaction() as db:
            row = self._row(db)
            if row['status'] in ('INTENT', 'COMPLETED'):
                raise LoadHeld('Load already reserved; native outcome must not be retried')
            require(row['status'] == 'STAGED', 'Full checkpoint not durably staged')
            self._parts(db)  # Detect changed DB bytes before issuing permission.
            db.execute("UPDATE metadata SET status='INTENT',intent=? WHERE id=1",
                       (canonical(intent),))
        return {'checkpoint_id': identity['checkpoint_id'],
                'intent': coordinator_intent, 'native_load_permitted_once': True}

    def invoke_once(self, coordinator_intent, host_observation, guest_observation, invoke):
        """Convenience callback boundary; exceptions leave the durable INTENT.

        The callback receives a permit and verified bytes; it must marshal onto
        the native game thread. No such marshaling or native call exists here.
        Its returned receipt is validated and committed before this returns.
        """
        require(callable(invoke), 'Missing trusted native callback')
        permit = self.reserve_load(coordinator_intent, host_observation, guest_observation)
        receipt = invoke(permit, self.verified_parts())
        return self.complete(receipt)

    def _validate_receipt(self, receipt, intent):
        fields = {'player', 'epoch', 'checkpoint_id', 'intent', 'world_sha256',
                  'viewer_force', 'attachment', 'host_observation'}
        require(type(receipt) is dict and set(receipt) == fields, 'Bad load receipt')
        identity = self.identity; manifest = identity['manifest']
        require(receipt['player'] == 'B' and receipt['epoch'] == manifest['epoch'] and
                receipt['checkpoint_id'] == identity['checkpoint_id'] and
                receipt['intent'] == intent['coordinator_intent'], 'Wrong load receipt binding')
        require(receipt['world_sha256'] == manifest['world_sha256'],
                'Restored world does not match authority')
        require(type(receipt['viewer_force']) is int and
                receipt['viewer_force'] == identity['scope']['bindings']['B']['force_id'],
                'Guest faction was not restored')
        require(hexid(receipt['attachment'], 32) and
                receipt['attachment'] not in identity['attachments'].values(),
                'Guest attachment is not fresh')
        self._check_host(receipt['host_observation'])

    def complete(self, receipt):
        receipt = deepcopy(receipt)
        with self._transaction() as db:
            row = self._row(db)
            require(row['status'] in ('INTENT', 'COMPLETED'), 'No durable load intent')
            intent = self._intent(row['intent'])
            self._validate_receipt(receipt, intent)
            raw = canonical(receipt)
            if row['status'] == 'COMPLETED':
                require(row['receipt'] == raw, 'Conflicting repeated load receipt')
                return {'duplicate': True, 'status': 'COMPLETED'}
            self._parts(db)
            db.execute("UPDATE metadata SET status='COMPLETED',receipt=? WHERE id=1", (raw,))
        return {'duplicate': False, 'status': 'COMPLETED'}

    def coordinator_arguments(self):
        """Inspect a completed receipt; this alone is not fresh live evidence.

        Prefer apply_to_coordinator(), which requires current observations too.
        A persisted receipt cannot establish that either game stayed loaded.
        """
        with self._transaction() as db:
            row = self._row(db)
            require(row['status'] == 'COMPLETED', 'Load result unknown; remain locked')
            self._parts(db)
            receipt = json.loads(row['receipt'])
            self._validate_receipt(receipt, self._intent(row['intent']))
        receipt['new_attachment'] = receipt.pop('attachment')
        return receipt

    def apply_to_coordinator(self, coordinator, host_observation, guest_observation):
        """Deliver/retry only the receipt to the still-existing coordinator.

        This method never reissues a native load and does not reconstruct a
        coordinator after a host restart. Native gameplay remains disabled.
        """
        require(type(coordinator) is PeriodCoordinator, 'Trusted coordinator required')
        args = self.coordinator_arguments(); identity = self.identity
        self._check_host(host_observation)
        expected_guest = {'attachment': args['new_attachment'],
                          'viewer_force': args['viewer_force'],
                          'world_sha256': args['world_sha256'],
                          'node': identity['manifest']['node'], 'safe_boundary': True}
        require(type(guest_observation) is dict and
                canonical(guest_observation) == canonical(expected_guest),
                'B no longer matches completed receipt; remain held')
        with coordinator.lock:
            require(canonical(coordinator.scope) == canonical(identity['scope']) and
                    coordinator.state_contract == identity['manifest']['state_contract'],
                    'Wrong room coordinator')
            if identity['checkpoint_id'] not in coordinator.applied_receipts:
                require(coordinator.attachments == identity['attachments'] and
                        coordinator.manifest == identity['manifest'] and
                        coordinator.period == identity['manifest']['period'] and
                        coordinator.bytes_received, 'Coordinator boundary/attachments changed')
            return coordinator.loaded(**args)

    def status(self):
        with self._transaction() as db:
            row = self._row(db)
            return {'status': row['status'], 'checkpoint_id': self.identity['checkpoint_id'],
                    'native_attempt_reserved': row['intent'] is not None,
                    'native_outcome_unknown': row['status'] == 'INTENT',
                    'native_gameplay_enabled': False, 'native_full_world_coverage_verified': False,
                    'host_restart_recovery_implemented': False}
