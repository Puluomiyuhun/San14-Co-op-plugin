# Explicit same-Runtime reward coexistence successor; frozen rules engine unchanged.
"""A human-AI protection beside installed save sources, finite observations only.
The original six-site native rules engine is unchanged. Same-world turns retain
one activation; a changed root/world is refused rather than silently rebound.
"""
from copy import deepcopy
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import hashlib
import threading

from authoritative_sync import scope_from_room,digest,next_node
from a_observed_room import ObservedRoom
from a_reward_runtime_boundary import AObservedBoundary
from b_warm_rules_capture import RulesWorldCapture,need
from b_warm_rules_factory import RulesFactory,RulesBuild
from human_rules_activation_room import rules,GAME_SHA
from human_rules_world_lifecycle import Config,Descriptor,NextWorldRequest,ResidentPort
from a_observed_start_call import remote_call
from a_save_runtime_control import RemoteCallUnknown

# (RVA, number of replaced bytes). These are disjoint resources, not permission.
RULE_SITES=((0xC6660,16),(0xC65F0,15),(0xC6580,15),(0xC66A0,15),(0x28DE71,5),(0x28DAA5,5))
SAVE_SITES=((0x3F8606,5),(0x3F9B16,5),(0x13DC09,5),(0x12CC4D0,8),
            (0x12DC620,8),(0x12CC9E0,8),(0x1297D10,8))
CAPABILITIES=dict(shared_runtime_reward=True,same_world_turn=True,world_replacement=False,reward_flow=False,
                  input_exclusion_proven=False,scheduler_fence_proven=False)


def no_overlap(first,second):
    return all(a+n<=b or b+m<=a for a,n in first for b,m in second)


class ProtectedRulesCapture(RulesWorldCapture):
    """A exact-type successor; reused capture still reads all Config fields."""
    def __init__(self,provider,room,coordinator,settings):
        need(type(provider) is AObservedBoundary and type(room) is ObservedRoom,
             'Retained A finite provider and observed Room required')
        need(type(settings) is dict and settings==rules(settings.get('native_income_key5'),settings.get('native_world_option8')),
             'Exact supported rules settings required')
        self.provider,self.room,self.coordinator=provider,room,coordinator
        self.reader=provider.reader;self.pid=provider.pid;self.birth=provider.birth;self.image=provider.base
        self.read_birth=provider.read_birth;self.settings=deepcopy(settings)
        with room.lock,coordinator.lock:
            room._bound(coordinator);self.scope=deepcopy(scope_from_room(room))
            self.connections={k:v['connection'] for k,v in room.players.items()}
        self._check()

    def _check(self):
        p=self.provider;c=self.coordinator
        need(p.reader is self.reader and p.pid==self.pid and p.birth==self.birth and p.base==self.image,
             'A observation identity changed')
        with self.room.lock,c.lock:
            self.room._bound(c)
            need(c.scope==scope_from_room(self.room)==self.scope and c.connected=={'A','B'} and
                {k:v['connection'] for k,v in self.room.players.items()}==self.connections and
                self.scope['profile']['rules_sha256']==digest(self.settings) and
                self.scope['profile']['game_sha256']==GAME_SHA and self.room._held is None and not getattr(self.room,'_closed',False),
                'A room/rules connection held or changed')
            snapshot=self.reader.snapshot()
            node={k:snapshot['date'][k] for k in ('year','month','day')};node['phase']='PLANNING_BOUNDARY'
            allowed=[c.node]
            if c.phase=='RUNNING':allowed.append(next_node(c.node))
            if c.phase=='RECONCILING' and c.manifest is not None:allowed.append(c.manifest['node'])
            need(node in allowed,'A native date is outside current checkpoint boundary')
            p.observe(node)


class ProtectedRulesFactory(RulesFactory):
    """Same real native methods, explicit narrow capture constructor.

The constructor accepts only the A capture. Calls use unknown-safe logging and
the shared A lock; native Prepare/Seal and publisher validation are unchanged.
"""
    def __init__(self, capture, api, build, records, *, rulers):
        need(type(capture) is ProtectedRulesCapture and type(build) is RulesBuild,
             'Typed diagnostic capture/build required')
        need(api.reader is capture.reader, 'API/capture reader differs')
        self.capture, self.api, self.build = capture, api, build
        self.records = Path(records).resolve(strict=True)
        need(self.records.is_dir(), 'Private records directory required')
        self.rulers = dict(rulers)
        need(set(self.rulers) == {capture.scope['bindings'][p]['force_id'] for p in ('A', 'B')} and
             all(type(x) is int and 0 < x < 6000 for x in self.rulers.values()), 'Exact rulers required')
        self.retained=[]; self.publishers=[]; self.claimed=set(); self.failed=None; self.uncertain=False
        self._lock=threading.RLock(); k=api.k
        k.GetProcessId.argtypes=[W.HANDLE]; k.GetProcessId.restype=W.DWORD
        k.GetProcessTimes.argtypes=[W.HANDLE]+[C.c_void_p]*4; k.GetProcessTimes.restype=W.BOOL
        k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)]
        k.QueryFullProcessImageNameW.restype=W.BOOL
        self._identity()

    def _call(self,row,label,address,payload):
        # Native calls and debugger publishers cannot overlap the A Snapshot
        # callback. Always enter Room before the shared call lock.
        with self.capture.room.lock,self.capture.coordinator.lock,self.call_lock:
            self._identity()
            try:
                code,_=self.call_state.invoke(lambda:remote_call(self.api,address,payload,row['folder'],label))
                return code
            except RemoteCallUnknown:
                self.uncertain=True
                raise

    def _publish(self,row,operation):
        with self.capture.room.lock,self.capture.coordinator.lock,self.call_lock:
            return self.call_state.invoke(lambda:super(ProtectedRulesFactory,self)._publish(row,operation))


class ProtectedRulesOwner:
    def __init__(self,entry,api,build,settings,records,call_lock,*,reward_flow=False,input_fence=False):
        from a_reward_runtime_mount import RuntimeMount
        need(type(reward_flow) is RuntimeMount and reward_flow.entry is entry and
             reward_flow.api is api and reward_flow.phase=='CONFIGURED' and input_fence is False,
             'Only exact same Runtime reward mount; independent flows/fences rejected')
        need(entry.provider is not None and entry.phase=='BOUND','Bind the actual A runtime first')
        self.entry=entry;self.port=None;self.factory=None;self.phase='NEW';self.failure=None;self.call_lock=call_lock
        self.installed_once=False;self.restore_verified=False
        self.capture=ProtectedRulesCapture(entry.provider,entry.room,entry.coordinator,settings)
        self.factory=ProtectedRulesFactory(self.capture,api,build,records,
            rulers=self._rulers(settings))
        self.factory.call_lock=call_lock;self.factory.call_state=reward_flow.state

    def _rulers(self,settings):
        # Read both current native force identities; do not manufacture the
        # other player's ruler from A's viewer or a network address.
        p=self.entry.provider;r=p.reader
        values={}
        for side in ('A','B'):
            force=self.capture.scope['bindings'][side]['force_id']
            address=int.from_bytes(r.memory.read(p.root+0xDCA0+force*8,8),'little')
            r.require_type(address,'CForceData')
            ruler=int.from_bytes(r.memory.read(address+0x10,2),'little')
            need(0<ruler<6000,'Invalid current human ruler')
            values[force]=ruler
        need(values[p.force]==p.ruler,'A native ruler changed')
        return values

    def install(self):
        need(self.phase=='NEW','Rules installation is once-only')
        self.phase='PREPARING'
        try:
            e=self.entry
            with e.room.lock,e.coordinator.lock:
                p=e.prep
                request=NextWorldRequest(1,digest(dict(scope=self.capture.scope,prepare_sha256=hashlib.sha256(bytes(p)).hexdigest())),
                    p.epoch.to_bytes(16,'little'),p.year,p.month,p.day)
                observed=self.capture.capture_loaded(request,side='A',expected_ruler=p.ruler)
                self.port=self.factory.prepare_rules(observed)
                d=Descriptor.from_buffer_copy(self.port._read(self.port.module.descriptor,C.sizeof(Descriptor)))
                actual=tuple((s.address-p.base,s.patch_size) for s in d.sites)
                need(actual==RULE_SITES and no_overlap(tuple((s.address-p.base,s.profile_size) for s in d.sites),SAVE_SITES),
                     'Rules descriptor overlaps A sources or changes approved sites')
                self.port.install();self.installed_once=True;self.phase='INSTALLED'
                self.verify()
                return self.status()
        except BaseException as exc:
            self._failed(exc);raise

    def verify(self):
        need(self.phase=='INSTALLED' and type(self.port) is ResidentPort,'Installed retained rules required')
        with self.entry.room.lock,self.entry.coordinator.lock:
            return self.port.observe(True,allow_date_advance=True)

    def restore(self):
        need(self.phase=='INSTALLED','Rules restoration requires a known installed owner')
        try:
            with self.entry.room.lock,self.entry.coordinator.lock:
                self.verify();result=self.port.restore();self.port.retired=True;self.restore_verified=True;self.phase='RESTORED'
                return result
        except BaseException as exc:
            self._failed(exc);raise

    def _failed(self,exc):
        self.phase='HELD';self.failure=repr(exc)
        if self.factory is not None and self.factory.uncertain and not isinstance(exc,RemoteCallUnknown):
            raise RemoteCallUnknown('Rules native/publisher outcome unresolved',dict(error=repr(exc),
                retained_rules=True,publisher_pids=[p.pid for p in self.factory.publishers])) from exc

    def status(self):
        return dict(phase=self.phase,failure=self.failure,installed_once=self.installed_once,
            restore_verified=self.restore_verified,retained_or_unknown=bool(not self.restore_verified and self.factory and (self.factory.retained or self.factory.uncertain)),
            installed=self.phase=='INSTALLED',
            restored=self.phase=='RESTORED',uncertain=bool(self.factory and self.factory.uncertain),
            module=self.port.module.module if self.port else None,retained_modules=len(self.factory.retained) if self.factory else 0,
            **CAPABILITIES)
