"""Signed diagnostic completion for a retained, observed-boundary B Session.

No verify_held boolean, native fence, input permission or Ready is inferred.
Reply loss is terminal even when native loading or A's loaded transition already
succeeded. Journals, requests, native modules and the Session remain retained.
"""
import base64
from copy import deepcopy
from pathlib import Path
import threading

from authoritative_sync import canonical, hexid
from checkpoint_bootstrap_journal import BootstrapCheckpointJournal
from b_remote_session import Session, verify_sources
from b_remote_session_boundary import Observation
from b_warm_remote_completion import compact_witness, sample_check, load_receipt, key_check, durable
from b_warm_projection import TrustedProjection, need
import b_warm_world as world
from observed_completion_contract import (CONTRACT, COVERAGE, packet, boundary_envelope, validate_boundary)


class GuestCompletion:
    def __init__(self, session):
        need(type(session) is Session and session.phase=='ACTIVE' and not session.sessions,
             'Fresh retained diagnostic Session required; no adapter reconstruction')
        key_check(session._key)
        self.session=session;self.control=session.control;self._key=session._key
        self.phase='ACTIVE';self.held=None;self.record_error=None
        self.history=[];self.period=1;self.epoch=None;self.attachments=None
        self.host_identity=None;self.host_sequence=0;self._lock=threading.RLock()

    def _observe(self, context, profile, kind):
        s=self.session
        observed=s.boundary.begin(profile) if kind=='begin' else s.boundary.observe()
        need(type(observed) is Observation,'Actual typed local observation required')
        return boundary_envelope(observed,context,profile,kind,side='B')

    def _host_reply(self, reply, context, profile, kind):
        need(reply.get('boundary_contract')==CONTRACT and
             all(reply.get(k) is v for k,v in COVERAGE.items()) and
             reply.get('native_gameplay_enabled') is False,
             'Reply changed observed-boundary coverage')
        value=reply['host_boundary']
        validate_boundary(value,context,profile,kind,side='A')
        # These are the authenticated A adapter's local observation scalars,
        # not authority inferred from arbitrary native addresses in a packet.
        o=value;identity=(o['pid'],o['birth'])
        need(self.host_identity is None or self.host_identity==identity,'A process lifetime changed')
        need(o['sequence']>self.host_sequence,'A observation did not advance')
        self.host_identity=identity;self.host_sequence=o['sequence']

    def _terminal(self, exc, received):
        self.phase='TERMINAL';self.held=type(exc).__name__+': '+str(exc)
        self.session.phase='TERMINAL';self.session.boundary.hold(self.held)
        try:
            durable(received.directory/'observed-adapter-failed.json',dict(error=self.held,
                native_or_remote_completion_may_have_succeeded=True,retry_allowed=False,
                input_exclusion_proven=False,scheduler_fence_proven=False,ready_authorized=False))
        except BaseException as log_exc:
            self.record_error=repr(log_exc);exc.record_error=self.record_error

    def apply(self, received, request, profile):
        with self._lock,self.session._lock:
            need(self.phase=='ACTIVE','Observed completion terminal/consumed; no replay')
            self.phase='APPLYING';s=self.session
            try:
                need(s.phase=='ACTIVE' and s.control is self.control and s._key==self._key and
                     len(s.sessions)==len(self.history)<2,'Retained Session changed or consumed outside this adapter')
                verify_sources(s.source_pins)
                context=s._validate(received,request,profile,None);m=context['manifest']
                need(m['period']==self.period and (self.epoch is None or m['epoch']==self.epoch) and
                     (self.attachments is None or context['attachments']==self.attachments),
                     'Authority period/epoch/attachment lineage differs')
                before_boundary=self._observe(context,profile,'begin')
                before=dict(attachment=context['attachments']['B'],viewer_force=profile.currentForce,safe_boundary=True)
                body=dict(kind='begin',context=context,profile=base64.b64encode(bytes(profile)).decode('ascii'),
                    guest_before=before,bootstrap=type(received.journal) is BootstrapCheckpointJournal,
                    boundary=before_boundary)
                durable(received.directory/'observed-adapter-begin.json',body)
                reply=self.control.request(packet(self._key,body))
                need(reply.get('ok') is True,'Host rejected observed reservation: '+str(reply.get('error')))
                need(reply.get('checkpoint_id')==request.checkpoint and hexid(reply.get('intent'),32) and
                     int(reply['intent'],16),'Reservation identity differs')
                self._host_reply(reply,context,profile,'begin')
                permit=received.journal.reserve_load(reply['intent'],reply['host_observation'],before)
                # A fresh complete read before native entry, not a held flag.
                self._observe(context,profile,'begin')
                outcome=s.apply_native(received,request,profile,reservation=permit)
                answer=TrustedProjection._completion(None,outcome['completion'],profile,m)
                sample_check(outcome['sample'],profile,context,answer['accepted']['receipt_key'],answer)
                received.verified_file()
                after_boundary=self._observe(context,profile,'complete')
                receipt=load_receipt(context,reply['intent'],answer)
                received.journal.complete(receipt)
                body=dict(kind='complete',checkpoint_id=request.checkpoint,intent=reply['intent'],
                    completion=answer,sample=compact_witness(outcome['sample']),receipt=receipt,boundary=after_boundary)
                durable(received.directory/'observed-adapter-completion.json',body)
                result=self.control.request(packet(self._key,body))
                need(result.get('ok') is True,'Host rejected observed completion: '+str(result.get('error')))
                need(result.get('checkpoint_id')==request.checkpoint and result.get('intent')==reply['intent'] and
                     result.get('result')=='OBSERVED_REMOTE_PARTIAL_LOADED' and result.get('contract')==world.CONTRACT and
                     result.get('ready_authorized') is False and result.get('full_world_verified') is False,
                     'Completion reply identity/authority differs')
                self._host_reply(result,context,profile,'complete')
                progress=result['protocol_progress'];args=received.journal.coordinator_arguments()
                need(progress.get('period')==self.period+1 and hexid(progress.get('epoch'),32) and
                     progress['epoch']!=m['epoch'],'Authority returned another period')
                durable(received.directory/'observed-adapter-reply.json',result)
                self.history.append(dict(checkpoint_id=request.checkpoint,period=self.period,
                    intent=reply['intent'],native_receipt=answer['accepted']['receipt_key'],result=deepcopy(result)))
                self.attachments=deepcopy(context['attachments']);self.attachments['B']=args['new_attachment']
                self.period,self.epoch=progress['period'],progress['epoch']
                self.phase='ACTIVE' if len(self.history)<2 else 'TWO_COMPLETIONS_RETAINED'
                return result
            except BaseException as exc:
                self._terminal(exc,received)
                raise

    def status(self):
        return dict(phase=self.phase,held=self.held,formal_completions=len(self.history),
            boundary_contract=CONTRACT,input_exclusion_proven=False,scheduler_fence_proven=False,
            full_world_verified=False,native_gameplay_enabled=False,ready_authorized=False)
