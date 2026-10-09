"""Existing ordered reward flow with checked local ports; no Ready permission.

The independent reward projection is not the observed save/load Room contract.
No menu hook, game process, network service, or native executor is created here.
"""
from copy import deepcopy
from types import MappingProxyType
import threading

from reward_observed_context import CheckedPort,CONTRACT,need
from reward_room_flow import RewardFlow,Replica,envelope,report_proof

CAPABILITIES=MappingProxyType(dict(
    schema='san14.reward-observed-capabilities.v1',state_contract=CONTRACT,
    actual_game_reader_context=True,actual_projected_result_validation=True,
    shared_authority_queue=True,durable_execution_journal=True,
    full_world_verified=False,input_exclusion_proven=False,ui_refresh_verified=False,
    menu_interception_installed=False,production_native_submit_bridge=False,
    observed_room_ready_integration=False,native_gameplay_enabled=False,
    required_native_port='same-retained-User-Save-Owner identity()+execute(command)',
    native_hook_writes=(),read_resources=('root/world/date','person/task/army-pools',
       'two-player-force/district/funding-city','five-planning-state-identities')))


class ObservedRewardFlow(RewardFlow):
    def __init__(self,folder,room,host_port,guest_attachment,initial_node,*,guest_report_key):
        need(type(host_port) is CheckedPort,'Checked production-context port required')
        sampler=host_port.sampler
        need(room.bindings is not None and sampler.viewer==room.bindings['A']['force_id'] and
             {f:v['district'] for f,v in sampler.players.items()}==
             {v['force_id']:v['main_district_id'] for v in room.bindings.values()} and
             initial_node==dict(**sampler.node,phase='PLANNING_BOUNDARY'),
             'Host native binding/date differs from authenticated room')
        super().__init__(folder,room,host_port,guest_attachment,CONTRACT,initial_node,guest_report_key=guest_report_key)
        # The local attachment epoch and this fresh wire ordering epoch are
        # distinct identities. Replica's immutable attachment binds the two;
        # never rewrite the local owner's epoch to make them numerically equal.
        self.local_attachment_epoch=host_port.sampler.epoch

    def handle(self,player,connection,request):
        need(request.get('action')!='reward_ready','This finite reward adapter cannot authorize Ready')
        return super().handle(player,connection,request)

    def seal(self):raise ValueError('Reward projection is not observed Room/native Ready permission')

    def retire(self,reason):
        with self.lock,self.room.lock:
            self.host.port.retire(reason);self.hold(str(reason));self.period.phase='HELD'


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
