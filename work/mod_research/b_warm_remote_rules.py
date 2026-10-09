"""B-side native rules capture through an authenticated authority connection.

No A Room or PeriodCoordinator is copied into B. The server's read-only binding
endpoint authenticates the current B control connection and its retained scope.
A network reply never proves native exclusion: guard_check remains a trusted
local owner callback. Importing this module neither opens nor writes a process.
"""
from copy import deepcopy
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import threading

from authoritative_sync import canonical, validate_scope
from checkpoint_room_client import RoomConnection
from b_warm_rules_capture import RulesWorldCapture, need
from b_warm_rules_factory import RulesFactory, RulesBuild
from human_rules_activation_room import GAME_SHA, rules
from human_rules_world_lifecycle import check_port
from room_session import digest


class RemoteRulesWorldCapture(RulesWorldCapture):
    def __init__(self, reader, control, scope, settings, *, pid, birth,
                 read_birth, guard_check):
        need(type(control) is RoomConnection and control.player_id == 'B',
             'Retained authenticated B control connection required')
        validate_scope(scope)
        need(type(pid) is int and 0 < pid < 2**32 and
             type(birth) is int and 0 < birth < 2**64, 'Explicit process incarnation required')
        need(callable(read_birth) and callable(guard_check), 'Local identity and boundary callbacks required')
        need(type(settings) is dict and settings == rules(settings.get('native_income_key5'),
             settings.get('native_world_option8')), 'Unsupported rules settings')
        self.reader, self.control = reader, control
        self._control_owner = control
        self.settings, self.scope = deepcopy(settings), deepcopy(scope)
        self._scope_bytes = canonical(scope)
        self.pid, self.birth = pid, birth
        self.read_birth, self.guard_check = read_birth, guard_check
        self.image = reader.memory.base
        need(type(self.image) is int and 0x10000 <= self.image < 0x7fffffffffff-0x2238000,
             'Invalid image')
        self.failed = None
        self._check()

    def _check(self):
        need(self.failed is None, 'Remote rules capture is held; no automatic reconnect')
        try:
            check_port(self.guard_check)
            need(self.control is self._control_owner and type(self.control) is RoomConnection and
                 self.control.player_id == 'B' and self.control.status()['transport_open'] is True,
                 'Retained B control connection changed or closed')
            r = self.reader
            need(r.pid == self.pid and r.memory.base == self.image and r.sha256 == GAME_SHA and
                 self.read_birth() == self.birth, 'Pinned process/image incarnation changed')
            need(canonical(self.scope) == self._scope_bytes and
                 self.scope['profile']['game_sha256'] == GAME_SHA and
                 self.scope['profile']['rules_sha256'] == digest(self.settings),
                 'Pinned room rules/build changed')
            reply = self.control.request({'action': 'warm_rules_binding'})
            need(type(reply) is dict and reply.get('ok') is True and
                 canonical(reply.get('scope')) == self._scope_bytes and
                 reply.get('native_permission') is False and
                 reply.get('native_gameplay_enabled') is False,
                 'Authority binding unavailable, held or changed')
            check_port(self.guard_check)
        except BaseException as exc:
            self.failed = type(exc).__name__ + ': ' + str(exc)
            raise


class RemoteRulesFactory(RulesFactory):
    """Explicit constructor successor; native preparation/publication unchanged.

    Only the accepted capture type differs. RulesBuild and actual ProcessAPI
    identity checks remain the predecessor's; no fake local Room is introduced.
    """
    def __init__(self, capture, api, build, records, *, rulers):
        need(type(capture) is RemoteRulesWorldCapture and type(build) is RulesBuild,'Retained typed native capture/build required')
        need(api.reader is capture.reader,'API and capture must share the retained reader')
        self.capture,self.api,self.build=capture,api,build
        self.records=Path(records).resolve(strict=True)
        need(self.records.is_dir(),'Existing private records directory required')
        self.rulers=dict(rulers)
        need(set(self.rulers)==set(capture.scope['bindings'][p]['force_id'] for p in ('A','B')) and
             all(type(x) is int and 0<x<6000 for x in self.rulers.values()),'Exact two viewer/ruler expectations required')
        self.retained=[];self.publishers=[];self.claimed=set();self.failed=None;self.uncertain=False
        self._lock=threading.RLock()
        k=api.k
        k.GetProcessId.argtypes=[W.HANDLE];k.GetProcessId.restype=W.DWORD
        k.GetProcessTimes.argtypes=[W.HANDLE]+[C.c_void_p]*4;k.GetProcessTimes.restype=W.BOOL
        k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.QueryFullProcessImageNameW.restype=W.BOOL
        self._identity()
