"""Keep one HWND input owner bound to each accepted three-chain world.

Each transition remains LOAD-held. Fresh command owners must be installed and
verified separately before reopening planning. No game discovery or installer.
"""
from copy import deepcopy
from pathlib import Path
import hashlib

from b_remote_chain_session import Session,verify_sources
from b_observed_chain_completion import GuestCompletion
from b_remote_session_boundary import Observation
from b_warm_received_apply import write_once
import player_input_rebind_port as inputs
from authoritative_sync import canonical

FLAGS=dict(input_planning_open=False,next_reward_lane_installed=False,
           third_checkpoint_enabled=False,native_gameplay_enabled=False,
           full_input_exclusion_proven=False,room_ready_sent=False)

def need(ok,message):
    if not ok:raise ValueError(message)

def observe_completed(session,guest):
    """Current local completion owners plus fresh authenticated room observation."""
    need(type(session) is Session and type(guest) is GuestCompletion and guest.session is session,
         'Exact retained checkpoint owners required')
    s,g=session,guest
    n=len(g.history)
    expected=('ACTIVE','ACTIVE') if n<3 else ('THREE_LOADS_RETAINED','THREE_COMPLETIONS_RETAINED')
    need(n in (1,2,3) and len(s.sessions)==n and (s.phase,g.phase)==expected and
         g.period==n+1 and not g.held,
         'Accepted native loads and formal completions required')
    need(s.control is g.control and s.control.status()['transport_open'] is True and
         s.read_birth()==s.native_identity[1] and s.reader.pid==s.native_identity[0],
         'Live reader or retained authenticated connection changed')
    need(not s.warm.calls.uncertain and not getattr(s.factory,'uncertain',False),
         'Native loading/rules result uncertain')
    verify_sources(s.source_pins)
    for index,(native,formal) in enumerate(zip(s.sessions,g.history),1):
        need(native['period']==formal['period']==index and native['checkpoint']==formal['checkpoint_id'],
             'Native and formal checkpoint history differ')
        need(native['result']['completion']['accepted']['receipt_key']==formal['native_receipt'],
             'Formal completion is bound to another native receipt')
    last=g.history[-1];progress=last['result']['protocol_progress']
    need(progress['period']==g.period and progress['epoch']==g.epoch,'Final formal progress differs')
    port=s.lifecycle.current
    need(not port.retired and port.world.generation==n+1 and port.world.checkpoint==last['checkpoint_id'],
         'Current human rules belong to another world')
    port.observe(True)
    local=s.boundary.observe()
    need(type(local) is Observation and (local.pid,local.birth)==s.native_identity,
         'Current local planning observation differs')
    p=s.boundary.profile
    need(p.currentForce==p.target.force and bytes(p.before)==bytes(p.loaded),
         'Loaded target planning identity not established')
    reply=s.control.request(dict(action='pilot_context'))
    need(type(reply) is dict and reply.get('ok') is True and reply.get('native_gameplay_enabled') is False,
         'Authenticated current room observation refused')
    c=reply['context'];node=dict(year=p.loaded.year,month=p.loaded.month,day=p.loaded.day,phase='PLANNING_BOUNDARY')
    need(canonical(c['scope'])==canonical(s.scope) and c['phase']=='PLANNING' and c['period']==g.period and
         c['epoch']==g.epoch and c['attachments']==g.attachments and c['node']==node,
         'Room has not settled at this loaded planning boundary')
    return dict(pid=local.pid,birth=local.birth,room_id=s.scope['room_id'],period=g.period,epoch=g.epoch,
        attachment=g.attachments['B'],checkpoint=last['checkpoint_id'],node=node,
        profile_sha256=hashlib.sha256(bytes(p)).hexdigest(),rules_generation=port.world.generation,
        observation_sequence=local.sequence,completed_checkpoints=n,**FLAGS)

def rebind_after_load(session,guest,input_owner,*,records):
    """Exactly one attempt per checkpoint, retaining the same input owner."""
    need(type(session) is Session and type(guest) is GuestCompletion and guest.session is session and
         type(input_owner) is inputs.InputLease,'Exact checkpoint and successor input owners required')
    with guest._lock,session._lock,input_owner.lock:
        transitions=getattr(session,'_chain_input_transitions',None)
        if transitions is None:
            need(getattr(session,'_chain_input_owner',input_owner) is input_owner,
                 'Preinstalled input owner cannot be replaced')
            transitions={};session._chain_input_transitions=transitions
            session._chain_input_owner=input_owner
        need(session._chain_input_owner is input_owner,'Input owner cannot be replaced between worlds')
        n=len(guest.history)
        need(n in (1,2,3) and n not in transitions,'This checkpoint already attempted input transition')
        need(len(transitions)==n-1 and all(transitions[i]['phase']=='REBOUND_HELD' for i in range(1,n)),
             'Prior input transitions missing or not acknowledged')
        directory=Path(records);need(directory.is_absolute(),'Absolute fresh transition records required')
        directory.mkdir(parents=True,exist_ok=False)
        state=dict(phase='CHECKING',records=str(directory),rebind_attempted=False,**FLAGS)
        transitions[n]=state
        try:
            input_owner.state.require_known();before=observe_completed(session,guest)
            old=input_owner.binding
            need(input_owner.local_binding[:2]==session.native_identity and bytes(old.room).hex()==before['room_id'] and
                 old.seat==1 and old.period==before['period']-1,'Input owner belongs to another process/room/period')
            target=inputs.Binding();target.room[:]=bytes.fromhex(before['room_id']);target.epoch[:]=bytes.fromhex(before['epoch'])
            target.attachment[:]=bytes.fromhex(before['attachment']);target.period=before['period'];target.seat=1
            write_once(directory/'intent.json',dict(observation=before,old_binding=inputs.common.base.values(old),
                new_binding=inputs.common.base.values(target),**FLAGS))
            state['rebind_attempted']=True
            receipt=input_owner.rebind_after_load(target)
            after=observe_completed(session,guest)
            need(all(before[k]==after[k] for k in before if k!='observation_sequence') and
                 after['observation_sequence']>before['observation_sequence'], 'Loaded boundary changed during input transition')
            snapshot=input_owner.snapshot()
            need(bytes(snapshot.binding)==bytes(target) and snapshot.phase==2 and snapshot.held and snapshot.acknowledged and
                 snapshot.revision==snapshot.acknowledgedRevision and not any((snapshot.pending,snapshot.active,snapshot.leaseId,
                 snapshot.localCommandPolicyOpen,snapshot.remoteExecutionPolicyOpen)), 'Rebound input did not remain held')
            result=dict(result='NEW_WORLD_INPUT_BOUND_STILL_HELD',before=before,after=after,input_receipt=receipt,**FLAGS)
            write_once(directory/'result.json',result);state['phase']='REBOUND_HELD'
            return result
        except BaseException as exc:
            state.update(phase='HELD',error_type=type(exc).__name__)
            # No native retry/cleanup RPC after an uncertain rebind. Both native
            # outcomes retain LOAD; terminal owners prevent subsequent reopening.
            input_owner.failed=input_owner.failed or repr(exc)
            session.phase=guest.phase='TERMINAL';session.boundary.hold(repr(exc));guest.held=repr(exc)
            try:write_once(directory/'failed.json',deepcopy(state))
            except BaseException as secondary:state['record_error']=repr(secondary)
            raise
