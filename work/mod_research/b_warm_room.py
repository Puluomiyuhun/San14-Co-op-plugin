"""Existing TLS checkpoint transfer plus advisory warm-load completion.

No process access, native load, world hash invention, loaded(), or Ready grant.
The local coordinator must validate native completion before reporting it. A
remote completion packet is still a guest claim, never native evidence at A.
"""
from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path

from checkpoint_room_lifecycle import CheckpointRoom
from checkpoint_room_artifacts import RoomError, SyncError, require
from authoritative_sync import CheckpointReceiver, canonical, digest, hexid, sha
from checkpoint_journal import CheckpointJournal
from checkpoint_transfer import receive_checkpoint

ACTION = 'warm_load_diagnostic_ack'
FIELDS = {'action', 'checkpoint_id', 'scope_sha256', 'epoch', 'period', 'cut',
          'file_sha256', 'file_size', 'profile_sha256', 'receipt_key', 'attempt',
          'pid', 'birth', 'loaded_date', 'viewer_force', 'viewer_ruler'}


def number(value, low=1, high=2**53):
    require(type(value) is int and low <= value < high, 'Invalid exact integer')


def validate_ack(packet, manifest, scope, checkpoint_id):
    require(type(packet) is dict and set(packet) == FIELDS, 'Invalid warm diagnostic fields')
    require(packet['action'] == ACTION and packet['checkpoint_id'] == checkpoint_id,
            'Foreign checkpoint completion')
    require(packet['scope_sha256'] == digest(scope) == manifest['scope_sha256'] and
            packet['epoch'] == manifest['epoch'] and packet['period'] == manifest['period'] and
            canonical(packet['cut']) == canonical(manifest['cut']), 'Foreign completion scope')
    number(packet['period'])
    number(packet['file_size'], high=16*1024*1024+1)
    require((packet['file_size'], packet['file_sha256']) ==
            (manifest['parts']['world.s14']['size'], manifest['parts']['world.s14']['sha256']),
            'Completion references different save bytes')
    for key in ('profile_sha256', 'receipt_key'):
        require(hexid(packet[key]) and packet[key] != '0'*64, 'Invalid '+key)
    # uint64 native identities use canonical decimal strings, avoiding JSON's
    # existing safe-integer protocol limit. They are claims, not attach tokens.
    for key in ('attempt', 'birth'):
        value = packet[key]
        require(type(value) is str and value.isascii() and value.isdecimal() and
                value == str(int(value)) and 0 < int(value) < 2**64, 'Invalid '+key)
    number(packet['pid'], high=2**32)
    number(packet['viewer_force'], high=255)
    number(packet['viewer_ruler'], high=6000)
    require(packet['viewer_force'] == scope['bindings']['B']['force_id'], 'Wrong guest force')
    require(canonical(packet['loaded_date']) == canonical(manifest['node']), 'Wrong loaded date')


class WarmRoom(CheckpointRoom):
    """Retains existing authenticated transport, publication and Ready policy."""
    def __init__(self, manifest):
        super().__init__(manifest)
        self._warm_ack = None

    def install_offered_checkpoint(self, coordinator, package):
        with self.lock:
            previous = self.artifacts.checkpoint_id if self.artifacts else None
            service = super().install_offered_checkpoint(coordinator, package)
            if previous != service.checkpoint_id:
                self._warm_ack = None
            return service

    def view(self, player):
        with self.lock:
            state = super().view(player)
            state['warm_completion'] = deepcopy(self._warm_ack)
            return state

    def handle(self, player, connection_id, request):
        if type(request) is not dict or request.get('action') != ACTION:
            return super().handle(player, connection_id, request)
        try:
            with self.lock:
                require(player == 'B' and self.players.get('B', {}).get('connection') == connection_id,
                        'Only current authenticated B may report completion')
                require(self._coordinator is not None and self.artifacts is not None, 'No offered checkpoint')
                with self._coordinator.lock, self.artifacts.lock:
                    self._bound(self._coordinator)
                    c, m = self._coordinator, self.artifacts.manifest
                    # A native load may already have a local reservation. The
                    # download service's _current() intentionally forbids that;
                    # a completion diagnostic must not demand a new download.
                    require(not self.artifacts.closed and c.phase == 'RECONCILING' and
                            c.connected == {'A', 'B'} and c.scope == self._scope and
                            c.manifest == m and c.checkpoint_id == self.artifacts.checkpoint_id and
                            c.epoch == m['epoch'] and c.period == m['period'], 'Checkpoint no longer current')
                    validate_ack(request, self.artifacts.manifest, self._scope, self.artifacts.checkpoint_id)
                    row = dict(packet=deepcopy(request), source='GUEST_REPORTED_WARM_COMPLETE',
                               full_world_verified=False, ready_authorized=False,
                               next_period_authorized=False, native_gameplay_enabled=False)
                    duplicate = self._warm_ack is not None
                    require(not duplicate or self._warm_ack == row, 'Conflicting completion replay')
                    self._warm_ack = row
                    return dict(ok=True, duplicate=duplicate, warm_completion=deepcopy(row))
        except (RoomError, SyncError, ValueError, TypeError, KeyError) as exc:
            return dict(ok=False, error=str(exc), applied_to_game=False)


@dataclass
class ReceivedCheckpoint:
    """Local byte evidence only. No engine exclusion or load permission."""
    context_json: bytes
    directory: Path
    journal: CheckpointJournal
    ack_attempted: bool = False

    def context(self):
        return json.loads(self.context_json)

    @property
    def file(self):
        return self.directory/'world.s14'

    def verified_file(self):
        context = self.context()
        raw = self.file.read_bytes()
        expected = context['manifest']['parts']['world.s14']
        require(len(raw) == expected['size'] and sha(raw) == expected['sha256'] and
                self.journal.verified_parts()['world.s14'] == raw, 'Received local file changed')
        return raw


def receive_staged(control, connect_download, *, checkpoint_id, scope, epoch, period,
                   cut, attachments, directory):
    """Download on a separate actual TLS client; retain actual journal + file.

    connect_download(token) must create the existing pinned room_transport.Client.
    directory is a NEW coordinator-owned private directory, never a Steam path.
    A failed partial directory is retained; retry needs explicit inspection.
    """
    require(control.player_id == 'B', 'Guest control connection required')
    reply = control.request(dict(action='checkpoint_download_offer', checkpoint_id=checkpoint_id))
    require(reply.get('ok') is True and reply.get('checkpoint_id') == checkpoint_id, 'Download offer rejected')
    receiver = CheckpointReceiver(reply['manifest'], checkpoint_id, scope, epoch, period, cut)
    require(receiver.manifest['parts']['world.s14']['size'] <= 16*1024*1024,
            'File exceeds warm native profile limit')
    folder = Path(directory).resolve()
    folder.mkdir(exist_ok=False)
    transfer = receive_checkpoint(connect_download(reply['download_token']), receiver, action='checkpoint_chunk')
    context = dict(checkpoint_id=checkpoint_id, scope=deepcopy(scope), manifest=receiver.manifest,
                   attachments=deepcopy(attachments))
    journal = CheckpointJournal(folder/'checkpoint.sqlite', scope, receiver.manifest, checkpoint_id,
                                epoch, period, cut, attachments, create=True)
    journal.stage(receiver)
    # Independent reopening catches a database/file mismatch before exposing it.
    journal = CheckpointJournal(folder/'checkpoint.sqlite', scope, receiver.manifest, checkpoint_id,
                                epoch, period, cut, attachments)
    require(journal.verified_parts() == transfer['parts'], 'Journal bytes differ')
    for name, data in [('world.s14', transfer['parts']['world.s14']),
                       ('adapter.json', transfer['parts']['adapter.json']), ('context.json', canonical(context))]:
        with (folder/name).open('xb') as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
    result = ReceivedCheckpoint(canonical(context), folder, journal)
    result.verified_file()
    return result


def report_warm_completion(control, received, *, profile_sha256, receipt_key, attempt,
                           pid, birth, loaded_date, viewer_force, viewer_ruler):
    """Call only after the local coordinator's actual deep native acceptance.

    These arguments record that result; they do NOT replace its verifier. Even
    valid-looking remote arguments cannot advance the existing coordinator.
    A sent request whose reply is lost is not automatically replayed.
    """
    require(type(received) is ReceivedCheckpoint and not received.ack_attempted,
            'Completion already attempted or foreign local record')
    require(control.player_id == 'B', 'Guest control connection required')
    number(attempt, high=2**64)
    number(birth, high=2**64)
    context = received.context()
    manifest = context['manifest']
    received.verified_file()
    packet = dict(action=ACTION, checkpoint_id=context['checkpoint_id'], scope_sha256=digest(context['scope']),
                  epoch=manifest['epoch'], period=manifest['period'], cut=manifest['cut'],
                  file_sha256=manifest['parts']['world.s14']['sha256'], file_size=manifest['parts']['world.s14']['size'],
                  profile_sha256=profile_sha256, receipt_key=receipt_key, attempt=str(attempt), pid=pid, birth=str(birth),
                  loaded_date=deepcopy(loaded_date), viewer_force=viewer_force, viewer_ruler=viewer_ruler)
    validate_ack(packet, manifest, context['scope'], context['checkpoint_id'])
    received.ack_attempted = True
    # Durable record precedes the send; failure does not create a retry right.
    with (received.directory/'warm-ack-attempt.json').open('xb') as out:
        out.write(canonical(packet)); out.flush(); os.fsync(out.fileno())
    reply = control.request(packet)
    require(reply.get('ok') is True and reply.get('warm_completion', {}).get('packet') == packet,
            'Warm diagnostic completion rejected or unpaired')
    require(all(reply['warm_completion'].get(k) is False for k in
                ('full_world_verified', 'ready_authorized', 'next_period_authorized', 'native_gameplay_enabled')),
            'Unexpected authority in diagnostic ACK')
    return reply
