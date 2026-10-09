"""Explicit formal first source-view to target-view checkpoint successor.

The frozen Journal and Projection require a target viewer before loading.
This module instead uses the separately versioned BootstrapCheckpointJournal
for period 1, preserving truthful source observations and strict target receipts.
After that one transition use the ordinary Journal/TrustedProjection. No game
launcher, input fence, remote native permission, or world-coverage claim lives here.
"""
import base64
from copy import deepcopy
import hashlib
import os
from pathlib import Path

from authoritative_sync import CheckpointReceiver, CHUNK, canonical, digest, require
from checkpoint_bootstrap_journal import BootstrapCheckpointJournal
from checkpoint_transfer import receive_checkpoint
from b_warm_room import ReceivedCheckpoint
from b_warm_projection import TrustedProjection, need
from b_warm_bootstrap import BootstrapReceivedApply, BootstrapRulesBridge
from b_warm_profile_contract import Profile, validate_profile
from human_rules_world_lifecycle import NextWorldRequest
import b_warm_staging as files
import b_warm_world as world

def receive_bootstrap_staged(control, connect_download, *, checkpoint_id, scope, epoch, period,
                   cut, attachments, directory):
    """Download on a separate actual TLS client; retain actual journal + file.

    connect_download(token) must create the existing pinned room_transport.Client.
    directory is a NEW coordinator-owned private directory, never a Steam path.
    A failed partial directory is retained; retry needs explicit inspection.
    """
    require(type(period) is int and period == 1, 'Bootstrap receive is only valid for initial period')
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
    journal = BootstrapCheckpointJournal(folder/'checkpoint.sqlite', scope, receiver.manifest, checkpoint_id,
                                epoch, period, cut, attachments, create=True)
    journal.stage(receiver)
    # Independent reopening catches a database/file mismatch before exposing it.
    journal = BootstrapCheckpointJournal(folder/'checkpoint.sqlite', scope, receiver.manifest, checkpoint_id,
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


def bootstrap_receiver_from_journal(journal):
    """Recheck durable received bytes; no dependency on A's package instance."""
    need(type(journal) is BootstrapCheckpointJournal, 'Actual local journal required')
    i=journal.identity;m=i['manifest']
    receiver=CheckpointReceiver(m,i['checkpoint_id'],i['scope'],m['epoch'],m['period'],m['cut'])
    for name,data in journal.verified_parts().items():
        for offset in range(0,len(data),CHUNK):
            receiver.accept(dict(checkpoint_id=i['checkpoint_id'],part=name,index=offset//CHUNK,
                                 data=base64.b64encode(data[offset:offset+CHUNK]).decode('ascii')))
    need(receiver.verified_parts()==journal.verified_parts(), 'Staged bytes changed during reconstruction')
    return receiver


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

class BootstrapProjection(TrustedProjection):
    """Period-1 source precondition; inherited target completion stays strict.

    A new, separate journal is created by receive_bootstrap_staged. No old DB
    is migrated and no target-view observation is fabricated. Failure is terminal
    for this owner, and an existing INTENT never permits another native attempt.
    """
    def apply(self, journal, receiver, profile, *, host_receipt_key):
        """Reserve the real journal once, load once, then apply real loaded().

        native_load(permit) may call ReceivedApply.apply(...,reservation=permit)
        and return its actual completion. It must not accept a remote ACK as a
        substitute. A failure retains INTENT and never reissues native work.
        """
        with self._lock:
            self._held()
            try:
                need(type(journal) is BootstrapCheckpointJournal and type(receiver) is CheckpointReceiver,
                     'Actual staged journal and verified receiver required')
                need(type(profile) is Profile, 'Typed profile required');validate_profile(profile)
                c=self.coordinator;identity=journal.identity;m=identity['manifest']
                need(c.period == 1 and not c.applied_receipts and
                     profile.currentForce == profile.source.force and profile.source.force != profile.target.force and
                     identity['pre_load_viewer_force'] == profile.source.force,
                     'Bootstrap requires initial source viewer and no prior applied checkpoints')
                need(m['state_contract']==world.CONTRACT, 'Offered checkpoint has a different contract')
                need((profile.file.size,bytes(profile.file.sha256).hex()) ==
                     (m['parts']['world.s14']['size'],m['parts']['world.s14']['sha256']), 'Profile differs from checkpoint bytes')
                with c.lock:
                    need(c.phase=='RECONCILING' and c.scope==identity['scope'] and c.manifest==m and
                         c.checkpoint_id==identity['checkpoint_id'] and c.attachments==identity['attachments'] and
                         c.period==m['period'] and c.epoch==m['epoch'], 'Coordinator/journal lineage differs')
                    need((profile.before.year,profile.before.month,profile.before.day)==tuple(c.node[k] for k in ('year','month','day')) and
                         (profile.loaded.year,profile.loaded.month,profile.loaded.day)==tuple(m['node'][k] for k in ('year','month','day')),
                         'Profile dates differ from the offered period')
                    context=dict(scope=deepcopy(c.scope),epoch=c.epoch,period=c.period,node=deepcopy(m['node']))
                need(journal.verified_parts()==receiver.verified_parts(), 'Verified byte stores differ')
                a=self._sample('A',profile,host_receipt_key,context)
                need(a['partial_sha256']==m['world_sha256'], 'A changed its declared projection')
                host=dict(attachment=identity['attachments']['A'],world_sha256=a['partial_sha256'],node=m['node'])
                guest=self.guest_before()
                need(guest==dict(attachment=identity['attachments']['B'],viewer_force=profile.source.force,safe_boundary=True),
                     'Trusted initial source-view boundary differs')
                self._held()
                c.received('B',m['epoch'],receiver)
                intent=c.begin_guest_load('B',m['epoch'])
                permit=journal.reserve_load(intent,host,guest)
                self._held()
                answer=self._completion(self.native_load(permit),profile,m)
                self._held()
                b=self._sample('B',profile,answer['accepted']['receipt_key'],context,answer)
                again=self._sample('A',profile,host_receipt_key,context)
                comparison=world.compare(again,b)
                need(a['shared']==again['shared'] and comparison['result']=='PARTIAL_MATCH' and
                     b['partial_sha256']==m['world_sha256'], 'Loaded declared projection differs')
                # New attachment is a local protocol lifetime, derived from this
                # exact journal intent and independently accepted native result.
                new_attachment=digest(dict(checkpoint=identity['checkpoint_id'],intent=intent,
                    pid=answer['pid'],birth=answer['birth'],attempt=answer['attempt'],
                    receipt_key=answer['accepted']['receipt_key']))[:32]
                receipt=dict(player='B',epoch=m['epoch'],checkpoint_id=identity['checkpoint_id'],intent=intent,
                    world_sha256=b['partial_sha256'],viewer_force=profile.target.force,attachment=new_attachment,
                    host_observation=host)
                self._held();journal.complete(receipt)
                current_host=self._sample('A',profile,host_receipt_key,context)
                current_guest=self._sample('B',profile,answer['accepted']['receipt_key'],context,answer)
                need(current_host['shared']==again['shared'] and current_guest['shared']==b['shared'],
                     'Projection changed before receipt application')
                self._held()
                progress=journal.apply_to_coordinator(c,host,dict(attachment=new_attachment,
                    viewer_force=profile.target.force,world_sha256=b['partial_sha256'],node=m['node'],safe_boundary=True))
                return dict(result='BOOTSTRAP_DECLARED_PROJECTION_LOADED',contract=world.CONTRACT,partial_sha256=b['partial_sha256'],
                    protocol_progress=progress,comparison=comparison,source_kind=self.source_kind,
                    native_gameplay_enabled=False,full_world_verified=False,native_full_world_coverage_verified=False,
                    ready_authorized=False,fence_released=False)
            except BaseException as exc:
                self.held_reason=type(exc).__name__+': '+str(exc)
                raise
