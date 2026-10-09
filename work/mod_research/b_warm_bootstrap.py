"""Explicit first A-view to B-view warm load, then the existing second bank.

Starts with real installed two-human rules in the source view. This is a local
successor, not a rule-free launcher, native permission packet or three-bank
implementation. Old code and claims remain resident and are never reset.
"""
from contextlib import ExitStack
import hashlib
import secrets
import time

import b_warm_staging as files
from b_warm_rules_bridge import WarmRulesBridge
from b_warm_received_apply import ReceivedApply
from b_warm_profile_contract import Profile, validate_profile
from b_warm_room import ReceivedCheckpoint
from authoritative_sync import canonical
from human_rules_world_lifecycle import (
    Config, NextWorldRequest, WorldGeneration, ResidentPort, check_port)


class BootstrapRulesBridge(WarmRulesBridge):
    """First replacement explicitly changes viewer; all later rules stay strict."""
    def validate_current_profile(self, profile):
        files.need(type(profile) is Profile, 'Typed profile required')
        validate_profile(profile)
        old = self.lifecycle.current
        c = Config.from_buffer_copy(old.world.config)
        expected = profile.source.force if not self.completed else profile.target.force
        files.need(c.viewer == profile.currentForce == expected,
                   'Current rules/viewer do not match the explicit bootstrap stage')
        files.need(dict(zip(c.force, c.main_district)) == {
            profile.source.force: profile.source.district,
            profile.target.force: profile.target.district}, 'Human faction/district bindings differ')
        files.need(self.warm.reader.pid == old.module.pid, 'Warm and rules process differ')

    def _load_first(self, request, profile, source):
        folder = self.records / ('generation-' + str(request.generation))
        folder.mkdir()
        bank = self.warm.open_bank(0)
        proposed = files.plan(source, self.target.parent,
                              bytes(profile.file.sha256).hex(), profile.file.size)
        evidence = folder/'bootstrap-rules-restored.json'
        files.save_new(evidence, files.canonical(dict(history=self.lifecycle.history,
            checkpoint=request.checkpoint, generation=request.generation, permission=False)))
        permit = folder/'file-authorization.json'
        files.save_new(permit, files.canonical(dict(
            schema='san14.local-file-overwrite-authorization.v1', nonce=secrets.token_hex(16),
            plan_sha256=files.digest(files.canonical(proposed)), expires_unix=int(time.time())+120,
            retirement_reference=str(evidence), retirement_sha256=files.digest(evidence.read_bytes()))))
        staged = files.apply(proposed, permit, files.digest(permit.read_bytes()), folder)
        files.need(staged['result'] == 'STAGED', 'First checkpoint staging incomplete')
        with ExitStack() as held:
            files.pin_parents(held, self.target)
            handle = held.enter_context(files.Handle(self.target))
            identity, raw = handle.snapshot()
            files.need((identity['size'], identity['sha256']) ==
                       (profile.file.size, bytes(profile.file.sha256).hex()), 'Staged bootstrap file differs')
            try:
                completion = self.warm.load(bank, profile, raw)
                files.need(type(completion) is dict and
                           (completion['pid'], completion['birth']) ==
                           (self.lifecycle.current.module.pid, self.lifecycle.current.module.birth) and
                           completion['profile_sha256'] == hashlib.sha256(bytes(profile)).hexdigest() and
                           completion['slots_restored'] is True and
                           completion['accepted']['result'] == 'PASS_WARM_LOAD_RETIRED',
                           'First native completion is not paired to the rules process/profile')
                files.need(handle.snapshot()[0] == identity, 'Bootstrap file changed during load')
            except BaseException:
                self.warm.abort()  # keep file lease during bounded known-completed Stop
                raise
        return dict(file_identity=identity, completion=completion, staging=staged)

    def replace(self, request, profile, source, *, observe_loaded, prepare_rules):
        with self._lock:
            files.need(self.phase == 'ACTIVE', 'Bootstrap already consumed/held')
            if self.completed:
                try:
                    self.validate_current_profile(profile)
                except BaseException as exc:
                    self.phase = self.lifecycle.phase = 'HELD'
                    self.lifecycle.held_reason = type(exc).__name__ + ': ' + str(exc)
                    try:
                        check_port(self.lifecycle._on_hold, self.lifecycle.held_reason)
                    except BaseException as hold_exc:
                        self.lifecycle.hold_error = repr(hold_exc)
                    raise
                return super().replace(request, profile, source,
                    observe_loaded=observe_loaded, prepare_rules=prepare_rules)
            life = self.lifecycle
            with life._lock:
                files.need(life.phase == 'ACTIVE', 'Existing rule lifecycle is not active')
                self.phase = 'REPLACING'
                try:
                    files.need(type(request) is NextWorldRequest and callable(observe_loaded) and
                               callable(prepare_rules), 'Typed first request and trusted callbacks required')
                    self.validate_current_profile(profile)
                    old = life.current
                    before = Config.from_buffer_copy(old.world.config)
                    files.need(request.generation == old.world.generation+1 and
                               request.checkpoint != old.world.checkpoint and
                               (request.year, request.month, request.day) ==
                               (profile.loaded.year, profile.loaded.month, profile.loaded.day),
                               'First checkpoint generation/date differs')
                    check_port(life._guard)
                    life.phase = 'RESTORING'
                    life.history.append(old.restore())
                    check_port(life._guard)
                    old.retired = True
                    life.phase = 'LOAD_ALLOWED'
                    life.history.append(dict(operation='BOOTSTRAP_LOAD_ALLOWED', generation=request.generation))
                    check_port(life._guard)
                    life.phase = 'LOADING'
                    result = self._load_first(request, profile, source)
                    check_port(life._guard)
                    life.phase = 'OBSERVING_LOADED_WORLD'
                    observed = observe_loaded(request)
                    files.need(type(observed) is WorldGeneration and
                               (observed.generation, observed.checkpoint) ==
                               (request.generation, request.checkpoint), 'Observed different first world')
                    after = Config.from_buffer_copy(observed.config)
                    files.need(bytes(after.epoch) == request.epoch and
                               (after.year, after.month, after.day) ==
                               (request.year, request.month, request.day) and
                               after.viewer == profile.target.force, 'Loaded B epoch/date/viewer differs')
                    files.need(before.image == after.image and bytes(before.room) == bytes(after.room) and
                               bytes(before.rules_digest) == bytes(after.rules_digest) and
                               list(before.force) == list(after.force) and
                               list(before.main_district) == list(after.main_district) and
                               before.income_key5 == after.income_key5 and
                               before.world_option8 == after.world_option8,
                               'Bootstrap changed room/human bindings/settings')
                    check_port(life._guard)
                    life.history.append(dict(operation='BOOTSTRAP_TARGET_OBSERVED', generation=request.generation,
                                             root=after.root, world=after.world, viewer=after.viewer))
                    life.phase = 'REBINDING'
                    new = prepare_rules(observed)
                    files.need(type(new) is ResidentPort, 'Actual prepared resident rule port required')
                    life.retained.append(new)
                    files.need(new.world == observed and new.module.pid == old.module.pid and
                               new.module.birth == old.module.birth and
                               new.module.source_kind == old.module.source_kind and
                               new.module.module not in life._used_modules and
                               new.module.nonce not in life._used_nonces, 'New rule module identity differs')
                    life._used_modules.add(new.module.module)
                    life._used_nonces.add(new.module.nonce)
                    check_port(life._guard)
                    life.history.append(new.install())
                    check_port(life._guard)
                    life.current = new
                    life.phase = 'ACTIVE'
                    result['rules'] = dict(phase='RULES_REBOUND', generation=observed.generation,
                        checkpoint=observed.checkpoint, ready=False, fence_released=False,
                        full_world_verified=False, source_kind=new.module.source_kind)
                    self.completed.append(result)
                    self.phase = 'ACTIVE'
                    return dict(result='WARM_LOAD_AND_RULES_REBOUND', generation=request.generation,
                        checkpoint=request.checkpoint, details=result, bootstrap=True, ready=False,
                        fence_released=False, full_world_verified=False)
                except BaseException as exc:
                    self.phase = life.phase = 'HELD'
                    life.held_reason = type(exc).__name__ + ': ' + str(exc)
                    try:
                        check_port(life._on_hold, life.held_reason)
                    except BaseException as hold_exc:
                        life.hold_error = repr(hold_exc)
                    raise


class BootstrapReceivedApply(ReceivedApply):
    """Explicit pre-load successor; no fabricated target-view validation profile.

    The unchanged parent owns intents, native result pairing and ACK. Only the
    first current-view constraint differs, checked against the retained rules.
    """
    def _validate(self, received, request, profile, reservation):
        files.need(type(self.bridge) is BootstrapRulesBridge, 'Explicit bootstrap bridge required')
        # The frozen formal Journal requires B's target viewer before reserve.
        # A source-view bootstrap cannot truthfully satisfy that precondition.
        files.need(self.bridge.completed or reservation is None,
                   'First source-view bootstrap needs its own formal journal boundary; diagnostic only')
        files.need(type(received) is ReceivedCheckpoint and type(request) is NextWorldRequest and
                   type(profile) is Profile and not received.ack_attempted, 'Typed unused local inputs required')
        self.bridge.validate_current_profile(profile)
        context = received.context(); m = context['manifest']
        files.need(canonical(context['scope']) == canonical(self.scope) and
                   canonical(context['attachments']) == canonical(self.attachments) and
                   (m['epoch'], m['period']) == (self.epoch, self.period), 'Foreign room/period/attachment')
        files.need(request.checkpoint == context['checkpoint_id'], 'Native request targets another checkpoint')
        expected = dict(schema='san14.checkpoint-journal.v1', local_player='B', scope=self.scope,
                        manifest=m, checkpoint_id=context['checkpoint_id'], attachments=self.attachments)
        files.need(canonical(received.journal.identity) == canonical(expected), 'Journal context changed')
        module = self.bridge.lifecycle.current.module
        files.need((module.pid, module.birth) == self.native_identity and
                   self.bridge.warm.reader.pid == module.pid, 'Retained process binding changed')
        if reservation is None:
            files.need(received.journal.status()['status'] == 'STAGED', 'Journal already reserved')
        else:
            files.need(type(reservation) is dict and set(reservation) ==
                       {'checkpoint_id', 'intent', 'native_load_permitted_once'} and
                       reservation['checkpoint_id'] == request.checkpoint and
                       reservation['native_load_permitted_once'] is True, 'Invalid local reservation')
            with received.journal._transaction() as db:
                row = received.journal._row(db)
                files.need(row['status'] == 'INTENT', 'No persisted current load reservation')
                intent = received.journal._intent(row['intent'])
                files.need(intent['coordinator_intent'] == reservation['intent'], 'Reservation differs from journal')
        files.need(m['node'] == dict(year=request.year, month=request.month, day=request.day,
                                    phase='PLANNING_BOUNDARY') and
                   (profile.loaded.year, profile.loaded.month, profile.loaded.day) ==
                   (request.year, request.month, request.day), 'Loaded date differs')
        for side, viewer in (('A', profile.source), ('B', profile.target)):
            files.need(self.scope['bindings'][side] == dict(force_id=viewer.force,
                       main_district_id=viewer.district), 'Profile changes room human identity')
        raw = received.verified_file()
        files.need((profile.file.size, bytes(profile.file.sha256).hex()) ==
                   (len(raw), hashlib.sha256(raw).hexdigest()), 'Profile references different received bytes')
        return context
