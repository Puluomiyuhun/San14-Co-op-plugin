"""Apply one received checkpoint through a retained local rules/warm bridge.

Local callable only, not an RPC or permission verifier. Actual native evidence
remains owned by Resident and WorldLifecycle; this adapter binds their outcome
to the TLS bytes and sends an advisory ACK. It never invents a world digest,
completes the formal Journal, grants Ready, releases input, or retries a load.
"""
from copy import deepcopy
import hashlib
import os
import threading

from authoritative_sync import canonical, digest, hexid, validate_scope
from b_warm_profile_contract import Profile, validate_profile
from b_warm_room import ReceivedCheckpoint, report_warm_completion, number
from b_warm_world import validate_sample
from human_rules_world_lifecycle import NextWorldRequest


def need(ok, message):
    if not ok:
        raise ValueError(message)


def write_once(path, value):
    with path.open('xb') as out:
        raw = canonical(value)
        need(out.write(raw) == len(raw), 'Short local record write')
        out.flush()
        os.fsync(out.fileno())


class ReceivedApply:
    """Single use, scoped local session with an already held native fence.

    bridge is the retained WarmRulesBridge; tests explicitly substitute it.
    on_hold must retain the real fence and invalidate readiness, returning None
    or raising. A network disconnect or ACK failure must not release that fence.
    Native epoch and wire epoch are distinct namespaces; request.epoch remains
    the trusted lifecycle caller's native binding, never inferred from a packet.
    """
    def __init__(self, bridge, control, *, scope, epoch, period, attachments, on_hold):
        validate_scope(scope)
        need(hexid(epoch, 32) and int(epoch, 16), 'Missing wire epoch')
        number(period)
        need(type(attachments) is dict and set(attachments) == {'A', 'B'} and
             all(hexid(v, 32) for v in attachments.values()) and
             attachments['A'] != attachments['B'], 'Old attachment identities required')
        need(callable(getattr(bridge, 'replace', None)) and callable(on_hold) and
             control.player_id == 'B', 'Retained local bridge, hold port and B control required')
        self.bridge, self.control, self.on_hold = bridge, control, on_hold
        module = bridge.lifecycle.current.module
        number(module.pid, high=2**32); number(module.birth, high=2**64)
        need(bridge.warm.reader.pid == module.pid, 'Warm and rules ports target different processes')
        self.native_identity = (module.pid, module.birth)
        self.scope, self.attachments = deepcopy(scope), deepcopy(attachments)
        self.epoch, self.period = epoch, period
        self.phase, self.hold_error = 'NEW', None
        self._lock = threading.Lock()

    def _validate(self, received, request, profile, reservation):
        need(type(received) is ReceivedCheckpoint and type(request) is NextWorldRequest and
             type(profile) is Profile and not received.ack_attempted, 'Typed unused local inputs required')
        validate_profile(profile)
        context = received.context()
        m = context['manifest']
        need(canonical(context['scope']) == canonical(self.scope) and
             canonical(context['attachments']) == canonical(self.attachments) and
             (m['epoch'], m['period']) == (self.epoch, self.period), 'Foreign room/period/attachment')
        need(request.checkpoint == context['checkpoint_id'], 'Native request targets another checkpoint')
        expected_identity = dict(schema='san14.checkpoint-journal.v1', local_player='B',
            scope=self.scope, manifest=m, checkpoint_id=context['checkpoint_id'], attachments=self.attachments)
        need(canonical(received.journal.identity) == canonical(expected_identity), 'Journal context changed')
        module = self.bridge.lifecycle.current.module
        need((module.pid, module.birth) == self.native_identity and
             self.bridge.warm.reader.pid == module.pid, 'Retained process binding changed')
        if reservation is None:
            need(received.journal.status()['status'] == 'STAGED', 'Journal already reserved')
        else:
            # Only a current locally persisted reservation is accepted. This
            # does not interpret a packet as engine exclusion/load permission.
            need(type(reservation) is dict and set(reservation) ==
                 {'checkpoint_id', 'intent', 'native_load_permitted_once'} and
                 reservation['checkpoint_id'] == request.checkpoint and
                 reservation['native_load_permitted_once'] is True, 'Invalid local reservation')
            with received.journal._transaction() as db:
                row = received.journal._row(db)
                need(row['status'] == 'INTENT', 'No persisted current load reservation')
                intent = received.journal._intent(row['intent'])
                need(intent['coordinator_intent'] == reservation['intent'], 'Reservation differs from journal')
        need(m['node'] == dict(year=request.year, month=request.month, day=request.day,
                             phase='PLANNING_BOUNDARY') and
             (profile.loaded.year, profile.loaded.month, profile.loaded.day) ==
             (request.year, request.month, request.day), 'Loaded date differs')
        for side, viewer in (('A', profile.source), ('B', profile.target)):
            need(self.scope['bindings'][side] == dict(force_id=viewer.force,
                 main_district_id=viewer.district), 'Profile changes room human identity')
        need(profile.currentForce == profile.target.force, 'Rules bridge requires existing B perspective')
        raw = received.verified_file()
        need((profile.file.size, bytes(profile.file.sha256).hex()) ==
             (len(raw), hashlib.sha256(raw).hexdigest()), 'Profile references different received bytes')
        return context

    def _completion(self, outcome, request, profile):
        need(outcome['result'] == 'WARM_LOAD_AND_RULES_REBOUND' and
             (outcome['generation'], outcome['checkpoint']) == (request.generation, request.checkpoint),
             'Bridge returned another generation/checkpoint')
        for row in (outcome, outcome['details']['rules']):
            need(all(row.get(k) is False for k in ('ready', 'fence_released', 'full_world_verified')),
                 'Unsupported bridge authority')
        rules = outcome['details']['rules']
        need(rules['phase'] == 'RULES_REBOUND' and
             (rules['generation'], rules['checkpoint']) == (request.generation, request.checkpoint),
             'Rules have not rebound to loaded world')
        c = outcome['details']['completion']; accepted = c['accepted']
        need(c['profile_sha256'] == hashlib.sha256(bytes(profile)).hexdigest() and
             c['slots_restored'] is True and accepted['result'] == 'PASS_WARM_LOAD_RETIRED' and
             hexid(accepted['receipt_key']) and int(accepted['receipt_key'], 16), 'Unpaired warm acceptance')
        need(accepted['ready_authorized'] is False and accepted['full_world_verified'] is False and
             (accepted['source_force'], accepted['source_ruler'], accepted['target_force'], accepted['target_ruler']) ==
             (profile.source.force, profile.source.ruler, profile.target.force, profile.target.ruler),
             'Native outcome changes identities or claims unsupported permission')
        number(c['pid'], high=2**32); number(c['birth'], high=2**64); number(c['attempt'], high=2**64)
        need((c['pid'], c['birth']) == self.native_identity, 'Completion comes from another process lifetime')
        snap = c['snapshot']
        need(tuple(snap['date'][k] for k in ('year', 'month', 'day')) ==
             (request.year, request.month, request.day) and
             (snap['player']['force_id'], snap['player']['ruler_id']) ==
             (profile.target.force, profile.target.ruler), 'Fresh loaded viewer/date differs')
        return c

    def apply(self, received, request, profile, *, observe_loaded, prepare_rules, sample_loaded=None, reservation=None):
        with self._lock:
            need(self.phase == 'NEW', 'Local apply already consumed/held; no replay')
            self.phase = 'VALIDATING'
            try:
                context = self._validate(received, request, profile, reservation)
                need(callable(observe_loaded) and callable(prepare_rules) and
                     (sample_loaded is None or callable(sample_loaded)), 'Trusted local callbacks required')
                # Kept separate from the formal world's Journal INTENT: these
                # diagnostics do not satisfy that broader world's observations.
                # Exclusive creation survives process restart and reply loss.
                write_once(received.directory/'warm-local-load-intent.json', dict(
                    schema='san14.warm-local-load-intent.v1', checkpoint=request.checkpoint,
                    context_sha256=digest(context), profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(),
                    generation=request.generation, native_epoch=request.epoch.hex(),
                    wire_epoch=self.epoch, period=self.period, retry_allowed=False, grants_permission=False))
                self.phase = 'LOADING'
                outcome = self.bridge.replace(request, profile, received.file,
                    observe_loaded=observe_loaded, prepare_rules=prepare_rules)
                c = self._completion(outcome, request, profile)
                received.verified_file()
                write_once(received.directory/'warm-local-load-completion.json', outcome)
                if sample_loaded is not None:
                    observation = sample_loaded(received, profile, c)
                    validate_sample(observation)
                    b = observation['binding']
                    need(b == dict(scope_sha256=digest(self.scope), epoch=self.epoch, period=self.period,
                        profile_sha256=c['profile_sha256'], side='B', receipt_key=c['accepted']['receipt_key'],
                        pid=c['pid'], birth=c['birth'], viewer_force=profile.target.force,
                        viewer_ruler=profile.target.ruler), 'Partial observation is from another load')
                    need(observation['shared']['date'] == context['manifest']['node'], 'Partial observation date differs')
                    write_once(received.directory/'warm-partial-world.json', observation)
                self.phase = 'ACKNOWLEDGING'
                reply = report_warm_completion(self.control, received,
                    profile_sha256=c['profile_sha256'], receipt_key=c['accepted']['receipt_key'],
                    attempt=c['attempt'], pid=c['pid'], birth=c['birth'],
                    loaded_date=context['manifest']['node'], viewer_force=profile.target.force,
                    viewer_ruler=profile.target.ruler)
                self.phase = 'DIAGNOSTIC_COMPLETE_HELD'
                return dict(result='RECEIVED_APPLIED_AND_REPORTED', reply=reply, completion=c, ready=False,
                            full_world_verified=False, fence_released=False, next_period_authorized=False)
            except BaseException as exc:
                self.phase = 'HELD'
                try:
                    need(self.on_hold(type(exc).__name__ + ': ' + str(exc)) is None,
                         'Hold callback must return None')
                except BaseException as hold_exc:
                    self.hold_error = repr(hold_exc)
                raise
