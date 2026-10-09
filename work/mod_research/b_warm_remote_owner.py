"""Retained B native/rules owner behind the authenticated completion client.

Construction does not attach/inject/arm anything. The caller supplies one
already initialized Resident, installed WorldLifecycle and real held boundary.
No empty guard, room JSON or callback return is an engine exclusion proof.
"""
from copy import deepcopy
import threading

from authoritative_sync import canonical, validate_scope
from checkpoint_journal import CheckpointJournal
from checkpoint_bootstrap_journal import BootstrapCheckpointJournal
from checkpoint_room_client import RoomConnection
from b_warm_bootstrap import BootstrapRulesBridge
from b_warm_rules_bridge import WarmRulesBridge
from b_warm_bootstrap_protocol import FormalBootstrapReceivedApply
from b_warm_received_apply import ReceivedApply, need
from b_warm_remote_completion import RemoteGuestCompletion
from b_warm_profile_contract import Profile, validate_profile
from b_warm_room import ReceivedCheckpoint
from human_rules_world_lifecycle import WorldLifecycle, Config, NextWorldRequest, check_port
import b_warm_world as world


class RetainedRemoteOwner:
    def __init__(self, bridge, control, key, *, scope, read_birth, observe_loaded,
                 prepare_rules, guard_check, on_hold):
        need(type(bridge) in (BootstrapRulesBridge, WarmRulesBridge) and
             type(bridge.lifecycle) is WorldLifecycle, 'Actual retained bridge/lifecycle required')
        need(type(control) is RoomConnection and control.player_id == 'B', 'Actual B TLS control required')
        validate_scope(scope)
        need(all(callable(f) for f in (read_birth, observe_loaded, prepare_rules, guard_check, on_hold)),
             'Retained native observation, rules preparation and guard ports required')
        need(guard_check is bridge.lifecycle._guard, 'Same lifecycle execution guard required')
        need(bridge.phase == bridge.lifecycle.phase == 'ACTIVE' and not bridge.completed,
             'Owner starts before this Resident consumes bank 0')
        self.bridge, self.control = bridge, control
        self.lifecycle, self.warm, self.reader = bridge.lifecycle, bridge.warm, bridge.warm.reader
        self._owners = (bridge, self.lifecycle, self.warm, self.reader, control)
        self.scope = deepcopy(scope); self._scope = canonical(scope)
        self.read_birth, self.observe_loaded, self.prepare_rules = read_birth, observe_loaded, prepare_rules
        self.guard_check, self.on_hold = guard_check, on_hold
        self.native_identity = (self.lifecycle.current.module.pid, self.lifecycle.current.module.birth)
        self.image = self.reader.memory.base
        self.phase, self.held_reason, self.hold_error = 'ACTIVE', None, None
        self.period, self.epoch, self.attachments = 1, None, None
        self.sessions, self.samples, self.history = [], [], []
        self._active = None; self._lock = threading.RLock()
        self.remote = RemoteGuestCompletion(control, key, verify_held=self._verify_held)
        self._check()

    def _check(self):
        need(self.phase != 'HELD', 'Retained B owner is held; no replay/reconstruction recovery')
        need(self._owners == (self.bridge, self.bridge.lifecycle, self.bridge.warm, self.bridge.warm.reader, self.control) and
             self.bridge.lifecycle is self.lifecycle and self.bridge.warm is self.warm and self.warm.reader is self.reader,
             'Retained owner graph changed')
        need(self.guard_check is self.lifecycle._guard and canonical(self.scope) == self._scope,
             'Retained guard/scope changed')
        check_port(self.guard_check)
        module = self.lifecycle.current.module
        need((module.pid, module.birth) == self.native_identity == (self.reader.pid, self.read_birth()) and
             self.reader.memory.base == self.image and self.reader.sha256 == world.objects.GAME_SHA256,
             'Native process incarnation/image changed')
        c = Config.from_buffer_copy(self.lifecycle.current.world.config)
        need(c.image == self.image and bytes(c.room).hex() == self.scope['room_id'] and
             list(c.force) == [self.scope['bindings'][s]['force_id'] for s in ('A','B')] and
             list(c.main_district) == [self.scope['bindings'][s]['main_district_id'] for s in ('A','B')] and
             bytes(c.rules_digest).hex() == self.scope['profile']['rules_sha256'], 'Retained native rules scope differs')
        need(self.control.status()['transport_open'] is True, 'Original B control connection is unavailable')
        check_port(self.guard_check)

    def _verify_held(self):
        # This adapts an existing strict throwing port; it does not implement it.
        self._check()
        return True

    def _hold(self, reason):
        if self.phase == 'HELD': return
        self.phase = 'HELD'; self.held_reason = str(reason)
        try: check_port(self.on_hold, self.held_reason)
        except BaseException as exc: self.hold_error = repr(exc)

    def _before(self, received, profile):
        self._check()
        context = received.context()
        c = Config.from_buffer_copy(self.lifecycle.current.world.config)
        expected_ruler = profile.source.ruler if c.viewer == profile.source.force else profile.target.ruler
        expected = (profile.before.year, profile.before.month, profile.before.day, profile.currentForce, expected_ruler)
        reads = world.Reads(self.reader.memory.read)
        first = world.context(self.reader, reads, self.read_birth, expected)
        second = world.context(self.reader, reads, self.read_birth, expected)
        need(first == second and (first['root'], first['world']) == (c.root, c.world) and c.viewer == profile.currentForce,
             'Current planning world/viewer changed before reservation')
        self._check()
        return dict(attachment=context['attachments']['B'], viewer_force=c.viewer, safe_boundary=True)

    def _sample(self, received, profile, completion):
        self._check()
        ctx = received.context(); m = ctx['manifest']
        result = world.sample(self.reader, scope=self.scope, epoch=m['epoch'], period=m['period'], profile=profile,
            side='B', receipt_key=completion['accepted']['receipt_key'], read_birth=self.read_birth)
        self._check()
        return result

    def apply_received(self, received, request, profile, *, reservation):
        """Only callable by this owner's currently executing remote transaction."""
        with self._lock:
            need(self.phase == 'APPLYING' and self._active is not None and
                 all(x is y for x,y in zip(self._active,(received,request,profile))),
                 'No matching retained remote transaction')
            self._check()
            ctx = received.context(); m = ctx['manifest']
            adapter_type = FormalBootstrapReceivedApply if type(self.bridge) is BootstrapRulesBridge else ReceivedApply
            adapter = adapter_type(self.bridge, self.control, scope=self.scope, epoch=m['epoch'],
                period=m['period'], attachments=ctx['attachments'], on_hold=self._hold)
            self.sessions.append(adapter)
            captured = []
            def sample(r,p,c):
                value = self._sample(r,p,c); captured.append(value); return value
            result = adapter.apply(received, request, profile, reservation=reservation,
                observe_loaded=self.observe_loaded, prepare_rules=self.prepare_rules, sample_loaded=sample)
            # Sample again after the actual diagnostic ACK, before remote formal
            # completion. The ACK itself is not a native/world receipt.
            latest = self._sample(received,profile,result['completion'])
            need(len(captured) == 1 and captured[0]['shared'] == latest['shared'] and
                 captured[0]['binding'] == latest['binding'], 'Projection changed across diagnostic ACK')
            self.samples.append(latest)
            return dict(completion=result['completion'], sample=latest)

    def apply(self, received, request, profile):
        with self._lock:
            need(self.phase == 'ACTIVE', 'Retained B owner already executing/held')
            self.phase = 'APPLYING'
            try:
                self._check()
                need(type(received) is ReceivedCheckpoint and type(request) is NextWorldRequest and type(profile) is Profile,
                     'Typed local receive/request/profile required')
                validate_profile(profile)
                ctx = received.context(); m = ctx['manifest']
                need(canonical(ctx['scope']) == self._scope and type(m['period']) is int and m['period'] == self.period and
                     (self.epoch is None or m['epoch'] == self.epoch) and
                     (self.attachments is None or ctx['attachments'] == self.attachments), 'Remote period/attachment lineage differs')
                need(len(self.bridge.completed) == self.period-1 and self.period <= 2 and
                     request.generation == self.lifecycle.current.world.generation+1 and request.checkpoint == ctx['checkpoint_id'],
                     'Native bank/generation lineage differs')
                expected_journal = BootstrapCheckpointJournal if type(self.bridge) is BootstrapRulesBridge and self.period == 1 else CheckpointJournal
                need(type(received.journal) is expected_journal, 'Wrong bootstrap/ordinary journal generation')
                # Observe before sending begin as well, so local invalid context
                # cannot consume A's one intent. Remote client rechecks it later.
                self._before(received,profile)
                self._active = (received,request,profile)
                result = self.remote.apply(received,profile,guest_before=lambda:self._before(received,profile),
                    apply_received=lambda permit:self.apply_received(received,request,profile,reservation=permit))
                self._check()
                progress = result['protocol_progress']; args = received.journal.coordinator_arguments()
                need(progress.get('period') == self.period+1 and type(progress.get('epoch')) is str,
                     'Authority returned another period')
                self.history.append(dict(period=self.period, checkpoint=request.checkpoint, generation=request.generation,
                    intent=args['intent'], native_receipt=self.samples[-1]['binding']['receipt_key'], result=deepcopy(result)))
                self.attachments = deepcopy(ctx['attachments']); self.attachments['B'] = args['new_attachment']
                self.period, self.epoch = progress['period'], progress['epoch']
                self.phase = 'ACTIVE'
                return result
            except BaseException as exc:
                self._hold(type(exc).__name__+': '+str(exc))
                raise
            finally:
                self._active = None
