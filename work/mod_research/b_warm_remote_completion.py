"""Authenticated remote adapter completion for the declared partial contract.

A alone owns PeriodCoordinator. B owns its SQLite journal and retained native
owner. An independently provisioned adapter key authenticates B's local owner;
it is not the room join token and is never sent on the wire. This authenticates
origin, not engine execution: callers must retain their real native boundary.
No complete-world, Ready, or gameplay permission is provided.
"""
import base64
from copy import deepcopy
import hashlib
import hmac
import json
import os
import threading
import zlib

from authoritative_sync import CheckpointReceiver, canonical, digest, hexid
from checkpoint_journal import CheckpointJournal
from checkpoint_bootstrap_journal import BootstrapCheckpointJournal
from b_warm_room import WarmRoom, ReceivedCheckpoint
from b_warm_profile_contract import Profile, validate_profile
from b_warm_projection import TrustedProjection, need
import b_warm_world as world

ACTION = 'warm_adapter_completion_v1'
DOMAIN = b'san14.remote-partial-completion.v1\0'
MAX_RAW = 256 * 1024
WITNESS_SCHEMA = 'san14.authenticated-partial-witness.v1'


def compact_witness(value):
    """Local full validation first; this summary is an authenticated assertion.

    Hashes attest neither native execution nor a scheduling fence. A compares
    them with its own fresh full sample under the same declared contract.
    """
    payload = world.validate_sample(value)
    s = value['shared']
    return dict(schema=WITNESS_SCHEMA, binding=deepcopy(value['binding']),
        contract=s['contract'], game_sha256=s['game_sha256'], date=deepcopy(s['date']),
        partial_sha256=value['partial_sha256'],
        table_sha256={name:hashlib.sha256(raw).hexdigest() for name, raw in payload.items()},
        physical_slots=deepcopy(value['physical_slots']), repeated_reads_equal=True,
        complete_selected_tables=True, atomic_world_snapshot=False, full_world_verified=False,
        loaded_authorized=False, ready_authorized=False)


def witness_check(value, profile, context, receipt, native):
    fields = {'schema','binding','contract','game_sha256','date','partial_sha256','table_sha256',
              'physical_slots','repeated_reads_equal','complete_selected_tables','atomic_world_snapshot',
              'full_world_verified','loaded_authorized','ready_authorized'}
    need(type(value) is dict and set(value) == fields and value['schema'] == WITNESS_SCHEMA,
         'Exact authenticated witness required')
    world.validate_node(value['date'])
    need(value['contract'] == world.CONTRACT and value['game_sha256'] == world.objects.GAME_SHA256 and
         value['date'] == context['manifest']['node'] and
         value['partial_sha256'] == context['manifest']['world_sha256'], 'Witness contract/date/hash differs')
    need(type(value['table_sha256']) is dict and set(value['table_sha256']) == {'objects','forces'} and
         all(hexid(v) for v in value['table_sha256'].values()), 'Witness table digests differ')
    need(value['physical_slots'] == dict(objects=world.objects.SLOT_COUNT,forces=world.forces.SLOT_COUNT) and
         value['repeated_reads_equal'] is True and value['complete_selected_tables'] is True and
         all(value[k] is False for k in ('atomic_world_snapshot','full_world_verified','loaded_authorized','ready_authorized')),
         'Witness coverage/authority differs')
    expected = dict(scope_sha256=digest(context['scope']), epoch=context['manifest']['epoch'],
        period=context['manifest']['period'], profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(),
        side='B', receipt_key=receipt, viewer_force=profile.target.force, viewer_ruler=profile.target.ruler,
        pid=native['pid'], birth=native['birth'])
    need(type(value['binding']) is dict and canonical(value['binding']) == canonical(expected),
         'Witness native identity differs')


def key_check(key):
    need(type(key) is bytes and len(key) == 32 and any(key), 'Independent local adapter key required')


def packet(key, value):
    key_check(key)
    raw = canonical(value)
    need(len(raw) <= MAX_RAW, 'Adapter payload too large')
    packed = zlib.compress(raw)
    value = dict(action=ACTION, payload=base64.b64encode(packed).decode('ascii'),
                 mac=hmac.new(key, DOMAIN+packed, hashlib.sha256).hexdigest())
    need(len(canonical(value)) < 65000, 'Compressed adapter packet exceeds existing TLS limit')
    return value


def unpack(key, value):
    key_check(key)
    need(type(value) is dict and set(value) == {'action', 'payload', 'mac'} and value['action'] == ACTION,
         'Wrong adapter packet')
    packed = base64.b64decode(value['payload'], validate=True)
    need(len(packed) < 48000 and type(value['mac']) is str and
         hmac.compare_digest(value['mac'], hmac.new(key, DOMAIN+packed, hashlib.sha256).hexdigest()),
         'Adapter authentication failed')
    decoder = zlib.decompressobj()
    raw = decoder.decompress(packed, MAX_RAW+1)
    need(len(raw) <= MAX_RAW and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
         'Unbounded/noncanonical compressed payload')
    answer = json.loads(raw)
    need(type(answer) is dict and canonical(answer) == raw, 'Noncanonical adapter body')
    return answer


def profile_from(text):
    raw = base64.b64decode(text, validate=True)
    need(len(raw) == __import__('ctypes').sizeof(Profile), 'Wrong profile size')
    p = Profile.from_buffer_copy(raw); validate_profile(p)
    return p


def sample_check(value, profile, context, receipt, native):
    world.validate_sample(value)
    b = value['binding']; p = profile.target
    expected = dict(scope_sha256=digest(context['scope']), epoch=context['manifest']['epoch'],
        period=context['manifest']['period'], profile_sha256=hashlib.sha256(bytes(profile)).hexdigest(),
        side='B', receipt_key=receipt, viewer_force=p.force, viewer_ruler=p.ruler,
        pid=native['pid'], birth=native['birth'])
    need(all(b.get(k) == v for k, v in expected.items()), 'Remote observation identity differs')
    need(value['shared']['date'] == context['manifest']['node'] and
         value['partial_sha256'] == context['manifest']['world_sha256'], 'Remote projection differs')


def load_receipt(context, intent, completion):
    m = context['manifest']; a = completion['accepted']
    attachment = digest(dict(checkpoint=context['checkpoint_id'], intent=intent,
        pid=completion['pid'], birth=completion['birth'], attempt=completion['attempt'], receipt_key=a['receipt_key']))[:32]
    return dict(player='B', epoch=m['epoch'], checkpoint_id=context['checkpoint_id'], intent=intent,
        world_sha256=m['world_sha256'], viewer_force=context['scope']['bindings']['B']['force_id'],
        attachment=attachment, host_observation=dict(attachment=context['attachments']['A'],
            world_sha256=m['world_sha256'], node=m['node']))


class RemoteCompletionRoom(WarmRoom):
    def __init__(self, manifest):
        super().__init__(manifest)
        self._remote = None

    def enroll_adapter(self, key, *, host_sampler, verify_held, host_receipt_key, source_kind):
        """A's trusted launcher only, after both control seats are bound.

        Provision the same key privately to the B retained owner. There is no
        network enrollment/key exchange or reconnect/restart recovery here.
        """
        with self.lock:
            key_check(key)
            need(self._remote is None and self._coordinator is not None, 'Adapter already enrolled/no coordinator')
            need(callable(host_receipt_key), 'Current owned A receipt key callback required')
            c = self._coordinator
            helper = TrustedProjection(c, host_sampler=host_sampler, guest_sampler=lambda *_: None,
                verify_held=verify_held, guest_before=lambda: None, native_load=lambda _: None, source_kind=source_kind)
            self._remote = dict(key=key, helper=helper, host_key=host_receipt_key,
                connection=self.players['B']['connection'], rows={}, held=None)

    def _remote_current(self, player, connection):
        need(player == 'B' and self.players.get('B', {}).get('connection') == connection,
             'Current authenticated B connection required')
        need(self._coordinator is not None and self._held is None, 'Room held/unbound')
        self._bound(self._coordinator)
        need(self._coordinator.connected == {'A', 'B'}, 'Both control connections required')

    def handle(self, player, connection_id, request):
        if type(request) is not dict or request.get('action') not in (ACTION, 'warm_rules_binding'):
            return super().handle(player, connection_id, request)
        try:
            with self.lock:
                self._remote_current(player, connection_id)
                if request['action'] == 'warm_rules_binding':
                    need(set(request) == {'action'}, 'Binding query has no parameters')
                    need(self._coordinator.phase != 'HELD', 'Coordinator held')
                    return dict(ok=True, scope=deepcopy(self._scope), native_permission=False, native_gameplay_enabled=False)
                r = self._remote
                need(r is not None and r['connection'] == connection_id and r['held'] is None,
                     'No current enrolled adapter')
                body = unpack(r['key'], request)
                with self._coordinator.lock:
                    if body.get('kind') == 'begin': return self._begin(body)
                    need(body.get('kind') == 'complete', 'Unknown adapter operation')
                    return self._complete(body)
        except (ValueError, TypeError, KeyError, RuntimeError) as exc:
            return dict(ok=False, error=str(exc), native_gameplay_enabled=False)

    def _begin(self, b):
        need(set(b) == {'kind', 'context', 'profile', 'guest_before', 'bootstrap'}, 'Wrong begin fields')
        c = self._coordinator; r = self._remote; context = b['context']; m = context['manifest']
        need(type(b['bootstrap']) is bool, 'Explicit journal kind required')
        need(context == dict(scope=c.scope, manifest=c.manifest, checkpoint_id=c.checkpoint_id, attachments=c.attachments)
             and c.phase == 'RECONCILING' and c.load_intent is None and self.artifacts is not None and
             not self.artifacts.closed, 'Offered context no longer current')
        need(c.checkpoint_id not in r['rows'] and len(r['rows']) < 16, 'Once-only adapter window exhausted')
        p = profile_from(b['profile'])
        need((p.file.size, bytes(p.file.sha256).hex()) ==
             (m['parts']['world.s14']['size'], m['parts']['world.s14']['sha256']), 'Profile file differs')
        need(tuple(c.node[k] for k in ('year', 'month', 'day')) == (p.before.year, p.before.month, p.before.day) and
             tuple(m['node'][k] for k in ('year', 'month', 'day')) == (p.loaded.year, p.loaded.month, p.loaded.day),
             'Profile dates differ')
        for side, ident in (('A', p.source), ('B', p.target)):
            need(c.scope['bindings'][side] == dict(force_id=ident.force, main_district_id=ident.district), 'Profile faction differs')
        if b['bootstrap']:
            need(c.period == 1 and not c.applied_receipts and p.currentForce == p.source.force,
                 'Bootstrap is initial truthful source view only')
        else: need(p.currentForce == p.target.force, 'Ordinary load requires target view')
        viewer = p.source.force if b['bootstrap'] else p.target.force
        need(b['guest_before'] == dict(attachment=c.attachments['B'], viewer_force=viewer, safe_boundary=True),
             'Authenticated pre-load boundary differs')
        sc = dict(scope=c.scope, epoch=c.epoch, period=c.period, node=m['node'])
        host_key = r['host_key']()
        need(hexid(host_key) and int(host_key, 16), 'Current A receipt identity required')
        a = r['helper']._sample('A', p, host_key, sc)
        need(a['partial_sha256'] == m['world_sha256'], 'A projection changed before remote load')
        # Reconstruct A's immutable transmitted bytes; B's separately signed
        # begin is the retained adapter's assertion that its Journal is STAGED.
        receiver = CheckpointReceiver(m, c.checkpoint_id, c.scope, c.epoch, c.period, m['cut'])
        for chunk in self.artifacts.chunks.values(): receiver.accept(chunk)
        c.received('B', c.epoch, receiver)
        intent = c.begin_guest_load('B', c.epoch)
        row = dict(context=deepcopy(context), profile=b['profile'], intent=intent, a=a, host_key=host_key,
                   begin=deepcopy(b), reply=None, complete=None)
        r['rows'][c.checkpoint_id] = row
        return dict(ok=True, checkpoint_id=c.checkpoint_id, intent=intent, host_observation=dict(attachment=c.attachments['A'],
                    world_sha256=m['world_sha256'], node=m['node']), native_gameplay_enabled=False)

    def _complete(self, b):
        need(set(b) == {'kind', 'checkpoint_id', 'intent', 'completion', 'sample', 'receipt'}, 'Wrong completion fields')
        r = self._remote; c = self._coordinator
        need(b['checkpoint_id'] in r['rows'], 'No authenticated once-only reservation')
        row = r['rows'][b['checkpoint_id']]
        if row['complete'] is not None:
            need(row['complete'] == b, 'Conflicting completion replay')
            return {**deepcopy(row['reply']), 'duplicate': True}
        try:
            context = row['context']; m = context['manifest']; p = profile_from(row['profile'])
            need(c.phase == 'RECONCILING' and c.manifest == m and c.attachments == context['attachments'] and
                 c.load_intent == row['intent'] == b['intent'], 'Completion binding changed')
            answer = r['helper']._completion(b['completion'], p, m)
            witness_check(b['sample'], p, context, answer['accepted']['receipt_key'], answer)
            need(b['receipt'] == load_receipt(context, b['intent'], answer), 'Persisted native receipt differs')
            sc = dict(scope=c.scope, epoch=c.epoch, period=c.period, node=m['node'])
            need(r['host_key']() == row['host_key'], 'A Save receipt lifetime changed')
            a = r['helper']._sample('A', p, row['host_key'], sc)
            a_witness = compact_witness(a)
            need(a['shared'] == row['a']['shared'] and
                 {k:v for k,v in a_witness.items() if k != 'binding'} ==
                 {k:v for k,v in b['sample'].items() if k != 'binding'},
                 'A/B declared projection changed')
            r['helper']._held()
            receipt = deepcopy(b['receipt']); receipt['new_attachment'] = receipt.pop('attachment')
            progress = c.loaded(**receipt)
            reply = dict(ok=True, result='AUTHENTICATED_REMOTE_PARTIAL_LOADED', protocol_progress=progress,
                checkpoint_id=b['checkpoint_id'], intent=b['intent'],
                duplicate=False, contract=world.CONTRACT, ready_authorized=False, full_world_verified=False,
                native_gameplay_enabled=False, source='ENROLLED_REMOTE_ADAPTER')
            row.update(complete=deepcopy(b), reply=deepcopy(reply))
            return reply
        except BaseException as exc:
            r['held'] = type(exc).__name__+': '+str(exc)
            self._held = 'REMOTE_COMPLETION_UNCERTAIN'; c.ready.clear(); c.phase = 'HELD'
            raise


def durable(path, value):
    with path.open('xb') as out:
        out.write(canonical(value)); out.flush(); os.fsync(out.fileno())


class RemoteGuestCompletion:
    """B-side retained local owner adapter. Never holds an A Coordinator.

    apply_received(permit) returns {'completion': actual native accepted output,
    'sample': fresh world.sample output}. The caller must maintain its trusted
    local input/execution boundary throughout. No packet installs native code.
    """
    def __init__(self, control, key, *, verify_held):
        key_check(key)
        need(control.player_id == 'B' and callable(verify_held), 'B retained owner required')
        self.control, self.key, self.verify_held = control, key, verify_held
        self.held = None
        self._lock = threading.RLock()

    def apply(self, received, profile, *, guest_before, apply_received):
        with self._lock:
            return self._apply(received, profile, guest_before=guest_before, apply_received=apply_received)

    def _apply(self, received, profile, *, guest_before, apply_received):
        need(self.held is None and self.verify_held() is True, 'Guest adapter held/unsafe')
        need(type(received) is ReceivedCheckpoint and type(profile) is Profile, 'Actual local staged owner required')
        j = received.journal
        need(type(j) in (CheckpointJournal, BootstrapCheckpointJournal), 'Explicit journal type required')
        bootstrap = type(j) is BootstrapCheckpointJournal
        context = received.context(); m = context['manifest']; validate_profile(profile)
        need(j.identity['scope'] == context['scope'] and j.identity['manifest'] == m and
             j.identity['attachments'] == context['attachments'] and j.identity['checkpoint_id'] == context['checkpoint_id'] and
             j.status()['status'] == 'STAGED', 'Journal context/stage differs')
        received.verified_file()
        try:
            before = guest_before()
            b = dict(kind='begin', context=context, profile=base64.b64encode(bytes(profile)).decode('ascii'),
                     guest_before=before, bootstrap=bootstrap)
            # Claim before even sending begin: a lost begin reply cannot produce
            # a new intent or an automatic native retry on reopening this folder.
            durable(received.directory/'remote-adapter-begin.json', b)
            reply = self.control.request(packet(self.key, b))
            need(reply.get('ok') is True, 'Host rejected remote reservation: '+str(reply.get('error')))
            need(reply.get('checkpoint_id') == context['checkpoint_id'] and hexid(reply.get('intent'), 32) and
                 reply.get('native_gameplay_enabled') is False, 'Reservation reply identity differs')
            permit = j.reserve_load(reply['intent'], reply['host_observation'], before)
            need(self.verify_held() is True, 'Guest boundary released before native load')
            outcome = apply_received(permit)
            answer = TrustedProjection._completion(None, outcome['completion'], profile, m)
            sample_check(outcome['sample'], profile, context, answer['accepted']['receipt_key'], answer)
            received.verified_file()
            need(self.verify_held() is True, 'Guest boundary released after native load')
            receipt = load_receipt(context, reply['intent'], answer)
            j.complete(receipt)
            witness = compact_witness(outcome['sample'])
            b = dict(kind='complete', checkpoint_id=context['checkpoint_id'], intent=reply['intent'],
                     completion=answer, sample=witness, receipt=receipt)
            durable(received.directory/'remote-adapter-completion.json', b)
            need(self.verify_held() is True, 'Guest boundary released before completion delivery')
            result = self.control.request(packet(self.key, b))
            need(result.get('ok') is True, 'Host rejected remote completion: '+str(result.get('error')))
            need(result.get('checkpoint_id') == context['checkpoint_id'] and result.get('intent') == reply['intent'] and
                 result.get('result') == 'AUTHENTICATED_REMOTE_PARTIAL_LOADED' and result.get('contract') == world.CONTRACT and
                 all(result.get(k) is False for k in ('native_gameplay_enabled','ready_authorized','full_world_verified')),
                 'Completion reply identity/authority differs')
            durable(received.directory/'remote-adapter-reply.json', result)
            return result
        except BaseException as exc:
            self.held = type(exc).__name__+': '+str(exc)
            raise
