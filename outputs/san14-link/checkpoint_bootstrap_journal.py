"""One first-period B load from A's viewer, with a distinct durable identity.

This is a local journal contract, not native evidence or an RPC. A retained
adapter must actually observe the source viewer before reservation and target
B after loading. Existing ordinary Journals are never migrated or reused.
"""
from pathlib import Path

from authoritative_sync import (CheckpointReceiver, canonical, hexid, require,
                                validate_scope, validate_manifest, validate_cut)
from checkpoint_journal import CheckpointJournal

SCHEMA = 'san14.checkpoint-bootstrap-journal.v1'
SQLITE_VERSION = 2


class BootstrapCheckpointJournal(CheckpointJournal):
    """Exact first-period source→target successor of the ordinary B journal.

    Constructor arguments match CheckpointJournal. Only the durable identity,
    SQLite version, first-period admission and pre-load viewer differ. The
    inherited completion and coordinator application still require target B.
    Reopening an INTENT never returns another native load permit.
    """
    def __init__(self, path, scope, manifest, checkpoint_id, epoch, period, cut,
                 attachments, *, create=False):
        # Explicit constructor successor: never create a v1 ordinary journal
        # and then rewrite it into bootstrap semantics.
        validate_scope(scope); validate_manifest(manifest); validate_cut(cut)
        require(hexid(epoch, 32) and type(period) is int and period == 1,
                'Bootstrap journal is restricted to the first protocol period')
        CheckpointReceiver(manifest, checkpoint_id, scope, epoch, period, cut)
        require(type(attachments) is dict and set(attachments) == {'A', 'B'} and
                all(hexid(v, 32) for v in attachments.values()) and
                attachments['A'] != attachments['B'], 'Bad old attachments')
        identity = dict(schema=SCHEMA, local_player='B', scope=scope, manifest=manifest,
            checkpoint_id=checkpoint_id, attachments=attachments,
            pre_load_viewer_force=scope['bindings']['A']['force_id'])
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
                db.execute("INSERT INTO metadata VALUES (1,?,'EMPTY',NULL,NULL)", (self._identity,))
                db.execute('PRAGMA user_version=2')
        with self._transaction() as db:
            require(db.execute('PRAGMA quick_check').fetchone()[0] == 'ok',
                    'Bootstrap journal integrity failure')
            require(db.execute('PRAGMA user_version').fetchone()[0] == SQLITE_VERSION,
                    'Unsupported bootstrap journal version; no migration allowed')
            row = self._row(db)
            # On reopen validate not just identity/status, but any persisted
            # source-view intent and target-view receipt before exposing it.
            if row['intent'] is not None:
                intent = self._intent(row['intent'])
                if row['receipt'] is not None:
                    import json
                    self._validate_receipt(json.loads(row['receipt']), intent)

    def _guest(self):
        identity = self.identity
        require(identity['schema'] == SCHEMA and
                identity['pre_load_viewer_force'] == identity['scope']['bindings']['A']['force_id'] and
                identity['manifest']['period'] == 1, 'Invalid bootstrap pre-load identity')
        return dict(attachment=identity['attachments']['B'],
                    viewer_force=identity['pre_load_viewer_force'], safe_boundary=True)
