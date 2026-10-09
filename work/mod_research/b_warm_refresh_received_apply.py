"""Refresh bridge adapters; retain original journal, intent and ACK implementation.

Only exact new bridge types are accepted. Complete native refresh/lease evidence
is required in addition to the original load, rules and projection acceptance.
"""
import hashlib
from authoritative_sync import canonical
import b_warm_staging as files
from b_warm_received_apply import ReceivedApply as FrozenReceivedApply, need
from b_warm_refresh_rules_bridge import WarmRulesBridge
from b_warm_refresh_bootstrap import BootstrapRulesBridge
from b_warm_profile_contract import Profile
from b_warm_room import ReceivedCheckpoint
from checkpoint_bootstrap_journal import BootstrapCheckpointJournal
from human_rules_world_lifecycle import NextWorldRequest


class ReceivedApply(FrozenReceivedApply):
    def __init__(self,bridge,*args,**kwargs):
        need(type(bridge) in (WarmRulesBridge,BootstrapRulesBridge),'Actual refresh bridge required')
        super().__init__(bridge,*args,**kwargs)

    def _completion(self,outcome,request,profile):
        c=super()._completion(outcome,request,profile)
        r=c['refresh']
        expected=dict(state=4,error=0,captured=1,executeCalls=1,writeAttempts=1,writeReturned=1,
            intentCreated=1,intentDurable=1,matched=1,leaseHeld=0,leaseReleased=1,releaseCalls=1,
            previousReads=2,newReads=2,osError=0,exceptionCode=0)
        need(all(type(r.get(k)) is int and r[k]==v for k,v in expected.items()),
             'Native refresh or target lease not completed')
        need(c.get('target_lease_released') is True and r['attempt']==c['attempt'] and
             r['new_size']==profile.file.size and r['new_sha256']==bytes(profile.file.sha256).hex() and
             r['stage']=='released_after_native_retirement','Refresh belongs to another native load')
        return c


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


class FormalBootstrapReceivedApply(BootstrapReceivedApply):
    """Retains original intent/completion/ACK owner; changes only first schema."""
    def _validate(self, received, request, profile, reservation):
        files.need(type(self.bridge) is BootstrapRulesBridge, 'Explicit bootstrap bridge required')
        if self.bridge.completed:
            return super()._validate(received, request, profile, reservation)
        files.need(self.period == 1 and reservation is not None,
                   'First formal bootstrap requires initial period and durable reservation')
        files.need(type(received) is ReceivedCheckpoint and type(request) is NextWorldRequest and
                   type(profile) is Profile and not received.ack_attempted, 'Typed unused local inputs required')
        files.need(type(received.journal) is BootstrapCheckpointJournal,
                   'Explicit bootstrap journal required; never reinterpret ordinary INTENT')
        self.bridge.validate_current_profile(profile)
        context = received.context(); m = context['manifest']
        files.need(canonical(context['scope']) == canonical(self.scope) and
                   canonical(context['attachments']) == canonical(self.attachments) and
                   (m['epoch'], m['period']) == (self.epoch, self.period), 'Foreign room/period/attachment')
        files.need(request.checkpoint == context['checkpoint_id'], 'Native request targets another checkpoint')
        expected = dict(schema='san14.checkpoint-bootstrap-journal.v1', local_player='B', scope=self.scope,
                        manifest=m, checkpoint_id=context['checkpoint_id'], attachments=self.attachments,
                        pre_load_viewer_force=self.scope['bindings']['A']['force_id'])
        files.need(canonical(received.journal.identity) == canonical(expected), 'Journal context changed')
        module = self.bridge.lifecycle.current.module
        files.need((module.pid, module.birth) == self.native_identity and
                   self.bridge.warm.reader.pid == module.pid, 'Retained process binding changed')
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
