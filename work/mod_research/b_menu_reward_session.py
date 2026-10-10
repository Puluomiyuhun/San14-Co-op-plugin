"""Trusted PendingReward proposal submission; never native menu permission.

The captured packet/request ID is immutable. An accepted queue reply is not a
native completion, UI refresh or permission to close the captured menu.
"""
from copy import deepcopy
import hashlib
import threading
from reward_menu_capture import PendingReward
from reward_observed_context import need
from reward_room_flow import envelope
from b_reward_session import RewardSession
from b_warm_received_apply import write_once
import execution_journal as journal
import b_input_reward_runner as predecessor

class MenuRewardSession:
    def __init__(self,reward):
        need(type(reward) is RewardSession,'Exact retained B reward session required')
        with reward.lock:
            reward._binding();need(reward.phase=='ACTIVE' and not reward.cut.prepared and
                not hasattr(reward,'_menu_submission_owner'),'One menu submission owner in active Planning required')
            self.reward=reward;self.bound=reward.bound;self.scope=deepcopy(reward.replica.scope)
            self.records=reward.records/'menu-proposals';self.records.mkdir(exist_ok=False)
            self.rows={};self.failed=None;self.lock=threading.RLock();reward._menu_submission_owner=self

    def _current(self,pending,attachment_id):
        r=self.reward;r._binding()
        need(self.failed is None and r._menu_submission_owner is self and r.bound==self.bound and
             r.phase=='ACTIVE' and not r.cut.prepared,'Menu proposal scope ended; no replay')
        need(type(pending) is PendingReward and pending.player_id=='B' and
             type(attachment_id) is str and attachment_id==self.bound[3]['B']==r.guest.attachments['B']==r.replica.port.attachment_id,
             'Exact B proposal and current native attachment required')
        packet=pending.packet();scope=r.replica.scope
        need(journal.canonical(scope)==journal.canonical(self.scope) and
             packet==envelope(scope,'reward_submit',request_id=pending.request_id,district_id=pending.district_id,officer_ids=list(pending.officer_ids)),
             'Captured room/binding/planning epoch differs')
        need(journal.hex_id(pending.request_id,32) and journal.hex_id(pending.preview_sha256) and
             type(pending.district_id) is int and pending.district_id==scope['bindings']['B']['main_district_id'] and
             type(pending.officer_ids) is tuple and 1<=len(pending.officer_ids)<=16 and
             all(type(i) is int and 1<=i<6000 for i in pending.officer_ids) and len(set(pending.officer_ids))==len(pending.officer_ids),
             'Malformed or foreign captured proposal')
        # Real local sampler checks retained identities/date before submission.
        # This proves no permission to close a native menu or bypass authority.
        r.replica.port.context(scope['bindings']['B']['force_id'])
        return packet

    @staticmethod
    def _public(row,duplicate):
        return dict(authority_ack=deepcopy(row['reply']),local_duplicate=duplicate,
            request_id=row['packet']['request_id'],proposal_only=True,
            native_menu_close_authorized=False,native_execution_verified=False,ui_refresh_verified=False)

    def submit_pending(self,pending,*,attachment_id):
        r=self.reward
        with self.lock,r.lock:
            try:
                packet=self._current(pending,attachment_id)
                fingerprint=journal.digest(dict(packet=packet,preview_sha256=pending.preview_sha256,attachment=attachment_id))
                old=self.rows.get(pending.request_id)
                if old is not None:
                    need(old['fingerprint']==fingerprint and old['state']=='ACKNOWLEDGED','Request reused with changed proposal or unresolved outcome')
                    return self._public(old,True)
                need(len(self.rows)<256,'Menu proposal lifetime capacity exhausted')
                row=dict(packet=deepcopy(packet),fingerprint=fingerprint,state='INTENT',reply=None)
                self.rows[pending.request_id]=row
                write_once(self.records/(pending.request_id+'-intent.json'),dict(packet=packet,
                    preview_sha256=pending.preview_sha256,attachment=attachment_id,proposal_only=True))
                reply=r.cut._request(packet)
                need(type(reply) is dict and reply.get('ok') is True and reply.get('player')=='B' and
                     reply.get('request_id')==pending.request_id and type(reply.get('ordinal')) is int and reply['ordinal']>0 and
                     reply.get('status') in ('QUEUED','DISPATCHING','AWAITING_B','PAIRED','REJECTED') and
                     type(reply.get('duplicate')) is bool,'Foreign or malformed proposal acknowledgement')
                write_once(self.records/(pending.request_id+'-ack.json'),reply)
                row.update(state='ACKNOWLEDGED',reply=deepcopy(reply));return self._public(row,False)
            except BaseException as exc:
                self.failed=self.failed or repr(exc);r.hold(exc)
                try:write_once(self.records/'held.json',dict(error=self.failed,no_replay=True,native_menu_close_authorized=False))
                except BaseException as secondary:exc.menu_record_error=repr(secondary)
                raise

class Runner(predecessor.Runner):
    """Thin inherited entry; only adds exact-packet proposal submission."""
    def _reward_sources(self,pins):
        super()._reward_sources(pins)
        path=predecessor.predecessor.HERE/'b_menu_reward_session.py'
        need(pins.get(str(path.resolve()))==hashlib.sha256(path.read_bytes()).hexdigest(),'Menu submission source missing or changed')

    def submit_pending(self,pending,*,attachment_id):
        with self.reward_lock:
            need(self.phase=='REWARD_PLANNING' and self.reward is not None and not self.finish_requested.is_set(),
                 'B planning no longer accepts confirmations')
            if not hasattr(self,'menu'):self.menu=MenuRewardSession(self.reward)
            return self.menu.submit_pending(pending,attachment_id=attachment_id)
