"""Explicit observed-boundary successor; frozen strong-fence contracts unchanged.

Reuses their exact native restore/load/world/Prepare/Seal/install predicates.
Only this constructor contract accepts repeated observations plus the human
no-new-command condition, instead of claiming a continuously held native fence.
"""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import threading

from b_remote_session_boundary import DiagnosticBoundary, need
from b_warm_remote_rules import RemoteRulesWorldCapture
from b_warm_rules_factory import RulesFactory, RulesBuild
from b_warm_refresh_bootstrap import BootstrapRulesBridge
from human_rules_world_lifecycle import WorldLifecycle
import b_warm_staging as files


class DiagnosticRulesCapture(RemoteRulesWorldCapture):
    def __init__(self, reader, control, scope, settings, *, boundary, read_birth):
        need(type(boundary) is DiagnosticBoundary and boundary.reader is reader,
             'Same typed diagnostic observation owner required')
        self.boundary = boundary
        super().__init__(reader, control, scope, settings, pid=boundary.pid, birth=boundary.birth,
                         read_birth=read_birth, guard_check=boundary.check)


class DiagnosticRulesFactory(RulesFactory):
    """Same real native methods, explicit narrow capture constructor.

The copied constructor differs only in accepted capture type. No native method
is overridden and there is still no reset, Revoke, unload or publisher retry.
"""
    def __init__(self, capture, api, build, records, *, rulers):
        need(type(capture) is DiagnosticRulesCapture and type(build) is RulesBuild,
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


class DiagnosticLifecycle(WorldLifecycle):
    """Local failure is terminal, NOT a claim that a native fence remains held."""
    def __init__(self, current, boundary):
        need(type(boundary) is DiagnosticBoundary, 'Typed observation owner required')
        self.boundary=boundary
        super().__init__(current, guard_check=boundary.check, on_hold=boundary.hold)

    def status(self):
        return {**super().status(), 'input_exclusion_proven':False,
                'scheduler_fence_proven':False, 'human_no_new_commands':True,
                'boundary_kind':'REPEATED_COMPLETE_PLANNING_OBSERVATION'}


class DiagnosticBridge(BootstrapRulesBridge):
    def __init__(self, lifecycle, warm, *, target, records):
        need(type(lifecycle) is DiagnosticLifecycle, 'Explicit diagnostic lifecycle required')
        need(all(callable(getattr(warm,n,None)) for n in ('open_bank','authorize_second','load','abort')),
             'Missing retained native warm port')
        self.lifecycle,self.warm=lifecycle,warm
        self.target,self.records=files.clean_path(target),files.clean_path(records)
        need(self.target.name==files.NAME and self.records.is_dir() and self.records!=self.target.parent,
             'Independent private records and exact target required')
        self.completed=[]; self.phase='ACTIVE'; self._lock=threading.RLock()
        self.initial_target=files.read_file(self.target)[0]

    def _load_checkpoint(self, request, profile, source, index):
        result=super()._load_checkpoint(request,profile,source,index)
        # Original acceptance (including native refresh + retired target lease)
        # has succeeded; only now may observations address the new planning world.
        self.lifecycle.boundary.loaded(profile)
        return result

    def replace(self, request, profile, source, *, observe_loaded, prepare_rules):
        self.lifecycle.boundary.begin(profile)
        return super().replace(request,profile,source,observe_loaded=observe_loaded,prepare_rules=prepare_rules)
