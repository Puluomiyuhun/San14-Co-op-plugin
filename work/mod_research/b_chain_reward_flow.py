"""B chain reward protocol owners accepting the successor input-aware port.
Independent constructors avoid relaxing the frozen predecessor type checks.
"""
from copy import deepcopy
import threading
from reward_observed_context import ContextSampler,CONTRACT,need
from reward_rebind_context import CheckedPort
from reward_room_flow import Replica,envelope,report_proof
from b_warm_profile_contract import Profile,validate_profile
from checkpoint_fresh_save_binding import LocalWorldObservation
from authoritative_sync import digest,hexid
import b_warm_world as world
from reward_checkpoint_observer import SCHEMA,COVERAGE,key_check,packet
from a_save_runtime_control import require
import a_runtime_reward_port as reward_port

class GuestConsumer:
    """Trusted local loop, not a TLS callback. Lost replies terminate this object."""
    def __init__(self,control,replica,key):
        need(type(replica) is Replica and type(replica.port) is CheckedPort and replica.player=='B',
             'Actual B journal and checked local port required')
        need(type(key) is bytes and len(key)==32,'Separately provisioned report key required')
        sampler=replica.port.sampler
        need(sampler.viewer==replica.scope['bindings']['B']['force_id'] and
             {f:v['district'] for f,v in sampler.players.items()}==
             {v['force_id']:v['main_district_id'] for v in replica.scope['bindings'].values()},
             'Guest native binding differs from authenticated room')
        self.control,self.replica,self._key=control,replica,key;self.failed=None;self.lock=threading.RLock()

    def _request(self,value):
        reply=self.control.request(value);need(reply.get('ok') is True,'Reward authority rejected request');return reply

    def report(self):
        with self.lock:
            need(self.failed is None,'Reward consumer terminal; no replay')
            try:
                value=self.replica.report()
                return self._request(envelope(self.replica.scope,'reward_report',report=value,
                                               proof=report_proof(self._key,value)))
            except BaseException as exc:self._fail(exc);raise

    def _fail(self,exc):
        if self.failed is None:self.failed=type(exc).__name__+': '+str(exc)
        self.replica.port.retire(self.failed)
        # Control disconnect holds the authority queue. No native cancel/release
        # or restart is inferred; the local Journal keeps INTENT/APPLIED evidence.
        try:self.control.close()
        except BaseException:pass

    def consume_one(self):
        with self.lock:
            need(self.failed is None,'Reward consumer terminal; no replay')
            try:
                value=self._request(envelope(self.replica.scope,'reward_next'))
                if value['intent'] is None:return dict(status='QUEUE_EMPTY',native_invoked=False)
                receipt=self.replica.apply(value['intent']);ack=self.report()
                return dict(receipt=deepcopy(receipt),ack=ack,ui_refresh_verified=False)
            except BaseException as exc:self._fail(exc);raise

class CutObserver:
    """Brackets the old complete two-table sampler with the reward projection.

    A separate read-only ContextSampler is pinned at construction to the EXACT
    same reader/context as the execution port. It remains available for the
    pre-turn recheck after the execution port has been permanently retired.
    It has no execute method and does not revive the retired journal or port.
    """
    def __init__(self, replica, profile):
        need(type(replica) is Replica and type(replica.port) is CheckedPort,
             'Actual replica and checked port required')
        need(type(profile) is Profile, 'Typed retained bootstrap profile required')
        validate_profile(profile)
        self.replica = replica; self.profile = Profile.from_buffer_copy(bytes(profile))
        original = replica.port.sampler
        self.sampler = ContextSampler(original.reader, pid=original.pid, birth=original.birth,
            epoch=original.epoch, attachment_id=original.attachment_id,
            current_binding=original.current_binding, node=original.node, viewer=original.viewer,
            players=original.players, read_birth=original.read_birth)
        need(self.sampler.local_identity == original.local_identity,
             'Execution and observation contexts differ')
        self.failed = None; self.sequence = 0; self.challenge_id = None

    def capture(self, challenge, *, retired_report=None):
        with self.sampler.lock:
            try:
                need(self.failed is None, 'Cut observer retired')
                need(type(challenge) is dict and challenge.get('schema') == 'san14.reward-cut-challenge.v1'
                     and hexid(challenge.get('id'), 32), 'Explicit cut challenge required')
                cid = digest(challenge)
                need(self.challenge_id in (None, cid), 'Cut observer cannot rebind challenge')
                self.challenge_id = cid
                b = challenge['binding']; side = self.replica.player; s = self.sampler
                need(challenge['reward_scope'] == self.replica.scope and
                     b['attachments'][side] == self.replica.attachment == s.attachment_id and
                     b['checkpoint_contract'] == world.CONTRACT and b['node'] == world.node(self.profile),
                     'Cut scope, attachment, date or state contract differs')
                expected = challenge['reports'][side]
                if retired_report is None:
                    need(self.replica.report() == expected, 'Actual reward journal tip changed')
                else:
                    need(retired_report == expected, 'Retired tip differs')
                _, before = s.capture()
                need(before['schema'] == CONTRACT and digest(before) == expected['state_sha256'],
                     'Reward loyalty/cost projection differs from actual paired tip')
                if retired_report is not None:
                    need(self.replica.journal.report(lambda: digest(before)) == expected,
                         'Retired execution journal changed before observation')
                sample = world.sample(s.reader, scope=b['scope'], epoch=b['checkpoint_epoch'],
                    period=b['checkpoint_period'], profile=self.profile, side=side,
                    receipt_key=cid, read_birth=s.read_birth)
                _, after = s.capture()
                need(before == after and s.local_identity == self.replica.port.sampler.local_identity,
                     'Same-reader projections changed during sampling')
                if retired_report is None:
                    need(self.replica.report() == expected, 'Reward tip changed during world capture')
                else:
                    need(self.replica.journal.report(lambda: digest(after)) == expected,
                         'Retired execution journal changed during observation')
                self.sequence += 1
                return dict(schema=SCHEMA, challenge_sha256=cid, side=side,
                    attachment=s.attachment_id, sequence=self.sequence,
                    reward_report=deepcopy(expected), reward_projection=after, world_sample=sample,
                    same_reader=True, **COVERAGE)
            except BaseException as exc:
                self.failed = str(exc); self.sampler.retire(str(exc)); raise

    def attest(self, challenge, key):
        need(self.replica.player == 'B', 'Only B signs a guest observation')
        return packet(key, self.capture(challenge))

    def local_observation(self, challenge, report):
        value = self.capture(challenge, retired_report=report)
        s = self.sampler; node = challenge['binding']['node']
        return LocalWorldObservation(s.attachment_id, node['year'], node['month'], node['day'],
            s.viewer, s.players[s.viewer]['ruler'], world.CONTRACT,
            value['world_sample']['partial_sha256'], True), value


class GuestCutConsumer:
    """Thin retained B pump; native B executor must already be bound locally.

    Explicit finish_input is separate from polling. Loss of any response is
    terminal, including a possibly accepted signed cut; no replay is attempted.
    """
    def __init__(self,consumer,profile,*,cut_key,checkpoint_epoch):
        require(type(consumer) is GuestConsumer,'Existing retained B reward consumer required')
        key_check(cut_key);require(reward_port.journal.hex_id(checkpoint_epoch,32),'Current checkpoint epoch required')
        self.consumer=consumer;self.observer=CutObserver(consumer.replica,profile);self.key=cut_key;self.epoch=checkpoint_epoch
        self.prepared=False;self.attest_attempted=False;self.ready_attempted=False;self.failed=None
    def _request(self,value):
        require(self.failed is None,'Guest cut owner is terminal')
        try:
            r=self.consumer.control.request(value);require(r.get('ok') is True,'Reward/cut endpoint rejected request');return r
        except BaseException as exc:self.failed=repr(exc);self.consumer._fail(exc);raise
    def finish_input(self):
        require(not self.prepared,'Input-finished notification is once-only');self.prepared=True
        return self._request(dict(action='reward_cut_prepare',epoch=self.epoch))
    def poll(self):
        try:
            status=self._request(dict(action='reward_cut_status'))
            if status['state']=='ACTIVE':return self.consumer.consume_one()
            if status['state']=='COLLECTING' and not self.attest_attempted:
                require(self.prepared,'Cannot attest before explicitly ending input')
                self.attest_attempted=True
                return self._request(self.observer.attest(status['challenge'],self.key))
            require(status['state'] in ('COLLECTING','RETIRED_SHARED_CUT'),'Reward cut held or retired incorrectly')
            return status
        except BaseException as exc:
            if self.failed is None:self.failed=repr(exc);self.consumer._fail(exc)
            raise
    def ready_after_cut(self):
        require(not self.ready_attempted,'B Ready after cut is once-only');self.ready_attempted=True
        status=self._request(dict(action='reward_cut_status'))
        require(self.prepared and status['state']=='RETIRED_SHARED_CUT' and status['receipt']['checkpoint_cut_installed'],
                'Actual paired checkpoint cut required before B Ready')
        return self._request(dict(action='period_ready',epoch=self.epoch,ready=True))
