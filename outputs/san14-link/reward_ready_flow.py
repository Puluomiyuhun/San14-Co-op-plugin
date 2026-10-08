"""Observed Owner fences after paired rewards; no native simulation permit.

Successor composition of frozen reward_room_flow. The local adapter invokes
fences on its serialized execution lane. TLS handlers only carry challenges and
signed observations. The proven coverage is User/reward/save admission, never
all engine writers, all UI input, world replacement, or complete gameplay Ready.
"""
from copy import deepcopy
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import threading

import execution_journal as journal
from reward_room_flow import RewardFlow, FlowError, require, object_keys

FENCE_SCHEMA = 'san14.reward-owner-fence.v1'
COVERAGE = 'user-callback-and-reward-save-admission.v1'


def proof(key, body):
    require(type(key) is bytes and len(key) == 32, 'Missing trusted adapter key')
    return hmac.new(key, ('san14.reward-ready-report.v1\n' + journal.canonical(body)).encode('utf-8'),
                    hashlib.sha256).hexdigest()


def cut(report):
    return {key: report[key] for key in ('sequence', 'prefix_sha256', 'state_sha256')}


def validate_challenge(value, scope, attachments):
    object_keys(value, {'schema', 'id', 'scope_sha256', 'epoch', 'attachments', 'revisions', 'cut'})
    require(value['schema'] == 'san14.reward-ready-challenge.v1' and journal.hex_id(value['id'], 32),
            'Invalid fence challenge')
    require(value['scope_sha256'] == journal.digest(scope) and value['epoch'] == scope['timeline_epoch'],
            'Old planning scope')
    require(value['attachments'] == attachments and type(attachments) is dict and set(attachments) == {'A', 'B'}
            and all(journal.hex_id(v, 32) for v in attachments.values()), 'Attachment binding changed')
    object_keys(value['revisions'], {'A', 'B'})
    require(all(type(n) is int and 1 <= n < 2**31 for n in value['revisions'].values()), 'Invalid fence revisions')
    object_keys(value['cut'], {'sequence', 'prefix_sha256', 'state_sha256'})
    require(type(value['cut']['sequence']) is int and 0 <= value['cut']['sequence'] < 2**31 and
            all(journal.hex_id(value['cut'][k]) for k in ('prefix_sha256', 'state_sha256')), 'Invalid input cut')


def validate_fence(value, revision):
    object_keys(value, {'schema', 'coverage', 'revision', 'requested', 'observed', 'active', 'queued',
                       'uncertain', 'owner_stopped', 'owner_error', 'user_native_started_delta',
                       'user_native_returned_delta', 'user_finally_delta', 'all_input_held'})
    require(value['schema'] == FENCE_SCHEMA and value['coverage'] == COVERAGE, 'Unknown fence coverage')
    require(type(value['revision']) is int and value['revision'] == revision, 'Wrong fence revision')
    require(value['requested'] is True and value['observed'] is True and value['queued'] is False and
            value['uncertain'] is False and value['owner_stopped'] is False, 'Fence not observed or uncertain')
    for name, expected in (('active', 0), ('owner_error', 0), ('user_native_started_delta', 0),
                           ('user_native_returned_delta', 0), ('user_finally_delta', 1)):
        require(type(value[name]) is int and value[name] == expected, 'Unexpected callback evidence: ' + name)
    require(value['all_input_held'] is False, 'This contract cannot attest complete input exclusion')


class FenceReplica:
    """Durable local fence intent, observation, and duplicate re-observation.

    A setter result alone never completes an intent. An ambiguous request remains
    held and is not retried. No error path releases a possibly active fence.
    """
    def __init__(self, replica, path, attachments):
        self.replica = replica
        self.lock = threading.RLock()
        self.attachments = deepcopy(attachments)
        self.path = Path(path).resolve()
        require(self.attachments.get(replica.player) == replica.attachment, 'Wrong local attachment')
        with self.path.open('xb'):
            pass
        with self._db() as db:
            db.execute('CREATE TABLE fence (id INTEGER PRIMARY KEY, challenge TEXT, status TEXT, body TEXT, error TEXT)')
            db.execute('CREATE TABLE identity (value TEXT NOT NULL)')
            db.execute('INSERT INTO identity VALUES (?)', (journal.canonical(replica.journal.identity),))

    def _db(self):
        db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        # Standard sqlite context manager commits/rolls back; caller also closes.
        from contextlib import contextmanager
        @contextmanager
        def transaction():
            try:
                with db:
                    db.execute('BEGIN IMMEDIATE')
                    yield db
            finally:
                db.close()
        return transaction()

    def apply(self, challenge):
        with self.lock:
            return self._apply(challenge)

    def _checked_report(self):
        expected = self.attachments[self.replica.player]
        require(self.replica.port.attachment_id == self.replica.attachment == expected,
                'Fence replica attachment changed before observation')
        report = self.replica.report()
        require(self.replica.port.attachment_id == self.replica.attachment == expected and
                report['attachment_id'] == expected, 'Fence replica attachment changed during observation')
        return report

    def _apply(self, challenge):
        challenge = deepcopy(challenge)
        validate_challenge(challenge, self.replica.scope, self.attachments)
        canonical = journal.canonical(challenge)
        with self._db() as db:
            require(db.execute('SELECT value FROM identity').fetchone()[0] ==
                    journal.canonical(self.replica.journal.identity), 'Fence identity changed')
            existing = db.execute('SELECT * FROM fence WHERE id=1').fetchone()
            if existing:
                require(existing['challenge'] == canonical, 'Fence already belongs to another challenge')
                require(existing['status'] == 'OBSERVED', 'Fence result unknown; do not retry setter')
            else:
                before = self._checked_report()
                require(cut(before) == challenge['cut'], 'Local replica has not applied the sealed cut')
                db.execute("INSERT INTO fence VALUES(1,?,'INTENT',NULL,NULL)", (canonical,))
        revision = challenge['revisions'][self.replica.player]
        try:
            # A duplicate observation is still a new native callback. Check the
            # uninterrupted attachment BEFORE entering it, as well as afterward.
            require(cut(self._checked_report()) == challenge['cut'], 'Current replica differs from fence cut')
            if existing is None:
                response = self.replica.port.request_fence(revision)
                require(type(response) is dict and response.get('requested') is True and
                        response.get('revision') == revision, 'Fence setter failed or ambiguous')
            evidence = self.replica.port.observe_fence(revision)
            validate_fence(evidence, revision)
            report = self._checked_report()
            require(cut(report) == challenge['cut'], 'World changed while applying fence')
            body = {'schema': 'san14.reward-ready-report.v1', 'challenge': challenge,
                    'report': report, 'fence': deepcopy(evidence)}
            with self._db() as db:
                updated = db.execute("UPDATE fence SET status='OBSERVED',body=? WHERE id=1 AND challenge=? "
                                     "AND status IN ('INTENT','OBSERVED')",
                                     (journal.canonical(body), canonical))
                require(updated.rowcount == 1, 'Fence outcome changed; unknown result cannot be overwritten')
            return body
        except Exception as error:
            with self._db() as db:
                db.execute("UPDATE fence SET status='UNKNOWN',error=COALESCE(error,?) WHERE id=1", (str(error),))
            raise

    def status(self):
        with self._db() as db:
            row = db.execute('SELECT status,error FROM fence WHERE id=1').fetchone()
        return dict(row) if row else {'status': 'UNREQUESTED', 'error': None}


class ReadyRewardFlow(RewardFlow):
    """Two-stage observed-fence successor. All native work stays off TLS handlers."""
    def __init__(self, *args, fence_revisions, **kwargs):
        object_keys(fence_revisions, {'A', 'B'})
        require(all(type(v) is int and 1 <= v < 2**31 for v in fence_revisions.values()), 'Bad native revisions')
        self.fence_phase = 'OPEN'
        self.challenge = None
        self.guest_fence = None
        self.sealed_result = None
        self.revisions = deepcopy(fence_revisions)
        super().__init__(*args, **kwargs)
        self.host_fence = FenceReplica(self.host, self.folder / 'host-fence.sqlite', self.period.attachments)
        with self.db() as db:
            db.execute('CREATE TABLE finalization (id INTEGER PRIMARY KEY, challenge TEXT, status TEXT, '
                       'host_report TEXT, guest_report TEXT, result TEXT)')

    def hold(self, reason):
        super().hold(reason)
        # Revoke the coordinator's sealed state as well, so its old cut cannot
        # remain acceptable to a caller retaining the protocol coordinator.
        with self.period.lock:
            self.period.phase = 'HELD'
        self.fence_phase = 'HELD'

    def _active(self, planning=True):
        super()._active(planning)
        if planning:
            require(self.fence_phase == 'OPEN', 'Fence finalization closed planning input')

    def begin_seal(self):
        """Trusted local lane: reserve cut then request/observe A's actual fence."""
        with self.lock, self.room.lock:
            self._active()
            require(self.period.ready == {'A', 'B'}, 'Both players must be ready')
            self._pending()
            require(not any(self.period.inflight.values()), 'Commands still in flight')
            report = self._host_report()
            journal.compare_applied_prefixes(self.scope, report['sequence'], {'A': report, 'B': self.last_guest})
            self.challenge = {'schema': 'san14.reward-ready-challenge.v1', 'id': secrets.token_hex(16),
                    'scope_sha256': journal.digest(self.scope), 'epoch': self.scope['timeline_epoch'],
                    'attachments': deepcopy(self.period.attachments), 'revisions': deepcopy(self.revisions),
                    'cut': cut(report)}
            validate_challenge(self.challenge, self.scope, self.period.attachments)
            with self.db() as db:
                db.execute("INSERT INTO finalization VALUES(1,?,'INTENT',NULL,NULL,NULL)",
                           (journal.canonical(self.challenge),))
            self.fence_phase = 'WAITING_OWNER_FENCES'
            try:
                body = self.host_fence.apply(self.challenge)
                with self.db() as db:
                    db.execute("UPDATE finalization SET status='HOST_OBSERVED',host_report=? WHERE id=1",
                               (journal.canonical(body),))
                return {'status': 'WAITING_GUEST_OWNER_FENCE', 'challenge': deepcopy(self.challenge),
                        'native_gameplay_enabled': False}
            except Exception as error:
                self.hold('Host fence application uncertain: ' + str(error))
                raise

    def _receive_fence(self, player, body, signature):
        require(player == 'B', 'Only B can attest B fence')
        require(journal.hex_id(signature) and hmac.compare_digest(signature, proof(self._guest_report_key, body)),
                'Missing/invalid trusted fence attestation')
        object_keys(body, {'schema', 'challenge', 'report', 'fence'})
        require(body['schema'] == 'san14.reward-ready-report.v1' and self.challenge is not None and
                body['challenge'] == self.challenge, 'Wrong or retired fence challenge')
        validate_challenge(body['challenge'], self.scope, self.period.attachments)
        report = body['report']
        # Compare to the last paired B report without touching native code on a TLS thread.
        require(report == self.last_guest, 'Guest report differs from paired cut/attachment')
        validate_fence(body['fence'], self.challenge['revisions']['B'])
        if self.fence_phase == 'OWNER_FENCES_CONFIRMED':
            require(body == self.guest_fence, 'Confirmed fence observation changed')
            return {'status': 'ALREADY_CONFIRMED', 'native_gameplay_enabled': False}
        require(self.fence_phase == 'WAITING_OWNER_FENCES', 'No fence finalization in progress')
        with self.db() as db:
            db.execute("UPDATE finalization SET status='BOTH_REPORTED',guest_report=? WHERE id=1",
                       (journal.canonical(body),))
        self.guest_fence = deepcopy(body)
        return {'status': 'GUEST_FENCE_RECORDED', 'native_gameplay_enabled': False}

    def complete_seal(self):
        """Trusted lane: re-observe A after B attests, then close protocol input."""
        with self.lock, self.room.lock:
            # Completion can be returned again, but must revalidate local fence.
            super()._active(planning=False)
            require(self.fence_phase in ('WAITING_OWNER_FENCES', 'OWNER_FENCES_CONFIRMED') and
                    self.guest_fence is not None, 'Guest physical fence observation missing')
            try:
                host = self.host_fence.apply(self.challenge)
                journal.compare_applied_prefixes(self.scope, self.challenge['cut']['sequence'],
                        {'A': host['report'], 'B': self.guest_fence['report']})
                if self.sealed_result is not None:
                    return deepcopy(self.sealed_result)
                self._pending()
                period_cut = self.period.seal_inputs()
                self.sealed_result = {'status': 'OWNER_FENCES_CONFIRMED', 'cut': period_cut,
                        'challenge_id': self.challenge['id'], 'coverage': COVERAGE,
                        'owner_fences_observed': True, 'native_gameplay_enabled': False,
                        'all_input_held': False, 'native_simulation_permit': False,
                        'full_world_synchronization_proven': False}
                with self.db() as db:
                    db.execute("UPDATE finalization SET status='CONFIRMED',host_report=?,result=? WHERE id=1",
                               (journal.canonical(host), journal.canonical(self.sealed_result)))
                self.fence_phase = 'OWNER_FENCES_CONFIRMED'
                return deepcopy(self.sealed_result)
            except Exception as error:
                self.hold('Owner fence confirmation uncertain: ' + str(error))
                raise

    def seal(self):
        # Cannot inherit the predecessor shortcut which seals before native evidence.
        return self.begin_seal() if self.fence_phase == 'OPEN' else self.complete_seal()

    def retire(self, reason):
        """Control-plane retirement only; never unload hooks, release, or load a world."""
        with self.lock, self.room.lock:
            require(type(reason) is str and 1 <= len(reason) <= 256, 'Missing retirement reason')
            self.hold('Planning scope retired: ' + reason)
            self.fence_phase = 'RETIRED'
            self._guest_report_key = b''

    def handle(self, player, connection, request):
        with self.lock, self.room.lock:
            self._authenticated(player, connection)
            require(type(request) is dict, 'Expected object')
            action = request.get('action')
            if action not in ('reward_fence_next', 'reward_fence_report'):
                return super().handle(player, connection, request)
            super()._active(planning=False)
            if action == 'reward_fence_next':
                self._envelope(request, set())
                require(player == 'B', 'Only guest consumes fence challenge')
                return {'ok': True, 'challenge': deepcopy(self.challenge), 'native_gameplay_enabled': False}
            self._envelope(request, {'body', 'proof'})
            try:
                result = self._receive_fence(player, request['body'], request['proof'])
            except Exception as error:
                self.hold('Guest fence evidence rejected: ' + str(error))
                raise
            return {'ok': True, **result}

    def status(self):
        return {**super().status(), 'fence_phase': self.fence_phase,
                'owner_fence_coverage': COVERAGE, 'native_simulation_permit': False}
