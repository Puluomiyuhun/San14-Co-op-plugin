"""A-side exact captured proposal submission through the mounted TLS gate.

Only a trusted local caller may supply PendingReward and current attachment.
Queue acknowledgement never permits native menu closure or claims UI refresh.
"""
from copy import deepcopy
import threading
from a_reward_runtime_mount import RuntimeMount
from reward_checkpoint_shared_cut import SharedCutGate
from reward_menu_capture import PendingReward
from reward_room_flow import envelope
from reward_observed_context import need
from b_warm_received_apply import write_once
import execution_journal as journal

class MenuRewardSession:
    def __init__(self,mount):
        need(type(mount) is RuntimeMount and type(mount.gate) is SharedCutGate,
             'Exact retained A RuntimeMount and shared cut gate required')
        self.mount=mount;self.lock=threading.RLock();self.failed=None;self.rows={}
        with mount.gate.lock,mount.room.lock,mount.c.lock:
            mount.gate._current()
            need(mount.phase=='ACTIVE' and 'A' not in mount.gate.finished and
                 not hasattr(mount,'_menu_submission_owner'),'One menu proposal owner in active A Planning required')
            self.owners=(mount.service,mount.room,mount.c,mount.flow,mount.gate,mount.port,mount.native,mount.entry)
            self.control=mount.service.control;self.connection=mount.room.players['A']['connection']
            self.attachment=mount.attachment;self.scope=deepcopy(mount.flow.scope);self.binding=deepcopy(mount.gate.binding)
            need(self.control.player_id=='A' and self.connection and self.attachment==mount.c.attachments['A'],
                 'Current authenticated A attachment required')
            self.records=mount.records/'menu-proposals';self.records.mkdir(exist_ok=False)
            mount._menu_submission_owner=self

    def _current(self,pending,attachment_id):
        m=self.mount
        # Same order as flow/poll/cut. No gate/room/coordinator lock crosses TLS.
        with m.gate.lock,m.room.lock,m.c.lock:
            need(self.failed is None and m._menu_submission_owner is self and
                 self.owners==(m.service,m.room,m.c,m.flow,m.gate,m.port,m.native,m.entry) and
                 m.service.control is self.control and m.room.players['A']['connection']==self.connection and
                 m.phase=='ACTIVE' and not m.failure and 'A' not in m.gate.finished,
                 'A mount/connection ended or input finished; no replay')
            m.gate._current()
            need(m.gate.binding==self.binding and journal.canonical(m.flow.scope)==journal.canonical(self.scope) and
                 bytes(m.prep)==m.prepared_bytes and m.attachment==self.attachment==m.c.attachments['A'],
                 'A native/checkpoint attachment drifted')
            need(type(pending) is PendingReward and pending.player_id=='A' and
                 type(attachment_id) is str and attachment_id==self.attachment==m.port.attachment_id,
                 'Exact A proposal/current attachment required')
            packet=pending.packet();scope=m.flow.scope
            need(packet==envelope(scope,'reward_submit',request_id=pending.request_id,
                     district_id=pending.district_id,officer_ids=list(pending.officer_ids)),
                 'Captured A room/binding/planning epoch differs')
            need(journal.hex_id(pending.request_id,32) and journal.hex_id(pending.preview_sha256) and
                 type(pending.district_id) is int and pending.district_id==scope['bindings']['A']['main_district_id'] and
                 type(pending.officer_ids) is tuple and 1<=len(pending.officer_ids)<=16 and
                 all(type(i) is int and 1<=i<6000 for i in pending.officer_ids) and len(set(pending.officer_ids))==len(pending.officer_ids),
                 'Malformed or foreign captured A proposal')
            m.port.context(scope['bindings']['A']['force_id'])
            return packet

    @staticmethod
    def _public(row,duplicate):
        return dict(authority_ack=deepcopy(row['reply']),request_id=row['packet']['request_id'],
            local_duplicate=duplicate,proposal_only=True,native_menu_close_authorized=False,
            native_execution_verified=False,ui_refresh_verified=False)

    def submit_pending(self,pending,*,attachment_id):
        with self.lock:
            try:
                packet=self._current(pending,attachment_id)
                fingerprint=journal.digest(dict(packet=packet,preview_sha256=pending.preview_sha256,attachment=attachment_id))
                row=self.rows.get(pending.request_id)
                if row is not None:
                    need(row['fingerprint']==fingerprint and row['state']=='ACKNOWLEDGED',
                         'A request ID changed or result unresolved')
                    return self._public(row,True)
                need(len(self.rows)<256,'A menu proposal capacity exhausted')
                row=dict(packet=deepcopy(packet),fingerprint=fingerprint,state='INTENT',reply=None)
                self.rows[pending.request_id]=row
                write_once(self.records/(pending.request_id+'-intent.json'),dict(packet=packet,
                    preview_sha256=pending.preview_sha256,attachment=attachment_id,proposal_only=True))
                reply=self.control.request(packet)
                need(type(reply) is dict and reply.get('ok') is True and reply.get('player')=='A' and
                     reply.get('request_id')==pending.request_id and type(reply.get('ordinal')) is int and reply['ordinal']>0 and
                     reply.get('status') in ('QUEUED','DISPATCHING','AWAITING_B','PAIRED','REJECTED') and
                     type(reply.get('duplicate')) is bool,'A proposal rejected or acknowledgement differs')
                write_once(self.records/(pending.request_id+'-ack.json'),reply)
                row.update(state='ACKNOWLEDGED',reply=deepcopy(reply));return self._public(row,False)
            except BaseException as exc:
                self.failed=self.failed or repr(exc);m=self.mount
                with m.gate.lock,m.room.lock,m.c.lock:m.hold(exc)
                try:write_once(self.records/'held.json',dict(error=self.failed,no_replay=True,native_menu_close_authorized=False))
                except BaseException as secondary:exc.menu_record_error=repr(secondary)
                raise
