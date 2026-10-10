"""One retained reader, two named finite projections at a paired reward cut.

No process opening or native permission. The reward projection is never placed
in a warm-world hash field. Signatures identify a trusted adapter, not a fence.
"""
from copy import deepcopy
import base64
import hashlib
import hmac
import json
import zlib

from authoritative_sync import canonical, digest, hexid
from b_warm_profile_contract import Profile, validate_profile
from checkpoint_fresh_save_binding import LocalWorldObservation
from reward_observed_context import ContextSampler, CheckedPort, CONTRACT, need
from reward_room_flow import Replica
import b_warm_world as world

ACTION = 'reward_cut_observation'
DOMAIN = b'san14.reward-checkpoint-two-projections.v1\0'
SCHEMA = 'san14.reward-checkpoint-two-projections.v1'
MAX_RAW = 512 * 1024
COVERAGE = dict(human_no_new_commands=True, input_exclusion_proven=False,
                atomic_snapshot=False, full_world_verified=False,
                reward_fields_verified_after_checkpoint_load=False)


def key_check(key):
    need(type(key) is bytes and len(key) == 32 and any(key), 'Separate cut adapter key required')


def packet(key, body):
    key_check(key); raw = canonical(body)
    need(len(raw) <= MAX_RAW, 'Cut sample too large')
    packed = zlib.compress(raw)
    result = dict(action=ACTION, payload=base64.b64encode(packed).decode('ascii'),
                  mac=hmac.new(key, DOMAIN + packed, hashlib.sha256).hexdigest())
    need(len(canonical(result)) < 65000, 'Cut sample exceeds TLS frame')
    return result


def unpack(key, value):
    key_check(key)
    need(type(value) is dict and set(value) == {'action', 'payload', 'mac'} and value['action'] == ACTION,
         'Exact cut sample envelope required')
    need(type(value['payload']) is str and len(value['payload']) < 64000 and type(value['mac']) is str,
         'Bounded cut sample envelope required')
    packed = base64.b64decode(value['payload'], validate=True)
    need(len(packed) < 48000 and hmac.compare_digest(value['mac'],
         hmac.new(key, DOMAIN + packed, hashlib.sha256).hexdigest()), 'Cut sample authentication failed')
    decoder = zlib.decompressobj(); raw = decoder.decompress(packed, MAX_RAW + 1)
    need(len(raw) <= MAX_RAW and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
         'Unbounded cut sample')
    body = json.loads(raw)
    need(type(body) is dict and canonical(body) == raw, 'Canonical cut sample required')
    return body


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


def validate_body(body, challenge, side):
    need(type(body) is dict and set(body) == {'schema', 'challenge_sha256', 'side', 'attachment',
         'sequence', 'reward_report', 'reward_projection', 'world_sample', 'same_reader'} | set(COVERAGE),
         'Exact combined cut observation required')
    need(body['schema'] == SCHEMA and body['challenge_sha256'] == digest(challenge) and
         body['side'] == side and body['attachment'] == challenge['binding']['attachments'][side] and
         body['same_reader'] is True and type(body['sequence']) is int and body['sequence'] > 0 and
         all(body[k] is v for k, v in COVERAGE.items()), 'Cut observation binding or coverage differs')
    need(body['reward_report'] == challenge['reports'][side] and
         body['reward_projection'].get('schema') == CONTRACT and
         digest(body['reward_projection']) == body['reward_report']['state_sha256'],
         'Reward projection does not match the paired report')
    value = body['world_sample']; world.validate_sample(value); b = challenge['binding']
    need(value['binding']['scope_sha256'] == digest(b['scope']) and
         value['binding']['epoch'] == b['checkpoint_epoch'] and
         value['binding']['period'] == b['checkpoint_period'] and
         value['binding']['side'] == side and value['binding']['receipt_key'] == digest(challenge) and
         value['shared']['date'] == b['node'], 'World sample belongs to another cut')
    return body
