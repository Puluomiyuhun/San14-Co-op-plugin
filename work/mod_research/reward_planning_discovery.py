"""Authenticated, read-only discovery of A's first reward planning mount.
Install before bootstrap. The non-reward action remains reachable through the
later MountedEndpoint; a generic room error is never interpreted as readiness.
"""
from copy import deepcopy
import hashlib
from a_reward_runtime_mount import RuntimeMount
from observed_room_service import HostService
from authoritative_sync import scope_from_room
from a_save_runtime_control import require

ACTION='planning_reward_context'
SCHEMA='san14.reward-planning-discovery.v1'

class Endpoint:
    def __init__(self,service,mount,previous):
        self.service,self.mount,self.previous=service,mount,previous
    def authenticate(self,*args):return self.previous.authenticate(*args)
    def disconnect(self,*args):return self.previous.disconnect(*args)
    def handle(self,player,connection,request):
        if type(request) is not dict or request.get('action')!=ACTION:
            return self.previous.handle(player,connection,request)
        try:
            require(request=={'action':ACTION},'Exact planning discovery request required')
            m=self.mount;r=m.room;c=m.c
            with r.lock,c.lock:
                require(player=='B' and r.players.get(player,{}).get('connection')==connection,
                        'Current authenticated B seat required')
                r._bound(c)
                require(c.connected=={'A','B'} and c.phase not in ('HELD','CLOSED','DISCONNECTED') and
                        m.failure is None and self.service.failure is None,
                        'Planning owner unavailable; do not reconnect')
                if m.phase in ('NEW','BINDING','CONFIGURED','OPENING') or (m.phase=='ACTIVE' and m.gate is None):
                    return dict(ok=True,schema=SCHEMA,ready=False,context=None,native_gameplay_enabled=False)
                require(m.phase=='ACTIVE' and m.gate.state=='ACTIVE' and c.bootstrap_completed and
                        c.period==2 and c.phase=='PLANNING' and len(c.applied_receipts)==1 and
                        c.scope==scope_from_room(r) and m.flow.room is r and
                        m.flow.period.attachments==c.attachments,
                        'Initial reward planning window is no longer available')
                return dict(ok=True,schema=SCHEMA,ready=True,context=dict(
                    scope=deepcopy(m.flow.scope),profile_sha256=hashlib.sha256(bytes(m.profile)).hexdigest(),
                    checkpoint_epoch=c.epoch,checkpoint_period=c.period,node=deepcopy(c.node),
                    attachments=deepcopy(c.attachments)),native_gameplay_enabled=False)
        except (ValueError,RuntimeError,TypeError,KeyError) as exc:
            return dict(ok=False,error=str(exc),schema=SCHEMA,native_gameplay_enabled=False)

def install(service,mount):
    require(type(service) is HostService and type(mount) is RuntimeMount and mount.service is service and
            mount.room is service.room and mount.c is service.coordinator,
            'Same retained host service and Runtime mount required')
    require(not hasattr(service,'_reward_planning_discovery') and mount.phase in ('NEW','CONFIGURED'),
            'Install discovery exactly once before opening reward planning')
    server=service.servers[0][0];endpoint=Endpoint(service,mount,server.room)
    service._reward_planning_discovery=endpoint;server.room=endpoint
    return endpoint

def host_entry(service,adapter_key,*,reward_key,guest_cut_key,records,wait_seconds=10):
    """Concrete A entry factory for the paired B reward runner; no native call."""
    from a_reward_runtime_entry import ProtectedRoomEntry
    mount=RuntimeMount(service,reward_key=reward_key,guest_cut_key=guest_cut_key,
                       records=records,wait_seconds=wait_seconds)
    entry=ProtectedRoomEntry(service.room,service.coordinator,adapter_key,mount=mount,no_new_commands=True)
    install(service,mount)
    return entry
